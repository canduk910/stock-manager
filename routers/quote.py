"""
실시간 호가 WebSocket 엔드포인트.
국내(KR): KIS WS 브릿지 (100ms 메시지 병합), 해외(US): OverseasQuoteManager pub/sub.
"""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.quote_service import get_manager, get_overseas_manager
from stock.utils import is_domestic, is_fno

router = APIRouter(tags=["quote"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/quote/{symbol}")
async def quote_ws(websocket: WebSocket, symbol: str, market: str = ""):
    await websocket.accept()
    symbol = symbol.upper()
    try:
        if market == "FNO" or (not market and is_fno(symbol)):
            await _stream_fno(websocket, symbol)
        elif is_domestic(symbol):
            await _stream_domestic(websocket, symbol)
        else:
            await _stream_overseas(websocket, symbol)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("[QuoteWS] %s: %s", symbol, e)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


async def _stream_domestic(websocket: WebSocket, symbol: str):
    """KIS WebSocket → FastAPI WebSocket 브릿지 (국내주식).

    100ms 창 내 메시지를 병합하여 최신 price/orderbook만 전송.
    """
    manager = get_manager()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    await manager.subscribe(symbol, queue)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # 연결 유지용 ping
                await websocket.send_json({"type": "ping"})
                continue

            # 100ms 창 내 추가 메시지 수집 → 같은 type은 최신만 유지
            latest = {msg["type"]: msg}
            deadline = asyncio.get_event_loop().time() + 0.1
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    extra = await asyncio.wait_for(queue.get(), timeout=remaining)
                    latest[extra["type"]] = extra
                except asyncio.TimeoutError:
                    break

            # 병합된 최신 메시지만 전송
            for m in latest.values():
                await websocket.send_json(m)
    finally:
        manager.unsubscribe(symbol, queue)


async def _stream_fno(websocket: WebSocket, symbol: str):
    """KIS WebSocket → FastAPI WebSocket 브릿지 (선물옵션). 100ms 메시지 병합."""
    manager = get_manager()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    await manager.subscribe(symbol, queue, is_fno=True)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue

            latest = {msg["type"]: msg}
            deadline = asyncio.get_event_loop().time() + 0.1
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    extra = await asyncio.wait_for(queue.get(), timeout=remaining)
                    latest[extra["type"]] = extra
                except asyncio.TimeoutError:
                    break

            for m in latest.values():
                await websocket.send_json(m)
    finally:
        manager.unsubscribe(symbol, queue)


async def _stream_overseas(websocket: WebSocket, symbol: str):
    """OverseasQuoteManager pub/sub → FastAPI WebSocket (해외주식)."""
    manager = get_overseas_manager()
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    await manager.subscribe(symbol, queue)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    finally:
        manager.unsubscribe(symbol, queue)
