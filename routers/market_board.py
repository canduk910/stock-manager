"""
시세판 API 라우터.
GET    /api/market-board/new-highs-lows         신고가/신저가 Top 10
POST   /api/market-board/sparklines             복수 종목 sparkline 배치
GET    /api/market-board/prices                 다중심볼 가격 일괄 폴링 (REST, yfinance+KIS REST 폴백)
GET    /api/market-board/custom-stocks          별도 등록 종목 목록
POST   /api/market-board/custom-stocks          별도 등록 종목 추가
DELETE /api/market-board/custom-stocks/{code}   별도 등록 종목 삭제

NOTE: 시세판 다중심볼 WS (`/ws/market-board`)는 2026-05-12 폐지됨.
      KIS WS slot 잠식(자동매매 41건 제한)을 회수하기 위해 REST 일괄 폴링으로 전환.
      장중 15s / 장외 60s 폴링 (in-memory 캐시는 장중 10s/장외 60s).
"""
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from services.auth_deps import get_current_user
from services.exceptions import NotFoundError, ConflictError, ServiceError
from stock.market import fetch_prices_batch

router = APIRouter(tags=["market-board"])
logger = logging.getLogger(__name__)


# ── REST 엔드포인트 ────────────────────────────────────────────────────────────

@router.get("/api/market-board/new-highs-lows")
def get_new_highs_lows(top: int = 10, _user: dict = Depends(get_current_user)):
    """당일 신고가/신저가 종목 조회 (시총 상위 기준)."""
    from stock.market_board import fetch_new_highs_lows
    return fetch_new_highs_lows(top_n=top)


class SparklineRequest(BaseModel):
    items: list[dict]  # [{"code": "005930", "market": "KR"}, ...]


@router.post("/api/market-board/sparklines")
def get_sparklines(body: SparklineRequest, _user: dict = Depends(get_current_user)):
    """복수 종목 1년 주봉 종가 배치 조회."""
    from stock.market_board import fetch_sparklines_batch
    return fetch_sparklines_batch(body.items)


@router.post("/api/market-board/intraday-ohlc")
def get_intraday_ohlc(body: SparklineRequest, _user: dict = Depends(get_current_user)):
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
def list_custom_stocks(user: dict = Depends(get_current_user)):
    """시세판 별도 등록 종목 목록."""
    from stock.market_board_store import all_items
    return {"items": all_items(user["id"])}


@router.post("/api/market-board/custom-stocks", status_code=201)
def add_custom_stock(body: CustomStockBody, user: dict = Depends(get_current_user)):
    """시세판 별도 종목 추가."""
    from stock.market_board_store import add_item
    ok = add_item(user["id"], body.code, body.name, body.market)
    if not ok:
        raise ConflictError("이미 등록된 종목입니다.")
    return {"item": {"code": body.code, "market": body.market, "name": body.name}}


@router.delete("/api/market-board/custom-stocks/{code}", status_code=204)
def remove_custom_stock(code: str, market: str = Query("KR"), user: dict = Depends(get_current_user)):
    """시세판 별도 종목 삭제."""
    from stock.market_board_store import remove_item
    ok = remove_item(user["id"], code, market)
    if not ok:
        raise NotFoundError("등록되지 않은 종목입니다.")


# ── 종목 순서 ────────────────────────────────────────────────────────────────

@router.get("/api/market-board/order")
def get_board_order(user: dict = Depends(get_current_user)):
    """시세판 종목 표시 순서 조회."""
    from stock.market_board_store import get_order
    return {"items": get_order(user["id"])}


@router.put("/api/market-board/order")
def save_board_order(body: SaveOrderBody, user: dict = Depends(get_current_user)):
    """시세판 종목 표시 순서 저장 (전체 교체)."""
    from stock.market_board_store import save_order
    save_order(user["id"], [item.model_dump() for item in body.items])
    return {"ok": True}


# ── 다중심볼 가격 일괄 폴링 (REST) ────────────────────────────────────────────

# 시세판 폴링 가드 — 한 번에 최대 50종목까지만 허용
_MAX_BATCH_CODES = 50


@router.get("/api/market-board/prices")
def get_prices_batch(
    codes: str = Query(..., description="콤마 구분 종목코드 목록, 최대 50개"),
    market: str = Query("KR", description="KR / US"),
    _user: dict = Depends(get_current_user),
):
    """다중심볼 가격 일괄 폴링.

    1차 yfinance ``Tickers(...).fast_info`` 일괄 + 2차 KIS REST 폴백.
    in-memory TTL 캐시(장중 10s / 장외 60s)로 rate limit 방지.
    부분 실패 시에도 200 + 성공한 종목만 반환 (보드는 부분 표시가 더 유용).

    Args:
        codes: ``"005930,000660"`` 형식. 최대 50개. 빈 문자열 허용(빈 결과).
        market: ``"KR"`` 또는 ``"US"``.

    Returns:
        ``{"prices": {code: {price, change, change_pct, prev_close, volume}}}``

    Raises:
        ServiceError(400): codes 개수가 50개를 초과한 경우.
    """
    raw = (codes or "").strip()
    if not raw:
        return {"prices": {}}
    code_list = [c.strip().upper() for c in raw.split(",") if c.strip()]
    if len(code_list) > _MAX_BATCH_CODES:
        raise ServiceError(
            f"codes 최대 {_MAX_BATCH_CODES}개까지 허용 (요청 {len(code_list)}개)"
        )
    mkt = (market or "KR").upper()
    if mkt not in ("KR", "US"):
        raise ServiceError(f"market은 'KR' 또는 'US'여야 합니다 (입력: {market})")

    try:
        prices = fetch_prices_batch(code_list, market=mkt) or {}
    except Exception as e:
        # 부분 실패 정책: 외부 API 예외도 빈 결과로 graceful degrade
        logger.warning("[market-board/prices] fetch_prices_batch 실패: %s", e)
        prices = {}
    return {"prices": prices}
