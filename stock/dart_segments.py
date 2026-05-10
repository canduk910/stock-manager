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

# 매출 표 후보 식별 키워드 (보험/제조업/금융업 공통 패턴)
_REVENUE_TABLE_KEYWORDS = [
    "사업부문", "영업부문", "사업의 개요", "주요 매출",
    "매출 현황", "보험영업수익", "보험손익", "장기보험", "자동차보험", "일반보험",
    "수익 현황", "부문별", "제품별", "서비스별",
]

# 영업의 현황 섹션 시작 패턴 (DART 사업보고서 표준)
_REVENUE_SECTION_HEADERS = [
    "영업의 현황",
    "사업의 개요",
    "주요 사업부문",
]

# 다음 큰 섹션 헤더 (영업의 현황 종료 추정)
_NEXT_SECTION_HEADERS = [
    "III. 재무에 관한 사항",
    "Ⅲ. 재무에 관한 사항",
    "III.재무에 관한 사항",
    "감사인의 감사",
    "주주에 관한 사항",
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
    """document.xml ZIP 다운로드 → XML 본문 반환."""
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
        # 첫 XML 파일 사용 (보통 {rcept_no}.xml 단일)
        return zf.read(names[0]).decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, requests.RequestException, KeyError) as e:
        logger.debug("document.xml 다운로드 실패 (rcept=%s): %s", rcept_no, e)
        return None


def _extract_revenue_section(xml: str) -> Optional[str]:
    """XML 5MB 중 "영업의 현황" 섹션(≤300KB) 추출.

    헤더 매칭 → 다음 큰 섹션 헤더까지. 둘 다 못 찾으면 None.
    """
    if not xml:
        return None

    start = -1
    for header in _REVENUE_SECTION_HEADERS:
        pos = xml.find(header)
        if pos != -1:
            start = pos
            break
    if start == -1:
        return None

    end = len(xml)
    for next_header in _NEXT_SECTION_HEADERS:
        # start + 1로 검색 — 동일 헤더 직후도 다음 섹션 인정
        pos = xml.find(next_header, start + 1)
        if pos != -1 and pos < end:
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
        score = sum(1 for kw in _REVENUE_TABLE_KEYWORDS if kw in text)
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


# ── 6. 5년치 통합 진입점 ────────────────────────────────────────────────


def fetch_segments_history_dart(
    code: str,
    name: str,
    *,
    years: int = 5,
    user_id: Optional[int] = None,
) -> dict:
    """N년치 DART 사업보고서 본문 파싱 통합. 호출자(advisory_fetcher)가 사용.

    캐시 키: advisor:segments_history_dart:{code}:{years}
    반환:
        {
            "years_data": [{"year": int, "segments": [{segment, revenue_pct, raw_amount, note}]}, ...],
            "highlights": {"growing": [...], "shrinking": [...]},
            "confidence": "high",
            "source": "dart_parsed",
            "covered_years": int,  # 실제 DART 파싱 성공 연도 수
        }
    실패 (전체) 시 빈 years_data 반환.
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
    years_data = []
    for y in range(latest_year - years + 1, latest_year + 1):
        segs = fetch_segments_dart_single(corp_code, name, y, user_id=user_id)
        if segs:
            years_data.append({"year": y, "segments": segs})

    if not years_data:
        return empty

    # highlights 계산 (Phase A와 동일 ±5%p 임계)
    from stock.advisory_fetcher import _compute_segments_highlights

    result = {
        "years_data": years_data,
        "highlights": _compute_segments_highlights(years_data),
        "confidence": "high",
        "source": "dart_parsed",
        "covered_years": len(years_data),
    }
    set_cached(cache_key, result, ttl_hours=_CACHE_TTL_HOURS)
    return result
