"""MacroRepository — 1:1 mapping to stock/macro_store.py functions."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models.macro import MacroGptCache
from db.utils import now_kst


def _today_kst() -> str:
    return now_kst().strftime("%Y-%m-%d")


class MacroRepository:
    def __init__(self, db: Session):
        self.db = db

    def cleanup_old(self, days: int = 30) -> int:
        """N일 이전 캐시 삭제. 삭제 건수 반환."""
        cutoff = (now_kst() - timedelta(days=days)).strftime("%Y-%m-%d")
        return self.db.query(MacroGptCache).filter(
            MacroGptCache.date_kst < cutoff
        ).delete()

    def delete_before_today(self) -> int:
        """오늘(KST) 이전 모든 매크로 GPT 캐시 삭제 — 일일 자정 cleanup 정책.

        2026-05-09: 매크로 정보는 당일치만 유지. 자정 KST 이후 어제 이전
        모든 row 삭제 (`scheduler_service._run_macro_cleanup_job` 호출).
        삭제 건수 반환.
        """
        today = _today_kst()
        return self.db.query(MacroGptCache).filter(
            MacroGptCache.date_kst < today
        ).delete()

    def get_today(self, category: str) -> Optional[any]:
        today = _today_kst()
        row = (
            self.db.query(MacroGptCache)
            .filter_by(category=category, date_kst=today)
            .first()
        )
        if not row:
            return None
        return row.result

    def delete_today(self, category: str) -> int:
        """오늘자 캐시 강제 삭제. 외부 키 갱신/장애 복구 시 사용."""
        today = _today_kst()
        return self.db.query(MacroGptCache).filter_by(
            category=category, date_kst=today,
        ).delete()

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
