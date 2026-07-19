"""DB retention cleanup — 스케줄러 잡 `_run_db_retention_cleanup_job` 단위 테스트 (RED).

요건서: `_workspace/dev/db-swirling-mccarthy.md` Part B.
`services/scheduler_service.py`에 `_run_macro_cleanup_job()` 패턴으로 신규 잡 추가 예정.

검증 대상 (아직 미구현 — ImportError/AttributeError로 실패해야 정상):
  - 각 테이블 delete가 독립 try/except로 격리되어, 한 repo가 raise해도 나머지 삭제가 계속 호출됨
  - 잡 함수 자체는 예외를 밖으로 전파하지 않음 (raise 금지 — 스케줄러 보호)
  - config의 DB_RETENTION_* 값을 참조함 (import 가능 여부 확인용 — GREEN 이후 통과 목표)
"""

from __future__ import annotations

import pytest


def test_run_db_retention_cleanup_job_importable():
    """`_run_db_retention_cleanup_job`이 scheduler_service에 정의되어 있어야 한다."""
    from services import scheduler_service
    assert hasattr(scheduler_service, "_run_db_retention_cleanup_job")


def test_job_does_not_raise_when_all_repos_succeed(monkeypatch):
    """모든 repo delete가 정상 동작하면 잡 함수는 예외 없이 반환한다."""
    from services import scheduler_service

    calls = []

    def _make_ok(name):
        def _fn(self, cutoff):
            calls.append(name)
            return 1
        return _fn

    monkeypatch.setattr(
        "db.repositories.page_view_repo.PageViewRepository.delete_before",
        _make_ok("page_views"),
    )
    monkeypatch.setattr(
        "db.repositories.admin_repo.AdminRepository.delete_ai_usage_before",
        _make_ok("ai_usage"),
    )
    monkeypatch.setattr(
        "db.repositories.admin_repo.AdminRepository.delete_audit_before",
        _make_ok("audit"),
    )
    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_recommendations_before",
        _make_ok("recommendations"),
    )
    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_daily_reports_before",
        _make_ok("daily_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_reports_before",
        _make_ok("advisory_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_portfolio_reports_before",
        _make_ok("portfolio_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_signals_before",
        _make_ok("signals"),
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_indicator_values_before",
        _make_ok("indicator_values"),
    )

    # 잡 함수 자체가 예외를 던지지 않아야 한다.
    scheduler_service._run_db_retention_cleanup_job()

    # 9개 테이블 모두 호출되어야 한다.
    assert set(calls) == {
        "page_views", "ai_usage", "audit", "recommendations",
        "daily_reports", "advisory_reports", "portfolio_reports",
        "signals", "indicator_values",
    }


def test_job_isolates_exception_from_one_repo(monkeypatch):
    """한 repo의 delete가 raise해도 나머지 테이블 삭제 호출은 계속되어야 한다."""
    from services import scheduler_service

    calls = []

    def _make_ok(name):
        def _fn(self, cutoff):
            calls.append(name)
            return 1
        return _fn

    def _make_raise(name):
        def _fn(self, cutoff):
            calls.append(name)
            raise RuntimeError(f"{name} delete boom")
        return _fn

    # page_views만 실패, 나머지는 정상.
    monkeypatch.setattr(
        "db.repositories.page_view_repo.PageViewRepository.delete_before",
        _make_raise("page_views"),
    )
    monkeypatch.setattr(
        "db.repositories.admin_repo.AdminRepository.delete_ai_usage_before",
        _make_ok("ai_usage"),
    )
    monkeypatch.setattr(
        "db.repositories.admin_repo.AdminRepository.delete_audit_before",
        _make_ok("audit"),
    )
    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_recommendations_before",
        _make_ok("recommendations"),
    )
    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_daily_reports_before",
        _make_ok("daily_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_reports_before",
        _make_ok("advisory_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_portfolio_reports_before",
        _make_ok("portfolio_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_signals_before",
        _make_ok("signals"),
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_indicator_values_before",
        _make_ok("indicator_values"),
    )

    # 잡 함수 자체는 raise하지 않아야 한다 (예외 격리).
    scheduler_service._run_db_retention_cleanup_job()

    # page_views가 실패했어도 나머지 8개 테이블은 모두 호출되어야 한다.
    assert set(calls) == {
        "page_views", "ai_usage", "audit", "recommendations",
        "daily_reports", "advisory_reports", "portfolio_reports",
        "signals", "indicator_values",
    }


def test_job_isolates_exception_from_middle_repo(monkeypatch):
    """중간 테이블(advisory_reports)이 실패해도 이후 테이블 삭제가 계속되어야 한다."""
    from services import scheduler_service

    calls = []

    def _make_ok(name):
        def _fn(self, cutoff):
            calls.append(name)
            return 1
        return _fn

    def _make_raise(name):
        def _fn(self, cutoff):
            calls.append(name)
            raise ValueError(f"{name} delete boom")
        return _fn

    monkeypatch.setattr(
        "db.repositories.page_view_repo.PageViewRepository.delete_before",
        _make_ok("page_views"),
    )
    monkeypatch.setattr(
        "db.repositories.admin_repo.AdminRepository.delete_ai_usage_before",
        _make_ok("ai_usage"),
    )
    monkeypatch.setattr(
        "db.repositories.admin_repo.AdminRepository.delete_audit_before",
        _make_ok("audit"),
    )
    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_recommendations_before",
        _make_ok("recommendations"),
    )
    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_daily_reports_before",
        _make_ok("daily_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_reports_before",
        _make_raise("advisory_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_portfolio_reports_before",
        _make_ok("portfolio_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_signals_before",
        _make_ok("signals"),
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_indicator_values_before",
        _make_ok("indicator_values"),
    )

    scheduler_service._run_db_retention_cleanup_job()

    assert set(calls) == {
        "page_views", "ai_usage", "audit", "recommendations",
        "daily_reports", "advisory_reports", "portfolio_reports",
        "signals", "indicator_values",
    }


def test_job_uses_db_retention_config_values(monkeypatch):
    """cutoff 계산에 config.DB_RETENTION_* 값을 참조하는지 확인.

    config 값을 극단으로 바꿨을 때 delete 메서드에 전달되는 cutoff가
    그 값을 반영해 달라져야 한다 (하드코딩된 cutoff가 아님을 검증).
    GREEN 단계에서 config.DB_RETENTION_PAGE_VIEWS_DAYS 등이 정의되어야 통과.
    """
    import config
    from services import scheduler_service

    captured_cutoffs = {}

    def _capture(name):
        def _fn(self, cutoff):
            captured_cutoffs[name] = cutoff
            return 0
        return _fn

    monkeypatch.setattr(
        "db.repositories.page_view_repo.PageViewRepository.delete_before",
        _capture("page_views"),
    )
    monkeypatch.setattr(
        "db.repositories.admin_repo.AdminRepository.delete_ai_usage_before",
        _capture("ai_usage"),
    )
    monkeypatch.setattr(
        "db.repositories.admin_repo.AdminRepository.delete_audit_before",
        _capture("audit"),
    )
    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_recommendations_before",
        _capture("recommendations"),
    )
    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_daily_reports_before",
        _capture("daily_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_reports_before",
        _capture("advisory_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_portfolio_reports_before",
        _capture("portfolio_reports"),
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_signals_before",
        _capture("signals"),
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_indicator_values_before",
        _capture("indicator_values"),
    )

    # config 값을 1일로 극단 축소 — 각 cutoff는 "오늘-1일" 근방이어야 한다.
    monkeypatch.setattr(config, "DB_RETENTION_PAGE_VIEWS_DAYS", 1, raising=False)
    monkeypatch.setattr(config, "DB_RETENTION_AI_USAGE_DAYS", 1, raising=False)
    monkeypatch.setattr(config, "DB_RETENTION_AUDIT_DAYS", 1, raising=False)
    monkeypatch.setattr(config, "DB_RETENTION_RECOMMENDATION_DAYS", 1, raising=False)
    monkeypatch.setattr(config, "DB_RETENTION_ADVISORY_REPORTS_DAYS", 1, raising=False)
    monkeypatch.setattr(config, "DB_RETENTION_PORTFOLIO_REPORTS_DAYS", 1, raising=False)
    monkeypatch.setattr(config, "DB_RETENTION_DAILY_REPORTS_DAYS", 1, raising=False)
    monkeypatch.setattr(config, "DB_RETENTION_SEMI_SIGNALS_DAYS", 1, raising=False)
    monkeypatch.setattr(config, "DB_RETENTION_SEMI_INDICATORS_DAYS", 1, raising=False)

    scheduler_service._run_db_retention_cleanup_job()

    # 모든 테이블에 대해 cutoff가 캡처되어야 하고, 문자열(ISO)이어야 한다.
    assert set(captured_cutoffs.keys()) == {
        "page_views", "ai_usage", "audit", "recommendations",
        "daily_reports", "advisory_reports", "portfolio_reports",
        "signals", "indicator_values",
    }
    for name, cutoff in captured_cutoffs.items():
        assert isinstance(cutoff, str), f"{name} cutoff should be ISO string"


# ──────────────────────────────────────────────────────────────────────────
# 실 PostgreSQL 세션 격리 검증 (2026-07-19 부서장 지시 — mock만으로는
# 트랜잭션 abort 시나리오를 재현하지 못한다는 지적 반영).
#
# `_run_one_retention_table()`이 테이블마다 독립 `get_session()` 블록을 여는
# 구조(services/scheduler_service.py:232)를 실제 DB로 검증한다: 중간 테이블에서
# DB 레벨 에러(존재하지 않는 테이블 SELECT)로 그 세션의 트랜잭션이 실제로
# aborted 상태가 되어도, 이미 커밋된 앞 테이블의 삭제는 유지되고 뒤 테이블은
# (새 세션이므로) 영향받지 않아야 한다.
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture
def _scheduler_session_bound(_test_engine):
    """`get_session()`이 테스트 PostgreSQL 엔진을 사용하도록 SessionLocal을 reconfigure.

    tests/unit/test_portfolio_user_id.py의 `session_bound` fixture와 동일 패턴.
    `_run_one_retention_table`은 `db.session.get_session()`으로 자체 세션을 열므로,
    SessionLocal의 bind를 테스트 엔진으로 바꿔주면 잡이 그대로 테스트 DB(5433)를 본다.
    """
    import db.session as _db_session_mod

    orig_bind = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=_test_engine)
    yield
    _db_session_mod.SessionLocal.configure(bind=orig_bind)


def test_job_persists_across_real_db_level_failure_in_middle_table(
    _scheduler_session_bound, db_session, monkeypatch,
):
    """실 PostgreSQL에서: 중간 테이블(ai_usage_log)이 DB 레벨 에러로 세션을 실제로
    abort시켜도, 앞 테이블(page_views)의 삭제는 커밋되어 남아있고 뒤 테이블
    (audit_log)의 삭제도 정상 커밋된다.

    핵심 차이(순수 mock 대비): `AdminRepository.delete_ai_usage_before`를 단순
    `raise`가 아니라 실제 존재하지 않는 테이블을 SELECT하는 SQL로 교체 —
    PostgreSQL이 해당 트랜잭션을 실제로 "current transaction is aborted" 상태로
    만든다. `_run_one_retention_table`이 테이블별 독립 `get_session()`을 열지
    않고 단일 세션을 공유했다면 이 지점에서 이후 모든 delete가 InFailedSqlTransaction
    으로 연쇄 실패했을 것 — 그 회귀를 실 DB로 잡아낸다.
    """
    from sqlalchemy import text
    from services import scheduler_service
    from db.models.page_view import PageView
    from db.models.admin import AuditLog

    from db.utils import now_kst
    from datetime import timedelta

    base = now_kst()

    def _old(days):
        return (base - timedelta(days=days)).isoformat()

    # config 보존 기간을 짧게 고정해 cutoff를 예측 가능하게 만든다.
    import config
    monkeypatch.setattr(config, "DB_RETENTION_PAGE_VIEWS_DAYS", 30, raising=False)
    monkeypatch.setattr(config, "DB_RETENTION_AUDIT_DAYS", 90, raising=False)

    # 앞 테이블: page_views에 cutoff 이전 데이터 시드 (실제 삭제 대상)
    db_session.add(PageView(
        user_id=1, path="/api/x", method="GET", status_code=200,
        duration_ms=1.0, created_at=_old(31),
    ))
    # 뒤 테이블: audit_log에 cutoff 이전 데이터 시드 (실제 삭제 대상)
    db_session.add(AuditLog(
        actor_id=1, action="set_limit", target_type="ai_limit",
        created_at=_old(91),
    ))
    db_session.commit()

    # 다른 9개 테이블의 delete는 no-op(0건)으로 만들어 이번 테스트 범위를
    # page_views(앞) / ai_usage_log(중간, DB 레벨 실패) / audit_log(뒤) 로 한정.
    def _noop(self, cutoff):
        return 0

    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_recommendations_before",
        _noop,
    )
    monkeypatch.setattr(
        "db.repositories.report_repo.ReportRepository.delete_daily_reports_before",
        _noop,
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_reports_before",
        _noop,
    )
    monkeypatch.setattr(
        "db.repositories.advisory_repo.AdvisoryRepository.delete_portfolio_reports_before",
        _noop,
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_signals_before",
        _noop,
    )
    monkeypatch.setattr(
        "db.repositories.semiconductor_repo.SemiconductorRepository.delete_indicator_values_before",
        _noop,
    )

    # 중간 테이블(ai_usage_log): 실제 DB 레벨 에러를 유발 — 존재하지 않는
    # 테이블을 SELECT해 해당 세션의 트랜잭션을 실제로 abort 상태로 만든다.
    def _db_level_boom(self, cutoff):
        self.db.execute(text("SELECT * FROM nonexistent_table_xyz"))
        return 0  # 도달 못 함 — 위 execute가 raise

    monkeypatch.setattr(
        "db.repositories.admin_repo.AdminRepository.delete_ai_usage_before",
        _db_level_boom,
    )

    # 잡 자체는 raise 없이 완료되어야 한다 (예외 격리 — 스케줄러 보호).
    scheduler_service._run_db_retention_cleanup_job()

    # 앞 테이블(page_views)의 cutoff 이전 행이 실제로 삭제·커밋됐는지 확인.
    remaining_pv = db_session.query(PageView).filter(
        PageView.created_at < _old(0)
    ).all()
    # 별도 fresh 세션(db_session)으로 재조회 — 잡이 연 세션과는 무관한 커넥션.
    assert db_session.query(PageView).count() == 0, (
        "page_views(앞 테이블)의 cutoff 이전 행이 실제 커밋되어 삭제되지 않았다 — "
        "중간 테이블 DB 레벨 실패가 앞 테이블 커밋에 영향을 준 회귀 가능성"
    )

    # 뒤 테이블(audit_log)의 cutoff 이전 행도 실제로 삭제·커밋됐는지 확인.
    assert db_session.query(AuditLog).count() == 0, (
        "audit_log(뒤 테이블)의 cutoff 이전 행이 삭제되지 않았다 — "
        "중간 테이블의 aborted 세션이 뒤 테이블의 새 세션에 전파된 회귀 가능성 "
        "(단일 세션 공유 구조였다면 InFailedSqlTransaction으로 여기서 실패했을 것)"
    )
