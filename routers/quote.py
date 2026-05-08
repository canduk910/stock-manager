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
async def quote_ws(websocket: WebSocket, symbol: str, market: str = "", exchange: str = "auto"):
    """실시간 호가/체결 WebSocket.

    Query params:
        token: JWT (인증)
        market: "" / "FNO" — 시장 분기
        exchange: KR 거래소 — "auto"(기본, 시계 기반 4구간) / "UN" / "KRX" / "NXT"
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        from services.auth_service import verify_token
        verify_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    symbol = symbol.upper()
    exchange = (exchange or "auto").upper() if exchange.lower() != "auto" else "auto"
    try:
        if market == "FNO" or (not market and is_fno(symbol)):
            await _stream_fno(websocket, symbol)
        elif is_domestic(symbol):
            await _stream_domestic(websocket, symbol, exchange)
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


async def _stream_domestic(websocket: WebSocket, symbol: str, exchange: str = "auto"):
    """KIS WebSocket → FastAPI WebSocket 브릿지 (국내주식).

    100ms 창 내 메시지를 병합하여 최신 price/orderbook만 전송.
    exchange: 'auto'(기본) / 'UN' / 'KRX' / 'NXT' — KISQuoteManager가 시계 기반 분기.
    """
    manager = get_manager()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    await manager.subscribe(symbol, queue, exchange=exchange)
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


@router.websocket("/ws/execution-notice")
async def execution_notice_ws(websocket: WebSocket):
    """체결통보(H0STCNI0) 실시간 수신 WebSocket."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        from services.auth_service import verify_token
        verify_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    manager = get_manager()
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    await manager.subscribe_notice(queue)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("[ExecutionNoticeWS] %s", e)
    finally:
        manager.unsubscribe_notice(queue)


@router.websocket("/ws/market-status")
async def market_status_ws(websocket: WebSocket):
    """장운영정보(H0UNMKO0+H0STMKO0+H0NXMKO0) 통합 멀티플렉스 WebSocket.

    클라이언트(useMarketClock 등)는 KST 시계 기반 4구간 자동 분기를 1차로 쓰되,
    이 WS 메시지가 도착하면 정밀 trigger(휴장/장개시/장종료)로 override 한다.

    응답 메시지 포맷: `{type: "market_status", exchange: "UN"|"KRX"|"NXT", tr_id, raw}`.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        from services.auth_service import verify_token
        verify_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    manager = get_manager()
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    await manager.subscribe_market_status(queue)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("[MarketStatusWS] %s", e)
    finally:
        manager.unsubscribe_market_status(queue)
