"""REQ-WS-05: services/quote_overseas.py KIS 호가 채널 통합 단위 테스트.

- subscribe → KIS REST 호가 폴러 시작 → orderbook 메시지 broadcast
- unsubscribe (구독자 0) → 호가 폴러 cancel
- KIS get_kis_orderbook None 반환 → 메시지 발행 안함, 폴러 유지
- 메시지 type="orderbook" + asks/bids/total_ask_volume/total_bid_volume 필드 포함
- 가격(체결가) 채널과 별도로 동작 (price 채널 미영향)
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.asyncio
async def test_subscribe_starts_orderbook_poller_and_broadcasts():
    """subscribe → KIS get_kis_orderbook 호출 → orderbook 메시지 큐에 도착."""
    from services.quote_overseas import OverseasQuoteManager

    mgr = OverseasQuoteManager()
    # FINNHUB 미사용 모드로 강제 (quote_overseas 모듈 상수)
    with patch("services.quote_overseas.FINNHUB_API_KEY", None):
        await mgr.start()

    ob = {
        "asks": [{"price": 200.10, "volume": 100}, {"price": 200.20, "volume": 200}],
        "bids": [{"price": 199.90, "volume": 120}, {"price": 199.80, "volume": 220}],
        "total_ask_volume": 5500,
        "total_bid_volume": 6700,
        "exchange": "NAS",
    }

    queue: asyncio.Queue = asyncio.Queue(maxsize=10)

    with patch("services.quote_overseas.get_kis_orderbook", return_value=ob), \
         patch("services.quote_overseas._fetch_quote_message", return_value=None):
        await mgr.subscribe("AAPL", queue)
        # 호가 폴러가 첫 fetch + broadcast 할 시간 확보
        msg = None
        for _ in range(40):  # 최대 4초 대기
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=0.1)
                if msg.get("type") == "orderbook":
                    break
            except asyncio.TimeoutError:
                continue

        assert msg is not None
        assert msg["type"] == "orderbook"
        assert msg["symbol"] == "AAPL"
        assert msg["asks"][0]["price"] == pytest.approx(200.10)
        assert msg["bids"][0]["price"] == pytest.approx(199.90)
        assert msg["total_ask_volume"] == 5500
        assert msg["total_bid_volume"] == 6700

        mgr.unsubscribe("AAPL", queue)
    await mgr.stop()


@pytest.mark.asyncio
async def test_unsubscribe_stops_orderbook_poller():
    """모든 구독자 제거 → orderbook 폴러도 cancel."""
    from services.quote_overseas import OverseasQuoteManager

    mgr = OverseasQuoteManager()
    with patch("services.quote_overseas.FINNHUB_API_KEY", None):
        await mgr.start()

    queue: asyncio.Queue = asyncio.Queue(maxsize=10)

    with patch("services.quote_overseas.get_kis_orderbook", return_value=None), \
         patch("services.quote_overseas._fetch_quote_message", return_value=None):
        await mgr.subscribe("AAPL", queue)
        await asyncio.sleep(0.05)

        # 폴러 동작 확인
        assert "AAPL" in mgr._orderbook_pollers
        ob_task = mgr._orderbook_pollers["AAPL"]
        assert not ob_task.done()

        # 구독자 0 해제
        mgr.unsubscribe("AAPL", queue)
        # 비동기 cancel 처리될 시간 확보
        await asyncio.sleep(0.1)

        # 폴러는 dict에서 제거
        assert "AAPL" not in mgr._orderbook_pollers

    await mgr.stop()


@pytest.mark.asyncio
async def test_orderbook_none_does_not_broadcast():
    """KIS 호가 None → orderbook 메시지는 broadcast 안 함, 폴러는 유지."""
    from services.quote_overseas import OverseasQuoteManager

    mgr = OverseasQuoteManager()
    with patch("services.quote_overseas.FINNHUB_API_KEY", None):
        await mgr.start()

    queue: asyncio.Queue = asyncio.Queue(maxsize=10)

    with patch("services.quote_overseas.get_kis_orderbook", return_value=None), \
         patch("services.quote_overseas._fetch_quote_message", return_value=None):
        await mgr.subscribe("AAPL", queue)
        await asyncio.sleep(0.3)

        # orderbook 메시지가 큐에 없어야 함
        ob_msgs = []
        while not queue.empty():
            try:
                m = queue.get_nowait()
                if m.get("type") == "orderbook":
                    ob_msgs.append(m)
            except asyncio.QueueEmpty:
                break
        assert len(ob_msgs) == 0
        # 폴러는 살아있어야 함
        assert "AAPL" in mgr._orderbook_pollers

        mgr.unsubscribe("AAPL", queue)
    await mgr.stop()
