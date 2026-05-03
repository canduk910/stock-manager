"""관리자 전용: 페이지별 이용현황 통계. Phase 4 단계 5."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query

from db.repositories.page_view_repo import PageViewRepository
from db.session import get_session
from db.utils import KST
from services.auth_deps import require_admin

router = APIRouter(prefix="/api/admin/page-stats", tags=["admin-stats"])


def _default_from_date() -> str:
    return (datetime.now(KST) - timedelta(days=7)).strftime("%Y-%m-%d")


def _default_to_date() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


@router.get("")
def get_page_stats(
    date_from: str = Query(default_factory=_default_from_date, alias="from"),
    date_to: str = Query(default_factory=_default_to_date, alias="to"),
    top: int = Query(20, ge=1, le=200),
    _admin: dict = Depends(require_admin),
):
    """경로별 호출 횟수 + 평균/p95 latency + 일별 시계열 + 유저 수.

    Args:
        from: YYYY-MM-DD
        to:   YYYY-MM-DD
        top:  상위 N path
    """
    with get_session() as db:
        repo = PageViewRepository(db)
        summary = repo.aggregate_by_path(date_from, date_to, top=top)
        timeseries = repo.daily_timeseries(date_from, date_to, top=top)

    return {
        "from": date_from,
        "to": date_to,
        "top": top,
        "summary": summary,
        "timeseries": timeseries,
    }
