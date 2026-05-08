"""R_5 (KRX+NXT 통합시세): /ws/quote/{symbol} exchange 쿼리 + /ws/market-status WS API 테스트.

KIS WS 실연결은 모킹하지 않고, KISQuoteManager 의 subscribe/subscribe_market_status 만 mock.
verify_token 도 mock 으로 통과시켜 인증 분기 검증과 본문 흐름 검증을 분리.
"""
import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """라우터만 마운트한 최소 FastAPI 앱."""
    from fastapi import FastAPI
    from routers.quote import router as quote_router

    app = FastAPI()
    app.include_router(quote_router)
    return app


def test_quote_ws_rejects_missing_token(app):
    """token 없으면 1008 close."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/quote/005930"):
            pass


def test_market_status_ws_rejects_missing_token(app):
    """/ws/market-status: token 없으면 1008 close."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/market-status"):
            pass


def test_quote_ws_subscribe_exchange_nxt(app):
    """exchange=NXT 쿼리가 manager.subscribe 에 forward 된다."""
    captured = {}

    class FakeManager:
        async def subscribe(self, symbol, queue, *, is_fno=False, exchange="auto"):
            captured["symbol"] = symbol
            captured["exchange"] = exchange
            captured["is_fno"] = is_fno

        def unsubscribe(self, *a, **kw):
            pass

    with patch("routers.quote.get_manager", return_value=FakeManager()), \
         patch("services.auth_service.verify_token", return_value={"sub": "1"}):
        client = TestClient(app)
        try:
            with client.websocket_connect("/ws/quote/005930?token=abc&exchange=NXT") as ws:
                # subscribe 가 호출됐는지만 확인하고 즉시 종료
                ws.close()
        except Exception:
            pass

    assert captured.get("symbol") == "005930"
    assert captured.get("exchange") == "NXT"


def test_quote_ws_subscribe_default_exchange_is_auto(app):
    """exchange 쿼리 미지정 시 'auto' 가 manager 에 forward."""
    captured = {}

    class FakeManager:
        async def subscribe(self, symbol, queue, *, is_fno=False, exchange="auto"):
            captured["exchange"] = exchange

        def unsubscribe(self, *a, **kw):
            pass

    with patch("routers.quote.get_manager", return_value=FakeManager()), \
         patch("services.auth_service.verify_token", return_value={"sub": "1"}):
        client = TestClient(app)
        try:
            with client.websocket_connect("/ws/quote/005930?token=abc") as ws:
                ws.close()
        except Exception:
            pass

    assert captured.get("exchange") == "auto"


def test_market_status_ws_subscribes_market_status(app):
    """/ws/market-status 가 manager.subscribe_market_status 를 호출한다."""
    called = {"sub": False, "unsub": False}

    class FakeManager:
        async def subscribe_market_status(self, queue):
            called["sub"] = True

        def unsubscribe_market_status(self, queue):
            called["unsub"] = True

    with patch("routers.quote.get_manager", return_value=FakeManager()), \
         patch("services.auth_service.verify_token", return_value={"sub": "1"}):
        client = TestClient(app)
        try:
            with client.websocket_connect("/ws/market-status?token=abc") as ws:
                ws.close()
        except Exception:
            pass

    assert called["sub"] is True
    # close 후 finally 블록에서 unsubscribe
    assert called["unsub"] is True
