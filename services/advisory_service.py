"""AI자문 서비스 레이어.

종목별 AI 투자 리포트를 생성하는 핵심 서비스. 데이터 수집부터 GPT 호출, 결과 저장까지의
전체 파이프라인을 관리한다.

데이터 흐름:
  refresh_stock_data()               generate_ai_report()
  ┌──────────────────┐               ┌──────────────────────────────────┐
  │ _collect_fundamental (7~8 task)│   │ advisory_cache → 프롬프트 조립    │
  │ _collect_technical (15분봉)    │──→│ _build_system_prompt (4전략+7점) │
  │ _collect_strategy_signals(MCP) │   │ _build_prompt (재무+기술+매크로)  │
  │         ↓                      │   │         ↓                        │
  │ advisory_cache에 JSON 저장     │   │ OpenAI GPT 호출 (재시도 3단계)   │
  └──────────────────┘               │         ↓                        │
                                      │ _parse_report → Pydantic v2 검증│
                                      │         ↓                        │
                                      │ advisory_reports DB 저장          │
                                      └──────────────────────────────────┘

재시도 전략 3단계:
1) 토큰 잘림(finish_reason=="length"): 10000→12000 토큰으로 재시도, 2차 실패 시 저장 거부
2) Pydantic v2 검증 실패: 추가 지침과 함께 1회 재시도
3) 일반 에러(네트워크/rate limit 등): 2초 backoff 후 1회 재시도

의존 관계:
- stock/advisory_fetcher.py → 15분봉 OHLCV + 기술지표 + 사업 개요
- stock/dart_fin.py → 국내 DART 재무제표
- stock/yf_client.py → 해외 yfinance 재무데이터
- stock/advisory_store.py → 캐시/리포트 DB CRUD
- services/macro_regime.py → 공용 체제 판단
- services/safety_grade.py → 7점 등급 사전 계산
- services/backtest_service.py → MCP 전략 신호 (선택)
"""

from __future__ import annotations

import json
from typing import Optional

import logging

from config import OPENAI_API_KEY, OPENAI_MODEL

from stock import advisory_store, advisory_fetcher
from stock.utils import is_domestic
from services.exceptions import (
    ConfigError, ExternalAPIError, NotFoundError, PaymentRequiredError,
)
from services.macro_regime import (
    determine_regime as _shared_determine_regime,
    REGIME_DESC,
    get_regime_params as _get_regime_params_cycle,
    get_margin_requirement as _get_margin_requirement_cycle,
)

logger = logging.getLogger(__name__)


# ── 공개 API ──────────────────────────────────────────────────────────────────

def refresh_stock_data(code: str, market: str, name: str, user_id: int = 1) -> dict:
    """전체 데이터 수집 → advisory_cache 저장 → 저장된 캐시 반환.

    국내(KR): dart_fin + market.fetch_market_metrics + 15분봉KIS
    해외(US): yf_client + 15분봉 yfinance
    + KIS MCP 전략 신호 (활성화 시)
    """
    fundamental = _collect_fundamental(code, market, name, user_id)
    technical = _collect_technical(code, market)
    strategy_signals = _collect_strategy_signals(code, market)
    research_data = _collect_research(code, market, name)

    advisory_store.save_cache(user_id, code, market, fundamental, technical,
                              strategy_signals=strategy_signals,
                              research_data=research_data)
    return advisory_store.get_cache(user_id, code, market) or {}


def _collect_research(code: str, market: str, name: str) -> dict:
    """리서치 데이터 수집 (실패 시 빈 dict)."""
    try:
        from stock.research_collector import collect_all_research
        return collect_all_research(code, market, name)
    except Exception as e:
        logger.warning("리서치 데이터 수집 실패 %s: %s", code, e)
        return {}


def generate_ai_report(code: str, market: str, name: str, user_id: int = 1) -> dict:
    """저장된 캐시 데이터를 기반으로 OpenAI GPT-4o 리포트 생성.

    Phase 3: max_completion_tokens 10000 기본, 재시도 시 12000.
    finish_reason=="length" 1차 재시도, 2차 실패 시 ExternalAPIError → 저장 거부.
    Pydantic v2 검증 실패 시 1회 재시도.
    """
    if not OPENAI_API_KEY:
        raise ConfigError("OPENAI_API_KEY가 설정되지 않았습니다.")

    cache = advisory_store.get_cache(user_id, code, market)
    if not cache:
        raise NotFoundError("분석 데이터가 없습니다. 먼저 새로고침을 해주세요.")

    fundamental = cache.get("fundamental") or {}
    technical = cache.get("technical") or {}
    strategy_signals = cache.get("strategy_signals")  # MCP 전략 신호 (없으면 None)
    research_data = cache.get("research_data") or {}

    model = OPENAI_MODEL
    graham_data = _calc_graham_number(fundamental, market)

    # 매크로 컨텍스트 수집 (캐시 활용, 실패 시 빈 dict)
    macro_ctx = _get_macro_context()
    regime, regime_desc = _determine_regime(macro_ctx)

    # 경기 사이클 컨텍스트 수집 (신규: 보수성 완화 위해 cycle×regime 조합 판단)
    cycle_ctx = _get_cycle_context()

    # 항상 통합 프롬프트 (v2/v3 분기 없음)
    system_prompt = _build_system_prompt(regime, regime_desc, cycle_ctx)
    prompt = _build_prompt(code, market, name, fundamental, technical,
                           graham_data, macro_ctx, regime, regime_desc,
                           strategy_signals, research_data, cycle_ctx)

    def _call_openai(max_tokens: int, extra_user_msg: str = "", check_quota: bool = True) -> tuple[str, str]:
        """AI Gateway를 통한 OpenAI 호출. (content, finish_reason) 반환."""
        from services.ai_gateway import call_openai_chat
        user_content = prompt + extra_user_msg
        resp = call_openai_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            user_id=user_id,
            service_name="advisory_report",
            check_quota=check_quota,
            model=model,
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        finish = resp.choices[0].finish_reason or "stop"
        return content, finish

    try:
        import time as _time
        from services.ai_gateway import AiQuotaExceededError

        # 통합 v3: 16000 기본, 20000 재시도
        base_tokens = 16000
        retry_tokens = 20000

        content, finish_reason = _call_openai(base_tokens)

        # 토큰 잘림 1차 재시도
        if finish_reason == "length":
            logger.warning("종목 자문 응답 토큰 잘림 1차 (%s), %d로 재시도", code, retry_tokens)
            _time.sleep(1)
            content, finish_reason = _call_openai(retry_tokens, check_quota=False)
            if finish_reason == "length":
                logger.error("종목 자문 응답 토큰 잘림 2차 (%s), 저장 거부", code)
                raise ExternalAPIError("응답이 토큰 제한으로 잘렸습니다. 다시 시도해주세요.")

        report = _parse_report(content)

        # Pydantic v3 검증
        from services.schemas.advisory_report_v3 import validate_v3_report
        ok, _, err = validate_v3_report(report)

        if not ok:
            logger.warning("v3 검증 실패 (%s): %s — 1회 재시도", code, err[:200] if err else "")
            _time.sleep(1)
            retry_msg = "\n\n응답을 반드시 유효한 JSON으로 작성하세요. schema_version='v3' 필수 필드를 누락하지 마세요."
            content2, finish2 = _call_openai(base_tokens, retry_msg, check_quota=False)
            if finish2 == "length":
                logger.warning("v3 재시도도 토큰 잘림 (%s)", code)
            report = _parse_report(content2)

    except (ConfigError, NotFoundError, PaymentRequiredError, ExternalAPIError, AiQuotaExceededError):
        raise
    except Exception as e:
        err_str = str(e)
        if "insufficient_quota" in err_str or "429" in err_str:
            raise PaymentRequiredError(
                "OpenAI API 크레딧이 부족합니다. platform.openai.com에서 결제 정보를 확인해주세요.",
            )
        # 일반 에러 1회 재시도 (backoff 2초)
        import time as _time
        logger.warning("OpenAI 1차 호출 실패 (%s): %s — 2초 후 재시도", code, err_str[:200])
        _time.sleep(2)
        try:
            content, finish_reason = _call_openai(14000, check_quota=False)
            report = _parse_report(content)
        except Exception as e2:
            raise ExternalAPIError(f"OpenAI 호출 실패: {str(e2)}")

    # 정량 필드 추출 → DB 저장 (항상 v3)
    from services.schemas.advisory_report_v3 import extract_v3_fields
    v2_fields = extract_v3_fields(report)

    report_id = advisory_store.save_report(
        user_id, code, market, model, report,
        grade=v2_fields.get("grade"),
        grade_score=v2_fields.get("grade_score"),
        composite_score=v2_fields.get("composite_score"),
        regime_alignment=v2_fields.get("regime_alignment"),
        schema_version=v2_fields.get("schema_version", "v1"),
        value_trap_warning=v2_fields.get("value_trap_warning", False),
    )

    # 사전 계산 vs GPT 등급 gap 로깅
    gpt_grade = v2_fields.get("grade")
    if gpt_grade:
        logger.info("리포트 저장 [%s %s]: GPT등급=%s, schema=%s, VT=%s",
                     code, gpt_grade, v2_fields.get("schema_version"),
                     v2_fields.get("value_trap_warning"))

    return advisory_store.get_latest_report(user_id, code, market) or {}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _collect_fundamental(code: str, market: str, name: str, user_id: int = 1) -> dict:
    """기본적 분석 데이터 수집."""
    if market == "KR":
        return _collect_fundamental_kr(code, name, user_id)
    return _collect_fundamental_us(code)


def _collect_fundamental_kr(code: str, name: str, user_id: int = 1) -> dict:
    """국내 종목 기본적 분석 데이터 수집.

    ThreadPoolExecutor 7개 task 매핑표:
    | Task         | 함수                                | 데이터               | 소스      |
    |--------------|-------------------------------------|---------------------|-----------|
    | f_income     | dart_fin.fetch_income_detail_annual  | 손익계산서 (10년)     | DART      |
    | f_bs_cf      | dart_fin.fetch_bs_cf_annual          | 대차대조표+현금흐름(10년)| DART    |
    | f_metrics    | fetch_market_metrics                 | PER/PBR/ROE/시총    | yfinance  |
    | f_segments   | advisory_fetcher.fetch_segments_kr   | 사업 개요+키워드      | DART+GPT  |
    | f_forward    | fetch_forward_estimates_yf           | Forward PE/EPS      | yfinance  |
    | f_val_stats  | advisory_fetcher.fetch_valuation_stats| PER/PBR 5년 통계   | yfinance  |
    | f_quarterly  | dart_fin.fetch_quarterly_financials  | 분기 실적 (8분기)    | DART      |
    """
    from concurrent.futures import ThreadPoolExecutor
    from stock import dart_fin
    from stock.market import fetch_market_metrics
    from stock.yf_client import fetch_forward_estimates_yf

    with ThreadPoolExecutor(max_workers=7) as pool:
        f_income = pool.submit(dart_fin.fetch_income_detail_annual, code, 10)
        f_bs_cf = pool.submit(dart_fin.fetch_bs_cf_annual, code, 10)
        f_metrics = pool.submit(fetch_market_metrics, code)
        f_segments = pool.submit(advisory_fetcher.fetch_segments_kr, code, name, user_id)
        f_forward = pool.submit(fetch_forward_estimates_yf, code, True)
        f_val_stats = pool.submit(advisory_fetcher.fetch_valuation_stats, code, "KR")
        f_quarterly = pool.submit(dart_fin.fetch_quarterly_financials, code, 8)

        income_stmt = f_income.result()
        bs_cf = f_bs_cf.result()
        balance_sheet = bs_cf.get("balance_sheet", [])
        cashflow = bs_cf.get("cashflow", [])
        metrics_raw = f_metrics.result()
        metrics = _build_metrics_kr(metrics_raw, balance_sheet, income_stmt)
        segments_data = f_segments.result()
        forward_estimates = f_forward.result()
        valuation_stats = f_val_stats.result()
        quarterly = f_quarterly.result()

    # 하위호환: 구 캐시가 list일 수 있음
    if isinstance(segments_data, dict):
        segments = segments_data.get("segments", [])
        biz_desc = segments_data.get("description", "")
        biz_keywords = segments_data.get("keywords", [])
    else:
        segments = segments_data if isinstance(segments_data, list) else []
        biz_desc = ""
        biz_keywords = []

    return {
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "metrics": metrics,
        "segments": segments,
        "business_description": biz_desc,
        "business_keywords": biz_keywords,
        "forward_estimates": forward_estimates,
        "valuation_stats": valuation_stats,  # Phase 2-2
        "quarterly": quarterly,              # Phase 2-3
    }


def _collect_fundamental_us(code: str) -> dict:
    """해외 종목 기본적 분석 데이터 수집.

    ThreadPoolExecutor 8개 task — 모두 yfinance 기반 (DART 미사용).
    국내 _collect_fundamental_kr과 동일한 반환 구조를 유지하여 하위 호출자가
    시장 구분 없이 동일하게 처리할 수 있다.
    """
    from concurrent.futures import ThreadPoolExecutor
    from stock.yf_client import (
        fetch_income_detail_yf,
        fetch_balance_sheet_yf,
        fetch_cashflow_yf,
        fetch_metrics_yf,
        fetch_segments_yf,
        fetch_forward_estimates_yf,
        fetch_quarterly_financials_yf,
    )

    with ThreadPoolExecutor(max_workers=8) as pool:
        f_income = pool.submit(fetch_income_detail_yf, code, 10)
        f_bs = pool.submit(fetch_balance_sheet_yf, code, 10)
        f_cf = pool.submit(fetch_cashflow_yf, code, 10)
        f_metrics = pool.submit(fetch_metrics_yf, code)
        f_segments = pool.submit(fetch_segments_yf, code)
        f_forward = pool.submit(fetch_forward_estimates_yf, code, False)
        f_val_stats = pool.submit(advisory_fetcher.fetch_valuation_stats, code, "US")
        f_quarterly = pool.submit(fetch_quarterly_financials_yf, code, 8)

        income_stmt = f_income.result()
        balance_sheet = f_bs.result()
        cashflow = f_cf.result()
        metrics = f_metrics.result()
        segments_data = f_segments.result()
        forward_estimates = f_forward.result()
        valuation_stats = f_val_stats.result()
        quarterly = f_quarterly.result()

    # 하위호환: 구 캐시가 list일 수 있음
    if isinstance(segments_data, dict):
        segments = segments_data.get("segments", [])
        biz_desc = segments_data.get("description", "")
        biz_keywords = segments_data.get("keywords", [])
    else:
        segments = segments_data if isinstance(segments_data, list) else []
        biz_desc = ""
        biz_keywords = []

    return {
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "metrics": metrics,
        "segments": segments,
        "business_description": biz_desc,
        "business_keywords": biz_keywords,
        "forward_estimates": forward_estimates,
        "valuation_stats": valuation_stats,  # Phase 2-2
        "quarterly": quarterly,              # Phase 2-3
    }


def _build_metrics_kr(
    raw: Optional[dict],
    balance_sheet: list | None = None,
    income_stmt: list | None = None,
) -> dict:
    """stock/market.py fetch_market_metrics + 재무데이터 → advisory 표준 형식.

    balance_sheet/income_stmt에서 ROA, 부채비율, 유동비율, PSR, PBR(대안) 계산.
    """
    base = raw or {}
    per = base.get("per")
    pbr = base.get("pbr")
    roe = base.get("roe")
    mktcap = base.get("mktcap")
    market_type = base.get("market_type")

    # 대차대조표 최신 연도 값
    bs_latest = (balance_sheet or [])[-1] if balance_sheet else None
    debt_to_equity = None
    current_ratio = None
    total_assets = None
    total_equity = None
    if bs_latest:
        debt_to_equity = bs_latest.get("debt_ratio")
        current_ratio = bs_latest.get("current_ratio")
        total_assets = bs_latest.get("total_assets")
        total_equity = bs_latest.get("total_equity")

    # 손익계산서 최신 연도 값
    is_latest = (income_stmt or [])[-1] if income_stmt else None
    revenue = None
    net_income = None
    if is_latest:
        revenue = is_latest.get("revenue")
        net_income = is_latest.get("net_income")

    # ROA = 순이익 / 총자산 × 100
    roa = None
    if net_income is not None and total_assets and total_assets > 0:
        roa = round(net_income / total_assets * 100, 2)

    # PSR = 시가총액 / 매출액
    psr = None
    if mktcap and revenue and revenue > 0:
        psr = round(mktcap / revenue, 2)

    # PBR: yfinance에서 None이면 시가총액/자본총계로 대체 계산
    if pbr is None and mktcap and total_equity and total_equity > 0:
        pbr = round(mktcap / total_equity, 2)

    # EPS (주당순이익) — DART 우선, 없으면 net_income/shares fallback
    eps = None
    if is_latest:
        eps = is_latest.get("eps")
    if not eps and net_income and net_income > 0:
        shares = base.get("shares")
        if shares and shares > 0:
            eps = round(net_income / shares)

    # Graham Number = sqrt(22.5 × EPS × BPS)
    graham_number = None
    if eps and eps > 0 and pbr and pbr > 0:
        shares = base.get("shares")
        if mktcap and shares and shares > 0:
            price = mktcap / shares
            bps = price / pbr
            import math
            graham_number = round(math.sqrt(22.5 * eps * bps))

    return {
        "per": per,
        "pbr": pbr,
        "roe": roe,
        "market_cap": mktcap,
        "market_type": market_type,
        "psr": psr,
        "ev_ebitda": None,  # 순부채 데이터 필요, 추후 지원
        "roa": roa,
        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "eps": eps,
        "graham_number": graham_number,
        "dividend_yield": base.get("dividend_yield"),
        "dividend_per_share": base.get("dividend_per_share"),
    }


def _collect_technical(code: str, market: str) -> dict:
    """기술적 분석 데이터 수집 (15분봉 + 지표)."""
    if market == "KR":
        ohlcv = advisory_fetcher.fetch_15min_ohlcv_kr(code)
    else:
        ohlcv = advisory_fetcher.fetch_15min_ohlcv_us(code)

    indicators = advisory_fetcher.calc_technical_indicators(ohlcv)

    return {
        "ohlcv": ohlcv,
        "indicators": indicators,
    }


def _collect_strategy_signals(code: str, market: str) -> Optional[dict]:
    """KIS AI Extensions 전략 신호 수집 (MCP 비활성화 시 None).

    MCP 서버가 비활성화(KIS_MCP_ENABLED=false)이거나 연결 실패 시 None을 반환하여
    전략 신호 없이도 AI 리포트가 정상 생성되도록 graceful degrade를 보장한다.
    """
    try:
        from services.backtest_service import get_strategy_signals
        return get_strategy_signals(code, market)
    except Exception as e:
        logger.debug("전략 신호 수집 실패 [%s]: %s", code, e)
        return None


def _calc_graham_number(fundamental: dict, market: str) -> dict:
    """Graham Number = sqrt(22.5 × EPS × BPS) 계산.
    BPS 직접 데이터 없으면 price/PBR 역산 (KR/US 공통).
    EPS <= 0 이면 Graham Number = None.
    """
    import math as _math
    metrics = fundamental.get("metrics") or {}
    income  = fundamental.get("income_stmt") or []
    per = metrics.get("per")
    pbr = metrics.get("pbr")

    eps: Optional[float] = None
    if income:
        raw_eps = income[-1].get("eps")
        if raw_eps is not None:
            try:
                eps = float(raw_eps)
            except (TypeError, ValueError):
                eps = None

    bps: Optional[float] = None
    method = "N/A"
    if per and pbr and per > 0 and pbr > 0 and eps and eps > 0:
        estimated_price = eps * per
        bps = round(estimated_price / pbr, 2)
        method = "PBR역산"

    graham_number: Optional[float] = None
    if eps and bps and eps > 0 and bps > 0:
        graham_number = round(_math.sqrt(22.5 * eps * bps), 2)

    current_price: Optional[float] = None
    if eps and per and per > 0:
        current_price = round(eps * per, 0)
    else:
        mc = metrics.get("market_cap")
        sh = metrics.get("shares")
        if mc and sh and sh > 0:
            current_price = round(mc / sh, 2)

    discount_rate: Optional[float] = None
    if graham_number and current_price and current_price > 0:
        discount_rate = round((graham_number - current_price) / current_price * 100, 1)

    return {
        "graham_number": graham_number,
        "eps": round(eps, 2) if eps else None,
        "bps": bps,
        "discount_rate": discount_rate,
        "method": method,
    }


def _get_macro_context() -> dict:
    """매크로 심리 데이터 수집 (캐시 활용, 실패 시 빈 dict)."""
    try:
        from services import macro_service
        return macro_service.get_sentiment()
    except Exception as e:
        logger.debug("매크로 컨텍스트 수집 실패: %s", e)
        return {}


def _determine_regime(sentiment: dict) -> tuple[str, str]:
    """sentiment → (regime, regime_desc) 반환 — 공용 모듈 위임.

    2차원 버핏×공포탐욕 매트릭스 + VIX>35 오버라이드 적용.
    """
    result = _shared_determine_regime(sentiment)
    return result["regime"], result["regime_desc"]


def _get_cycle_context() -> dict:
    """경기 사이클 국면 데이터 수집. 실패 시 빈 dict.

    portfolio_advisor와 동일 함수 — 향후 macro_service.get_macro_cycle()로 통합 가능.
    """
    try:
        from stock import macro_fetcher
        from services.macro_cycle import determine_cycle_phase
        inputs = macro_fetcher.fetch_cycle_inputs()
        return determine_cycle_phase(inputs)
    except Exception as e:
        logger.debug("경기 사이클 수집 실패: %s", e)
        return {}


# 체제별 요구 안전마진(%) — 공용 모듈 REGIME_PARAMS에서 가져옴 (하위 호환)
# 예: accumulation=20%, selective=25%, cautious=30%, defensive=40%
# 이 값은 프롬프트에 "요구 안전마진: N% 이상"으로 삽입되어
# GPT가 Graham Number 할인율과 비교하여 투자 판단을 내리는 기준이 된다.
from services.macro_regime import REGIME_PARAMS as _SHARED_REGIME_PARAMS
_REGIME_MARGIN = {k: v["margin"] for k, v in _SHARED_REGIME_PARAMS.items()}


def _build_macro_section(macro_ctx: Optional[dict], regime: str, regime_desc: str) -> str:
    """유저 프롬프트에 삽입할 매크로 환경 섹션."""
    if not macro_ctx:
        return ""
    fg = macro_ctx.get("fear_greed") or {}
    fg_val = fg.get("value") if fg.get("value") is not None else fg.get("score")
    vix = macro_ctx.get("vix") or {}
    buffett = macro_ctx.get("buffett") or {}
    vix_val = vix.get("value")
    buf_ratio = buffett.get("ratio")
    req_margin = _REGIME_MARGIN.get(regime, 25)
    lines = [f"## 매크로 환경 (시장 체제: {regime_desc})"]
    if fg_val is not None:
        lines.append(f"- 공포탐욕지수: {fg_val}")
    if vix_val is not None:
        lines.append(f"- VIX: {vix_val}")
    if buf_ratio is not None:
        lines.append(f"- 버핏지수: {buf_ratio}%")
    lines.append(f"- 시장 체제: {regime} ({regime_desc})")
    lines.append(f"- 요구 안전마진: {req_margin}% 이상")
    return "\n".join(lines)


def _build_strategy_signal_section(signals: Optional[dict]) -> str:
    """KIS 전략 신호 프롬프트 섹션.

    MCP 전략 신호 dict를 프롬프트 텍스트로 변환한다.
    - signals가 None이면 "MCP 서버 비활성화" 메시지 반환
    - 각 전략의 BUY/SELL/HOLD 신호와 강도를 퍼센트로 표시
    - 백테스트 메트릭(수익률/샤프/낙폭)이 있으면 함께 표시
    """
    if not signals:
        return "## KIS 전략 신호\n- MCP 서버 비활성화 (전략 분석 미사용)"

    lines = ["## KIS 전략 신호 (퀀트 백테스팅 기반)"]
    for s in signals.get("signals", []):
        strength_pct = f"{s.get('strength', 0) * 100:.0f}%"
        lines.append(f"- {s.get('strategy', 'unknown')}: {s.get('signal', 'HOLD')} (강도 {strength_pct})")

    consensus = signals.get("consensus", "HOLD")
    avg = signals.get("avg_strength", 0)
    lines.append(f"- 전략 합의: {consensus} (평균 강도 {avg * 100:.0f}%)")

    bt_list = signals.get("backtest_metrics") or []
    if bt_list:
        for bt in bt_list if isinstance(bt_list, list) else [bt_list]:
            if isinstance(bt, dict):
                ret = bt.get("total_return_pct")
                sharpe = bt.get("sharpe_ratio")
                dd = bt.get("max_drawdown")
                parts = []
                if ret is not None:
                    parts.append(f"수익률 {ret:+.1f}%")
                if sharpe is not None:
                    parts.append(f"샤프 {sharpe:.2f}")
                if dd is not None:
                    parts.append(f"낙폭 {dd:.1f}%")
                if parts:
                    name = bt.get("strategy", "")
                    lines.append(f"- 백테스트({name}): {', '.join(parts)}")

    return "\n".join(lines)


# ── 체제×사이클 16셀 투자 원칙 ─────────────────────────────────────────
# 기존 단일 체제 규칙은 cycle을 무시해 "확장+defensive" 같은 조합에서 사이클 주도
# 섹터 진입을 봉쇄했다. 신규 매트릭스는 cycle 보정으로 강세장에서 부분 진입을
# 허용하면서도 약세장 보수성을 유지한다.
#
# 행=regime, 열=cycle_phase (recovery/expansion/overheating/contraction)
# 각 셀: 진입 정책 한 줄 — 시스템 프롬프트에 삽입되어 GPT 판단을 가이드한다.
_CYCLE_REGIME_RULES: dict[tuple[str, str], str] = {
    # accumulation (저평가 — 적극 진입 기조)
    ("accumulation", "recovery"):
        "축적+회복기: 사이클 주도 섹터(금융/산업재/소재) 적극 매수. Graham 할인 15%+ 강매수. 종목당 7%까지.",
    ("accumulation", "expansion"):
        "축적+확장기: 기술/임의소비재 우선. Graham 할인 15%+ 매수. 종목당 6%까지.",
    ("accumulation", "overheating"):
        "축적+과열기: 에너지/소재/필수소비재 회전. Graham 할인 25%+ 강매수. 종목당 5%.",
    ("accumulation", "contraction"):
        "축적+수축기: 유틸리티/헬스케어/필수소비재. Graham 할인 10%+ 매수. 종목당 5%.",
    # selective (중립 — 선별 매수)
    ("selective", "recovery"):
        "선별+회복기: 사이클 주도 섹터 한정 매수. Graham 할인 15%+. 종목당 5%.",
    ("selective", "expansion"):
        "선별+확장기: 기술 성장주 우선. Graham 할인 15%+. 종목당 4%.",
    ("selective", "overheating"):
        "선별+과열기: 방어 회전. Graham 할인 25%+ 만 매수. 종목당 3%.",
    ("selective", "contraction"):
        "선별+수축기: 방어주 한정. Graham 할인 10%+ 매수. 종목당 4%.",
    # cautious (신중 — 방어적 운용)
    ("cautious", "recovery"):
        "신중+회복기: 사이클 주도 섹터에 한해 분할 매수 허용. Graham 할인 15%+. 종목당 4%. 손절 명시.",
    ("cautious", "expansion"):
        "신중+확장기: 기술 성장주 분할 매수. Graham 할인 15%+. 종목당 3%. 손절 명시.",
    ("cautious", "overheating"):
        "신중+과열기: 매수 신호 보수적. Graham 할인 25%+만. 종목당 2%. 손절 -10%.",
    ("cautious", "contraction"):
        "신중+수축기: 방어주만 매수. Graham 할인 10%+. 종목당 3%. 손절 명시.",
    # defensive (방어 — 사이클 보정으로 부분 매수 허용)
    ("defensive", "recovery"):
        "방어+회복기: **사이클 주도 섹터 한정 단계적 매수 허용**(권고치의 30~50%). Graham 할인 15%+. 종목당 7%. "
        "성장 보조 G-A 종목은 가치 D라도 분할 진입 검토.",
    ("defensive", "expansion"):
        "방어+확장기: **사이클 주도 섹터(기술/임의소비재) 단계적 매수 허용**(권고치 30~50%). Graham 할인 15%+. 종목당 5%.",
    ("defensive", "overheating"):
        "방어+과열기: 매수 매우 제한적(권고치 30%만). Graham 할인 25%+만. 종목당 2%. 손절 -8%.",
    ("defensive", "contraction"):
        "방어+수축기: 신규 매수 금지. 매도/관망/현금 보존. 안전마진 40%+ 종목만 관심목록.",
}


def _format_cycle_regime_rule(regime: str, cycle_phase: Optional[str]) -> str:
    """체제+사이클 결합 규칙 1줄 + Graham 할인 임계 cycle 보정 안내."""
    if cycle_phase:
        rule = _CYCLE_REGIME_RULES.get((regime, cycle_phase))
        if rule:
            return rule
    # cycle 정보 없으면 기존 체제 단일 기조 (보수성 완화 톤)
    fallback = {
        "accumulation": "축적: 안전마진 20%+ 적극 매수. 종목당 5~7%.",
        "selective": "선별: 안전마진 25%+ 매수. 종목당 4~5%.",
        "cautious": "신중: 안전마진 30%+ 조건부 매수. 종목당 3~4%. 손절 명시.",
        "defensive": "방어: 신규 매수 매우 제한적. 사이클 정보 부재 시 관망 우선.",
    }
    return fallback.get(regime, fallback["selective"])


def _build_system_prompt(
    regime: str,
    regime_desc: str,
    cycle_ctx: Optional[dict] = None,
) -> str:
    """통합 시스템 프롬프트 — 6대 비판적 분석 + 정량 프레임워크 + 미래지향/역발상.

    cycle_ctx 추가(2026-05-01): cycle×regime 16셀 매트릭스로 cycle을 반영해
    "어떤 경우에도 매수 금지" 톤을 사이클 보정으로 완화.
    """
    cycle_phase = (cycle_ctx or {}).get("phase")
    cycle_label = (cycle_ctx or {}).get("phase_label", cycle_phase or "데이터없음")
    leader_sectors = (cycle_ctx or {}).get("leader_sectors") or []
    cycle_conf = (cycle_ctx or {}).get("confidence")
    regime_rule = _format_cycle_regime_rule(regime, cycle_phase)
    leader_str = ", ".join(leader_sectors) if leader_sectors else "데이터없음"
    return (
        "당신은 20년 경력의 베테랑 수석 에퀴티 리서치 애널리스트이다. "
        "'안전마진'과 '전통적 가치'를 중시하되, **결정은 과거가 아닌 미래에 베팅한다**. "
        "비판적 투자 보고서를 JSON으로 작성하며, 예스맨의 태도를 버리고 냉철하게 분석하라. "
        "모든 결론은 데이터에 근거해야 하며, 낙관적 전망보다 리스크 관리에 우선순위를 둔다. "
        "증권사 컨센서스를 무비판적으로 수용하지 말 것 — 합의도(dispersion)/과열(consensus_overheated)/체제 신뢰도를 종합 판단할 것. "
        "컨센서스 과열 또는 일방적 매수 의견은 **반박 기회**(역발상)로 간주한다.\n\n"

        "【핵심 분석 원칙】\n"
        "1. 과거 재무는 '점검 도구'이고, 결정의 근거는 '미래의 변화'다. 과거 5년 ROE보다 향후 12개월 catalyst가 더 중요할 수 있다.\n"
        "2. 역발상(Contrarian)을 적극 검토하라:\n"
        "   - 과매도+펀더멘털 강건 → 매수 기회 (시장 오해 식별)\n"
        "   - 산업 저점에서의 capex 회복 → 사이클 턴어라운드 신호\n"
        "   - 컨센서스 일방적 매수+dispersion<0.1 → 과열 의심 (반박 근거 우선 탐색)\n"
        "   - 컨센서스 일방적 매도+자사주 매입+내부자 매수 → 시장 오해 가능성\n"
        "3. catalyst를 명시적으로 식별하라 (3개 이상 권장):\n"
        "   - 신규 사업/제품/시장 진입, 규제 변경, M&A, 자사주 매입, 배당 정책 변경, 구조조정, 산업 사이클 회복, capex 변곡점\n"
        "4. peak-out 검증: 매출/이익 성장률 둔화, capex 정점 통과, 산업 출하/가동률 하락은 미래 EPS 하향의 선행지표.\n"
        "5. 산업 사이클 단계(industry_cycle_phase: 도입/성장/성숙/쇠퇴/불명)와 종목 위치를 일치시켜 판단하라.\n\n"

        "【보고서 핵심 구조 — 8대 분석 항목 (JSON에 반드시 포함)】\n\n"

        "1. 재무건전성분석: OCF vs 순이익 괴리(분식 가능성), 부채비율 추세, 이자보상배율 → risk_level(안전/주의/위험/심각)\n"
        "2. 밸류에이션분석: PER/PBR 밴드 내 현재 위치, 적정가치 산출, 업종대비, PEG → 밸류에이션판단\n"
        "3. 매크로및산업분석: 시장체제 해석, 금리/환율 영향, Peak-out 여부, 산업사이클(도입/성장/성숙/쇠퇴/불명)\n"
        "4. 경영진트랙레코드: M&A 성패, 자본배분 일관성(우수/양호/보통/미흡), 배당정책, 거버넌스\n"
        "5. 가치함정분석: 구조적 쇠퇴 vs 일시적 악재 판별 → decline_type + evidence 배열\n"
        "6. 최종매매전략: 적정가치/추천진입가/손절가/upside·downside %/worst_scenario/포지션사이징/action(적극매수~전량매도)\n"
        "7. 미래성장동력 (FORWARD-LOOKING): catalysts(3개 이상), turning_points(변곡점 신호), industry_tailwinds(산업 순풍), peak_out_signals(피크아웃 신호 또는 빈 배열)\n"
        "8. 역발상관점 (CONTRARIAN): contrarian_thesis(역발상 논제), market_misperception(시장 오해 포인트), edge(차별화된 인사이트), rebut_consensus(컨센서스 반박 또는 동조 근거)\n\n"

        "【정량 분석 프레임워크】\n\n"
        "전략 1: 변동성 돌파 (래리 윌리엄스) — 당일 시가+(전일 범위×K) 돌파 시 매수. K=0.5 표준.\n"
        "전략 2: 안전마진 (벤자민 그레이엄) — Graham Number=sqrt(22.5×EPS×BPS). 할인율 >30%: 강매수, 10~30%: 매수, <0%: 고평가. 적자 3년↑: 평가불가.\n"
        "전략 3: 추세추종 — MA5>MA20>MA60 정배열+MACD+RSI55↑: 강세.\n\n"

        "【7점 등급 체계 (28점 만점)】\n"
        "| 지표 | 4점 | 3점 | 2점 | 1점 |\n"
        "| Graham 할인율 | >40% | 20-40% | 0-20% | <0% |\n"
        "| PER vs 5Y평균 | <-30% | -30~-10% | ±10% | >+10% |\n"
        "| PBR 절대 | <0.7 | 0.7-1.0 | 1.0-1.5 | >1.5 |\n"
        "| 부채비율 | <50% | 50-100% | 100-200% | >200% |\n"
        "| 유동비율 | >2.0 | 1.5-2.0 | 1.0-1.5 | <1.0 |\n"
        "| FCF 양수연수 | 3년 | 2년 | 1년 | 0 |\n"
        "| 매출CAGR(3Y) | >10% | 5-10% | 0-5% | <0% |\n"
        "등급: A=24-28, B+=20-23, B=16-19, C=12-15, D=<12. 데이터 없으면 2점.\n\n"

        "MacroSentinel: 버핏지수×공포탐욕 매트릭스. VIX>35→extreme_fear 강제.\n"
        "OrderAdvisor: 손절 A=-8%/B+=-10%/B=-12%/C·D=진입금지. grade_factor A=1.0/B+=0.75/B=0.50/C·D=0. 분할매수 50-30-20%. R:R≥2.0.\n"
        "ValueScreener Value Trap 6규칙 (2개↑ 시 경고): 1)매출CAGR<0%+PER<5, 2)영업이익률 3년↓, 3)FCF 3년음수, 4)부채비율 30%p↑, 5)배당중단, 6)증권사 컨센서스 과열(consensus_overheated=True 시 가산 1점).\n"
        "KIS 퀀트 (보조): SMA/Momentum/Trend 3전략. consensus=BUY+강도>0.6이면 확인.\n\n"

        f"【현재 매크로 환경】\n"
        f"체제={regime}({regime_desc}) / 사이클={cycle_label}"
        + (f" (신뢰도 {cycle_conf}%)" if cycle_conf is not None else "")
        + f" / 주도 섹터={leader_str}\n"
        f"진입 정책: {regime_rule}\n\n"

        "【보수성 완화 — 체제×사이클 조합 판단】\n"
        "- defensive 체제라도 사이클이 회복/확장이면 사이클 주도 섹터에 한정해 단계적 매수(권고치의 30~50%) 가능.\n"
        "  단 '확신 없는 일괄 매수 금지'는 유효 — 진입가/손절가/리스크보상비율을 명시하라.\n"
        "- C 등급(점수 12~15)은 GRADE_FACTOR=0.25로 소형 분할 진입 허용. 손절 -15%.\n"
        "- D 등급(점수 <12)은 가치 평가상 진입 금지가 원칙. 단 **성장주 보조 등급 G-A**(아래 참조)인 경우\n"
        "  factor=0.30, 손절 -20%로 분할 진입 검토 가능. 일반 가치주 D는 진입 금지 유지.\n"
        "- 모든 매수 권고는 분할(1차 30% → 2차 30% → 3차 40%)과 손절가를 명시하라.\n\n"

        "【성장주 보조 트랙】\n"
        "프롬프트 하단 '성장주 보조 등급 사전 계산값'을 참조하여 가치 D 종목이라도 G-A이면\n"
        "JSON 응답의 '성장주_보조판단' 필드에 growth_grade/growth_score/growth_thesis/cycle_alignment를 채우고,\n"
        "최종매매전략.action을 '분할매수'로 권고할 수 있다(가치 D + G-A 조합만 허용).\n"
        "단 가치 D + G-B/G-C는 진입 금지를 유지하라.\n\n"

        "【Graham 할인 임계의 사이클 보정】\n"
        "강매수 임계는 사이클별로 차등 적용한다 (전 체제 공통):\n"
        "- 회복/확장기: 15% 이상 (강세장 정량 벽 완화)\n"
        "- 과열기: 25% 이상 (안전마진 강화)\n"
        "- 수축기: 10% 이상 (충분한 가격 조정 후)\n"
        "기존 30% 일률 적용보다 시장 분위기를 반영한 합리적 기준이다.\n\n"

        "모든 논리적 허점은 가차 없이 비판하라. 단 '매도/SKIP만의 일변도'는 회피하라 — "
        "체제×사이클 조합이 허용하는 범위에서 진입 시그널을 적극 식별할 것."
    )


def _format_money(value, market: str) -> str:
    """금액 표기 — KR: 천원 단위 콤마, US: $."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if (market or "").upper() == "KR":
        return f"{int(round(v)):,}원"
    return f"${v:,.2f}"


def _build_consensus_section(
    consensus_data: Optional[dict],
    market: str,
    regime: str,
) -> str:
    """REQ-ANALYST-08: 증권사 컨센서스 12번 섹션 빌더.

    체제별 차등:
      - defensive → 빈 문자열 (섹션 자체 미표시)
      - cautious → 50% 감산 경고 라인 포함
      - accumulation/selective → 정상

    데이터 0건(data_source='empty') → 빈 문자열.
    US (target_price 부재) → 등급 변경 이력 형식.
    """
    # 2026-05-01: defensive 체제 가드 폐지 — cautious와 동일하게 50% 가중 감산만 적용.
    # 기존엔 defensive에서 컨센서스 섹션 자체가 사라져 매수 의견이 GPT 시야에서 제거됐다.
    # 이제 defensive에서도 컨센서스 노출하되 신뢰도 50% 감산 경고를 명시한다.
    if not consensus_data or not isinstance(consensus_data, dict):
        return ""

    data_source = consensus_data.get("data_source") or "empty"
    if data_source == "empty":
        return ""

    reports = consensus_data.get("reports") or []
    if not reports:
        return ""

    consensus = consensus_data.get("consensus") or {}
    momentum_signal = consensus_data.get("momentum_signal") or "flat"
    overheated = bool(consensus_data.get("consensus_overheated"))
    history_line = consensus_data.get("history_line") or ""
    is_us_grades = data_source == "yfinance_upgrades" or (
        consensus.get("target_median") is None
    )

    lines: list[str] = []

    if is_us_grades:
        # ── US: 등급 변경 이력 형식 ──
        lines.append("\n## 12. 증권사 등급 변경 이력")
        lines.append("  최근 3건:")
        for r in reports[:3]:
            broker = r.get("broker", "?")
            date_s = r.get("date", "")
            title = r.get("title", "")
            lines.append(f"    - {broker} ({date_s}): {title}")
        lines.append(f"  momentum_signal: {momentum_signal}")
    else:
        # ── KR: 컨센서스 통계 형식 ──
        lines.append("\n## 12. 증권사 컨센서스")
        target_median = consensus.get("target_median")
        upside = consensus.get("upside_pct_median")
        if target_median is not None:
            up_str = (
                f" (현재가 대비 {upside:+.1f}%)" if upside is not None else ""
            )
            lines.append(
                f"  중앙 목표가: {_format_money(target_median, market)}{up_str}"
            )

        target_mean = consensus.get("target_mean")
        target_stdev = consensus.get("target_stdev")
        if target_mean is not None and target_stdev is not None:
            lines.append(
                f"  평균: {_format_money(target_mean, market)}, "
                f"표준편차: {_format_money(target_stdev, market)}"
            )

        dispersion = consensus.get("target_dispersion")
        if dispersion is not None:
            lines.append(f"  합의도(dispersion): {dispersion} (0.2 미만=강합의)")

        d3 = consensus.get("opinion_dist_3") or {}
        count = consensus.get("count", 0)
        lines.append(
            f"  매수 {d3.get('buy', 0)} / 보유 {d3.get('hold', 0)} / "
            f"매도 {d3.get('sell', 0)} (3단계 정규화, 총 {count}건)"
        )
        lines.append(f"  momentum_signal: {momentum_signal}")

        if overheated:
            lines.append(
                "  ⚠ 과열 시그널: 6개월 내 동일 증권사들이 평균 30% 이상 상향. "
                "Value Trap 평가 시 가중 반영."
            )

        regime_lc = (regime or "").lower()
        if regime_lc in ("cautious", "defensive"):
            lines.append(
                "  ⚠ 신중/방어 체제에서는 증권사 컨센서스가 늦은 하향 경향. "
                "신뢰도 50% 가중 감산 필요."
            )

        # 최근 3건 요약
        lines.append("")
        lines.append("  최근 3건 요약:")
        for r in reports[:3]:
            broker = r.get("broker", "?")
            date_s = r.get("date", "")
            opinion = r.get("opinion", "")
            tp = r.get("target_price")
            tp_str = (
                f", TP {_format_money(tp, market)}" if tp is not None else ""
            )
            summary = (r.get("summary") or "").strip()
            summary_disp = summary[:100] if summary else "(본문 요약 없음)"
            lines.append(
                f"    - {broker} ({date_s}, {opinion}{tp_str}): {summary_disp}"
            )

        if history_line:
            lines.append("")
            lines.append(f"  6개월 목표가 추이: {history_line}")

    return "\n".join(lines)


def _build_prompt(code: str, market: str, name: str, fundamental: dict, technical: dict,
                  graham_data: Optional[dict] = None,
                  macro_ctx: Optional[dict] = None,
                  regime: str = "selective",
                  regime_desc: str = "중립",
                  strategy_signals: Optional[dict] = None,
                  research_data: Optional[dict] = None,
                  cycle_ctx: Optional[dict] = None) -> str:
    """GPT 유저 프롬프트 구성 (통합 v3).

    프롬프트 구조 (위→아래 순서):
    1) 손익계산서 (전체)
    2) 이자보상배율 추세
    3) 대차대조표 (전체)
    4) 현금흐름표 (전체)
    5) 계량지표 (PER/PBR/ROE/PSR/EV-EBITDA)
    6) 기술적 시그널 (MACD/RSI/Stochastic/MA20)
    7) 변동성 돌파 전략 데이터 (ATR, K=0.3/0.5/0.7 목표가)
    8) 안전마진 분석 (Graham Number + 할인율)
    9) 추세추종 전략 데이터 (MA 정배열, MACD 크로스)
    10) 포워드 가이던스 (Forward PE/EPS, 애널리스트 컨센서스)
    11) PER/PBR 5년 히스토리 비교
    12) 분기 실적 추세 (최근 4분기)
    13) 거래량·볼린저밴드 신호
    14) 7점 등급 사전 계산값 (safety_grade.py 결과 — GPT 참고용)
    15) 매크로 환경 섹션 (체제 + VIX + 버핏지수 + 공포탐욕)
    16) KIS 전략 신호 (MCP 백테스트 결과)
    17) 리서치 데이터 (거시지표/실적일/경영진/공시/뉴스)
    18) JSON 응답 스키마 명세 (v3 통합)
    """
    currency = "KRW(억원)" if market == "KR" else "USD(백만달러)"

    # 손익 요약 (전체)
    income = fundamental.get("income_stmt") or []
    income_all = income
    income_summary = []
    for row in income_all:
        rev = row.get("revenue")
        oi = row.get("operating_income")
        ni = row.get("net_income")
        oi_m = row.get("oi_margin")
        net_m = row.get("net_margin")
        income_summary.append(
            f"  {row['year']}년: 매출={_fmt(rev, market)}, "
            f"영업이익={_fmt(oi, market)}({oi_m}%), "
            f"순이익={_fmt(ni, market)}({net_m}%)"
        )

    # 이자보상배율 추세
    ic_summary = []
    for row in income:
        oi = row.get("operating_income")
        ie = row.get("interest_expense")
        if oi is not None and ie is not None and ie != 0:
            cov = round(oi / abs(ie), 2)
            ic_summary.append(f"  {row['year']}년: 이자보상배율={cov}x")

    # 대차대조표 요약 (전체)
    bs = fundamental.get("balance_sheet") or []
    bs_all = bs
    bs_summary = []
    for row in bs_all:
        ta = row.get("total_assets")
        te = row.get("total_equity")
        dr = row.get("debt_ratio")
        cr = row.get("current_ratio")
        bs_summary.append(
            f"  {row['year']}년: 자산={_fmt(ta, market)}, "
            f"자본={_fmt(te, market)}, 부채비율={dr}%, 유동비율={cr}%"
        )

    # 현금흐름 요약 (전체)
    cf = fundamental.get("cashflow") or []
    cf_all = cf
    cf_summary = []
    for row in cf_all:
        op = row.get("operating_cf")
        fc = row.get("free_cf")
        cf_summary.append(
            f"  {row['year']}년: 영업CF={_fmt(op, market)}, FCF={_fmt(fc, market)}"
        )

    # 계량지표
    metrics = fundamental.get("metrics") or {}
    per = metrics.get("per", "N/A")
    pbr = metrics.get("pbr", "N/A")
    roe = metrics.get("roe", "N/A")
    psr = metrics.get("psr", "N/A")
    ev_ebitda = metrics.get("ev_ebitda", "N/A")
    div_yield = metrics.get("dividend_yield")
    div_per_share = metrics.get("dividend_per_share")
    div_yield_str = f"{div_yield}%" if div_yield is not None else "N/A"
    div_per_share_str = (
        f"{div_per_share:,.0f}원" if (market or "").upper() == "KR" and div_per_share
        else (f"${div_per_share}" if div_per_share else "N/A")
    )

    # 기술적 시그널
    indicators = technical.get("indicators") or {}
    signals = indicators.get("current_signals") or {}
    macd_cross = signals.get("macd_cross", "none")
    rsi_signal = signals.get("rsi_signal", "neutral")
    rsi_val = signals.get("rsi_value")
    stoch_signal = signals.get("stoch_signal", "neutral")
    stoch_k = signals.get("stoch_k")
    above_ma20 = signals.get("above_ma20", False)

    # 전략 관련 신규 필드
    ma5_cur      = signals.get("ma5")
    ma20_cur     = signals.get("ma20")
    ma60_cur     = signals.get("ma60")
    ma_alignment = signals.get("ma_alignment", "혼합")
    atr_val      = signals.get("atr")
    cur_price_sig = signals.get("current_price")
    vt_k03 = signals.get("volatility_target_k03") or indicators.get("volatility_target_k03")
    vt_k05 = signals.get("volatility_target_k05") or indicators.get("volatility_target_k05")
    vt_k07 = signals.get("volatility_target_k07") or indicators.get("volatility_target_k07")

    def _break_status(target, price):
        if target is None or price is None or price == 0:
            return "데이터없음"
        return "돌파" if price >= target else "미돌파"

    vt_k03_status = _break_status(vt_k03, cur_price_sig)
    vt_k05_status = _break_status(vt_k05, cur_price_sig)
    vt_k07_status = _break_status(vt_k07, cur_price_sig)

    # Graham Number
    gn = graham_data or {}
    graham_number = gn.get("graham_number")
    discount_rate = gn.get("discount_rate")
    gn_eps        = gn.get("eps")
    gn_bps        = gn.get("bps")
    gn_method     = gn.get("method", "N/A")
    gn_str        = f"{graham_number:,.0f} ({gn_method})" if graham_number else f"N/A ({gn_method})"
    dr_str        = f"{discount_rate:+.1f}%" if discount_rate is not None else "N/A"

    macd_label = {'golden': '골든크로스(매수신호)', 'dead': '데드크로스(매도신호)', 'none': '크로스 없음'}.get(macd_cross, macd_cross)

    # Forward Estimates (yfinance) — 국내는 전 필드 None인 경우 많음
    fwd = fundamental.get("forward_estimates") or {}

    def _fmt_na(v, suffix=""):
        if v is None or (isinstance(v, float) and (v != v)):  # NaN 체크
            return "N/A"
        if isinstance(v, (int, float)):
            return f"{v}{suffix}"
        return f"{v}{suffix}"

    forward_pe = _fmt_na(fwd.get("forward_pe"))
    forward_eps = _fmt_na(fwd.get("forward_eps"))
    target_mean = _fmt_na(fwd.get("target_mean_price"))
    recommendation = _fmt_na(fwd.get("recommendation"))
    num_analysts = _fmt_na(fwd.get("num_analysts"))

    # Phase 2-2: PER/PBR 5년 통계
    val_stats = fundamental.get("valuation_stats") or {}
    per_avg_5y = _fmt_na(val_stats.get("per_avg_5y"))
    per_max_5y = _fmt_na(val_stats.get("per_max_5y"))
    per_min_5y = _fmt_na(val_stats.get("per_min_5y"))
    per_cur_5y = _fmt_na(val_stats.get("per_current"))
    per_dev_pct = _fmt_na(val_stats.get("per_deviation_pct"))
    pbr_avg_5y = _fmt_na(val_stats.get("pbr_avg_5y"))
    pbr_max_5y = _fmt_na(val_stats.get("pbr_max_5y"))
    pbr_min_5y = _fmt_na(val_stats.get("pbr_min_5y"))
    pbr_cur_5y = _fmt_na(val_stats.get("pbr_current"))
    pbr_dev_pct = _fmt_na(val_stats.get("pbr_deviation_pct"))

    # Phase 2-3: 분기 실적 (최근 4분기)
    quarterly = fundamental.get("quarterly") or []
    quarterly_summary = []
    for q in quarterly[-4:]:
        quarterly_summary.append(
            f"  {q.get('year')}Q{q.get('quarter')}: 매출={_fmt(q.get('revenue'), market)}, "
            f"영업이익={_fmt(q.get('operating_income'), market)}({q.get('oi_margin')}%), "
            f"순이익={_fmt(q.get('net_income'), market)}({q.get('net_margin')}%)"
        )

    # Phase 2-1: 거래량·변동성 신호
    volume_signal = _fmt_na(signals.get("volume_signal"))
    volume_5d = _fmt_na(signals.get("volume_5d_avg"))
    volume_20d = _fmt_na(signals.get("volume_20d_avg"))
    bb_position = _fmt_na(signals.get("bb_position"))

    # 사업 개요 + 사업부문 (역발상/미래지향 분석 핵심)
    biz_desc = fundamental.get("business_description") or ""
    biz_keywords = fundamental.get("business_keywords") or []
    segments = fundamental.get("segments") or []
    segments_lines = []
    for s in segments[:8]:
        if isinstance(s, dict):
            seg_name = s.get("name") or s.get("segment") or ""
            seg_pct = s.get("ratio") or s.get("pct") or s.get("percentage")
            seg_desc = s.get("description") or ""
            if seg_pct is not None:
                segments_lines.append(f"  - {seg_name} {seg_pct}%{(': ' + seg_desc) if seg_desc else ''}")
            elif seg_name:
                segments_lines.append(f"  - {seg_name}{(': ' + seg_desc) if seg_desc else ''}")
        elif isinstance(s, str):
            segments_lines.append(f"  - {s}")

    # 52주 가격 위치 (research.basic_macro에서)
    bm_quick = (research_data or {}).get("basic_macro") or {}
    high_52 = bm_quick.get("high_52")
    low_52 = bm_quick.get("low_52")
    cur_for_pos = cur_price_sig or bm_quick.get("current_price")
    pos_lines = []
    if cur_for_pos and high_52:
        try:
            pct_to_high = (float(cur_for_pos) - float(high_52)) / float(high_52) * 100
            pos_lines.append(f"  현재가 vs 52주 고가({_format_money(high_52, market)}): {pct_to_high:+.1f}%")
        except Exception:
            pass
    if cur_for_pos and low_52:
        try:
            pct_from_low = (float(cur_for_pos) - float(low_52)) / float(low_52) * 100
            pos_lines.append(f"  현재가 vs 52주 저가({_format_money(low_52, market)}): {pct_from_low:+.1f}%")
        except Exception:
            pass

    # 자본행위 분류 (CB/BW/유증/감자/자사주/배당) — 미래 EPS 변화 신호
    capital_keywords = {
        "유상증자": ["유상증자", "주주배정", "제3자배정"],
        "전환사채(CB)": ["전환사채", "CB"],
        "신주인수권부사채(BW)": ["신주인수권", "BW"],
        "감자": ["감자"],
        "자사주매입": ["자기주식취득", "자사주취득", "자기주식매입"],
        "자사주소각": ["자기주식소각", "자사주소각"],
        "배당": ["배당"],
        "M&A": ["합병", "분할", "양수도", "인수"],
    }
    ca_research = (research_data or {}).get("capital_actions") or {}
    filings_all = ca_research.get("filings") or []
    capital_events = []
    for f_item in filings_all[:30]:
        report_name = (f_item.get("report_name") or f_item.get("report_type") or "")
        for label, keywords in capital_keywords.items():
            if any(k in report_name for k in keywords):
                rcept = f_item.get("rcept_dt", "")
                capital_events.append(f"  - {rcept}: [{label}] {report_name}")
                break

    # 장기(10년) 밸류에이션 사이클 — 저점/평균/고점 + 현재 위치
    val_history = ((research_data or {}).get("valuation_band") or {}).get("valuation_history") or []
    val_cycle_line = ""
    if val_history:
        per_vals = [v.get("per") for v in val_history if v.get("per") is not None]
        pbr_vals = [v.get("pbr") for v in val_history if v.get("pbr") is not None]
        if per_vals:
            per_lo = min(per_vals); per_hi = max(per_vals)
            per_avg = sum(per_vals) / len(per_vals)
            val_cycle_line = (
                f"  PER 10년 범위: {per_lo:.1f}~{per_hi:.1f}배, 평균 {per_avg:.1f}배 (n={len(per_vals)})"
            )
            if pbr_vals:
                pbr_lo = min(pbr_vals); pbr_hi = max(pbr_vals)
                pbr_avg = sum(pbr_vals) / len(pbr_vals)
                val_cycle_line += (
                    f"\n  PBR 10년 범위: {pbr_lo:.2f}~{pbr_hi:.2f}배, 평균 {pbr_avg:.2f}배"
                )

    # 경쟁사 비교 (peers)
    peers_data = ((research_data or {}).get("industry_peers") or {}).get("peers") or []
    peers_lines = []
    for p in peers_data[:6]:
        if isinstance(p, dict):
            ticker = p.get("ticker") or p.get("symbol") or ""
            p_name = p.get("name") or ticker
            p_per = p.get("per")
            p_pbr = p.get("pbr")
            p_mc = p.get("market_cap")
            mc_str = _format_money(p_mc, market) if p_mc else "N/A"
            peers_lines.append(
                f"  - {p_name}({ticker}): PER={p_per if p_per is not None else 'N/A'}, "
                f"PBR={p_pbr if p_pbr is not None else 'N/A'}, 시총={mc_str}"
            )

    # Phase 2-4: 7점 등급 사전 계산 (참고용)
    from services.safety_grade import compute_grade_7point, compute_composite_score, compute_regime_alignment
    grade_pre = compute_grade_7point(
        metrics=metrics,
        balance_sheet=fundamental.get("balance_sheet") or [],
        cashflow=fundamental.get("cashflow") or [],
        income_stmt=fundamental.get("income_stmt") or [],
        valuation_stats=val_stats if val_stats else None,
        graham_number=gn.get("graham_number") if gn else None,
        current_price=gn.get("current_price") if gn else None,
    )
    composite_score = compute_composite_score(metrics)
    regime_alignment_score = compute_regime_alignment(
        regime=regime,
        grade_score=grade_pre["score"],
        fcf_years_positive=grade_pre["details"]["fcf_trend"]["years_positive"],
    )

    # 성장주 보조 등급 (2026-05-01 신규) — 가치 평가에 불리한 성장주 우회 트랙
    from services.growth_grade import compute_growth_grade, combine_grades
    sector_str = (research_data or {}).get("industry_peers", {}).get("sector") or fundamental.get("sector")
    cycle_phase = (cycle_ctx or {}).get("phase")
    growth_pre = compute_growth_grade(
        metrics=metrics,
        income_stmt=fundamental.get("income_stmt") or [],
        cashflow=fundamental.get("cashflow") or [],
        rnd_ratio=metrics.get("rnd_ratio") if metrics else None,
        sector=sector_str,
        cycle_phase=cycle_phase,
    )
    final_factor, final_label = combine_grades(grade_pre["grade"], growth_pre["grade"])

    # cycle 보정 안전마진 요구치
    margin_req = _get_margin_requirement_cycle(regime, cycle_phase) if cycle_phase else _REGIME_MARGIN.get(regime, 25)
    cycle_label_for_prompt = (cycle_ctx or {}).get("phase_label", cycle_phase or "데이터없음")
    leader_sectors_for_prompt = ", ".join((cycle_ctx or {}).get("leader_sectors") or []) or "데이터없음"
    cycle_conf = (cycle_ctx or {}).get("confidence")

    prompt = f"""다음은 {name}({code}, {market}) 종목의 분석 데이터입니다. 통화단위: {currency}

## 손익계산서 (전체)
{chr(10).join(income_summary) or '데이터 없음'}

## 이자보상배율 추세
{chr(10).join(ic_summary) or '  데이터 없음 (이자비용 미공시)'}

## 대차대조표 (전체)
{chr(10).join(bs_summary) or '데이터 없음'}

## 현금흐름표 (전체)
{chr(10).join(cf_summary) or '데이터 없음'}

## 계량지표
- PER: {per}배, PBR: {pbr}배, ROE: {roe}%, PSR: {psr}배, EV/EBITDA: {ev_ebitda}배
- 배당수익률: {div_yield_str}, 주당배당금: {div_per_share_str}

## 사업 개요 (역발상·미래지향 분석의 출발점)
- 설명: {biz_desc or '데이터 없음'}
- 핵심 키워드: {', '.join(biz_keywords) if biz_keywords else 'N/A'}
- 사업부문 매출 비중:
{chr(10).join(segments_lines) or '  데이터 없음'}

## 가격 위치 (52주 기준)
{chr(10).join(pos_lines) or '  데이터 없음'}

## 자본행위 분류 (최근 1년 — 미래 EPS·주주가치 변화 신호)
{chr(10).join(capital_events) or '  유의미한 자본행위 공시 없음'}

## 장기(10년) 밸류에이션 사이클
{val_cycle_line or '  데이터 없음'}

## 경쟁사 비교
{chr(10).join(peers_lines) or '  데이터 없음'}

## 기술적 시그널 (15분봉 기준)
- MACD: {macd_cross} ({macd_label})
- RSI: {rsi_val}({rsi_signal})
- 스토캐스틱 %K: {stoch_k}({stoch_signal})
- MA20 상회: {above_ma20}

## 변동성 돌파 전략 데이터
- 현재가: {cur_price_sig}
- ATR(14): {atr_val}
- K=0.3 목표가: {vt_k03} → {vt_k03_status}
- K=0.5 목표가: {vt_k05} → {vt_k05_status}
- K=0.7 목표가: {vt_k07} → {vt_k07_status}

## 안전마진 분석 (Graham Number)
- Graham Number: {gn_str}
- EPS: {gn_eps}, BPS: {gn_bps}
- 현재가 대비 할인율: {dr_str} (양수=내재가치 대비 저평가, 음수=고평가)

## 추세추종 전략 데이터
- MA 정렬: {ma_alignment} (MA5={ma5_cur}, MA20={ma20_cur}, MA60={ma60_cur})
- MACD 크로스: {macd_cross}
- RSI: {rsi_val} ({rsi_signal})

## 포워드 가이던스 (국내종목은 대부분 N/A)
- Forward PE: {forward_pe}
- Forward EPS: {forward_eps}
- 애널리스트 목표가(평균): {target_mean}
- 투자의견 점수(1=Strong Buy ~ 5=Strong Sell): {recommendation}
- 애널리스트 수: {num_analysts}

## PER/PBR 5년 히스토리 비교
- PER: 현재 {per_cur_5y}배 / 5년 평균 {per_avg_5y}배 (범위 {per_min_5y}~{per_max_5y}, 편차 {per_dev_pct}%)
- PBR: 현재 {pbr_cur_5y}배 / 5년 평균 {pbr_avg_5y}배 (범위 {pbr_min_5y}~{pbr_max_5y}, 편차 {pbr_dev_pct}%)
- 편차 <-20%: 5년 평균 대비 저평가 / >+20%: 고평가로 해석

## 분기 실적 추세 (최근 {len(quarterly)}분기)
{chr(10).join(quarterly_summary) or '  데이터 없음 (소형주 또는 미공시)'}

## 거래량·변동성 신호
- 거래량 신호 (최신/직전5일평균): {volume_signal}배 (>1.5 급증 / <0.7 급감)
- 5일 평균 거래량: {volume_5d}, 20일 평균: {volume_20d}
- 볼린저밴드 위치: {bb_position} (0=하단 터치, 100=상단 터치, 50=중간)

## 7점 등급 사전 계산값 (참고용 — 가치 평가)
사전 계산 등급: {grade_pre['grade']} ({grade_pre['score']}/28점)
- Graham 할인율: {grade_pre['details']['discount']['points']}/4
- PER vs 5년평균: {grade_pre['details']['per_vs_avg']['points']}/4
- PBR 절대: {grade_pre['details']['pbr']['points']}/4
- 부채비율: {grade_pre['details']['debt_ratio']['points']}/4
- 유동비율: {grade_pre['details']['current_ratio']['points']}/4
- FCF 추세: {grade_pre['details']['fcf_trend']['points']}/4
- 매출 CAGR: {grade_pre['details']['revenue_cagr']['points']}/4
복합 점수: {composite_score}/100 (ValueScreener 공식)
체제 정합성: {regime_alignment_score}/100

## 성장주 보조 등급 사전 계산값 (참고용 — 신규 트랙)
사전 계산 성장 등급: {growth_pre['grade']} ({growth_pre['score']}/20점)
- 매출 CAGR: {growth_pre['details']['revenue_cagr']['points']}/4
- 영업이익 CAGR: {growth_pre['details']['operating_cagr']['points']}/4
- FCF 추세: {growth_pre['details']['fcf_trend']['points']}/4 ({growth_pre['details']['fcf_trend']['label']})
- R&D/매출: {growth_pre['details']['rnd_ratio']['points']}/4
- 사이클 정합성: {growth_pre['details']['cycle_alignment']['points']}/4 ({growth_pre['details']['cycle_alignment']['label']})
성장 thesis: {growth_pre['thesis']}
가치+성장 결합 라벨: {final_label} (final_factor={final_factor})
※ 가치 D + 성장 G-A 종목은 분할 진입 검토 가능 (factor=0.30, 손절 -20%).
※ 위는 데이터 기반 사전 계산이며, GPT는 추세·매크로·기술시그널을 종합해 최종 등급을 부여할 것.
   사전 계산을 단순 복사하지 말고, 독립적 판단을 내리되 불일치 시 reasoning에 근거 명시.

## 경기 사이클 + 체제 조합
- 시장 체제: {regime} ({regime_desc})
- 경기 사이클 국면: {cycle_label_for_prompt}{f" (신뢰도 {cycle_conf}%)" if cycle_conf is not None else ""}
- 사이클 주도 섹터: {leader_sectors_for_prompt}
- 본 종목 섹터: {sector_str or 'N/A'}
- cycle 보정 안전마진 요구치: {margin_req}% 이상 (Graham 할인율 기준)
- 진입 정책: {_format_cycle_regime_rule(regime, cycle_phase)}

{_build_macro_section(macro_ctx, regime, regime_desc)}

{_build_strategy_signal_section(strategy_signals)}

"""

    # ── 리서치 데이터 섹션 (있으면 추가) ──
    research = research_data or {}
    research_sections = []

    # 거시 지표
    bm = research.get("basic_macro") or {}
    macro_ind = bm.get("macro") or {}
    if macro_ind:
        lines = ["\n## 8. 거시 경제 지표"]
        if macro_ind.get("us_10y_yield") is not None: lines.append(f"  미국 10Y 국채: {macro_ind['us_10y_yield']}%")
        if macro_ind.get("gold") is not None: lines.append(f"  금(Gold): ${macro_ind['gold']}/oz")
        if macro_ind.get("oil_wti") is not None: lines.append(f"  WTI 원유: ${macro_ind['oil_wti']}/bbl")
        if macro_ind.get("usd_krw") is not None: lines.append(f"  원/달러: {macro_ind['usd_krw']}원")
        if macro_ind.get("dollar_index") is not None: lines.append(f"  달러인덱스: {macro_ind['dollar_index']}")
        research_sections.append("\n".join(lines))

    # 밸류에이션 밴드 + 실적일
    vb = research.get("valuation_band") or {}
    ed = vb.get("earnings_dates") or []
    if ed:
        lines = ["\n## 실적 발표일 및 서프라이즈"]
        for e in ed[:8]:
            surprise = f"{e.get('surprise_pct')}%" if e.get("surprise_pct") is not None else "N/A"
            lines.append(f"  {e.get('date','?')}: 예상={e.get('eps_estimate','N/A')}, 실제={e.get('eps_actual','N/A')}, 서프라이즈={surprise}")
        research_sections.append("\n".join(lines))

    # 경영진
    mgmt = research.get("management") or {}
    officers = mgmt.get("officers") or []
    if officers:
        lines = ["\n## 9. 경영진 정보"]
        for o in officers[:5]:
            pay = f", 보수=${o['total_pay']:,.0f}" if o.get("total_pay") else ""
            lines.append(f"  - {o.get('name','')} ({o.get('title','')}{pay})")
        research_sections.append("\n".join(lines))

    holders = mgmt.get("major_holders") or {}
    inst = holders.get("institutional") or []
    if inst:
        lines = ["\n## 주요 기관투자자"]
        for h in inst[:5]:
            pct = f"{h.get('pct_held',0)*100:.1f}%" if h.get("pct_held") else "N/A"
            lines.append(f"  - {h.get('holder','')}: {pct}")
        research_sections.append("\n".join(lines))

    # 공시
    ca = research.get("capital_actions") or {}
    filings = ca.get("filings") or []
    if filings:
        lines = ["\n## 10. 최근 1년 주요 공시"]
        for f in filings[:10]:
            lines.append(f"  {f.get('rcept_dt','')}: {f.get('report_name', f.get('report_type',''))}")
        research_sections.append("\n".join(lines))

    # 뉴스/경쟁사
    ip = research.get("industry_peers") or {}
    news = ip.get("news") or []
    if news:
        lines = ["\n## 11. 업황 뉴스"]
        for n in news[:8]:
            lines.append(f"  - [{n.get('source','')}] {n.get('title','')}")
        research_sections.append("\n".join(lines))
    sector = ip.get("sector", "")
    industry = ip.get("industry", "")
    if sector or industry:
        research_sections.append(f"\n  섹터: {sector}, 산업: {industry}")

    # ── 12번 섹션: 증권사 컨센서스 (REQ-ANALYST-08) ──
    consensus_block = _build_consensus_section(
        research.get("analyst_consensus"), market, regime,
    )
    if consensus_block:
        research_sections.append(consensus_block)

    if research_sections:
        prompt += "\n".join(research_sections)

    # ── v3 통합 JSON 스키마 ──
    prompt += """

위 데이터를 기반으로 다음 JSON 형식의 통합 투자 보고서를 작성하세요:
{{
  "schema_version": "v3",
  "종목등급": "A|B+|B|C|D",
  "등급점수": 0-28,
  "복합점수": 0-100,
  "체제정합성점수": 0-100,
  "종합투자의견": {{"등급":"매수|중립|매도", "요약":"2-3문장", "근거":["...", "..."]}},

  "재무건전성분석": {{"ocf_vs_net_income":"OCF vs 순이익 괴리 분석", "debt_ratio_analysis":"부채비율 분석", "interest_coverage_analysis":"이자보상배율 분석", "risk_level":"안전|주의|위험|심각", "summary":"종합 요약"}},
  "밸류에이션분석": {{"적정가치":숫자|null, "산출방법":"...", "per_band_position":"PER 밴드 내 위치", "pbr_band_position":"PBR 밴드 내 위치", "업종대비":"...", "PEG분석":"...", "밸류에이션판단":"저평가|적정|고평가 + 근거"}},
  "매크로및산업분석": {{"시장체제해석":"...", "금리영향":"...", "섹터전망":"...", "매크로리스크":"...", "peak_out_assessment":"Peak-out 검증", "industry_cycle_phase":"도입|성장|성숙|쇠퇴|불명"}},
  "경영진트랙레코드": {{"ma_track_record":"M&A 성패", "capital_allocation_grade":"우수|양호|보통|미흡", "dividend_policy":"배당 정책", "governance_assessment":"거버넌스 평가"}},
  "가치함정분석": {{"is_structural_decline":true|false, "decline_type":"구조적_쇠퇴|일시적_악재|판단불가", "evidence":["근거1","근거2"], "safety_margin_assessment":"안전마진 평가"}},
  "최종매매전략": {{"등급팩터":0-1, "추천진입가":정수|null, "진입가근거":"...", "손절가":정수|null, "손절근거":"...", "리스크보상비율":소수|null, "분할매수제안":"50-30-20%", "recommendation":"ENTER|HOLD|SKIP", "적정가치":정수|null, "적정가치산출":"...", "upside_pct":숫자|null, "downside_pct":숫자|null, "worst_scenario":"최악 시나리오", "action":"적극매수|분할매수|관망|분할매도|전량매도"}},
  "미래성장동력": {{"catalysts":["catalyst1","catalyst2","catalyst3"], "turning_points":["변곡점 신호1","변곡점 신호2"], "industry_tailwinds":"산업 순풍 (수요·정책·사이클)", "peak_out_signals":["피크아웃 신호 또는 빈 배열"], "growth_horizon":"단기(3개월)|중기(12개월)|장기(3년+)", "confidence":"높음|보통|낮음"}},
  "역발상관점": {{"contrarian_thesis":"역발상 핵심 논제 (시장이 놓친 것)", "market_misperception":"시장의 오해·과잉 반응 포인트", "edge":"차별화된 인사이트", "rebut_consensus":"증권사 컨센서스 반박 또는 동조 근거", "asymmetric_payoff":"비대칭 보상 구조(상방/하방 비율)"}},
  "성장주_보조판단": {{"growth_grade":"G-A|G-B|G-C", "growth_score":0-20, "growth_thesis":"성장 thesis (catalyst+사이클 정합)", "cycle_alignment":"주도섹터/부분일치/중립/반대사이클", "combined_factor":0-1, "combined_label":"가치우위|가치+성장혼합|가치C|성장우위(가치D)|진입금지"}},

  "전략별평가": {{"변동성돌파":{{"신호":"...", "목표가":숫자|null, "근거":"..."}}, "안전마진":{{"신호":"...", "graham_number":숫자|null, "할인율":숫자|null, "근거":"..."}}, "추세추종":{{"신호":"...", "추세강도":"강|중|약", "근거":"..."}}}},
  "기술적시그널": {{"신호":"...", "해석":"...", "지표별":{{"macd":"...", "rsi":"...", "stoch":"...", "volume":"...", "bb":"..."}}}},
  "시나리오분석": {{"낙관":{{"목표가":숫자, "확률":0-100, "근거":"..."}}, "기본":{{"목표가":숫자, "확률":0-100, "근거":"..."}}, "비관":{{"목표가":숫자, "확률":0-100, "근거":"..."}}}},
  "리스크요인": [{{"요인":"...", "설명":"..."}}],
  "투자포인트": [{{"포인트":"...", "설명":"..."}}],
  "관련투자대안": [{{"유형":"ETF|지수|원자재|채권|대체주", "종목명":"...", "코드":"...|null", "사유":"..."}}],
  "Value_Trap_경고": true|false,
  "Value_Trap_근거": ["근거1"]
}}"""

    return prompt



def _fmt(val, market: str) -> str:
    """금액 포맷팅."""
    if val is None:
        return "N/A"
    if market == "KR":
        # 원 → 억원
        v = val / 1e8
        if abs(v) >= 10000:
            return f"{v/10000:.1f}조"
        return f"{v:.0f}억"
    else:
        # USD(원시값 USD) → M USD
        v = val / 1e6
        if abs(v) >= 1000:
            return f"${v/1000:.1f}B"
        return f"${v:.0f}M"


def _parse_report(content: str) -> dict:
    """OpenAI 응답 JSON 파싱. 실패 시 원문 포함."""
    try:
        return json.loads(content)
    except Exception:
        return {"raw": content}

