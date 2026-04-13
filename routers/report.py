"""일일 보고서 + 추천 이력 API 라우터."""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from services import report_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ── 일일 보고서 ───────────────────────────────────────────────

@router.get("")
def list_reports(
    market: Optional[str] = None,
    limit: int = 30,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """일일 보고서 목록 (최신순)."""
    return report_service.list_daily_reports(db, market=market, limit=limit, offset=offset)


# ── 추천 이력 (/{report_id}보다 먼저 등록) ────────────────────

@router.get("/recommendations")
def list_recommendations(
    market: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """추천 이력 목록."""
    return report_service.list_recommendations(
        db, market=market, status=status, limit=limit, offset=offset
    )


@router.get("/recommendations/{rec_id}")
def get_recommendation(rec_id: int, db: Session = Depends(get_db)):
    """추천 이력 상세."""
    return report_service.get_recommendation(db, rec_id)


# ── 성과 통계 ─────────────────────────────────────────────────

@router.get("/performance")
def get_performance(market: Optional[str] = None, db: Session = Depends(get_db)):
    """추천 적중률 + 수익률 통계."""
    return report_service.get_performance_stats(db, market=market)


# ── 매크로 체제 이력 ──────────────────────────────────────────

@router.get("/regimes")
def list_regimes(limit: int = 90, db: Session = Depends(get_db)):
    """매크로 체제 이력 (최근 90일)."""
    return report_service.list_regimes(db, limit=limit)


@router.get("/regimes/latest")
def get_latest_regime(db: Session = Depends(get_db)):
    """최신 매크로 체제."""
    regime = report_service.get_latest_regime(db)
    return regime or {"regime": "unknown", "date": None}


# ── 보고서 상세 (path param — 마지막에 등록) ──────────────────

@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    """일일 보고서 상세."""
    return report_service.get_daily_report(db, report_id)
