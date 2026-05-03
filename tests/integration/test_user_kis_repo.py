"""db/repositories/user_kis_repo.py 통합 테스트.

실 DB(PostgreSQL/SQLite)에 user_kis_credentials 테이블 스키마가 존재해야 한다.
암호화 round-trip은 secure_store 단위 테스트에서 검증; 여기선 DB 영속성만.
"""

import base64
import secrets
from datetime import datetime, timedelta, timezone

import pytest

KST = timezone(timedelta(hours=9))


@pytest.fixture(autouse=True)
def _set_master_key(monkeypatch):
    key_b64 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    monkeypatch.setenv("KIS_ENCRYPTION_KEY", key_b64)
    yield


@pytest.fixture
def user_id(db_session):
    """테스트용 사용자 1명 생성."""
    from db.repositories.user_repo import UserRepository
    repo = UserRepository(db_session)
    user = repo.create_user("kistest", "KIS Test", "hashed", role="user")
    db_session.commit()
    return user["id"]


def _sample_kis(app_key="APP_KEY_REAL_1234", app_secret="APP_SECRET_REAL_5678"):
    return {
        "app_key": app_key,
        "app_secret": app_secret,
        "acnt_no": "12345678",
        "acnt_prdt_cd_stk": "01",
        "acnt_prdt_cd_fno": None,
        "hts_id": None,
        "base_url": "https://openapi.koreainvestment.com:9443",
    }


class TestUserKisRepo:
    def test_upsert_and_get_round_trip(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        db_session.commit()

        creds = repo.get(user_id)
        assert creds is not None
        assert creds["app_key"] == "APP_KEY_REAL_1234"
        assert creds["app_secret"] == "APP_SECRET_REAL_5678"
        assert creds["acnt_no"] == "12345678"
        assert creds["acnt_prdt_cd_stk"] == "01"
        assert creds["base_url"] == "https://openapi.koreainvestment.com:9443"

    def test_get_returns_none_when_missing(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        assert repo.get(user_id) is None

    def test_upsert_updates_existing(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        db_session.commit()

        repo.upsert(user_id, _sample_kis(app_key="UPDATED_KEY"))
        db_session.commit()

        creds = repo.get(user_id)
        assert creds["app_key"] == "UPDATED_KEY"

    def test_delete_removes_record(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        db_session.commit()

        repo.delete(user_id)
        db_session.commit()
        assert repo.get(user_id) is None

    def test_secret_stored_encrypted_in_db(self, db_session, user_id):
        """plaintext app_secret이 DB row에 그대로 저장되면 안 된다."""
        from db.repositories.user_kis_repo import UserKisRepository
        from sqlalchemy import text

        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        db_session.commit()

        row = db_session.execute(
            text("SELECT app_secret_enc, app_key_enc FROM user_kis_credentials WHERE user_id = :u"),
            {"u": user_id},
        ).fetchone()
        assert row is not None
        # plaintext 가 그대로 저장돼있으면 안 된다
        assert "APP_SECRET_REAL_5678" not in row[0]
        assert "APP_KEY_REAL_1234" not in row[1]

    def test_mark_validated_and_is_valid(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        db_session.commit()

        # 검증 전: is_valid False
        assert repo.is_valid(user_id) is False

        # 검증 후
        repo.mark_validated(user_id)
        db_session.commit()
        assert repo.is_valid(user_id) is True

    def test_is_valid_false_when_ttl_expired(self, db_session, user_id, monkeypatch):
        from db.repositories.user_kis_repo import UserKisRepository
        from db.models.user_kis import UserKisCredentials

        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        # 25시간 전으로 직접 설정 (TTL 24h 가정)
        old_ts = (datetime.now(KST) - timedelta(hours=25)).isoformat(timespec="seconds")
        row = db_session.query(UserKisCredentials).filter_by(user_id=user_id).first()
        row.validated_at = old_ts
        db_session.commit()

        assert repo.is_valid(user_id) is False
