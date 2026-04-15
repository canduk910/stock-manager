"""보고서 CRUD — db/repositories/report_repo.py 위임 래퍼.

다른 6개 store(store.py, order_store.py 등)와 동일한 패턴:
- get_session()으로 세션 자동 관리
- 기존 ReportRepository 메서드에 1:1 위임
"""

from typing import Optional

from db.repositories.report_repo import ReportRepository
from db.session import get_session


# ── RecommendationHistory ─────────────────────────────────────

def save_recommendation(**kwargs) -> int:
    with get_session() as db:
        return ReportRepository(db).save_recommendation(**kwargs)


def save_recommendations_batch(items: list[dict]) -> list[int]:
    with get_session() as db:
        return ReportRepository(db).save_recommendations_batch(items)


def update_recommendation_status(rec_id: int, status: str, **kwargs) -> bool:
    with get_session() as db:
        return ReportRepository(db).update_recommendation_status(rec_id, status, **kwargs)


def get_recommendation(rec_id: int) -> Optional[dict]:
    with get_session() as db:
        return ReportRepository(db).get_recommendation(rec_id)


def list_recommendations(
    market: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    with get_session() as db:
        return ReportRepository(db).list_recommendations(
            market=market, status=status, limit=limit, offset=offset
        )


def list_recommendations_by_date(date: str, market: Optional[str] = None) -> list[dict]:
    with get_session() as db:
        return ReportRepository(db).list_recommendations_by_date(date, market=market)


def count_recommendations(
    market: Optional[str] = None, status: Optional[str] = None
) -> int:
    with get_session() as db:
        return ReportRepository(db).count_recommendations(market=market, status=status)


def get_performance_stats(market: Optional[str] = None) -> dict:
    with get_session() as db:
        return ReportRepository(db).get_performance_stats(market=market)


# ── MacroRegimeHistory ────────────────────────────────────────

def save_regime(date: str, regime: str, **kwargs) -> int:
    with get_session() as db:
        return ReportRepository(db).save_regime(date, regime, **kwargs)


def get_regime(date: str) -> Optional[dict]:
    with get_session() as db:
        return ReportRepository(db).get_regime(date)


def get_latest_regime() -> Optional[dict]:
    with get_session() as db:
        return ReportRepository(db).get_latest_regime()


def list_regimes(limit: int = 90) -> list[dict]:
    with get_session() as db:
        return ReportRepository(db).list_regimes(limit=limit)


# ── DailyReport ───────────────────────────────────────────────

def save_daily_report(
    date: str,
    market: str,
    report_markdown: str,
    report_json: Optional[dict] = None,
    regime: Optional[str] = None,
    candidates_count: int = 0,
    recommended_count: int = 0,
) -> int:
    with get_session() as db:
        return ReportRepository(db).save_daily_report(
            date=date,
            market=market,
            report_markdown=report_markdown,
            report_json=report_json,
            regime=regime,
            candidates_count=candidates_count,
            recommended_count=recommended_count,
        )


def mark_telegram_sent(report_id: int) -> bool:
    with get_session() as db:
        return ReportRepository(db).mark_telegram_sent(report_id)


def get_daily_report(report_id: int) -> Optional[dict]:
    with get_session() as db:
        return ReportRepository(db).get_daily_report(report_id)


def get_daily_report_by_date(date: str, market: str) -> Optional[dict]:
    with get_session() as db:
        return ReportRepository(db).get_daily_report_by_date(date, market)


def list_daily_reports(
    market: Optional[str] = None,
    limit: int = 30,
    offset: int = 0,
) -> list[dict]:
    with get_session() as db:
        return ReportRepository(db).list_daily_reports(market=market, limit=limit, offset=offset)


def count_daily_reports(market: Optional[str] = None) -> int:
    with get_session() as db:
        return ReportRepository(db).count_daily_reports(market=market)
