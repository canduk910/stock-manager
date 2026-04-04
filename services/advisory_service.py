"""AI자문 서비스 레이어.

데이터 수집(advisory_fetcher) + 재무데이터(dart_fin/yf_client) + OpenAI 호출.
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

logger = logging.getLogger(__name__)


# ── 공개 API ──────────────────────────────────────────────────────────────────

def refresh_stock_data(code: str, market: str, name: str) -> dict:
    """전체 데이터 수집 → advisory_cache 저장 → 저장된 캐시 반환.

    국내(KR): dart_fin + market.fetch_market_metrics + 15분봉KIS
    해외(US): yf_client + 15분봉 yfinance
    """
    fundamental = _collect_fundamental(code, market, name)
    technical = _collect_technical(code, market)

    advisory_store.save_cache(code, market, fundamental, technical)
    return advisory_store.get_cache(code, market) or {}


def generate_ai_report(code: str, market: str, name: str) -> dict:
    """저장된 캐시 데이터를 기반으로 OpenAI GPT-4o 리포트 생성.

    OPENAI_API_KEY 미설정 시 HTTPException(503).
    캐시 없을 시 HTTPException(404).
    """
    if not OPENAI_API_KEY:
        raise ConfigError("OPENAI_API_KEY가 설정되지 않았습니다.")

    cache = advisory_store.get_cache(code, market)
    if not cache:
        raise NotFoundError("분석 데이터가 없습니다. 먼저 새로고침을 해주세요.")

    fundamental = cache.get("fundamental") or {}
    technical = cache.get("technical") or {}

    model = OPENAI_MODEL
    graham_data = _calc_graham_number(fundamental, market)

    # 매크로 컨텍스트 수집 (캐시 활용, 실패 시 빈 dict)
    macro_ctx = _get_macro_context()
    regime, regime_desc = _determine_regime(macro_ctx)

    prompt = _build_prompt(code, market, name, fundamental, technical, graham_data, macro_ctx, regime, regime_desc)
    system_prompt = _build_system_prompt(regime, regime_desc)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=8000,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"

        # 토큰 제한으로 응답 잘림 감지
        if resp.choices[0].finish_reason == "length":
            logger.warning("종목 자문 응답이 토큰 제한으로 잘렸습니다 (%s)", code)

        report = _parse_report(content)
    except (ConfigError, NotFoundError, PaymentRequiredError, ExternalAPIError):
        raise
    except Exception as e:
        err_str = str(e)
        if "insufficient_quota" in err_str or "429" in err_str:
            raise PaymentRequiredError(
                "OpenAI API 크레딧이 부족합니다. platform.openai.com에서 결제 정보를 확인해주세요.",
            )
        raise ExternalAPIError(f"OpenAI 호출 실패: {err_str}")

    report_id = advisory_store.save_report(code, market, model, report)
    return advisory_store.get_latest_report(code, market) or {}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _collect_fundamental(code: str, market: str, name: str) -> dict:
    """기본적 분석 데이터 수집."""
    if market == "KR":
        return _collect_fundamental_kr(code, name)
    return _collect_fundamental_us(code)


def _collect_fundamental_kr(code: str, name: str) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    from stock import dart_fin
    from stock.market import fetch_market_metrics
    from stock.yf_client import fetch_forward_estimates_yf

    # 5개 독립 데이터 소스 병렬 수집
    with ThreadPoolExecutor(max_workers=5) as pool:
        f_income = pool.submit(dart_fin.fetch_income_detail_annual, code, 5)
        f_bs_cf = pool.submit(dart_fin.fetch_bs_cf_annual, code, 5)
        f_metrics = pool.submit(fetch_market_metrics, code)
        f_segments = pool.submit(advisory_fetcher.fetch_segments_kr, code, name)
        f_forward = pool.submit(fetch_forward_estimates_yf, code, True)

        income_stmt = f_income.result()
        bs_cf = f_bs_cf.result()
        balance_sheet = bs_cf.get("balance_sheet", [])
        cashflow = bs_cf.get("cashflow", [])
        metrics_raw = f_metrics.result()
        metrics = _build_metrics_kr(metrics_raw, balance_sheet, income_stmt)
        segments_data = f_segments.result()
        forward_estimates = f_forward.result()

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
    }


def _collect_fundamental_us(code: str) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    from stock.yf_client import (
        fetch_income_detail_yf,
        fetch_balance_sheet_yf,
        fetch_cashflow_yf,
        fetch_metrics_yf,
        fetch_segments_yf,
        fetch_forward_estimates_yf,
    )

    # 6개 독립 데이터 소스 병렬 수집
    with ThreadPoolExecutor(max_workers=6) as pool:
        f_income = pool.submit(fetch_income_detail_yf, code, 5)
        f_bs = pool.submit(fetch_balance_sheet_yf, code, 5)
        f_cf = pool.submit(fetch_cashflow_yf, code, 5)
        f_metrics = pool.submit(fetch_metrics_yf, code)
        f_segments = pool.submit(fetch_segments_yf, code)
        f_forward = pool.submit(fetch_forward_estimates_yf, code, False)

        income_stmt = f_income.result()
        balance_sheet = f_bs.result()
        cashflow = f_cf.result()
        metrics = f_metrics.result()
        segments_data = f_segments.result()
        forward_estimates = f_forward.result()

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
    """sentiment → (regime, regime_desc) 반환."""
    fg = sentiment.get("fear_greed") or {}
    fg_val = fg.get("value") if fg.get("value") is not None else fg.get("score")
    if fg_val is None:
        return "selective", "중립 (적극적)"
    fg_val = float(fg_val)
    if fg_val <= 25:
        return "defensive", "공포 (방어적)"
    if fg_val <= 45:
        return "cautious", "신중 (선별적)"
    if fg_val <= 60:
        return "selective", "중립 (적극적)"
    return "accumulation", "탐욕 (축적)"


_REGIME_MARGIN = {
    "accumulation": 20, "selective": 25, "cautious": 30, "defensive": 40,
}


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


_REGIME_RULES = {
    "accumulation": (
        "시장 체제: accumulation (탐욕 — 축적 구간)\n"
        "안전마진 20% 이상이면 적극 매수 가능. 기술적 신호가 약해도 밸류에이션이 좋으면 진입 검토.\n"
        "현금 비중 25% 이상 유지."
    ),
    "selective": (
        "시장 체제: selective (중립 — 선별 매수)\n"
        "안전마진 25% 이상인 종목만 매수 권고. 기술적 추세와 펀더멘털이 모두 양호한 경우에만.\n"
        "현금 비중 35% 이상 유지."
    ),
    "cautious": (
        "시장 체제: cautious (신중 — 방어적 운용)\n"
        "안전마진 30% 이상인 종목만 조건부 매수. 추세 하락 신호는 하향 조정.\n"
        "하방 리스크를 강조하고 손절 기준을 명시할 것. 현금 비중 50% 이상 유지."
    ),
    "defensive": (
        "시장 체제: defensive (공포 — 방어 구간)\n"
        "【중요】 매수 등급을 부여하지 마세요. 최대 '관망'까지만 허용.\n"
        "매도 검토 우선, 현금 보존 최우선. 안전마진 40% 이상이면 관심 목록에만 추가.\n"
        "현금 비중 75% 이상 유지."
    ),
}


def _build_system_prompt(regime: str, regime_desc: str) -> str:
    """체제별 투자 원칙이 포함된 시스템 프롬프트."""
    regime_rule = _REGIME_RULES.get(regime, _REGIME_RULES["selective"])
    return (
        "당신은 전문 주식 애널리스트입니다. "
        "다음 세 가지 전략 프레임워크를 반드시 평가하여 종합 투자 의견을 JSON 형식으로 작성해주세요.\n\n"
        "【전략 1: 변동성 돌파 전략 (래리 윌리엄스)】\n"
        "당일 시가 + (전일 고저 범위 × K값) 돌파 시 매수 진입. K=0.5 표준. ATR 기반 변동성 수준 판단.\n\n"
        "【전략 2: 안전마진 전략 (벤자민 그레이엄)】\n"
        "Graham Number = sqrt(22.5 × EPS × BPS). "
        "할인율 >30%: 강한 매수, 10~30%: 매수, 0~10%: 중립, 음수: 고평가.\n"
        "- 적자 기업(EPS≤0): 3년 이상 연속 적자면 '구조적 적자'로 안전마진 전략 평가 불가. "
        "일시적 적자(과거 흑자 이력)면 '조건부 관망'까지만 허용.\n"
        "- BPS가 PBR 역산인 경우 '시장가 기반 참고치'임을 명시.\n\n"
        "【전략 3: 추세추종 전략】\n"
        "MA5>MA20>MA60 정배열 + MACD 방향 + RSI 모멘텀. "
        "정배열+골든크로스+RSI 55↑: 강한 추세. 역배열: 하락추세.\n\n"
        "【재무 건전성 체크리스트】\n"
        "부채비율 >200% 위험, 유동비율 <100% 위험, FCF 3년 연속 음수 위험. "
        "2개 이상 '위험'이면 안전마진 전략 매수 판정 금지 + '가치 함정 주의' 경고.\n\n"
        "【업종 상대평가】\n"
        "종목의 섹터/업종을 감안하여 동종 업종 평균 PER/PBR 대비 상대적 위치를 평가하세요 (참고용).\n\n"
        f"【현재 매크로 환경】\n{regime_rule}\n\n"
        "각 전략 신호를 독립적으로 평가하고, 전략 간 일치/불일치도 종합 의견에 반영하세요.\n"
        "매크로 체제가 defensive이면 어떤 경우에도 '매수' 등급을 부여하지 마세요."
    )


def _build_prompt(code: str, market: str, name: str, fundamental: dict, technical: dict,
                  graham_data: Optional[dict] = None,
                  macro_ctx: Optional[dict] = None,
                  regime: str = "selective",
                  regime_desc: str = "중립 (적극적)") -> str:
    """GPT 프롬프트 구성."""
    currency = "KRW(억원)" if market == "KR" else "USD(백만달러)"

    # 최근 3년 손익 요약
    income = fundamental.get("income_stmt") or []
    income_3y = income[-3:] if len(income) >= 3 else income
    income_summary = []
    for row in income_3y:
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

    # 최근 3년 대차대조표 요약
    bs = fundamental.get("balance_sheet") or []
    bs_3y = bs[-3:] if len(bs) >= 3 else bs
    bs_summary = []
    for row in bs_3y:
        ta = row.get("total_assets")
        te = row.get("total_equity")
        dr = row.get("debt_ratio")
        cr = row.get("current_ratio")
        bs_summary.append(
            f"  {row['year']}년: 자산={_fmt(ta, market)}, "
            f"자본={_fmt(te, market)}, 부채비율={dr}%, 유동비율={cr}%"
        )

    # 최근 3년 현금흐름 요약
    cf = fundamental.get("cashflow") or []
    cf_3y = cf[-3:] if len(cf) >= 3 else cf
    cf_summary = []
    for row in cf_3y:
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

    prompt = f"""다음은 {name}({code}, {market}) 종목의 분석 데이터입니다. 통화단위: {currency}

## 손익계산서 (최근 3년)
{chr(10).join(income_summary) or '데이터 없음'}

## 대차대조표 (최근 3년)
{chr(10).join(bs_summary) or '데이터 없음'}

## 현금흐름표 (최근 3년)
{chr(10).join(cf_summary) or '데이터 없음'}

## 계량지표
- PER: {per}배, PBR: {pbr}배, ROE: {roe}%, PSR: {psr}배, EV/EBITDA: {ev_ebitda}배

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

{_build_macro_section(macro_ctx, regime, regime_desc)}

위 데이터를 세 가지 전략 프레임워크(변동성 돌파/안전마진/추세추종)로 종합 분석하여 다음 JSON 형식으로 투자 의견을 작성해주세요:
{{
  "종합투자의견": {{
    "등급": "매수 또는 중립 또는 매도",
    "요약": "2-3문장 요약",
    "근거": ["근거1", "근거2", "근거3"]
  }},
  "전략별평가": {{
    "변동성돌파": {{
      "신호": "매수 또는 관망",
      "목표가": K=0.5 목표가 숫자 또는 null,
      "근거": "돌파 여부와 ATR 기반 변동성 수준 설명"
    }},
    "안전마진": {{
      "신호": "매수 또는 중립 또는 매도",
      "graham_number": Graham Number 숫자 또는 null,
      "할인율": 할인율 숫자(%) 또는 null,
      "근거": "Graham Number 해석 및 안전마진 수준 설명"
    }},
    "추세추종": {{
      "신호": "매수 또는 관망 또는 매도",
      "추세강도": "강 또는 중 또는 약",
      "근거": "MA 정배열/RSI/MACD 조합 해석"
    }}
  }},
  "기술적시그널": {{
    "신호": "매수 또는 관망 또는 매도",
    "해석": "기술적 분석 해석 2-3문장",
    "지표별": {{
      "macd": "해석",
      "rsi": "해석",
      "stoch": "해석"
    }}
  }},
  "포지션가이드": {{
    "추천진입가": 현재가 또는 기술적 지지선 기반 정수,
    "진입가근거": "진입가 산정 근거",
    "손절가": 진입가 대비 -10~-15% 정수,
    "손절근거": "손절가 산정 근거 (등급별 차등: 강한매수 -15%, 매수 -12%, 조건부 -10%)",
    "1차익절가": Graham Number 또는 목표가 정수,
    "익절근거": "익절가 산정 근거",
    "리스크보상비율": (익절가-진입가)/(진입가-손절가) 소수점1자리,
    "분할매수제안": "1차 50%(현재) - 2차 30%(지지선-3%) - 3차 20%(전저점)"
  }},
  "리스크요인": [
    {{"요인": "리스크명", "설명": "설명"}},
    ...
  ],
  "투자포인트": [
    {{"포인트": "포인트명", "설명": "설명"}},
    ...
  ]
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
