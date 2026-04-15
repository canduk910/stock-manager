"""OrderRepository — 1:1 mapping to stock/order_store.py functions."""

from typing import Optional

from sqlalchemy.orm import Session

from db.models.order import Order, Reservation
from db.utils import now_kst_iso


def _now() -> str:
    return now_kst_iso()


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Order CRUD ──────────────────────────────────────────────

    def insert_order(
        self,
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
        now = _now()
        order = Order(
            order_no=order_no,
            org_no=org_no,
            symbol=symbol,
            symbol_name=symbol_name,
            market=market,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            currency=currency,
            memo=memo,
            status=status,
            placed_at=now,
            updated_at=now,
            kis_response=kis_response,
        )
        self.db.add(order)
        self.db.flush()
        return order.to_dict()

    def update_order_status(
        self,
        order_id: int,
        status: str,
        *,
        filled_quantity: int = None,
        filled_price: float = None,
        order_no: str = None,
        org_no: str = None,
        kis_response: str = None,
    ) -> Optional[dict]:
        order = self.db.query(Order).filter_by(id=order_id).first()
        if not order:
            return None

        order.status = status
        order.updated_at = _now()

        if filled_quantity is not None:
            order.filled_quantity = filled_quantity
        if filled_price is not None:
            order.filled_price = filled_price
        if order_no is not None:
            order.order_no = order_no
        if org_no is not None:
            order.org_no = org_no
        if kis_response is not None:
            order.kis_response = kis_response
        if status == "FILLED":
            order.filled_at = _now()

        self.db.flush()
        return order.to_dict()

    def get_order(self, order_id: int) -> Optional[dict]:
        order = self.db.query(Order).filter_by(id=order_id).first()
        return order.to_dict() if order else None

    def get_order_by_order_no(self, order_no: str, market: str = "KR") -> Optional[dict]:
        order = (
            self.db.query(Order)
            .filter_by(order_no=order_no, market=market)
            .order_by(Order.id.desc())
            .first()
        )
        return order.to_dict() if order else None

    def list_orders(
        self,
        symbol: str = None,
        market: str = None,
        status: str = None,
        date_from: str = None,
        date_to: str = None,
        limit: int = 100,
    ) -> list[dict]:
        q = self.db.query(Order)
        if symbol:
            q = q.filter(Order.symbol == symbol)
        if market:
            q = q.filter(Order.market == market)
        if status:
            q = q.filter(Order.status == status)
        if date_from:
            q = q.filter(Order.placed_at >= date_from)
        if date_to:
            q = q.filter(Order.placed_at <= date_to + "T23:59:59")
        rows = q.order_by(Order.id.desc()).limit(limit).all()
        return [r.to_dict() for r in rows]

    def list_active_orders(self) -> list[dict]:
        rows = (
            self.db.query(Order)
            .filter(Order.status.in_(["PENDING", "PLACED", "PARTIAL"]))
            .order_by(Order.id.desc())
            .all()
        )
        return [r.to_dict() for r in rows]

    def update_order_details(
        self,
        order_id: int,
        *,
        price: float = None,
        quantity: int = None,
        order_type: str = None,
    ) -> Optional[dict]:
        order = self.db.query(Order).filter_by(id=order_id).first()
        if not order:
            return None

        order.updated_at = _now()
        if price is not None:
            order.price = price
        if quantity is not None:
            order.quantity = quantity
        if order_type is not None:
            order.order_type = order_type

        self.db.flush()
        return order.to_dict()

    # ── Reservation CRUD ────────────────────────────────────────

    def insert_reservation(
        self,
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
        now = _now()
        res = Reservation(
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
            created_at=now,
            updated_at=now,
        )
        self.db.add(res)
        self.db.flush()
        return res.to_dict()

    def update_reservation_status(
        self,
        res_id: int,
        status: str,
        *,
        result_order_no: str = None,
    ) -> Optional[dict]:
        res = self.db.query(Reservation).filter_by(id=res_id).first()
        if not res:
            return None

        res.status = status
        res.updated_at = _now()
        if status == "TRIGGERED":
            res.triggered_at = _now()
        if result_order_no is not None:
            res.result_order_no = result_order_no

        self.db.flush()
        return res.to_dict()

    def list_reservations(self, status: str = None) -> list[dict]:
        q = self.db.query(Reservation)
        if status:
            q = q.filter(Reservation.status == status)
        rows = q.order_by(Reservation.id.desc()).all()
        return [r.to_dict() for r in rows]

    def get_reservation(self, res_id: int) -> Optional[dict]:
        res = self.db.query(Reservation).filter_by(id=res_id).first()
        return res.to_dict() if res else None

    def delete_reservation(self, res_id: int) -> bool:
        count = (
            self.db.query(Reservation)
            .filter_by(id=res_id, status="WAITING")
            .delete()
        )
        return count > 0
