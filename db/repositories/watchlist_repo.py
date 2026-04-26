"""WatchlistRepository — 1:1 mapping to stock/store.py functions."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from db.models.watchlist import Watchlist, WatchlistOrder


class WatchlistRepository:
    def __init__(self, db: Session):
        self.db = db

    def all_items(self, user_id: int) -> list[dict]:
        rows = (
            self.db.query(Watchlist)
            .filter_by(user_id=user_id)
            .order_by(Watchlist.added_date, Watchlist.code)
            .all()
        )
        return [r.to_dict() for r in rows]

    def get_item(self, user_id: int, code: str, market: str = "KR") -> Optional[dict]:
        row = (
            self.db.query(Watchlist)
            .filter_by(user_id=user_id, code=code, market=market)
            .first()
        )
        return row.to_dict() if row else None

    def add_item(self, user_id: int, code: str, name: str, memo: str = "", market: str = "KR") -> bool:
        """Add item. Return False if already exists."""
        existing = (
            self.db.query(Watchlist)
            .filter_by(user_id=user_id, code=code, market=market)
            .first()
        )
        if existing:
            return False
        self.db.add(Watchlist(
            user_id=user_id,
            code=code,
            market=market,
            name=name,
            added_date=date.today().isoformat(),
            memo=memo,
        ))
        self.db.flush()
        return True

    def remove_item(self, user_id: int, code: str, market: str = "KR") -> bool:
        count = (
            self.db.query(Watchlist)
            .filter_by(user_id=user_id, code=code, market=market)
            .delete()
        )
        return count > 0

    def update_memo(self, user_id: int, code: str, memo: str, market: str = "KR") -> bool:
        count = (
            self.db.query(Watchlist)
            .filter_by(user_id=user_id, code=code, market=market)
            .update({"memo": memo})
        )
        return count > 0

    # ── order management ────────────────────────────────────────

    def get_order(self, user_id: int) -> list[dict]:
        rows = (
            self.db.query(WatchlistOrder)
            .filter_by(user_id=user_id)
            .order_by(WatchlistOrder.position)
            .all()
        )
        return [r.to_dict() for r in rows]

    def save_order(self, user_id: int, items: list[dict]) -> None:
        self.db.query(WatchlistOrder).filter_by(user_id=user_id).delete()
        self.db.add_all([
            WatchlistOrder(user_id=user_id, code=it["code"], market=it["market"], position=i)
            for i, it in enumerate(items)
        ])
