"""MarketBoardRepository — 1:1 mapping to stock/market_board_store.py functions."""

from datetime import date

from sqlalchemy.orm import Session

from db.models.market_board import MarketBoardOrder, MarketBoardStock


class MarketBoardRepository:
    def __init__(self, db: Session):
        self.db = db

    def all_items(self) -> list[dict]:
        rows = (
            self.db.query(MarketBoardStock)
            .order_by(MarketBoardStock.added_date, MarketBoardStock.code)
            .all()
        )
        return [r.to_dict() for r in rows]

    def add_item(self, code: str, name: str, market: str = "KR") -> bool:
        existing = (
            self.db.query(MarketBoardStock)
            .filter_by(code=code, market=market)
            .first()
        )
        if existing:
            return False
        self.db.add(MarketBoardStock(
            code=code,
            market=market,
            name=name,
            added_date=date.today().isoformat(),
        ))
        return True

    def remove_item(self, code: str, market: str = "KR") -> bool:
        count = (
            self.db.query(MarketBoardStock)
            .filter_by(code=code, market=market)
            .delete()
        )
        return count > 0

    # ── order management ────────────────────────────────────────

    def get_order(self) -> list[dict]:
        rows = (
            self.db.query(MarketBoardOrder)
            .order_by(MarketBoardOrder.position)
            .all()
        )
        return [r.to_dict() for r in rows]

    def save_order(self, items: list[dict]) -> None:
        self.db.query(MarketBoardOrder).delete()
        self.db.add_all([
            MarketBoardOrder(code=it["code"], market=it["market"], position=i)
            for i, it in enumerate(items)
        ])
