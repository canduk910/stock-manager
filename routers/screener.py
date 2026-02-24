"""스크리닝 API 라우터."""

from fastapi import APIRouter, HTTPException, Query

from screener.dart import fetch_filings
from screener.krx import get_all_stocks
from screener.service import (
    ScreenerValidationError,
    apply_filters,
    normalize_date,
    parse_sort_spec,
    sort_stocks,
)

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("/stocks")
def get_stocks(
    date: str | None = Query(None, description="조회 날짜 (YYYYMMDD 또는 YYYY-MM-DD, 기본: 오늘)"),
    sort_by: str | None = Query(None, description='정렬 기준 (예: PER, "ROE desc, PER asc")'),
    top: int | None = Query(None, description="상위 N개만 반환"),
    per_min: float | None = Query(None, description="PER 최소값"),
    per_max: float | None = Query(None, description="PER 최대값"),
    pbr_max: float | None = Query(None, description="PBR 최대값"),
    roe_min: float | None = Query(None, description="ROE 최소값 (%)"),
    market: str | None = Query(None, description="시장 필터 (KOSPI 또는 KOSDAQ)"),
    include_negative: bool = Query(False, description="적자기업(PER 음수) 포함 여부"),
    earnings_only: bool = Query(False, description="당일 실적발표 종목만 대상"),
):
    """전종목 멀티팩터 스크리닝."""
    # 날짜 정규화
    try:
        target_date = normalize_date(date)
    except ScreenerValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 시장 파라미터 검증
    if market and market.upper() not in ("KOSPI", "KOSDAQ"):
        raise HTTPException(status_code=422, detail=f"시장은 KOSPI 또는 KOSDAQ만 허용됩니다: {market}")

    # 정렬 조건 파싱
    if sort_by:
        try:
            sort_specs = parse_sort_spec(sort_by)
        except ScreenerValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
    else:
        sort_specs = [("mktcap", True)]  # 기본: 시가총액 내림차순

    # KRX 데이터 수집 (동기 — threadpool에서 실행됨)
    try:
        stocks = get_all_stocks(target_date)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 당일 실적발표 종목 필터
    if earnings_only:
        try:
            filings = fetch_filings(target_date, target_date)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))
        filing_codes = {f["stock_code"] for f in filings}
        stocks = [s for s in stocks if s["code"] in filing_codes]

    # 필터 적용
    stocks = apply_filters(
        stocks,
        market=market,
        per_min=per_min,
        per_max=per_max,
        pbr_max=pbr_max,
        roe_min=roe_min,
        include_negative=include_negative,
    )

    # 정렬
    stocks = sort_stocks(stocks, sort_specs)

    # 상위 N개 제한
    if top is not None and top > 0:
        stocks = stocks[:top]

    return {
        "date": target_date,
        "total": len(stocks),
        "stocks": stocks,
    }
