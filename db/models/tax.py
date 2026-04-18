"""TaxTransaction + TaxCalculation models — 해외주식 양도소득세."""

from sqlalchemy import Column, Float, Index, Integer, String, Text, text

from db.base import Base


class TaxTransaction(Base):
    """해외주식 양도세 대상 매매 기록 (원장)."""

    __tablename__ = "tax_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)  # KIS | LOCAL | MANUAL
    source_order_id = Column(Integer)  # orders.id (KIS/LOCAL 소스일 때)
    symbol = Column(String, nullable=False)
    symbol_name = Column(String)
    side = Column(String, nullable=False)  # buy | sell
    quantity = Column(Integer, nullable=False)
    price_foreign = Column(Float, nullable=False)  # 외화 체결단가
    currency = Column(String, nullable=False, default="USD", server_default=text("'USD'"))
    exchange_rate = Column(Float)  # 체결일 기준 환율 (KRW/외화)
    price_krw = Column(Float)  # price_foreign * exchange_rate (원화 환산 단가)
    commission = Column(Float, default=0, server_default=text("0"))  # 외화 수수료
    commission_krw = Column(Float, default=0, server_default=text("0"))  # 원화 수수료
    trade_date = Column(String, nullable=False)  # YYYY-MM-DD
    created_at = Column(String, nullable=False)
    memo = Column(Text, default="", server_default=text("''"))

    __table_args__ = (
        Index("idx_tax_tx_symbol_date", "symbol", "trade_date"),
        Index("idx_tax_tx_year", "trade_date"),
        Index("idx_tax_tx_source", "source", "source_order_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "source_order_id": self.source_order_id,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "side": self.side,
            "quantity": self.quantity,
            "price_foreign": self.price_foreign,
            "currency": self.currency,
            "exchange_rate": self.exchange_rate,
            "price_krw": self.price_krw,
            "commission": self.commission,
            "commission_krw": self.commission_krw,
            "trade_date": self.trade_date,
            "created_at": self.created_at,
            "memo": self.memo,
        }


class TaxCalculation(Base):
    """매도 건별 양도차익 계산 결과 (FIFO/AVG)."""

    __tablename__ = "tax_calculations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sell_tx_id = Column(Integer, nullable=False)  # tax_transactions.id (매도 건)
    symbol = Column(String, nullable=False)
    method = Column(String, nullable=False)  # FIFO | AVG
    sell_quantity = Column(Integer, nullable=False)
    sell_price_krw = Column(Float, nullable=False)  # 매도가 총액 (원화)
    acquisition_cost_krw = Column(Float, nullable=False)  # 취득가 총액 (원화)
    commission_total_krw = Column(Float, default=0, server_default=text("0"))
    gain_loss_krw = Column(Float, nullable=False)  # 양도차익
    trade_date = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    detail_json = Column(Text)  # FIFO 소진 상세 JSON
    calculated_at = Column(String, nullable=False)

    __table_args__ = (
        Index("idx_tax_calc_year_method", "year", "method"),
        Index("idx_tax_calc_symbol", "symbol", "year"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sell_tx_id": self.sell_tx_id,
            "symbol": self.symbol,
            "method": self.method,
            "sell_quantity": self.sell_quantity,
            "sell_price_krw": self.sell_price_krw,
            "acquisition_cost_krw": self.acquisition_cost_krw,
            "commission_total_krw": self.commission_total_krw,
            "gain_loss_krw": self.gain_loss_krw,
            "trade_date": self.trade_date,
            "year": self.year,
            "detail_json": self.detail_json,
            "calculated_at": self.calculated_at,
        }


class TaxFifoLot(Base):
    """FIFO 매도→매수 매핑 (1매도 = N매수 lot)."""

    __tablename__ = "tax_fifo_lots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calculation_id = Column(Integer, nullable=False)  # tax_calculations.id
    sell_tx_id = Column(Integer, nullable=False)       # 매도 거래 ID
    buy_tx_id = Column(Integer)                         # 매수 거래 ID (None=부족)
    symbol = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)           # 소진 수량
    buy_price_krw = Column(Float)                       # 매수 원화 단가
    buy_trade_date = Column(String)                     # 매수일
    cost_krw = Column(Float)                            # 취득원가 (원화)
    warning = Column(String)                            # "매수 내역 부족" 등

    __table_args__ = (
        Index("idx_fifo_lot_calc", "calculation_id"),
        Index("idx_fifo_lot_sell", "sell_tx_id"),
        Index("idx_fifo_lot_buy", "buy_tx_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "calculation_id": self.calculation_id,
            "sell_tx_id": self.sell_tx_id,
            "buy_tx_id": self.buy_tx_id,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "buy_price_krw": self.buy_price_krw,
            "buy_trade_date": self.buy_trade_date,
            "cost_krw": self.cost_krw,
            "warning": self.warning,
        }
