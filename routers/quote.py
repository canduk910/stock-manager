"""
실시간 호가 WebSocket 엔드포인트.
국내(KR): KIS WS 브릿지, 해외(US): yfinance 2초 polling.
"""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.quote_service import get_manager
from stock.utils import is_domestic

router = APIRouter(tags=["quote"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/quote/{symbol}")
async def quote_ws(websocket: WebSocket, symbol: str):
    await websocket.accept()
    symbol = symbol.upper()
    try:
        if is_domestic(symbol):
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
    """KIS WebSocket → FastAPI WebSocket 브릿지 (국내주식)."""
    manager = get_manager()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    await manager.subscribe(symbol, queue)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                # 연결 유지용 ping
                await websocket.send_json({"type": "ping"})
    finally:
        manager.unsubscribe(symbol, queue)


async def _stream_overseas(websocket: WebSocket, symbol: str):
    """yfinance 2초 polling → FastAPI WebSocket (해외주식)."""
    import yfinance as yf

    while True:
        try:
            fi = yf.Ticker(symbol).fast_info
            price = fi.last_price
            prev = fi.previous_close
            change = (price - prev) if (price and prev) else 0.0
            rate = (change / prev * 100) if prev else 0.0
            await websocket.send_json({
                "type": "price",
                "symbol": symbol,
                "price": round(float(price), 2) if price else None,
                "change": round(float(change), 2),
                "change_rate": round(float(rate), 2),
                "sign": "2" if change >= 0 else "5",
                "asks": [],
                "bids": [],
            })
        except WebSocketDisconnect:
            raise
        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})
        await asyncio.sleep(2)
