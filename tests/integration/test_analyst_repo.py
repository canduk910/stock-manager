"""REQ-ANALYST-06: AnalystRepository 통합 테스트 (PostgreSQL)."""

from datetime import date, timedelta

import pytest

from db.repositories.analyst_repo import AnalystRepository


def _today_iso():
    return date.today().isoformat()


def _days_ago_iso(n):
    return (date.today() - timedelta(days=n)).isoformat()


class TestUpsertReport:
    def test_insert_new_report(self, db_session):
        repo = AnalystRepository(db_session)
        ok = repo.upsert_report(
            code="005930", market="KR", broker="미래에셋",
            target_price=100000, opinion="Buy",
            title="HBM 점유율 확대", pdf_url="https://example.com/a.pdf",
            summary="투자포인트 요약", published_at=_today_iso(),
        )
        db_session.commit()
        assert ok is True

        rows = repo.list_reports("005930", "KR")
        assert len(rows) == 1
        assert rows[0]["broker"] == "미래에셋"
        assert rows[0]["target_price"] == 100000

    def test_upsert_uniqueness(self, db_session):
        """동일 (code, market, broker, published_at, title) 2회 → row 1개."""
        repo = AnalystRepository(db_session)
        pub = _today_iso()
        repo.upsert_report(
            code="005930", market="KR", broker="미래에셋",
            target_price=100000, opinion="Buy",
            title="동일 제목", pdf_url="https://e.com/a.pdf",
            summary="첫번째 요약", published_at=pub,
        )
        db_session.commit()

        # 두 번째 upsert: 동일 키, summary/target_price만 다름
        repo.upsert_report(
            code="005930", market="KR", broker="미래에셋",
            target_price=110000, opinion="Strong Buy",
            title="동일 제목", pdf_url="https://e.com/a.pdf",
            summary="두번째 요약", published_at=pub,
        )
        db_session.commit()

        rows = repo.list_reports("005930", "KR")
        assert len(rows) == 1
        assert rows[0]["summary"] == "두번째 요약"
        assert rows[0]["target_price"] == 110000

    def test_biginteger_target_price(self, db_session):
        """KR 메가캡: target_price=2,500,000,000 저장/조회 정상."""
        repo = AnalystRepository(db_session)
        repo.upsert_report(
            code="005930", market="KR", broker="키움",
            target_price=2_500_000_000, opinion="Buy",
            title="대규모", pdf_url="", summary="",
            published_at=_today_iso(),
        )
        db_session.commit()
        rows = repo.list_reports("005930", "KR")
        assert rows[0]["target_price"] == 2_500_000_000

    def test_published_at_future_replaced_with_fetched_at(self, db_session):
        """미래 날짜 published_at은 fetched_at으로 대체."""
        repo = AnalystRepository(db_session)
        future = (date.today() + timedelta(days=30)).isoformat()
        repo.upsert_report(
            code="005930", market="KR", broker="키움",
            target_price=80000, opinion="Hold",
            title="future title", pdf_url="", summary="",
            published_at=future,
        )
        db_session.commit()
        rows = repo.list_reports("005930", "KR")
        # Repository는 미래 날짜를 오늘로 보정
        assert rows[0]["published_at"] <= _today_iso()


class TestListReports:
    def test_list_reports_latest_first(self, db_session):
        repo = AnalystRepository(db_session)
        repo.upsert_report(code="005930", market="KR", broker="A",
                           target_price=80000, opinion="Buy", title="t1",
                           pdf_url="", summary="", published_at=_days_ago_iso(20))
        repo.upsert_report(code="005930", market="KR", broker="B",
                           target_price=85000, opinion="Buy", title="t2",
                           pdf_url="", summary="", published_at=_days_ago_iso(5))
        repo.upsert_report(code="005930", market="KR", broker="C",
                           target_price=90000, opinion="Buy", title="t3",
                           pdf_url="", summary="", published_at=_days_ago_iso(1))
        db_session.commit()

        rows = repo.list_reports("005930", "KR", limit=10)
        # 최신순 (오늘 가까운 순)
        assert rows[0]["broker"] == "C"
        assert rows[1]["broker"] == "B"
        assert rows[2]["broker"] == "A"

    def test_list_reports_filter_by_market(self, db_session):
        repo = AnalystRepository(db_session)
        repo.upsert_report(code="AAPL", market="US", broker="GS",
                           target_price=None, opinion="Overweight", title="t",
                           pdf_url="", summary="", published_at=_today_iso())
        repo.upsert_report(code="005930", market="KR", broker="키움",
                           target_price=100000, opinion="Buy", title="t",
                           pdf_url="", summary="", published_at=_today_iso())
        db_session.commit()

        kr = repo.list_reports("005930", "KR")
        us = repo.list_reports("AAPL", "US")
        assert len(kr) == 1 and kr[0]["broker"] == "키움"
        assert len(us) == 1 and us[0]["broker"] == "GS"


class TestGetTargetPriceHistory:
    def test_180_day_window(self, db_session):
        repo = AnalystRepository(db_session)
        # 200일 전: 윈도 외부
        repo.upsert_report(code="005930", market="KR", broker="A",
                           target_price=70000, opinion="Buy", title="old",
                           pdf_url="", summary="", published_at=_days_ago_iso(200))
        # 30일 전: 윈도 내부
        repo.upsert_report(code="005930", market="KR", broker="A",
                           target_price=85000, opinion="Buy", title="recent",
                           pdf_url="", summary="", published_at=_days_ago_iso(30))
        db_session.commit()

        hist = repo.get_target_price_history("005930", "KR", days=180)
        assert len(hist) == 1
        assert hist[0]["broker"] == "A"
        assert hist[0]["target_price"] == 85000

    def test_history_includes_all_brokers(self, db_session):
        repo = AnalystRepository(db_session)
        repo.upsert_report(code="005930", market="KR", broker="A",
                           target_price=80000, opinion="Buy", title="a",
                           pdf_url="", summary="", published_at=_days_ago_iso(150))
        repo.upsert_report(code="005930", market="KR", broker="A",
                           target_price=100000, opinion="Buy", title="a2",
                           pdf_url="", summary="", published_at=_days_ago_iso(10))
        repo.upsert_report(code="005930", market="KR", broker="B",
                           target_price=95000, opinion="Hold", title="b",
                           pdf_url="", summary="", published_at=_days_ago_iso(20))
        db_session.commit()

        hist = repo.get_target_price_history("005930", "KR", days=180)
        assert len(hist) == 3
        brokers = {r["broker"] for r in hist}
        assert brokers == {"A", "B"}

    def test_history_returned_keys(self, db_session):
        """반환 dict 형식: broker/date/target_price/opinion."""
        repo = AnalystRepository(db_session)
        repo.upsert_report(code="005930", market="KR", broker="A",
                           target_price=80000, opinion="Buy", title="t",
                           pdf_url="", summary="", published_at=_today_iso())
        db_session.commit()

        hist = repo.get_target_price_history("005930", "KR", days=180)
        assert hist
        for required in ("broker", "date", "target_price", "opinion"):
            assert required in hist[0]
