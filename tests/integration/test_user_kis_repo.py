"""db/repositories/user_kis_repo.py 통합 테스트.

실 DB(PostgreSQL/SQLite)에 user_kis_credentials 테이블 스키마가 존재해야 한다.
암호화 round-trip은 secure_store 단위 테스트에서 검증; 여기선 DB 영속성만.

R1 (KIS 멀티 계좌) — 신규 멀티 row 인터페이스 추가 검증:
- list_accounts / get_by_label / get_default / create_account / update_account /
  delete_account / set_default / mark_validated_label / is_valid_label
- 백워드 호환: 기존 get(uid) / upsert(uid, kis) / delete(uid) 는 default 계좌 의미로 재정의되어 보존.
- 라벨 UNIQUE(user_id, label) — 라벨 중복 시 ConflictError.
- is_default=true 가 사용자당 최대 1개 (자동 승격 가드).
- 마지막 1개 삭제도 허용 (0개 상태 OK).
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


@pytest.fixture
def user_id_b(db_session):
    """두 번째 테스트 사용자 — 사용자 격리 검증용."""
    from db.repositories.user_repo import UserRepository
    repo = UserRepository(db_session)
    user = repo.create_user("kistest_b", "KIS Test B", "hashed", role="user")
    db_session.commit()
    return user["id"]


def _sample_kis(app_key="APP_KEY_REAL_1234", app_secret="APP_SECRET_REAL_5678", label=None, is_default=None):
    kis = {
        "app_key": app_key,
        "app_secret": app_secret,
        "acnt_no": "12345678",
        "acnt_prdt_cd_stk": "01",
        "acnt_prdt_cd_fno": None,
        "hts_id": None,
        "base_url": "https://openapi.koreainvestment.com:9443",
    }
    if label is not None:
        kis["label"] = label
    if is_default is not None:
        kis["is_default"] = is_default
    return kis


# ──────────────────────────────────────────────────────────────────────────────
# 백워드 호환 — 기존 단일-row API
# ──────────────────────────────────────────────────────────────────────────────


class TestUserKisRepoBackwardCompat:
    """기존 get/upsert/delete API 가 default 계좌 의미로 재정의되어 그대로 동작해야 한다."""

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
        # 첫 upsert는 default 계좌로 보존되어야 한다.
        assert creds.get("is_default") is True
        # 백워드 호환 시드는 라벨 '기본'으로 채워진다.
        assert creds.get("label") == "기본"

    def test_get_returns_none_when_missing(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        assert repo.get(user_id) is None

    def test_upsert_updates_existing_default(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        db_session.commit()

        # 같은 user_id 로 upsert → default 계좌가 갱신되어야 한다 (라벨 유지).
        repo.upsert(user_id, _sample_kis(app_key="UPDATED_KEY"))
        db_session.commit()

        creds = repo.get(user_id)
        assert creds["app_key"] == "UPDATED_KEY"
        # 행 수는 1 (라벨 중복 없음)
        assert len(repo.list_accounts(user_id)) == 1

    def test_delete_removes_default_only(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        # 계좌 2개: '기본'(default), '연금'
        repo.create_account(user_id, _sample_kis(label="기본", is_default=True))
        repo.create_account(user_id, _sample_kis(label="연금"))
        db_session.commit()

        # 기존 delete(uid) 는 default 계좌만 삭제 + 다른 계좌가 default 승격.
        assert repo.delete(user_id) is True
        db_session.commit()
        remaining = repo.list_accounts(user_id)
        assert len(remaining) == 1
        assert remaining[0]["label"] == "연금"
        # 승격 확인
        assert remaining[0]["is_default"] is True

    def test_mark_validated_and_is_valid_default(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.upsert(user_id, _sample_kis())
        db_session.commit()

        assert repo.is_valid(user_id) is False
        repo.mark_validated(user_id)
        db_session.commit()
        assert repo.is_valid(user_id) is True


# ──────────────────────────────────────────────────────────────────────────────
# 신규 멀티 계좌 API
# ──────────────────────────────────────────────────────────────────────────────


class TestUserKisMultiAccount:
    def test_create_account_first_is_default(self, db_session, user_id):
        """0계좌 상태에서 첫 등록 → 자동 is_default=true (body의 is_default 무시)."""
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="주식", is_default=False))
        db_session.commit()

        accounts = repo.list_accounts(user_id)
        assert len(accounts) == 1
        assert accounts[0]["label"] == "주식"
        assert accounts[0]["is_default"] is True  # 첫 계좌는 무조건 default

    def test_create_two_accounts_only_one_default(self, db_session, user_id):
        """두 번째 계좌가 is_default=true 로 생성되면 첫 번째는 자동 false 로 강등."""
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="A"))
        repo.create_account(user_id, _sample_kis(label="B", is_default=True))
        db_session.commit()

        accounts = {a["label"]: a for a in repo.list_accounts(user_id)}
        assert accounts["A"]["is_default"] is False
        assert accounts["B"]["is_default"] is True

    def test_label_unique_per_user(self, db_session, user_id):
        """같은 user_id 내 동일 라벨로 create 시 ConflictError."""
        from db.repositories.user_kis_repo import UserKisRepository
        from services.exceptions import ConflictError
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="주식"))
        db_session.commit()
        with pytest.raises(ConflictError):
            repo.create_account(user_id, _sample_kis(label="주식"))
            db_session.commit()

    def test_label_unique_per_user_isolated(self, db_session, user_id, user_id_b):
        """라벨 UNIQUE 는 사용자 범위 — 다른 사용자가 같은 라벨 사용 가능."""
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="주식"))
        repo.create_account(user_id_b, _sample_kis(label="주식"))
        db_session.commit()
        assert len(repo.list_accounts(user_id)) == 1
        assert len(repo.list_accounts(user_id_b)) == 1

    def test_get_by_label(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="주식", app_key="K_STOCK_111122223333"))
        repo.create_account(user_id, _sample_kis(label="연금", app_key="K_PENSION_4444555566"))
        db_session.commit()
        s = repo.get_by_label(user_id, "주식")
        p = repo.get_by_label(user_id, "연금")
        assert s["app_key"] == "K_STOCK_111122223333"
        assert p["app_key"] == "K_PENSION_4444555566"
        assert repo.get_by_label(user_id, "없는라벨") is None

    def test_get_default_returns_default_row(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="A"))
        repo.create_account(user_id, _sample_kis(label="B", is_default=True))
        db_session.commit()
        d = repo.get_default(user_id)
        assert d is not None
        assert d["label"] == "B"

    def test_set_default_switches(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="A"))  # default
        repo.create_account(user_id, _sample_kis(label="B"))
        db_session.commit()

        repo.set_default(user_id, "B")
        db_session.commit()
        accounts = {a["label"]: a for a in repo.list_accounts(user_id)}
        assert accounts["A"]["is_default"] is False
        assert accounts["B"]["is_default"] is True

    def test_set_default_not_found_raises(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        from services.exceptions import NotFoundError
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="A"))
        db_session.commit()
        with pytest.raises(NotFoundError):
            repo.set_default(user_id, "없는라벨")

    def test_update_account_partial(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="주식"))
        db_session.commit()

        # 자격증명만 변경 → validated_at 자동 해제 (재검증 강제)
        repo.mark_validated_label(user_id, "주식")
        db_session.commit()
        assert repo.is_valid_label(user_id, "주식") is True

        repo.update_account(user_id, "주식", {"app_key": "NEW_KEY_VALUE_FOR_RE_VAL"})
        db_session.commit()
        c = repo.get_by_label(user_id, "주식")
        assert c["app_key"] == "NEW_KEY_VALUE_FOR_RE_VAL"
        assert repo.is_valid_label(user_id, "주식") is False  # 재검증 강제

    def test_update_account_rename_label(self, db_session, user_id):
        """라벨 변경. 새 라벨이 다른 row 와 충돌 시 ConflictError."""
        from db.repositories.user_kis_repo import UserKisRepository
        from services.exceptions import ConflictError
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="A"))
        repo.create_account(user_id, _sample_kis(label="B"))
        db_session.commit()

        # 정상 rename
        repo.update_account(user_id, "A", {"label": "C"})
        db_session.commit()
        assert repo.get_by_label(user_id, "A") is None
        assert repo.get_by_label(user_id, "C") is not None

        # 충돌 rename
        with pytest.raises(ConflictError):
            repo.update_account(user_id, "B", {"label": "C"})
            db_session.commit()

    def test_update_account_not_found_raises(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        from services.exceptions import NotFoundError
        repo = UserKisRepository(db_session)
        with pytest.raises(NotFoundError):
            repo.update_account(user_id, "없는라벨", {"app_key": "X"})

    def test_delete_default_auto_promotes(self, db_session, user_id):
        """default 계좌 삭제 시 남은 계좌 중 1개를 자동 default 승격."""
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="A"))  # default
        repo.create_account(user_id, _sample_kis(label="B"))
        repo.create_account(user_id, _sample_kis(label="C"))
        db_session.commit()

        assert repo.delete_account(user_id, "A") is True
        db_session.commit()
        accounts = {a["label"]: a for a in repo.list_accounts(user_id)}
        assert "A" not in accounts
        assert sum(1 for a in accounts.values() if a["is_default"]) == 1

    def test_delete_last_account_allows_zero_state(self, db_session, user_id):
        """마지막 1개 삭제도 허용 (0계좌 상태 OK)."""
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="유일"))
        db_session.commit()

        assert repo.delete_account(user_id, "유일") is True
        db_session.commit()
        assert repo.list_accounts(user_id) == []

    def test_delete_non_default_keeps_default(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="A"))  # default
        repo.create_account(user_id, _sample_kis(label="B"))
        db_session.commit()

        repo.delete_account(user_id, "B")
        db_session.commit()
        remaining = repo.list_accounts(user_id)
        assert len(remaining) == 1
        assert remaining[0]["label"] == "A"
        assert remaining[0]["is_default"] is True

    def test_delete_account_not_found_returns_false(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        assert repo.delete_account(user_id, "없음") is False

    def test_mark_validated_label_independent(self, db_session, user_id):
        """계좌별 validated_at 독립 — A 검증해도 B는 미검증."""
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="A"))
        repo.create_account(user_id, _sample_kis(label="B"))
        db_session.commit()
        repo.mark_validated_label(user_id, "A")
        db_session.commit()
        assert repo.is_valid_label(user_id, "A") is True
        assert repo.is_valid_label(user_id, "B") is False

    def test_is_valid_label_ttl_expired(self, db_session, user_id):
        from db.repositories.user_kis_repo import UserKisRepository
        from db.models.user_kis import UserKisCredentials
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="X"))
        db_session.commit()
        old_ts = (datetime.now(KST) - timedelta(hours=25)).isoformat(timespec="seconds")
        row = db_session.query(UserKisCredentials).filter_by(user_id=user_id, label="X").first()
        row.validated_at = old_ts
        db_session.commit()
        assert repo.is_valid_label(user_id, "X") is False

    def test_list_accounts_returns_masked_or_plain(self, db_session, user_id):
        """list_accounts 는 list[dict] — masked 가 아니라 plain (라우터에서 마스킹)."""
        from db.repositories.user_kis_repo import UserKisRepository
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="A"))
        repo.create_account(user_id, _sample_kis(label="B"))
        db_session.commit()
        accounts = repo.list_accounts(user_id)
        assert len(accounts) == 2
        labels = sorted(a["label"] for a in accounts)
        assert labels == ["A", "B"]
        # plain dict 키 보장
        for a in accounts:
            assert "app_key" in a
            assert "is_default" in a
            assert "validated_at" in a

    def test_secret_stored_encrypted_in_db(self, db_session, user_id):
        """plaintext app_secret 이 DB row 에 그대로 저장되면 안 된다."""
        from db.repositories.user_kis_repo import UserKisRepository
        from sqlalchemy import text
        repo = UserKisRepository(db_session)
        repo.create_account(user_id, _sample_kis(label="X"))
        db_session.commit()

        row = db_session.execute(
            text("SELECT app_secret_enc, app_key_enc FROM user_kis_credentials WHERE user_id = :u AND label = 'X'"),
            {"u": user_id},
        ).fetchone()
        assert row is not None
        assert "APP_SECRET_REAL_5678" not in row[0]
        assert "APP_KEY_REAL_1234" not in row[1]
