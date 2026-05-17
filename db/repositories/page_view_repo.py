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

    def count_by_user(self, user_ids: list[int]) -> dict[int, int]:
        """사용자별 누적 방문 카운트 (PageView 전체 누계).

        N+1 회피: user_ids 목록을 한 번에 IN 쿼리로 집계.
        anonymous(user_id IS NULL) 행은 제외. 카운트 없는 사용자는 0.

        Returns: {user_id: count}
        """
        if not user_ids:
            return {}
        rows = (
            self.db.query(
                PageView.user_id.label("uid"),
                func.count(PageView.id).label("cnt"),
            )
            .filter(PageView.user_id.in_(user_ids))
            .filter(PageView.user_id.isnot(None))
            .group_by(PageView.user_id)
            .all()
        )
        counts = {int(r.uid): int(r.cnt or 0) for r in rows}
        # 누락 사용자는 0으로 채움
        return {uid: counts.get(uid, 0) for uid in user_ids}

    def user_daily_timeseries(
        self, user_id: int, date_from: str, date_to: str
    ) -> list[dict]:
        """사용자별 일별 PV + 고유 path 수 시계열.

        Args:
            user_id: 대상 사용자 ID (user_id IS NULL 행은 자동 제외).
            date_from: 'YYYY-MM-DD' (KST 일자, 포함).
            date_to:   'YYYY-MM-DD' (포함).

        Returns:
            [{date: 'YYYY-MM-DD', views: int, unique_paths: int}, ...] date asc.
            데이터 없는 날은 결과에 포함 안 됨(라우터에서 padding).
        """
        date_col = func.substr(PageView.created_at, 1, 10).label("date")
        rows = (
            self.db.query(
                date_col,
                func.count(PageView.id).label("views"),
                func.count(func.distinct(PageView.path)).label("unique_paths"),
            )
            .filter(PageView.user_id == user_id)
            .filter(PageView.user_id.isnot(None))
            .filter(PageView.created_at >= f"{date_from}T00:00:00")
            .filter(PageView.created_at <= f"{date_to}T23:59:59")
            .group_by(date_col)
            .order_by(date_col.asc())
            .all()
        )
        return [
            {
                "date": r.date,
                "views": int(r.views or 0),
                "unique_paths": int(r.unique_paths or 0),
            }
            for r in rows
        ]

    def user_top_paths(
        self, user_id: int, date_from: str, date_to: str, top: int = 5
    ) -> list[dict]:
        """사용자의 상위 N개 경로 (views desc).

        user_id IS NULL 행은 자동 제외.

        Returns: [{path: str, views: int}, ...] views desc, 최대 top개.
        """
        rows = (
            self.db.query(
                PageView.path.label("path"),
                func.count(PageView.id).label("views"),
            )
            .filter(PageView.user_id == user_id)
            .filter(PageView.user_id.isnot(None))
            .filter(PageView.created_at >= f"{date_from}T00:00:00")
            .filter(PageView.created_at <= f"{date_to}T23:59:59")
            .group_by(PageView.path)
            .order_by(func.count(PageView.id).desc())
            .limit(top)
            .all()
        )
        return [
            {"path": r.path, "views": int(r.views or 0)}
            for r in rows
        ]

    def user_last_seen_at(self, user_id: int) -> Optional[str]:
        """사용자의 마지막 PageView created_at (전체 누계 기준, days 무관).

        user_id IS NULL 행은 자동 제외. 기록 없는 사용자는 None.

        Returns: KST ISO 문자열 또는 None.
        """
        result = (
            self.db.query(func.max(PageView.created_at))
            .filter(PageView.user_id == user_id)
            .filter(PageView.user_id.isnot(None))
            .scalar()
        )
        return result if result else None

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
