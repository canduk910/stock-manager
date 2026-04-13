"""보고서 서비스 레이어.

추천 이력, 매크로 체제 이력, 일일 보고서 CRUD + 통합 생성.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from db.repositories.report_repo import ReportRepository
from services.exceptions import NotFoundError
from stock.db_base import now_kst_iso

logger = logging.getLogger(__name__)


# ── 추천 이력 ─────────────────────────────────────────────────

def save_recommendation(db: Session, **kwargs) -> int:
    repo = ReportRepository(db)
    return repo.save_recommendation(**kwargs)


def save_recommendations_batch(db: Session, items: list[dict]) -> list[int]:
    repo = ReportRepository(db)
    return repo.save_recommendations_batch(items)


def update_recommendation_status(
    db: Session, rec_id: int, status: str, **kwargs
) -> dict:
    repo = ReportRepository(db)
    ok = repo.update_recommendation_status(rec_id, status, **kwargs)
    if not ok:
        raise NotFoundError(f"추천 이력 #{rec_id}을 찾을 수 없습니다.")
    return repo.get_recommendation(rec_id)


def get_recommendation(db: Session, rec_id: int) -> dict:
    repo = ReportRepository(db)
    rec = repo.get_recommendation(rec_id)
    if not rec:
        raise NotFoundError(f"추천 이력 #{rec_id}을 찾을 수 없습니다.")
    return rec


def list_recommendations(
    db: Session,
    market: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    repo = ReportRepository(db)
    items = repo.list_recommendations(market=market, status=status, limit=limit, offset=offset)
    total = repo.count_recommendations(market=market, status=status)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def get_performance_stats(db: Session, market: Optional[str] = None) -> dict:
    repo = ReportRepository(db)
    return repo.get_performance_stats(market=market)


# ── 매크로 체제 이력 ──────────────────────────────────────────

def save_regime(db: Session, date: str, regime: str, **kwargs) -> int:
    repo = ReportRepository(db)
    return repo.save_regime(date, regime, **kwargs)


def get_latest_regime(db: Session) -> Optional[dict]:
    repo = ReportRepository(db)
    return repo.get_latest_regime()


def list_regimes(db: Session, limit: int = 90) -> list[dict]:
    repo = ReportRepository(db)
    return repo.list_regimes(limit=limit)


# ── 일일 보고서 ───────────────────────────────────────────────

def save_daily_report(
    db: Session,
    date: str,
    market: str,
    report_markdown: str,
    report_json: Optional[dict] = None,
    regime: Optional[str] = None,
    candidates_count: int = 0,
    recommended_count: int = 0,
) -> int:
    repo = ReportRepository(db)
    return repo.save_daily_report(
        date=date,
        market=market,
        report_markdown=report_markdown,
        report_json=report_json,
        regime=regime,
        candidates_count=candidates_count,
        recommended_count=recommended_count,
    )


def get_daily_report(db: Session, report_id: int) -> dict:
    repo = ReportRepository(db)
    report = repo.get_daily_report(report_id)
    if not report:
        raise NotFoundError(f"보고서 #{report_id}을 찾을 수 없습니다.")
    return report


def get_daily_report_by_date(db: Session, date: str, market: str) -> Optional[dict]:
    repo = ReportRepository(db)
    return repo.get_daily_report_by_date(date, market)


def list_daily_reports(
    db: Session,
    market: Optional[str] = None,
    limit: int = 30,
    offset: int = 0,
) -> dict:
    repo = ReportRepository(db)
    items = repo.list_daily_reports(market=market, limit=limit, offset=offset)
    total = repo.count_daily_reports(market=market)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def mark_telegram_sent(db: Session, report_id: int) -> bool:
    repo = ReportRepository(db)
    ok = repo.mark_telegram_sent(report_id)
    if not ok:
        raise NotFoundError(f"보고서 #{report_id}을 찾을 수 없습니다.")
    return True


# ── 통합 보고서 생성 ──────────────────────────────────────────

def generate_daily_report_markdown(
    regime_data: Optional[dict],
    recommendations: list[dict],
    market: str,
    date: str,
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
