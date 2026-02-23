"""공시(정기보고서) API 라우터."""

from fastapi import APIRouter, HTTPException, Query

from screener.dart import fetch_filings
from screener.service import ScreenerValidationError, normalize_date

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


@router.get("/filings")
def get_filings(
    date: str | None = Query(None, description="조회 날짜 (YYYYMMDD 또는 YYYY-MM-DD, 기본: 오늘)"),
):
    """특정 날짜의 정기보고서(사업/반기/분기) 제출 목록 조회."""
    try:
        target_date = normalize_date(date)
    except ScreenerValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        filings = fetch_filings(target_date)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "date": target_date,
        "total": len(filings),
        "filings": filings,
    }
