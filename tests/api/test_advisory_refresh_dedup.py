"""트랙 1 stampede 방지 검증.

동시 N명이 동일 종목 refresh_stock_data 호출 시 외부 fetcher는 1회만 호출되어야 한다.
"""
import threading
import time
from unittest.mock import patch

from services import advisory_service


def test_concurrent_refresh_deduplicates(client, db_session):
    """ThreadPoolExecutor로 동시 5번 refresh → fetcher 1회 호출.

    client fixture 사용 — SessionLocal 바인딩을 테스트 엔진으로 교체 → fixture cleanup으로 truncate 보장.
    """
    call_counts = {"fundamental": 0, "technical": 0, "research": 0, "strategy": 0}
    lock = threading.Lock()

    def slow_fundamental(code, market, name, user_id=1):
        with lock:
            call_counts["fundamental"] += 1
        time.sleep(0.3)
        return {"metrics": {"per": 10}}

    def slow_technical(code, market):
        with lock:
            call_counts["technical"] += 1
        time.sleep(0.3)
        return {"indicators": {"rsi": 55}}

    def slow_research(code, market, name):
        with lock:
            call_counts["research"] += 1
        time.sleep(0.3)
        return {"news": []}

    def slow_strategy(code, market):
        with lock:
            call_counts["strategy"] += 1
        time.sleep(0.3)
        return None

    with patch.object(advisory_service, "_collect_fundamental", side_effect=slow_fundamental), \
         patch.object(advisory_service, "_collect_technical", side_effect=slow_technical), \
         patch.object(advisory_service, "_collect_research", side_effect=slow_research), \
         patch.object(advisory_service, "_collect_strategy_signals", side_effect=slow_strategy):

        # 동시 5 호출 (다른 user_id로)
        threads = []
        results = []

        def call(user_id):
            try:
                r = advisory_service.refresh_stock_data("005930", "KR", "삼성전자", user_id=user_id)
                results.append(r)
            except Exception as e:
                results.append({"error": str(e)})

        for uid in range(1, 6):
            t = threading.Thread(target=call, args=(uid,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

    # Stampede 방지: 각 collector는 1회만 호출
    assert call_counts["fundamental"] == 1, f"fundamental called {call_counts['fundamental']}x"
    assert call_counts["technical"] == 1, f"technical called {call_counts['technical']}x"
    assert call_counts["research"] == 1, f"research called {call_counts['research']}x"
    # strategy도 1회 (mcp 비활성화여도 lock 안에서 1회만)
    assert call_counts["strategy"] == 1, f"strategy called {call_counts['strategy']}x"

    # 모든 호출이 동일 데이터 반환
    assert len(results) == 5
    for r in results:
        assert "fundamental" in r or "error" in r
