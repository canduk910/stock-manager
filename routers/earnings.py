"""공시(정기보고서) API 라우터."""

from fastapi import APIRouter, HTTPException, Query

from screener.dart import fetch_filings
from screener.service import ScreenerValidationError, normalize_date
from stock.dart_fin import fetch_financials
from stock.market import fetch_period_returns

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


@router.get("/filings")
def get_filings(
    date: str | None = Query(
        None,
        description="단일 날짜 조회 (YYYYMMDD 또는 YYYY-MM-DD). start_date/end_date 와 함께 쓰면 무시됨.",
    ),
    start_date: str | None = Query(None, description="시작 날짜 (YYYYMMDD 또는 YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="종료 날짜 (YYYYMMDD 또는 YYYY-MM-DD)"),
):
    """기간별 정기보고서(사업/반기/분기) 제출 목록 조회.

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

    try:
        filings = fetch_filings(s, e)
    except RuntimeError as ex:
        raise HTTPException(status_code=502, detail=str(ex))

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
        "start_date": s,
        "end_date": e,
        "total": len(filings),
        "filings": filings,
    }
