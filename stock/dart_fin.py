"""OpenDart API 기반 재무데이터 조회 (fnlttSinglAcntAll).

최근 사업보고서(연간) 기준 연결재무제표 우선, 없으면 개별재무제표.
"""

import os
import time
from datetime import date
from typing import Optional

import requests

from .cache import delete_prefix, get_cached, set_cached

_BASE_URL = "https://opendart.fss.or.kr/api"
_REPRT_CODE = "11011"  # 사업보고서


_DART_HEADERS = {"Connection": "close"}  # keep-alive 재사용 방지 → RemoteDisconnected 방지


def _dart_get(url: str, params: dict, timeout: int = 20) -> requests.Response:
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

    resp = _dart_get(
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


def _load_corp_name_map() -> dict[str, str]:
    """전체 기업명 맵 (stock_code → corp_name) 반환.

    DART corpCode.xml에서 corp_name도 포함해 파싱. 30일 캐싱.
    pykrx KRX 서버 이슈 시 종목명 대체 소스로 활용.
    """
    cache_key = "dart:corp_name_map:v1"
    cached = get_cached(cache_key)
    if cached:
        return cached

    import io
    import xml.etree.ElementTree as ET
    import zipfile

    try:
        resp = _dart_get(
            f"{_BASE_URL}/corpCode.xml",
            params={"crtfc_key": _api_key()},
            timeout=60,
        )
        resp.raise_for_status()
    except Exception:
        return {}

    name_map: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        with z.open(z.namelist()[0]) as f:
            root = ET.parse(f).getroot()
            for child in root:
                stock_code = (child.findtext("stock_code") or "").strip()
                corp_name = (child.findtext("corp_name") or "").strip()
                if stock_code and corp_name:
                    name_map[stock_code] = corp_name

    set_cached(cache_key, name_map, ttl_hours=24 * 30)
    return name_map


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
    resp = _dart_get(
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
    "revenue": ("매출액", "수익(매출액)", "영업수익", "매출"),
    "operating_income": ("영업이익", "영업이익(손실)", "영업손실"),
    "net_income": (
        "당기순이익", "당기순이익(손실)", "당기순손익", "당기순손실",
        "연결당기순이익",  # 골프존 등 CIS 방식 기업
    ),
}

# ── 대차대조표 계정 매핑 ──────────────────────────────────────────────────────

_BS_KEYS = {
    "total_assets":               ("자산총계",),
    "current_assets":             ("유동자산",),
    "non_current_assets":         ("비유동자산",),
    "cash_and_equiv":             ("현금및현금성자산",),
    "receivables":                ("매출채권및기타채권", "매출채권", "단기매출채권"),
    "inventories":                ("재고자산",),
    "ppe":                        ("유형자산",),
    "intangibles":                ("무형자산",),
    "total_liabilities":          ("부채총계",),
    "current_liabilities":        ("유동부채",),
    "non_current_liabilities":    ("비유동부채",),
    "short_term_debt":            ("단기차입금",),
    "long_term_debt":             ("장기차입금", "장기차입금및사채"),
    "total_equity":               ("자본총계",),
    "retained_earnings":          ("이익잉여금", "결손금"),
}

# ── 현금흐름표 계정 매핑 ──────────────────────────────────────────────────────

_CF_KEYS = {
    "operating_cf":  ("영업활동현금흐름", "영업활동 현금흐름"),
    "investing_cf":  ("투자활동현금흐름", "투자활동 현금흐름"),
    "financing_cf":  ("재무활동현금흐름", "재무활동 현금흐름"),
    "capex":         ("유형자산의취득", "유형자산 취득"),
    "depreciation":  ("감가상각비",),
    "cash_change":   ("현금및현금성자산의증가", "현금및현금성자산 증가감소"),
}

# ── 손익계산서 세부 계정 매핑 ─────────────────────────────────────────────────

_IS_DETAIL_KEYS = {
    "revenue":          ("매출액", "수익(매출액)", "영업수익", "매출"),
    "cogs":             ("매출원가",),
    "gross_profit":     ("매출총이익",),
    "sga":              ("판매비와관리비", "판매비및관리비"),
    "operating_income": ("영업이익", "영업이익(손실)", "영업손실"),
    "interest_income":  ("이자수익",),
    "interest_expense": ("이자비용",),
    "pretax_income":    ("법인세비용차감전순이익", "세전이익"),
    "tax_expense":      ("법인세비용",),
    "net_income":       (
        "당기순이익", "당기순이익(손실)", "당기순손익", "당기순손실",
        "연결당기순이익",  # 골프존 등 CIS 방식 기업
    ),
    "eps":              ("기본주당이익(손실)", "기본주당순이익", "기본주당이익"),
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


def _extract_period_accounts(is_items: list[dict], period_key: str) -> dict:
    """특정 기간(thstrm/frmtrm/bfefrmtrm)의 IS 계정 금액 추출.

    period_key: "thstrm" | "frmtrm" | "bfefrmtrm"
    반환: {revenue, operating_income, net_income} — 단위: 원
    """
    amount_key = f"{period_key}_amount"
    result: dict[str, Optional[int]] = {}
    for field, keywords in _ACCOUNT_KEYS.items():
        result[field] = None
        for item in is_items:
            nm = item.get("account_nm", "").strip()
            if nm in keywords:
                result[field] = _parse_amount(item.get(amount_key))
                break
    return result


def _bsns_year_candidates() -> list[int]:
    """시도할 사업연도 목록 (최근 연도 우선).

    3~4월에도 전년도 사업보고서가 공시되므로 항상 y-1 우선 시도.
    """
    y = date.today().year
    return [y - 1, y - 2, y - 3]


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
            set_cached(cache_key, result, ttl_hours=168)
            # 영속 캐시 write-through
            try:
                from .stock_info_store import upsert_financials
                upsert_financials(stock_code, "KR", result)
            except Exception:
                pass
            return result

    # 재무데이터 없음 (신규상장 등)
    empty = {"bsns_year": None, "fs_div": None}
    set_cached(cache_key, empty, ttl_hours=6)
    return empty


def fetch_financials_multi_year(
    stock_code: str, years: int = 10
) -> list[dict]:
    """최대 years개 사업연도의 재무데이터 반환.

    3년 단위 배치 호출(최대 4회)로 효율적으로 수집한다.
    반환: [
        {
            "year": 2024,
            "revenue": ...,           # 원
            "operating_income": ...,
            "net_income": ...,
            "rcept_no": "20250317000123",
            "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=...",
        },
        ...  # 과거 → 최신 순 정렬
    ]
    """
    cache_key = f"dart:fin_multi:{stock_code}:{years}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    corp_code = _fetch_corp_code(stock_code)
    if not corp_code:
        set_cached(cache_key, [], ttl_hours=6)
        return []

    # 최근 확정 사업연도 결정 (3~4월에도 전년도 사업보고서 공시됨)
    today = date.today()
    latest_year = today.year - 1

    # 3년 단위 앵커 연도 목록 (최대 ceil(years/3)개 배치)
    num_batches = (years + 2) // 3
    anchor_years = [latest_year - i * 3 for i in range(num_batches)]

    collected: dict[int, dict] = {}
    fs_div_used: Optional[str] = None  # 연결/별도 결정 후 고정

    for batch_idx, anchor in enumerate(anchor_years):
        if len(collected) >= years:
            break

        # 첫 번째 배치(latest_year)가 미공시면 anchor-1로 fallback
        effective_anchor = anchor
        items: list = []
        found_fs: Optional[str] = None

        for try_anchor in ([anchor, anchor - 1] if batch_idx == 0 else [anchor]):
            fs_divs = [fs_div_used] if fs_div_used else ["CFS", "OFS"]
            for fs_div in fs_divs:
                try:
                    candidate = _call_fin_api(corp_code, try_anchor, fs_div)
                except Exception:
                    continue
                if not candidate:
                    continue
                if not any(i.get("sj_div") in ("IS", "CIS") for i in candidate):
                    continue
                items = candidate
                found_fs = fs_div
                effective_anchor = try_anchor
                break
            if items:
                break

        if not items:
            continue

        is_items = [i for i in items if i.get("sj_div") in ("IS", "CIS")]
        rcept_no = is_items[0].get("rcept_no", "")
        dart_url = (
            f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
            if rcept_no
            else ""
        )

        # thstrm(당기), frmtrm(전기), bfefrmtrm(전전기) 각각 추출
        for period_key, year_offset in [
            ("thstrm", 0),
            ("frmtrm", -1),
            ("bfefrmtrm", -2),
        ]:
            target_year = effective_anchor + year_offset
            if target_year in collected:
                continue
            period_data = _extract_period_accounts(is_items, period_key)
            if period_data.get("revenue") is None:
                continue
            collected[target_year] = {
                "year": target_year,
                "revenue": period_data["revenue"],
                "operating_income": period_data["operating_income"],
                "net_income": period_data["net_income"],
                "rcept_no": rcept_no,
                "dart_url": dart_url,
            }

        if fs_div_used is None and collected:
            fs_div_used = found_fs

    # 과거 → 최신 정렬, 최대 years개
    result = sorted(collected.values(), key=lambda x: x["year"])[-years:]

    set_cached(cache_key, result, ttl_hours=168)
    return result


# ── BS/CF 공용 헬퍼 ───────────────────────────────────────────────────────────

def _extract_sheet_period(items: list[dict], sj_divs: tuple, keys: dict, period_key: str) -> dict:
    """특정 재무제표(BS/CF)의 특정 기간 계정 금액 추출.

    sj_divs: 필터할 sj_div 값 목록 (예: ('BS', 'CBS') or ('CF', 'CCF'))
    keys: {field_name: (계정명1, 계정명2, ...)} 매핑
    period_key: 'thstrm' | 'frmtrm' | 'bfefrmtrm'
    """
    filtered = [i for i in items if i.get("sj_div") in sj_divs]
    amount_key = f"{period_key}_amount"
    result: dict = {}
    for field, keywords in keys.items():
        result[field] = None
        for item in filtered:
            nm = item.get("account_nm", "").strip()
            if nm in keywords:
                result[field] = _parse_amount(item.get(amount_key))
                break
    return result


def _extract_is_detail_period(items: list[dict], period_key: str) -> dict:
    """IS 세부 계정 특정 기간 추출."""
    is_items = [i for i in items if i.get("sj_div") in ("IS", "CIS")]
    amount_key = f"{period_key}_amount"
    result: dict = {}
    for field, keywords in _IS_DETAIL_KEYS.items():
        result[field] = None
        for item in is_items:
            nm = item.get("account_nm", "").strip()
            if nm in keywords:
                result[field] = _parse_amount(item.get(amount_key))
                break
    return result


# ── 공개 API: 대차대조표 + 현금흐름표 ─────────────────────────────────────────

def fetch_bs_cf_annual(stock_code: str, years: int = 5) -> dict:
    """대차대조표 + 현금흐름표 연간 데이터 (최대 years년).

    반환:
        {
            "balance_sheet": [{year, total_assets, current_assets, ...}],
            "cashflow": [{year, operating_cf, investing_cf, ...}],
        }
    데이터 없으면 빈 리스트.
    """
    cache_key = f"dart:bs_cf:{stock_code}:{years}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    corp_code = _fetch_corp_code(stock_code)
    if not corp_code:
        empty = {"balance_sheet": [], "cashflow": []}
        set_cached(cache_key, empty, ttl_hours=6)
        return empty

    today = date.today()
    latest_year = today.year - 1  # 3~4월에도 전년도 사업보고서 공시됨

    num_batches = (years + 2) // 3
    anchor_years = [latest_year - i * 3 for i in range(num_batches)]

    bs_collected: dict[int, dict] = {}
    cf_collected: dict[int, dict] = {}
    fs_div_used: Optional[str] = None

    for batch_idx, anchor in enumerate(anchor_years):
        if len(bs_collected) >= years and len(cf_collected) >= years:
            break

        # 첫 번째 배치(latest_year)가 미공시면 anchor-1로 fallback
        effective_anchor = anchor
        items: list = []
        found_fs: Optional[str] = None

        for try_anchor in ([anchor, anchor - 1] if batch_idx == 0 else [anchor]):
            fs_divs = [fs_div_used] if fs_div_used else ["CFS", "OFS"]
            for fs_div in fs_divs:
                try:
                    candidate = _call_fin_api(corp_code, try_anchor, fs_div)
                except Exception:
                    continue
                if not candidate:
                    continue
                has_bs = any(i.get("sj_div") in ("BS", "CBS") for i in candidate)
                has_cf = any(i.get("sj_div") in ("CF", "CCF") for i in candidate)
                if not has_bs and not has_cf:
                    continue
                items = candidate
                found_fs = fs_div
                effective_anchor = try_anchor
                break
            if items:
                break

        if not items:
            continue

        has_bs = any(i.get("sj_div") in ("BS", "CBS") for i in items)
        has_cf = any(i.get("sj_div") in ("CF", "CCF") for i in items)

        for period_key, year_offset in [
            ("thstrm", 0),
            ("frmtrm", -1),
            ("bfefrmtrm", -2),
        ]:
            target_year = effective_anchor + year_offset

            if target_year not in bs_collected and has_bs:
                bs_data = _extract_sheet_period(items, ("BS", "CBS"), _BS_KEYS, period_key)
                if bs_data.get("total_assets") is not None:
                    # 부채비율, 유동비율 계산
                    equity = bs_data.get("total_equity") or 0
                    liab = bs_data.get("total_liabilities") or 0
                    cur_a = bs_data.get("current_assets") or 0
                    cur_l = bs_data.get("current_liabilities") or 1
                    bs_data["debt_ratio"] = round(liab / equity * 100, 1) if equity else None
                    bs_data["current_ratio"] = round(cur_a / cur_l * 100, 1) if cur_l else None
                    bs_collected[target_year] = {"year": target_year, **bs_data}

            if target_year not in cf_collected and has_cf:
                cf_data = _extract_sheet_period(items, ("CF", "CCF"), _CF_KEYS, period_key)
                if cf_data.get("operating_cf") is not None:
                    op_cf = cf_data.get("operating_cf") or 0
                    capex = cf_data.get("capex") or 0
                    # capex는 음수로 기재되는 경우 있음 → abs
                    free_cf = op_cf - abs(capex)
                    cf_data["free_cf"] = free_cf
                    cf_collected[target_year] = {"year": target_year, **cf_data}

        if fs_div_used is None and (bs_collected or cf_collected):
            fs_div_used = found_fs

    bs_result = sorted(bs_collected.values(), key=lambda x: x["year"])[-years:]
    cf_result = sorted(cf_collected.values(), key=lambda x: x["year"])[-years:]

    result = {"balance_sheet": bs_result, "cashflow": cf_result}
    set_cached(cache_key, result, ttl_hours=168)
    return result


def fetch_income_detail_annual(stock_code: str, years: int = 5) -> list[dict]:
    """손익계산서 세부 연간 데이터 (매출원가/매출총이익/SGA/EPS 포함).

    반환: [{year, revenue, cogs, gross_profit, sga, operating_income,
             interest_income, interest_expense, pretax_income,
             tax_expense, net_income, eps, oi_margin, net_margin}]
    """
    cache_key = f"dart:is_detail:{stock_code}:{years}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    corp_code = _fetch_corp_code(stock_code)
    if not corp_code:
        set_cached(cache_key, [], ttl_hours=6)
        return []

    today = date.today()
    latest_year = today.year - 1  # 3월에도 전년도 사업보고서가 공시됨

    num_batches = (years + 2) // 3
    anchor_years = [latest_year - i * 3 for i in range(num_batches)]

    collected: dict[int, dict] = {}
    fs_div_used: Optional[str] = None

    for batch_idx, anchor in enumerate(anchor_years):
        if len(collected) >= years:
            break

        items: list = []
        found_fs: Optional[str] = None
        effective_anchor = anchor

        # 첫 번째 배치는 anchor-1도 fallback 시도 (미공시 기업 대응)
        for try_anchor in ([anchor, anchor - 1] if batch_idx == 0 else [anchor]):
            fs_divs = [fs_div_used] if fs_div_used else ["CFS", "OFS"]
            for fs_div in fs_divs:
                try:
                    candidate = _call_fin_api(corp_code, try_anchor, fs_div)
                except Exception:
                    continue
                if not candidate:
                    continue
                if not any(i.get("sj_div") in ("IS", "CIS") for i in candidate):
                    continue
                items = candidate
                found_fs = fs_div
                effective_anchor = try_anchor
                break
            if items:
                break

        if not items:
            continue

        for period_key, year_offset in [
            ("thstrm", 0),
            ("frmtrm", -1),
            ("bfefrmtrm", -2),
        ]:
            target_year = effective_anchor + year_offset
            if target_year in collected:
                continue
            row = _extract_is_detail_period(items, period_key)
            if row.get("revenue") is None:
                continue
            # 마진 계산
            rev = row.get("revenue") or 0
            oi = row.get("operating_income") or 0
            ni = row.get("net_income") or 0
            row["oi_margin"] = round(oi / rev * 100, 1) if rev else None
            row["net_margin"] = round(ni / rev * 100, 1) if rev else None
            collected[target_year] = {"year": target_year, **row}

        if fs_div_used is None and collected:
            fs_div_used = found_fs

    result = sorted(collected.values(), key=lambda x: x["year"])[-years:]
    set_cached(cache_key, result, ttl_hours=168)
    return result


# ── Phase 2-3: 분기 실적 ─────────────────────────────────────────────────────

# reprt_code 매핑 (OpenDart):
# 11013 = Q1(1분기보고서), 11012 = 반기(2분기 누계), 11014 = Q3(3분기 누계), 11011 = 사업보고서(연간)
_QUARTERLY_REPRT_CODES = [
    ("11013", 1),  # Q1
    ("11012", 2),  # 반기 (2분기 누계 = Q1 + Q2)
    ("11014", 3),  # 3분기 누계 (Q1 + Q2 + Q3)
    ("11011", 4),  # 연간
]


def _call_fin_api_reprt(corp_code: str, bsns_year: int, reprt_code: str, fs_div: str) -> list[dict]:
    """분기 보고서 원시 응답 반환 (reprt_code 지정). 실패/비어있으면 []."""
    try:
        resp = _dart_get(
            f"{_BASE_URL}/fnlttSinglAcntAll.json",
            params={
                "crtfc_key": _api_key(),
                "corp_code": corp_code,
                "bsns_year": str(bsns_year),
                "reprt_code": reprt_code,
                "fs_div": fs_div,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "000":
            return []
        return data.get("list", []) or []
    except Exception:
        return []


def _extract_quarterly_accumulated(items: list[dict]) -> dict:
    """분기/반기/3분기누계/연간 보고서의 IS(or CIS) 당기 누계값 추출.

    반환: {revenue, operating_income, net_income} (누계 기준)
    """
    data = {"revenue": None, "operating_income": None, "net_income": None}
    for it in items:
        if it.get("sj_div") not in ("IS", "CIS"):
            continue
        nm = (it.get("account_nm") or "").strip()
        for key, aliases in _ACCOUNT_KEYS.items():
            if nm in aliases:
                # thstrm_amount = 당기(해당 분기/반기/누계)
                amt = _parse_amount(it.get("thstrm_amount"))
                if amt is not None and data[key] is None:
                    data[key] = amt
                break
    return data


def fetch_quarterly_financials(stock_code: str, quarters: int = 4) -> list[dict]:
    """국내 종목 최근 N분기 손익 (DART 분기보고서 누계 → 개별 분기 환산).

    변환 공식:
      Q1 값 = 11013 thstrm (Q1)
      Q2 값 = 11012 thstrm (반기) − Q1
      Q3 값 = 11014 thstrm (3분기누계) − 반기
      Q4 값 = 11011 thstrm (연간) − 3분기누계

    반환: [{year, quarter, revenue, operating_income, net_income, oi_margin, net_margin}] 오래된순
    미공시 분기 건너뜀 (graceful). 캐시: `dart:quarterly:{code}:{quarters}` 7일.
    """
    cache_key = f"dart:quarterly:{stock_code}:{quarters}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    corp_code = _fetch_corp_code(stock_code)
    if not corp_code:
        set_cached(cache_key, [], ttl_hours=24)
        return []

    today = date.today()
    latest_year = today.year
    # 최대 2년치(=최근 8분기) 조회하여 이후 quarters 만큼 슬라이스
    years_to_fetch = max(2, (quarters + 3) // 4 + 1)

    quarterly_rows: list[dict] = []

    for year_offset in range(years_to_fetch):
        target_year = latest_year - year_offset

        # 4개 reprt_code 조회 → 누계값 수집
        accum: dict[int, dict] = {}  # quarter(1-4) → {revenue, operating_income, net_income}
        fs_div_used: Optional[str] = None
        for reprt_code, qnum in _QUARTERLY_REPRT_CODES:
            fs_divs = [fs_div_used] if fs_div_used else ["CFS", "OFS"]
            items: list = []
            for fs_div in fs_divs:
                candidate = _call_fin_api_reprt(corp_code, target_year, reprt_code, fs_div)
                if candidate:
                    items = candidate
                    if fs_div_used is None:
                        fs_div_used = fs_div
                    break
            if items:
                accum[qnum] = _extract_quarterly_accumulated(items)

        if not accum:
            continue

        # 누계 → 개별 분기 환산
        for q in range(1, 5):
            if q not in accum:
                continue
            cur = accum[q]
            prev = accum.get(q - 1) if q > 1 else None
            row = {"year": target_year, "quarter": q}
            for key in ("revenue", "operating_income", "net_income"):
                cur_val = cur.get(key)
                if cur_val is None:
                    row[key] = None
                    continue
                if prev and prev.get(key) is not None:
                    row[key] = cur_val - prev[key]
                else:
                    row[key] = cur_val  # 직전 누계 없으면 당기 값 그대로 (Q1 또는 graceful)
            # 마진 계산
            rev = row.get("revenue") or 0
            oi = row.get("operating_income") or 0
            ni = row.get("net_income") or 0
            row["oi_margin"] = round(oi / rev * 100, 1) if rev > 0 and oi is not None else None
            row["net_margin"] = round(ni / rev * 100, 1) if rev > 0 and ni is not None else None
            quarterly_rows.append(row)

    # 연도-분기 오래된→최신 정렬 후 최근 quarters만
    quarterly_rows.sort(key=lambda r: (r["year"], r["quarter"]))
    result = quarterly_rows[-quarters:] if len(quarterly_rows) > quarters else quarterly_rows
    set_cached(cache_key, result, ttl_hours=24 * 7)
    return result
