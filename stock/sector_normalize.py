"""섹터명 한글 라벨 정규화 모듈.

매크로 페이지 섹터히트맵의 분류 체계를 단일 정답(SSoT)으로 삼아 모든 노출 영역에서
동일한 한글 라벨로 표시되도록 한다.

SSoT:
- KR 14개: ``stock.macro_fetcher._KR_SECTOR_ETFS`` 의 ``name_ko``
  → ``KR_SECTOR_LABELS`` 자동 동기 (라벨/순서 변경 시 import-time 반영)
- US 11개: GICS 영문 → 한글 정적 매핑 (KB/미래에셋 리서치 표기 관행)
- 70개 KR 대표종목 코드: ``frontend/src/components/macro/sectorRepresentatives.js``
  ``KR_SECTOR_REPS`` 와 정확히 동일 (도메인 자문 합의안)

설계 원칙:
- ``normalize_sector`` 는 **순수 함수** — 캐시 비의존
- 캐시는 ``normalize_sector_cached`` 별도 wrapper에서 처리 (레이어 분리)
- 코드 직접 매핑 우선 → 정규식 폴백 → "기타"

CLAUDE.md "키워드 텍스트 검색은 정규식" 지침 준수.
"""
from __future__ import annotations

import re
from typing import Optional


# ──────────────────────────────────────────────────────────────────────
# US GICS → 한글 정적 매핑 (11개)
# ──────────────────────────────────────────────────────────────────────

US_SECTOR_LABELS: tuple[str, ...] = (
    "정보기술", "헬스케어", "금융", "커뮤니케이션 서비스",
    "임의소비재", "필수소비재", "산업재", "에너지",
    "유틸리티", "부동산", "소재",
)

# 영문 변형 → 한글 (대소문자/공백 정규화 후 매칭)
_US_SECTOR_MAP: dict[str, str] = {
    # 정보기술
    "technology": "정보기술",
    "information technology": "정보기술",
    "tech": "정보기술",
    "infotech": "정보기술",
    # 헬스케어
    "health care": "헬스케어",
    "healthcare": "헬스케어",
    # 금융
    "financials": "금융",
    "financial services": "금융",
    "finance": "금융",
    # 커뮤니케이션
    "communication services": "커뮤니케이션 서비스",
    "communications": "커뮤니케이션 서비스",
    "communication": "커뮤니케이션 서비스",
    "telecommunication services": "커뮤니케이션 서비스",
    # 임의소비재
    "consumer discretionary": "임의소비재",
    "consumer cyclical": "임의소비재",
    # 필수소비재
    "consumer staples": "필수소비재",
    "consumer defensive": "필수소비재",
    # 산업재
    "industrials": "산업재",
    "industrial": "산업재",
    # 에너지
    "energy": "에너지",
    # 유틸리티
    "utilities": "유틸리티",
    "utility": "유틸리티",
    # 부동산
    "real estate": "부동산",
    "realestate": "부동산",
    # 소재
    "basic materials": "소재",
    "materials": "소재",
}


def normalize_us_sector(raw: Optional[str]) -> str:
    """영문 GICS sector → 한글. 매칭 실패 시 "기타"."""
    if not raw or not isinstance(raw, str):
        return "기타"
    key = re.sub(r"\s+", " ", raw.strip().lower())
    if not key:
        return "기타"
    return _US_SECTOR_MAP.get(key, "기타")


# ──────────────────────────────────────────────────────────────────────
# KR 14개 한글 라벨 (매크로 SSoT 자동 동기)
# ──────────────────────────────────────────────────────────────────────

def _load_kr_labels_from_macro() -> tuple[str, ...]:
    """macro_fetcher._KR_SECTOR_ETFS 의 name_ko 순서를 그대로 export.

    SSoT 보존을 위해 import-time 동기화. 매크로 정의 변경 시 본 모듈은 자동 추종.
    순환 import 방지를 위해 함수 내부 import.
    """
    from stock.macro_fetcher import _KR_SECTOR_ETFS  # noqa: WPS433
    return tuple(name_ko for _, _, name_ko in _KR_SECTOR_ETFS)


KR_SECTOR_LABELS: tuple[str, ...] = _load_kr_labels_from_macro()


# ──────────────────────────────────────────────────────────────────────
# KR 정규식 매핑 (다대일, 우선순위 순)
# REQ-BACK-002 — CLAUDE.md "키워드 검색은 정규식" 지침 준수
# ──────────────────────────────────────────────────────────────────────

# 라벨이 서로 어긋나지 않도록 패턴 정의 시 14 라벨 화이트리스트와 1:1 매칭.
# 순서가 중요 — 위에서부터 첫 매치 채택.
# 한글(KRX 업종명) + 영문 GICS sector/industry 패턴 혼합 — yfinance가 KR 종목에
# 영문 GICS 라벨을 반환하는 케이스(대다수)를 커버하기 위함.
_KR_REGEX_RULES: list[tuple[re.Pattern, str]] = [
    # 1. 반도체 — KRX "전기전자" + Semiconductors / Electronic Components / Consumer Electronics
    (re.compile(
        r"반도체|전기[\s·]?전자|디스플레이"
        r"|Semiconductors?|Electronic\s+Components?|Consumer\s+Electronics"
        r"|Hardware,?\s*Storage|Computer\s+Hardware",
        re.IGNORECASE), "반도체"),
    # 2. 2차전지 — IT 보다 우선
    (re.compile(r"2\s*차[\s]?전지|이차전지|배터리|Batteries|Battery", re.IGNORECASE),
     "2차전지"),
    # 3. 바이오/헬스케어 — Drug Manufacturers / Biotechnology / Medical Devices / Healthcare
    (re.compile(
        r"바이오|제약|의약|의료|헬스"
        r"|Drug\s+Manufacturers?|Biotech(?:nology)?|Pharmaceutical"
        r"|Medical\s+(?:Devices|Instruments|Care)|Health\s*Care|Healthcare",
        re.IGNORECASE), "바이오/헬스케어"),
    # 4. 은행/금융 — Banks / Insurance / Capital Markets / Financial Services
    (re.compile(
        r"은행|증권|보험|금융|카드|캐피탈"
        r"|Banks?(?:\s*-\s*\w+)?|Insurance|Capital\s+Markets"
        r"|Financial\s+Services?|Asset\s+Management|Credit\s+Services",
        re.IGNORECASE), "은행/금융"),
    # 5. 자동차 — KRX "운수장비" + Auto Manufacturers / Auto Parts
    (re.compile(
        r"자동차|운수장비|타이어|모비스"
        r"|Auto\s+(?:Manufacturers?|Parts|Components?|Dealerships?)"
        r"|Automobile|Tires?\b",
        re.IGNORECASE), "자동차"),
    # 6. 운송/물류 — KRX "운수창고업" + Airlines / Marine / Trucking / Railroads / Logistics
    (re.compile(
        r"운송|물류|항공운송|해운|택배|운수창고"
        r"|Airlines?|Marine\s+Shipping|Trucking|Railroads?"
        r"|Integrated\s+Freight|Logistics|Air\s+Freight",
        re.IGNORECASE), "운송/물류"),
    # 7. 미디어/엔터 — Entertainment / Broadcasting / Telecom / Communication
    # \bMedia\b 단어경계 — "Multimedia"(IT 게이밍)와 충돌 방지
    (re.compile(
        r"미디어|엔터|영화|방송|음악|콘텐츠"
        r"|Entertainment|Broadcasting|\bMedia\b|Publishing"
        r"|Telecom\s+Services?|Communication\s+Services?|Communications?",
        re.IGNORECASE), "미디어/엔터"),
    # 8. 필수소비재 — Packaged Foods / Beverages / Tobacco / Consumer Defensive
    (re.compile(
        r"필수소비|식품|음식료|생활용품|담배"
        r"|Packaged\s+Foods?|Beverages?(?:\s*-\s*\w+)?|Tobacco"
        r"|Household\s+(?:&\s*)?Personal\s+Products?"
        r"|Consumer\s+(?:Defensive|Staples)|Food\s+Distribution"
        r"|Confectioners|Farm\s+Products?",
        re.IGNORECASE), "필수소비재"),
    # 9. 경기소비재 — Apparel / Specialty Retail / Restaurants / Lodging / Consumer Cyclical
    (re.compile(
        r"경기소비|유통|화장품|패션|의류|레저|호텔|여행|섬유"
        r"|Apparel(?:\s+\w+)?|Specialty\s+Retail|Restaurants?"
        r"|Lodging|Resorts?\s*&\s*Casinos?|Travel\s+Services"
        r"|Personal\s+Services|Leisure|Footwear"
        r"|Consumer\s+Cyclical|Department\s+Stores"
        r"|Internet\s+Retail|Luxury\s+Goods",
        re.IGNORECASE), "경기소비재"),
    # 10. 건설 — Engineering & Construction / Building Materials / Construction
    (re.compile(
        r"건설|건자재"
        r"|Engineering\s*&\s*Construction|Construction(?:\s+\w+)?"
        r"|Building\s+Materials?|Building\s+Products|Cement",
        re.IGNORECASE), "건설"),
    # 11. 유틸리티 — Utilities (Regulated Electric/Gas/Water)
    (re.compile(
        r"유틸|가스|난방|상하수도"
        r"|Utilities?(?:\s*-\s*[\w\s]+)?|Water\s+Utilities?",
        re.IGNORECASE), "유틸리티"),
    # 12. 에너지/화학 — Oil & Gas / Chemicals / Energy / Renewable
    (re.compile(
        r"정유|석유|에너지|신재생|화학(?!소재)|전력(?!.*가스)"
        r"|Oil\s*&\s*Gas(?:\s+\w+)?|Petroleum|Energy(?!\s*(?:Equipment|Services))"
        r"|Specialty\s+Chemicals|Chemicals?\b|Coal|Solar"
        r"|Refineries|Pipelines",
        re.IGNORECASE), "에너지/화학"),
    # 13. 철강/소재 — Steel / Metals & Mining / Aluminum / Copper / Specialty Materials
    (re.compile(
        r"철강|금속|비철|화학소재|기초소재"
        r"|Steel|Metals?\s*&\s*Mining|Aluminum|Copper|Gold|Silver"
        r"|Other\s+Industrial\s+Metals|Other\s+Precious\s+Metals"
        r"|Paper(?:\s+\w+)?|Lumber|Basic\s+Materials?",
        re.IGNORECASE), "철강/소재"),
    # 14. IT/인터넷 — Software / Internet / Gaming / Information Technology
    (re.compile(
        r"IT|인터넷|소프트웨어|게임|플랫폼|서비스업"
        r"|Software(?:\s*-\s*\w+)?|Information\s+Technology(?:\s+Services)?"
        r"|Internet(?:\s+Content(?:\s*&\s*Information)?)?"
        r"|Electronic\s+Gaming|Gaming\s*&\s*Multimedia"
        r"|IT\s+Services?|SaaS|Cloud(?:\s+\w+)?"
        r"|Solution\s+Services|Tech(?:nology)?(?!\s*Hardware)",
        re.IGNORECASE), "IT/인터넷"),
]


def _match_kr_regex(raw: str) -> Optional[str]:
    """raw 문자열에 14 라벨 정규식을 순차 적용. 첫 매치 라벨 반환."""
    if not raw:
        return None
    for pattern, label in _KR_REGEX_RULES:
        if pattern.search(raw):
            return label
    return None


def _match_kr_combined(raw: Optional[str], industry: Optional[str]) -> Optional[str]:
    """industry → sector 순으로 14 라벨 매칭. industry가 더 세밀해 우선.

    yfinance/yf info에서 KR 종목은 영문 GICS sector(광역) + industry(세부)를 반환.
    industry가 sector보다 14 ETF 분류와 정합성 높아 먼저 시도.
    """
    if industry and isinstance(industry, str) and industry.strip():
        m = _match_kr_regex(industry.strip())
        if m:
            return m
    if raw and isinstance(raw, str) and raw.strip():
        m = _match_kr_regex(raw.strip())
        if m:
            return m
    return None


# ──────────────────────────────────────────────────────────────────────
# REQ-BACK-003: 종목코드 직접 매핑 (KR 70개)
# 프론트 KR_SECTOR_REPS 와 동일 — 매크로 SSoT 보존
# ──────────────────────────────────────────────────────────────────────

# (code, label) 튜플 리스트로 정의 → dict 변환. 가독성 우선.
_CODE_TO_KR_SECTOR_RAW: tuple[tuple[str, str], ...] = (
    # 반도체 (KODEX 091160)
    ("005930", "반도체"), ("000660", "반도체"), ("042700", "반도체"),
    ("240810", "반도체"), ("058470", "반도체"),
    # IT/인터넷 (KODEX 157490)
    ("035420", "IT/인터넷"), ("035720", "IT/인터넷"), ("018260", "IT/인터넷"),
    ("036570", "IT/인터넷"), ("251270", "IT/인터넷"),
    # 2차전지 (KODEX 305720)
    ("373220", "2차전지"), ("006400", "2차전지"), ("003670", "2차전지"),
    ("247540", "2차전지"), ("086520", "2차전지"),
    # 건설 (KODEX 117700)
    ("000720", "건설"), ("006360", "건설"), ("375500", "건설"),
    ("047040", "건설"), ("294870", "건설"),
    # 바이오/헬스케어 (KODEX 244580)
    ("207940", "바이오/헬스케어"), ("068270", "바이오/헬스케어"),
    ("000100", "바이오/헬스케어"), ("128940", "바이오/헬스케어"),
    ("326030", "바이오/헬스케어"),
    # 은행/금융 (KODEX 091170)
    ("105560", "은행/금융"), ("055550", "은행/금융"), ("086790", "은행/금융"),
    ("316140", "은행/금융"), ("323410", "은행/금융"),
    # 철강/소재 (KODEX 117680)
    ("005490", "철강/소재"), ("004020", "철강/소재"), ("103140", "철강/소재"),
    ("001230", "철강/소재"), ("014285", "철강/소재"),
    # 자동차 (KODEX 091180)
    ("005380", "자동차"), ("000270", "자동차"), ("012330", "자동차"),
    ("161390", "자동차"), ("204320", "자동차"),
    # 에너지/화학 (KODEX 117460)
    ("051910", "에너지/화학"), ("011170", "에너지/화학"),
    ("096770", "에너지/화학"), ("010950", "에너지/화학"),
    ("009830", "에너지/화학"),
    # 미디어/엔터 (KODEX 266390)
    ("035760", "미디어/엔터"), ("352820", "미디어/엔터"),
    ("041510", "미디어/엔터"), ("122870", "미디어/엔터"),
    ("253450", "미디어/엔터"),
    # 필수소비재 (KODEX 266410)
    ("033780", "필수소비재"), ("004370", "필수소비재"),
    ("271560", "필수소비재"), ("097950", "필수소비재"),
    ("007310", "필수소비재"),
    # 경기소비재 (KODEX 266420)
    ("008770", "경기소비재"), ("139480", "경기소비재"),
    ("004170", "경기소비재"), ("383220", "경기소비재"),
    ("090430", "경기소비재"),
    # 운송/물류 (KODEX 140710)
    ("003490", "운송/물류"), ("011200", "운송/물류"),
    ("000120", "운송/물류"), ("028670", "운송/물류"),
    ("002320", "운송/물류"),
    # 유틸리티 (KODEX 227550)
    ("015760", "유틸리티"), ("036460", "유틸리티"), ("018670", "유틸리티"),
    ("071320", "유틸리티"), ("004690", "유틸리티"),
)

_CODE_TO_KR_SECTOR: dict[str, str] = dict(_CODE_TO_KR_SECTOR_RAW)


def normalize_kr_sector(
    raw: Optional[str],
    code: Optional[str] = None,
    industry: Optional[str] = None,
) -> str:
    """KR 종목 sector raw + 코드 → 14 한글 라벨.

    우선순위:
      1. ``code`` 가 70개 화이트리스트에 있으면 즉시 반환 (정규식보다 우선).
      2. ``industry`` (더 세밀) → ``raw`` 정규식 14 패턴 순차 매치.
      3. 모두 실패 → "기타".

    Args:
        raw: yfinance/pykrx/DART 등에서 받은 sector 문자열 (None/공백 허용)
        code: KR 종목코드 (6자리 또는 7자리). 코드 직접 매핑 화이트리스트 조회용.
        industry: yfinance ``info.industry`` 같은 세부 분류 (있으면 sector보다 우선)

    Returns:
        14개 라벨 중 하나 또는 "기타".
    """
    # 1. 코드 직접 매핑 (KR_SECTOR_REPS 70개 — 매크로 SSoT 정합)
    if code:
        normalized_code = str(code).strip().upper().lstrip("0").rjust(6, "0")
        if normalized_code in _CODE_TO_KR_SECTOR:
            return _CODE_TO_KR_SECTOR[normalized_code]
        # 원본도 그대로 시도 (이미 6자리이거나 변형된 형태)
        plain = str(code).strip().upper()
        if plain in _CODE_TO_KR_SECTOR:
            return _CODE_TO_KR_SECTOR[plain]

    # 2. industry → sector 순으로 정규식 매핑 (industry가 GICS sub로 더 세밀)
    label = _match_kr_combined(raw, industry)
    if label:
        return label

    # 3. 폴백 (Graham 보수 원칙 — false 매핑 회피)
    return "기타"


# ──────────────────────────────────────────────────────────────────────
# 통합 진입점
# ──────────────────────────────────────────────────────────────────────

def normalize_sector(
    raw: Optional[str],
    market: str,
    code: Optional[str] = None,
    industry: Optional[str] = None,
) -> str:
    """sector raw + market → 한글 화이트리스트 라벨.

    Args:
        raw: 원본 sector 문자열 (None/공백 허용)
        market: "KR" | "US" (대소문자 무관)
        code: 종목코드 (KR 직접 매핑용, 옵션)
        industry: 세부 industry (KR에서 sector보다 우선 매칭, 옵션)

    Returns:
        14(KR)/11(US) 한글 라벨 중 하나 또는 "기타".
        market 인식 불가 → "기타".
    """
    market_upper = (market or "").strip().upper()
    if market_upper == "KR":
        return normalize_kr_sector(raw, code=code, industry=industry)
    if market_upper == "US":
        # US는 industry 폴백 — sector 미매칭 시 industry로 한 번 더 시도
        label = normalize_us_sector(raw)
        if label != "기타":
            return label
        if industry:
            return normalize_us_sector(industry)
        return "기타"
    return "기타"


# ──────────────────────────────────────────────────────────────────────
# REQ-BACK-005: 캐시 wrapper (레이어 분리)
# normalize_sector 자체는 순수 함수. 캐시는 별도 함수에서 처리.
# ──────────────────────────────────────────────────────────────────────

_CACHE_TTL_HOURS = 24 * 30  # 30일


def cache_key(market: str, code: str) -> str:
    """캐시 키 빌더. ``sector_norm:{MARKET}:{CODE}`` (대문자 정규화)."""
    return f"sector_norm:{(market or '').strip().upper()}:{(code or '').strip().upper()}"


def normalize_sector_cached(
    raw: Optional[str],
    market: str,
    code: Optional[str],
) -> str:
    """정규화 결과를 cache.db에 30일 TTL로 저장하는 wrapper.

    캐시 hit → 저장된 한글 라벨 즉시 반환.
    캐시 miss 또는 만료 → ``normalize_sector()`` 실행 + write-through.

    Args:
        raw: 원본 sector
        market: "KR" | "US"
        code: 종목코드 (필수 — 캐시 키 일부)

    Returns:
        한글 라벨 (14/11/"기타").
    """
    # 코드 없으면 캐시 비활성 (키 미생성)
    if not code:
        return normalize_sector(raw, market)

    from stock import cache as _cache  # 지연 import (테스트 격리)
    from stock.db_base import now_kst_iso  # KST helper

    key = cache_key(market, code)
    hit = _cache.get_cached(key)
    if isinstance(hit, dict) and hit.get("sector"):
        sector = hit["sector"]
        # 화이트리스트 보증 — 만료 후 재검증
        if sector in KR_SECTOR_LABELS or sector in US_SECTOR_LABELS or sector == "기타":
            return sector

    label = normalize_sector(raw, market, code=code)
    source = "code_map" if (code and label != "기타" and (market or "").upper() == "KR"
                            and str(code).strip().upper() in _CODE_TO_KR_SECTOR) else "regex"
    if not raw and label != "기타":
        source = "code_map"

    payload = {
        "sector": label,
        "raw": raw or "",
        "source": source,
        "normalized_at": now_kst_iso(),
    }
    try:
        _cache.set_cached(key, payload, ttl_hours=_CACHE_TTL_HOURS)
    except Exception:
        # 캐시 실패는 정규화 결과에 영향 없음
        pass
    return label
