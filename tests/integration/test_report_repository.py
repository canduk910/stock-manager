"""ReportRepository 통합 테스트 — 인메모리 SQLite."""

import pytest
from db.repositories.report_repo import ReportRepository


class TestRecommendationHistory:
    def test_save_and_get(self, db_session):
        repo = ReportRepository(db_session)
        rec_id = repo.save_recommendation(
            market="KR", regime="selective", code="005930", name="삼성전자",
            graham_number=82500, entry_price=62000, safety_grade="A",
            discount_rate=35.0, recommended_qty=80,
            stop_loss=55800, take_profit=82500, risk_reward=2.8,
        )
        db_session.commit()
        assert rec_id > 0

        rec = repo.get_recommendation(rec_id)
        assert rec is not None
        assert rec["code"] == "005930"
        assert rec["safety_grade"] == "A"
        assert rec["status"] == "recommended"

    def test_update_status_to_approved(self, db_session):
        repo = ReportRepository(db_session)
        rec_id = repo.save_recommendation(
            market="KR", regime="selective", code="005930", name="삼성전자",
            entry_price=62000, recommended_qty=80,
        )
        db_session.commit()

        ok = repo.update_recommendation_status(rec_id, "approved")
        db_session.commit()
        assert ok is True

        rec = repo.get_recommendation(rec_id)
        assert rec["status"] == "approved"
        assert rec["approved_at"] is not None

    def test_update_status_to_closed_calculates_pnl(self, db_session):
        repo = ReportRepository(db_session)
        rec_id = repo.save_recommendation(
            market="KR", regime="selective", code="005930", name="삼성전자",
            entry_price=62000, recommended_qty=80,
        )
        db_session.commit()

        ok = repo.update_recommendation_status(rec_id, "closed", closed_price=70000)
        db_session.commit()
        assert ok is True

        rec = repo.get_recommendation(rec_id)
        assert rec["status"] == "closed"
        assert rec["realized_pnl_pct"] == pytest.approx(12.90, abs=0.1)

    def test_list_by_market(self, db_session):
        repo = ReportRepository(db_session)
        repo.save_recommendation(market="KR", regime="selective", code="005930", name="삼성전자", entry_price=62000, recommended_qty=80)
        repo.save_recommendation(market="US", regime="selective", code="AAPL", name="Apple", entry_price=150, recommended_qty=10)
        db_session.commit()

        kr_recs = repo.list_recommendations(market="KR")
        assert len(kr_recs) == 1
        assert kr_recs[0]["code"] == "005930"

        all_recs = repo.list_recommendations()
        assert len(all_recs) == 2

    def test_performance_stats_empty(self, db_session):
        repo = ReportRepository(db_session)
        stats = repo.get_performance_stats()
        assert stats["total"] == 0
        assert stats["win_rate"] == 0

    def test_save_recommendations_batch(self, db_session):
        repo = ReportRepository(db_session)
        items = [
            {"market": "KR", "regime": "selective", "code": "005930",
             "name": "삼성전자", "entry_price": 62000, "recommended_qty": 80},
            {"market": "KR", "regime": "selective", "code": "000660",
             "name": "SK하이닉스", "entry_price": 100000, "recommended_qty": 50},
        ]
        ids = repo.save_recommendations_batch(items)
        db_session.commit()

        assert len(ids) == 2
        assert all(i > 0 for i in ids)

        rec1 = repo.get_recommendation(ids[0])
        assert rec1["code"] == "005930"
        rec2 = repo.get_recommendation(ids[1])
        assert rec2["code"] == "000660"

    def test_update_status_nonexistent(self, db_session):
        repo = ReportRepository(db_session)
        ok = repo.update_recommendation_status(99999, "approved")
        assert ok is False

    def test_update_status_ordered(self, db_session):
        repo = ReportRepository(db_session)
        rec_id = repo.save_recommendation(
            market="KR", regime="selective", code="005930", name="삼성전자",
            entry_price=62000, recommended_qty=80,
        )
        db_session.commit()

        ok = repo.update_recommendation_status(rec_id, "ordered", order_id=42)
        db_session.commit()
        assert ok is True

        rec = repo.get_recommendation(rec_id)
        assert rec["status"] == "ordered"
        assert rec["order_id"] == 42

    def test_performance_stats_with_data(self, db_session):
        repo = ReportRepository(db_session)
        # 2건 추천 → 1건 수익 청산, 1건 손실 청산
        id1 = repo.save_recommendation(
            market="KR", regime="selective", code="005930", name="삼성전자",
            entry_price=62000, recommended_qty=80,
        )
        id2 = repo.save_recommendation(
            market="KR", regime="selective", code="000660", name="SK하이닉스",
            entry_price=100000, recommended_qty=50,
        )
        db_session.commit()

        repo.update_recommendation_status(id1, "closed", closed_price=70000)
        repo.update_recommendation_status(id2, "closed", closed_price=90000)
        db_session.commit()

        stats = repo.get_performance_stats()
        assert stats["total"] == 2
        assert stats["wins"] == 1
        assert stats["losses"] == 1
        assert stats["win_rate"] == 50.0

    def test_performance_stats_by_market(self, db_session):
        repo = ReportRepository(db_session)
        id1 = repo.save_recommendation(
            market="KR", regime="selective", code="005930", name="삼성전자",
            entry_price=62000, recommended_qty=80,
        )
        id2 = repo.save_recommendation(
            market="US", regime="selective", code="AAPL", name="Apple",
            entry_price=150, recommended_qty=10,
        )
        db_session.commit()

        repo.update_recommendation_status(id1, "closed", closed_price=70000)
        repo.update_recommendation_status(id2, "closed", closed_price=160)
        db_session.commit()

        kr_stats = repo.get_performance_stats(market="KR")
        assert kr_stats["total"] == 1

    def test_list_recommendations_by_status(self, db_session):
        repo = ReportRepository(db_session)
        id1 = repo.save_recommendation(
            market="KR", regime="selective", code="005930", name="삼성전자",
            entry_price=62000, recommended_qty=80,
        )
        repo.save_recommendation(
            market="KR", regime="selective", code="000660", name="SK하이닉스",
            entry_price=100000, recommended_qty=50,
        )
        db_session.commit()

        repo.update_recommendation_status(id1, "approved")
        db_session.commit()

        approved = repo.list_recommendations(status="approved")
        assert len(approved) == 1

    def test_count_recommendations(self, db_session):
        repo = ReportRepository(db_session)
        repo.save_recommendation(
            market="KR", regime="selective", code="005930", name="삼성전자",
            entry_price=62000, recommended_qty=80,
        )
        repo.save_recommendation(
            market="US", regime="selective", code="AAPL", name="Apple",
            entry_price=150, recommended_qty=10,
        )
        db_session.commit()

        assert repo.count_recommendations() == 2
        assert repo.count_recommendations(market="KR") == 1


class TestMacroRegimeHistory:
    def test_save_and_get(self, db_session):
        repo = ReportRepository(db_session)
        rid = repo.save_regime("2026-04-13", "selective",
                               buffett_ratio=1.28, vix=22.5, fear_greed_score=45)
        db_session.commit()
        assert rid > 0

        regime = repo.get_regime("2026-04-13")
        assert regime["regime"] == "selective"
        assert regime["vix"] == 22.5

    def test_upsert_same_date(self, db_session):
        repo = ReportRepository(db_session)
        repo.save_regime("2026-04-13", "selective")
        db_session.commit()

        repo.save_regime("2026-04-13", "cautious", vix=30)
        db_session.commit()

        regime = repo.get_regime("2026-04-13")
        assert regime["regime"] == "cautious"

    def test_latest_regime(self, db_session):
        repo = ReportRepository(db_session)
        repo.save_regime("2026-04-12", "accumulation")
        repo.save_regime("2026-04-13", "selective")
        db_session.commit()

        latest = repo.get_latest_regime()
        assert latest["date"] == "2026-04-13"

    def test_latest_regime_empty(self, db_session):
        repo = ReportRepository(db_session)
        assert repo.get_latest_regime() is None

    def test_list_regimes(self, db_session):
        repo = ReportRepository(db_session)
        repo.save_regime("2026-04-11", "accumulation")
        repo.save_regime("2026-04-12", "selective")
        repo.save_regime("2026-04-13", "cautious")
        db_session.commit()

        regimes = repo.list_regimes(limit=2)
        assert len(regimes) == 2
        # 최신순
        assert regimes[0]["date"] == "2026-04-13"
        assert regimes[1]["date"] == "2026-04-12"

    def test_regime_upsert_preserves_fields(self, db_session):
        repo = ReportRepository(db_session)
        repo.save_regime("2026-04-13", "selective", buffett_ratio=1.28, vix=22.5)
        db_session.commit()

        repo.save_regime("2026-04-13", "cautious", vix=30)
        db_session.commit()

        regime = repo.get_regime("2026-04-13")
        assert regime["regime"] == "cautious"
        assert regime["vix"] == 30


class TestDailyReport:
    def test_save_and_get(self, db_session):
        repo = ReportRepository(db_session)
        rid = repo.save_daily_report(
            date="2026-04-13", market="KR",
            report_markdown="# Test Report",
            regime="selective", candidates_count=12, recommended_count=3,
        )
        db_session.commit()
        assert rid > 0

        report = repo.get_daily_report(rid)
        assert report["market"] == "KR"
        assert report["report_markdown"] == "# Test Report"
        assert report["telegram_sent"] is False

    def test_mark_telegram_sent(self, db_session):
        repo = ReportRepository(db_session)
        rid = repo.save_daily_report(
            date="2026-04-13", market="KR", report_markdown="# Test",
        )
        db_session.commit()

        ok = repo.mark_telegram_sent(rid)
        db_session.commit()
        assert ok is True

        report = repo.get_daily_report(rid)
        assert report["telegram_sent"] is True

    def test_list_by_market(self, db_session):
        repo = ReportRepository(db_session)
        repo.save_daily_report(date="2026-04-13", market="KR", report_markdown="KR report")
        repo.save_daily_report(date="2026-04-13", market="US", report_markdown="US report")
        db_session.commit()

        kr = repo.list_daily_reports(market="KR")
        assert len(kr) == 1
        all_reports = repo.list_daily_reports()
        assert len(all_reports) == 2

    def test_mark_telegram_sent_nonexistent(self, db_session):
        repo = ReportRepository(db_session)
        ok = repo.mark_telegram_sent(99999)
        assert ok is False

    def test_get_daily_report_by_date(self, db_session):
        repo = ReportRepository(db_session)
        repo.save_daily_report(date="2026-04-13", market="KR", report_markdown="# KR")
        db_session.commit()

        report = repo.get_daily_report_by_date("2026-04-13", "KR")
        assert report is not None
        assert report["report_markdown"] == "# KR"

        assert repo.get_daily_report_by_date("2026-04-13", "US") is None

    def test_count_daily_reports(self, db_session):
        repo = ReportRepository(db_session)
        repo.save_daily_report(date="2026-04-12", market="KR", report_markdown="r1")
        repo.save_daily_report(date="2026-04-13", market="KR", report_markdown="r2")
        repo.save_daily_report(date="2026-04-13", market="US", report_markdown="r3")
        db_session.commit()

        assert repo.count_daily_reports() == 3
        assert repo.count_daily_reports(market="KR") == 2

    def test_daily_report_with_json(self, db_session):
        repo = ReportRepository(db_session)
        rid = repo.save_daily_report(
            date="2026-04-13", market="KR", report_markdown="# Test",
            report_json={"recommendations": [{"code": "005930"}]},
        )
        db_session.commit()

        report = repo.get_daily_report(rid)
        assert report["report_json"]["recommendations"][0]["code"] == "005930"
