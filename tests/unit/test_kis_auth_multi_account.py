"""R2 (KIS 멀티 계좌) — routers/_kis_auth.py 멀티 계좌 분기 단위 테스트.

REQ-AUTH-01: get_kis_credentials(user_id, account_label) 시그니처 확장
REQ-AUTH-02: _token_cache 키 = (user_id, account_label) 격리
REQ-AUTH-03: _current_account_label ContextVar (라우터 진입부 set, 서비스 fallback)
"""

import base64
import secrets
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _set_master_key(monkeypatch):
    key_b64 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    monkeypatch.setenv("KIS_ENCRYPTION_KEY", key_b64)
    yield


@pytest.fixture(autouse=True)
def _bind_session(_test_engine):
    """get_session() 이 테스트 PostgreSQL 을 쓰도록 SessionLocal reconfigure."""
    import db.session as _db_session_mod
    orig_bind = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=_test_engine)
    yield
    _db_session_mod.SessionLocal.configure(bind=orig_bind)


@pytest.fixture
def user_id(db_session):
    from db.repositories.user_repo import UserRepository
    repo = UserRepository(db_session)
    user = repo.create_user("kisauthtest", "Auth Test", "hashed", role="user")
    db_session.commit()
    return user["id"]


def _seed_two_accounts(db_session, user_id):
    """A=default(app_key=AAA_KEY...), B=non-default(app_key=BBB_KEY...) 시드."""
    from db.repositories.user_kis_repo import UserKisRepository
    repo = UserKisRepository(db_session)
    repo.create_account(user_id, {
        "label": "주식", "app_key": "AAA_KEY_111122223333",
        "app_secret": "AAA_SECRET_4444555566",
        "acnt_no": "11112222", "acnt_prdt_cd_stk": "01",
        "acnt_prdt_cd_fno": None, "is_default": True,
    })
    repo.create_account(user_id, {
        "label": "연금", "app_key": "BBB_KEY_777788889999",
        "app_secret": "BBB_SECRET_00001111",
        "acnt_no": "33334444", "acnt_prdt_cd_stk": "29",
        "acnt_prdt_cd_fno": "03",
    })
    # 검증 시각 부여 (TTL 유효성 검사 회피)
    repo.mark_validated_label(user_id, "주식")
    repo.mark_validated_label(user_id, "연금")
    db_session.commit()


class TestGetKisCredentialsMultiAccount:
    """REQ-AUTH-01: get_kis_credentials(user_id, account_label) 분기."""

    def test_user_id_label_default(self, db_session, user_id):
        """user_id 만 주면 default 계좌(주식) 자격증명 반환."""
        _seed_two_accounts(db_session, user_id)
        from routers import _kis_auth as kauth

        app_key, app_secret, acnt_no, prdt_stk, prdt_fno = kauth.get_kis_credentials(user_id=user_id)
        assert app_key == "AAA_KEY_111122223333"
        assert acnt_no == "11112222"
        assert prdt_stk == "01"
        assert prdt_fno == ""  # default 계좌 fno 없음 → 빈 문자열

    def test_user_id_with_label_specific(self, db_session, user_id):
        """user_id + account_label='연금' → 연금 계좌 자격증명 반환."""
        _seed_two_accounts(db_session, user_id)
        from routers import _kis_auth as kauth

        app_key, app_secret, acnt_no, prdt_stk, prdt_fno = kauth.get_kis_credentials(
            user_id=user_id, account_label="연금",
        )
        assert app_key == "BBB_KEY_777788889999"
        assert acnt_no == "33334444"
        assert prdt_stk == "29"
        assert prdt_fno == "03"

    def test_user_id_with_nonexistent_label_raises_not_found(self, db_session, user_id):
        """라벨 없으면 NotFoundError(404)."""
        _seed_two_accounts(db_session, user_id)
        from routers import _kis_auth as kauth
        from services.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            kauth.get_kis_credentials(user_id=user_id, account_label="없는라벨")

    def test_no_user_id_uses_env_keys(self, db_session, monkeypatch):
        """user_id=None 이면 운영자 .env 키 반환 (기존 동작 보존)."""
        from routers import _kis_auth as kauth
        # 캐시 초기화
        kauth.clear_token_cache()
        kauth._current_user_id.set(None)
        kauth._current_account_label.set(None) if hasattr(kauth, "_current_account_label") else None

        monkeypatch.setattr(kauth, "KIS_APP_KEY", "ENV_KEY_xxxx")
        monkeypatch.setattr(kauth, "KIS_APP_SECRET", "ENV_SECRET_yyyy")
        monkeypatch.setattr(kauth, "KIS_ACNT_NO", "ENV_ACNT_zz")
        monkeypatch.setattr(kauth, "KIS_ACNT_PRDT_CD_STK", "01")
        monkeypatch.setattr(kauth, "KIS_ACNT_PRDT_CD_FNO", "03")

        app_key, _, acnt_no, prdt_stk, prdt_fno = kauth.get_kis_credentials()
        assert app_key == "ENV_KEY_xxxx"
        assert acnt_no == "ENV_ACNT_zz"
        assert prdt_stk == "01"
        assert prdt_fno == "03"


class TestTokenCacheKeyIsolation:
    """REQ-AUTH-02: (user_id, account_label) 별 토큰 캐시 격리."""

    def test_token_cache_key_per_label(self, db_session, user_id):
        _seed_two_accounts(db_session, user_id)
        from routers import _kis_auth as kauth
        kauth.clear_token_cache()

        # KIS 토큰 발급 mock — 호출마다 다른 토큰 반환.
        call_count = {"n": 0}
        def fake_post(url, headers=None, data=None, timeout=10):
            call_count["n"] += 1
            res = MagicMock()
            res.status_code = 200
            res.json.return_value = {"access_token": f"TOK_{call_count['n']}", "expires_in": 3600}
            return res

        with patch("routers._kis_auth.requests.post", side_effect=fake_post):
            t_a = kauth.get_access_token(user_id=user_id, account_label="주식")
            t_b = kauth.get_access_token(user_id=user_id, account_label="연금")
            # 같은 (user_id, label) 재호출 → 캐시 hit (POST 호출 안 늘어남)
            t_a2 = kauth.get_access_token(user_id=user_id, account_label="주식")

        assert t_a != t_b, "계좌별 토큰이 격리되지 않았다 (캐시 키 충돌)"
        assert t_a == t_a2, "동일 (user_id, label) 재호출 시 캐시 hit 이어야 한다"
        assert call_count["n"] == 2, f"토큰 발급 POST 가 {call_count['n']} 회 (기대: 2회)"

    def test_clear_token_cache_per_label(self, db_session, user_id):
        _seed_two_accounts(db_session, user_id)
        from routers import _kis_auth as kauth
        kauth.clear_token_cache()

        call_count = {"n": 0}
        def fake_post(url, headers=None, data=None, timeout=10):
            call_count["n"] += 1
            res = MagicMock()
            res.status_code = 200
            res.json.return_value = {"access_token": f"TOK_{call_count['n']}", "expires_in": 3600}
            return res

        with patch("routers._kis_auth.requests.post", side_effect=fake_post):
            kauth.get_access_token(user_id=user_id, account_label="주식")
            kauth.get_access_token(user_id=user_id, account_label="연금")

            # 주식 계좌만 invalidate
            kauth.clear_token_cache(user_id=user_id, account_label="주식")
            # 주식 재호출 → 신규 POST, 연금 재호출 → 캐시 hit
            kauth.get_access_token(user_id=user_id, account_label="주식")
            kauth.get_access_token(user_id=user_id, account_label="연금")

        assert call_count["n"] == 3, f"토큰 발급 POST {call_count['n']} (기대: 3 — 주식2 + 연금1)"


class TestContextVarLabel:
    """REQ-AUTH-03: _current_account_label ContextVar 전파."""

    def test_explicit_arg_takes_precedence_over_context(self, db_session, user_id):
        _seed_two_accounts(db_session, user_id)
        from routers import _kis_auth as kauth

        kauth.set_current_user_id(user_id)
        kauth.set_current_account_label("주식")
        # explicit account_label='연금' 가 ContextVar('주식') 보다 우선
        app_key, *_ = kauth.get_kis_credentials(account_label="연금")
        assert app_key == "BBB_KEY_777788889999"

    def test_context_var_fallback_when_no_explicit(self, db_session, user_id):
        _seed_two_accounts(db_session, user_id)
        from routers import _kis_auth as kauth

        kauth.set_current_user_id(user_id)
        kauth.set_current_account_label("연금")
        # explicit 인자 없음 → ContextVar('연금') fallback
        app_key, *_ = kauth.get_kis_credentials()
        assert app_key == "BBB_KEY_777788889999"

    def test_context_var_none_falls_to_default(self, db_session, user_id):
        _seed_two_accounts(db_session, user_id)
        from routers import _kis_auth as kauth

        kauth.set_current_user_id(user_id)
        kauth.set_current_account_label(None)
        app_key, *_ = kauth.get_kis_credentials()
        assert app_key == "AAA_KEY_111122223333"  # default(주식)

    def test_context_isolated_per_async_task(self, db_session, user_id):
        """ContextVar 는 asyncio Task 단위 격리 — 동시 요청 2건 간섭 없음."""
        import asyncio
        _seed_two_accounts(db_session, user_id)
        from routers import _kis_auth as kauth

        async def get_for_label(label):
            kauth.set_current_user_id(user_id)
            kauth.set_current_account_label(label)
            await asyncio.sleep(0)  # 컨텍스트 스위치
            app_key, *_ = kauth.get_kis_credentials()
            return app_key

        async def run_both():
            return await asyncio.gather(
                get_for_label("주식"),
                get_for_label("연금"),
            )

        results = asyncio.run(run_both())
        assert sorted(results) == sorted(["AAA_KEY_111122223333", "BBB_KEY_777788889999"])
