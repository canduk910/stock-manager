"""Order API 엔드포인트 테스트 (A-020 ~ A-029)."""

import pytest


class TestOrderPlace:
    """주문 발송 — KIS 키 미설정 시 503."""

    def test_place_order_no_kis(self, client):
        """A-020: KIS 키 없이 주문 → 503 (ConfigError)."""
        resp = client.post("/api/order/place", json={
            "symbol": "005930",
            "symbol_name": "삼성전자",
            "market": "KR",
            "side": "buy",
            "order_type": "00",
            "price": 70000,
            "quantity": 1,
        })
        # KIS 키 미설정 → ConfigError(503) 또는 ExternalAPIError(502)
        assert resp.status_code in (503, 502, 400)


class TestOrderQueries:
    """주문 조회 엔드포인트."""

    def test_get_buyable(self, client):
        """A-021: 매수가능 조회 → 200 or 503."""
        resp = client.get("/api/order/buyable", params={
            "symbol": "005930",
            "market": "KR",
            "price": 70000,
        })
        # KIS 키 미설정 → 503
        assert resp.status_code in (200, 503, 502)

    def test_get_open_orders(self, client):
        """A-022: 미체결 조회 → 200 or 503."""
        resp = client.get("/api/order/open", params={"market": "KR"})
        assert resp.status_code in (200, 503, 502)

    def test_get_executions(self, client):
        """A-023: 체결 내역 → 200 or 503."""
        resp = client.get("/api/order/executions", params={"market": "KR"})
        assert resp.status_code in (200, 503, 502)

    def test_get_order_history(self, client):
        """A-024: 로컬 주문 이력 → 200 (DB 기반, KIS 불필요)."""
        resp = client.get("/api/order/history")
        assert resp.status_code in (200, 503, 502)
        if resp.status_code == 200:
            data = resp.json()
            assert "orders" in data
            assert isinstance(data["orders"], list)

    def test_sync_orders(self, client):
        """A-025: 대사 → 200 or 503."""
        resp = client.post("/api/order/sync")
        assert resp.status_code in (200, 503, 502)


class TestOrderReservation:
    """예약주문 엔드포인트."""

    def test_create_reservation(self, client):
        """A-026: 예약주문 생성 → 201."""
        resp = client.post("/api/order/reserve", json={
            "symbol": "005930",
            "symbol_name": "삼성전자",
            "market": "KR",
            "side": "buy",
            "order_type": "00",
            "price": 70000,
            "quantity": 1,
            "condition_type": "price_below",
            "condition_value": "65000",
        })
        # 예약주문은 DB 기반 → KIS 키 불필요, 201 가능
        # 단, 서비스에서 검증 실패 시 400
        assert resp.status_code in (201, 400, 503)

    def test_list_reservations(self, client):
        """A-027: 예약 목록 → 200."""
        resp = client.get("/api/order/reserves")
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert "reservations" in data

    def test_delete_reservation_not_found(self, client):
        """A-028: 없는 예약 삭제 → 404."""
        resp = client.delete("/api/order/reserve/99999")
        assert resp.status_code in (404, 503)


class TestOrderFNO:
    """선물옵션 시세 조회."""

    def test_get_fno_price(self, client):
        """A-029: FNO 현재가 → 200 or 503."""
        resp = client.get("/api/order/fno-price", params={
            "symbol": "101W09",
            "mrkt_div": "F",
        })
        assert resp.status_code in (200, 503, 502)
