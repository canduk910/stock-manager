"""Market Board API 엔드포인트 테스트 (A-090 ~ A-096)."""

import pytest


class TestMarketBoardData:
    """시세판 데이터 엔드포인트."""

    def test_get_new_highs_lows(self, client):
        """A-090: GET /api/market-board/new-highs-lows → 200."""
        resp = client.get("/api/market-board/new-highs-lows")
        assert resp.status_code in (200, 502)

    def test_post_sparklines(self, client):
        """A-091: POST /api/market-board/sparklines → 200."""
        resp = client.post("/api/market-board/sparklines", json={
            "items": [
                {"code": "005930", "market": "KR"},
            ]
        })
        assert resp.status_code in (200, 502)


class TestMarketBoardCustomStocks:
    """시세판 별도 등록 종목 CRUD."""

    def test_list_custom_stocks(self, client):
        """A-092: GET /api/market-board/custom-stocks → 200."""
        resp = client.get("/api/market-board/custom-stocks")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_add_custom_stock(self, client):
        """A-093: POST /api/market-board/custom-stocks → 201."""
        resp = client.post("/api/market-board/custom-stocks", json={
            "code": "005930",
            "name": "삼성전자",
            "market": "KR",
        })
        assert resp.status_code in (201, 409)
        if resp.status_code == 201:
            data = resp.json()
            assert "item" in data

    def test_add_custom_stock_duplicate(self, client):
        """A-093b: 중복 추가 → 409."""
        body = {"code": "TEST01", "name": "테스트", "market": "KR"}
        client.post("/api/market-board/custom-stocks", json=body)
        second = client.post("/api/market-board/custom-stocks", json=body)
        assert second.status_code == 409

    def test_remove_custom_stock_not_found(self, client):
        """A-094: 없는 종목 삭제 → 404."""
        resp = client.delete(
            "/api/market-board/custom-stocks/ZZZZZZ",
            params={"market": "KR"},
        )
        assert resp.status_code == 404


class TestMarketBoardOrder:
    """시세판 종목 순서 관리."""

    def test_get_board_order(self, client):
        """A-095: GET /api/market-board/order → 200."""
        resp = client.get("/api/market-board/order")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_save_board_order(self, client):
        """A-096: PUT /api/market-board/order → 200."""
        resp = client.put("/api/market-board/order", json={
            "items": [
                {"code": "005930", "market": "KR"},
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True
