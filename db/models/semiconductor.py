"""Semiconductor cycle indicators — Phase 1.

3 tables:
- IndicatorValue: 시계열 raw value (per indicator_name, per observed_at)
- Signal: 상태 변경 시 fired 신호 이력
- SemiconductorThreshold: 임계값 관리자 편집 (관리자 UI에서 수정)
"""

from sqlalchemy import BigInteger, Boolean, Column, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.dialects import sqlite

from db.base import Base

# SQLite에서는 BigInteger AUTOINCREMENT가 unsupported → Integer로 자동 down-spec.
# stock_info / page_view 패턴과 동일.
_BIGINT = BigInteger().with_variant(Integer(), "sqlite")


class IndicatorValue(Base):
    __tablename__ = "semi_indicator_values"

    id = Column(_BIGINT, primary_key=True, autoincrement=True)
    indicator_name = Column(String(64), nullable=False)
    observed_at = Column(String(10), nullable=False)  # YYYY-MM-DD (분기는 분기 마지막일)
    value = Column(JSON, nullable=True)  # 실수(JSON FLOAT) — SQLite Float 정밀도 회피
    value_meta = Column(JSON, nullable=False, default=dict)
    source = Column(String(128), nullable=False, default="")
    collected_at = Column(String(32), nullable=False)  # ISO KST

    __table_args__ = (
        UniqueConstraint("indicator_name", "observed_at", name="uq_semi_indicator_obs"),
        Index("idx_semi_indicator_obs_desc", "indicator_name", "observed_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "indicator_name": self.indicator_name,
            "observed_at": self.observed_at,
            "value": self.value,
            "value_meta": self.value_meta or {},
            "source": self.source,
            "collected_at": self.collected_at,
        }


class Signal(Base):
    __tablename__ = "semi_signals"

    id = Column(_BIGINT, primary_key=True, autoincrement=True)
    indicator_name = Column(String(64), nullable=False)  # composite 포함
    fired_at = Column(String(32), nullable=False)  # ISO KST
    level = Column(String(16), nullable=False)  # INFO/WARNING/ALERT/GREEN/YELLOW/RED
    message = Column(Text, nullable=False, default="")
    value_snapshot = Column(JSON, nullable=False, default=dict)  # 직전 4관측치 등
    ack = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_semi_signals_indicator_fired", "indicator_name", "fired_at"),
        Index("idx_semi_signals_fired", "fired_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "indicator_name": self.indicator_name,
            "fired_at": self.fired_at,
            "level": self.level,
            "message": self.message,
            "value_snapshot": self.value_snapshot or {},
            "ack": bool(self.ack),
        }


class SemiconductorThreshold(Base):
    __tablename__ = "semi_thresholds"

    id = Column(_BIGINT, primary_key=True, autoincrement=True)
    indicator_name = Column(String(64), nullable=False)
    threshold_key = Column(String(64), nullable=False)
    value = Column(JSON, nullable=False)
    comment = Column(Text, nullable=True)
    updated_at = Column(String(32), nullable=False)  # ISO KST
    updated_by = Column(Integer, nullable=True)  # users.id (관리자)

    __table_args__ = (
        UniqueConstraint("indicator_name", "threshold_key", name="uq_semi_threshold_key"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "indicator_name": self.indicator_name,
            "threshold_key": self.threshold_key,
            "value": self.value,
            "comment": self.comment,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }
