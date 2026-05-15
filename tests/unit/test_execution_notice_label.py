"""R6 (KIS 멀티 계좌) — H0STCNI0 체결통보의 account_label 매칭 LRU.

REQ-ORDER-03:
- KIS H0STCNI0 응답의 ACNT_NO 8자리 → user_kis_credentials.acnt_no 복호화 매칭 → label.
- 매칭 캐시: (user_id, decrypted_acnt_no) → label 인메모리 LRU 100.
- 매칭 실패 시 label=None + 경고 로그.
- /ws/execution-notice 메시지 payload 에 account_label 필드 추가.
"""

import base64
import secrets

import pytest


@pytest.fixture(autouse=True)
def _set_master_key(monkeypatch):
    key_b64 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    monkeypatch.setenv("KIS_ENCRYPTION_KEY", key_b64)


@pytest.fixture(autouse=True)
def _bind_session(_test_engine):
    import db.session as _db_session_mod
    orig = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=_test_engine)
    yield
    _db_session_mod.SessionLocal.configure(bind=orig)


@pytest.fixture
def user_id(db_session):
    from db.repositories.user_repo import UserRepository
    repo = UserRepository(db_session)
    u = repo.create_user("execnotice_user", "Test", "h", role="user")
    db_session.commit()
    return u["id"]


def _seed_accounts(db_session, user_id):
    from db.repositories.user_kis_repo import UserKisRepository
    repo = UserKisRepository(db_session)
    repo.create_account(user_id, {
        "label": "주식", "is_default": True,
        "app_key": "K1_111122223333", "app_secret": "S1_44445555",
        "acnt_no": "11112222", "acnt_prdt_cd_stk": "01",
    })
    repo.create_account(user_id, {
        "label": "연금",
        "app_key": "K2_777788889999", "app_secret": "S2_00001111",
        "acnt_no": "33334444", "acnt_prdt_cd_stk": "29",
    })
    db_session.commit()


class TestAccountLabelMatcher:
    def test_match_label_by_acnt_no(self, db_session, user_id):
        _seed_accounts(db_session, user_id)
        from services.account_label_matcher import match_account_label

        # 8자리 평문 ACNT_NO → 라벨 매칭
        assert match_account_label(user_id, "11112222") == "주식"
        assert match_account_label(user_id, "33334444") == "연금"
        # 매칭 실패
        assert match_account_label(user_id, "99999999") is None

    def test_lru_cache_repeated_lookup(self, db_session, user_id):
        """동일 (user_id, acnt_no) 반복 조회 시 LRU 캐시 hit."""
        _seed_accounts(db_session, user_id)
        from services import account_label_matcher

        # 캐시 초기화
        account_label_matcher.invalidate_cache()
        assert account_label_matcher.match_account_label(user_id, "11112222") == "주식"
        # 두 번째 호출 — 캐시 hit (DB 재조회 없어야 함; 검증은 cache_info)
        assert account_label_matcher.match_account_label(user_id, "11112222") == "주식"

        info = account_label_matcher.cache_stats()
        assert info["hits"] >= 1

    def test_invalidate_clears_cache(self, db_session, user_id):
        _seed_accounts(db_session, user_id)
        from services import account_label_matcher

        account_label_matcher.match_account_label(user_id, "11112222")
        account_label_matcher.invalidate_cache(user_id)
        info = account_label_matcher.cache_stats()
        # invalidate 후 size 가 0 으로 떨어졌거나 user_id 항목이 사라졌음
        assert info["current_size"] == 0 or all(k[0] != user_id for k in info["keys"])
