"""dart_fin._BS_REGEX payables 계정 추가 테스트 (REQ-ACCOUNT-01).

매입채무회전율(REQ-MARGIN-02) 분모 확보를 위해 `_BS_REGEX`에 `payables` 키 추가.
receivables 패턴(`매출채권(및기타채권)?`)과 대칭.
CLAUDE.md 정규식 키워드 검색 원칙 (변형 흡수) 준수.
"""

from stock import dart_fin


# ── payables 정규식 매칭 ──

def test_payables_key_exists():
    """_BS_REGEX에 payables 키 존재."""
    assert "payables" in dart_fin._BS_REGEX


def test_payables_matches_basic():
    """`매입채무` 매칭."""
    pat = dart_fin._BS_REGEX["payables"]
    assert pat.match("매입채무")


def test_payables_matches_combined():
    """`매입채무및기타채무` 매칭 (변형 흡수)."""
    pat = dart_fin._BS_REGEX["payables"]
    assert pat.match("매입채무및기타채무")


def test_payables_matches_short_term():
    """`단기매입채무` 매칭."""
    pat = dart_fin._BS_REGEX["payables"]
    assert pat.match("단기매입채무")


def test_payables_matches_trade_and_other():
    """`매입채무및기타지급채무` 매칭."""
    pat = dart_fin._BS_REGEX["payables"]
    assert pat.match("매입채무및기타지급채무")


# ── receivables 충돌 차단 ──

def test_receivables_not_matched_by_payables():
    """`매출채권및기타채권`은 receivables 매칭, payables 아님 (충돌 없음)."""
    pat_pay = dart_fin._BS_REGEX["payables"]
    pat_rec = dart_fin._BS_REGEX["receivables"]
    assert not pat_pay.match("매출채권및기타채권")
    assert pat_rec.match("매출채권및기타채권")


def test_payables_rejects_partial():
    """하위/유사 항목 오매칭 차단 (^...$ 앵커)."""
    pat = dart_fin._BS_REGEX["payables"]
    assert not pat.match("매입채무증가")
    assert not pat.match("기타매입채무회전율")


# ── 통합: _extract_sheet_period BS 추출에 payables 포함 ──

def test_extract_bs_includes_payables():
    """BS 항목에 매입채무 존재 시 payables 추출."""
    items = [
        {"sj_div": "BS", "account_nm": "자산총계", "thstrm_amount": "1000000000"},
        {"sj_div": "BS", "account_nm": "매입채무", "thstrm_amount": "300000000"},
    ]
    result = dart_fin._extract_sheet_period(
        items, ("BS", "CBS"), dart_fin._BS_REGEX, "thstrm"
    )
    assert result["payables"] == 300000000


def test_extract_bs_payables_none_when_absent():
    """매입채무 없는 회사는 payables None (graceful)."""
    items = [
        {"sj_div": "BS", "account_nm": "자산총계", "thstrm_amount": "1000000000"},
    ]
    result = dart_fin._extract_sheet_period(
        items, ("BS", "CBS"), dart_fin._BS_REGEX, "thstrm"
    )
    assert result.get("payables") is None


def test_extract_bs_existing_fields_unchanged():
    """회귀 가드: 기존 receivables/inventories 추출 불변 (payables 추가 외 변화 없음)."""
    items = [
        {"sj_div": "BS", "account_nm": "자산총계", "thstrm_amount": "1000000000"},
        {"sj_div": "BS", "account_nm": "매출채권및기타채권", "thstrm_amount": "200000000"},
        {"sj_div": "BS", "account_nm": "재고자산", "thstrm_amount": "150000000"},
        {"sj_div": "BS", "account_nm": "매입채무", "thstrm_amount": "100000000"},
    ]
    result = dart_fin._extract_sheet_period(
        items, ("BS", "CBS"), dart_fin._BS_REGEX, "thstrm"
    )
    assert result["receivables"] == 200000000
    assert result["inventories"] == 150000000
    assert result["payables"] == 100000000
