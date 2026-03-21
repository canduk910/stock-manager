"""AI자문 서비스 레이어.

데이터 수집(advisory_fetcher) + 재무데이터(dart_fin/yf_client) + OpenAI 호출.
"""

from __future__ import annotations

import json
from typing import Optional

from config import OPENAI_API_KEY, OPENAI_MODEL

from stock import advisory_store, advisory_fetcher
from stock.utils import is_domestic
from services.exceptions import (
    ConfigError, ExternalAPIError, NotFoundError, PaymentRequiredError,
)


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
    prompt = _build_prompt(code, market, name, fundamental, technical)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 전문 주식 애널리스트입니다. "
                        "제공된 재무 데이터와 기술적 분석 결과를 바탕으로 "
                        "종합 투자 의견을 JSON 형식으로 작성해주세요."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=1500,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
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
    from stock import dart_fin
    from stock.market import fetch_market_metrics

    # 손익계산서 세부
    income_stmt = dart_fin.fetch_income_detail_annual(code, years=5)

    # 대차대조표 + 현금흐름표
    bs_cf = dart_fin.fetch_bs_cf_annual(code, years=5)
    balance_sheet = bs_cf.get("balance_sheet", [])
    cashflow = bs_cf.get("cashflow", [])

    # 계량지표 (시가총액, PER, PBR, ROE) — balance_sheet/income_stmt도 전달해 추가 지표 계산
    metrics_raw = fetch_market_metrics(code)
    metrics = _build_metrics_kr(metrics_raw, balance_sheet, income_stmt)

    # 사업별 매출비중 (OpenAI 추론)
    segments = advisory_fetcher.fetch_segments_kr(code, name)

    return {
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "metrics": metrics,
        "segments": segments,
    }


def _collect_fundamental_us(code: str) -> dict:
    from stock.yf_client import (
        fetch_income_detail_yf,
        fetch_balance_sheet_yf,
        fetch_cashflow_yf,
        fetch_metrics_yf,
        fetch_segments_yf,
    )

    income_stmt = fetch_income_detail_yf(code, years=5)
    balance_sheet = fetch_balance_sheet_yf(code, years=5)
    cashflow = fetch_cashflow_yf(code, years=5)
    metrics = fetch_metrics_yf(code)
    segments = fetch_segments_yf(code)

    return {
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "metrics": metrics,
        "segments": segments,
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


def _build_prompt(code: str, market: str, name: str, fundamental: dict, technical: dict) -> str:
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
    vol_target = indicators.get("volatility_target")

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
- MACD: {macd_cross} ({{'golden': '골든크로스(매수신호)', 'dead': '데드크로스(매도신호)', 'none': '크로스 없음'}}.get(macd_cross, macd_cross))
- RSI: {rsi_val}({rsi_signal})
- 스토캐스틱 %K: {stoch_k}({stoch_signal})
- MA20 상회: {above_ma20}
- 변동성 돌파 목표가: {vol_target}

위 데이터를 종합 분석하여 다음 JSON 형식으로 투자 의견을 작성해주세요:
{{
  "종합투자의견": {{
    "등급": "매수 또는 중립 또는 매도",
    "요약": "2-3문장 요약",
    "근거": ["근거1", "근거2", "근거3"]
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
