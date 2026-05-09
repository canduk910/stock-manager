"""공시(정기보고서) API 라우터."""

from fastapi import APIRouter, Depends, HTTPException, Query

from services.auth_deps import get_current_user
from services.exceptions import ExternalAPIError
from screener.dart import fetch_filings, ALLOWED_CATEGORIES, DEFAULT_CATEGORIES
from screener.service import ScreenerValidationError, normalize_date
from stock.dart_fin import fetch_financials
from stock.market import fetch_period_returns
from stock.sec_filings import fetch_sec_filings
from stock.yf_client import fetch_period_returns_yf

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


def _parse_category_csv(raw: str | None) -> list[str] | None:
    """CSV 카테고리 문자열 → 검증된 코드 리스트. 무효 시 422.

    Phase 2A (2026-05-10): None → 기존 동작(['A'] 단독, 백워드 호환).
    """
    if not raw:
        return None
    parts = [p.strip().upper() for p in raw.split(",") if p.strip()]
    invalid = [p for p in parts if p not in ALLOWED_CATEGORIES]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"알 수 없는 공시 카테고리 코드: {','.join(invalid)}. 허용: {','.join(sorted(ALLOWED_CATEGORIES))}",
        )
    return parts or None


@router.get("/filings")
def get_filings(
    market: str = Query("KR", description="KR (국내 DART) 또는 US (미국 SEC EDGAR)"),
    date: str | None = Query(
        None,
        description="단일 날짜 조회 (YYYYMMDD 또는 YYYY-MM-DD). start_date/end_date 와 함께 쓰면 무시됨.",
    ),
    start_date: str | None = Query(None, description="시작 날짜 (YYYYMMDD 또는 YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="종료 날짜 (YYYYMMDD 또는 YYYY-MM-DD)"),
    categories: str | None = Query(
        None,
        description=(
            "공시 카테고리 CSV (예: A,B,D,F). DART pblntf_ty 코드. 미지정 시 A(정기공시)만. "
            "ValueScreener 권고 default: A/B/D/F. KR 한정. US는 무시."
        ),
    ),
    details: str | None = Query(
        None,
        description="세부 카테고리(pblntf_detail_ty) CSV. Phase 2B 활용 예정.",
    ),
    _user: dict = Depends(get_current_user),
):
    """기간별 공시 제출 목록 조회 — 카테고리 다중 필터 지원.

    - market=KR: 국내 DART (categories 미지정 시 정기공시 A만, 백워드 호환)
    - market=US: 미국 SEC EDGAR (10-K / 10-Q, categories 무시)
    - start_date + end_date: 기간 조회
    - date: 단일 날짜 조회 (start_date = end_date = date)
    - 모두 생략: 오늘 날짜
    """
    try:
        if start_date or end_date:
            s = normalize_date(start_date)
            e = normalize_date(end_date) if end_date else s
        else:
            s = e = normalize_date(date)
    except ScreenerValidationError as ex:
        raise HTTPException(status_code=422, detail=str(ex))

    # 최대 90일 제한 (API 부하 방지)
    from datetime import datetime
    try:
        dt_s = datetime.strptime(s, "%Y%m%d")
        dt_e = datetime.strptime(e, "%Y%m%d")
        if dt_e < dt_s:
            raise HTTPException(status_code=422, detail="종료 날짜가 시작 날짜보다 앞설 수 없습니다.")
        if (dt_e - dt_s).days > 90:
            raise HTTPException(status_code=422, detail="조회 기간은 최대 90일입니다.")
    except ValueError:
        raise HTTPException(status_code=422, detail="날짜 형식이 올바르지 않습니다.")

    cat_list = _parse_category_csv(categories)
    det_list = _parse_category_csv(details) if False else (
        [d.strip() for d in details.split(",") if d.strip()] if details else None
    )

    if market.upper() == "US":
        # SEC EDGAR는 form type 별도 체계 — 카테고리 무시 (Phase 2B 확장 가능)
        return _get_filings_us(s, e)
    else:
        return _get_filings_kr(s, e, pblntf_types=cat_list, detail_types=det_list)


def _get_filings_kr(
    s: str,
    e: str,
    *,
    pblntf_types: list[str] | None = None,
    detail_types: list[str] | None = None,
) -> dict:
    """국내 DART 공시 조회. pblntf_types 미지정 시 기존 동작(A 단독)."""
    try:
        filings = fetch_filings(
            s, e,
            pblntf_types=pblntf_types,
            detail_types=detail_types,
        )
    except RuntimeError as ex:
        raise ExternalAPIError(str(ex))

    # 종목별 수익률 일괄 조회
    unique_codes = list({f["stock_code"] for f in filings})
    returns_map: dict[str, dict] = {}
    for code in unique_codes:
        try:
            returns_map[code] = fetch_period_returns(code)
        except Exception:
            returns_map[code] = {}

    for f in filings:
        r = returns_map.get(f["stock_code"], {})
        f["change_pct"] = r.get("change_pct")
        f["return_3m"]  = r.get("return_3m")
        f["return_6m"]  = r.get("return_6m")
        f["return_1y"]  = r.get("return_1y")

    # 종목별 재무 데이터 (매출액/영업이익) 일괄 조회
    fin_map: dict[str, dict] = {}
    for code in unique_codes:
        try:
            fin = fetch_financials(code)
            if fin:
                fin_map[code] = fin
        except Exception:
            pass

    for f in filings:
        fin = fin_map.get(f["stock_code"], {})
        f["fin_year"]             = fin.get("bsns_year")
        f["revenue"]              = fin.get("revenue")
        f["revenue_prev"]         = fin.get("revenue_prev")
        f["operating_income"]     = fin.get("operating_income")
        f["operating_income_prev"] = fin.get("operating_income_prev")

    return {
        "market": "KR",
        "start_date": s,
        "end_date": e,
        "total": len(filings),
        "filings": filings,
    }


def _get_filings_us(s: str, e: str) -> dict:
    """미국 SEC EDGAR 공시 조회."""
    try:
        filings = fetch_sec_filings(s, e)
    except Exception as ex:
        raise ExternalAPIError(f"SEC EDGAR 조회 실패: {ex}")

    # 수익률은 ticker가 있는 경우만 조회
    unique_codes = list({f["stock_code"] for f in filings if f.get("stock_code")})
    returns_map: dict[str, dict] = {}
    for code in unique_codes:
        try:
            returns_map[code] = fetch_period_returns_yf(code)
        except Exception:
            returns_map[code] = {}

    for f in filings:
        r = returns_map.get(f["stock_code"], {})
        f["change_pct"] = r.get("change_pct")
        f["return_3m"]  = r.get("return_3m")
        f["return_6m"]  = r.get("return_6m")
        f["return_1y"]  = r.get("return_1y")
        # 재무 필드 (미국은 SEC에서 직접 조회하지 않고 공란)
        f["fin_year"]              = None
        f["revenue"]               = None
        f["revenue_prev"]          = None
        f["operating_income"]      = None
        f["operating_income_prev"] = None

    return {
        "market": "US",
        "start_date": s,
        "end_date": e,
        "total": len(filings),
        "filings": filings,
    }
