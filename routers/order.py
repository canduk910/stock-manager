"""주문 API 라우터.

주문 발송 / 정정 / 취소 / 미체결 조회 / 체결 내역 / 이력 / 대사 / 예약주문.
KIS API 키 미설정 시 503 반환.
모든 엔드포인트는 services.order_service를 통해서만 데이터에 접근한다.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from services import order_service

router = APIRouter(prefix="/api/order", tags=["order"])


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
    nmpr_type_cd: str = ""      # 호가유형코드 (FNO)
    krx_nmpr_cndt_cd: str = ""  # KRX 호가조건코드 (FNO)
    ord_dvsn_cd: str = ""       # 주문구분코드 (FNO)


class ModifyOrderBody(BaseModel):
    org_no: str
    market: str = "KR"          # KR / US / FNO
    order_type: str = "00"
    price: float
    quantity: int
    total: bool = True
    # FNO 전용 (선택)
    nmpr_type_cd: str = ""
    krx_nmpr_cndt_cd: str = ""
    ord_dvsn_cd: str = ""


class CancelOrderBody(BaseModel):
    org_no: str
    market: str = "KR"          # KR / US / FNO
    order_type: str = "00"
    quantity: int = 0
    total: bool = True


class ReservationBody(BaseModel):
    symbol: str
    symbol_name: str = ""
    market: str = "KR"
    side: str                       # buy / sell
    order_type: str = "00"          # 00(지정가) / 01(시장가)
    price: float = 0.0
    quantity: int
    condition_type: str             # price_below / price_above / scheduled
    condition_value: str            # 목표가격(숫자 문자열) 또는 ISO 8601 datetime
    memo: str = ""


# ── 주문 발송 ─────────────────────────────────────────────────────────────────

@router.post("/place", status_code=201)
def place_order(body: PlaceOrderBody):
    """주문 발송 (국내/해외 매수/매도).

    KIS API 키 미설정 시 503.
    주문 실패 시 400.
    """
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
    )
    return {"order": order, "balance_stale": True}


# ── 매수가능 조회 ─────────────────────────────────────────────────────────────

@router.get("/buyable")
def get_buyable(
    symbol: str = Query(...),
    market: str = Query("KR"),
    price: float = Query(0.0),
    order_type: str = Query("00"),
    side: str = Query("buy"),
):
    """매수가능 금액/수량 조회. FNO는 side 파라미터 필요."""
    return order_service.get_buyable(symbol, market, price, order_type, side=side)


# ── 미체결 주문 목록 (KIS) ────────────────────────────────────────────────────

@router.get("/open")
def get_open_orders(market: str = Query("KR")):
    """미체결 주문 목록 (KIS 실시간). market: KR / US."""
    orders = order_service.get_open_orders(market)
    return {"orders": orders}


# ── 주문 정정 ─────────────────────────────────────────────────────────────────

@router.post("/{order_no}/modify")
def modify_order(order_no: str, body: ModifyOrderBody):
    """주문 정정 (가격/수량 변경)."""
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
    )
    return result


# ── 주문 취소 ─────────────────────────────────────────────────────────────────

@router.post("/{order_no}/cancel")
def cancel_order(order_no: str, body: CancelOrderBody):
    """주문 취소 (잔량전부/일부)."""
    result = order_service.cancel_order(
        order_no=order_no,
        org_no=body.org_no,
        market=body.market,
        order_type=body.order_type,
        quantity=body.quantity,
        total=body.total,
    )
    return result


# ── 당일 체결 내역 (KIS) ──────────────────────────────────────────────────────

@router.get("/executions")
def get_executions(market: str = Query("KR")):
    """당일 체결 내역 (KIS). market: KR / US."""
    executions = order_service.get_executions(market)
    return {"executions": executions}


# ── 선물옵션 시세 조회 ────────────────────────────────────────────────────────

@router.get("/fno-price")
def get_fno_price(
    symbol: str = Query(..., description="선물옵션 단축코드 (예: 101W09)"),
    mrkt_div: str = Query("F", description="시장분류: F=지수선물, O=지수옵션, JF=주식선물"),
):
    """선물옵션 현재가 조회. 주문 전 시세 확인 및 종목 유효성 검증에 사용."""
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
):
    """로컬 DB 주문 이력. 반환 전 활성 주문을 KIS와 자동 대사."""
    orders = order_service.get_order_history(
        symbol=symbol,
        market=market,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return {"orders": orders}


# ── 대사/동기화 ───────────────────────────────────────────────────────────────

@router.post("/sync")
def sync_orders():
    """KIS 체결+미체결 내역과 로컬 DB 대사(Reconciliation)."""
    result = order_service.sync_orders()
    return result


# ── 예약주문 ──────────────────────────────────────────────────────────────────

@router.post("/reserve", status_code=201)
def create_reservation(body: ReservationBody):
    """예약주문 등록. 도메인 규칙 검증 포함."""
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
    )
    return {"reservation": reservation}


@router.get("/reserves")
def list_reservations(status: Optional[str] = Query(None)):
    """예약주문 목록. status: WAITING / TRIGGERED / EXECUTED / FAILED / CANCELLED"""
    reservations = order_service.get_reservations(status=status)
    return {"reservations": reservations}


@router.delete("/reserve/{res_id}")
def delete_reservation(res_id: int):
    """예약주문 삭제 (WAITING 상태만 가능)."""
    deleted = order_service.delete_reservation(res_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="예약주문을 찾을 수 없거나 WAITING 상태가 아닙니다.",
        )
    return {"deleted": True}
