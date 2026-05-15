"""REQ-SECTOR-01/02 — 업종 판별 헬퍼 + sector_tier 응답 전파.

도메인 결정 D-2, D-7 (요건서 _workspace/dev/01_requirements.md).
우선순위: insurance → bank_holding → securities → general.

회계과목 패턴 기반 자동 감지 (DART induty_code 별도 호출 회피).
"""
from __future__ import annotations

import pytest


# ── 픽스처: 종목별 DART items 미니멀 모킹 ───────────────────────────────────

def _mk_item(account_nm: str, sj_div: str = "IS") -> dict:
    """최소 형태의 DART API 응답 row."""
    return {
        "account_nm": account_nm,
        "sj_div": sj_div,
        "thstrm_amount": "1000000",
    }


@pytest.fixture
def items_bank_holding_086790() -> list[dict]:
    """086790 하나금융지주 패턴: 이자수익 + 수수료수익 (보험수익 일부) 동시 존재.

    실측: 매출액/영업수익 단독 부재 → bank_holding.
    """
    return [
        _mk_item("이자수익", "IS"),
        _mk_item("수수료수익", "IS"),
        _mk_item("보험수익", "IS"),
        _mk_item("영업이익", "IS"),
        _mk_item("당기순이익", "IS"),
        _mk_item("자산총계", "BS"),
    ]


@pytest.fixture
def items_bank_holding_316140() -> list[dict]:
    """316140 우리금융지주: 보험수익 없음 (이자+수수료만)."""
    return [
        _mk_item("이자수익", "IS"),
        _mk_item("수수료수익", "IS"),
        _mk_item("영업이익", "IS"),
        _mk_item("자산총계", "BS"),
    ]


@pytest.fixture
def items_insurance_005830() -> list[dict]:
    """005830 DB손해보험: 보험계약부채 BS 존재 → insurance."""
    return [
        _mk_item("보험영업수익", "IS"),
        _mk_item("영업이익", "IS"),
        _mk_item("보험계약부채", "BS"),
        _mk_item("자산총계", "BS"),
    ]


@pytest.fixture
def items_securities_006800() -> list[dict]:
    """006800 미래에셋증권: 영업수익 단일 + 이자수익(소액) — bank_holding보다 우선순위 낮춰 securities."""
    return [
        _mk_item("영업수익", "IS"),
        _mk_item("이자수익", "IS"),  # 증권사도 이자수익 있지만 수수료수익은 없거나 작음
        _mk_item("영업이익", "IS"),
        _mk_item("자산총계", "BS"),
    ]


@pytest.fixture
def items_general_005930() -> list[dict]:
    """005930 삼성전자: 매출액 단독 — general."""
    return [
        _mk_item("매출액", "IS"),
        _mk_item("매출원가", "IS"),
        _mk_item("매출총이익", "IS"),
        _mk_item("영업이익", "IS"),
        _mk_item("당기순이익", "IS"),
        _mk_item("자산총계", "BS"),
        _mk_item("유동자산", "BS"),
    ]


@pytest.fixture
def items_general_kakao_035720() -> list[dict]:
    """035720 카카오: 영업수익 사용 + 이자수익(소액) — 그러나 매출원가/매출총이익 존재 → general 회귀.

    핵심 회귀 가드: bank_holding 오발동 방지 (수수료수익 부재 체크) +
    securities 오발동 방지 (일반 손익 구조 매출원가/매출총이익 존재로 차단).
    실제 카카오 2024 IS는 영업수익(7.87조) + 매출원가/매출총이익 보고 (일반 IT 구조).
    """
    return [
        _mk_item("영업수익", "IS"),
        _mk_item("이자수익", "IS"),  # 소액 — 수수료수익 없으면 bank_holding 아님
        _mk_item("매출원가", "IS"),    # 일반 손익 구조 → securities 차단
        _mk_item("매출총이익", "IS"),
        _mk_item("영업이익", "IS"),
        _mk_item("당기순이익", "IS"),
        _mk_item("자산총계", "BS"),
    ]


# ── REQ-SECTOR-01: detect_sector_tier ──────────────────────────────────────

class TestDetectSectorTier:
    """업종 4-tier 자동 감지 (요건서 §D-2 우선순위)."""

    def test_returns_bank_holding_for_086790_hana(self, items_bank_holding_086790):
        from stock.dart_fin import detect_sector_tier
        assert detect_sector_tier(items_bank_holding_086790) == "bank_holding"

    def test_returns_bank_holding_for_316140_woori_no_insurance(self, items_bank_holding_316140):
        from stock.dart_fin import detect_sector_tier
        # 보험수익 없어도 이자+수수료만으로 bank_holding 판정
        assert detect_sector_tier(items_bank_holding_316140) == "bank_holding"

    def test_returns_insurance_for_005830_db_insurance(self, items_insurance_005830):
        from stock.dart_fin import detect_sector_tier
        # 보험계약부채 BS 존재 → insurance (bank_holding보다 우선)
        assert detect_sector_tier(items_insurance_005830) == "insurance"

    def test_returns_securities_for_006800_mirae(self, items_securities_006800):
        from stock.dart_fin import detect_sector_tier
        # 영업수익 + 이자수익 있지만 수수료수익 없음 → securities
        assert detect_sector_tier(items_securities_006800) == "securities"

    def test_returns_general_for_005930_samsung(self, items_general_005930):
        from stock.dart_fin import detect_sector_tier
        assert detect_sector_tier(items_general_005930) == "general"

    def test_returns_general_for_035720_kakao_regression(self, items_general_kakao_035720):
        """REQ-SECTOR-01 회귀: 카카오는 영업수익+이자수익이지만 수수료수익 없음 → general."""
        from stock.dart_fin import detect_sector_tier
        assert detect_sector_tier(items_general_kakao_035720) == "general"

    def test_returns_general_for_empty_items(self):
        from stock.dart_fin import detect_sector_tier
        assert detect_sector_tier([]) == "general"

    def test_returns_general_for_none(self):
        from stock.dart_fin import detect_sector_tier
        # graceful: None 입력도 "general" 보수적 기본값
        assert detect_sector_tier(None) == "general"

    def test_priority_insurance_beats_bank_holding(self):
        """우선순위 검증: insurance 신호(보험계약부채) + bank_holding 신호(이자+수수료) 동시 → insurance."""
        from stock.dart_fin import detect_sector_tier
        items = [
            _mk_item("이자수익", "IS"),
            _mk_item("수수료수익", "IS"),
            _mk_item("보험계약부채", "BS"),  # insurance 신호 (BS)
        ]
        assert detect_sector_tier(items) == "insurance"

    def test_returns_value_in_valid_enum(self, items_bank_holding_086790, items_general_005930):
        """반환값 enum 검증."""
        from stock.dart_fin import detect_sector_tier
        valid = {"bank_holding", "insurance", "securities", "general"}
        assert detect_sector_tier(items_bank_holding_086790) in valid
        assert detect_sector_tier(items_general_005930) in valid


# ── REQ-ACCOUNT-01/02: 금융지주 매출 합산 ──────────────────────────────────

class TestExtractAccountsBankHoldingRevenue:
    """REQ-ACCOUNT-01: 금융지주 매출 = 이자수익 + 수수료수익 + 보험수익 합산.

    분기 진입은 _extract_accounts(items, sector_tier='bank_holding').
    """

    def test_bank_holding_sums_revenue_three_components(self):
        """086790 케이스: 이자 24.12조 + 수수료 3.60조 + 보험 0.61조 ≈ 28.33조."""
        from stock.dart_fin import _extract_accounts
        items = [
            {"sj_div": "IS", "account_nm": "이자수익",
             "thstrm_amount": "24120000000000", "frmtrm_amount": "20000000000000",
             "bfefrmtrm_amount": "18000000000000",
             "thstrm_nm": "제55기", "frmtrm_nm": "제54기", "bfefrmtrm_nm": "제53기",
             "thstrm_dt": "2024.01.01~2024.12.31"},
            {"sj_div": "IS", "account_nm": "수수료수익",
             "thstrm_amount": "3600000000000", "frmtrm_amount": "3500000000000",
             "bfefrmtrm_amount": "3000000000000"},
            {"sj_div": "IS", "account_nm": "보험수익",
             "thstrm_amount": "610000000000", "frmtrm_amount": "550000000000",
             "bfefrmtrm_amount": "500000000000"},
            {"sj_div": "IS", "account_nm": "영업이익",
             "thstrm_amount": "4850000000000", "frmtrm_amount": "4200000000000",
             "bfefrmtrm_amount": "3800000000000"},
            {"sj_div": "IS", "account_nm": "당기순이익",
             "thstrm_amount": "3770000000000", "frmtrm_amount": "3000000000000",
             "bfefrmtrm_amount": "2800000000000"},
        ]
        result = _extract_accounts(items, sector_tier="bank_holding")
        # 매출 합산 (단위: 원)
        expected_revenue = 24120000000000 + 3600000000000 + 610000000000  # 28.33조
        assert result["revenue"] == expected_revenue
        assert result["revenue_prev"] == 20000000000000 + 3500000000000 + 550000000000
        assert result["revenue_prev2"] == 18000000000000 + 3000000000000 + 500000000000
        # 영업이익/순이익은 기존 매칭 무변경
        assert result["operating_income"] == 4850000000000
        assert result["net_income"] == 3770000000000

    def test_bank_holding_no_insurance_revenue_316140(self):
        """316140 우리금융: 보험수익 없으면 0으로 취급 (이자 + 수수료만)."""
        from stock.dart_fin import _extract_accounts
        items = [
            {"sj_div": "IS", "account_nm": "이자수익",
             "thstrm_amount": "22010000000000"},
            {"sj_div": "IS", "account_nm": "수수료수익",
             "thstrm_amount": "2870000000000"},
            {"sj_div": "IS", "account_nm": "영업이익",
             "thstrm_amount": "4260000000000"},
            {"sj_div": "IS", "account_nm": "당기순이익",
             "thstrm_amount": "3000000000000"},
        ]
        result = _extract_accounts(items, sector_tier="bank_holding")
        assert result["revenue"] == 22010000000000 + 2870000000000  # 24.88조

    def test_bank_holding_all_none_returns_none(self):
        """이자/수수료/보험수익 모두 부재 시 revenue None."""
        from stock.dart_fin import _extract_accounts
        items = [
            {"sj_div": "IS", "account_nm": "영업이익", "thstrm_amount": "1000000"},
        ]
        result = _extract_accounts(items, sector_tier="bank_holding")
        assert result["revenue"] is None

    def test_general_uses_regex_match_005930_regression(self):
        """일반 제조업은 기존 정규식 그대로."""
        from stock.dart_fin import _extract_accounts
        items = [
            {"sj_div": "IS", "account_nm": "매출액",
             "thstrm_amount": "300000000000000",  # 300조
             "frmtrm_amount": "279000000000000",
             "bfefrmtrm_amount": "260000000000000",
             "thstrm_nm": "제55기", "frmtrm_nm": "제54기", "bfefrmtrm_nm": "제53기",
             "thstrm_dt": "2024.01.01~2024.12.31"},
            {"sj_div": "IS", "account_nm": "영업이익", "thstrm_amount": "30000000000000"},
            {"sj_div": "IS", "account_nm": "당기순이익", "thstrm_amount": "25000000000000"},
        ]
        result = _extract_accounts(items, sector_tier="general")
        assert result["revenue"] == 300000000000000

    def test_insurance_uses_existing_regex_005830_regression(self):
        """보험사: 기존 정규식(보험영업수익) 그대로 매칭."""
        from stock.dart_fin import _extract_accounts
        items = [
            {"sj_div": "IS", "account_nm": "보험영업수익",
             "thstrm_amount": "16080000000000"},
            {"sj_div": "IS", "account_nm": "영업이익", "thstrm_amount": "800000000000"},
        ]
        result = _extract_accounts(items, sector_tier="insurance")
        assert result["revenue"] == 16080000000000

    def test_securities_uses_existing_regex(self):
        """증권사: 영업수익 단일 매칭 (합산 안 함)."""
        from stock.dart_fin import _extract_accounts
        items = [
            {"sj_div": "IS", "account_nm": "영업수익",
             "thstrm_amount": "22200000000000"},
            {"sj_div": "IS", "account_nm": "이자수익",
             "thstrm_amount": "1000000000000"},  # 합산 안 됨
        ]
        result = _extract_accounts(items, sector_tier="securities")
        assert result["revenue"] == 22200000000000  # 이자 미합산

    def test_default_no_sector_tier_param_works_general(self):
        """sector_tier 미전달 시 기존 동작(general 동등) — 백워드 호환."""
        from stock.dart_fin import _extract_accounts
        items = [
            {"sj_div": "IS", "account_nm": "매출액", "thstrm_amount": "100000000"},
        ]
        # sector_tier 인자 없이 호출 → 기존 정규식 매칭 (general 동등)
        result = _extract_accounts(items)
        assert result["revenue"] == 100000000


# ── REQ-ACCOUNT-01 분기: _extract_period_accounts ──────────────────────────

class TestExtractPeriodAccountsBankHolding:
    """REQ-ACCOUNT-01: multi_year 진입점에서도 합산."""

    def test_period_extract_bank_holding_sums(self):
        from stock.dart_fin import _extract_period_accounts
        items = [
            {"sj_div": "IS", "account_nm": "이자수익", "thstrm_amount": "24120000000000"},
            {"sj_div": "IS", "account_nm": "수수료수익", "thstrm_amount": "3600000000000"},
            {"sj_div": "IS", "account_nm": "보험수익", "thstrm_amount": "610000000000"},
            {"sj_div": "IS", "account_nm": "영업이익", "thstrm_amount": "4850000000000"},
        ]
        result = _extract_period_accounts(items, "thstrm", sector_tier="bank_holding")
        assert result["revenue"] == 24120000000000 + 3600000000000 + 610000000000

    def test_period_extract_general_unchanged(self):
        from stock.dart_fin import _extract_period_accounts
        items = [
            {"sj_div": "IS", "account_nm": "매출액", "thstrm_amount": "300000000000000"},
        ]
        result = _extract_period_accounts(items, "thstrm", sector_tier="general")
        assert result["revenue"] == 300000000000000


# ── REQ-ACCOUNT-01 분기: _extract_is_detail_period ─────────────────────────

class TestExtractIsDetailBankHolding:
    """REQ-ACCOUNT-01: 손익세부 추출도 동일 분기."""

    def test_is_detail_bank_holding_sums(self):
        from stock.dart_fin import _extract_is_detail_period
        items = [
            {"sj_div": "IS", "account_nm": "이자수익", "thstrm_amount": "24120000000000"},
            {"sj_div": "IS", "account_nm": "수수료수익", "thstrm_amount": "3600000000000"},
            {"sj_div": "IS", "account_nm": "보험수익", "thstrm_amount": "610000000000"},
            {"sj_div": "IS", "account_nm": "영업이익", "thstrm_amount": "4850000000000"},
            {"sj_div": "IS", "account_nm": "당기순이익", "thstrm_amount": "3770000000000"},
            {"sj_div": "IS", "account_nm": "기본주당이익", "thstrm_amount": "12629"},
        ]
        result = _extract_is_detail_period(items, "thstrm", sector_tier="bank_holding")
        assert result["revenue"] == 24120000000000 + 3600000000000 + 610000000000
        assert result["operating_income"] == 4850000000000
        assert result["net_income"] == 3770000000000
        assert result["eps"] == 12629  # 매칭 무변경


# ── REQ-ACCOUNT-04: BS 신규 금융업 필드 ─────────────────────────────────────

class TestBsBankHoldingFields:
    """REQ-ACCOUNT-04: 예수부채/차입부채/사채/현금및예치금/대출채권 신규 추출 (P2)."""

    def test_bank_holding_extracts_deposits_payable(self):
        from stock.dart_fin import _extract_sheet_period, _BS_REGEX
        items = [
            {"sj_div": "BS", "account_nm": "예수부채", "thstrm_amount": "200000000000000"},
            {"sj_div": "BS", "account_nm": "차입부채", "thstrm_amount": "30000000000000"},
            {"sj_div": "BS", "account_nm": "사채", "thstrm_amount": "15000000000000"},
        ]
        result = _extract_sheet_period(items, ("BS", "CBS"), _BS_REGEX, "thstrm")
        assert result.get("deposits_payable") == 200000000000000
        assert result.get("borrowings_payable") == 30000000000000
        assert result.get("debentures") == 15000000000000

    def test_general_returns_none_for_bank_fields(self):
        """제조업은 None 채워짐."""
        from stock.dart_fin import _extract_sheet_period, _BS_REGEX
        items = [
            {"sj_div": "BS", "account_nm": "자산총계", "thstrm_amount": "100000000"},
            {"sj_div": "BS", "account_nm": "유동자산", "thstrm_amount": "50000000"},
        ]
        result = _extract_sheet_period(items, ("BS", "CBS"), _BS_REGEX, "thstrm")
        assert result.get("deposits_payable") is None
        assert result.get("borrowings_payable") is None
        assert result.get("debentures") is None
