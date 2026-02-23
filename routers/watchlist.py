"""관심종목 API 라우터."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.watchlist_service import WatchlistService
from stock import store

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])
_svc = WatchlistService()


# ── 요청 바디 모델 ───────────────────────────────────────────────────────────

class AddBody(BaseModel):
    code: str           # 종목코드 또는 종목명
    memo: str = ""


class MemoBody(BaseModel):
    memo: str


# ── CRUD ────────────────────────────────────────────────────────────────────

@router.get("")
def list_watchlist():
    """관심종목 목록."""
    return {"items": store.all_items()}


@router.post("", status_code=201)
def add_watchlist(body: AddBody):
    """관심종목 추가 (종목코드 또는 종목명 허용)."""
    try:
        code, name = _svc.resolve_symbol(body.code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    added = store.add_item(code, name, body.memo)
    if not added:
        raise HTTPException(status_code=409, detail=f"이미 등록된 종목입니다: {name} ({code})")

    item = store.get_item(code)
    return {"item": item}


@router.delete("/{code}")
def remove_watchlist(code: str):
    """관심종목 삭제."""
    if not store.remove_item(code):
        raise HTTPException(status_code=404, detail=f"관심종목에 없는 종목코드입니다: {code}")
    return {"deleted": True}


@router.patch("/{code}")
def update_memo(code: str, body: MemoBody):
    """메모 수정."""
    if not store.update_memo(code, body.memo):
        raise HTTPException(status_code=404, detail=f"관심종목에 없는 종목코드입니다: {code}")
    item = store.get_item(code)
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
def get_stock_info(code: str):
    """단일 종목 상세 (기본정보 + 3개년 재무)."""
    try:
        detail = _svc.get_stock_detail(code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    if not detail["basic"]:
        raise HTTPException(status_code=404, detail=f"종목 정보를 찾을 수 없습니다: {code}")

    return detail
