"""투자 파이프라인 서비스.

매크로 분석 → 스크리닝 → 심층 분석 → 7점 등급 → 추천 생성 → 보고서 저장.
기존 서비스 함수를 직접 호출하며 HTTP를 경유하지 않는다.
"""
from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Optional

from services import macro_service, report_service
from services.advisory_service import refresh_stock_data, _calc_graham_number
from services.exceptions import ExternalAPIError
from db.utils import now_kst_iso

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# ── 체제 판단 ─────────────────────────────────────────────────

REGIME_MATRIX = {
    ("low", "extreme_fear"): "accumulation",
    ("low", "fear"): "accumulation",
    ("low", "neutral"): "selective",
    ("low", "greed"): "cautious",
    ("low", "extreme_greed"): "cautious",
    ("normal", "extreme_fear"): "selective",
    ("normal", "fear"): "selective",
    ("normal", "neutral"): "cautious",
    ("normal", "greed"): "cautious",
    ("normal", "extreme_greed"): "defensive",
    ("high", "extreme_fear"): "selective",
    ("high", "fear"): "cautious",
    ("high", "neutral"): "cautious",
    ("high", "greed"): "defensive",
    ("high", "extreme_greed"): "defensive",
    ("extreme", "extreme_fear"): "cautious",
    ("extreme", "fear"): "defensive",
    ("extreme", "neutral"): "defensive",
    ("extreme", "greed"): "defensive",
    ("extreme", "extreme_greed"): "defensive",
}

REGIME_PARAMS = {
    "accumulation": {"per_max": 20, "pbr_max": 2.0, "roe_min": 5, "margin_threshold": 20, "max_position": 0.05, "max_invest": 0.75},
    "selective":    {"per_max": 15, "pbr_max": 1.5, "roe_min": 8, "margin_threshold": 30, "max_position": 0.04, "max_invest": 0.65},
    "cautious":     {"per_max": 12, "pbr_max": 1.2, "roe_min": 10, "margin_threshold": 40, "max_position": 0.03, "max_invest": 0.50},
    "defensive":    {"per_max": 0,  "pbr_max": 0,   "roe_min": 0,  "margin_threshold": 999, "max_position": 0, "max_invest": 0},
}


def _classify_buffett(ratio: Optional[float]) -> str:
    if ratio is None:
        return "normal"
    if ratio < 0.8:
        return "low"
    if ratio < 1.2:
        return "normal"
    if ratio < 1.6:
        return "high"
    return "extreme"


def _classify_fear_greed(score: Optional[float], vix: Optional[float] = None) -> str:
    # VIX > 35 오버라이드
    if vix is not None and vix > 35:
        return "extreme_fear"
    if score is None:
        return "neutral"
    if score < 20:
        return "extreme_fear"
    if score < 40:
        return "fear"
    if score < 60:
        return "neutral"
    if score < 80:
        return "greed"
    return "extreme_greed"


def _determine_regime(sentiment: dict) -> dict:
    """매크로 심리 데이터에서 시장 체제를 결정한다."""
    raw_vix = sentiment.get("vix")
    vix = raw_vix.get("value") if isinstance(raw_vix, dict) else raw_vix

    buffett_data = sentiment.get("buffett_indicator") or {}
    buffett_ratio = buffett_data.get("ratio") if isinstance(buffett_data, dict) else buffett_data
    # ratio가 백분율(235.2)이면 소수(2.352)로 변환
    if buffett_ratio is not None and buffett_ratio > 10:
        buffett_ratio = round(buffett_ratio / 100, 3)

    fear_greed = sentiment.get("fear_greed") or {}
    fg_score = fear_greed.get("score") if isinstance(fear_greed, dict) else fear_greed

    buffett_level = _classify_buffett(buffett_ratio)
    fg_level = _classify_fear_greed(fg_score, vix)

    regime = REGIME_MATRIX.get((buffett_level, fg_level), "cautious")
    params = REGIME_PARAMS[regime]

    return {
        "regime": regime,
        "params": params,
        "vix": vix,
        "buffett_ratio": buffett_ratio,
        "fear_greed_score": fg_score,
        "buffett_level": buffett_level,
        "fear_greed_level": fg_level,
    }


# ── 스크리닝 ──────────────────────────────────────────────────

def _screen_stocks(market: str, regime_data: dict) -> list[dict]:
    """체제별 필터로 종목 스크리닝."""
    regime = regime_data["regime"]
    if regime == "defensive":
        logger.info("Defensive 체제 — 스크리닝 중단, 현금 보존 권고")
        return []

    params = regime_data["params"]
    today = datetime.now(KST).strftime("%Y%m%d")

    try:
        from screener.krx import get_all_stocks
        from screener.service import apply_filters, sort_stocks

        stocks, actual_date = get_all_stocks(today)
        logger.info(f"전종목 수집: {len(stocks)}개 (거래일: {actual_date})")

        filtered = apply_filters(
            stocks,
            market=market if market != "ALL" else None,
            per_min=0,
            per_max=params["per_max"],
            pbr_max=params["pbr_max"],
            roe_min=params["roe_min"],
        )
        logger.info(f"필터 통과: {len(filtered)}개 (PER<{params['per_max']}, PBR<{params['pbr_max']}, ROE>{params['roe_min']})")

        # 복합 점수로 정렬
        for s in filtered:
            per = s.get("per") or 999
            pbr = s.get("pbr") or 999
            roe = s.get("roe") or 0
            div_yield = s.get("dividend_yield") or 0
            s["_score"] = (
                (1 / max(per, 0.1)) * 0.3
                + (1 / max(pbr, 0.1)) * 0.3
                + (roe / 100) * 0.25
                + (div_yield / 100) * 0.15
            )

        filtered.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return filtered[:20]  # 상위 20개 후보

    except Exception as e:
        logger.error(f"스크리닝 실패: {e}")
        return []


# ── 심층 분석 + 7점 등급 ──────────────────────────────────────

def _calc_safety_grade(
    graham_number: Optional[float],
    current_price: Optional[float],
    per: Optional[float],
    per_5yr_avg: Optional[float],
    pbr: Optional[float],
    debt_ratio: Optional[float],
    current_ratio: Optional[float],
    fcf_years_positive: int = 0,
    revenue_cagr: Optional[float] = None,
) -> dict:
    """7개 지표 기반 종합 등급 (28점 만점)."""
    details = {}
    score = 0

    # 1. Graham 할인율
    if graham_number and current_price and current_price > 0:
        discount = (graham_number - current_price) / current_price * 100
        pts = 4 if discount > 40 else 3 if discount > 20 else 2 if discount > 0 else 1
    else:
        discount = None
        pts = 1
    details["discount"] = {"value": discount, "points": pts}
    score += pts

    # 2. PER vs 5년 평균
    if per and per_5yr_avg and per_5yr_avg > 0:
        per_diff = (per - per_5yr_avg) / per_5yr_avg * 100
        pts = 4 if per_diff < -30 else 3 if per_diff < -10 else 2 if per_diff < 10 else 1
    else:
        pts = 2  # 데이터 없으면 중립
    details["per_vs_avg"] = {"value": per, "avg": per_5yr_avg, "points": pts}
    score += pts

    # 3. PBR 절대
    if pbr is not None:
        pts = 4 if pbr < 0.7 else 3 if pbr < 1.0 else 2 if pbr < 1.5 else 1
    else:
        pts = 2
    details["pbr"] = {"value": pbr, "points": pts}
    score += pts

    # 4. 부채비율
    if debt_ratio is not None:
        pts = 4 if debt_ratio < 50 else 3 if debt_ratio < 100 else 2 if debt_ratio < 200 else 1
    else:
        pts = 2
    details["debt_ratio"] = {"value": debt_ratio, "points": pts}
    score += pts

    # 5. 유동비율
    if current_ratio is not None:
        pts = 4 if current_ratio > 2.0 else 3 if current_ratio > 1.5 else 2 if current_ratio > 1.0 else 1
    else:
        pts = 2
    details["current_ratio"] = {"value": current_ratio, "points": pts}
    score += pts

    # 6. FCF 추세
    pts = 4 if fcf_years_positive >= 3 else 3 if fcf_years_positive >= 2 else 2 if fcf_years_positive >= 1 else 1
    details["fcf_trend"] = {"years_positive": fcf_years_positive, "points": pts}
    score += pts

    # 7. 매출 CAGR
    if revenue_cagr is not None:
        pts = 4 if revenue_cagr > 10 else 3 if revenue_cagr > 5 else 2 if revenue_cagr > 0 else 1
    else:
        pts = 2
    details["revenue_cagr"] = {"value": revenue_cagr, "points": pts}
    score += pts

    grade = "A" if score >= 24 else "B+" if score >= 20 else "B" if score >= 16 else "C" if score >= 12 else "D"
    return {"score": score, "grade": grade, "details": details}


def _extract_financial_metrics(fundamental: dict) -> dict:
    """fundamental 데이터에서 재무 지표를 추출한다."""
    metrics = fundamental.get("metrics") or {}
    bs = fundamental.get("balance_sheet") or []
    cf = fundamental.get("cashflow") or []
    income = fundamental.get("income_stmt") or []

    # 부채비율
    debt_ratio = None
    if bs:
        latest = bs[-1] if bs else {}
        total_debt = latest.get("total_debt") or latest.get("total_liabilities")
        total_equity = latest.get("total_equity") or latest.get("stockholders_equity")
        if total_debt and total_equity and total_equity > 0:
            debt_ratio = round(total_debt / total_equity * 100, 1)

    # 유동비율
    current_ratio = None
    if bs:
        latest = bs[-1] if bs else {}
        ca = latest.get("current_assets")
        cl = latest.get("current_liabilities")
        if ca and cl and cl > 0:
            current_ratio = round(ca / cl, 2)

    # FCF 양수 연수
    fcf_years = 0
    for entry in reversed(cf[-3:]) if len(cf) >= 3 else reversed(cf):
        op_cf = entry.get("operating_cashflow") or entry.get("op_cashflow") or 0
        capex = abs(entry.get("capex") or entry.get("capital_expenditure") or 0)
        if op_cf - capex > 0:
            fcf_years += 1
        else:
            break

    # 매출 CAGR (3년)
    revenue_cagr = None
    if len(income) >= 2:
        first_rev = income[0].get("revenue")
        last_rev = income[-1].get("revenue")
        years = len(income) - 1
        if first_rev and last_rev and first_rev > 0 and years > 0:
            try:
                revenue_cagr = round(((last_rev / first_rev) ** (1 / years) - 1) * 100, 1)
            except (ValueError, ZeroDivisionError):
                pass

    return {
        "per": metrics.get("per"),
        "pbr": metrics.get("pbr"),
        "roe": metrics.get("roe"),
        "debt_ratio": debt_ratio,
        "current_ratio": current_ratio,
        "fcf_years_positive": fcf_years,
        "revenue_cagr": revenue_cagr,
    }


def _analyze_single(code: str, name: str, market: str) -> Optional[dict]:
    """단일 종목 심층 분석."""
    try:
        cache = refresh_stock_data(code, market, name)
        fundamental = cache.get("fundamental") or {}
        graham = _calc_graham_number(fundamental, market)
        fin_metrics = _extract_financial_metrics(fundamental)

        # 현재가 추정
        current_price = None
        eps = graham.get("eps")
        per = fin_metrics.get("per")
        if eps and per and per > 0:
            current_price = round(eps * per, 0)

        grade_result = _calc_safety_grade(
            graham_number=graham.get("graham_number"),
            current_price=current_price,
            per=fin_metrics.get("per"),
            per_5yr_avg=None,  # 히스토리 데이터 미사용 (속도 우선)
            pbr=fin_metrics.get("pbr"),
            debt_ratio=fin_metrics.get("debt_ratio"),
            current_ratio=fin_metrics.get("current_ratio"),
            fcf_years_positive=fin_metrics.get("fcf_years_positive", 0),
            revenue_cagr=fin_metrics.get("revenue_cagr"),
        )

        return {
            "code": code,
            "name": name,
            "market": market,
            "current_price": current_price,
            "graham_number": graham.get("graham_number"),
            "discount_rate": graham.get("discount_rate"),
            "eps": graham.get("eps"),
            "bps": graham.get("bps"),
            "safety_grade": grade_result["grade"],
            "safety_score": grade_result["score"],
            "grade_details": grade_result["details"],
            "financial_metrics": fin_metrics,
        }
    except Exception as e:
        logger.error(f"분석 실패 [{code} {name}]: {e}")
        return None


def _analyze_candidates(candidates: list[dict], market: str) -> list[dict]:
    """상위 후보 종목 병렬 심층 분석."""
    analyses = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_analyze_single, s["code"], s["name"], market): s
            for s in candidates
        }
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                analyses.append(result)

    # 등급순 정렬 (A > B+ > B > C > D)
    grade_order = {"A": 0, "B+": 1, "B": 2, "C": 3, "D": 4}
    analyses.sort(key=lambda x: (grade_order.get(x["safety_grade"], 5), -(x.get("discount_rate") or -999)))
    return analyses


# ── 추천 생성 ─────────────────────────────────────────────────

def _generate_recommendations(analyses: list[dict], regime_data: dict) -> list[dict]:
    """분석 결과에서 매수 추천을 생성한다."""
    regime = regime_data["regime"]
    params = regime_data["params"]
    margin_threshold = params["margin_threshold"]

    recommendations = []
    for a in analyses:
        grade = a.get("safety_grade", "D")
        discount = a.get("discount_rate")

        # 등급 B+ 이상만 추천
        if grade not in ("A", "B+"):
            continue

        # 할인율이 체제 안전마진 임계값 이상이어야
        if discount is None or discount < margin_threshold:
            continue

        entry_price = a.get("current_price") or 0
        graham_number = a.get("graham_number") or 0

        # 손절/익절
        stop_pct = 0.08 if grade == "A" else 0.10
        stop_loss = round(entry_price * (1 - stop_pct)) if entry_price else None
        take_profit = graham_number if graham_number else None

        # R:R
        risk_reward = None
        if stop_loss and take_profit and entry_price and entry_price > stop_loss:
            risk_reward = round((take_profit - entry_price) / (entry_price - stop_loss), 1)

        # R:R < 2.0 이면 스킵
        if risk_reward is not None and risk_reward < 2.0:
            continue

        recommendations.append({
            "market": a["market"],
            "regime": regime,
            "code": a["code"],
            "name": a["name"],
            "graham_number": graham_number,
            "entry_price": entry_price,
            "safety_grade": grade,
            "discount_rate": round(discount, 1) if discount else None,
            "recommended_qty": 0,  # 포지션 사이징은 잔고 연동 후 계산
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward": risk_reward,
            "reasoning": f"Graham 할인율 {discount:.0f}%, 등급 {grade} (점수 {a.get('safety_score', 0)}/28)",
        })

    return recommendations[:5]  # 최대 5종목


# ── 메인 파이프라인 ───────────────────────────────────────────

def run_pipeline(market: str = "KR") -> dict:
    """전체 투자 파이프라인 실행.

    Returns:
        dict: report_id, regime, candidates_count, recommended_count, errors
    """
    errors = []
    today = datetime.now(KST).strftime("%Y-%m-%d")
    logger.info(f"=== 파이프라인 시작: {market} ({today}) ===")

    # Step 1: 매크로 체제 판단
    try:
        sentiment = macro_service.get_sentiment()
        regime_data = _determine_regime(sentiment)
        logger.info(f"체제 판단: {regime_data['regime']} (VIX={regime_data['vix']}, 버핏={regime_data['buffett_ratio']}, 공포탐욕={regime_data['fear_greed_score']})")
    except Exception as e:
        logger.error(f"매크로 분석 실패, cautious 기본값 사용: {e}")
        errors.append(f"매크로 분석 실패: {e}")
        regime_data = _determine_regime({})

    # 체제 이력 저장
    report_service.save_regime(
        today, regime_data["regime"],
        buffett_ratio=regime_data.get("buffett_ratio"),
        vix=regime_data.get("vix"),
        fear_greed_score=regime_data.get("fear_greed_score"),
    )

    # Step 2: 종목 스크리닝
    if regime_data["regime"] == "defensive":
        candidates = []
        logger.info("Defensive 체제 — 스크리닝 중단")
    else:
        candidates = _screen_stocks(market, regime_data)
        logger.info(f"스크리닝 결과: {len(candidates)}개 후보")

    # Step 3: 심층 분석 (상위 10개)
    analyses = []
    if candidates:
        top = candidates[:10]
        logger.info(f"심층 분석 시작: {len(top)}개 종목")
        analyses = _analyze_candidates(top, market)
        logger.info(f"분석 완료: {len(analyses)}개 (등급: {', '.join(a['safety_grade'] for a in analyses)})")

    # Step 4: 추천 생성
    recommendations = _generate_recommendations(analyses, regime_data) if analyses else []
    logger.info(f"매수 추천: {len(recommendations)}개")

    # Step 5: DB 저장
    if recommendations:
        report_service.save_recommendations_batch(recommendations)

    # 보고서 생성 + 저장
    md = report_service.generate_daily_report_markdown(
        regime_data=regime_data,
        recommendations=recommendations,
        market=market,
        date=today,
    )
    report_id = report_service.save_daily_report(
        date=today,
        market=market,
        report_markdown=md,
        report_json={
            "regime_data": {k: v for k, v in regime_data.items() if k != "params"},
            "candidates_count": len(candidates),
            "analyses_count": len(analyses),
            "recommendations": recommendations,
        },
        regime=regime_data["regime"],
        candidates_count=len(candidates),
        recommended_count=len(recommendations),
    )

    logger.info(f"=== 파이프라인 완료: 보고서 #{report_id} ===")
    return {
        "report_id": report_id,
        "date": today,
        "market": market,
        "regime": regime_data["regime"],
        "candidates_count": len(candidates),
        "analyses_count": len(analyses),
        "recommended_count": len(recommendations),
        "errors": errors,
    }
