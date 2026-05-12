"""트랙 4 service: WatchlistService.fetch_batch_details mock 검증."""
from unittest.mock import patch

from services.watchlist_service import WatchlistService


def test_batch_details_threadpool_calls(db_session):
    """ThreadPoolExecutor가 코드별 fetch를 병렬 호출."""
    calls = []

    def fake_metrics(code):
        calls.append(code)
        return {
            "market_type": "KOSPI",
            "mktcap": 100,
            "per": 10,
            "pbr": 1.0,
            "roe": 8,
            "dividend_yield": 2,
            "sector": "반도체",
        }

    def fake_price(code):
        return {"close": 70000, "change": 100, "change_pct": 0.1, "mktcap": 100}

    svc = WatchlistService()
    with patch("services.watchlist_service.fetch_market_metrics", side_effect=fake_metrics), \
         patch("services.watchlist_service.fetch_price", side_effect=fake_price):
        result = svc.fetch_batch_details(["005930", "000660", "035420"], market="KR")

    assert set(calls) == {"005930", "000660", "035420"}
    assert "details" in result
    assert len(result["details"]) == 3
    assert result["errors"] == []


def test_batch_details_partial_failure_skips_failed(db_session):
    """한 종목 실패 → errors에 기록, 나머지는 정상 반환."""
    def fake_metrics(code):
        if code == "BAD":
            raise RuntimeError("boom")
        return {"per": 5, "pbr": 1, "roe": 7, "dividend_yield": 1, "sector": "IT", "mktcap": 100}

    def fake_price(code):
        return {"close": 1000, "change": 0, "change_pct": 0, "mktcap": 100}

    svc = WatchlistService()
    with patch("services.watchlist_service.fetch_market_metrics", side_effect=fake_metrics), \
         patch("services.watchlist_service.fetch_price", side_effect=fake_price):
        result = svc.fetch_batch_details(["005930", "BAD"], market="KR")

    assert "005930" in result["details"]
    assert "BAD" not in result["details"]
    assert any("BAD" in e for e in result["errors"])


def test_batch_details_auto_market_per_code(db_session):
    """auto 모드 — code별 KR/US 자동 판별."""
    def fake_metrics(code):
        return {"per": 10, "pbr": 1, "roe": 8, "dividend_yield": 2, "sector": "반도체", "mktcap": 100}

    def fake_price(code):
        return {"close": 70000, "change": 0, "change_pct": 0, "mktcap": 100}

    def fake_us_detail(code):
        return {"close": 200, "change": 0, "change_pct": 0, "mktcap": 5000,
                "per": 30, "pbr": 10, "dividend_yield": 0.5, "sector": "IT"}

    svc = WatchlistService()
    with patch("services.watchlist_service.fetch_market_metrics", side_effect=fake_metrics), \
         patch("services.watchlist_service.fetch_price", side_effect=fake_price), \
         patch("stock.yf_client.fetch_detail_yf", side_effect=fake_us_detail):
        result = svc.fetch_batch_details(["005930", "AAPL"], market="auto")

    assert "005930" in result["details"]
    assert "AAPL" in result["details"]
    # 통화 구분
    assert result["details"]["005930"]["currency"] == "KRW"
    assert result["details"]["AAPL"]["currency"] == "USD"
