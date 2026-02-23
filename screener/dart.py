"""DART(전자공시시스템) API 모듈.

정기보고서(사업/반기/분기) 제출 목록을 조회한다.
"""

import os
import time

import requests

from .cache import get_cached, set_cached

_DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"

REPORT_TYPES: dict[str, str] = {
    "A001": "사업보고서",
    "A002": "반기보고서",
    "A003": "분기보고서",
}


def _get_api_key() -> str:
    key = os.environ.get("OPENDART_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENDART_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "https://opendart.fss.or.kr 에서 API 키를 발급받아 설정해주세요."
        )
    return key


def fetch_filings(date_str: str) -> list[dict]:
    """특정 날짜의 정기보고서 제출 목록 조회.

    Args:
        date_str: YYYYMMDD 형식의 날짜 문자열

    Returns:
        list of dict with keys:
            corp_name, stock_code, report_type, report_name, rcept_dt, flr_nm
    """
    cache_key = f"dart_filings:{date_str}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    api_key = _get_api_key()
    all_filings: list[dict] = []

    for report_code, report_type_name in REPORT_TYPES.items():
        page_no = 1
        while True:
            params = {
                "crtfc_key": api_key,
                "bgn_de": date_str,
                "end_de": date_str,
                "pblntf_ty": "A",  # 정기공시
                "pblntf_detail_ty": report_code,
                "page_no": page_no,
                "page_count": 100,
            }

            try:
                resp = requests.get(
                    _DART_LIST_URL, params=params, timeout=30
                )
                resp.raise_for_status()
            except requests.RequestException as e:
                raise RuntimeError(f"DART API 호출 실패: {e}") from e

            data = resp.json()
            status = data.get("status", "")

            if status == "013":  # 조회된 데이터 없음
                break
            if status == "020":  # 요청 제한 초과
                time.sleep(1)
                continue
            if status != "000":
                msg = data.get("message", "알 수 없는 오류")
                raise RuntimeError(f"DART API 오류 ({status}): {msg}")

            items = data.get("list", [])
            for item in items:
                stock_code = (item.get("stock_code") or "").strip()
                if not stock_code:
                    continue  # 비상장 기업 제외

                rcept_no = item.get("rcept_no", "")
                all_filings.append(
                    {
                        "corp_name": item.get("corp_name", ""),
                        "stock_code": stock_code,
                        "report_type": report_type_name,
                        "report_code": report_code,
                        "report_name": item.get("report_nm", ""),
                        "rcept_no": rcept_no,
                        "dart_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}" if rcept_no else "",
                        "rcept_dt": item.get("rcept_dt", ""),
                        "flr_nm": item.get("flr_nm", ""),
                    }
                )

            total_page = data.get("total_page", 1)
            if page_no >= total_page:
                break
            page_no += 1
            time.sleep(0.5)  # Rate limit

        time.sleep(0.5)  # 보고서 유형 간 대기

    set_cached(cache_key, all_filings)
    return all_filings