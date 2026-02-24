"""종목 상세 분석 API 라우터.

GET /api/detail/financials/{symbol}   — 10년 재무 데이터
GET /api/detail/valuation/{symbol}    — 월별 PER/PBR 히스토리
GET /api/detail/report/{symbol}       — 재무 + 밸류에이션 + 종합 요약

모든 핸들러는 sync def (pykrx/requests가 동기 라이브러리).
"""

from fastapi import APIRouter, HTTPException, Query

from services.detail_service import DetailService

router = APIRouter(prefix="/api/detail", tags=["detail"])
_svc = DetailService()


@router.get("/financials/{symbol}")
def get_financials(
    symbol: str,
    years: int = Query(default=10, ge=1, le=20),
):
    """최대 years개 사업연도 재무 데이터."""
    try:
        return _svc.get_financials(symbol, years)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/valuation/{symbol}")
def get_valuation(
    symbol: str,
    years: int = Query(default=10, ge=1, le=20),
):
    """월별 PER/PBR 히스토리 + 기간 평균."""
    try:
        return _svc.get_valuation_chart(symbol, years)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{symbol}")
def get_report(
    symbol: str,
    years: int = Query(default=10, ge=1, le=20),
):
    """재무 + 밸류에이션 + 종합 요약 통합."""
    try:
        return _svc.get_report(symbol, years)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
