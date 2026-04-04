"""MacroRepository — 1:1 mapping to stock/macro_store.py functions."""

from __future__ import annotations

import random
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models.macro import MacroGptCache
from stock.db_base import now_kst


def _today_kst() -> str:
    return now_kst().strftime("%Y-%m-%d")


class MacroRepository:
    def __init__(self, db: Session):
        self.db = db

    def _maybe_cleanup(self) -> None:
        """~5% probability: delete entries older than 30 days."""
        if random.random() < 0.05:
            cutoff = (now_kst() - timedelta(days=30)).strftime("%Y-%m-%d")
            self.db.query(MacroGptCache).filter(
                MacroGptCache.date_kst < cutoff
            ).delete()

    def get_today(self, category: str) -> Optional[any]:
        today = _today_kst()
        self._maybe_cleanup()
        row = (
            self.db.query(MacroGptCache)
            .filter_by(category=category, date_kst=today)
            .first()
        )
        if not row:
            return None
        return row.result

    def save_today(self, category: str, result) -> None:
        today = _today_kst()
        now = now_kst().isoformat()
        row = (
            self.db.query(MacroGptCache)
            .filter_by(category=category, date_kst=today)
            .first()
        )
        if not row:
            row = MacroGptCache(category=category, date_kst=today)
            self.db.add(row)
        row.result = result
        row.created_at = now
