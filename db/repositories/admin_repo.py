"""AdminRepository — AI 사용량, 한도, 감사 로그 CRUD."""

import json
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models.admin import AiUsageLog, AiLimit, AuditLog


class AdminRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── AI 사용량 ─────────────────────────────────────────────

    def get_daily_usage_count(self, user_id: int, date: str) -> int:
        """특정 유저의 특정 날짜 AI 호출 횟수."""
        return (
            self.db.query(func.count(AiUsageLog.id))
            .filter(AiUsageLog.user_id == user_id, AiUsageLog.date == date)
            .scalar()
        ) or 0

    def record_usage(self, user_id: int, date: str, service_name: str) -> None:
        """AI 호출 1건 기록."""
        from db.utils import now_kst_iso
        row = AiUsageLog(
            user_id=user_id,
            date=date,
            service_name=service_name,
            created_at=now_kst_iso(),
        )
        self.db.add(row)
        self.db.flush()

    def get_usage_summary(self, date: str) -> list[dict]:
        """특정 날짜의 유저별 사용량 집계."""
        rows = (
            self.db.query(
                AiUsageLog.user_id,
                func.count(AiUsageLog.id).label("count"),
            )
            .filter(AiUsageLog.date == date)
            .group_by(AiUsageLog.user_id)
            .all()
        )
        return [{"user_id": r.user_id, "count": r.count} for r in rows]

    def get_usage_detail(self, date: str, user_id: Optional[int] = None) -> list[dict]:
        """특정 날짜의 서비스별 사용량 상세."""
        q = (
            self.db.query(
                AiUsageLog.user_id,
                AiUsageLog.service_name,
                func.count(AiUsageLog.id).label("count"),
            )
            .filter(AiUsageLog.date == date)
        )
        if user_id is not None:
            q = q.filter(AiUsageLog.user_id == user_id)
        rows = q.group_by(AiUsageLog.user_id, AiUsageLog.service_name).all()
        return [{"user_id": r.user_id, "service_name": r.service_name, "count": r.count} for r in rows]

    def get_monthly_usage(self, year_month: str, user_id: Optional[int] = None) -> list[dict]:
        """월간 유저별 일별 사용량. year_month = 'YYYY-MM'."""
        q = (
            self.db.query(
                AiUsageLog.user_id,
                AiUsageLog.date,
                func.count(AiUsageLog.id).label("count"),
            )
            .filter(AiUsageLog.date.like(f"{year_month}%"))
        )
        if user_id is not None:
            q = q.filter(AiUsageLog.user_id == user_id)
        rows = q.group_by(AiUsageLog.user_id, AiUsageLog.date).order_by(AiUsageLog.date).all()
        return [{"user_id": r.user_id, "date": r.date, "count": r.count} for r in rows]

    # ── AI 한도 ───────────────────────────────────────────────

    def get_default_limit(self) -> Optional[dict]:
        """기본(전체) 일별 한도 조회. user_id=NULL인 행."""
        row = self.db.query(AiLimit).filter(AiLimit.user_id.is_(None)).first()
        return row.to_dict() if row else None

    def get_user_limit(self, user_id: int) -> Optional[dict]:
        """특정 유저의 개별 한도. 없으면 None (기본 한도 적용)."""
        row = self.db.query(AiLimit).filter(AiLimit.user_id == user_id).first()
        return row.to_dict() if row else None

    def get_effective_limit(self, user_id: int) -> int:
        """유저의 실효 한도 (개별 → 기본 → 하드코딩 50)."""
        user_limit = self.get_user_limit(user_id)
        if user_limit:
            return user_limit["daily_limit"]
        default = self.get_default_limit()
        return default["daily_limit"] if default else 50

    def set_limit(self, user_id: Optional[int], daily_limit: int, updated_by: int) -> dict:
        """한도 설정/업데이트. user_id=None이면 기본 한도."""
        from db.utils import now_kst_iso
        if user_id is None:
            row = self.db.query(AiLimit).filter(AiLimit.user_id.is_(None)).first()
        else:
            row = self.db.query(AiLimit).filter(AiLimit.user_id == user_id).first()

        if row:
            row.daily_limit = daily_limit
            row.updated_at = now_kst_iso()
            row.updated_by = updated_by
        else:
            row = AiLimit(
                user_id=user_id,
                daily_limit=daily_limit,
                updated_at=now_kst_iso(),
                updated_by=updated_by,
            )
            self.db.add(row)
        self.db.flush()
        return row.to_dict()

    def get_all_limits(self) -> list[dict]:
        """모든 한도 설정 조회 (기본 + 개별)."""
        rows = self.db.query(AiLimit).order_by(AiLimit.user_id).all()
        return [r.to_dict() for r in rows]

    def delete_user_limit(self, user_id: int) -> bool:
        """개별 한도 삭제 (기본 한도로 복귀). 기본 한도(user_id=NULL)는 삭제 불가."""
        count = self.db.query(AiLimit).filter(AiLimit.user_id == user_id).delete()
        return count > 0

    # ── 감사 로그 ─────────────────────────────────────────────

    def add_audit_log(
        self,
        actor_id: int,
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        old_value: object = None,
        new_value: object = None,
    ) -> dict:
        """감사 로그 1건 추가."""
        from db.utils import now_kst_iso
        row = AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            old_value=json.dumps(old_value, ensure_ascii=False) if old_value is not None else None,
            new_value=json.dumps(new_value, ensure_ascii=False) if new_value is not None else None,
            created_at=now_kst_iso(),
        )
        self.db.add(row)
        self.db.flush()
        return row.to_dict()

    def list_audit_logs(self, limit: int = 100, offset: int = 0) -> dict:
        """감사 로그 목록 (최신순)."""
        total = self.db.query(func.count(AuditLog.id)).scalar() or 0
        rows = (
            self.db.query(AuditLog)
            .order_by(AuditLog.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {"total": total, "items": [r.to_dict() for r in rows]}
