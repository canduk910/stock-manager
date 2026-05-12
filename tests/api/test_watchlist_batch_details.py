"""트랙 4: GET /api/watchlist/batch-details 엔드포인트 검증."""
from unittest.mock import patch


def _fake_kr_metrics(code):
    return {
        "market_type": "KOSPI",
        "mktcap": 100000000000,
        "per": 10.5,
        "pbr": 1.2,
        "roe": 8.0,
        "dividend_yield": 2.5,
        "sector": "반도체",
    }


def _fake_kr_price(code):
    return {
        "close": 70000,
        "change": 500,
        "change_pct": 0.72,
        "mktcap": 100000000000,
    }


def _fake_us_detail(code):
    return {
        "close": 200.0,
        "change": 2.0,
        "change_pct": 1.0,
        "mktcap": 3000000000000,
        "per": 28.0,
        "pbr": 9.5,
        "dividend_yield": 0.5,
        "sector": "IT",
    }


def test_batch_details_success_kr(client):
    """codes 2개 KR 조회 → details에 두 종목 모두 키 존재."""
    with patch("services.watchlist_service.fetch_market_metrics", side_effect=_fake_kr_metrics), \
         patch("services.watchlist_service.fetch_price", side_effect=_fake_kr_price):
        r = client.get("/api/watchlist/batch-details?codes=005930,000660&market=KR")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "details" in body
    assert "errors" in body
    assert "005930" in body["details"]
    assert "000660" in body["details"]
    assert body["details"]["005930"]["per"] == 10.5
    assert body["details"]["005930"]["sector"]  # 한글 정규화 통과


def test_batch_details_empty_codes_returns_400(client):
    r = client.get("/api/watchlist/batch-details?codes=&market=KR")
    assert r.status_code == 400


def test_batch_details_exceeds_50_returns_400(client):
    codes = ",".join(f"{i:06d}" for i in range(51))
    r = client.get(f"/api/watchlist/batch-details?codes={codes}&market=KR")
    assert r.status_code == 400


def test_batch_details_auto_market(client):
    """market=auto → 국내 6자리 KR, 알파벳 US 자동 판별."""
    with patch("services.watchlist_service.fetch_market_metrics", side_effect=_fake_kr_metrics), \
         patch("services.watchlist_service.fetch_price", side_effect=_fake_kr_price), \
         patch("stock.yf_client.fetch_detail_yf", side_effect=_fake_us_detail):
        r = client.get("/api/watchlist/batch-details?codes=005930,AAPL&market=auto")
    assert r.status_code == 200
    body = r.json()
    assert "005930" in body["details"]
    assert "AAPL" in body["details"]


def test_batch_details_partial_failure(client):
    """일부 종목 fetch 실패 시 부분 결과 반환."""
    call_count = {"n": 0}

    def metrics(code):
        call_count["n"] += 1
        if code == "999999":
            raise RuntimeError("not found")
        return _fake_kr_metrics(code)

    with patch("services.watchlist_service.fetch_market_metrics", side_effect=metrics), \
         patch("services.watchlist_service.fetch_price", side_effect=_fake_kr_price):
        r = client.get("/api/watchlist/batch-details?codes=005930,999999&market=KR")
    assert r.status_code == 200
    body = r.json()
    assert "005930" in body["details"]
    # 실패한 코드는 errors에 기록
    assert any("999999" in str(e) for e in body["errors"])


def test_batch_details_unauthorized(raw_client):
    """인증 없이 호출 시 401."""
    r = raw_client.get("/api/watchlist/batch-details?codes=005930&market=KR")
    assert r.status_code in (401, 403)
