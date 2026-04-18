"""MacroRepository 통합 테스트 — 인메모리 SQLite."""

import pytest
from unittest.mock import patch
from datetime import datetime
from db.repositories.macro_repo import MacroRepository


def _patch_today(date_str):
    """_today_kst()를 고정 날짜로 패치."""
    dt = datetime.fromisoformat(date_str + "T12:00:00+09:00")
    return patch("db.repositories.macro_repo.now_kst", return_value=dt)


class TestMacroSaveAndGet:
    def test_save_and_get_today(self, db_session):
        repo = MacroRepository(db_session)
        with _patch_today("2026-04-19"):
            repo.save_today("news_kr", {"items": [{"title": "Test"}]})
            db_session.commit()

            result = repo.get_today("news_kr")
        assert result is not None
        assert result["items"][0]["title"] == "Test"

    def test_get_today_empty(self, db_session):
        repo = MacroRepository(db_session)
        with _patch_today("2026-04-19"):
            result = repo.get_today("nonexistent")
        assert result is None

    def test_save_upsert(self, db_session):
        """같은 카테고리+날짜에 재저장하면 덮어쓰기."""
        repo = MacroRepository(db_session)
        with _patch_today("2026-04-19"):
            repo.save_today("news_kr", {"v": 1})
            db_session.commit()

            repo.save_today("news_kr", {"v": 2})
            db_session.commit()

            result = repo.get_today("news_kr")
        assert result["v"] == 2

    def test_different_dates(self, db_session):
        """다른 날짜의 데이터는 독립."""
        repo = MacroRepository(db_session)
        with _patch_today("2026-04-18"):
            repo.save_today("news_kr", {"v": 1})
            db_session.commit()

        with _patch_today("2026-04-19"):
            repo.save_today("news_kr", {"v": 2})
            db_session.commit()

            # 오늘 것만 조회
            result = repo.get_today("news_kr")
        assert result["v"] == 2


class TestMacroCleanup:
    def test_cleanup_old(self, db_session):
        repo = MacroRepository(db_session)

        # 40일 전 데이터 직접 삽입
        from db.models.macro import MacroGptCache
        old_row = MacroGptCache(
            category="old_cat",
            date_kst="2026-03-01",
            result={"old": True},
            created_at="2026-03-01T12:00:00",
        )
        db_session.add(old_row)
        db_session.commit()

        with _patch_today("2026-04-19"):
            deleted = repo.cleanup_old(days=30)
        db_session.commit()

        assert deleted == 1

    def test_cleanup_keeps_recent(self, db_session):
        repo = MacroRepository(db_session)
        with _patch_today("2026-04-19"):
            repo.save_today("news_kr", {"recent": True})
            db_session.commit()

            deleted = repo.cleanup_old(days=30)
        db_session.commit()

        assert deleted == 0
        with _patch_today("2026-04-19"):
            assert repo.get_today("news_kr") is not None
