"""MarketBoardRepository — 1:1 mapping to stock/market_board_store.py functions."""

from datetime import date

from sqlalchemy.orm import Session

from db.models.market_board import MarketBoardOrder, MarketBoardStock


class MarketBoardRepository:
    def __init__(self, db: Session):
        self.db = db

    def all_items(self, user_id: int) -> list[dict]:
        rows = (
            self.db.query(MarketBoardStock)
            .filter_by(user_id=user_id)
            .order_by(MarketBoardStock.added_date, MarketBoardStock.code)
            .all()
        )
        return [r.to_dict() for r in rows]

    def add_item(self, user_id: int, code: str, name: str, market: str = "KR") -> bool:
        existing = (
            self.db.query(MarketBoardStock)
            .filter_by(user_id=user_id, code=code, market=market)
            .first()
        )
        if existing:
            return False
        self.db.add(MarketBoardStock(
            user_id=user_id,
            code=code,
            market=market,
            name=name,
            added_date=date.today().isoformat(),
        ))
        return True

    def remove_item(self, user_id: int, code: str, market: str = "KR") -> bool:
        count = (
            self.db.query(MarketBoardStock)
            .filter_by(user_id=user_id, code=code, market=market)
            .delete()
        )
        return count > 0

    # ── order management ────────────────────────────────────────

    def get_order(self, user_id: int) -> list[dict]:
        rows = (
            self.db.query(MarketBoardOrder)
            .filter_by(user_id=user_id)
            .order_by(MarketBoardOrder.position)
            .all()
        )
        return [r.to_dict() for r in rows]

    def save_order(self, user_id: int, items: list[dict]) -> None:
        self.db.query(MarketBoardOrder).filter_by(user_id=user_id).delete()
        self.db.add_all([
            MarketBoardOrder(user_id=user_id, code=it["code"], market=it["market"], position=i)
            for i, it in enumerate(items)
        ])
