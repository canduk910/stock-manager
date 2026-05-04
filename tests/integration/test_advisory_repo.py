"""AdvisoryRepository 통합 테스트 — 인메모리 SQLite."""

import pytest
from db.repositories.advisory_repo import AdvisoryRepository


class TestAdvisoryStock:
    def test_add_stock(self, db_session):
        repo = AdvisoryRepository(db_session)
        ok = repo.add_stock(1, "005930", "KR", "삼성전자")
        db_session.commit()
        assert ok is True

        stock = repo.get_stock(1, "005930", "KR")
        assert stock is not None
        assert stock["name"] == "삼성전자"
        assert stock["code"] == "005930"

    def test_add_stock_duplicate(self, db_session):
        repo = AdvisoryRepository(db_session)
        repo.add_stock(1, "005930", "KR", "삼성전자")
        db_session.commit()

        ok = repo.add_stock(1, "005930", "KR", "삼성전자")
        assert ok is False

    def test_add_stock_case_insensitive(self, db_session):
        """code/market은 upper()로 저장."""
        repo = AdvisoryRepository(db_session)
        repo.add_stock(1, "aapl", "us", "Apple")
        db_session.commit()

        stock = repo.get_stock(1, "AAPL", "US")
        assert stock is not None
        assert stock["code"] == "AAPL"
        assert stock["market"] == "US"

    def test_remove_stock(self, db_session):
        repo = AdvisoryRepository(db_session)
        repo.add_stock(1, "005930", "KR", "삼성전자")
        db_session.commit()

        ok = repo.remove_stock(1, "005930", "KR")
        db_session.commit()
        assert ok is True

        stock = repo.get_stock(1, "005930", "KR")
        assert stock is None

    def test_remove_stock_nonexistent(self, db_session):
        repo = AdvisoryRepository(db_session)
        ok = repo.remove_stock(1, "999999", "KR")
        assert ok is False

    def test_all_stocks(self, db_session):
        repo = AdvisoryRepository(db_session)
        repo.add_stock(1, "005930", "KR", "삼성전자")
        repo.add_stock(1, "AAPL", "US", "Apple")
        db_session.commit()

        stocks = repo.all_stocks(1)
        assert len(stocks) == 2

    def test_get_stock_case_insensitive(self, db_session):
        repo = AdvisoryRepository(db_session)
        repo.add_stock(1, "AAPL", "US", "Apple")
        db_session.commit()

        # 소문자로 조회
        stock = repo.get_stock(1, "aapl", "us")
        assert stock is not None
        assert stock["code"] == "AAPL"


class TestAdvisoryCache:
    def test_save_cache(self, db_session):
        repo = AdvisoryRepository(db_session)
        fundamental = {"revenue": 100000, "net_income": 20000}
        technical = {"rsi": 55.0, "macd_cross": "golden"}

        repo.save_cache(1, "005930", "KR", fundamental, technical)
        db_session.commit()

        cache = repo.get_cache(1, "005930", "KR")
        assert cache is not None
        assert cache["fundamental"]["revenue"] == 100000
        assert cache["technical"]["rsi"] == 55.0

    def test_save_cache_update(self, db_session):
        repo = AdvisoryRepository(db_session)
        repo.save_cache(1, "005930", "KR", {"rev": 100}, {"rsi": 50})
        db_session.commit()
        first_cache = repo.get_cache(1, "005930", "KR")
        first_updated = first_cache["updated_at"]

        # 업데이트
        repo.save_cache(1, "005930", "KR", {"rev": 200}, {"rsi": 60})
        db_session.commit()

        cache = repo.get_cache(1, "005930", "KR")
        assert cache["fundamental"]["rev"] == 200
        assert cache["technical"]["rsi"] == 60

    def test_get_cache_nonexistent(self, db_session):
        repo = AdvisoryRepository(db_session)
        cache = repo.get_cache(1, "NOEXIST", "KR")
        assert cache is None

    def test_save_cache_with_strategy_signals(self, db_session):
        repo = AdvisoryRepository(db_session)
        signals = {"backtest": {"cagr": 12.5}}
        repo.save_cache(1, "005930", "KR", {}, {}, strategy_signals=signals)
        db_session.commit()

        cache = repo.get_cache(1, "005930", "KR")
        assert cache is not None


class TestAdvisoryReport:
    def test_save_report(self, db_session):
        repo = AdvisoryRepository(db_session)
        report_data = {"opinion": "매수", "target_price": 80000}
        rid = repo.save_report(1, 
            code="005930", market="KR", model="gpt-5.4",
            report=report_data, grade="A", grade_score=24,
            composite_score=75.0, regime_alignment=85.0,
            schema_version="v2",
        )
        db_session.commit()
        assert rid > 0

        report = repo.get_report_by_id(rid)
        assert report is not None
        assert report["report"]["opinion"] == "매수"
        assert report["grade"] == "A"
        assert report["grade_score"] == 24

    def test_get_latest_report(self, db_session):
        repo = AdvisoryRepository(db_session)
        repo.save_report(1, "005930", "KR", "gpt-5.4", {"v": 1})
        repo.save_report(1, "005930", "KR", "gpt-5.4", {"v": 2})
        db_session.commit()

        latest = repo.get_latest_report(1, "005930", "KR")
        assert latest["report"]["v"] == 2

    def test_get_latest_report_nonexistent(self, db_session):
        repo = AdvisoryRepository(db_session)
        assert repo.get_latest_report(1, "NOEXIST", "KR") is None

    def test_list_reports(self, db_session):
        repo = AdvisoryRepository(db_session)
        for i in range(5):
            repo.save_report(1, "005930", "KR", "gpt-5.4", {"v": i})
        db_session.commit()

        reports = repo.get_report_history(1, "005930", "KR", limit=3)
        assert len(reports) == 3
        # 최신순
        assert reports[0]["id"] > reports[1]["id"]

    def test_report_summary_dict(self, db_session):
        repo = AdvisoryRepository(db_session)
        repo.save_report(1, "005930", "KR", "gpt-5.4", {"big": "data"},
                         grade="B+", grade_score=20, schema_version="v2")
        db_session.commit()

        history = repo.get_report_history(1, "005930", "KR")
        assert len(history) == 1
        # summary에는 report 본문이 없어야 함
        assert "report" not in history[0]
        assert history[0]["grade"] == "B+"


class TestPortfolioReport:
    def test_save_portfolio_report(self, db_session):
        repo = AdvisoryRepository(db_session)
        rid = repo.save_portfolio_report(
            model="gpt-5.4",
            report={"summary": "test"},
            weighted_grade_avg=3.5,
            regime="selective",
        )
        db_session.commit()
        assert rid > 0

        report = repo.get_portfolio_report_by_id(rid)
        assert report is not None
        assert report["regime"] == "selective"

    def test_get_latest_portfolio_report(self, db_session):
        repo = AdvisoryRepository(db_session)
        repo.save_portfolio_report("gpt-5.4", {"v": 1})
        repo.save_portfolio_report("gpt-5.4", {"v": 2})
        db_session.commit()

        latest = repo.get_latest_portfolio_report()
        assert latest["report"]["v"] == 2

    def test_get_latest_portfolio_report_empty(self, db_session):
        repo = AdvisoryRepository(db_session)
        assert repo.get_latest_portfolio_report() is None

    def test_portfolio_report_history(self, db_session):
        repo = AdvisoryRepository(db_session)
        for i in range(5):
            repo.save_portfolio_report("gpt-5.4", {"v": i})
        db_session.commit()

        history = repo.get_portfolio_report_history(limit=3)
        assert len(history) == 3
