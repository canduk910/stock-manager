"""DART(전자공시시스템) API 모듈.

정기/주요사항/지분/외부감사 등 카테고리별 공시 제출 목록 조회 + 분류.
"""

import os
import time

import requests

from .cache import get_cached, set_cached


_DART_HEADERS = {"Connection": "close"}  # keep-alive 재사용 방지 → RemoteDisconnected 방지


def _dart_get(url: str, params: dict, timeout: int = 30) -> requests.Response:
    """DART API GET 요청.

    Connection: close 헤더로 keep-alive 재사용을 끊어 RemoteDisconnected를 방지.
    ConnectionError 발생 시 최대 3회 재시도 (1s / 2s 간격).
    """
    last_exc: Exception = RuntimeError("no attempt")
    for attempt in range(3):
        try:
            return requests.get(url, params=params, timeout=timeout, headers=_DART_HEADERS)
        except requests.exceptions.ConnectionError as e:
            last_exc = e
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise last_exc

import re

_DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"

# report_nm에 포함되는 패턴 → 보고서 종류 분류 (정기공시 A 카테고리용)
# CLAUDE.md "키워드 검색은 정규식" 지침 준수. 띄어쓰기/접두사 변형 자동 흡수.
_REPORT_PATTERNS: list[tuple] = [
    (re.compile(r"사업\s*보고서"), "사업보고서"),
    (re.compile(r"반기\s*보고서"), "반기보고서"),
    (re.compile(r"분기\s*보고서"), "분기보고서"),
]

# DART pblntf_ty 코드 → 한글 카테고리 라벨 (Phase 2A, ValueScreener 자문 2026-05-10)
# Default ON: A/B/D/F (가치투자 안전마진 평가에 필수)
# Default OFF (사용자 토글): C/E/I — 노이즈 가능성 있으나 의도 시 조회
# 미노출: G(펀드)/H(자산유동화)/J(공정위) — 일반 종목 무관
CATEGORY_LABELS: dict[str, str] = {
    "A": "정기공시",
    "B": "주요사항보고",
    "C": "발행공시",
    "D": "지분공시",
    "E": "기타공시",
    "F": "외부감사관련",
    "G": "펀드공시",
    "H": "자산유동화",
    "I": "거래소공시",
    "J": "공정위공시",
}

DEFAULT_CATEGORIES: tuple[str, ...] = ("A", "B", "D", "F")
ALLOWED_CATEGORIES: frozenset[str] = frozenset(CATEGORY_LABELS.keys())


def _get_api_key() -> str:
    key = os.environ.get("OPENDART_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENDART_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "https://opendart.fss.or.kr 에서 API 키를 발급받아 설정해주세요."
        )
    return key


def _classify_report(report_nm: str) -> str | None:
    """report_nm에서 정기공시(사업/반기/분기) 패턴 추출. 없으면 None.

    정기공시(A) 카테고리 세부분류용. non-A 카테고리는 report_nm을 그대로
    사용하므로(예: "유상증자결정") None 반환을 제외 사유로 삼지 않는다.
    """
    for pattern, label in _REPORT_PATTERNS:
        if pattern.search(report_nm):
            return label
    return None


def _fetch_filings_single_category(
    api_key: str,
    start_date: str,
    end_date: str,
    pblntf_ty: str,
    corp_code: str | None,
) -> list[dict]:
    """단일 카테고리 호출. 페이지네이션 + 비상장 기업 제외.

    카테고리 A는 _classify_report로 사업/반기/분기 분류, non-A는 report_nm 그대로.
    """
    results: list[dict] = []
    page_no = 1
    while True:
        params: dict = {
            "crtfc_key": api_key,
            "bgn_de": start_date,
            "end_de": end_date,
            "pblntf_ty": pblntf_ty,
            "page_no": page_no,
            "page_count": 100,
        }
        if corp_code:
            params["corp_code"] = corp_code

        try:
            resp = _dart_get(_DART_LIST_URL, params=params, timeout=30)
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
            classified = _classify_report(report_nm)

            # 카테고리 A는 정기공시 키워드(사업/반기/분기)만 통과 — 기존 동작 보존.
            # 비-A 카테고리는 report_nm 그대로 노출 (예: "유상증자결정").
            if pblntf_ty == "A":
                if classified is None:
                    continue
                report_type = classified
            else:
                report_type = classified or report_nm  # 키워드 없으면 원문 노출

            rcept_no = item.get("rcept_no", "")
            results.append(
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
                    "category_code": pblntf_ty,
                    "category": CATEGORY_LABELS.get(pblntf_ty, pblntf_ty),
                }
            )

        total_page = data.get("total_page", 1)
        if page_no >= total_page:
            break
        page_no += 1
        time.sleep(0.3)

    return results


def fetch_filings(
    start_date: str,
    end_date: str,
    *,
    corp_code: str | None = None,
    pblntf_types: list[str] | None = None,
    detail_types: list[str] | None = None,
) -> list[dict]:
    """기간별 공시 제출 목록 조회 — 카테고리 다중 선택 지원.

    Phase 2A (2026-05-10, ValueScreener 자문): pblntf_ty 다중 카테고리 분기.
    DART API는 pblntf_ty 단일만 받으므로 카테고리별 별도 호출 후 머지 + 중복 제거.

    Args:
        start_date: YYYYMMDD 형식 시작 날짜
        end_date:   YYYYMMDD 형식 종료 날짜
        corp_code: DART 회사 고유번호(8자리). 지정 시 해당 회사만 조회 +
                   검색기간 무제한. None이면 전종목 조회(DART 정책상 3개월
                   초과 시 거부됨 — 호출자 책임).
        pblntf_types: 카테고리 코드 리스트 ['A','B','D','F']. None이면 ['A'] 단독
                      (백워드 호환). 무효 코드는 silent skip.
        detail_types: 세부 카테고리(pblntf_detail_ty) 코드 리스트. 현재 미사용
                      (Phase 2B에서 활용 예정). 캐시 키 분리에는 반영.

    Returns:
        list of dict with keys:
            corp_name, stock_code, report_type, report_name,
            rcept_no, dart_url, rcept_dt, flr_nm,
            category_code, category  (Phase 2A 신규)
    """
    from datetime import date as _date

    today_str = _date.today().strftime("%Y%m%d")
    use_cache = end_date < today_str

    # 카테고리 정규화
    if pblntf_types is None:
        types_to_call = ["A"]  # 백워드 호환
    else:
        types_to_call = sorted(set(t for t in pblntf_types if t in ALLOWED_CATEGORIES))
        if not types_to_call:
            types_to_call = ["A"]

    # 캐시 키: corp_code + 카테고리 + 세부 코드 모두 분리
    cache_suffix = f":{corp_code}" if corp_code else ""
    if pblntf_types is not None:
        cache_suffix += f":cats={','.join(types_to_call)}"
    if detail_types:
        cache_suffix += f":dets={','.join(sorted(set(detail_types)))}"
    cache_key = f"dart_filings:{start_date}:{end_date}{cache_suffix}"
    if use_cache:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    api_key = _get_api_key()
    all_filings: list[dict] = []
    seen_rcept_nos: set[str] = set()

    for ty in types_to_call:
        single = _fetch_filings_single_category(
            api_key, start_date, end_date, ty, corp_code,
        )
        for item in single:
            rcept_no = item.get("rcept_no", "")
            if rcept_no and rcept_no in seen_rcept_nos:
                continue
            if rcept_no:
                seen_rcept_nos.add(rcept_no)
            all_filings.append(item)
        # 카테고리 간 rate limit 보호
        if len(types_to_call) > 1:
            time.sleep(0.3)

    if use_cache:
        set_cached(cache_key, all_filings)
    return all_filings
