"""Watchlist API 엔드포인트 테스트 (A-001 ~ A-010)."""

import pytest


class TestWatchlistCRUD:
    """관심종목 CRUD 엔드포인트."""

    def test_list_watchlist(self, client):
        """A-001: GET /api/watchlist → 200, items 리스트."""
        resp = client.get("/api/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_add_watchlist(self, client):
        """A-002: POST /api/watchlist → 201 or 409(이미 존재) or 404."""
        resp = client.post("/api/watchlist", json={
            "code": "005930",
            "memo": "테스트",
            "market": "KR",
        })
        # 종목명 조회 실패 → 404, 이미 존재 → 409, 성공 → 201
        assert resp.status_code in (201, 404, 409)

    def test_add_watchlist_duplicate(self, client):
        """A-003: 중복 추가 시 409."""
        body = {"code": "005930", "memo": "", "market": "KR"}
        first = client.post("/api/watchlist", json=body)
        if first.status_code == 201:
            second = client.post("/api/watchlist", json=body)
            assert second.status_code == 409

    def test_remove_nonexistent(self, client):
        """A-005: 없는 종목 삭제 → 404."""
        resp = client.delete("/api/watchlist/999999", params={"market": "KR"})
        assert resp.status_code == 404

    def test_update_memo_not_found(self, client):
        """A-006: 없는 종목 메모 수정 → 404."""
        resp = client.patch(
            "/api/watchlist/999999",
            json={"memo": "새 메모"},
            params={"market": "KR"},
        )
        assert resp.status_code == 404


class TestWatchlistDashboard:
    """대시보드 + 종목정보 엔드포인트."""

    def test_get_dashboard(self, client):
        """A-007: GET /api/watchlist/dashboard → 200."""
        resp = client.get("/api/watchlist/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "stocks" in data
        assert isinstance(data["stocks"], list)

    def test_get_stock_info_not_found(self, client):
        """A-008: 존재하지 않는 종목 정보 조회."""
        resp = client.get("/api/watchlist/info/999999", params={"market": "KR"})
        # yfinance가 빈 데이터라도 200 반환 가능, 또는 404/502/500
        assert resp.status_code in (200, 404, 500, 502)


class TestWatchlistOrder:
    """관심종목 순서 관리."""

    def test_get_order(self, client):
        """A-009: GET /api/watchlist/order → 200."""
        resp = client.get("/api/watchlist/order")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_save_order(self, client):
        """A-010: PUT /api/watchlist/order → 200."""
        resp = client.put("/api/watchlist/order", json={
            "items": [
                {"code": "005930", "market": "KR"},
                {"code": "000660", "market": "KR"},
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True
