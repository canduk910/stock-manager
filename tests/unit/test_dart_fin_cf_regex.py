"""dart_fin._CF_REGEX 회귀 테스트.

2026-05-09 진단: DB손해보험(005830) CF 39개 항목 모두 `영업활동순현금흐름` /
`투자활동순현금흐름` / `재무활동순현금흐름` 형식 사용. 현재 정규식이 `순` 자 없는
패턴만 매칭해 보험사 CF 0년치 추출되던 결함.

수정: `(순)?` 옵션 추가로 보험사·일반 제조업 양쪽 백워드 호환.
"""

from stock import dart_fin


# ── 일반 제조업 (회귀 가드: 005930 삼성전자 패턴) ──

def test_operating_cf_matches_general_manufacturing():
    """일반 제조업 `영업활동현금흐름` 그대로 매칭."""
    pat = dart_fin._CF_REGEX["operating_cf"]
    assert pat.match("영업활동현금흐름")
    assert pat.match("영업활동으로인한현금흐름")


def test_investing_cf_matches_general_manufacturing():
    pat = dart_fin._CF_REGEX["investing_cf"]
    assert pat.match("투자활동현금흐름")
    assert pat.match("투자활동으로인한현금흐름")


def test_financing_cf_matches_general_manufacturing():
    pat = dart_fin._CF_REGEX["financing_cf"]
    assert pat.match("재무활동현금흐름")
    assert pat.match("재무활동으로인한현금흐름")


# ── 보험사·금융업 (DB손해보험 005830 패턴) ──

def test_operating_cf_matches_insurance_format():
    """보험사 `영업활동순현금흐름` 매칭 (2026-05-09 결함 해소)."""
    pat = dart_fin._CF_REGEX["operating_cf"]
    assert pat.match("영업활동순현금흐름")


def test_investing_cf_matches_insurance_format():
    pat = dart_fin._CF_REGEX["investing_cf"]
    assert pat.match("투자활동순현금흐름")


def test_financing_cf_matches_insurance_format():
    pat = dart_fin._CF_REGEX["financing_cf"]
    assert pat.match("재무활동순현금흐름")


def test_operating_cf_combined_insurance_long_form():
    """`영업활동으로인한순현금흐름` 같은 결합 패턴도 매칭."""
    pat = dart_fin._CF_REGEX["operating_cf"]
    assert pat.match("영업활동으로인한순현금흐름")


# ── 부분 일치 차단 ──

def test_cf_regex_rejects_partial_match():
    """하위 항목 오매칭 차단 (^...$ 앵커)."""
    pat = dart_fin._CF_REGEX["operating_cf"]
    assert not pat.match("영업활동현금흐름증가율")
    assert not pat.match("총영업활동현금흐름")
    assert not pat.match("영업활동")  # 단독 키워드만


# ── 통합: _extract_sheet_period CF 추출 ──

def test_extract_cf_period_with_insurance_format():
    """보험사 CF 항목에서 영업/투자/재무 모두 정상 추출."""
    items = [
        {"sj_div": "CF", "account_nm": "영업활동순현금흐름",
         "thstrm_amount": "5000000000"},
        {"sj_div": "CF", "account_nm": "투자활동순현금흐름",
         "thstrm_amount": "-2000000000"},
        {"sj_div": "CF", "account_nm": "재무활동순현금흐름",
         "thstrm_amount": "-1500000000"},
    ]
    result = dart_fin._extract_sheet_period(
        items, ("CF", "CCF"), dart_fin._CF_REGEX, "thstrm"
    )
    assert result["operating_cf"] == 5000000000
    assert result["investing_cf"] == -2000000000
    assert result["financing_cf"] == -1500000000


def test_extract_cf_period_with_legacy_format_unchanged():
    """일반 제조업 CF 추출 회귀 0건."""
    items = [
        {"sj_div": "CF", "account_nm": "영업활동현금흐름",
         "thstrm_amount": "10000000000"},
    ]
    result = dart_fin._extract_sheet_period(
        items, ("CF", "CCF"), dart_fin._CF_REGEX, "thstrm"
    )
    assert result["operating_cf"] == 10000000000
