"""dart_fin.py 보험업 회계과목 매핑 회귀 테스트.

2026-05-09 진단: DB손해보험(005830) 등 보험사가 일반 제조업 회계과목
정규식과 매칭 안 되어 fetch_financials_multi_year가 0년치 반환하던 결함.

ValueScreener 자문(2026-05-09): 매출 매핑은 `보험(영업)?수익` 정규식 추가,
업종 자동 감지는 `보험계약부채`/`책임준비금`/`보험계약자산` 패턴 사용.
"""

import re

from stock import dart_fin


# ── 매출 정규식 ───────────────────────────────────────────────

def test_revenue_regex_matches_legacy_manufacturing():
    """기존 제조업 매출 항목은 그대로 매칭 (백워드 호환)."""
    pat = dart_fin._ACCOUNT_REGEX["revenue"]
    assert pat.match("매출액")
    assert pat.match("매출")
    assert pat.match("영업수익")
    assert pat.match("수익(매출액)")


def test_revenue_regex_matches_insurance_revenue():
    """보험사 `보험영업수익` (손해보험 표준)."""
    pat = dart_fin._ACCOUNT_REGEX["revenue"]
    assert pat.match("보험영업수익")


def test_revenue_regex_matches_ifrs17_insurance_revenue():
    """IFRS17 (2023~) 표기 `보험수익`."""
    pat = dart_fin._ACCOUNT_REGEX["revenue"]
    assert pat.match("보험수익")


def test_revenue_regex_rejects_partial_match():
    """부분 일치 차단 — 하위 계정 오매칭 방지."""
    pat = dart_fin._ACCOUNT_REGEX["revenue"]
    # 보험영업수익의 하위 항목들
    assert not pat.match("보험영업수익증가율")
    assert not pat.match("총보험영업수익")


def test_is_detail_revenue_regex_includes_insurance():
    """IS_DETAIL의 revenue도 보험업 매핑 포함 (advisory_service 손익 분석용)."""
    pat = dart_fin._IS_DETAIL_REGEX["revenue"]
    assert pat.match("보험영업수익")
    assert pat.match("보험수익")
    assert pat.match("매출액")  # 백워드 호환


# ── 보험업 자동 감지 ─────────────────────────────────────────

def test_is_insurance_company_detects_보험계약부채():
    """`보험계약부채` 항목 존재 시 보험업 판정."""
    items = [
        {"account_nm": "자산총계", "sj_div": "BS"},
        {"account_nm": "보험계약부채", "sj_div": "BS"},
        {"account_nm": "자본총계", "sj_div": "BS"},
    ]
    assert dart_fin.is_insurance_company(items) is True


def test_is_insurance_company_detects_책임준비금():
    """`책임준비금` (생보/손보 공통)."""
    items = [{"account_nm": "책임준비금", "sj_div": "BS"}]
    assert dart_fin.is_insurance_company(items) is True


def test_is_insurance_company_detects_보험계약자산():
    """`보험계약자산` (재보험 포함)."""
    items = [{"account_nm": "보험계약자산", "sj_div": "BS"}]
    assert dart_fin.is_insurance_company(items) is True


def test_is_insurance_company_handles_whitespace():
    """공백 포함 회계과목명도 정확히 감지 (DART 표기 유연성)."""
    items = [{"account_nm": "보험 계약 부채", "sj_div": "BS"}]
    assert dart_fin.is_insurance_company(items) is True


def test_is_insurance_company_returns_false_for_manufacturing():
    """일반 제조업 항목만 있을 시 False."""
    items = [
        {"account_nm": "자산총계", "sj_div": "BS"},
        {"account_nm": "유동자산", "sj_div": "BS"},
        {"account_nm": "재고자산", "sj_div": "BS"},
        {"account_nm": "매출액", "sj_div": "IS"},
    ]
    assert dart_fin.is_insurance_company(items) is False


def test_is_insurance_company_handles_empty_items():
    """빈 리스트는 False (보험업 단정 금지)."""
    assert dart_fin.is_insurance_company([]) is False


def test_is_insurance_company_handles_none_account_nm():
    """account_nm이 None인 항목 graceful 처리."""
    items = [{"account_nm": None, "sj_div": "BS"}]
    assert dart_fin.is_insurance_company(items) is False


# ── 보험업 BS 추가 필드 ───────────────────────────────────────

def test_bs_regex_includes_insurance_liabilities():
    """`보험계약부채` 또는 `책임준비금` 매칭 — Optional 필드."""
    pat = dart_fin._BS_REGEX["insurance_liabilities"]
    assert pat.match("보험계약부채")
    assert pat.match("책임준비금")
    assert not pat.match("부채총계")  # 일반 부채와 분리


def test_bs_regex_includes_insurance_assets():
    """`보험계약자산` 또는 `재보험계약자산`."""
    pat = dart_fin._BS_REGEX["insurance_assets"]
    assert pat.match("보험계약자산")
    assert pat.match("재보험계약자산")
    assert not pat.match("자산총계")


def test_bs_regex_preserves_legacy_total_keys():
    """일반 제조업 표준 키는 그대로 보존 (백워드 호환)."""
    assert dart_fin._BS_REGEX["total_assets"].match("자산총계")
    assert dart_fin._BS_REGEX["total_liabilities"].match("부채총계")
    assert dart_fin._BS_REGEX["total_equity"].match("자본총계")


# ── 통합 추출 시나리오 ─────────────────────────────────────────

def test_extract_accounts_uses_insurance_revenue():
    """_extract_accounts가 보험업 항목에서 매출(보험영업수익)을 정상 추출."""
    items = [
        {"sj_div": "IS", "account_nm": "보험영업수익",
         "thstrm_amount": "10000000000", "frmtrm_amount": "9000000000",
         "bfefrmtrm_amount": "8000000000",
         "thstrm_nm": "당기", "frmtrm_nm": "전기", "bfefrmtrm_nm": "전전기",
         "thstrm_dt": "2024-12-31"},
        {"sj_div": "IS", "account_nm": "영업이익",
         "thstrm_amount": "1500000000", "frmtrm_amount": "1200000000",
         "bfefrmtrm_amount": "1000000000"},
        {"sj_div": "IS", "account_nm": "당기순이익",
         "thstrm_amount": "1100000000", "frmtrm_amount": "900000000",
         "bfefrmtrm_amount": "750000000"},
    ]
    result = dart_fin._extract_accounts(items)
    assert result["revenue"] == 10000000000
    assert result["operating_income"] == 1500000000
    assert result["net_income"] == 1100000000
    assert result["revenue_prev"] == 9000000000


def test_extract_accounts_legacy_manufacturing_unchanged():
    """일반 제조업 추출 동작 변경 없음 (회귀 0건)."""
    items = [
        {"sj_div": "IS", "account_nm": "매출액",
         "thstrm_amount": "5000000000", "frmtrm_amount": "4500000000",
         "bfefrmtrm_amount": "4000000000",
         "thstrm_nm": "당기", "frmtrm_nm": "전기", "bfefrmtrm_nm": "전전기",
         "thstrm_dt": "2024-12-31"},
    ]
    result = dart_fin._extract_accounts(items)
    assert result["revenue"] == 5000000000


# ── IS_DETAIL 보험사 추가 매핑 (2026-05-09 진단) ──

def test_pretax_income_matches_insurance_short_form():
    """보험사 `법인세차감전순이익` (`비용` 생략) 매칭."""
    pat = dart_fin._IS_DETAIL_REGEX["pretax_income"]
    assert pat.match("법인세차감전순이익")


def test_pretax_income_matches_legacy_long_form():
    """일반 제조업 `법인세비용차감전순이익` 회귀."""
    pat = dart_fin._IS_DETAIL_REGEX["pretax_income"]
    assert pat.match("법인세비용차감전순이익")
    assert pat.match("법인세비용차감전계속영업순이익")


def test_interest_expense_matches_insurance_form():
    """보험사 `금융부채의이자비용` (공백 제거 후) 매칭."""
    pat = dart_fin._IS_DETAIL_REGEX["interest_expense"]
    assert pat.match("금융부채의이자비용")


def test_interest_expense_matches_legacy_form():
    """일반 제조업 `이자비용` 회귀."""
    pat = dart_fin._IS_DETAIL_REGEX["interest_expense"]
    assert pat.match("이자비용")


def test_eps_matches_insurance_form():
    """보험사 `보통주기본주당이익(손실)` 매칭."""
    pat = dart_fin._IS_DETAIL_REGEX["eps"]
    # 공백 제거 후 비교 (실제 _match_account 로직)
    assert pat.match("보통주기본주당이익(손실)")
    assert pat.match("보통주기본주당이익")


def test_eps_matches_legacy_form():
    """일반 제조업 `기본주당순이익` 회귀."""
    pat = dart_fin._IS_DETAIL_REGEX["eps"]
    assert pat.match("기본주당순이익")
    assert pat.match("기본주당이익")
    assert pat.match("기본주당이익(손실)")
