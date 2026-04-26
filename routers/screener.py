"""스크리닝 API 라우터 — 구루 공식 + 체제 연계 확장."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends, HTTPException, Query

from services.auth_deps import get_current_user
from services.exceptions import ExternalAPIError
from screener.dart import fetch_filings
from screener.krx import get_all_stocks
from screener.service import (
    ScreenerValidationError,
    apply_filters,
    enrich_seo_scores,
    get_preset_filters,
    normalize_date,
    parse_sort_spec,
    sort_by_greenblatt_rank,
    sort_stocks,
)
from stock.market import fetch_market_metrics, fetch_period_returns, fetch_price

logger = logging.getLogger(__name__)

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


def _enrich_guru(stock: dict) -> dict:
    """종목별 구루 공식 점수 계산 (DART BS/IS 필요)."""
    from stock.dart_fin import fetch_bs_cf_annual, fetch_income_detail_annual
    from services.guru_formulas import (
        calc_greenblatt, calc_neff, calc_seo_expected_return,
        calc_guru_panel, check_value_trap,
    )
    from services.safety_grade import _count_fcf_years_positive, _calc_revenue_cagr

    code = stock["code"]
    enriched = {**stock}

    try:
        bs_cf = fetch_bs_cf_annual(code, years=3)
        bs_list = bs_cf.get("balance_sheet", [])
        cf_list = bs_cf.get("cashflow", [])
        is_detail = fetch_income_detail_annual(code, years=4)
        latest_bs = bs_list[-1] if bs_list else {}

        greenblatt = calc_greenblatt(
            operating_income=is_detail[-1].get("operating_income") if is_detail else None,
            current_assets=latest_bs.get("current_assets"),
            current_liabilities=latest_bs.get("current_liabilities"),
            ppe=latest_bs.get("ppe"),
            mktcap=stock.get("mktcap"),
            total_liabilities=latest_bs.get("total_liabilities"),
            cash_and_equiv=latest_bs.get("cash_and_equiv"),
        )

        eps_values = [row.get("eps") for row in is_detail if row.get("eps") is not None]
        neff = calc_neff(
            eps_values=eps_values,
            dividend_yield=stock.get("dividend_yield"),
            per=stock.get("per"),
        )

        seo = calc_seo_expected_return(
            roe=stock.get("roe"), pbr=stock.get("pbr"),
            per=stock.get("per"), dividend_yield=stock.get("dividend_yield"),
        )

        enriched["guru_scores"] = calc_guru_panel(greenblatt, neff, seo)

        fcf_years = _count_fcf_years_positive(cf_list)
        revenue_cagr = _calc_revenue_cagr(
            [{"revenue": row.get("revenue")} for row in is_detail] if is_detail else []
        )
        enriched["value_trap_warnings"] = check_value_trap(
            per=stock.get("per"), pbr=stock.get("pbr"), roe=stock.get("roe"),
            revenue_cagr=revenue_cagr, fcf_years_positive=fcf_years,
            debt_ratio=latest_bs.get("debt_ratio"),
        )
    except Exception:
        logger.warning("guru enrichment failed: %s", code, exc_info=True)
        enriched["guru_scores"] = None
        enriched["value_trap_warnings"] = []

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
    preset: str | None = Query(None, description="구루 프리셋: greenblatt | neff | seo"),
    regime_aware: bool = Query(False, description="체제 연계 (응답에 regime 포함)"),
    include_guru: bool = Query(False, description="구루 점수 포함 (DART enrichment 실행)"),
    guru_top: int | None = Query(None, description="DART enrichment 대상 종목 수"),
    _user: dict = Depends(get_current_user),
):
    """전종목 멀티팩터 스크리닝 + 구루 공식 + 체제 연계."""

    # ── 0단계: 체제 조회 ──
    regime_data = None
    if regime_aware or preset:
        try:
            from services import macro_service
            from services.macro_regime import determine_regime
            sentiment = macro_service.get_sentiment()
            regime_data = determine_regime(sentiment)
        except Exception:
            logger.warning("체제 조회 실패, graceful degradation", exc_info=True)

    # 프리셋별 기본 필터
    if preset and preset in ("greenblatt", "neff", "seo"):
        regime_name = regime_data["regime"] if regime_data else None
        pf = get_preset_filters(preset, regime_name)
        per_min = per_min if per_min is not None else pf.get("per_min")
        per_max = per_max if per_max is not None else pf.get("per_max")
        pbr_max = pbr_max if pbr_max is not None else pf.get("pbr_max")
        roe_min = roe_min if roe_min is not None else pf.get("roe_min")

    # ── 날짜 정규화 ──
    try:
        target_date = normalize_date(date)
    except ScreenerValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if market and market.upper() not in ("KOSPI", "KOSDAQ"):
        raise HTTPException(status_code=422, detail=f"시장은 KOSPI 또는 KOSDAQ만 허용됩니다: {market}")

    # ── 정렬 조건 ──
    if preset == "seo" and not sort_by:
        sort_specs = [("seo_return", True)]
    elif sort_by:
        try:
            sort_specs = parse_sort_spec(sort_by)
        except ScreenerValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
    else:
        sort_specs = [("mktcap", True)]

    # ── 1단계: KRX 데이터 수집 + 기본 필터 ──
    try:
        stocks, actual_date = get_all_stocks(target_date)
    except RuntimeError as e:
        raise ExternalAPIError(str(e))

    if earnings_only:
        try:
            filings = fetch_filings(target_date, target_date)
        except RuntimeError as e:
            raise ExternalAPIError(str(e))
        filing_codes = {f["stock_code"] for f in filings}
        stocks = [s for s in stocks if s["code"] in filing_codes]

    stocks = apply_filters(
        stocks, market=market, per_min=per_min, per_max=per_max,
        pbr_max=pbr_max, roe_min=roe_min, include_negative=include_negative,
    )

    # 서준식 점수 즉시 계산 (KRX 데이터만)
    stocks = enrich_seo_scores(stocks)

    stocks = sort_stocks(stocks, sort_specs)

    if top is not None and top > 0:
        stocks = stocks[:top]

    # ── 2단계: yfinance enrichment (기존) ──
    if stocks:
        enriched: list[dict | None] = [None] * len(stocks)
        with ThreadPoolExecutor(max_workers=min(20, len(stocks))) as ex:
            futures = {ex.submit(_enrich_stock, s): i for i, s in enumerate(stocks)}
            for fut in as_completed(futures):
                enriched[futures[fut]] = fut.result()
        stocks = enriched

    if drop_from_high is not None:
        threshold = drop_from_high if drop_from_high < 0 else -drop_from_high
        stocks = [
            s for s in stocks
            if s.get("drop_from_high") is not None and s["drop_from_high"] <= threshold
        ]

    # ── 3단계: DART guru enrichment ──
    guru_enabled = include_guru or (preset and preset in ("greenblatt", "neff"))
    if guru_enabled and stocks:
        enrich_count = guru_top or len(stocks)
        target_stocks = stocks[:enrich_count]
        rest_stocks = stocks[enrich_count:]

        guru_enriched: list[dict | None] = [None] * len(target_stocks)
        with ThreadPoolExecutor(max_workers=min(10, len(target_stocks))) as ex:
            futures = {ex.submit(_enrich_guru, s): i for i, s in enumerate(target_stocks)}
            for fut in as_completed(futures):
                guru_enriched[futures[fut]] = fut.result()

        if preset == "greenblatt":
            guru_enriched = sort_by_greenblatt_rank(guru_enriched)
        elif preset == "neff":
            guru_enriched.sort(
                key=lambda s: (s.get("guru_scores") or {}).get("neff", {}).get("neff_ratio") or -999,
                reverse=True,
            )

        stocks = guru_enriched + [
            {**s, "guru_scores": None, "value_trap_warnings": []} for s in rest_stocks
        ]

    # ── 4단계: 응답 조립 ──
    response = {
        "date": actual_date,
        "total": len(stocks),
        "stocks": stocks,
    }

    if regime_data:
        response["regime"] = {
            "regime": regime_data["regime"],
            "regime_desc": regime_data.get("regime_desc", ""),
            "vix": regime_data.get("vix"),
            "buffett_ratio": regime_data.get("buffett_ratio"),
            "fear_greed_score": regime_data.get("fear_greed_score"),
        }

    if preset:
        response["preset"] = preset

    return response
