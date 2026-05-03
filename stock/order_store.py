"""주문/예약주문 저장소 — SQLAlchemy ORM adapter.

기존 함수 시그니처 100% 유지. 내부는 OrderRepository에 위임.
services/, routers/ 변경 없음.

Phase 4 D.3: insert_order/insert_reservation은 ContextVar에서 현재 user_id를
자동 부착해 신규 row에 user_id 컬럼을 채운다 (시그니처 변경 없음).
"""

from typing import Optional

from db.repositories.order_repo import OrderRepository
from db.session import get_session


def _ctx_user_id() -> Optional[int]:
    """ContextVar에서 현재 user_id 추출 (라우터 진입 시 set됨). 시스템 호출 시 None."""
    try:
        from routers._kis_auth import get_current_user_id
        return get_current_user_id()
    except Exception:
        return None


# ── 주문 CRUD ────────────────────────────────────────────────────────────────

def insert_order(
    symbol: str,
    symbol_name: str,
    market: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    currency: str = "KRW",
    memo: str = "",
    order_no: str = None,
    org_no: str = None,
    kis_response: str = None,
    status: str = "PLACED",
) -> dict:
    with get_session() as db:
        return OrderRepository(db).insert_order(
            symbol=symbol,
            symbol_name=symbol_name,
            market=market,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            currency=currency,
            memo=memo,
            order_no=order_no,
            org_no=org_no,
            kis_response=kis_response,
            status=status,
            user_id=_ctx_user_id(),
        )


def update_order_status(
    order_id: int,
    status: str,
    *,
    filled_quantity: int = None,
    filled_price: float = None,
    order_no: str = None,
    org_no: str = None,
    kis_response: str = None,
) -> Optional[dict]:
    with get_session() as db:
        return OrderRepository(db).update_order_status(
            order_id,
            status,
            filled_quantity=filled_quantity,
            filled_price=filled_price,
            order_no=order_no,
            org_no=org_no,
            kis_response=kis_response,
        )


def get_order(order_id: int) -> Optional[dict]:
    with get_session() as db:
        return OrderRepository(db).get_order(order_id)


def get_order_by_order_no(order_no: str, market: str = "KR") -> Optional[dict]:
    with get_session() as db:
        return OrderRepository(db).get_order_by_order_no(order_no, market)


def list_orders(
    symbol: str = None,
    market: str = None,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
) -> list[dict]:
    with get_session() as db:
        return OrderRepository(db).list_orders(
            symbol=symbol,
            market=market,
            status=status,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )


def list_active_orders() -> list[dict]:
    """PENDING, PLACED 또는 PARTIAL 상태인 주문 목록."""
    with get_session() as db:
        return OrderRepository(db).list_active_orders()


def update_order_details(
    order_id: int,
    *,
    price: float = None,
    quantity: int = None,
    order_type: str = None,
) -> Optional[dict]:
    """주문 정정 사항 로컬 반영 (가격/수량/주문유형)."""
    with get_session() as db:
        return OrderRepository(db).update_order_details(
            order_id,
            price=price,
            quantity=quantity,
            order_type=order_type,
        )


# ── 예약주문 CRUD ─────────────────────────────────────────────────────────────

def insert_reservation(
    symbol: str,
    symbol_name: str,
    market: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    condition_type: str,
    condition_value: str,
    memo: str = "",
) -> dict:
    with get_session() as db:
        return OrderRepository(db).insert_reservation(
            symbol=symbol,
            symbol_name=symbol_name,
            market=market,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            condition_type=condition_type,
            condition_value=condition_value,
            memo=memo,
            user_id=_ctx_user_id(),
        )


def update_reservation_status(
    res_id: int,
    status: str,
    *,
    result_order_no: str = None,
) -> Optional[dict]:
    with get_session() as db:
        return OrderRepository(db).update_reservation_status(
            res_id,
            status,
            result_order_no=result_order_no,
        )


def list_reservations(status: str = None) -> list[dict]:
    with get_session() as db:
        return OrderRepository(db).list_reservations(status=status)


def get_reservation(res_id: int) -> Optional[dict]:
    with get_session() as db:
        return OrderRepository(db).get_reservation(res_id)


def delete_reservation(res_id: int) -> bool:
    with get_session() as db:
        return OrderRepository(db).delete_reservation(res_id)
