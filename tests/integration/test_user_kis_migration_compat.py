"""REQ-MIGRATION-01 — 기존 1계좌 사용자 → 라벨 '기본' + is_default=true 보존.

마이그레이션 자체(alembic upgrade)는 컨테이너 부팅 시 자동 실행되므로 본 테스트는
- Repository 레벨에서 단일-row API(upsert/get)가 default 계좌 의미로 보존되는지
- 기존 코드가 호출하던 패턴 (upsert(uid, kis) → get(uid))이 그대로 동작하는지
- 마이그레이션 후 신규 사용자가 첫 계좌 등록 시 자동 is_default=true 인지
- 라벨이 자동으로 '기본' 시드되는지
의 4건을 통합 검증한다.
"""

import base64
import secrets

import pytest


@pytest.fixture(autouse=True)
def _set_master_key(monkeypatch):
    key_b64 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    monkeypatch.setenv("KIS_ENCRYPTION_KEY", key_b64)
    yield


@pytest.fixture
def user_id(db_session):
    from db.repositories.user_repo import UserRepository
    repo = UserRepository(db_session)
    user = repo.create_user("legacy_user", "Legacy User", "hashed", role="user")
    db_session.commit()
    return user["id"]


def _sample_kis():
    return {
        "app_key": "LEGACY_APP_KEY_1234",
        "app_secret": "LEGACY_APP_SECRET_5678",
        "acnt_no": "98765432",
        "acnt_prdt_cd_stk": "01",
        "acnt_prdt_cd_fno": None,
        "hts_id": None,
        "base_url": "https://openapi.koreainvestment.com:9443",
    }


class TestMigrationBackwardCompat:
    def test_legacy_upsert_creates_default_row_with_basic_label(self, db_session, user_id):
        """기존 호출자: upsert(user_id, kis) — 라벨 미지정.
        → label='기본', is_default=true 로 자동 시드되어야 한다.
        """
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        db_session.commit()

        accounts = repo.list_accounts(user_id)
        assert len(accounts) == 1
        a = accounts[0]
        assert a["label"] == "기본"
        assert a["is_default"] is True

    def test_legacy_get_returns_default_account(self, db_session, user_id):
        """기존 호출자: get(user_id) — 라벨 미지정.
        → default 계좌(is_default=true) row 를 반환해야 한다.
        """
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        db_session.commit()

        creds = repo.get(user_id)
        assert creds is not None
        assert creds["app_key"] == "LEGACY_APP_KEY_1234"
        assert creds.get("is_default") is True
        assert creds.get("label") == "기본"

    def test_legacy_upsert_then_new_create_account_coexist(self, db_session, user_id):
        """기존 upsert 로 시드된 '기본' 행 + create_account 로 추가 라벨 공존."""
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())  # '기본'
        kis2 = _sample_kis()
        kis2["label"] = "연금"
        repo.create_account(user_id, kis2)
        db_session.commit()

        accounts = sorted(repo.list_accounts(user_id), key=lambda x: x["label"])
        assert [a["label"] for a in accounts] == ["기본", "연금"]
        # '기본'은 여전히 default
        defaults = [a for a in accounts if a["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["label"] == "기본"

    def test_new_user_first_account_auto_default(self, db_session, user_id):
        """마이그레이션 후 신규 사용자가 create_account 로 첫 계좌 등록 → 자동 is_default=true."""
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        kis = _sample_kis()
        kis["label"] = "주식"
        kis["is_default"] = False  # 명시적으로 false 라도 강제 true
        repo.create_account(user_id, kis)
        db_session.commit()
        a = repo.list_accounts(user_id)[0]
        assert a["is_default"] is True
