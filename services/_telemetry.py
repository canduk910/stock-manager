"""경량 계측 모듈 (Phase 3 — 1주 누적 측정).

설계 원칙:
- **외부 의존성 0**: stdlib + 기존 logging만 사용. prometheus/statsd 도입 X.
- **본 로직 미터치**: 데코레이터/카운터 호출만 추가. 함수 시그니처/반환값 보존.
- **메모리 안전**: t3.small 4GB swap 환경. Counter dict + percentile deque 합 < 1MB 유지.
- **즉시 dump 금지**: 5분 누적 후 stdout dump → Docker logs 수집.

API:
- `@timed(name)`               : 함수 실행 시간 측정 데코레이터
- `record_event(name, n=1)`     : counter 증가
- `observe(name, value)`        : 분포 관측 (p50/p95/p99 계산용)
- `flush_counters()`            : 즉시 dump + reset (테스트/관리용)
- `start_periodic_flush(interval_sec=300)` / `stop_periodic_flush()` : main.py lifespan 통합
- `snapshot()`                  : 현재 누적값을 dict로 반환 (테스트 검증용)
"""

import logging
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger("telemetry")

# ── 내부 상태 (모듈 전역, threading.Lock 보호) ────────────────────────────────

_lock = threading.Lock()

# counter: {name: int}
_counters: dict[str, int] = defaultdict(int)

# observation window: {name: deque[float]} — 최근 N개 관측값. percentile 계산용.
# maxlen은 메모리 상한. 1000 × 8 bytes ≈ 8KB/observation. 50개 이름 가정 시 400KB.
_OBSERVE_MAXLEN = 1000
_observations: dict[str, deque] = defaultdict(lambda: deque(maxlen=_OBSERVE_MAXLEN))

# periodic flush thread
_flush_thread: Optional[threading.Thread] = None
_flush_stop_event: Optional[threading.Event] = None

# 환경변수로 비활성화 (TESTING 환경에선 자동 off, prod에선 명시 enable)
_ENABLED = os.environ.get("TELEMETRY_ENABLED", "1") not in ("0", "false", "False")

_KST = timezone(timedelta(hours=9))


def _kst_now_str() -> str:
    return datetime.now(_KST).strftime("%Y-%m-%d %H:%M:%S KST")


# ── 공개 API ────────────────────────────────────────────────────────────────


def record_event(name: str, n: int = 1) -> None:
    """카운터 +n. 실패해도 본 로직 영향 없음 (best effort)."""
    if not _ENABLED:
        return
    try:
        with _lock:
            _counters[name] += n
    except Exception:
        pass  # 계측 실패가 본 로직을 죽이지 않게


def observe(name: str, value: float) -> None:
    """분포 관측. duration_ms 등 percentile 대상 값을 넣는다."""
    if not _ENABLED:
        return
    try:
        with _lock:
            _observations[name].append(float(value))
    except Exception:
        pass


def timed(name: str) -> Callable:
    """함수 실행 시간(ms)을 `{name}.duration_ms`로 observe하는 데코레이터.

    - 호출 횟수는 `{name}.calls`로 별도 카운터에 기록.
    - 예외 발생 시 `{name}.errors` 카운터 증가 + 예외는 그대로 전파 (본 로직 보호).
    - 동기 함수 전용 (FastAPI sync 핸들러 + ThreadPool 작업자에 적합).
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _ENABLED:
                return func(*args, **kwargs)
            t0 = time.perf_counter()
            try:
                return func(*args, **kwargs)
            except Exception:
                record_event(f"{name}.errors")
                raise
            finally:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                observe(f"{name}.duration_ms", duration_ms)
                record_event(f"{name}.calls")
        return wrapper
    return decorator


def _percentiles(values: list[float]) -> dict[str, float]:
    """p50/p95/p99 계산 (단순 sort + 인덱싱). values가 비면 빈 dict."""
    if not values:
        return {}
    s = sorted(values)
    n = len(s)

    def _pick(p: float) -> float:
        # nearest-rank percentile (단순/일관성 우선)
        idx = max(0, min(n - 1, int(round(p / 100.0 * (n - 1)))))
        return round(s[idx], 1)

    return {"p50": _pick(50), "p95": _pick(95), "p99": _pick(99), "n": n}


def snapshot() -> dict[str, Any]:
    """현재 누적값 스냅샷 (reset 없음). 테스트/디버깅용."""
    with _lock:
        counters = dict(_counters)
        observations = {k: list(v) for k, v in _observations.items()}
    return {
        "counters": counters,
        "percentiles": {k: _percentiles(v) for k, v in observations.items()},
    }


def flush_counters(reset: bool = True) -> None:
    """현재 누적값을 stdout(logger.info)으로 dump. reset=True면 비운다.

    Docker logs / journald가 line-based로 수집. nginx access_log와 별개 stdout.
    """
    if not _ENABLED:
        return
    snap = snapshot()
    ts = _kst_now_str()
    for name in sorted(snap["counters"].keys()):
        logger.info("[%s] telemetry counter %s=%d", ts, name, snap["counters"][name])
    for name in sorted(snap["percentiles"].keys()):
        pct = snap["percentiles"][name]
        if not pct:
            continue
        logger.info(
            "[%s] telemetry observe %s p50=%.1f p95=%.1f p99=%.1f n=%d",
            ts, name, pct["p50"], pct["p95"], pct["p99"], pct["n"],
        )
    if reset:
        with _lock:
            _counters.clear()
            _observations.clear()


# ── 주기적 flush (lifespan 통합) ─────────────────────────────────────────────


def start_periodic_flush(interval_sec: int = 300) -> None:
    """5분 간격으로 flush_counters() 호출하는 백그라운드 스레드 시작.

    main.py lifespan startup에서 호출.
    이미 실행 중이면 무시 (idempotent).
    """
    global _flush_thread, _flush_stop_event
    if not _ENABLED:
        return
    if _flush_thread is not None and _flush_thread.is_alive():
        return

    _flush_stop_event = threading.Event()
    stop_event = _flush_stop_event

    def _run():
        while not stop_event.wait(interval_sec):
            try:
                flush_counters(reset=True)
            except Exception as e:  # 절대 죽지 않도록
                logger.warning("telemetry flush failed: %s", e)

    _flush_thread = threading.Thread(target=_run, name="telemetry-flush", daemon=True)
    _flush_thread.start()


def stop_periodic_flush(final_flush: bool = True) -> None:
    """주기적 flush 중지. main.py lifespan shutdown에서 호출."""
    global _flush_thread, _flush_stop_event
    if _flush_stop_event is not None:
        _flush_stop_event.set()
    if _flush_thread is not None:
        _flush_thread.join(timeout=2.0)
    _flush_thread = None
    _flush_stop_event = None
    if final_flush and _ENABLED:
        try:
            flush_counters(reset=True)
        except Exception:
            pass


# ── 테스트 헬퍼 (프로덕션에서도 안전) ─────────────────────────────────────────


def _reset_for_test() -> None:
    """테스트 격리용. counter + observation 모두 비운다."""
    with _lock:
        _counters.clear()
        _observations.clear()
