"""보고서 서비스 레이어.

추천 이력, 매크로 체제 이력, 일일 보고서 비즈니스 로직 + 통합 생성.
DB 접근은 stock/report_store.py 래퍼 경유 (다른 서비스와 동일 패턴).
"""
from __future__ import annotations

import logging
from typing import Optional

from services.exceptions import NotFoundError
from stock import report_store
from db.utils import now_kst_iso

logger = logging.getLogger(__name__)


# ── 추천 이력 ─────────────────────────────────────────────────

def save_recommendation(**kwargs) -> int:
    return report_store.save_recommendation(**kwargs)


def save_recommendations_batch(items: list[dict]) -> list[int]:
    return report_store.save_recommendations_batch(items)


def update_recommendation_status(rec_id: int, status: str, **kwargs) -> dict:
    ok = report_store.update_recommendation_status(rec_id, status, **kwargs)
    if not ok:
        raise NotFoundError(f"추천 이력 #{rec_id}을 찾을 수 없습니다.")
    return report_store.get_recommendation(rec_id)


def get_recommendation(rec_id: int) -> dict:
    rec = report_store.get_recommendation(rec_id)
    if not rec:
        raise NotFoundError(f"추천 이력 #{rec_id}을 찾을 수 없습니다.")
    return rec


def list_recommendations(
    market: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    items = report_store.list_recommendations(market=market, status=status, limit=limit, offset=offset)
    total = report_store.count_recommendations(market=market, status=status)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def get_performance_stats(market: Optional[str] = None) -> dict:
    return report_store.get_performance_stats(market=market)


# ── 매크로 체제 이력 ──────────────────────────────────────────

def save_regime(date: str, regime: str, **kwargs) -> int:
    return report_store.save_regime(date, regime, **kwargs)


def get_latest_regime() -> Optional[dict]:
    return report_store.get_latest_regime()


def list_regimes(limit: int = 90) -> list[dict]:
    return report_store.list_regimes(limit=limit)


# ── 일일 보고서 ───────────────────────────────────────────────

def save_daily_report(
    date: str,
    market: str,
    report_markdown: str,
    report_json: Optional[dict] = None,
    regime: Optional[str] = None,
    candidates_count: int = 0,
    recommended_count: int = 0,
) -> int:
    return report_store.save_daily_report(
        date=date,
        market=market,
        report_markdown=report_markdown,
        report_json=report_json,
        regime=regime,
        candidates_count=candidates_count,
        recommended_count=recommended_count,
    )


def get_daily_report(report_id: int) -> dict:
    report = report_store.get_daily_report(report_id)
    if not report:
        raise NotFoundError(f"보고서 #{report_id}을 찾을 수 없습니다.")
    return report


def get_daily_report_by_date(date: str, market: str) -> Optional[dict]:
    return report_store.get_daily_report_by_date(date, market)


def list_daily_reports(
    market: Optional[str] = None,
    limit: int = 30,
    offset: int = 0,
) -> dict:
    items = report_store.list_daily_reports(market=market, limit=limit, offset=offset)
    total = report_store.count_daily_reports(market=market)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def mark_telegram_sent(report_id: int) -> bool:
    ok = report_store.mark_telegram_sent(report_id)
    if not ok:
        raise NotFoundError(f"보고서 #{report_id}을 찾을 수 없습니다.")
    return True


# ── 통합 보고서 생성 ──────────────────────────────────────────

def generate_daily_report_markdown(
    regime_data: Optional[dict],
    recommendations: list[dict],
    market: str,
    date: str,
    sector_recommendations: Optional[dict] = None,
) -> str:
    """분석 결과를 통합 Markdown 보고서로 생성."""
    lines = []
    lines.append(f"# 일일 투자 보고서 ({date} / {market})")
    lines.append("")

    # 체제 요약
    if regime_data:
        regime = regime_data.get("regime", "unknown")
        vix = regime_data.get("vix")
        buffett = regime_data.get("buffett_ratio")
        fear = regime_data.get("fear_greed_score")
        lines.append(f"## 시장 체제: {regime}")
        parts = []
        if vix is not None:
            parts.append(f"VIX {vix:.1f}")
        if buffett is not None:
            parts.append(f"버핏지수 {buffett:.2f}")
        if fear is not None:
            parts.append(f"공포탐욕 {fear:.0f}")
        if parts:
            lines.append(f"지표: {' / '.join(parts)}")
        lines.append("")

    # 섹터 추천 (GPT)
    concepts = (sector_recommendations or {}).get("concepts", [])
    if concepts:
        lines.append("## 탑픽 섹터 추천")
        lines.append("")
        concept_labels = {"momentum": "모멘텀", "contrarian": "역발상", "forward_3m": "3개월 선점"}
        for concept in concepts:
            label = concept.get("concept_label") or concept_labels.get(concept.get("concept"), "")
            desc = concept.get("description", "")
            lines.append(f"### {label}: {desc}")
            for sector in concept.get("sectors", []):
                lines.append(f"**{sector.get('sector_name', '')}** — {sector.get('rationale', '')}")
                for stock in sector.get("stocks", []):
                    lines.append(f"- {stock.get('name', '')} ({stock.get('code', '')}) : {stock.get('reason', '')}")
            lines.append("")

    # 추천 종목
    if recommendations:
        lines.append(f"## 매수 추천 ({len(recommendations)}건)")
        lines.append("")
        for i, rec in enumerate(recommendations, 1):
            grade = rec.get("safety_grade", "?")
            discount = rec.get("discount_rate")
            discount_str = f"{discount:.0f}%" if discount else "N/A"
            lines.append(
                f"### {i}. {rec['name']} ({rec['code']}) — 등급 {grade}, 할인율 {discount_str}"
            )
            lines.append(
                f"- 진입가: {rec['entry_price']:,.0f} / "
                f"수량: {rec['recommended_qty']}주"
            )
            sl = rec.get("stop_loss")
            tp = rec.get("take_profit")
            rr = rec.get("risk_reward")
            if sl and tp:
                lines.append(
                    f"- 손절: {sl:,.0f} / 익절: {tp:,.0f}"
                    + (f" (R:R {rr:.1f})" if rr else "")
                )
            reasoning = rec.get("reasoning", "")
            if reasoning:
                lines.append(f"- 사유: {reasoning}")
            lines.append("")
    else:
        lines.append("## 매수 추천 없음")
        lines.append("현재 조건에 부합하는 종목이 없습니다.")
        lines.append("")

    lines.append("---")
    lines.append(f"*생성: {now_kst_iso()}*")
    return "\n".join(lines)
