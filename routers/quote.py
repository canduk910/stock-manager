"""
실시간 호가 WebSocket 엔드포인트.
국내(KR): KIS WS 브릿지 (100ms 메시지 병합), 해외(US): OverseasQuoteManager pub/sub.

REQ-ROUTER-06: 미국 10단계 호가 + 현재가 상세 REST 엔드포인트 추가
(WS 차단/초기 로딩용 폴백).
"""
import asyncio
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from services.auth_deps import get_current_user
from services.quote_service import get_manager, get_overseas_manager
from stock.kis_overseas_client import get_kis_orderbook, get_kis_price_detail
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


@router.get("/api/quote/us/{symbol}/orderbook")
def get_us_orderbook(symbol: str, user: dict = Depends(get_current_user)):
    """미국 주식 10단계 호가 REST 폴백 엔드포인트 (REQ-ROUTER-06).

    WS 차단/초기 로딩용. 평시에는 ``/ws/quote/{symbol}`` 가 orderbook 메시지를
    push하므로 사용 빈도 낮음.

    Returns:
        200: ``{asks, bids, total_ask_volume, total_bid_volume, exchange}``
        503: KIS 키 부재(ConfigError)
        504: KIS 응답 없음/타임아웃
    """
    user_id = user.get("id") if isinstance(user, dict) else None
    ob = get_kis_orderbook(symbol.upper(), user_id=user_id)
    if ob is None:
        return JSONResponse(
            status_code=504,
            content={"detail": "KIS 해외 호가 응답 없음/타임아웃"},
        )
    return ob


@router.get("/api/quote/us/{symbol}/detail")
def get_us_price_detail(symbol: str, user: dict = Depends(get_current_user)):
    """미국 주식 현재가 상세 REST 엔드포인트 (REQ-ROUTER-06).

    Returns:
        200: ``{open, high, low, last, prev_close, volume, high_52w, low_52w,
                currency: "USD", exchange}``
        503: KIS 키 부재
        504: KIS 응답 없음
    """
    user_id = user.get("id") if isinstance(user, dict) else None
    d = get_kis_price_detail(symbol.upper(), user_id=user_id)
    if d is None:
        return JSONResponse(
            status_code=504,
            content={"detail": "KIS 해외 현재가 상세 응답 없음/타임아웃"},
        )
    return d


@router.websocket("/ws/execution-notice")
async def execution_notice_ws(websocket: WebSocket):
    """체결통보(H0STCNI0) 실시간 수신 WebSocket.

    R6 (KIS 멀티 계좌): 메시지 payload 에 account_label 부착.
    토큰 사용자 컨텍스트 + acnt_no_8 평문으로 services.account_label_matcher 호출.
    매칭 실패 시 label=None (다른 사용자 계좌 또는 신규 미등록).
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        from services.auth_service import verify_token
        payload = verify_token(token)
        user_id_for_label: int = int(payload["sub"])
    except Exception:
        await websocket.close(code=1008)
        return

    from services.account_label_matcher import match_account_label

    await websocket.accept()
    manager = get_manager()
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    await manager.subscribe_notice(queue)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                # 라벨 부착 (기존 필드 보존 + account_label 추가만)
                if isinstance(msg, dict) and msg.get("type") == "execution_notice":
                    acnt_8 = (msg.get("acnt_no_8") or "").strip()
                    if acnt_8 and msg.get("account_label") is None:
                        msg["account_label"] = match_account_label(user_id_for_label, acnt_8)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("[ExecutionNoticeWS] %s", e)
    finally:
        manager.unsubscribe_notice(queue)


# NOTE: /ws/market-status (장운영정보 멀티플렉스 H0UNMKO0/H0STMKO0/H0NXMKO0) 폐지 (2026-05-12).
#       KIS WS slot 잠식 회수를 위해 제거. useMarketClock은 시계 기반 폴백만 사용.
