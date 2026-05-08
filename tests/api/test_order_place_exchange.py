"""R_4 (KRX+NXT 통합시세): POST /api/order/place exchange 필드 API 테스트."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """주문 라우터 + 인증 dependency override."""
    from fastapi import FastAPI
    from routers.order import router as order_router
    from services.auth_deps import require_admin

    app = FastAPI()

    # main.py의 ServiceError → HTTP 핸들러 모방
    from services.exceptions import ServiceError
    @app.exception_handler(ServiceError)
    async def service_error_handler(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=getattr(exc, "status_code", 400), content={"detail": str(exc)})

    app.include_router(order_router)
    # require_admin 의존성을 더미로 교체
    app.dependency_overrides[require_admin] = lambda: {"id": 1, "role": "admin"}
    return app


def test_place_body_accepts_exchange_sor(app):
    """exchange='SOR' 입력 → service.place_order 에 forward."""
    captured = {}

    def fake_place(**kwargs):
        captured.update(kwargs)
        return {"id": 1, "status": "PLACED", "exchange": "SOR-KRX", "order_no": "X1"}

    with patch("services.order_service.place_order", side_effect=fake_place):
        client = TestClient(app)
        res = client.post("/api/order/place", json={
            "symbol": "005930", "symbol_name": "삼성전자",
            "market": "KR", "side": "buy",
            "order_type": "00", "price": 70000, "quantity": 1,
            "exchange": "SOR",
        })
    assert res.status_code == 201
    assert captured["exchange"] == "SOR"


def test_place_body_default_exchange_is_sor(app):
    """exchange 미지정 시 기본 'SOR' 적용."""
    captured = {}

    def fake_place(**kwargs):
        captured.update(kwargs)
        return {"id": 1, "status": "PLACED"}

    with patch("services.order_service.place_order", side_effect=fake_place):
        client = TestClient(app)
        res = client.post("/api/order/place", json={
            "symbol": "005930", "market": "KR", "side": "buy",
            "order_type": "00", "price": 70000, "quantity": 1,
        })
    assert res.status_code == 201
    assert captured["exchange"] == "SOR"


def test_place_body_rejects_invalid_exchange(app):
    """Literal 검증으로 'UN'(시세 전용) 입력 시 422."""
    client = TestClient(app)
    res = client.post("/api/order/place", json={
        "symbol": "005930", "market": "KR", "side": "buy",
        "order_type": "00", "price": 70000, "quantity": 1,
        "exchange": "UN",
    })
    assert res.status_code == 422


def test_place_body_accepts_nxt(app):
    """exchange='NXT' 정상 forward."""
    captured = {}

    def fake_place(**kwargs):
        captured.update(kwargs)
        return {"id": 1, "status": "PLACED"}

    with patch("services.order_service.place_order", side_effect=fake_place):
        client = TestClient(app)
        res = client.post("/api/order/place", json={
            "symbol": "005930", "market": "KR", "side": "buy",
            "order_type": "00", "price": 70000, "quantity": 1,
            "exchange": "NXT",
        })
    assert res.status_code == 201
    assert captured["exchange"] == "NXT"
