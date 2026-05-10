"""sector_normalize 모듈 단위 테스트.

REQ-BACK-001 (모듈 신설) + REQ-BACK-002 (KR 정규식 매핑) +
REQ-BACK-003 (코드 직접 매핑) + REQ-TEST-001 (단위 테스트 + 화이트리스트 보증).

SSoT:
- KR 14개 한글 라벨 = stock/macro_fetcher.py::_KR_SECTOR_ETFS 의 name_ko
- KR 70개 대표종목 코드 = frontend/src/components/macro/sectorRepresentatives.js::KR_SECTOR_REPS
- US 11개 한글 라벨 = sector_normalize 모듈 자체 정적 dict (GICS 직역)
"""
from __future__ import annotations

import pytest


# ──────────────────────────────────────────────────────────────────────
# REQ-BACK-001: 모듈 신설 + 화이트리스트
# ──────────────────────────────────────────────────────────────────────

def test_module_exports_required_symbols():
    """모듈이 외부 사용 함수/상수를 노출."""
    from stock import sector_normalize as sn

    assert callable(sn.normalize_sector)
    assert callable(sn.normalize_kr_sector)
    assert callable(sn.normalize_us_sector)
    assert isinstance(sn.KR_SECTOR_LABELS, tuple)
    assert isinstance(sn.US_SECTOR_LABELS, tuple)


def test_kr_labels_match_macro_ssot_count_and_order():
    """KR 14 라벨이 매크로 SSoT(_KR_SECTOR_ETFS)의 순서/구성과 100% 일치."""
    from stock.macro_fetcher import _KR_SECTOR_ETFS
    from stock.sector_normalize import KR_SECTOR_LABELS

    expected = tuple(name_ko for _, _, name_ko in _KR_SECTOR_ETFS)
    assert KR_SECTOR_LABELS == expected
    assert len(KR_SECTOR_LABELS) == 14


def test_us_labels_count():
    from stock.sector_normalize import US_SECTOR_LABELS

    assert len(US_SECTOR_LABELS) == 11
    # 한글 라벨이어야 함
    expected = {
        "정보기술", "헬스케어", "금융", "커뮤니케이션 서비스",
        "임의소비재", "필수소비재", "산업재", "에너지",
        "유틸리티", "부동산", "소재",
    }
    assert set(US_SECTOR_LABELS) == expected


# ──────────────────────────────────────────────────────────────────────
# REQ-BACK-001 수용 기준: US GICS 영문 → 한글
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("Technology", "정보기술"),
    ("Information Technology", "정보기술"),
    ("Tech", "정보기술"),
    ("Health Care", "헬스케어"),
    ("Healthcare", "헬스케어"),
    ("Financials", "금융"),
    ("Financial Services", "금융"),
    ("Communication Services", "커뮤니케이션 서비스"),
    ("Consumer Discretionary", "임의소비재"),
    ("Consumer Staples", "필수소비재"),
    ("Industrials", "산업재"),
    ("Energy", "에너지"),
    ("Utilities", "유틸리티"),
    ("Real Estate", "부동산"),
    ("Basic Materials", "소재"),
    ("Materials", "소재"),
])
def test_normalize_us(raw, expected):
    from stock.sector_normalize import normalize_sector
    assert normalize_sector(raw, "US") == expected


# ──────────────────────────────────────────────────────────────────────
# REQ-BACK-002: KR 정규식 다대일
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    # 반도체
    ("반도체", "반도체"),
    ("전기·전자", "반도체"),
    ("전기전자", "반도체"),
    ("디스플레이", "반도체"),
    # IT/인터넷 — KRX "서비스업"
    ("서비스업", "IT/인터넷"),
    ("IT 서비스", "IT/인터넷"),
    ("소프트웨어", "IT/인터넷"),
    ("게임", "IT/인터넷"),
    ("인터넷", "IT/인터넷"),
    ("플랫폼", "IT/인터넷"),
    # 2차전지
    ("2차전지", "2차전지"),
    ("이차전지", "2차전지"),
    ("배터리", "2차전지"),
    # 건설
    ("건설", "건설"),
    ("건설업", "건설"),
    ("건자재", "건설"),
    # 바이오/헬스케어
    ("바이오", "바이오/헬스케어"),
    ("의약품", "바이오/헬스케어"),
    ("제약", "바이오/헬스케어"),
    ("의료기기", "바이오/헬스케어"),
    # 은행/금융
    ("금융업", "은행/금융"),
    ("은행", "은행/금융"),
    ("증권", "은행/금융"),
    ("보험", "은행/금융"),
    ("카드", "은행/금융"),
    # 철강/소재
    ("철강금속", "철강/소재"),
    ("비철금속", "철강/소재"),
    # 자동차 — KRX "운수장비"
    ("운수장비", "자동차"),
    ("자동차", "자동차"),
    ("타이어", "자동차"),
    # 에너지/화학
    ("화학", "에너지/화학"),
    ("정유", "에너지/화학"),
    ("석유", "에너지/화학"),
    ("신재생에너지", "에너지/화학"),
    # 미디어/엔터
    ("미디어", "미디어/엔터"),
    ("엔터테인먼트", "미디어/엔터"),
    ("방송", "미디어/엔터"),
    ("콘텐츠", "미디어/엔터"),
    # 필수소비재
    ("음식료", "필수소비재"),
    ("식품", "필수소비재"),
    ("생활용품", "필수소비재"),
    ("담배", "필수소비재"),
    # 경기소비재
    ("유통업", "경기소비재"),
    ("화장품", "경기소비재"),
    ("패션", "경기소비재"),
    ("의류", "경기소비재"),
    ("호텔", "경기소비재"),
    # 운송/물류 — KRX "운수창고업"
    ("운수창고업", "운송/물류"),
    ("항공운송", "운송/물류"),
    ("해운", "운송/물류"),
    ("물류", "운송/물류"),
    # 유틸리티
    ("유틸리티", "유틸리티"),
    ("가스", "유틸리티"),
    ("난방", "유틸리티"),
])
def test_normalize_kr_regex(raw, expected):
    from stock.sector_normalize import normalize_sector
    assert normalize_sector(raw, "KR") == expected


# ──────────────────────────────────────────────────────────────────────
# 영문 GICS sector + industry → KR 14 한글 매핑
# yfinance가 KR 종목에 영문 GICS를 반환하는 케이스 (대다수) 커버
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sector,industry,expected", [
    # 자동차 — Auto Manufacturers / Auto Parts (현대차/기아/현대모비스)
    ("Consumer Cyclical", "Auto Manufacturers", "자동차"),
    ("Consumer Cyclical", "Auto Parts", "자동차"),
    # 반도체 — Semiconductors / Electronic Components / Consumer Electronics
    ("Technology", "Semiconductors", "반도체"),
    ("Technology", "Electronic Components", "반도체"),
    ("Technology", "Consumer Electronics", "반도체"),
    # 은행/금융 — Banks - Regional / Insurance / Capital Markets
    ("Financial Services", "Banks - Regional", "은행/금융"),
    ("Financial Services", "Insurance - Life", "은행/금융"),
    ("Financial Services", "Capital Markets", "은행/금융"),
    ("Financial Services", "Asset Management", "은행/금융"),
    ("Financial Services", "Credit Services", "은행/금융"),
    # 건설 — Engineering & Construction / Building Materials
    ("Industrials", "Engineering & Construction", "건설"),
    ("Industrials", "Building Materials", "건설"),
    # 바이오/헬스케어
    ("Healthcare", "Drug Manufacturers - Specialty & Generic", "바이오/헬스케어"),
    ("Healthcare", "Biotechnology", "바이오/헬스케어"),
    ("Healthcare", "Medical Devices", "바이오/헬스케어"),
    ("Healthcare", "Medical Care Facilities", "바이오/헬스케어"),
    # 미디어/엔터 — Telecom / Entertainment / Broadcasting / Communication
    ("Communication Services", "Telecom Services", "미디어/엔터"),
    ("Communication Services", "Entertainment", "미디어/엔터"),
    ("Communication Services", "Broadcasting", "미디어/엔터"),
    # 유틸리티
    ("Utilities", "Utilities - Regulated Electric", "유틸리티"),
    ("Utilities", "Utilities - Regulated Gas", "유틸리티"),
    ("Utilities", "Water Utilities", "유틸리티"),
    # 에너지/화학 — Oil & Gas / Specialty Chemicals
    ("Energy", "Oil & Gas Integrated", "에너지/화학"),
    ("Energy", "Oil & Gas E&P", "에너지/화학"),
    ("Basic Materials", "Specialty Chemicals", "에너지/화학"),
    ("Basic Materials", "Chemicals", "에너지/화학"),
    # 철강/소재
    ("Basic Materials", "Steel", "철강/소재"),
    ("Basic Materials", "Other Industrial Metals & Mining", "철강/소재"),
    ("Basic Materials", "Aluminum", "철강/소재"),
    ("Basic Materials", "Paper & Paper Products", "철강/소재"),
    # 운송/물류
    ("Industrials", "Airlines", "운송/물류"),
    ("Industrials", "Marine Shipping", "운송/물류"),
    ("Industrials", "Trucking", "운송/물류"),
    ("Industrials", "Railroads", "운송/물류"),
    ("Industrials", "Integrated Freight & Logistics", "운송/물류"),
    # 필수소비재
    ("Consumer Defensive", "Packaged Foods", "필수소비재"),
    ("Consumer Defensive", "Beverages - Non-Alcoholic", "필수소비재"),
    ("Consumer Defensive", "Tobacco", "필수소비재"),
    ("Consumer Defensive", "Household & Personal Products", "필수소비재"),
    # 경기소비재
    ("Consumer Cyclical", "Apparel Manufacturing", "경기소비재"),
    ("Consumer Cyclical", "Specialty Retail", "경기소비재"),
    ("Consumer Cyclical", "Restaurants", "경기소비재"),
    ("Consumer Cyclical", "Lodging", "경기소비재"),
    ("Consumer Cyclical", "Resorts & Casinos", "경기소비재"),
    ("Consumer Cyclical", "Department Stores", "경기소비재"),
    ("Consumer Cyclical", "Internet Retail", "경기소비재"),
    # IT/인터넷 — Software / Internet / Gaming / IT Services
    ("Technology", "Software - Application", "IT/인터넷"),
    ("Technology", "Software - Infrastructure", "IT/인터넷"),
    ("Technology", "Information Technology Services", "IT/인터넷"),
    ("Communication Services", "Internet Content & Information", "IT/인터넷"),
    ("Communication Services", "Electronic Gaming & Multimedia", "IT/인터넷"),
])
def test_normalize_kr_with_english_gics_industry(sector, industry, expected):
    """yfinance KR 종목 영문 GICS sector+industry → 14 한글 라벨."""
    from stock.sector_normalize import normalize_sector
    assert normalize_sector(sector, "KR", industry=industry) == expected


@pytest.mark.parametrize("sector,expected", [
    # industry 없이 sector만 — 광역 GICS도 14 매핑 (가장 가까운 라벨로)
    ("Consumer Cyclical", "경기소비재"),
    ("Consumer Defensive", "필수소비재"),
    ("Financial Services", "은행/금융"),
    ("Healthcare", "바이오/헬스케어"),
    ("Communication Services", "미디어/엔터"),
    ("Utilities", "유틸리티"),
    ("Energy", "에너지/화학"),
])
def test_normalize_kr_with_english_gics_sector_only(sector, expected):
    """industry 누락 시 영문 GICS sector만으로도 14 매핑."""
    from stock.sector_normalize import normalize_sector
    assert normalize_sector(sector, "KR") == expected


def test_normalize_kr_industry_takes_priority_over_sector():
    """industry가 sector보다 우선 매칭 (더 세밀)."""
    from stock.sector_normalize import normalize_sector
    # sector=Industrials는 자체로 매핑 없음, industry=Auto Parts → 자동차
    assert normalize_sector("Industrials", "KR", industry="Auto Parts") == "자동차"


def test_normalize_kr_code_map_still_top_priority():
    """코드 화이트리스트가 영문 GICS보다 여전히 우선."""
    from stock.sector_normalize import normalize_sector
    # 005930 삼성전자 = 반도체. industry가 다른 라벨이어도 코드 매핑 우선
    assert normalize_sector(
        "Healthcare", "KR", code="005930", industry="Drug Manufacturers",
    ) == "반도체"


def test_normalize_us_falls_back_to_industry():
    """US: sector 미매칭 시 industry 폴백."""
    from stock.sector_normalize import normalize_sector
    # sector=None, industry=Software → 정보기술 미매칭 (industry가 아닌 sector 사전 적용)
    # 빈 sector + industry로 매칭 가능한지 확인
    assert normalize_sector(None, "US", industry="Technology") == "정보기술"
    assert normalize_sector("Unknown", "US", industry="Health Care") == "헬스케어"


# ──────────────────────────────────────────────────────────────────────
# REQ-BACK-001 수용 기준: 폴백 / 빈 입력
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,market", [
    (None, "US"),
    ("", "KR"),
    ("   ", "KR"),
    ("Unknown XYZ", "US"),
    ("아무런 분류 없음", "KR"),
])
def test_normalize_fallback_to_etc(raw, market):
    from stock.sector_normalize import normalize_sector
    assert normalize_sector(raw, market) == "기타"


def test_normalize_none_with_code_falls_back_to_code_map():
    """raw=None 이라도 KR 70 화이트리스트 코드면 매핑."""
    from stock.sector_normalize import normalize_sector
    assert normalize_sector(None, "KR", code="005930") == "반도체"
    assert normalize_sector(None, "KR", code="105560") == "은행/금융"


# ──────────────────────────────────────────────────────────────────────
# REQ-BACK-003: 종목코드 직접 매핑 화이트리스트 (>=70)
# ──────────────────────────────────────────────────────────────────────

# 70개 대표 종목(KR_SECTOR_REPS의 14×5) — 라벨과 함께 고정 fixture
KR_70 = [
    # 반도체
    ("005930", "반도체"), ("000660", "반도체"), ("042700", "반도체"),
    ("240810", "반도체"), ("058470", "반도체"),
    # IT/인터넷
    ("035420", "IT/인터넷"), ("035720", "IT/인터넷"), ("018260", "IT/인터넷"),
    ("036570", "IT/인터넷"), ("251270", "IT/인터넷"),
    # 2차전지
    ("373220", "2차전지"), ("006400", "2차전지"), ("003670", "2차전지"),
    ("247540", "2차전지"), ("086520", "2차전지"),
    # 건설
    ("000720", "건설"), ("006360", "건설"), ("375500", "건설"),
    ("047040", "건설"), ("294870", "건설"),
    # 바이오/헬스케어
    ("207940", "바이오/헬스케어"), ("068270", "바이오/헬스케어"),
    ("000100", "바이오/헬스케어"), ("128940", "바이오/헬스케어"),
    ("326030", "바이오/헬스케어"),
    # 은행/금융
    ("105560", "은행/금융"), ("055550", "은행/금융"), ("086790", "은행/금융"),
    ("316140", "은행/금융"), ("323410", "은행/금융"),
    # 철강/소재
    ("005490", "철강/소재"), ("004020", "철강/소재"), ("103140", "철강/소재"),
    ("001230", "철강/소재"), ("014285", "철강/소재"),
    # 자동차
    ("005380", "자동차"), ("000270", "자동차"), ("012330", "자동차"),
    ("161390", "자동차"), ("204320", "자동차"),
    # 에너지/화학
    ("051910", "에너지/화학"), ("011170", "에너지/화학"),
    ("096770", "에너지/화학"), ("010950", "에너지/화학"),
    ("009830", "에너지/화학"),
    # 미디어/엔터
    ("035760", "미디어/엔터"), ("352820", "미디어/엔터"),
    ("041510", "미디어/엔터"), ("122870", "미디어/엔터"),
    ("253450", "미디어/엔터"),
    # 필수소비재
    ("033780", "필수소비재"), ("004370", "필수소비재"),
    ("271560", "필수소비재"), ("097950", "필수소비재"),
    ("007310", "필수소비재"),
    # 경기소비재
    ("008770", "경기소비재"), ("139480", "경기소비재"),
    ("004170", "경기소비재"), ("383220", "경기소비재"),
    ("090430", "경기소비재"),
    # 운송/물류
    ("003490", "운송/물류"), ("011200", "운송/물류"),
    ("000120", "운송/물류"), ("028670", "운송/물류"),
    ("002320", "운송/물류"),
    # 유틸리티
    ("015760", "유틸리티"), ("036460", "유틸리티"), ("018670", "유틸리티"),
    ("071320", "유틸리티"), ("004690", "유틸리티"),
]


def test_code_map_contains_at_least_70_entries():
    from stock.sector_normalize import _CODE_TO_KR_SECTOR
    assert len(_CODE_TO_KR_SECTOR) >= 70


@pytest.mark.parametrize("code,expected_label", KR_70)
def test_code_map_resolves_70_representatives(code, expected_label):
    """코드 직접 매핑은 raw 무관하게 라벨 반환 (정규식보다 우선)."""
    from stock.sector_normalize import normalize_sector
    # raw="아무거나" 정확한 14 라벨 반환
    assert normalize_sector("아무거나", "KR", code=code) == expected_label
    # raw=None도 동일
    assert normalize_sector(None, "KR", code=code) == expected_label


def test_code_map_priority_over_regex_conflict():
    """카카오뱅크(323410)는 회사명에 IT 단어 있어도 은행/금융 우선."""
    from stock.sector_normalize import normalize_sector
    assert normalize_sector("IT 서비스", "KR", code="323410") == "은행/금융"
    # 네이버(035420)는 KR_SECTOR_REPS에서 IT/인터넷 — Communication 충돌 해소
    assert normalize_sector("Communication", "KR", code="035420") == "IT/인터넷"


# ──────────────────────────────────────────────────────────────────────
# 회귀 가드: 모든 결과 라벨이 화이트리스트
# ──────────────────────────────────────────────────────────────────────

def test_all_outputs_in_whitelist():
    """랜덤 샘플 입력의 결과는 항상 14/11/"기타" 화이트리스트."""
    from stock.sector_normalize import (
        KR_SECTOR_LABELS, US_SECTOR_LABELS, normalize_sector,
    )
    valid_kr = set(KR_SECTOR_LABELS) | {"기타"}
    valid_us = set(US_SECTOR_LABELS) | {"기타"}

    samples_kr = ["반도체", "서비스업", "운수장비", "이상한카테고리", "", None,
                  "전기·전자", "운수창고업", "유틸리티", "화학"]
    samples_us = ["Technology", "Tech", "Healthcare", "Real Estate",
                  "Unknown", "", None, "Materials"]

    for s in samples_kr:
        assert normalize_sector(s, "KR") in valid_kr
    for s in samples_us:
        assert normalize_sector(s, "US") in valid_us


def test_invalid_market_falls_back_to_etc():
    from stock.sector_normalize import normalize_sector
    # 알 수 없는 market은 "기타"
    assert normalize_sector("Technology", "JP") == "기타"
    assert normalize_sector("Technology", "") == "기타"


def test_market_is_case_insensitive():
    from stock.sector_normalize import normalize_sector
    assert normalize_sector("Technology", "us") == "정보기술"
    assert normalize_sector("반도체", "kr") == "반도체"
