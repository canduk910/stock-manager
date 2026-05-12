"""PortfolioReport user_id 격리 테스트 (RED).

요건:
1. PortfolioReport 모델에 user_id 컬럼이 존재한다.
2. AdvisoryRepository.save_portfolio_report(user_id=..., ...) 가 user_id를 저장한다.
3. AdvisoryRepository.get_portfolio_report_by_id(report_id, user_id=user_id) 가 다른 사용자 보고서는 None을 반환한다.
4. AdvisoryRepository.get_portfolio_report_history(limit, user_id=user_id) 가 본인 보고서만 반환한다.
5. stock.advisory_store.save_portfolio_report / get_portfolio_report_by_id / get_portfolio_report_history adapter 도 user_id 파라미터를 받는다.
6. services.portfolio_advisor_service.get_report_by_id(report_id, user_id=...) 가 다른 사용자 접근 시 NotFoundError를 raise한다.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def session_bound(_test_engine):
    """get_session()이 테스트 PostgreSQL 엔진을 사용하도록 SessionLocal을 reconfigure한다."""
    import db.session as _db_session_mod
    orig_bind = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=_test_engine)
    yield
    _db_session_mod.SessionLocal.configure(bind=orig_bind)


def _seed_user(db_session, user_id: int) -> None:
    """포트폴리오 보고서 FK 제약을 만족시키기 위한 더미 사용자 시드."""
    from db.models.user import User
    from db.utils import now_kst_iso

    existing = db_session.query(User).filter_by(id=user_id).first()
    if existing:
        return
    db_session.add(User(
        id=user_id,
        username=f"user{user_id}",
        name=f"User {user_id}",
        hashed_password="x",
        role="admin" if user_id == 1 else "user",
        created_at=now_kst_iso(),
        updated_at=now_kst_iso(),
    ))
    db_session.flush()


class TestPortfolioReportUserIdColumn:
    """모델/스키마 레벨."""

    def test_model_has_user_id_column(self):
        from db.models.advisory import PortfolioReport
        cols = {c.name for c in PortfolioReport.__table__.columns}
        assert "user_id" in cols, "PortfolioReport 모델에 user_id 컬럼이 있어야 한다"

    def test_user_id_is_nullable(self):
        """기존 행 백필 후에도 NULL 허용 (FK ondelete=SET NULL 대비)."""
        from db.models.advisory import PortfolioReport
        col = PortfolioReport.__table__.columns["user_id"]
        assert col.nullable is True


class TestRepositorySaveAndIsolation:
    """Repository 레벨 격리."""

    def test_save_records_user_id(self, db_session):
        _seed_user(db_session, 42)
        from db.repositories.advisory_repo import AdvisoryRepository
        repo = AdvisoryRepository(db_session)
        rid = repo.save_portfolio_report(
            model="gpt-test",
            report={"diagnosis": {"summary": "u1"}},
            user_id=42,
        )
        db_session.flush()
        row = repo.get_portfolio_report_by_id(rid)
        assert row is not None
        # to_dict() 응답에 user_id가 포함되어 있어야 한다
        assert row.get("user_id") == 42

    def test_get_by_id_other_user_returns_none(self, db_session):
        _seed_user(db_session, 1)
        _seed_user(db_session, 2)
        from db.repositories.advisory_repo import AdvisoryRepository
        repo = AdvisoryRepository(db_session)
        rid = repo.save_portfolio_report(
            model="gpt-test",
            report={"diagnosis": {"summary": "user1"}},
            user_id=1,
        )
        db_session.flush()
        # 본인은 조회 가능
        assert repo.get_portfolio_report_by_id(rid, user_id=1) is not None
        # 다른 사용자 조회 시 None
        assert repo.get_portfolio_report_by_id(rid, user_id=2) is None
        # user_id 미지정(레거시) 시 권한 검증 없이 조회 가능 (백워드)
        assert repo.get_portfolio_report_by_id(rid) is not None

    def test_history_filters_by_user_id(self, db_session):
        _seed_user(db_session, 1)
        _seed_user(db_session, 2)
        from db.repositories.advisory_repo import AdvisoryRepository
        repo = AdvisoryRepository(db_session)
        repo.save_portfolio_report(model="m", report={"k": 1}, user_id=1)
        repo.save_portfolio_report(model="m", report={"k": 2}, user_id=2)
        repo.save_portfolio_report(model="m", report={"k": 3}, user_id=1)
        db_session.flush()
        hist_u1 = repo.get_portfolio_report_history(limit=20, user_id=1)
        hist_u2 = repo.get_portfolio_report_history(limit=20, user_id=2)
        assert len(hist_u1) == 2
        assert len(hist_u2) == 1
        # 백워드: user_id 없으면 모두 반환
        hist_all = repo.get_portfolio_report_history(limit=20)
        assert len(hist_all) == 3


class TestStoreAdapterSignature:
    """stock.advisory_store adapter — 백워드 호환 + user_id 파라미터.

    Store adapter는 get_session() 자체 컨텍스트로 별도 세션을 연다 — 같은 엔진을 공유하지만
    별도 트랜잭션이므로 FK 시드는 commit이 필요하다.
    """

    def test_save_portfolio_report_accepts_user_id(self, db_session, session_bound):
        _seed_user(db_session, 7)
        db_session.commit()  # 별도 세션에서 보이도록 commit
        from stock import advisory_store
        rid = advisory_store.save_portfolio_report(
            model="gpt-test",
            report={"diagnosis": {"summary": "via-adapter"}},
            user_id=7,
        )
        assert isinstance(rid, int) and rid > 0
        row = advisory_store.get_portfolio_report_by_id(rid)
        assert row is not None
        assert row.get("user_id") == 7

    def test_get_history_by_user_id(self, db_session, session_bound):
        _seed_user(db_session, 10)
        _seed_user(db_session, 11)
        db_session.commit()
        from stock import advisory_store
        advisory_store.save_portfolio_report(model="m", report={"k": "a"}, user_id=10)
        advisory_store.save_portfolio_report(model="m", report={"k": "b"}, user_id=11)
        h10 = advisory_store.get_portfolio_report_history(limit=20, user_id=10)
        h11 = advisory_store.get_portfolio_report_history(limit=20, user_id=11)
        codes_10 = [r.get("id") for r in h10]
        codes_11 = [r.get("id") for r in h11]
        assert len(codes_10) == 1
        assert len(codes_11) == 1
        assert set(codes_10).isdisjoint(set(codes_11))


class TestServiceLayerAuthCheck:
    """서비스 레이어: 다른 사용자 보고서 접근 시 NotFoundError(404 매핑)."""

    def test_get_report_by_id_forbids_other_user(self, db_session, session_bound):
        _seed_user(db_session, 100)
        _seed_user(db_session, 200)
        db_session.commit()
        from services import portfolio_advisor_service
        from services.exceptions import NotFoundError
        from stock import advisory_store

        rid = advisory_store.save_portfolio_report(
            model="m",
            report={"diagnosis": {"summary": "owner"}},
            user_id=100,
        )
        # 본인은 조회 가능
        own = portfolio_advisor_service.get_report_by_id(rid, user_id=100)
        assert own is not None and "report" in own
        # 다른 사용자는 NotFoundError
        with pytest.raises(NotFoundError):
            portfolio_advisor_service.get_report_by_id(rid, user_id=200)

    def test_get_report_history_filters_by_user(self, db_session, session_bound):
        _seed_user(db_session, 300)
        _seed_user(db_session, 400)
        db_session.commit()
        from services import portfolio_advisor_service
        from stock import advisory_store

        advisory_store.save_portfolio_report(model="m", report={"k": 1}, user_id=300)
        advisory_store.save_portfolio_report(model="m", report={"k": 2}, user_id=400)
        h300 = portfolio_advisor_service.get_report_history(limit=20, user_id=300)
        h400 = portfolio_advisor_service.get_report_history(limit=20, user_id=400)
        assert len(h300) == 1
        assert len(h400) == 1
