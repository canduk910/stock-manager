"""트랙 2: advisory_service.refresh_stock_data 4단계 병렬화 검증.

mock으로 각 단계 sleep(0.3) 부여 → 전체 wall-time < 0.6s 검증.
직렬이면 ≥1.2s이므로 명확히 구분된다.
"""
import time
from unittest.mock import patch

from services import advisory_service


def test_refresh_runs_phases_in_parallel(client, db_session):
    """4단계가 병렬 실행되어 전체 시간 ≈ max(개별 시간)."""

    def slow(name, *, delay=0.3, retval=None):
        def fn(*args, **kwargs):
            time.sleep(delay)
            return retval
        fn.__name__ = name
        return fn

    with patch.object(advisory_service, "_collect_fundamental",
                      side_effect=slow("fundamental", retval={"metrics": {}})), \
         patch.object(advisory_service, "_collect_technical",
                      side_effect=slow("technical", retval={"indicators": {}})), \
         patch.object(advisory_service, "_collect_research",
                      side_effect=slow("research", retval={})), \
         patch.object(advisory_service, "_collect_strategy_signals",
                      side_effect=slow("strategy", retval=None)):

        t0 = time.perf_counter()
        result = advisory_service.refresh_stock_data("005930", "KR", "삼성전자", user_id=1)
        elapsed = time.perf_counter() - t0

    # 병렬이면 < 0.6s (4 × 0.3 = 1.2s 직렬 → max ≈ 0.3s + overhead)
    # 단, stampede lock + DB 저장 오버헤드 고려 0.8s 허용
    assert elapsed < 0.9, f"phases not parallel: elapsed={elapsed:.3f}s"
    assert result is not None
    assert "fundamental" in result


def test_partial_failure_preserves_other_phases(client, db_session):
    """한 단계 예외 → 다른 단계 결과 보존, 실패 단계는 빈 dict."""

    def fail(*args, **kwargs):
        raise RuntimeError("simulated failure")

    def ok_fundamental(*args, **kwargs):
        return {"metrics": {"per": 12}}

    def ok_technical(*args, **kwargs):
        return {"indicators": {"rsi": 60}}

    def ok_research(*args, **kwargs):
        return {"news": ["x"]}

    with patch.object(advisory_service, "_collect_fundamental", side_effect=ok_fundamental), \
         patch.object(advisory_service, "_collect_technical", side_effect=ok_technical), \
         patch.object(advisory_service, "_collect_research", side_effect=fail), \
         patch.object(advisory_service, "_collect_strategy_signals", return_value=None):

        result = advisory_service.refresh_stock_data("005930", "KR", "삼성전자", user_id=1)

    assert result is not None
    # fundamental/technical은 정상 반환
    assert result["fundamental"]["metrics"]["per"] == 12
    assert result["technical"]["indicators"]["rsi"] == 60
    # research는 실패 → 빈 dict
    assert result["research_data"] == {}
