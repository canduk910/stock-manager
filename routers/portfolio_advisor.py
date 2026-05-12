"""AI 포트폴리오 자문 엔드포인트.

POST /api/portfolio-advisor/analyze — 잔고 데이터 기반 GPT 포트폴리오 분석.
POST /api/portfolio-advisor/chat    — 보고서 컨텍스트 챗봇.
GET  /api/portfolio-advisor/history  — 자문 이력 목록.
GET  /api/portfolio-advisor/history/{report_id} — 특정 자문 리포트 조회.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.auth_deps import require_admin
from services import portfolio_advisor_service
from services.exceptions import ServiceError

router = APIRouter(prefix="/api/portfolio-advisor", tags=["portfolio-advisor"])


class AnalyzeBody(BaseModel):
    balance_data: dict
    force_refresh: bool = False
    user_comment: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatBody(BaseModel):
    report_id: int
    messages: List[ChatMessage]


@router.post("/analyze")
def analyze(body: AnalyzeBody, _user: dict = Depends(require_admin)):
    """포트폴리오 AI 자문 분석. 캐시 히트 시 즉시 반환.

    user_comment(2026-05-07): 1000자 상한 검증 후 캐시 키 + 프롬프트에 전파.
    동일 잔고+다른 코멘트 = 새 보고서 (캐시 키 분리).
    """
    raw_comment = (body.user_comment or "").strip()
    if len(raw_comment) > 1000:
        raise ServiceError("사용자 코멘트는 1000자 이내여야 합니다.")
    user_comment = raw_comment or None

    return portfolio_advisor_service.analyze_portfolio(
        body.balance_data,
        body.force_refresh,
        user_id=_user.get("id"),
        user_comment=user_comment,
    )


@router.post("/chat")
def chat(body: ChatBody, _user: dict = Depends(require_admin)):
    """보고서 컨텍스트 stateless 챗봇. messages 배열은 클라이언트가 보관."""
    return portfolio_advisor_service.chat_with_report(
        body.report_id,
        [m.model_dump() for m in body.messages],
        user_id=_user.get("id"),
    )


@router.get("/history")
def get_history(limit: int = 20, _user: dict = Depends(require_admin)):
    """포트폴리오 자문 이력 목록 (본인 것만, 최신순, 본문 제외).

    2026-05-12: user_id 격리 — 멀티유저 환경에서 본인 보고서만 조회.
    """
    return portfolio_advisor_service.get_report_history(limit, user_id=_user.get("id"))


@router.get("/history/{report_id}")
def get_report(report_id: int, _user: dict = Depends(require_admin)):
    """특정 자문 리포트 상세 조회 (본인 것만).

    2026-05-12: user_id 격리 — 다른 사용자 리포트 접근은 404로 차단(존재 노출 회피).
    """
    return portfolio_advisor_service.get_report_by_id(report_id, user_id=_user.get("id"))
