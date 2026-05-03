"""관심종목 API 라우터."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from services import _dashboard_cache
from services.auth_deps import get_current_user
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
def get_watchlist_order(user: dict = Depends(get_current_user)):
    """관심종목 표시 순서 조회."""
    return {"items": store.get_order(user["id"])}


@router.put("/order")
def save_watchlist_order(body: SaveOrderBody, user: dict = Depends(get_current_user)):
    """관심종목 표시 순서 저장 (전체 교체)."""
    store.save_order(user["id"], [item.model_dump() for item in body.items])
    return {"ok": True}


# ── CRUD ────────────────────────────────────────────────────────────────────

@router.get("")
def list_watchlist(user: dict = Depends(get_current_user)):
    """관심종목 목록."""
    return {"items": store.all_items(user["id"])}


@router.post("", status_code=201)
def add_watchlist(body: AddBody, user: dict = Depends(get_current_user)):
    """관심종목 추가 (종목코드 또는 종목명 허용). market: KR | US."""
    try:
        code, name, market = _svc.resolve_symbol(body.code, body.market)
    except ValueError as e:
        raise NotFoundError(str(e))

    added = store.add_item(user["id"], code, name, body.memo, market)
    if not added:
        raise ConflictError(f"이미 등록된 종목입니다: {name} ({code})")

    # QW-4: 종목 추가 → dashboard 캐시 무효화
    _dashboard_cache.invalidate(user["id"])

    item = store.get_item(user["id"], code, market)
    return {"item": item}


@router.delete("/{code}")
def remove_watchlist(code: str, market: str = Query("KR"), user: dict = Depends(get_current_user)):
    """관심종목 삭제."""
    if not store.remove_item(user["id"], code, market):
        raise NotFoundError(f"관심종목에 없는 종목코드입니다: {code}")
    # QW-4: 종목 삭제 → dashboard 캐시 무효화
    _dashboard_cache.invalidate(user["id"])
    return {"deleted": True}


@router.patch("/{code}")
def update_memo(code: str, body: MemoBody, market: str = Query("KR"), user: dict = Depends(get_current_user)):
    """메모 수정."""
    if not store.update_memo(user["id"], code, body.memo, market):
        raise NotFoundError(f"관심종목에 없는 종목코드입니다: {code}")
    # QW-4: 메모 변경 → dashboard 캐시 무효화 (memo는 응답에 포함됨)
    _dashboard_cache.invalidate(user["id"])
    item = store.get_item(user["id"], code, market)
    return {"item": item}


# ── 대시보드 / 상세 ──────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(user: dict = Depends(get_current_user)):
    """전체 관심종목 시세 + 재무 대시보드.

    QW-4: 사용자별 60s in-memory 캐시. F5 연타 즉시 응답.
    부분 실패 응답은 15s 단축 캐시 (다음 요청에 재시도 유도).
    add/remove/update_memo 시 자동 invalidate.
    """
    items = store.all_items(user["id"])
    if not items:
        return {"stocks": []}

    # 캐시 hit 시 즉시 반환
    cached = _dashboard_cache.get(user_id=user["id"], items=items)
    if cached is not None:
        return {"stocks": cached}

    stocks = _svc.get_dashboard_data(items)
    _dashboard_cache.set(user_id=user["id"], items=items, data=stocks)
    return {"stocks": stocks}


@router.get("/info/{code}")
def get_stock_info(code: str, market: str = Query("KR"), _user: dict = Depends(get_current_user)):
    """단일 종목 상세 (기본정보 + 재무)."""
    try:
        detail = _svc.get_stock_detail(code, market)
    except Exception as e:
        raise ExternalAPIError(str(e))

    if not detail["basic"]:
        raise NotFoundError(f"종목 정보를 찾을 수 없습니다: {code}")

    return detail
