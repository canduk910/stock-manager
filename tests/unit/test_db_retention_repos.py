"""DB retention cleanup — Repository delete_*_before(cutoff) 단위 테스트 (RED).

요건서: `_workspace/dev/db-swirling-mccarthy.md` (RDS 스토리지 비용 절감).
모든 대상 타임스탬프 컬럼은 STRING ISO KST → 문자열 cutoff 비교로 삭제.
cutoff = (now_kst() - timedelta(days=N)).isoformat().

아직 구현되지 않은 메서드:
  - PageViewRepository.delete_before(cutoff)
  - AdminRepository.delete_ai_usage_before(cutoff) / delete_audit_before(cutoff)
  - ReportRepository.delete_recommendations_before(cutoff) / delete_daily_reports_before(cutoff)
  - AdvisoryRepository.delete_reports_before(cutoff) / delete_portfolio_reports_before(cutoff)
  - SemiconductorRepository.delete_signals_before(cutoff) / delete_indicator_values_before(cutoff)

RED 단계이므로 이 파일의 모든 테스트는 현재 AttributeError로 실패해야 정상이다.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from db.utils import now_kst

from db.repositories.page_view_repo import PageViewRepository
from db.repositories.admin_repo import AdminRepository
from db.repositories.report_repo import ReportRepository
from db.repositories.advisory_repo import AdvisoryRepository
from db.repositories.semiconductor_repo import SemiconductorRepository

from db.models.page_view import PageView
from db.models.admin import AiUsageLog, AuditLog
from db.models.report import RecommendationHistory, DailyReport
from db.models.advisory import AdvisoryReport, PortfolioReport, AdvisoryCache
from db.models.semiconductor import Signal, IndicatorValue


# 고정 기준 시각 — 모듈 임포트 시 1회만 평가.
# 테스트 내에서 now_kst()를 매 호출마다 재평가하면 삽입 시각과 cutoff 계산
# 시각 사이에 마이크로초 단위 어긋남이 생겨 "동일 시각" 경계 케이스가
# 깨진다 (dev-lead 지적, 2026-07-19). 모든 timestamp/cutoff는 이 BASE로부터
# 파생시켜 완전히 결정론적으로 만든다.
_BASE = now_kst()


def _iso(dt):
    return dt.isoformat()


def _days_ago(n: int) -> str:
    """BASE 기준 N일 전 KST ISO 문자열 (결정론적 — now_kst() 재호출 없음)."""
    return _iso(_BASE - timedelta(days=n))


# ──────────────────────────────────────────────────────────────────────────
# 1. PageViewRepository.delete_before(cutoff)
# ──────────────────────────────────────────────────────────────────────────

class TestPageViewDeleteBefore:
    def _insert_raw(self, db_session, created_at: str, path: str = "/api/x"):
        row = PageView(
            user_id=1,
            path=path,
            method="GET",
            status_code=200,
            duration_ms=10.0,
            created_at=created_at,
        )
        db_session.add(row)
        db_session.flush()
        return row

    def test_deletes_rows_before_cutoff(self, db_session):
        cutoff = _days_ago(30)
        self._insert_raw(db_session, _days_ago(31))  # 삭제 대상
        self._insert_raw(db_session, _days_ago(40))  # 삭제 대상
        self._insert_raw(db_session, _days_ago(1))   # 보존
        db_session.flush()

        repo = PageViewRepository(db_session)
        deleted = repo.delete_before(cutoff)

        assert deleted == 2
        remaining = db_session.query(PageView).all()
        assert len(remaining) == 1
        assert remaining[0].created_at == _days_ago(1)

    def test_boundary_equal_to_cutoff_is_preserved(self, db_session):
        """cutoff와 정확히 같은 timestamp는 보존 (< 비교, <= 아님)."""
        cutoff = _days_ago(30)
        self._insert_raw(db_session, cutoff)  # 경계값: 보존되어야 함
        db_session.flush()

        repo = PageViewRepository(db_session)
        deleted = repo.delete_before(cutoff)

        assert deleted == 0
        assert db_session.query(PageView).count() == 1

    def test_returns_int_deleted_count(self, db_session):
        self._insert_raw(db_session, _days_ago(100))
        db_session.flush()
        repo = PageViewRepository(db_session)
        deleted = repo.delete_before(_days_ago(30))
        assert isinstance(deleted, int)
        assert deleted == 1

    def test_empty_table_returns_zero(self, db_session):
        repo = PageViewRepository(db_session)
        deleted = repo.delete_before(_days_ago(30))
        assert deleted == 0


# ──────────────────────────────────────────────────────────────────────────
# 2. AdminRepository.delete_ai_usage_before / delete_audit_before
# ──────────────────────────────────────────────────────────────────────────

class TestAdminDeleteAiUsageBefore:
    def _insert_usage(self, db_session, created_at: str):
        row = AiUsageLog(
            user_id=1, date="2026-01-01", service_name="advisory",
            created_at=created_at,
        )
        db_session.add(row)
        db_session.flush()
        return row

    def test_deletes_rows_before_cutoff(self, db_session):
        cutoff = _days_ago(90)
        self._insert_usage(db_session, _days_ago(91))
        self._insert_usage(db_session, _days_ago(200))
        self._insert_usage(db_session, _days_ago(10))
        db_session.flush()

        repo = AdminRepository(db_session)
        deleted = repo.delete_ai_usage_before(cutoff)

        assert deleted == 2
        assert db_session.query(AiUsageLog).count() == 1

    def test_boundary_equal_to_cutoff_is_preserved(self, db_session):
        cutoff = _days_ago(90)
        self._insert_usage(db_session, cutoff)
        db_session.flush()
        repo = AdminRepository(db_session)
        deleted = repo.delete_ai_usage_before(cutoff)
        assert deleted == 0
        assert db_session.query(AiUsageLog).count() == 1

    def test_empty_table_returns_zero(self, db_session):
        repo = AdminRepository(db_session)
        assert repo.delete_ai_usage_before(_days_ago(90)) == 0


class TestAdminDeleteAuditBefore:
    def _insert_audit(self, db_session, created_at: str):
        row = AuditLog(
            actor_id=1, action="set_limit", target_type="ai_limit",
            created_at=created_at,
        )
        db_session.add(row)
        db_session.flush()
        return row

    def test_deletes_rows_before_cutoff(self, db_session):
        cutoff = _days_ago(90)
        self._insert_audit(db_session, _days_ago(91))
        self._insert_audit(db_session, _days_ago(5))
        db_session.flush()

        repo = AdminRepository(db_session)
        deleted = repo.delete_audit_before(cutoff)

        assert deleted == 1
        assert db_session.query(AuditLog).count() == 1

    def test_boundary_equal_to_cutoff_is_preserved(self, db_session):
        cutoff = _days_ago(90)
        self._insert_audit(db_session, cutoff)
        db_session.flush()
        repo = AdminRepository(db_session)
        assert repo.delete_audit_before(cutoff) == 0

    def test_empty_table_returns_zero(self, db_session):
        repo = AdminRepository(db_session)
        assert repo.delete_audit_before(_days_ago(90)) == 0


# ──────────────────────────────────────────────────────────────────────────
# 3. ReportRepository.delete_recommendations_before / delete_daily_reports_before
# ──────────────────────────────────────────────────────────────────────────

class TestReportDeleteRecommendationsBefore:
    def _insert_rec(self, db_session, created_at: str, market="KR", code="005930"):
        row = RecommendationHistory(
            created_at=created_at,
            market=market,
            regime="accumulation",
            code=code,
            name="삼성전자",
            entry_price=70000.0,
            recommended_qty=1,
            status="recommended",
        )
        db_session.add(row)
        db_session.flush()
        return row

    def test_deletes_rows_before_cutoff(self, db_session):
        cutoff = _days_ago(60)
        self._insert_rec(db_session, _days_ago(61))
        self._insert_rec(db_session, _days_ago(120))
        self._insert_rec(db_session, _days_ago(1))
        db_session.flush()

        repo = ReportRepository(db_session)
        deleted = repo.delete_recommendations_before(cutoff)

        assert deleted == 2
        assert db_session.query(RecommendationHistory).count() == 1

    def test_boundary_equal_to_cutoff_is_preserved(self, db_session):
        cutoff = _days_ago(60)
        self._insert_rec(db_session, cutoff)
        db_session.flush()
        repo = ReportRepository(db_session)
        assert repo.delete_recommendations_before(cutoff) == 0

    def test_empty_table_returns_zero(self, db_session):
        repo = ReportRepository(db_session)
        assert repo.delete_recommendations_before(_days_ago(60)) == 0


class TestReportDeleteDailyReportsBefore:
    """daily_reports: market별 최신 1건은 cutoff 이전이어도 보존."""

    def _insert_daily(self, db_session, created_at: str, market="KR", date="2026-01-01"):
        row = DailyReport(
            date=date,
            market=market,
            report_markdown="# report",
            created_at=created_at,
        )
        db_session.add(row)
        db_session.flush()
        return row

    def test_deletes_rows_before_cutoff(self, db_session):
        cutoff = _days_ago(60)
        self._insert_daily(db_session, _days_ago(90), market="KR", date="2026-01-01")
        self._insert_daily(db_session, _days_ago(70), market="KR", date="2026-01-02")
        self._insert_daily(db_session, _days_ago(1), market="KR", date="2026-06-01")
        db_session.flush()

        repo = ReportRepository(db_session)
        deleted = repo.delete_daily_reports_before(cutoff)

        # 90일전, 70일전 모두 cutoff 이전 & market KR의 최신(1일전)이 아니므로 삭제 대상.
        # 그런데 "market별 최신 1건 보존" 룰 확인을 위해 아래 별도 케이스로 분리.
        assert deleted == 2
        assert db_session.query(DailyReport).count() == 1

    def test_preserves_latest_per_market_even_if_all_before_cutoff(self, db_session):
        """그룹(market)별 전부 cutoff 이전인 오래된 행들만 있어도 최신 1건은 잔존."""
        cutoff = _days_ago(60)
        self._insert_daily(db_session, _days_ago(200), market="KR", date="2025-01-01")
        self._insert_daily(db_session, _days_ago(150), market="KR", date="2025-06-01")
        self._insert_daily(db_session, _days_ago(90), market="KR", date="2025-12-01")  # 최신 KR, 보존
        db_session.flush()

        repo = ReportRepository(db_session)
        deleted = repo.delete_daily_reports_before(cutoff)

        assert deleted == 2
        remaining = db_session.query(DailyReport).all()
        assert len(remaining) == 1
        assert remaining[0].date == "2025-12-01"

    def test_preserves_latest_independently_per_market(self, db_session):
        """market이 다르면 그룹이 분리되어 각각 최신 1건 보존."""
        cutoff = _days_ago(60)
        self._insert_daily(db_session, _days_ago(200), market="KR", date="2025-01-01")
        self._insert_daily(db_session, _days_ago(150), market="KR", date="2025-06-01")  # KR 최신, 보존
        self._insert_daily(db_session, _days_ago(300), market="US", date="2024-06-01")  # US 최신(유일), 보존
        db_session.flush()

        repo = ReportRepository(db_session)
        deleted = repo.delete_daily_reports_before(cutoff)

        assert deleted == 1  # KR의 2025-01-01만 삭제
        remaining = db_session.query(DailyReport).order_by(DailyReport.market).all()
        assert len(remaining) == 2
        markets_dates = {(r.market, r.date) for r in remaining}
        assert markets_dates == {("KR", "2025-06-01"), ("US", "2024-06-01")}

    def test_empty_table_returns_zero(self, db_session):
        repo = ReportRepository(db_session)
        assert repo.delete_daily_reports_before(_days_ago(60)) == 0


# ──────────────────────────────────────────────────────────────────────────
# 4. AdvisoryRepository.delete_reports_before / delete_portfolio_reports_before
# ──────────────────────────────────────────────────────────────────────────

class TestAdvisoryDeleteReportsBefore:
    """advisory_reports: (code, market)별 최신 1건 보존."""

    def _insert_report(self, db_session, generated_at: str, code="005930", market="KR", user_id=1):
        row = AdvisoryReport(
            user_id=user_id,
            code=code,
            market=market,
            generated_at=generated_at,
            model="gpt-5.4",
            report={"summary": "test"},
        )
        db_session.add(row)
        db_session.flush()
        return row

    def test_deletes_rows_before_cutoff(self, db_session):
        cutoff = _days_ago(60)
        self._insert_report(db_session, _days_ago(90), code="005930", market="KR")
        self._insert_report(db_session, _days_ago(70), code="005930", market="KR")
        self._insert_report(db_session, _days_ago(1), code="005930", market="KR")
        db_session.flush()

        repo = AdvisoryRepository(db_session)
        deleted = repo.delete_reports_before(cutoff)

        assert deleted == 2
        assert db_session.query(AdvisoryReport).count() == 1

    def test_preserves_latest_per_code_market_even_if_all_before_cutoff(self, db_session):
        cutoff = _days_ago(60)
        self._insert_report(db_session, _days_ago(200), code="005930", market="KR")
        self._insert_report(db_session, _days_ago(150), code="005930", market="KR")
        self._insert_report(db_session, _days_ago(90), code="005930", market="KR")  # 최신, 보존
        db_session.flush()

        repo = AdvisoryRepository(db_session)
        deleted = repo.delete_reports_before(cutoff)

        assert deleted == 2
        remaining = db_session.query(AdvisoryReport).all()
        assert len(remaining) == 1
        assert remaining[0].generated_at == _days_ago(90)

    def test_preserves_latest_independently_per_code_market_pair(self, db_session):
        """(code, market) 조합이 다르면 별도 그룹으로 각각 최신 1건 보존."""
        cutoff = _days_ago(60)
        self._insert_report(db_session, _days_ago(200), code="005930", market="KR")
        self._insert_report(db_session, _days_ago(150), code="005930", market="KR")  # 005930/KR 최신
        self._insert_report(db_session, _days_ago(300), code="AAPL", market="US")  # AAPL/US 최신(유일)
        db_session.flush()

        repo = AdvisoryRepository(db_session)
        deleted = repo.delete_reports_before(cutoff)

        assert deleted == 1
        remaining = db_session.query(AdvisoryReport).all()
        pairs = {(r.code, r.market, r.generated_at) for r in remaining}
        assert pairs == {("005930", "KR", _days_ago(150)), ("AAPL", "US", _days_ago(300))}

    def test_advisory_cache_untouched(self, db_session):
        """advisory_reports 삭제 시 advisory_cache(무관 테이블)는 미터치."""
        cutoff = _days_ago(60)
        self._insert_report(db_session, _days_ago(200), code="005930", market="KR")
        self._insert_report(db_session, _days_ago(150), code="005930", market="KR")
        cache_row = AdvisoryCache(
            code="005930", market="KR", user_id=1,
            updated_at=_days_ago(500),
            fundamental={}, technical={},
        )
        db_session.add(cache_row)
        db_session.flush()

        repo = AdvisoryRepository(db_session)
        repo.delete_reports_before(cutoff)

        assert db_session.query(AdvisoryCache).count() == 1

    def test_empty_table_returns_zero(self, db_session):
        repo = AdvisoryRepository(db_session)
        assert repo.delete_reports_before(_days_ago(60)) == 0


def _seed_user(db_session, user_id: int) -> None:
    """PortfolioReport.user_id FK(users.id) 제약을 만족시키기 위한 더미 사용자 시드.

    tests/unit/test_portfolio_user_id.py의 동일 헬퍼와 같은 패턴.
    """
    from db.models.user import User

    existing = db_session.query(User).filter_by(id=user_id).first()
    if existing:
        return
    db_session.add(User(
        id=user_id,
        username=f"user{user_id}",
        name=f"User {user_id}",
        hashed_password="x",
        role="admin" if user_id == 1 else "user",
        created_at=_days_ago(365),
        updated_at=_days_ago(365),
    ))
    db_session.flush()


class TestAdvisoryDeletePortfolioReportsBefore:
    """portfolio_reports: user별 최신 1건 보존."""

    def _insert_portfolio(self, db_session, generated_at: str, user_id=1):
        _seed_user(db_session, user_id)
        row = PortfolioReport(
            user_id=user_id,
            generated_at=generated_at,
            model="gpt-5.4",
            report={"summary": "test"},
        )
        db_session.add(row)
        db_session.flush()
        return row

    def test_deletes_rows_before_cutoff(self, db_session):
        cutoff = _days_ago(60)
        self._insert_portfolio(db_session, _days_ago(90), user_id=1)
        self._insert_portfolio(db_session, _days_ago(70), user_id=1)
        self._insert_portfolio(db_session, _days_ago(1), user_id=1)
        db_session.flush()

        repo = AdvisoryRepository(db_session)
        deleted = repo.delete_portfolio_reports_before(cutoff)

        assert deleted == 2
        assert db_session.query(PortfolioReport).count() == 1

    def test_preserves_latest_per_user_even_if_all_before_cutoff(self, db_session):
        cutoff = _days_ago(60)
        self._insert_portfolio(db_session, _days_ago(200), user_id=1)
        self._insert_portfolio(db_session, _days_ago(150), user_id=1)
        self._insert_portfolio(db_session, _days_ago(90), user_id=1)  # 최신, 보존
        db_session.flush()

        repo = AdvisoryRepository(db_session)
        deleted = repo.delete_portfolio_reports_before(cutoff)

        assert deleted == 2
        remaining = db_session.query(PortfolioReport).all()
        assert len(remaining) == 1
        assert remaining[0].generated_at == _days_ago(90)

    def test_preserves_latest_independently_per_user(self, db_session):
        cutoff = _days_ago(60)
        self._insert_portfolio(db_session, _days_ago(200), user_id=1)
        self._insert_portfolio(db_session, _days_ago(150), user_id=1)  # user1 최신
        self._insert_portfolio(db_session, _days_ago(300), user_id=2)  # user2 최신(유일)
        db_session.flush()

        repo = AdvisoryRepository(db_session)
        deleted = repo.delete_portfolio_reports_before(cutoff)

        assert deleted == 1
        remaining = db_session.query(PortfolioReport).all()
        pairs = {(r.user_id, r.generated_at) for r in remaining}
        assert pairs == {(1, _days_ago(150)), (2, _days_ago(300))}

    def test_empty_table_returns_zero(self, db_session):
        repo = AdvisoryRepository(db_session)
        assert repo.delete_portfolio_reports_before(_days_ago(60)) == 0


# ──────────────────────────────────────────────────────────────────────────
# 5. SemiconductorRepository.delete_signals_before / delete_indicator_values_before
# ──────────────────────────────────────────────────────────────────────────

class TestSemiconductorDeleteSignalsBefore:
    def _insert_signal(self, db_session, fired_at: str, indicator_name="capex"):
        row = Signal(
            indicator_name=indicator_name,
            fired_at=fired_at,
            level="WARNING",
            message="test signal",
            value_snapshot={},
            ack=False,
        )
        db_session.add(row)
        db_session.flush()
        return row

    def test_deletes_rows_before_cutoff(self, db_session):
        cutoff = _days_ago(90)
        self._insert_signal(db_session, _days_ago(91))
        self._insert_signal(db_session, _days_ago(200))
        self._insert_signal(db_session, _days_ago(5))
        db_session.flush()

        repo = SemiconductorRepository(db_session)
        deleted = repo.delete_signals_before(cutoff)

        assert deleted == 2
        assert db_session.query(Signal).count() == 1

    def test_boundary_equal_to_cutoff_is_preserved(self, db_session):
        cutoff = _days_ago(90)
        self._insert_signal(db_session, cutoff)
        db_session.flush()
        repo = SemiconductorRepository(db_session)
        assert repo.delete_signals_before(cutoff) == 0

    def test_empty_table_returns_zero(self, db_session):
        repo = SemiconductorRepository(db_session)
        assert repo.delete_signals_before(_days_ago(90)) == 0


class TestSemiconductorDeleteIndicatorValuesBefore:
    def _insert_indicator(self, db_session, collected_at: str, indicator_name="capex", observed_at="2026-01-01"):
        row = IndicatorValue(
            indicator_name=indicator_name,
            observed_at=observed_at,
            value=1.23,
            value_meta={},
            source="test",
            collected_at=collected_at,
        )
        db_session.add(row)
        db_session.flush()
        return row

    def test_deletes_rows_before_cutoff(self, db_session):
        cutoff = _days_ago(180)
        self._insert_indicator(db_session, _days_ago(181), observed_at="2025-01-01")
        self._insert_indicator(db_session, _days_ago(400), observed_at="2024-06-01")
        self._insert_indicator(db_session, _days_ago(10), observed_at="2026-06-01")
        db_session.flush()

        repo = SemiconductorRepository(db_session)
        deleted = repo.delete_indicator_values_before(cutoff)

        assert deleted == 2
        assert db_session.query(IndicatorValue).count() == 1

    def test_boundary_equal_to_cutoff_is_preserved(self, db_session):
        cutoff = _days_ago(180)
        self._insert_indicator(db_session, cutoff, observed_at="2025-06-01")
        db_session.flush()
        repo = SemiconductorRepository(db_session)
        assert repo.delete_indicator_values_before(cutoff) == 0

    def test_empty_table_returns_zero(self, db_session):
        repo = SemiconductorRepository(db_session)
        assert repo.delete_indicator_values_before(_days_ago(180)) == 0
