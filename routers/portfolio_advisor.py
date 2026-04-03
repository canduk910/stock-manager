"""AI 포트폴리오 자문 엔드포인트.

POST /api/portfolio-advisor/analyze — 잔고 데이터 기반 GPT 포트폴리오 분석.
GET  /api/portfolio-advisor/history  — 자문 이력 목록.
GET  /api/portfolio-advisor/history/{report_id} — 특정 자문 리포트 조회.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from services import portfolio_advisor_service

router = APIRouter(prefix="/api/portfolio-advisor", tags=["portfolio-advisor"])


class AnalyzeBody(BaseModel):
    balance_data: dict
    force_refresh: bool = False


@router.post("/analyze")
def analyze(body: AnalyzeBody):
    """포트폴리오 AI 자문 분석. 캐시 히트 시 즉시 반환."""
    return portfolio_advisor_service.analyze_portfolio(
        body.balance_data, body.force_refresh
    )


@router.get("/history")
def get_history(limit: int = 20):
    """포트폴리오 자문 이력 목록 (최신순, 본문 제외)."""
    return portfolio_advisor_service.get_report_history(limit)


@router.get("/history/{report_id}")
def get_report(report_id: int):
    """특정 자문 리포트 상세 조회."""
    return portfolio_advisor_service.get_report_by_id(report_id)
