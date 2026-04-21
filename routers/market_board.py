"""
시세판 API 라우터.
GET    /api/market-board/new-highs-lows         신고가/신저가 Top 10
POST   /api/market-board/sparklines             복수 종목 sparkline 배치
GET    /api/market-board/custom-stocks          별도 등록 종목 목록
POST   /api/market-board/custom-stocks          별도 등록 종목 추가
DELETE /api/market-board/custom-stocks/{code}   별도 등록 종목 삭제
WS     /ws/market-board                         다중심볼 실시간 시세
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from services.exceptions import NotFoundError, ConflictError

from services.quote_service import get_manager, get_overseas_manager
from stock.utils import is_domestic

router = APIRouter(tags=["market-board"])
logger = logging.getLogger(__name__)


# ── REST 엔드포인트 ────────────────────────────────────────────────────────────

@router.get("/api/market-board/new-highs-lows")
def get_new_highs_lows(top: int = 10):
    """당일 신고가/신저가 종목 조회 (시총 상위 기준)."""
    from stock.market_board import fetch_new_highs_lows
    return fetch_new_highs_lows(top_n=top)


class SparklineRequest(BaseModel):
    items: list[dict]  # [{"code": "005930", "market": "KR"}, ...]


@router.post("/api/market-board/sparklines")
def get_sparklines(body: SparklineRequest):
    """복수 종목 1년 주봉 종가 배치 조회."""
    from stock.market_board import fetch_sparklines_batch
    return fetch_sparklines_batch(body.items)


@router.post("/api/market-board/intraday-ohlc")
def get_intraday_ohlc(body: SparklineRequest):
    """복수 종목 당일 OHLC 배치 조회."""
    from stock.market_board import fetch_intraday_ohlc_batch
    return fetch_intraday_ohlc_batch(body.items)


# ── 시세판 별도 등록 종목 CRUD ──────────────────────────────────────────────────

class CustomStockBody(BaseModel):
    code: str
    name: str
    market: str = "KR"


class OrderItem(BaseModel):
    code: str
    market: str = "KR"


class SaveOrderBody(BaseModel):
    items: list[OrderItem]


@router.get("/api/market-board/custom-stocks")
def list_custom_stocks():
    """시세판 별도 등록 종목 목록."""
    from stock.market_board_store import all_items
    return {"items": all_items()}


@router.post("/api/market-board/custom-stocks", status_code=201)
def add_custom_stock(body: CustomStockBody):
    """시세판 별도 종목 추가."""
    from stock.market_board_store import add_item
    ok = add_item(body.code, body.name, body.market)
    if not ok:
        raise ConflictError("이미 등록된 종목입니다.")
    return {"item": {"code": body.code, "market": body.market, "name": body.name}}


@router.delete("/api/market-board/custom-stocks/{code}", status_code=204)
def remove_custom_stock(code: str, market: str = Query("KR")):
    """시세판 별도 종목 삭제."""
    from stock.market_board_store import remove_item
    ok = remove_item(code, market)
    if not ok:
        raise NotFoundError("등록되지 않은 종목입니다.")


# ── 종목 순서 ────────────────────────────────────────────────────────────────

@router.get("/api/market-board/order")
def get_board_order():
    """시세판 종목 표시 순서 조회."""
    from stock.market_board_store import get_order
    return {"items": get_order()}


@router.put("/api/market-board/order")
def save_board_order(body: SaveOrderBody):
    """시세판 종목 표시 순서 저장 (전체 교체)."""
    from stock.market_board_store import save_order
    save_order([item.model_dump() for item in body.items])
    return {"ok": True}


# ── 다중심볼 WebSocket ────────────────────────────────────────────────────────

@router.websocket("/ws/market-board")
async def market_board_ws(websocket: WebSocket):
    """다중심볼 실시간 시세 WebSocket.

    클라이언트 → 서버:
      {"action": "subscribe",   "symbols": ["005930", "000660", "AAPL"]}
      {"action": "unsubscribe", "symbols": ["000660"]}

    서버 → 클라이언트:
      {"type": "prices", "data": {"005930": {"price": 72000, "change_pct": 1.5, "sign": "2"}, ...}}
      {"type": "ping"}
    """
    await websocket.accept()

    domestic_mgr = get_manager()
    overseas_mgr = get_overseas_manager()

    # 심볼 → queue 매핑 (이 WS 연결 전용)
    queues: dict[str, asyncio.Queue] = {}

    async def subscribe_symbol(symbol: str):
        if symbol in queues:
            return
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        queues[symbol] = q
        if is_domestic(symbol):
            await domestic_mgr.subscribe(symbol, q)
        else:
            await overseas_mgr.subscribe(symbol, q)

    def unsubscribe_symbol(symbol: str):
        q = queues.pop(symbol, None)
        if q is None:
            return
        if is_domestic(symbol):
            domestic_mgr.unsubscribe(symbol, q)
        else:
            overseas_mgr.unsubscribe(symbol, q)

    def unsubscribe_all():
        for sym, q in list(queues.items()):
            if is_domestic(sym):
                domestic_mgr.unsubscribe(sym, q)
            else:
                overseas_mgr.unsubscribe(sym, q)
        queues.clear()

    async def recv_loop():
        """클라이언트 제어 메시지 수신."""
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
                action = msg.get("action")
                symbols = [s.upper() for s in msg.get("symbols", [])]
                if action == "subscribe":
                    for sym in symbols:
                        await subscribe_symbol(sym)
                elif action == "unsubscribe":
                    for sym in symbols:
                        unsubscribe_symbol(sym)
            except Exception as e:
                logger.debug("[MarketBoardWS] 제어 메시지 파싱 오류: %s", e)

    async def send_loop():
        """모든 구독 큐에서 메시지 수집 → 200ms 창 병합 → 클라이언트 전송."""
        while True:
            if not queues:
                # 구독 없음 → ping 유지
                await asyncio.sleep(20)
                await websocket.send_json({"type": "ping"})
                continue

            # 최대 200ms 동안 모든 큐 폴링
            batch: dict[str, dict] = {}  # symbol → latest price data
            deadline = asyncio.get_event_loop().time() + 0.2

            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break

                # 모든 큐에서 즉시 수집 (non-blocking)
                got_any = False
                for sym, q in list(queues.items()):
                    while not q.empty():
                        try:
                            msg = q.get_nowait()
                            if msg.get("type") == "price":
                                batch[sym] = {
                                    "price": msg.get("price"),
                                    "change_pct": msg.get("change_rate"),
                                    "change": msg.get("change"),
                                    "sign": msg.get("sign"),
                                    "open": msg.get("open"),
                                    "high": msg.get("high"),
                                    "low": msg.get("low"),
                                }
                            got_any = True
                        except asyncio.QueueEmpty:
                            break

                if not got_any:
                    # 새 메시지 없으면 잠깐 대기
                    await asyncio.sleep(0.05)

            if batch:
                await websocket.send_json({"type": "prices", "data": batch})
            else:
                # 200ms 동안 데이터 없으면 ping
                await asyncio.sleep(0.1)

    try:
        # recv_loop와 send_loop 동시 실행
        recv_task = asyncio.create_task(recv_loop())
        send_task = asyncio.create_task(send_loop())
        done, pending = await asyncio.wait(
            [recv_task, send_task],
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for t in pending:
            t.cancel()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("[MarketBoardWS] 오류: %s", e)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        unsubscribe_all()
