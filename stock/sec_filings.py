"""SEC EDGAR 기반 미국 정기보고서(10-K, 10-Q) 조회.

screener/dart.py 의 미국 버전. 국내 공시와 동일한 필드 구조로 반환한다.
"""

from __future__ import annotations

import re

import requests

# SEC EDGAR full-text search API
_SEC_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"

_HEADERS = {
    "User-Agent": "stock-manager/1.0 (contact@example.com)",
    "Accept": "application/json",
}


def _yyyymmdd_to_iso(s: str) -> str:
    """YYYYMMDD → YYYY-MM-DD."""
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _parse_display_name(display: str) -> tuple[str, str]:
    """'APPLE INC  (AAPL)  (CIK 0000320193)' → (corp_name, ticker)."""
    # 첫 번째 괄호에서 ticker 추출 (숫자만인 CIK 제외)
    m = re.search(r'\(([A-Z][A-Z0-9\-\.]{0,9})\)', display)
    ticker = m.group(1) if m else ""
    # CIK 패턴 제거 후 회사명 추출
    corp_name = re.sub(r'\s*\(.*?\)', '', display).strip()
    return corp_name, ticker


def fetch_sec_filings(start_date: str, end_date: str) -> list[dict]:
    """미국 정기보고서(10-K, 10-Q) 조회.

    Args:
        start_date: YYYYMMDD 형식
        end_date:   YYYYMMDD 형식

    Returns:
        국내 공시와 동일한 필드 구조의 dict 리스트.
        {
            corp_name, stock_code, report_name, report_code,
            rcept_no, rcept_dt, link
        }
    """
    s_iso = _yyyymmdd_to_iso(start_date)
    e_iso = _yyyymmdd_to_iso(end_date)

    results = []
    for form in ("10-K", "10-Q"):
        try:
            items = _fetch_form(form, s_iso, e_iso)
            results.extend(items)
        except Exception as e:
            print(f"[sec_filings] {form} 조회 실패: {e}")

    # 날짜 오름차순 정렬
    results.sort(key=lambda x: x["rcept_dt"])
    return results


def _fetch_form(form: str, start_iso: str, end_iso: str) -> list[dict]:
    """단일 양식(10-K 또는 10-Q) 조회. 최대 100건."""
    resp = requests.get(
        _SEC_EFTS_URL,
        params={
            "q": form,
            "dateRange": "custom",
            "startdt": start_iso,
            "enddt": end_iso,
            "forms": form,
        },
        headers=_HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()

    hits = data.get("hits", {}).get("hits", [])
    seen = set()  # 중복 제거 (adsh 기준)
    items = []

    for hit in hits:
        src = hit.get("_source", {})
        adsh = src.get("adsh", "")
        if adsh in seen:
            continue
        seen.add(adsh)

        display_names = src.get("display_names", [])
        display = display_names[0] if display_names else ""
        corp_name, ticker = _parse_display_name(display) if display else ("", "")

        file_date = src.get("file_date", "")
        rcept_dt = file_date.replace("-", "") if file_date else ""

        # 실제 filing 링크 구성
        if adsh:
            ciks = src.get("ciks", [])
            cik = ciks[0].lstrip("0") if ciks else ""
            acc_nodash = adsh.replace("-", "")
            link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{adsh}-index.htm"
        else:
            link = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type={form}&dateb=&owner=include&count=40"

        items.append({
            "corp_name": corp_name,
            "stock_code": ticker,
            "report_name": f"{corp_name} {form}" if corp_name else form,
            "report_code": form,
            "rcept_no": adsh,
            "rcept_dt": rcept_dt,
            "link": link,
        })

    return items
