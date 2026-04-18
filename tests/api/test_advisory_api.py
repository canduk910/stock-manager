"""Advisory API 엔드포인트 테스트 (A-040 ~ A-049)."""

import pytest


class TestAdvisoryStocks:
    """자문종목 관리."""

    def test_list_stocks(self, client):
        """A-040: GET /api/advisory → 200, list."""
        resp = client.get("/api/advisory")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_add_stock(self, client):
        """A-041: POST /api/advisory → 200 or 409(중복) or 400."""
        resp = client.post("/api/advisory", json={
            "code": "005930",
            "market": "KR",
            "memo": "테스트",
        })
        # 성공 → 200, 이미 등록 → 409, 종목명 조회 실패 → 400
        assert resp.status_code in (200, 201, 400, 409)

    def test_add_stock_duplicate(self, client):
        """A-042: 중복 추가 → 409."""
        body = {"code": "005930", "market": "KR"}
        first = client.post("/api/advisory", json=body)
        if first.status_code in (200, 201):
            second = client.post("/api/advisory", json=body)
            assert second.status_code == 409

    def test_remove_stock_not_found(self, client):
        """A-043: 없는 종목 삭제 → 404."""
        resp = client.delete("/api/advisory/ZZZZZZ", params={"market": "KR"})
        assert resp.status_code == 404


class TestAdvisoryData:
    """자문 데이터 조회."""

    def test_get_data_not_cached(self, client):
        """A-045: 캐시 없는 종목 데이터 → 404."""
        resp = client.get("/api/advisory/999999/data", params={"market": "KR"})
        assert resp.status_code == 404

    def test_analyze_no_openai(self, client):
        """A-046: AI 분석 → 503(키 없음) / 404(캐시 없음) / 200(정상)."""
        resp = client.post("/api/advisory/005930/analyze", params={"market": "KR"})
        # OpenAI 키 미설정 → 503, 캐시 없으면 404, 키+캐시 있으면 200
        assert resp.status_code in (200, 503, 404)

    def test_get_ohlcv(self, client):
        """A-047: OHLCV 차트 데이터 → 200 (yfinance 기반)."""
        resp = client.get("/api/advisory/005930/ohlcv", params={
            "market": "KR",
            "interval": "1d",
            "period": "1mo",
        })
        # yfinance 조회 → 200 or 외부 API 실패 시 502
        assert resp.status_code in (200, 502)


class TestAdvisoryReports:
    """자문 리포트 조회."""

    def test_get_report_history(self, client):
        """A-048: 리포트 이력 → 200, list."""
        resp = client.get("/api/advisory/005930/reports", params={"market": "KR"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_report_not_found(self, client):
        """A-049: 최신 리포트 없음 → 404."""
        resp = client.get("/api/advisory/ZZZZZZ/report", params={"market": "KR"})
        assert resp.status_code == 404
