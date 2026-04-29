"""Admin 모델 — AI 사용량 추적, 호출 한도 설정, 감사 로그."""

from sqlalchemy import Column, Integer, String, Text

from db.base import Base


class AiUsageLog(Base):
    """AI API 호출 사용량 일별 기록."""
    __tablename__ = "ai_usage_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(String, nullable=False, index=True)       # YYYY-MM-DD (KST)
    service_name = Column(String, nullable=False)            # advisory, portfolio, macro 등
    created_at = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": self.date,
            "service_name": self.service_name,
            "created_at": self.created_at,
        }


class AiLimit(Base):
    """AI API 일별 호출 한도 설정. user_id=None이면 기본(전체) 한도."""
    __tablename__ = "ai_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, unique=True, index=True)  # NULL = 기본 한도
    daily_limit = Column(Integer, nullable=False, default=50)
    updated_at = Column(String, nullable=False)
    updated_by = Column(Integer, nullable=True)  # 설정 변경한 admin user_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "daily_limit": self.daily_limit,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }


class AuditLog(Base):
    """감사 로그 — 관리자 작업 이력 추적."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(Integer, nullable=False, index=True)   # 작업 수행자 user_id
    action = Column(String, nullable=False)                  # 작업 유형 (예: set_limit, reset_usage)
    target_type = Column(String, nullable=False)             # 대상 유형 (예: ai_limit, ai_usage)
    target_id = Column(String, nullable=True)                # 대상 식별자 (예: user_id)
    old_value = Column(Text, nullable=True)                  # 변경 전 값 (JSON)
    new_value = Column(Text, nullable=True)                  # 변경 후 값 (JSON)
    created_at = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "created_at": self.created_at,
        }
