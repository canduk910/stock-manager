"""R7 (KIS 멀티 계좌) — 도메인 정합성 확인 테스트 (코드 변경 없는 항목).

REQ-DOMAIN-04: compute_grade_7point 시그니처 무변경 — 종목 단위 등급은 계좌 무관.
REQ-DOMAIN-05: portfolio_advisor._build_context 가 합산 잔고를 그대로 사용 (변경 0줄).
REQ-DOMAIN-06: _compute_cache_key 잔고 해시 기반 — 합산 잔고 변경 시 자동 캐시 미스.
"""

import inspect


class TestDomain04GradeInvariant:
    def test_compute_grade_7point_signature_unchanged(self):
        """7점 등급 함수는 계좌 인자 없이 종목 정보만 받는다 (도메인 무관)."""
        from services.safety_grade import compute_grade_7point
        sig = inspect.signature(compute_grade_7point)
        # 계좌 관련 인자 부재 확인
        params = list(sig.parameters.keys())
        for forbidden in ("user_id", "account_label", "accounts"):
            assert forbidden not in params, (
                f"compute_grade_7point 에 {forbidden} 인자 추가는 도메인 위반 — "
                "7점 등급은 종목 단위 (REQ-DOMAIN-04)"
            )
        # 기존 인자 명세 보존
        for required in ("metrics", "balance_sheet", "cashflow", "income_stmt"):
            assert required in params


class TestDomain05CashRatioInvariant:
    def test_build_context_uses_balance_data_as_single_source(self):
        """portfolio_advisor._build_context 는 balance_data dict 만 받는다.

        호출자가 합산 잔고를 주입하면 자동으로 합산 cash 비율로 컨텍스트 빌드.
        """
        from services.portfolio_advisor_service import _build_context
        sig = inspect.signature(_build_context)
        params = list(sig.parameters.keys())
        # 단일 인자 (balance_data)
        assert "balance_data" in params
        # 계좌 정보 직접 주입 불필요 — 합산 잔고가 충분 (REQ-DOMAIN-05)
        for forbidden in ("user_id", "account_label", "accounts"):
            assert forbidden not in params, (
                f"_build_context 에 {forbidden} 추가는 합산 잔고 도메인 위반"
            )


class TestDomain06CacheKeyHash:
    def test_compute_cache_key_changes_when_balance_changes(self):
        """잔고 해시가 다르면 캐시 키도 다름 (자동 격리)."""
        from services.portfolio_advisor_service import _compute_cache_key

        balance_a = {
            "total_evaluation": "10000000",
            "stock_list": [{"code": "005930", "quantity": "10"}],
        }
        balance_b = dict(balance_a)
        balance_b["stock_list"] = [{"code": "005930", "quantity": "20"}]

        key_a = _compute_cache_key(balance_a)
        key_b = _compute_cache_key(balance_b)
        assert key_a != key_b, "잔고 변경이 캐시 키에 반영되지 않음 — 멀티 계좌 합산 캐시 격리 깨짐"

    def test_compute_cache_key_user_comment_affects_key(self):
        """동일 잔고 + 다른 user_comment 는 다른 캐시 키."""
        from services.portfolio_advisor_service import _compute_cache_key

        balance = {"total_evaluation": "10000000", "stock_list": []}
        k1 = _compute_cache_key(balance)
        k2 = _compute_cache_key(balance, user_comment="A")
        k3 = _compute_cache_key(balance, user_comment="B")
        assert k1 != k2 != k3
        # 빈 코멘트 vs None 은 동일 취급
        assert k1 == _compute_cache_key(balance, user_comment=None)
