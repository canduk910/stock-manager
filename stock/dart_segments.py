"""DART 사업보고서 본문 직접 파싱 — 사업부문별 매출비중 실측 추출 (Phase B).

2026-05-10 ValueScreener 자문: GPT 통합 추론(Phase A)의 신빙성 한계 해소.
DART `document.xml` API → ZIP/XML → "영업의 현황" 섹션 → 부문별 매출 표 추출.
GPT는 표 정규화에만 사용 (회사별 명칭 통일 + 비중% 계산).

확정 데이터 흐름:
1. fetch_filings(corp_code=...)로 해당 연도 사업보고서 rcept_no 조회
2. /api/document.xml?rcept_no=... → ZIP 응답 (`{rcept_no}.xml` 단일 파일)
3. XML 5MB 중 "영업의 현황" 섹션(≤300KB) 추출
4. <TABLE> 후보 식별 (매출/영업/부문 키워드 포함)
5. GPT 1회 호출로 정규화 (segments + 비중%)
6. 캐시 TTL 7일 (사업보고서는 연 1회 공시)

Source/confidence 메타:
- 성공: source="dart_parsed", confidence="high"
- 실패 (corp_code 미존재, 본문 다운 실패, 표 미발견 등): None 반환 → 호출자 GPT fallback
"""

from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from datetime import date
from typing import Optional

import requests

from config import OPENAI_API_KEY
from stock.cache import get_cached, set_cached
from stock.dart_fin import _fetch_corp_code

logger = logging.getLogger(__name__)


_DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"
_DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
_DART_HEADERS = {"Connection": "close"}
_CACHE_TTL_HOURS = 24 * 7  # 사업보고서 연 1회 공시 → 7일 캐시

# 매출 표 후보 식별 패턴 (정규식, CLAUDE.md "키워드 검색은 정규식" 지침 준수)
# `\s*` 자동 흡수로 띄어쓰기 변형 모두 매칭. 단순 `keyword in text` 회피.
_REVENUE_TABLE_PATTERNS = [
    re.compile(r"사업\s*부문"),
    re.compile(r"영업\s*부문"),
    re.compile(r"사업의\s*개요"),
    re.compile(r"주요\s*매출"),
    re.compile(r"매출\s*현황"),
    re.compile(r"보험\s*영업\s*수익"),
    re.compile(r"보험\s*손익"),
    re.compile(r"장기\s*보험"),
    re.compile(r"자동차\s*보험"),
    re.compile(r"일반\s*보험"),
    re.compile(r"수익\s*현황"),
    re.compile(r"부문별"),
    re.compile(r"제품별"),
    re.compile(r"서비스별"),
]

# 사업의 내용 섹션 시작 패턴 (정규식)
# DART 헤더 변형 자동 흡수: ROMAN/한자(II↔Ⅱ), 띄어쓰기, 점/공백 유무.
# 215000 골프존 2025년 보고서 케이스(2026-05-10 진단): 단순 string match로
# 헤더 변형 미흡수 → 섹션 추출 실패. 정규식으로 일괄 해소.
_REVENUE_SECTION_PATTERNS = [
    re.compile(r"[IⅡ]{1,2}\s*\.?\s*사업의\s*내용"),  # II. / Ⅱ. / II 사업의 내용
    re.compile(r"영업의\s*현황"),
    re.compile(r"사업의\s*개요"),
    re.compile(r"주요\s*사업\s*부문"),
    re.compile(r"매출\s*및\s*수주\s*상황"),
    re.compile(r"주요\s*제품\s*및\s*서비스"),
]

# 다음 큰 섹션 헤더 (사업의 내용 섹션 종료)
_NEXT_SECTION_PATTERNS = [
    re.compile(r"[IⅢ]{1,3}\s*\.?\s*재무에\s*관한\s*사항"),  # III. / Ⅲ. / III 재무에 관한 사항
    re.compile(r"감사인의\s*감사"),
    re.compile(r"주주에\s*관한\s*사항"),
]


# ── 1. DART 사업보고서 rcept_no 조회 ─────────────────────────────────────


def _get_api_key() -> Optional[str]:
    import os
    return os.environ.get("OPENDART_API_KEY")


def _find_business_report_rcept(corp_code: str, bsns_year: int) -> Optional[str]:
    """해당 연도 사업보고서의 rcept_no 조회.

    DART 정책: 사업보고서는 사업연도 종료 후 다음해 3월 말까지 공시.
    예: 2024년 사업보고서 → 2025-01-01 ~ 2025-06-30 사이 공시.
    검색 범위: 사업연도 다음해 1~6월 + 정정공시 대비 다음해 12월까지.
    """
    api_key = _get_api_key()
    if not api_key or not corp_code:
        return None

    bgn_de = f"{bsns_year + 1}0101"
    end_de = f"{bsns_year + 1}1231"
    try:
        resp = requests.get(
            _DART_LIST_URL,
            params={
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bgn_de": bgn_de,
                "end_de": end_de,
                "pblntf_ty": "A",
                "page_count": 50,
            },
            timeout=15,
            headers=_DART_HEADERS,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != "000":
            return None
        for item in data.get("list", []):
            report_nm = item.get("report_nm", "")
            # "사업보고서 (2024.12)" 또는 "[기재정정]사업보고서 (2024.12)" 매칭
            if "사업보고서" in report_nm and f"{bsns_year}.12" in report_nm:
                return item.get("rcept_no")
        # 12월 표기 없을 시 첫 사업보고서
        for item in data.get("list", []):
            if "사업보고서" in item.get("report_nm", ""):
                return item.get("rcept_no")
    except Exception as e:
        logger.debug("rcept_no 조회 실패 (corp=%s, year=%d): %s", corp_code, bsns_year, e)
    return None


# ── 2. DART document.xml 다운로드 + 영업의 현황 섹션 추출 ───────────────


def _download_business_report_xml(rcept_no: str) -> Optional[str]:
    """document.xml ZIP 다운로드 → 본문 XML 반환.

    DART ZIP은 보고서별로 1~3개 파일 포함:
    - `{rcept_no}.xml` (suffix 없음) = 본문 (사업의 내용·영업의 현황 등 모든 섹션)
    - `{rcept_no}_00xxx.xml` (suffix 있음) = 첨부 (재무제표만, 영업의 현황 없음)

    2026-05-10 결함: 215000 골프존 2025년 사업보고서가 첨부 2개+본문 1개 구조였는데
    `names[0]`(첫 파일)이 첨부였음 → 영업의 현황 헤더 미발견 → 표 추출 0개.
    수정: suffix 없는 본문 우선 → 없으면 가장 큰 파일(폴백).
    """
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        resp = requests.get(
            _DART_DOCUMENT_URL,
            params={"crtfc_key": api_key, "rcept_no": rcept_no},
            timeout=30,
            headers=_DART_HEADERS,
        )
        if resp.status_code != 200 or not resp.content:
            return None
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        if not names:
            return None
        # 1순위: {rcept_no}.xml 정확 매칭 (본문)
        target = f"{rcept_no}.xml"
        if target in names:
            return zf.read(target).decode("utf-8", errors="replace")
        # 2순위 폴백: 가장 큰 파일 (보통 본문이 가장 풍부)
        largest = max(names, key=lambda n: zf.getinfo(n).file_size)
        return zf.read(largest).decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, requests.RequestException, KeyError) as e:
        logger.debug("document.xml 다운로드 실패 (rcept=%s): %s", rcept_no, e)
        return None


def _extract_revenue_section(xml: str) -> Optional[str]:
    """XML 5MB 중 "사업의 내용" 섹션 추출 (정규식 기반).

    DART 본문 XML 구조: 헤더가 **목차**와 **본문**에 2회 등장 + 회사별 띄어쓰기/
    한자(II↔Ⅱ) 변형. 정규식으로 변형 흡수 + `finditer`의 가장 마지막 매칭으로
    본문 우선. 종료 헤더는 시작점 +2000자 이후 가장 늦은 매칭 (목차 회피).
    """
    if not xml:
        return None

    # 모든 패턴의 모든 매칭 위치 수집 → 가장 이른 위치 = 가장 큰 부모 섹션
    candidates = []
    for pattern in _REVENUE_SECTION_PATTERNS:
        matches = list(pattern.finditer(xml))
        if matches:
            # 같은 패턴이 목차/본문 2회 등장 시 마지막(=본문) 위치 사용
            candidates.append(matches[-1].start())
    if not candidates:
        return None
    start = min(candidates)  # 가장 이른 위치 = 가장 큰 부모 섹션

    end = len(xml)
    for pattern in _NEXT_SECTION_PATTERNS:
        # 시작점 이후 가장 늦은 매칭 (목차 회피, 본문 종료 위치)
        # 단 start와 너무 가까우면(<2000자) 목차 인접 → 무시
        for m in pattern.finditer(xml):
            pos = m.start()
            if pos > start + 2000 and pos < end:
                end = pos

    section = xml[start:end]
    # 너무 크면 잘라냄 (GPT 토큰 절약)
    return section[:500_000] if len(section) > 500_000 else section


# ── 3. <TABLE> 후보 추출 + 평탄화 ────────────────────────────────────────


_TABLE_RE = re.compile(r"<TABLE[^>]*>(.*?)</TABLE>", re.DOTALL)
_ROW_RE = re.compile(r"<TR[^>]*>(.*?)</TR>", re.DOTALL)
_CELL_RE = re.compile(r"<T[DH][^>]*>(.*?)</T[DH]>", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _table_to_text(table_xml: str) -> str:
    """단일 <TABLE> XML → 행/열 정규화 텍스트 (GPT 입력용).

    각 행은 ` | ` 구분, 행 사이는 줄바꿈. HTML 엔티티/태그 제거.
    """
    rows_text = []
    for row_match in _ROW_RE.finditer(table_xml):
        cells = _CELL_RE.findall(row_match.group(1))
        cell_texts = [_WS_RE.sub(" ", _TAG_RE.sub("", c)).strip() for c in cells]
        if any(cell_texts):
            rows_text.append(" | ".join(cell_texts))
    return "\n".join(rows_text)


def _section_to_text(section_xml: str) -> str:
    """섹션 XML 전체 → 태그 제거 + 공백 정규화 텍스트.

    표 후보 추출이 실패한 경우 GPT 폴백 입력용. 보험사 등 표 구조가 단순
    매출비중 형태가 아닐 때 섹션 전체에서 GPT가 직접 추론.
    """
    if not section_xml:
        return ""
    text = _TAG_RE.sub(" ", section_xml)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def _extract_table_candidates(section_xml: str, max_tables: int = 5) -> list[str]:
    """매출/부문 키워드 포함 표만 후보. 최대 max_tables개 (GPT 토큰 절약)."""
    candidates: list[tuple[int, str]] = []  # (키워드 점수, 표 텍스트)
    for m in _TABLE_RE.finditer(section_xml):
        table_xml = m.group(0)
        text = _table_to_text(table_xml)
        if not text or len(text) < 50:
            continue
        # 행 5개 미만 또는 1500자 초과는 제외 (목차/장식 또는 너무 큰 표)
        if text.count("\n") < 4 or len(text) > 4000:
            continue
        score = sum(1 for p in _REVENUE_TABLE_PATTERNS if p.search(text))
        if score >= 1:
            candidates.append((score, text))
    candidates.sort(key=lambda x: -x[0])
    return [text for _, text in candidates[:max_tables]]


# ── 4. GPT 표 정규화 ─────────────────────────────────────────────────────


def _normalize_with_gpt(
    table_texts: list[str],
    bsns_year: int,
    name: str,
    user_id: Optional[int],
) -> Optional[list[dict]]:
    """표 텍스트들 → 표준 JSON segments. 1회 호출.

    반환: [{segment, revenue_pct, raw_amount?}] 또는 None (실패).
    """
    if not table_texts or not OPENAI_API_KEY:
        return None

    try:
        from services.ai_gateway import call_openai_chat

        joined = "\n\n---\n\n".join(table_texts)
        system_prompt = (
            "당신은 한국 가치투자 자문 시스템의 사업부문 추출 보조다. "
            "DART 사업보고서 본문에서 추출한 표를 입력으로 받아, "
            "사업부문별 매출(또는 영업수익) 비중을 표준 JSON으로 정규화한다. "
            "표에 명시된 수치만 사용하고 추측하지 않는다. 부문 명칭은 표 원문 그대로 보존한다."
        )
        user_prompt = (
            f"{name}의 {bsns_year}년 사업보고서 표에서 사업부문별 매출비중을 추출해 JSON으로:\n"
            f"{{\"segments\": [{{\"segment\": \"부문명\", \"revenue_pct\": 숫자, \"raw_amount\": 숫자(원)}}]}}\n"
            f"규칙:\n"
            f"- 합계 100 (반올림 오차 ±0.5 허용)\n"
            f"- 상위 4개 부문만 (나머지는 '기타'로 통합)\n"
            f"- raw_amount 있으면 원 단위, 없으면 null\n"
            f"- 부문 매출표가 없으면 빈 배열 반환\n\n"
            f"표 입력:\n{joined}"
        )

        resp = call_openai_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            user_id=user_id,
            service_name="segments_dart_normalize",
            max_completion_tokens=800,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        raw_segs = data.get("segments") or []
        if not isinstance(raw_segs, list) or not raw_segs:
            return None

        result = []
        for s in raw_segs[:4]:
            if not isinstance(s, dict):
                continue
            seg_name = s.get("segment") or ""
            pct = s.get("revenue_pct") or 0
            try:
                result.append({
                    "segment": str(seg_name),
                    "revenue_pct": float(pct),
                    "raw_amount": s.get("raw_amount"),
                    "note": "DART실측",
                })
            except (TypeError, ValueError):
                continue
        return result if result else None
    except Exception as e:
        logger.debug("GPT 정규화 실패 (%s, %d): %s", name, bsns_year, e)
        return None


# ── 5. 단일 연도 진입점 ─────────────────────────────────────────────────


def fetch_segments_dart_single(
    corp_code: str,
    name: str,
    bsns_year: int,
    user_id: Optional[int] = None,
) -> Optional[list[dict]]:
    """단일 연도 DART 사업보고서 본문 파싱.

    캐시 키: dart:segments:{corp_code}:{bsns_year}
    실패 시 None 반환 (호출자가 GPT fallback 결정).
    """
    if not corp_code:
        return None

    cache_key = f"dart:segments:{corp_code}:{bsns_year}"
    cached = get_cached(cache_key)
    if cached is not None:
        # 캐시된 빈 결과(False/[])도 그대로 반환 — 재시도 회피
        return cached or None

    rcept_no = _find_business_report_rcept(corp_code, bsns_year)
    if not rcept_no:
        set_cached(cache_key, [], ttl_hours=24)  # 1일 stale (정정공시 대비)
        return None

    xml = _download_business_report_xml(rcept_no)
    if not xml:
        set_cached(cache_key, [], ttl_hours=6)  # 6시간 stale (네트워크 장애 회복)
        return None

    section = _extract_revenue_section(xml)
    if not section:
        set_cached(cache_key, [], ttl_hours=24)
        return None

    # 1차: 표 후보 추출 + GPT 정규화 (저비용)
    candidates = _extract_table_candidates(section)
    segments = None
    if candidates:
        segments = _normalize_with_gpt(candidates, bsns_year, name, user_id)

    # 2차 폴백: 표 추출 실패 시 섹션 텍스트 전체 GPT 입력
    # 보험사처럼 부문별 매출표가 단순 표 추출로 안 잡히는 경우 보강.
    # 토큰 비용 ↑ (≤16K input) 이지만 신빙성 향상.
    if not segments:
        section_text = _section_to_text(section)
        if section_text:
            segments = _normalize_with_gpt([section_text[:30000]], bsns_year, name, user_id)

    if not segments:
        set_cached(cache_key, [], ttl_hours=6)
        return None

    set_cached(cache_key, segments, ttl_hours=_CACHE_TTL_HOURS)
    return segments


# ── 6. 5년치 통합 진입점 (2026-05-10 사용자 결정) ──────────────────────
# SK이노베이션(096770) 결함: 연도별 따로 GPT 호출 시 부문 명칭 완전 불일치
# (2022 석유/기타/기초유화 합계 158% / 2023 경유/무연휘발유 / 2025 기초유화/화학소재).
# 해결: 5년치 표를 1회 프롬프트로 통합 정규화 — 동일 부문명 강제 + 합계 100% 일관.


def _extract_year_tables(corp_code: str, year: int) -> list[str]:
    """단일 연도 사업보고서 표 후보 추출 (GPT 호출 없음).

    rcept_no 조회 → document.xml 다운로드 → 영업의 현황 섹션 → 표 후보.
    실패 시 빈 리스트.
    """
    rcept_no = _find_business_report_rcept(corp_code, year)
    if not rcept_no:
        return []
    xml = _download_business_report_xml(rcept_no)
    if not xml:
        return []
    section = _extract_revenue_section(xml)
    if not section:
        return []
    candidates = _extract_table_candidates(section)
    if not candidates:
        # 2차 폴백: 섹션 텍스트 전체 (보험사 등 표 구조 비정형)
        section_text = _section_to_text(section)
        if section_text:
            return [section_text[:25000]]
        return []
    return candidates


def _normalize_history_unified(
    tables_per_year: dict[int, list[str]],
    name: str,
    user_id: Optional[int],
) -> Optional[dict]:
    """N년치 표 통합 정규화 — GPT 1회 호출. 동일 부문명 강제.

    2026-05-10 사용자 결정: description + keywords도 같은 호출에서 함께 추출.
    DART 부문별 매출표를 컨텍스트로 받으므로 회사명 단독 추정보다 신빙성↑.

    핵심 결함 해소:
    - 연도별 명칭 불일치 (2022 석유/2023 경유 → 통일 '석유사업')
    - 큰 부문 + 세부 부문 중복으로 합계 100% 초과
    - 신규 진입/철수 사업 0% 또는 등장 반영

    Returns: {
        "years": {year: [segments]} 매핑,
        "description": "사업 설명 2~3문장",
        "keywords": ["키워드1", ...]
    } 또는 None (실패).
    """
    if not tables_per_year or not OPENAI_API_KEY:
        return None

    # 연도별 입력 블록 직렬화 (연도당 표 최대 3개)
    input_blocks = []
    for year in sorted(tables_per_year.keys()):
        tables = tables_per_year.get(year) or []
        if not tables:
            continue
        block_text = "\n\n".join(tables[:3])
        input_blocks.append(f"### {year}년 사업보고서\n{block_text}")
    if not input_blocks:
        return None
    joined = "\n\n===\n\n".join(input_blocks)
    # 토큰 보호 (gpt-5.4 기준 약 100K input). 한국어 평균 5자/토큰 → 60K 자 ≈ 12K 토큰.
    if len(joined) > 60000:
        joined = joined[:60000]

    try:
        from services.ai_gateway import call_openai_chat

        system_prompt = (
            "당신은 한국 가치투자 자문 시스템의 사업부문 정규화 전문가다. "
            "DART 사업보고서 N년치 표를 입력으로 받아, 사업부문별 매출비중 + 사업 개요 + "
            "투자 테마 키워드를 표준 JSON으로 통합 정규화한다.\n\n"
            "핵심 규칙 (절대 위반 금지):\n"
            "1. **동일 부문명 강제**: 모든 연도에서 같은 사업은 동일한 부문명 사용. "
            "예: 2022 '경유'/'무연휘발유'/'석유사업'은 모두 '석유사업'으로 통일. "
            "회사가 제시한 큰 분류(세그먼트) 기준으로 표준화.\n"
            "2. **각 연도 합계 100%** (반올림 ±0.5 허용). 100% 초과 절대 금지.\n"
            "3. **중복 추출 금지**: 큰 부문 + 그 안의 세부 부문을 동시 포함 금지. "
            "예: '화학사업' 와 '기초유화사업'(화학의 세부)을 동시 추출 금지 → "
            "'화학사업' 한 가지만 사용.\n"
            "4. **신규 진입/철수 사업도 명시**: 어떤 연도에 0% 또는 등장으로 반영해 추세 추적 가능.\n"
            "5. **표에 명시된 수치만 사용**, 추측/외삽 금지. 해당 연도 표가 부실하면 그 연도 누락.\n"
            "6. 부문 수: 회사 사업 구조에 맞는 수 (보통 3~5개). 불필요한 세부 분리 금지.\n"
            "7. **description**: DART 표 데이터 + 회사명 기반 회사 설명 2~3문장. 한국어. "
            "주요 사업 + 비중 변화/주목 포인트 포함. 단정 어조 금지.\n"
            "8. **keywords**: 투자 테마/키워드 5~8개 배열 (예: 반도체, 정유, 2차전지, "
            "친환경에너지). 표 데이터에 등장하는 사업 키워드 우선.\n"
            "9. **유사 명칭 자동 통합** (추세 추적 핵심): 의미가 유사한 부문 명칭은 "
            "가장 표준적인 형태로 적극적으로 통일. 작은 표기 차이(접미사/조사/축약형)는 "
            "동일 사업으로 간주. 통일 예시:\n"
            "   - '장기' / '장기보험' / '장기보험부문' / '장기보장성' → '장기보험'\n"
            "   - '자동차' / '자동차보험' / '자동차보험부문' → '자동차보험'\n"
            "   - 'DX' / 'DX 부문' / 'DX사업부' / '디바이스경험' → 'DX 부문'\n"
            "   - '석유' / '석유사업' / '정유' / '에너지' / '경유' / '무연휘발유' → "
            "(회사가 큰 분류로 묶었으면) '석유사업'\n"
            "   - '기초유화' / '기초유화사업' / '기초유분' → '기초유화사업'\n"
            "   - '화학' / '화학사업' / '화학소재' → '화학사업'\n"
            "   - '반도체' / '반도체부문' / 'DS 부문' → 'DS 부문'\n"
            "   원칙: 5년 모두 비교 가능해야 함. 같은 사업이 연도마다 다른 이름으로 나오면 "
            "추세 추적 불가능 → 적극적 통합. 단 본질적으로 다른 사업(예: '보험' vs '투자')은 "
            "절대 통합 금지.\n"
            "10. **파이차트와 추이차트 일관성**: 응답의 사업부문 명칭은 사업 개요 description "
            "에서 언급한 사업명과도 일치해야 함. 파이차트(최신 연도 segments)와 5년 추이 "
            "차트가 동일한 부문명을 보여주도록 작성.\n"
        )
        user_prompt = (
            f"{name}의 N년치 사업보고서 표를 받았습니다. "
            f"위 8개 규칙을 엄격히 따라 매출비중 + 사업 개요 + 키워드를 JSON으로 정규화하세요.\n\n"
            f"형식:\n"
            f"{{\n"
            f"  \"years_data\": [{{\"year\": 2024, \"segments\": "
            f"[{{\"segment\": \"부문명\", \"revenue_pct\": 숫자, \"raw_amount\": 숫자|null}}]}}, ...],\n"
            f"  \"description\": \"회사 설명 2~3문장\",\n"
            f"  \"keywords\": [\"키워드1\", \"키워드2\", ...]\n"
            f"}}\n\n"
            f"입력 표 (연도별 ===로 구분):\n{joined}"
        )

        resp = call_openai_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            user_id=user_id,
            service_name="segments_dart_normalize",
            max_completion_tokens=2500,  # 5년 × 5부문 × 3필드
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        raw_years = data.get("years_data") or []
        if not isinstance(raw_years, list):
            return None

        years_result: dict[int, list[dict]] = {}
        for entry in raw_years:
            if not isinstance(entry, dict):
                continue
            try:
                year = int(entry.get("year"))
            except (TypeError, ValueError):
                continue
            raw_segs = entry.get("segments") or []
            if not isinstance(raw_segs, list):
                continue
            segs = []
            for s in raw_segs[:5]:  # 5개까지 허용 (정합성 우선)
                if not isinstance(s, dict):
                    continue
                seg_name = s.get("segment") or ""
                pct = s.get("revenue_pct") or 0
                if not seg_name:
                    continue
                try:
                    segs.append({
                        "segment": str(seg_name),
                        "revenue_pct": float(pct),
                        "raw_amount": s.get("raw_amount"),
                        "note": "DART실측",
                    })
                except (TypeError, ValueError):
                    continue
            # 합계 100% 검증 — 100.5 초과 시 비례 재정규화 (GPT 가드 위반 fallback)
            total = sum(s["revenue_pct"] for s in segs)
            if 0 < total and total > 100.5:
                for s in segs:
                    s["revenue_pct"] = round(s["revenue_pct"] / total * 100, 1)
            if segs:
                years_result[year] = segs

        if not years_result:
            return None

        # description/keywords 추출 (GPT 통합 응답)
        description = data.get("description", "") if isinstance(data, dict) else ""
        keywords = data.get("keywords", []) if isinstance(data, dict) else []
        if not isinstance(keywords, list):
            keywords = []

        return {
            "years": years_result,
            "description": str(description)[:500] if description else "",
            "keywords": [str(k)[:30] for k in keywords[:8] if k],
        }
    except Exception as e:
        logger.debug("통합 정규화 실패 (%s): %s", name, e)
        return None


def fetch_segments_history_dart(
    code: str,
    name: str,
    *,
    years: int = 5,
    user_id: Optional[int] = None,
) -> dict:
    """N년치 DART 사업보고서 본문 파싱 + 통합 정규화. GPT 호출 1회.

    캐시 키: advisor:segments_history_dart:{code}:{years}
    """
    cache_key = f"advisor:segments_history_dart:{code}:{years}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    empty = {
        "years_data": [],
        "highlights": {"growing": [], "shrinking": []},
        "confidence": "high",
        "source": "dart_parsed",
        "covered_years": 0,
    }

    corp_code = _fetch_corp_code(code)
    if not corp_code:
        return empty

    latest_year = date.today().year - 1
    # 1. 각 연도별 표 추출 (GPT 호출 없음)
    tables_per_year: dict[int, list[str]] = {}
    for y in range(latest_year - years + 1, latest_year + 1):
        tables = _extract_year_tables(corp_code, y)
        if tables:
            tables_per_year[y] = tables

    if not tables_per_year:
        return empty

    # 2. 5년치 통합 GPT 1회 호출 (segments + description + keywords)
    normalized = _normalize_history_unified(tables_per_year, name, user_id)
    if not normalized or not normalized.get("years"):
        return empty

    years_map = normalized["years"]
    years_data = [
        {"year": y, "segments": years_map[y]}
        for y in sorted(years_map.keys())
    ]

    # 3. highlights 계산 (Phase A와 동일 ±5%p 임계)
    from stock.advisory_fetcher import _compute_segments_highlights

    result = {
        "years_data": years_data,
        "highlights": _compute_segments_highlights(years_data),
        "description": normalized.get("description", ""),  # DART 표 기반 사업 개요
        "keywords": normalized.get("keywords", []),         # DART 표 기반 키워드
        "confidence": "high",
        "source": "dart_parsed",
        "covered_years": len(years_data),
    }
    set_cached(cache_key, result, ttl_hours=_CACHE_TTL_HOURS)
    return result
