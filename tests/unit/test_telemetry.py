"""Phase 3 — services/_telemetry.py 단위 테스트.

검증 대상:
- @timed 데코레이터: 정상/예외 경로 모두 timing 기록
- record_event 카운터 누적
- observe → percentile (p50/p95/p99) 계산
- flush_counters: dump + reset
- start/stop_periodic_flush: 스레드 라이프사이클
- 비활성화(TELEMETRY_ENABLED=0)
"""

import logging
import threading
import time

import pytest

from services import _telemetry as tel


@pytest.fixture(autouse=True)
def _reset():
    """각 테스트 격리."""
    tel._reset_for_test()
    # ENABLED 강제 활성 (다른 테스트가 끄고 갔을 가능성 차단)
    tel._ENABLED = True
    yield
    tel._reset_for_test()


class TestRecordEvent:
    def test_basic_increment(self):
        tel.record_event("foo")
        tel.record_event("foo")
        tel.record_event("bar", 3)
        snap = tel.snapshot()
        assert snap["counters"]["foo"] == 2
        assert snap["counters"]["bar"] == 3

    def test_disabled_no_effect(self, monkeypatch):
        monkeypatch.setattr(tel, "_ENABLED", False)
        tel.record_event("foo")
        assert "foo" not in tel.snapshot()["counters"]

    def test_thread_safe(self):
        """동시에 1000건 +1 → 정확히 1000."""
        def _worker():
            for _ in range(100):
                tel.record_event("concurrent")

        threads = [threading.Thread(target=_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert tel.snapshot()["counters"]["concurrent"] == 1000


class TestObserveAndPercentile:
    def test_percentile_basic(self):
        for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            tel.observe("lat.ms", v)
        pct = tel.snapshot()["percentiles"]["lat.ms"]
        assert pct["n"] == 10
        # nearest-rank: p50 → idx=round(0.5*9)=4 → s[4]=50
        assert pct["p50"] == 50.0
        # p95 → idx=round(0.95*9)=9 → s[9]=100
        assert pct["p95"] == 100.0

    def test_empty_observations(self):
        snap = tel.snapshot()
        assert snap["percentiles"] == {}

    def test_observe_window_capped(self):
        """maxlen=1000 초과 시 oldest drop."""
        for i in range(1500):
            tel.observe("cap.ms", float(i))
        pct = tel.snapshot()["percentiles"]["cap.ms"]
        assert pct["n"] == 1000  # capped


class TestTimedDecorator:
    def test_records_duration_and_call_count(self):
        @tel.timed("widget.do")
        def do_work(x):
            time.sleep(0.005)  # 5ms
            return x * 2

        assert do_work(7) == 14
        assert do_work(3) == 6

        snap = tel.snapshot()
        assert snap["counters"]["widget.do.calls"] == 2
        pct = snap["percentiles"]["widget.do.duration_ms"]
        assert pct["n"] == 2
        assert pct["p50"] >= 4.0  # 5ms sleep → 최소 4ms 이상

    def test_records_error_and_propagates(self):
        @tel.timed("widget.fail")
        def will_fail():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            will_fail()

        snap = tel.snapshot()
        assert snap["counters"]["widget.fail.calls"] == 1
        assert snap["counters"]["widget.fail.errors"] == 1
        # errored 호출도 duration은 기록됨 (finally)
        assert "widget.fail.duration_ms" in snap["percentiles"]

    def test_preserves_signature(self):
        """functools.wraps로 메타데이터 보존."""
        @tel.timed("ws.f")
        def my_func(a, b):
            """orig docstring"""
            return a + b

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "orig docstring"
        assert my_func(2, 3) == 5

    def test_disabled_no_overhead_path(self, monkeypatch):
        """TELEMETRY_ENABLED=0이면 본 함수만 호출, 카운터 증가 없음."""
        monkeypatch.setattr(tel, "_ENABLED", False)

        @tel.timed("disabled.f")
        def f():
            return 42

        assert f() == 42
        assert "disabled.f.calls" not in tel.snapshot()["counters"]


class TestFlushCounters:
    def test_flush_dumps_and_resets(self, caplog):
        tel.record_event("a", 5)
        tel.observe("lat", 100)

        with caplog.at_level(logging.INFO, logger="telemetry"):
            tel.flush_counters(reset=True)

        # 로그에 카운터/observe 출력 확인
        msgs = " ".join(r.getMessage() for r in caplog.records)
        assert "a=5" in msgs
        assert "lat" in msgs

        # reset 확인
        snap = tel.snapshot()
        assert snap["counters"] == {}
        assert snap["percentiles"] == {}

    def test_flush_no_reset(self):
        tel.record_event("keep", 1)
        tel.flush_counters(reset=False)
        assert tel.snapshot()["counters"]["keep"] == 1


class TestPeriodicFlush:
    def test_start_stop_lifecycle(self):
        tel.start_periodic_flush(interval_sec=10)
        assert tel._flush_thread is not None
        assert tel._flush_thread.is_alive()

        # idempotent: 두 번 호출해도 추가 스레드 안 만듦
        first = tel._flush_thread
        tel.start_periodic_flush(interval_sec=10)
        assert tel._flush_thread is first

        tel.stop_periodic_flush(final_flush=False)
        assert tel._flush_thread is None

    def test_stop_without_start_safe(self):
        """start 안 했어도 stop 호출 안전."""
        tel.stop_periodic_flush(final_flush=False)  # no-op
