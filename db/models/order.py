"""Order + Reservation models."""

from sqlalchemy import Column, Float, Index, Integer, String, Text, text

from db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String)
    org_no = Column(String)
    symbol = Column(String, nullable=False)
    symbol_name = Column(String)
    market = Column(String, nullable=False, default="KR")
    side = Column(String, nullable=False)
    order_type = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    filled_price = Column(Float)
    filled_quantity = Column(Integer, default=0, server_default=text("0"))
    status = Column(String, nullable=False, default="PLACED", server_default=text("'PLACED'"))
    currency = Column(String, default="KRW", server_default=text("'KRW'"))
    memo = Column(Text, default="", server_default=text("''"))
    placed_at = Column(String, nullable=False)
    filled_at = Column(String)
    updated_at = Column(String, nullable=False)
    kis_response = Column(Text)

    __table_args__ = (
        Index("idx_orders_status", "status"),
        Index("idx_orders_order_no_market", "order_no", "market"),
        Index("idx_orders_symbol_market", "symbol", "market", "placed_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_no": self.order_no,
            "org_no": self.org_no,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "market": self.market,
            "side": self.side,
            "order_type": self.order_type,
            "price": self.price,
            "quantity": self.quantity,
            "filled_price": self.filled_price,
            "filled_quantity": self.filled_quantity,
            "status": self.status,
            "currency": self.currency,
            "memo": self.memo,
            "placed_at": self.placed_at,
            "filled_at": self.filled_at,
            "updated_at": self.updated_at,
            "kis_response": self.kis_response,
        }


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    symbol_name = Column(String)
    market = Column(String, nullable=False, default="KR", server_default=text("'KR'"))
    side = Column(String, nullable=False)
    order_type = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    condition_type = Column(String, nullable=False)
    condition_value = Column(String, nullable=False)
    status = Column(String, nullable=False, default="WAITING", server_default=text("'WAITING'"))
    result_order_no = Column(String)
    memo = Column(Text, default="", server_default=text("''"))
    created_at = Column(String, nullable=False)
    triggered_at = Column(String)
    updated_at = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "market": self.market,
            "side": self.side,
            "order_type": self.order_type,
            "price": self.price,
            "quantity": self.quantity,
            "condition_type": self.condition_type,
            "condition_value": self.condition_value,
            "status": self.status,
            "result_order_no": self.result_order_no,
            "memo": self.memo,
            "created_at": self.created_at,
            "triggered_at": self.triggered_at,
            "updated_at": self.updated_at,
        }
