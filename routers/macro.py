"""매크로 분석 API 라우터."""

from typing import Literal

from fastapi import APIRouter, Depends, Query

from services.auth_deps import get_current_user
from services import macro_service, supply_demand_service

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("/indices")
def get_indices(_user: dict = Depends(get_current_user)):
    """주요 지수 현재가 + 3개월 스파크라인."""
    return macro_service.get_indices()


@router.get("/news")
def get_news(_user: dict = Depends(get_current_user)):
    """한국 + 국제 뉴스 (NYT 한글 번역 포함)."""
    return macro_service.get_news(user_id=_user.get("id"))


@router.get("/sentiment")
def get_sentiment(_user: dict = Depends(get_current_user)):
    """시장심리 지표 (VIX + 버핏지수 + 공포탐욕)."""
    return macro_service.get_sentiment()


@router.get("/investor-quotes")
def get_investor_quotes(_user: dict = Depends(get_current_user)):
    """투자 대가 최근 코멘트."""
    return macro_service.get_investor_quotes(user_id=_user.get("id"))


@router.get("/yield-curve")
def get_yield_curve(_user: dict = Depends(get_current_user)):
    """미국 국채 수익률곡선 (현재값 + 시계열 + 역전 여부)."""
    return macro_service.get_yield_curve()


@router.get("/credit-spread")
def get_credit_spread(_user: dict = Depends(get_current_user)):
    """FRED HY OAS + IG OAS 기반 하이일드 신용스프레드 (하워드 막스 시계추)."""
    return macro_service.get_credit_spread()


@router.get("/currencies")
def get_currencies(_user: dict = Depends(get_current_user)):
    """주요 환율 현재가 + 스파크라인."""
    return macro_service.get_currencies()


@router.get("/commodities")
def get_commodities(_user: dict = Depends(get_current_user)):
    """주요 원자재 현재가 + 스파크라인."""
    return macro_service.get_commodities()


@router.get("/sector-heatmap")
def get_sector_heatmap(_user: dict = Depends(get_current_user)):
    """11개 섹터 ETF 기간별 수익률 히트맵."""
    return macro_service.get_sector_heatmap()


@router.get("/macro-cycle")
def get_macro_cycle(_user: dict = Depends(get_current_user)):
    """경기 사이클 국면 판단 (5지표 가중합산 → 4국면)."""
    return macro_service.get_macro_cycle()


@router.get("/summary")
def get_summary(_user: dict = Depends(get_current_user)):
    """전체 매크로 분석 통합 (섹션별 독립 — 부분 실패 허용)."""
    return macro_service.get_summary()


@router.get("/supply-demand")
def get_supply_demand(
    market: Literal["kospi", "kosdaq"] = Query(..., description="kospi 또는 kosdaq"),
    days: int = Query(20, description="조회 일수 (10~60)"),
    _user: dict = Depends(get_current_user),
):
    """매크로 페이지용 시장(KOSPI/KOSDAQ) 일별 수급 + 누적 추세.

    REQ-SUPPLY-ROUTER-01. 단위는 억원 (서비스 레이어에서 KIS 백만원 ÷ 100).
    market 잘못된 값 → 422 (FastAPI Literal). days 범위 외 → 400 (ServiceError).
    KIS 키 미설정 시 ConfigError(503) → 다른 매크로 섹션은 정상.
    """
    return supply_demand_service.fetch_market_supply_demand(market, days=days)
