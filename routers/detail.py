"""종목 상세 분석 API 라우터.

GET /api/detail/financials/{symbol}   — 10년 재무 데이터
GET /api/detail/valuation/{symbol}    — 월별 PER/PBR 히스토리
GET /api/detail/report/{symbol}       — 재무 + 밸류에이션 + 종합 요약

모든 핸들러는 sync def (pykrx/requests가 동기 라이브러리).
"""

from fastapi import APIRouter, Depends, Query

from services.auth_deps import get_current_user
from services.detail_service import DetailService

router = APIRouter(prefix="/api/detail", tags=["detail"])
_svc = DetailService()


@router.get("/financials/{symbol}")
def get_financials(
    symbol: str,
    years: int = Query(default=10, ge=1, le=20),
    _user: dict = Depends(get_current_user),
):
    """최대 years개 사업연도 재무 데이터."""
    return _svc.get_financials(symbol, years)


@router.get("/valuation/{symbol}")
def get_valuation(
    symbol: str,
    years: int = Query(default=10, ge=1, le=20),
    _user: dict = Depends(get_current_user),
):
    """월별 PER/PBR 히스토리 + 기간 평균."""
    return _svc.get_valuation_chart(symbol, years)


@router.get("/report/{symbol}")
def get_report(
    symbol: str,
    years: int = Query(default=10, ge=1, le=20),
    _user: dict = Depends(get_current_user),
):
    """재무 + 밸류에이션 + 종합 요약 통합."""
    return _svc.get_report(symbol, years)


@router.get("/{symbol}/bundle")
def get_bundle(
    symbol: str,
    market: str = Query(default="auto", pattern="^(auto|KR|US)$"),
    years: int = Query(default=10, ge=1, le=20),
    _user: dict = Depends(get_current_user),
):
    """DetailPage 마운트용 통합 응답 (병렬 수집 + 부분 실패 보존).

    2026-05-12: 프론트 N+1 호출(stock-detail + financials + valuation + ...) 패턴을 1회 호출로 축약.
    응답: {basic, financials, valuation, forward_estimates, summary, partial_failure}.
    부분 섹션 실패 시에도 200 + 해당 필드 null + partial_failure 리스트에 섹션명 기록.
    """
    return _svc.get_bundle(symbol, market=market, years=years)
