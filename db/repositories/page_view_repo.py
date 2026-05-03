"""PageViewRepository — 경로별 이용현황 집계.

raw 로그(record)는 FastAPI 미들웨어에서 비동기 INSERT.
대시보드 쿼리는 aggregate_by_path / daily_timeseries 사용.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from db.models.page_view import PageView
from db.utils import now_kst_iso


class PageViewRepository:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        user_id: Optional[int],
        path: str,
        method: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        row = PageView(
            user_id=user_id,
            path=path,
            method=method,
            status_code=status_code,
            duration_ms=float(duration_ms),
            created_at=now_kst_iso(),
        )
        self.db.add(row)
        self.db.flush()

    def aggregate_by_path(self, date_from: str, date_to: str, top: int = 20) -> list[dict]:
        """경로별 집계: 호출수 + 평균 latency + 유저 수.

        Args:
            date_from: YYYY-MM-DD (KST 포함)
            date_to: YYYY-MM-DD (포함)
            top: 상위 N path
        """
        # date_from 00:00 ~ date_to 23:59:59
        start = f"{date_from}T00:00:00"
        end = f"{date_to}T23:59:59"
        rows = (
            self.db.query(
                PageView.path.label("path"),
                func.count(PageView.id).label("calls"),
                func.avg(PageView.duration_ms).label("avg_ms"),
                func.max(PageView.duration_ms).label("max_ms"),
                func.count(func.distinct(PageView.user_id)).label("unique_users"),
            )
            .filter(PageView.created_at >= start, PageView.created_at <= end)
            .group_by(PageView.path)
            .order_by(func.count(PageView.id).desc())
            .limit(top)
            .all()
        )
        return [
            {
                "path": r.path,
                "calls": int(r.calls or 0),
                "avg_ms": round(float(r.avg_ms or 0), 1),
                "max_ms": round(float(r.max_ms or 0), 1),
                "unique_users": int(r.unique_users or 0),
            }
            for r in rows
        ]

    def daily_timeseries(self, date_from: str, date_to: str, top: int = 5) -> list[dict]:
        """일별 path별 호출 수 시계열 (상위 top path만)."""
        # 1) 상위 top path 추출
        top_paths_rows = (
            self.db.query(PageView.path, func.count(PageView.id).label("c"))
            .filter(PageView.created_at >= f"{date_from}T00:00:00")
            .filter(PageView.created_at <= f"{date_to}T23:59:59")
            .group_by(PageView.path)
            .order_by(func.count(PageView.id).desc())
            .limit(top)
            .all()
        )
        top_paths = [r.path for r in top_paths_rows]
        if not top_paths:
            return []

        # 2) 각 path × 날짜별 집계
        # created_at은 ISO 문자열 — 앞 10자리(YYYY-MM-DD)로 그룹.
        date_col = func.substr(PageView.created_at, 1, 10).label("date")
        rows = (
            self.db.query(
                date_col,
                PageView.path.label("path"),
                func.count(PageView.id).label("calls"),
            )
            .filter(PageView.path.in_(top_paths))
            .filter(PageView.created_at >= f"{date_from}T00:00:00")
            .filter(PageView.created_at <= f"{date_to}T23:59:59")
            .group_by(date_col, PageView.path)
            .order_by(date_col.asc())
            .all()
        )
        return [
            {"date": r.date, "path": r.path, "calls": int(r.calls or 0)}
            for r in rows
        ]
