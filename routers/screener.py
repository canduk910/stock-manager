"""스크리닝 API 라우터."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends, HTTPException, Query

from services.auth_deps import get_current_user
from services.exceptions import ExternalAPIError
from screener.dart import fetch_filings
from screener.krx import get_all_stocks
from screener.service import (
    ScreenerValidationError,
    apply_filters,
    normalize_date,
    parse_sort_spec,
    sort_stocks,
)
from stock.market import fetch_market_metrics, fetch_period_returns, fetch_price

router = APIRouter(prefix="/api/screener", tags=["screener"])


def _enrich_stock(stock: dict) -> dict:
    """종목별 현재가·수익률·배당수익률 추가 (캐시 활용)."""
    code = stock["code"]
    enriched = {**stock}

    try:
        price = fetch_price(code)
        if price:
            enriched["current_price"] = price["close"]
            prev = price["close"] - price["change"]
            enriched["prev_close"] = int(prev) if prev else None
            enriched["change_pct"] = price["change_pct"]
        else:
            enriched["current_price"] = None
            enriched["prev_close"] = None
            enriched["change_pct"] = None
    except Exception:
        enriched["current_price"] = None
        enriched["prev_close"] = None
        enriched["change_pct"] = None

    try:
        returns = fetch_period_returns(code)
        enriched["return_3m"] = returns.get("return_3m")
        enriched["return_6m"] = returns.get("return_6m")
        enriched["return_1y"] = returns.get("return_1y")
    except Exception:
        enriched["return_3m"] = None
        enriched["return_6m"] = None
        enriched["return_1y"] = None

    try:
        metrics = fetch_market_metrics(code)
        enriched["dividend_yield"] = metrics.get("dividend_yield")
        enriched["high_52"] = metrics.get("high_52")
        enriched["low_52"] = metrics.get("low_52")
        # 52주 고점 대비 하락률 (%)
        h52 = metrics.get("high_52")
        cur = enriched.get("current_price")
        if h52 and cur and h52 > 0:
            enriched["drop_from_high"] = round((cur - h52) / h52 * 100, 1)
        else:
            enriched["drop_from_high"] = None
    except Exception:
        enriched["dividend_yield"] = None
        enriched["high_52"] = None
        enriched["low_52"] = None
        enriched["drop_from_high"] = None

    return enriched


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
    drop_from_high: float | None = Query(None, description="52주 고점 대비 최대 하락률 (%, 예: -30)"),
    _user: dict = Depends(get_current_user),
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
        stocks, actual_date = get_all_stocks(target_date)
    except RuntimeError as e:
        raise ExternalAPIError(str(e))

    # 당일 실적발표 종목 필터
    if earnings_only:
        try:
            filings = fetch_filings(target_date, target_date)
        except RuntimeError as e:
            raise ExternalAPIError(str(e))
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

    # 현재가 · 수익률 · 배당수익률 · 52주 고저가 병렬 enrichment
    if stocks:
        enriched: list[dict | None] = [None] * len(stocks)
        with ThreadPoolExecutor(max_workers=min(20, len(stocks))) as ex:
            futures = {ex.submit(_enrich_stock, s): i for i, s in enumerate(stocks)}
            for fut in as_completed(futures):
                enriched[futures[fut]] = fut.result()
        stocks = enriched

    # 52주 고점 대비 하락률 필터 (enrichment 후 적용)
    if drop_from_high is not None:
        threshold = drop_from_high if drop_from_high < 0 else -drop_from_high
        stocks = [
            s for s in stocks
            if s.get("drop_from_high") is not None and s["drop_from_high"] <= threshold
        ]

    return {
        "date": actual_date,
        "total": len(stocks),
        "stocks": stocks,
    }
