"""OpenDart API 기반 재무데이터 조회 (fnlttSinglAcntAll).

최근 사업보고서(연간) 기준 연결재무제표 우선, 없으면 개별재무제표.
"""

import os
from datetime import date
from typing import Optional

import requests

from .cache import delete_prefix, get_cached, set_cached

_BASE_URL = "https://opendart.fss.or.kr/api"
_REPRT_CODE = "11011"  # 사업보고서


def _api_key() -> str:
    key = os.environ.get("OPENDART_API_KEY", "")
    if not key:
        raise RuntimeError(
            "OPENDART_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "https://opendart.fss.or.kr 에서 API 키를 발급받으세요."
        )
    return key


# ── corp_code 조회 ──────────────────────────────────────────────────────────

def _load_corp_map() -> dict[str, str]:
    """전체 기업코드 맵 (stock_code → corp_code) 반환.

    DART corpCode.xml ZIP을 다운로드해 파싱하고 30일 캐싱.
    상장법인(stock_code 있는 것)만 포함.
    """
    cache_key = "dart:corp_map:v1"
    cached = get_cached(cache_key)
    if cached:
        return cached

    import io
    import xml.etree.ElementTree as ET
    import zipfile

    resp = requests.get(
        f"{_BASE_URL}/corpCode.xml",
        params={"crtfc_key": _api_key()},
        timeout=60,
    )
    resp.raise_for_status()

    corp_map: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        with z.open(z.namelist()[0]) as f:
            root = ET.parse(f).getroot()
            for child in root:
                stock_code = (child.findtext("stock_code") or "").strip()
                corp_code = (child.findtext("corp_code") or "").strip()
                if stock_code and corp_code:
                    corp_map[stock_code] = corp_code

    set_cached(cache_key, corp_map, ttl_hours=24 * 30)
    return corp_map


def _fetch_corp_code(stock_code: str) -> Optional[str]:
    """종목코드 → OpenDart 기업고유번호(8자리)."""
    # 개별 캐시 우선
    cache_key = f"dart:corp_code:{stock_code}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    corp_map = _load_corp_map()
    corp_code = corp_map.get(stock_code)
    if corp_code:
        set_cached(cache_key, corp_code, ttl_hours=24 * 30)
    return corp_code


# ── fnlttSinglAcntAll 호출 ──────────────────────────────────────────────────

def _call_fin_api(corp_code: str, bsns_year: int, fs_div: str) -> list[dict]:
    """fnlttSinglAcntAll 원시 응답 반환."""
    resp = requests.get(
        f"{_BASE_URL}/fnlttSinglAcntAll.json",
        params={
            "crtfc_key": _api_key(),
            "corp_code": corp_code,
            "bsns_year": str(bsns_year),
            "reprt_code": _REPRT_CODE,
            "fs_div": fs_div,
        },
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "013":  # 데이터 없음
        return []
    if data.get("status") != "000":
        raise RuntimeError(f"DART API 오류: {data.get('message', '')}")
    return data.get("list", [])


def _parse_amount(s) -> Optional[int]:
    """금액 문자열 → int (원). 빈값/'-' 이면 None."""
    if not s or s.strip() in ("-", ""):
        return None
    try:
        return int(s.replace(",", "").replace(" ", ""))
    except ValueError:
        return None


_ACCOUNT_KEYS = {
    "revenue": ("매출액", "수익(매출액)", "영업수익"),
    "operating_income": ("영업이익", "영업이익(손실)"),
    "net_income": ("당기순이익", "당기순이익(손실)", "당기순손익"),
}


def _extract_accounts(items: list[dict]) -> dict:
    """IS/CIS 항목에서 매출/영업이익/순이익 추출. 단위: 원."""
    is_items = [
        i for i in items
        if i.get("sj_div") in ("IS", "CIS")
    ]

    result: dict[str, Optional[int]] = {}
    for field, keywords in _ACCOUNT_KEYS.items():
        for item in is_items:
            nm = item.get("account_nm", "").strip()
            if nm in keywords:
                result[f"{field}"] = _parse_amount(item.get("thstrm_amount"))
                result[f"{field}_prev"] = _parse_amount(item.get("frmtrm_amount"))
                result[f"{field}_prev2"] = _parse_amount(item.get("bfefrmtrm_amount"))
                # 기간 레이블 (당기명, 전기명)
                if "period" not in result:
                    result["period_cur"] = item.get("thstrm_nm", "")
                    result["period_prev"] = item.get("frmtrm_nm", "")
                    result["period_prev2"] = item.get("bfefrmtrm_nm", "")
                    result["thstrm_dt"] = item.get("thstrm_dt", "")
                break
        if field not in result:
            result[field] = None
            result[f"{field}_prev"] = None
            result[f"{field}_prev2"] = None

    return result


def _bsns_year_candidates() -> list[int]:
    """시도할 사업연도 목록 (최근 연도 우선)."""
    y = date.today().year
    # 4월 이후면 전년도 보고서 공시 가능성 높음
    if date.today().month >= 4:
        return [y - 1, y - 2, y - 3]
    return [y - 2, y - 1, y - 3]


# ── 공개 API ────────────────────────────────────────────────────────────────

def fetch_financials(stock_code: str, refresh: bool = False) -> Optional[dict]:
    """
    가장 최근 사업보고서 기준 재무데이터 반환.

    반환값 dict 키:
        bsns_year, fs_div, period_cur, thstrm_dt,
        revenue, operating_income, net_income          (당기, 원)
        revenue_prev, operating_income_prev, ...       (전기, 원)
        revenue_prev2, operating_income_prev2, ...     (전전기, 원)
    """
    cache_key = f"dart:fin:{stock_code}"
    if refresh:
        delete_prefix(f"dart:fin:{stock_code}")
        delete_prefix(f"dart:corp_code:{stock_code}")
    else:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    corp_code = _fetch_corp_code(stock_code)
    if not corp_code:
        return None

    for bsns_year in _bsns_year_candidates():
        for fs_div in ("CFS", "OFS"):
            try:
                items = _call_fin_api(corp_code, bsns_year, fs_div)
            except Exception:
                continue

            if not items:
                continue

            accounts = _extract_accounts(items)
            # 매출액이 없으면 유효한 데이터로 보지 않음
            if accounts.get("revenue") is None:
                continue

            result = {
                "bsns_year": bsns_year,
                "fs_div": fs_div,
                **accounts,
            }
            set_cached(cache_key, result)
            return result

    # 재무데이터 없음 (신규상장 등)
    empty = {"bsns_year": None, "fs_div": None}
    set_cached(cache_key, empty, ttl_hours=6)
    return empty
