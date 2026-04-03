"""관심종목 API 라우터."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from services.exceptions import NotFoundError, ConflictError, ExternalAPIError
from services.watchlist_service import WatchlistService
from stock import store

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])
_svc = WatchlistService()


# ── 요청 바디 모델 ───────────────────────────────────────────────────────────

class AddBody(BaseModel):
    code: str           # 종목코드 또는 종목명
    memo: str = ""
    market: str = "KR"  # "KR" 또는 "US"


class MemoBody(BaseModel):
    memo: str


class OrderItem(BaseModel):
    code: str
    market: str = "KR"


class SaveOrderBody(BaseModel):
    items: list[OrderItem]


# ── 종목 순서 (/{code} 라우트보다 앞에 등록해야 경로 충돌 방지) ────────────────

@router.get("/order")
def get_watchlist_order():
    """관심종목 표시 순서 조회."""
    return {"items": store.get_order()}


@router.put("/order")
def save_watchlist_order(body: SaveOrderBody):
    """관심종목 표시 순서 저장 (전체 교체)."""
    store.save_order([item.model_dump() for item in body.items])
    return {"ok": True}


# ── CRUD ────────────────────────────────────────────────────────────────────

@router.get("")
def list_watchlist():
    """관심종목 목록."""
    return {"items": store.all_items()}


@router.post("", status_code=201)
def add_watchlist(body: AddBody):
    """관심종목 추가 (종목코드 또는 종목명 허용). market: KR | US."""
    try:
        code, name, market = _svc.resolve_symbol(body.code, body.market)
    except ValueError as e:
        raise NotFoundError(str(e))

    added = store.add_item(code, name, body.memo, market)
    if not added:
        raise ConflictError(f"이미 등록된 종목입니다: {name} ({code})")

    item = store.get_item(code, market)
    return {"item": item}


@router.delete("/{code}")
def remove_watchlist(code: str, market: str = Query("KR")):
    """관심종목 삭제."""
    if not store.remove_item(code, market):
        raise NotFoundError(f"관심종목에 없는 종목코드입니다: {code}")
    return {"deleted": True}


@router.patch("/{code}")
def update_memo(code: str, body: MemoBody, market: str = Query("KR")):
    """메모 수정."""
    if not store.update_memo(code, body.memo, market):
        raise NotFoundError(f"관심종목에 없는 종목코드입니다: {code}")
    item = store.get_item(code, market)
    return {"item": item}


# ── 대시보드 / 상세 ──────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard():
    """전체 관심종목 시세 + 재무 대시보드."""
    items = store.all_items()
    if not items:
        return {"stocks": []}
    stocks = _svc.get_dashboard_data(items)
    return {"stocks": stocks}


@router.get("/info/{code}")
def get_stock_info(code: str, market: str = Query("KR")):
    """단일 종목 상세 (기본정보 + 재무)."""
    try:
        detail = _svc.get_stock_detail(code, market)
    except Exception as e:
        raise ExternalAPIError(str(e))

    if not detail["basic"]:
        raise NotFoundError(f"종목 정보를 찾을 수 없습니다: {code}")

    return detail
