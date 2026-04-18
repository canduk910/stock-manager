"""TaxRepository — 해외주식 양도세 매매내역 + 계산 결과 CRUD."""

from typing import Optional

from sqlalchemy.orm import Session

from db.models.tax import TaxCalculation, TaxTransaction
from db.utils import now_kst_iso


def _now() -> str:
    return now_kst_iso()


class TaxRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── TaxTransaction CRUD ───────────────────────────────────────

    def insert_transaction(
        self,
        source: str,
        symbol: str,
        side: str,
        quantity: int,
        price_foreign: float,
        trade_date: str,
        *,
        source_order_id: int = None,
        symbol_name: str = "",
        currency: str = "USD",
        exchange_rate: float = None,
        price_krw: float = None,
        commission: float = 0,
        commission_krw: float = 0,
        memo: str = "",
    ) -> dict:
        tx = TaxTransaction(
            source=source,
            source_order_id=source_order_id,
            symbol=symbol,
            symbol_name=symbol_name,
            side=side,
            quantity=quantity,
            price_foreign=price_foreign,
            currency=currency,
            exchange_rate=exchange_rate,
            price_krw=price_krw,
            commission=commission,
            commission_krw=commission_krw,
            trade_date=trade_date,
            created_at=_now(),
            memo=memo,
        )
        self.db.add(tx)
        self.db.flush()
        return tx.to_dict()

    def list_transactions(
        self,
        year: int = None,
        symbol: str = None,
        side: str = None,
    ) -> list[dict]:
        q = self.db.query(TaxTransaction)
        if year:
            start = f"{year}-01-01"
            end = f"{year}-12-31"
            q = q.filter(
                TaxTransaction.trade_date >= start,
                TaxTransaction.trade_date <= end,
            )
        if symbol:
            q = q.filter(TaxTransaction.symbol == symbol)
        if side:
            q = q.filter(TaxTransaction.side == side)
        rows = q.order_by(TaxTransaction.trade_date.asc(), TaxTransaction.id.asc()).all()
        return [r.to_dict() for r in rows]

    def get_transaction(self, tx_id: int) -> Optional[dict]:
        tx = self.db.query(TaxTransaction).filter_by(id=tx_id).first()
        return tx.to_dict() if tx else None

    def delete_transaction(self, tx_id: int) -> bool:
        count = self.db.query(TaxTransaction).filter_by(id=tx_id).delete()
        return count > 0

    def get_by_source_order_id(self, order_id: int) -> Optional[dict]:
        """중복 동기화 방지용."""
        tx = (
            self.db.query(TaxTransaction)
            .filter_by(source_order_id=order_id)
            .first()
        )
        return tx.to_dict() if tx else None

    def exists_by_key(self, symbol: str, side: str, trade_date: str, price_foreign: float, quantity: int) -> bool:
        """KIS/수동 입력 중복 체크용."""
        return (
            self.db.query(TaxTransaction)
            .filter_by(
                symbol=symbol,
                side=side,
                trade_date=trade_date,
                price_foreign=price_foreign,
                quantity=quantity,
            )
            .first()
        ) is not None

    # ── TaxCalculation CRUD ───────────────────────────────────────

    def insert_calculation(
        self,
        sell_tx_id: int,
        symbol: str,
        method: str,
        sell_quantity: int,
        sell_price_krw: float,
        acquisition_cost_krw: float,
        commission_total_krw: float,
        gain_loss_krw: float,
        trade_date: str,
        year: int,
        detail_json: str = None,
    ) -> dict:
        calc = TaxCalculation(
            sell_tx_id=sell_tx_id,
            symbol=symbol,
            method=method,
            sell_quantity=sell_quantity,
            sell_price_krw=sell_price_krw,
            acquisition_cost_krw=acquisition_cost_krw,
            commission_total_krw=commission_total_krw,
            gain_loss_krw=gain_loss_krw,
            trade_date=trade_date,
            year=year,
            detail_json=detail_json,
            calculated_at=_now(),
        )
        self.db.add(calc)
        self.db.flush()
        return calc.to_dict()

    def list_calculations(
        self,
        year: int,
        method: str = "FIFO",
        symbol: str = None,
    ) -> list[dict]:
        q = self.db.query(TaxCalculation).filter_by(year=year, method=method)
        if symbol:
            q = q.filter(TaxCalculation.symbol == symbol)
        rows = q.order_by(TaxCalculation.trade_date.asc(), TaxCalculation.id.asc()).all()
        return [r.to_dict() for r in rows]

    def delete_calculations_by_year(self, year: int, method: str) -> int:
        """재계산 전 기존 결과 삭제."""
        count = (
            self.db.query(TaxCalculation)
            .filter_by(year=year, method=method)
            .delete()
        )
        return count
