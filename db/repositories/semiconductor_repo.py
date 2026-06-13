"""SemiconductorRepository — CRUD for IndicatorValue / Signal / SemiconductorThreshold.

호출자: services/semiconductor_service.py, services/semiconductor_signals.py.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from db.models.semiconductor import IndicatorValue, Signal, SemiconductorThreshold
from db.utils import now_kst_iso


class SemiconductorRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── IndicatorValue ─────────────────────────────────────────

    def upsert_indicator_value(
        self,
        *,
        indicator_name: str,
        observed_at: str,
        value: Optional[float],
        value_meta: Optional[dict] = None,
        source: str = "",
    ) -> int:
        """`(indicator_name, observed_at)` 기준 upsert. PK id 반환."""
        row = (
            self.db.query(IndicatorValue)
            .filter_by(indicator_name=indicator_name, observed_at=observed_at)
            .first()
        )
        if row is None:
            row = IndicatorValue(
                indicator_name=indicator_name,
                observed_at=observed_at,
                value=value,
                value_meta=value_meta or {},
                source=source,
                collected_at=now_kst_iso(),
            )
            self.db.add(row)
            self.db.flush()
            return row.id
        row.value = value
        row.value_meta = value_meta or {}
        row.source = source
        row.collected_at = now_kst_iso()
        self.db.flush()
        return row.id

    def get_latest_value(self, indicator_name: str) -> Optional[dict]:
        row = (
            self.db.query(IndicatorValue)
            .filter_by(indicator_name=indicator_name)
            .order_by(IndicatorValue.observed_at.desc())
            .first()
        )
        return row.to_dict() if row else None

    def list_values(
        self,
        indicator_name: str,
        *,
        limit: int = 180,
        order: str = "asc",
    ) -> list[dict]:
        q = self.db.query(IndicatorValue).filter_by(indicator_name=indicator_name)
        if order == "desc":
            q = q.order_by(IndicatorValue.observed_at.desc())
        else:
            q = q.order_by(IndicatorValue.observed_at.asc())
        rows = q.limit(limit).all()
        return [r.to_dict() for r in rows]

    def list_recent_n(self, indicator_name: str, n: int = 4) -> list[dict]:
        """ASC 순서로 최근 N건 (시간순)."""
        rows = (
            self.db.query(IndicatorValue)
            .filter_by(indicator_name=indicator_name)
            .order_by(IndicatorValue.observed_at.desc())
            .limit(n)
            .all()
        )
        return [r.to_dict() for r in reversed(rows)]

    # ── Signal ────────────────────────────────────────────────

    def insert_signal(
        self,
        *,
        indicator_name: str,
        level: str,
        message: str,
        value_snapshot: Optional[dict] = None,
    ) -> int:
        row = Signal(
            indicator_name=indicator_name,
            fired_at=now_kst_iso(),
            level=level,
            message=message,
            value_snapshot=value_snapshot or {},
            ack=False,
        )
        self.db.add(row)
        self.db.flush()
        return row.id

    def get_last_signal(self, indicator_name: str) -> Optional[dict]:
        row = (
            self.db.query(Signal)
            .filter_by(indicator_name=indicator_name)
            .order_by(Signal.fired_at.desc())
            .first()
        )
        return row.to_dict() if row else None

    def list_signals(
        self,
        *,
        indicator_name: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        q = self.db.query(Signal)
        if indicator_name:
            q = q.filter(Signal.indicator_name == indicator_name)
        if since:
            q = q.filter(Signal.fired_at > since)
        if until:
            q = q.filter(Signal.fired_at <= until)
        rows = q.order_by(Signal.fired_at.desc()).limit(limit).all()
        return [r.to_dict() for r in rows]

    def ack_signal(self, signal_id: int, user_id: Optional[int] = None) -> bool:
        row = self.db.query(Signal).filter_by(id=signal_id).first()
        if not row:
            return False
        row.ack = True
        self.db.flush()
        return True

    # ── Threshold ─────────────────────────────────────────────

    def get_threshold(self, indicator_name: str, threshold_key: str) -> Optional[dict]:
        row = (
            self.db.query(SemiconductorThreshold)
            .filter_by(indicator_name=indicator_name, threshold_key=threshold_key)
            .first()
        )
        return row.to_dict() if row else None

    def get_threshold_value(
        self,
        indicator_name: str,
        threshold_key: str,
        default=None,
    ):
        row = self.get_threshold(indicator_name, threshold_key)
        if row is None:
            return default
        return row["value"]

    def list_thresholds(self, indicator_name: Optional[str] = None) -> list[dict]:
        q = self.db.query(SemiconductorThreshold)
        if indicator_name:
            q = q.filter(SemiconductorThreshold.indicator_name == indicator_name)
        rows = q.order_by(
            SemiconductorThreshold.indicator_name.asc(),
            SemiconductorThreshold.threshold_key.asc(),
        ).all()
        return [r.to_dict() for r in rows]

    def upsert_threshold(
        self,
        *,
        indicator_name: str,
        threshold_key: str,
        value,
        comment: Optional[str] = None,
        updated_by: Optional[int] = None,
    ) -> int:
        row = (
            self.db.query(SemiconductorThreshold)
            .filter_by(indicator_name=indicator_name, threshold_key=threshold_key)
            .first()
        )
        if row is None:
            row = SemiconductorThreshold(
                indicator_name=indicator_name,
                threshold_key=threshold_key,
                value=value,
                comment=comment,
                updated_at=now_kst_iso(),
                updated_by=updated_by,
            )
            self.db.add(row)
            self.db.flush()
            return row.id
        row.value = value
        if comment is not None:
            row.comment = comment
        row.updated_at = now_kst_iso()
        if updated_by is not None:
            row.updated_by = updated_by
        self.db.flush()
        return row.id

    def thresholds_as_map(self, indicator_name: str) -> dict:
        """`indicator_name`의 모든 threshold_key → value 평탄 dict."""
        rows = (
            self.db.query(SemiconductorThreshold)
            .filter_by(indicator_name=indicator_name)
            .all()
        )
        return {r.threshold_key: r.value for r in rows}
