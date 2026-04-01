"""매크로 분석 API 라우터."""

from fastapi import APIRouter

from services import macro_service

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("/indices")
def get_indices():
    """주요 지수 현재가 + 3개월 스파크라인."""
    return macro_service.get_indices()


@router.get("/news")
def get_news():
    """한국 + 국제 뉴스 (NYT 한글 번역 포함)."""
    return macro_service.get_news()


@router.get("/sentiment")
def get_sentiment():
    """시장심리 지표 (VIX + 버핏지수 + 공포탐욕)."""
    return macro_service.get_sentiment()


@router.get("/investor-quotes")
def get_investor_quotes():
    """투자 대가 최근 코멘트."""
    return macro_service.get_investor_quotes()


@router.get("/summary")
def get_summary():
    """전체 매크로 분석 통합 (섹션별 독립 — 부분 실패 허용)."""
    return macro_service.get_summary()
