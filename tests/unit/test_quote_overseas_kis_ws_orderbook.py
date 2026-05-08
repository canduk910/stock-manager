"""REQ-WS-01: KIS 해외 호가 WS(HDFSASP0) 채널 통합 단위 테스트.

검증 시나리오:
- WS 연결 성공 → subscribe 시 토픽 등록 + REST 호가 폴링 미시작
- WS 메시지 수신 시 orderbook broadcast 형식 보존
- WS 끊김 감지 → 모든 구독 종목 REST 폴링 자동 시작
- WS 재연결 + 토픽 재등록 → REST 폴링 자동 중단(WS 우선 복귀)
- KIS WS 키 부재(503/예외) → REST 폴링 즉시 fallback (graceful)
- broadcast shape 보존: {type, symbol, asks, bids, total_ask_volume, total_bid_volume}
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch, AsyncMock

import pytest


# ── Fake WS 클라이언트 ────────────────────────────────────────────────────────


def _bind_fake_ws(fake_ws):
    """patch side_effect 헬퍼: 클래스 생성자 호출 시 콜백을 fake_ws에 set 후 반환."""
    def _factory(*args, **kwargs):
        fake_ws.on_orderbook = kwargs.get("on_orderbook")
        fake_ws.on_disconnect = kwargs.get("on_disconnect")
        fake_ws.on_reconnect = kwargs.get("on_reconnect")
        return fake_ws
    return _factory


class FakeKisOverseasWS:
    """KISOverseasOrderbookWS 테스트 더블.

    실제 KIS WS와 동일한 인터페이스를 흉내낸다.
        - start() / stop()
        - is_connected (property)
        - subscribe(rsym) / unsubscribe(rsym)
        - on_message(payload) — 외부에서 임의 메시지 주입 (테스트용)
    """

    def __init__(self, on_orderbook=None, on_disconnect=None, on_reconnect=None):
        self.on_orderbook = on_orderbook
        self.on_disconnect = on_disconnect
        self.on_reconnect = on_reconnect
        self.connected = False
        self.subscriptions: set[str] = set()
        self.start_called = 0
        self.stop_called = 0

    async def start(self):
        self.start_called += 1
        self.connected = True

    async def stop(self):
        self.stop_called += 1
        self.connected = False

    @property
    def is_connected(self):
        return self.connected

    async def subscribe(self, rsym: str):
        self.subscriptions.add(rsym)

    async def unsubscribe(self, rsym: str):
        self.subscriptions.discard(rsym)

    async def trigger_disconnect(self):
        """테스트용: 연결 끊김 시뮬레이션."""
        self.connected = False
        if self.on_disconnect:
            await self.on_disconnect()

    async def trigger_reconnect(self):
        """테스트용: 재연결 시뮬레이션."""
        self.connected = True
        if self.on_reconnect:
            await self.on_reconnect()

    async def deliver(self, payload: dict):
        """테스트용: 메시지 도달 시뮬레이션."""
        if self.on_orderbook:
            await self.on_orderbook(payload)


# ── 테스트 ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_connected_subscribe_does_not_start_rest_orderbook_poller():
    """WS 연결 정상 시 종목 구독 → 토픽 등록 + REST 호가 폴링 미시작.

    가격 폴러는 (Finnhub 미사용 모드라) 시작될 수 있으나 호가 폴러는 WS 우선이라 미시작.
    """
    from services.quote_overseas import OverseasQuoteManager

    fake_ws = FakeKisOverseasWS()

    mgr = OverseasQuoteManager()
    with patch("services.quote_overseas.FINNHUB_API_KEY", None), \
         patch("services.quote_overseas.KISOverseasOrderbookWS", side_effect=_bind_fake_ws(fake_ws)), \
         patch("stock.kis_overseas_client._resolve_exchange", return_value="NAS"):
        await mgr.start()

        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        with patch("services.quote_overseas.get_kis_orderbook", return_value=None), \
             patch("services.quote_overseas._fetch_quote_message", return_value=None):
            await mgr.subscribe("AAPL", queue)
            await asyncio.sleep(0.05)

            # WS 토픽 등록됨
            assert any(s.endswith("AAPL") for s in fake_ws.subscriptions), \
                f"WS subscribe 미호출: {fake_ws.subscriptions}"
            # REST 호가 폴러는 시작되지 않음 (WS 우선)
            assert "AAPL" not in mgr._orderbook_pollers, \
                "WS 연결 정상인데 REST 호가 폴러가 시작됨"

            mgr.unsubscribe("AAPL", queue)
    await mgr.stop()


@pytest.mark.asyncio
async def test_ws_message_broadcasts_orderbook_with_correct_shape():
    """WS 메시지 도달 → broadcast shape 보존."""
    from services.quote_overseas import OverseasQuoteManager

    fake_ws = FakeKisOverseasWS()

    mgr = OverseasQuoteManager()
    with patch("services.quote_overseas.FINNHUB_API_KEY", None), \
         patch("services.quote_overseas.KISOverseasOrderbookWS", side_effect=_bind_fake_ws(fake_ws)), \
         patch("stock.kis_overseas_client._resolve_exchange", return_value="NAS"):
        await mgr.start()

        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        with patch("services.quote_overseas.get_kis_orderbook", return_value=None), \
             patch("services.quote_overseas._fetch_quote_message", return_value=None):
            await mgr.subscribe("AAPL", queue)
            await asyncio.sleep(0.05)

            # WS 메시지 도달 시뮬레이션 — wrapper.parse_overseas_orderbook 결과 형식
            await fake_ws.deliver({
                "symbol": "AAPL",
                "exchange": "NAS",
                "asks": [{"price": 200.10, "volume": 100}],
                "bids": [{"price": 199.90, "volume": 120}],
                "total_ask_volume": 5500,
                "total_bid_volume": 6700,
            })

            msg = None
            for _ in range(40):
                try:
                    m = await asyncio.wait_for(queue.get(), timeout=0.1)
                    if m.get("type") == "orderbook":
                        msg = m
                        break
                except asyncio.TimeoutError:
                    continue

            assert msg is not None, "WS broadcast 미발생"
            assert msg["type"] == "orderbook"
            assert msg["symbol"] == "AAPL"
            assert msg["asks"][0]["price"] == pytest.approx(200.10)
            assert msg["bids"][0]["price"] == pytest.approx(199.90)
            assert msg["total_ask_volume"] == 5500
            assert msg["total_bid_volume"] == 6700

            mgr.unsubscribe("AAPL", queue)
    await mgr.stop()


@pytest.mark.asyncio
async def test_ws_disconnect_starts_rest_orderbook_polling_for_all_subs():
    """WS 끊김 → 모든 구독 종목에 대해 REST 호가 폴링 자동 시작."""
    from services.quote_overseas import OverseasQuoteManager

    fake_ws = FakeKisOverseasWS()

    mgr = OverseasQuoteManager()
    with patch("services.quote_overseas.FINNHUB_API_KEY", None), \
         patch("services.quote_overseas.KISOverseasOrderbookWS", side_effect=_bind_fake_ws(fake_ws)), \
         patch("stock.kis_overseas_client._resolve_exchange", return_value="NAS"):
        await mgr.start()

        q1: asyncio.Queue = asyncio.Queue(maxsize=10)
        q2: asyncio.Queue = asyncio.Queue(maxsize=10)
        with patch("services.quote_overseas.get_kis_orderbook", return_value=None), \
             patch("services.quote_overseas._fetch_quote_message", return_value=None):
            await mgr.subscribe("AAPL", q1)
            await mgr.subscribe("MSFT", q2)
            await asyncio.sleep(0.05)

            assert "AAPL" not in mgr._orderbook_pollers
            assert "MSFT" not in mgr._orderbook_pollers

            # WS 끊김 시뮬레이션
            await fake_ws.trigger_disconnect()
            # 폴러 자동 시작 시간 확보
            await asyncio.sleep(0.1)

            assert "AAPL" in mgr._orderbook_pollers, "WS 끊김 후 AAPL REST 폴러 미시작"
            assert "MSFT" in mgr._orderbook_pollers, "WS 끊김 후 MSFT REST 폴러 미시작"

            mgr.unsubscribe("AAPL", q1)
            mgr.unsubscribe("MSFT", q2)
    await mgr.stop()


@pytest.mark.asyncio
async def test_ws_reconnect_stops_rest_orderbook_polling():
    """WS 재연결 + 토픽 재등록 → REST 호가 폴러 자동 중단(WS 우선 복귀)."""
    from services.quote_overseas import OverseasQuoteManager

    fake_ws = FakeKisOverseasWS()

    mgr = OverseasQuoteManager()
    with patch("services.quote_overseas.FINNHUB_API_KEY", None), \
         patch("services.quote_overseas.KISOverseasOrderbookWS", side_effect=_bind_fake_ws(fake_ws)), \
         patch("stock.kis_overseas_client._resolve_exchange", return_value="NAS"):
        await mgr.start()

        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        with patch("services.quote_overseas.get_kis_orderbook", return_value=None), \
             patch("services.quote_overseas._fetch_quote_message", return_value=None):
            await mgr.subscribe("AAPL", queue)
            await asyncio.sleep(0.05)

            # 끊김 → REST 폴링 시작
            await fake_ws.trigger_disconnect()
            await asyncio.sleep(0.1)
            assert "AAPL" in mgr._orderbook_pollers

            # 재연결 → REST 폴링 자동 중단
            await fake_ws.trigger_reconnect()
            await asyncio.sleep(0.15)
            assert "AAPL" not in mgr._orderbook_pollers, \
                "WS 재연결 후 REST 폴러가 cancel되지 않음"
            # 재연결 토픽도 재등록 되어야 함
            assert any(s.endswith("AAPL") for s in fake_ws.subscriptions)

            mgr.unsubscribe("AAPL", queue)
    await mgr.stop()


@pytest.mark.asyncio
async def test_ws_construction_failure_falls_back_to_rest_polling():
    """KISOverseasOrderbookWS 생성 실패(KIS 키 부재 등) → REST 폴링 fallback."""
    from services.quote_overseas import OverseasQuoteManager

    def _raise(*a, **k):
        raise RuntimeError("KIS key missing")

    mgr = OverseasQuoteManager()
    with patch("services.quote_overseas.FINNHUB_API_KEY", None), \
         patch("services.quote_overseas.KISOverseasOrderbookWS", side_effect=_raise):
        await mgr.start()

        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        with patch("services.quote_overseas.get_kis_orderbook", return_value=None), \
             patch("services.quote_overseas._fetch_quote_message", return_value=None):
            await mgr.subscribe("AAPL", queue)
            await asyncio.sleep(0.1)

            # WS 사용 불가 → REST 호가 폴러는 즉시 시작되어야 함
            assert "AAPL" in mgr._orderbook_pollers, \
                "WS 사용 불가 시 REST 호가 폴러 fallback 미동작"

            mgr.unsubscribe("AAPL", queue)
    await mgr.stop()


@pytest.mark.asyncio
async def test_ws_start_failure_falls_back_to_rest_polling():
    """WS start() 예외 발생 → REST 폴링 즉시 fallback."""
    from services.quote_overseas import OverseasQuoteManager

    fake_ws = FakeKisOverseasWS()
    fake_ws.start = AsyncMock(side_effect=RuntimeError("connect refused"))

    mgr = OverseasQuoteManager()
    with patch("services.quote_overseas.FINNHUB_API_KEY", None), \
         patch("services.quote_overseas.KISOverseasOrderbookWS", side_effect=_bind_fake_ws(fake_ws)), \
         patch("stock.kis_overseas_client._resolve_exchange", return_value="NAS"):
        await mgr.start()

        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        with patch("services.quote_overseas.get_kis_orderbook", return_value=None), \
             patch("services.quote_overseas._fetch_quote_message", return_value=None):
            await mgr.subscribe("AAPL", queue)
            await asyncio.sleep(0.1)

            # WS start 실패 → REST 폴러 fallback
            assert "AAPL" in mgr._orderbook_pollers, \
                "WS start 실패 시 REST 폴러 fallback 미동작"

            mgr.unsubscribe("AAPL", queue)
    await mgr.stop()
