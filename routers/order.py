"""주문 API 라우터.

주문 발송 / 정정 / 취소 / 미체결 조회 / 체결 내역 / 이력 / 대사 / 예약주문.
KIS API 키 미설정 시 503 반환.
모든 엔드포인트는 services.order_service를 통해서만 데이터에 접근한다.

R5 (KIS 멀티 계좌, 2026-05-15):
- POST /api/order body 에 account_label (default 폴백).
- GET /api/order/* 쿼리 account_label.
- 정정/취소는 원주문의 account_label 자동 사용 (REQ-API-05).
- 라우터 진입 시 ContextVar(user_id, account_label) 전파 → 서비스 체인이 직접 인자 없이도 인지.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Literal, Optional

from routers._kis_auth import set_current_account_label, set_current_user_id
from services.auth_deps import require_admin
from services import order_service
from services.exceptions import NotFoundError

router = APIRouter(prefix="/api/order", tags=["order"])


def _propagate_context(user: dict, account_label: Optional[str]) -> Optional[int]:
    user_id = int(user["id"]) if user and user.get("id") else None
    set_current_user_id(user_id)
    set_current_account_label(account_label)
    return user_id


# ── 요청 바디 모델 ────────────────────────────────────────────────────────────

class PlaceOrderBody(BaseModel):
    symbol: str
    symbol_name: str = ""
    market: str = "KR"          # KR / US / FNO
    side: str                   # buy / sell
    order_type: str = "00"      # 00(지정가) / 01(시장가)
    price: float = 0.0
    quantity: int
    memo: str = ""
    # FNO 전용 (선택)
    nmpr_type_cd: str = ""
    krx_nmpr_cndt_cd: str = ""
    ord_dvsn_cd: str = ""
    # KR 거래소 셀렉터
    exchange: Literal["SOR", "KRX", "NXT"] = "SOR"
    # R5 — 멀티 계좌 라벨 (None 시 default 폴백)
    account_label: Optional[str] = None


class ModifyOrderBody(BaseModel):
    org_no: str
    market: str = "KR"
    order_type: str = "00"
    price: float
    quantity: int
    total: bool = True
    nmpr_type_cd: str = ""
    krx_nmpr_cndt_cd: str = ""
    ord_dvsn_cd: str = ""
    symbol: str = ""
    account_label: Optional[str] = None  # 원주문과 불일치 시 400


class CancelOrderBody(BaseModel):
    org_no: str
    market: str = "KR"
    order_type: str = "00"
    quantity: int = 0
    total: bool = True
    symbol: str = ""
    account_label: Optional[str] = None


class ReservationBody(BaseModel):
    symbol: str
    symbol_name: str = ""
    market: str = "KR"
    side: str
    order_type: str = "00"
    price: float = 0.0
    quantity: int
    condition_type: str
    condition_value: str
    memo: str = ""
    account_label: Optional[str] = None


# ── 주문 발송 ─────────────────────────────────────────────────────────────────

@router.post("/place", status_code=201)
def place_order(body: PlaceOrderBody, user: dict = Depends(require_admin)):
    """주문 발송 (국내/해외 매수/매도).

    R5: body.account_label (옵셔널, default 폴백).
    """
    user_id = _propagate_context(user, body.account_label)
    order = order_service.place_order(
        symbol=body.symbol,
        symbol_name=body.symbol_name,
        market=body.market,
        side=body.side,
        order_type=body.order_type,
        price=body.price,
        quantity=body.quantity,
        memo=body.memo,
        nmpr_type_cd=body.nmpr_type_cd,
        krx_nmpr_cndt_cd=body.krx_nmpr_cndt_cd,
        ord_dvsn_cd=body.ord_dvsn_cd,
        exchange=body.exchange,
        user_id=user_id,
        account_label=body.account_label,
    )
    return {"order": order, "balance_stale": True, "account_label": order.get("account_label")}


# ── 매수가능 조회 ─────────────────────────────────────────────────────────────

@router.get("/buyable")
def get_buyable(
    symbol: str = Query(...),
    market: str = Query("KR"),
    price: float = Query(0.0),
    order_type: str = Query("00"),
    side: str = Query("buy"),
    account_label: Optional[str] = Query(None),
    user: dict = Depends(require_admin),
):
    user_id = _propagate_context(user, account_label)
    return order_service.get_buyable(
        symbol, market, price, order_type, side=side,
        user_id=user_id, account_label=account_label,
    )


# ── 미체결 주문 목록 ──────────────────────────────────────────────────────────

@router.get("/open")
def get_open_orders(
    market: str = Query("KR"),
    account_label: Optional[str] = Query(None),
    user: dict = Depends(require_admin),
):
    user_id = _propagate_context(user, account_label)
    orders = order_service.get_open_orders(market, user_id=user_id, account_label=account_label)
    return {"orders": orders}


# ── 주문 정정 ─────────────────────────────────────────────────────────────────

@router.post("/{order_no}/modify")
def modify_order(order_no: str, body: ModifyOrderBody, user: dict = Depends(require_admin)):
    """REQ-API-05: 원주문의 account_label 자동 사용. body.account_label 명시 시 불일치는 400."""
    user_id = _propagate_context(user, body.account_label)
    result = order_service.modify_order(
        order_no=order_no,
        org_no=body.org_no,
        market=body.market,
        order_type=body.order_type,
        price=body.price,
        quantity=body.quantity,
        total=body.total,
        nmpr_type_cd=body.nmpr_type_cd,
        krx_nmpr_cndt_cd=body.krx_nmpr_cndt_cd,
        ord_dvsn_cd=body.ord_dvsn_cd,
        symbol=body.symbol,
        user_id=user_id,
        account_label=body.account_label,
    )
    return result


# ── 주문 취소 ─────────────────────────────────────────────────────────────────

@router.post("/{order_no}/cancel")
def cancel_order(order_no: str, body: CancelOrderBody, user: dict = Depends(require_admin)):
    user_id = _propagate_context(user, body.account_label)
    result = order_service.cancel_order(
        order_no=order_no,
        org_no=body.org_no,
        market=body.market,
        order_type=body.order_type,
        quantity=body.quantity,
        total=body.total,
        symbol=body.symbol,
        user_id=user_id,
        account_label=body.account_label,
    )
    return result


# ── 당일 체결 내역 ────────────────────────────────────────────────────────────

@router.get("/executions")
def get_executions(
    market: str = Query("KR"),
    account_label: Optional[str] = Query(None),
    user: dict = Depends(require_admin),
):
    user_id = _propagate_context(user, account_label)
    executions = order_service.get_executions(market, user_id=user_id, account_label=account_label)
    return {"executions": executions}


# ── 선물옵션 시세 조회 ────────────────────────────────────────────────────────

@router.get("/fno-price")
def get_fno_price(
    symbol: str = Query(..., description="선물옵션 단축코드 (예: 101W09)"),
    mrkt_div: str = Query("F", description="시장분류: F=지수선물, O=지수옵션, JF=주식선물"),
    _user: dict = Depends(require_admin),
):
    return order_service.get_fno_price(symbol, mrkt_div)


# ── 로컬 주문 이력 ────────────────────────────────────────────────────────────

@router.get("/history")
def get_order_history(
    symbol: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    account_label: Optional[str] = Query(None),
    user: dict = Depends(require_admin),
):
    """로컬 DB 주문 이력. account_label 쿼리 필터 (REQ-API-04)."""
    user_id = _propagate_context(user, account_label)
    orders = order_service.get_order_history(
        symbol=symbol,
        market=market,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        user_id=user_id,
        account_label=account_label,
    )
    return {"orders": orders}


# ── 대사/동기화 ───────────────────────────────────────────────────────────────

@router.post("/sync")
def sync_orders(_user: dict = Depends(require_admin)):
    result = order_service.sync_orders()
    return result


# ── 예약주문 ──────────────────────────────────────────────────────────────────

@router.post("/reserve", status_code=201)
def create_reservation(body: ReservationBody, user: dict = Depends(require_admin)):
    """예약주문 등록. body.account_label 저장 (REQ-ORDER-02)."""
    user_id = _propagate_context(user, body.account_label)
    reservation = order_service.create_reservation(
        symbol=body.symbol,
        symbol_name=body.symbol_name,
        market=body.market,
        side=body.side,
        order_type=body.order_type,
        price=body.price,
        quantity=body.quantity,
        condition_type=body.condition_type,
        condition_value=body.condition_value,
        memo=body.memo,
        user_id=user_id,
        account_label=body.account_label,
    )
    return {"reservation": reservation}


@router.get("/reserves")
def list_reservations(
    status: Optional[str] = Query(None),
    account_label: Optional[str] = Query(None),
    user: dict = Depends(require_admin),
):
    user_id = _propagate_context(user, account_label)
    reservations = order_service.get_reservations(
        status=status, user_id=user_id, account_label=account_label,
    )
    return {"reservations": reservations}


@router.delete("/reserve/{res_id}")
def delete_reservation(res_id: int, _user: dict = Depends(require_admin)):
    deleted = order_service.delete_reservation(res_id)
    if not deleted:
        raise NotFoundError("예약주문을 찾을 수 없거나 WAITING 상태가 아닙니다.")
    return {"deleted": True}
