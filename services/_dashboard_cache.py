"""사용자별 watchlist dashboard 응답 in-memory 캐시 (QW-4).

목적
----
- F5 연타 시 ThreadPool 풀가동 반복으로 t3.small swap thrashing 발생.
- 사용자별 (user_id, items hash) 키로 60s TTL in-memory 캐시 → 즉시 응답.
- 동시 30 사용자 시 외부 API 호출 1/30로 감소.

설계
----
- 키: (user_id, hash(sorted((code, market) tuples))). 종목 추가/삭제 즉시 새 키.
- 값: (data, expires_at). data는 list[dict] (dashboard 행).
- TTL: 60s (default). add/remove/update_memo 핸들러에서 invalidate(user_id) 호출.
- 동시성: threading.Lock으로 dict 보호.
- 부분 실패(partial_failure 포함) 응답은 짧은 TTL(15s)로 캐시 — 다음 요청에서 재시도 유도.

멀티 인스턴스 제약 (F-4-A 참조)
----------------------------
- in-memory 캐시는 인스턴스별 독립. 멀티 인스턴스 전환 시 Redis 등 외부 캐시로 재설계 필요.
- 현재 EC2 단일 인스턴스 환경에서만 유효.
"""

from __future__ import annotations

import threading
import time
from typing import Iterable, Optional

# (user_id, items_hash) -> (data, expires_at)
_CACHE: dict[tuple, tuple] = {}
_LOCK = threading.Lock()

DEFAULT_TTL_SEC = 60.0
PARTIAL_FAILURE_TTL_SEC = 15.0  # 부분 실패는 짧게 캐시 → 곧 재시도


def _now() -> float:
    return time.time()


def _make_key(user_id: int, items: Iterable[dict]) -> tuple:
    """items 순서 무관, (code, market) 튜플의 sorted hash."""
    pairs = tuple(sorted(
        ((it.get("code", ""), it.get("market", "KR")) for it in (items or [])),
    ))
    return (int(user_id), pairs)


def _has_partial_failure(data) -> bool:
    if not isinstance(data, list):
        return False
    return any(
        isinstance(row, dict) and row.get("partial_failure")
        for row in data
    )


def get(*, user_id: int, items: Iterable[dict]) -> Optional[list]:
    """캐시 조회. 만료/미스 시 None."""
    key = _make_key(user_id, items)
    with _LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        data, expires_at = entry
        if _now() >= expires_at:
            _CACHE.pop(key, None)
            return None
        return data


def set(*, user_id: int, items: Iterable[dict], data: list, ttl: Optional[float] = None) -> None:
    """캐시 저장. ttl=None이면 partial_failure 여부에 따라 자동 결정."""
    key = _make_key(user_id, items)
    if ttl is None:
        ttl = PARTIAL_FAILURE_TTL_SEC if _has_partial_failure(data) else DEFAULT_TTL_SEC
    with _LOCK:
        _CACHE[key] = (data, _now() + ttl)


def invalidate(user_id: int) -> None:
    """특정 사용자 모든 캐시 엔트리 삭제."""
    uid = int(user_id)
    with _LOCK:
        keys_to_drop = [k for k in _CACHE if k[0] == uid]
        for k in keys_to_drop:
            _CACHE.pop(k, None)


def invalidate_all() -> None:
    """전체 캐시 비우기 (테스트 헬퍼)."""
    with _LOCK:
        _CACHE.clear()
