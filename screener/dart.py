"""DART(전자공시시스템) API 모듈.

정기보고서(사업/반기/분기) 제출 목록을 조회한다.
"""

import os
import time

import requests

from .cache import get_cached, set_cached

_DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"

# report_nm에 포함되는 키워드 → 보고서 종류 분류
_REPORT_KEYWORDS: list[tuple[str, str]] = [
    ("사업보고서", "사업보고서"),
    ("반기보고서", "반기보고서"),
    ("분기보고서", "분기보고서"),
]


def _get_api_key() -> str:
    key = os.environ.get("OPENDART_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENDART_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "https://opendart.fss.or.kr 에서 API 키를 발급받아 설정해주세요."
        )
    return key


def _classify_report(report_nm: str) -> str | None:
    """report_nm 문자열로 보고서 종류 판별. 해당 없으면 None."""
    for keyword, label in _REPORT_KEYWORDS:
        if keyword in report_nm:
            return label
    return None


def fetch_filings(start_date: str, end_date: str) -> list[dict]:
    """기간별 정기보고서 제출 목록 조회.

    pblntf_ty=A(정기공시)로 단일 쿼리 후 report_nm 기준으로 분류한다.
    동일 rcept_no 중복 제거 포함.

    Args:
        start_date: YYYYMMDD 형식 시작 날짜
        end_date:   YYYYMMDD 형식 종료 날짜

    Returns:
        list of dict with keys:
            corp_name, stock_code, report_type, report_name,
            rcept_no, dart_url, rcept_dt, flr_nm
    """
    cache_key = f"dart_filings:{start_date}:{end_date}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    api_key = _get_api_key()
    all_filings: list[dict] = []
    seen_rcept_nos: set[str] = set()

    page_no = 1
    while True:
        params = {
            "crtfc_key": api_key,
            "bgn_de": start_date,
            "end_de": end_date,
            "pblntf_ty": "A",   # 정기공시 전체 (detail_ty 미지정 → 중복 없음)
            "page_no": page_no,
            "page_count": 100,
        }

        try:
            resp = requests.get(_DART_LIST_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"DART API 호출 실패: {e}") from e

        data = resp.json()
        status = data.get("status", "")

        if status == "013":     # 조회된 데이터 없음
            break
        if status == "020":     # 요청 제한 초과
            time.sleep(1)
            continue
        if status != "000":
            msg = data.get("message", "알 수 없는 오류")
            raise RuntimeError(f"DART API 오류 ({status}): {msg}")

        items = data.get("list", [])
        for item in items:
            stock_code = (item.get("stock_code") or "").strip()
            if not stock_code:
                continue    # 비상장 기업 제외

            report_nm = item.get("report_nm", "")
            report_type = _classify_report(report_nm)
            if report_type is None:
                continue    # 사업/반기/분기보고서 외 제외

            rcept_no = item.get("rcept_no", "")
            if rcept_no in seen_rcept_nos:
                continue    # rcept_no 기준 중복 제거
            seen_rcept_nos.add(rcept_no)

            all_filings.append(
                {
                    "corp_name": item.get("corp_name", ""),
                    "stock_code": stock_code,
                    "report_type": report_type,
                    "report_name": report_nm,
                    "rcept_no": rcept_no,
                    "dart_url": (
                        f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                        if rcept_no
                        else ""
                    ),
                    "rcept_dt": item.get("rcept_dt", ""),
                    "flr_nm": item.get("flr_nm", ""),
                }
            )

        total_page = data.get("total_page", 1)
        if page_no >= total_page:
            break
        page_no += 1
        time.sleep(0.3)

    set_cached(cache_key, all_filings)
    return all_filings
