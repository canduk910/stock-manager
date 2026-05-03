"""PageView 모델 — Phase 4 단계 5.

FastAPI 미들웨어(`main.py`)에서 비동기 INSERT. 페이지별 이용현황 통계용.
경로별 호출 횟수 + latency + 일별 시계열 집계를 위한 raw 로그 테이블.
"""

from sqlalchemy import Column, Float, Index, Integer, String

from db.base import Base


class PageView(Base):
    __tablename__ = "page_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)  # 미인증 요청은 NULL
    path = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Float, nullable=False)
    created_at = Column(String, nullable=False)  # KST ISO

    __table_args__ = (
        Index("idx_page_views_path_created", "path", "created_at"),
        Index("idx_page_views_created", "created_at"),
    )
