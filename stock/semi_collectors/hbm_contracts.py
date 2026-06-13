"""지표 5 — HBM 공시 일일 스캔.

DART 주요사항보고(B) 일일 스캔 + 정규식 매칭:
- 1차 필터: report_nm ~= "단일판매·공급계약체결"
- 2차 필터: keyword_regex 매칭 (semi_thresholds 에서 동적 로드)
- 발행회사: 삼성전자(00126380) / SK하이닉스(00164779) 한정

멱등성: 동일 observed_at 호출 시 같은 row upsert (rcept_no set 누적).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from db.session import get_session
from db.repositories.semiconductor_repo import SemiconductorRepository
from stock.semi_collectors.base import CollectorResult

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))

# DART 주요사항보고 (Major Reports)
_DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"

# 메모리 2사 corp_code (DART 고유번호 8자리)
_TARGETS = {
    "00126380": ("삼성전자", "005930"),
    "00164779": ("SK하이닉스", "000660"),
}

# 1차 필터: 단일판매·공급계약체결 (한자/괄호/공백 변형 흡수 — CLAUDE.md 정규식 컨벤션)
_CONTRACT_PATTERN = re.compile(r"단일판매.{0,3}공급계약")

# 2차 필터 (기본값): 임계값 테이블에서 동적 로드. 미설정 시 사용.
_DEFAULT_HBM_KEYWORD = r"HBM|장기공급|메모리.{0,10}공급계약"


def _today_kst_date() -> str:
    return datetime.now(_KST).strftime("%Y-%m-%d")


def _today_kst_yyyymmdd() -> str:
    return datetime.now(_KST).strftime("%Y%m%d")


def _fetch_dart_major_reports(
    *,
    api_key: str,
    corp_code: str,
    bgn_de: str,
    end_de: str,
) -> list[dict]:
    """주요사항보고(pblntf_ty=B) 단일 corp 호출."""
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "pblntf_ty": "B",
        "page_no": 1,
        "page_count": 100,
    }
    resp = requests.get(_DART_LIST_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status", "")
    if status == "013":  # 데이터 없음
        return []
    if status != "000":
        raise RuntimeError(f"DART API 오류 ({status}): {data.get('message','')}")
    return data.get("list", []) or []


def _load_keyword_regex() -> re.Pattern:
    """semi_thresholds.hbm_contracts.keyword_regex 동적 로드 → re.IGNORECASE."""
    try:
        with get_session() as db:
            repo = SemiconductorRepository(db)
            raw = repo.get_threshold_value(
                "hbm_contracts", "keyword_regex", default=_DEFAULT_HBM_KEYWORD
            )
    except Exception as exc:
        logger.warning(f"[hbm_contracts] threshold 로드 실패, 기본값 사용: {exc}")
        raw = _DEFAULT_HBM_KEYWORD
    try:
        return re.compile(raw, re.IGNORECASE)
    except re.error as exc:
        logger.error(f"[hbm_contracts] keyword_regex 컴파일 실패 ({raw!r}): {exc}")
        return re.compile(_DEFAULT_HBM_KEYWORD, re.IGNORECASE)


def collect(
    *,
    observed_at: Optional[str] = None,
    fetch_fn=_fetch_dart_major_reports,
) -> list[CollectorResult]:
    """HBM 공시 수집기 — 당일치 1회.

    Args:
        observed_at: YYYY-MM-DD (기본 KST 오늘). 명시 시 해당 일자만 조회.
        fetch_fn:    테스트 주입용 DART API 호출 함수.

    Returns:
        단일 CollectorResult (당일 매칭 count). 0건도 row insert.

    Raises:
        RuntimeError: OPENDART_API_KEY 미설정 또는 DART API 오류.
    """
    api_key = os.environ.get("OPENDART_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENDART_API_KEY 환경변수 미설정")

    if observed_at is None:
        observed_at = _today_kst_date()
    # YYYY-MM-DD → YYYYMMDD
    bgn_end = observed_at.replace("-", "")

    keyword_re = _load_keyword_regex()

    matched: list[dict] = []  # rcept_no 기반 dedup 미가공 매칭 목록
    seen_rcept = set()

    for corp_code, (corp_name, stock_code) in _TARGETS.items():
        try:
            items = fetch_fn(
                api_key=api_key,
                corp_code=corp_code,
                bgn_de=bgn_end,
                end_de=bgn_end,
            )
        except Exception as exc:
            logger.warning(f"[hbm_contracts] {corp_name} DART 조회 실패: {exc}")
            continue

        for item in items:
            report_nm = item.get("report_nm", "") or ""
            if not _CONTRACT_PATTERN.search(report_nm):
                continue
            if not keyword_re.search(report_nm):
                continue
            rcept_no = item.get("rcept_no", "") or ""
            if rcept_no in seen_rcept:
                continue
            seen_rcept.add(rcept_no)
            matched.append(
                {
                    "rcept_no": rcept_no,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                    "report_nm": report_nm,
                    "rcept_dt": item.get("rcept_dt", ""),
                    "link": (
                        f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                        if rcept_no
                        else ""
                    ),
                    "matched_keywords": _extract_matched_keywords(report_nm, keyword_re),
                }
            )

    value = float(len(matched))
    value_meta = {
        "unit": "count",
        "rcept_no": [m["rcept_no"] for m in matched],
        "links": [m["link"] for m in matched],
        "matched_keywords": sorted(
            {kw for m in matched for kw in m["matched_keywords"]}
        ),
        "items": matched,  # 모달에 원문 노출용
        "keyword_regex": keyword_re.pattern,
    }

    return [
        CollectorResult(
            indicator_name="hbm_contracts",
            observed_at=observed_at,
            value=value,
            value_meta=value_meta,
            source="dart_major_reports",
            raw_at=datetime.now(_KST).isoformat(timespec="seconds"),
        )
    ]


def _extract_matched_keywords(text: str, pattern: re.Pattern) -> list[str]:
    """report_nm 에서 매칭된 부분 문자열들 반환 (중복 제거)."""
    matches = pattern.findall(text)
    # findall 이 group을 반환할 수 있어 정규화
    flat = []
    for m in matches:
        if isinstance(m, tuple):
            flat.extend([x for x in m if x])
        else:
            flat.append(m)
    return list(dict.fromkeys(flat))  # order-preserving dedup
