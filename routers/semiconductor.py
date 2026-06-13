"""반도체 사이클 모니터링 API.

prefix `/api/semiconductor`. 전부 `get_current_user` 의존.
관리자 전용(threshold PUT, signal ack, admin refresh) → `require_admin`.

8 라우트 (Phase 1 사용자 확정):
  GET  /dashboard
  GET  /indicators/{name}/history
  GET  /signals/recent
  GET  /signals
  POST /signals/{id}/ack
  GET  /thresholds
  PUT  /thresholds/{indicator_name}/{threshold_key}
  POST /admin/refresh
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field

from services import semiconductor_service as svc
from services.auth_deps import get_current_user, require_admin

router = APIRouter(prefix="/api/semiconductor", tags=["semiconductor"])


class ThresholdBody(BaseModel):
    value: object = Field(..., description="JSON-serializable threshold value")
    comment: Optional[str] = Field(None, description="관리자 코멘트")


@router.get("/dashboard")
def get_dashboard(_user: dict = Depends(get_current_user)):
    """카드 섹션 + 모달 마운트용 통합 응답."""
    return svc.get_dashboard()


@router.get("/indicators/{indicator_name}/history")
def get_history(
    indicator_name: str,
    days: int = Query(180, ge=7, le=730),
    _user: dict = Depends(get_current_user),
):
    """단일 지표 시계열."""
    return svc.get_indicator_history(indicator_name, days=days)


@router.get("/signals/recent")
def get_signals_recent(
    since: Optional[str] = Query(None, description="ISO datetime — 이후 신호만"),
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(get_current_user),
):
    """폴링용 incremental — `since`보다 새로운 신호만."""
    return svc.get_signals(since=since, limit=limit)


@router.get("/signals")
def get_signals(
    indicator_name: Optional[str] = Query(None),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    _user: dict = Depends(get_current_user),
):
    """신호 이력 검색."""
    return svc.get_signals(
        indicator_name=indicator_name, since=from_, until=to, limit=limit
    )


@router.post("/signals/{signal_id}/ack")
def ack_signal(signal_id: int, user: dict = Depends(require_admin)):
    svc.ack_signal(signal_id, user_id=user.get("id"))
    return {"ack": True, "id": signal_id}


@router.get("/thresholds")
def list_thresholds(
    indicator_name: Optional[str] = Query(None),
    _user: dict = Depends(get_current_user),
):
    return svc.list_thresholds(indicator_name)


@router.put("/thresholds/{indicator_name}/{threshold_key}")
def upsert_threshold(
    indicator_name: str,
    threshold_key: str,
    body: ThresholdBody = Body(...),
    user: dict = Depends(require_admin),
):
    return svc.upsert_threshold(
        indicator_name=indicator_name,
        threshold_key=threshold_key,
        value=body.value,
        comment=body.comment,
        updated_by=user.get("id"),
    )


@router.post("/admin/refresh")
def admin_refresh(
    indicator_name: Optional[str] = Query(
        None, description="None이면 5종 전체 — 수집기 ID (hyperscaler_capex/memory_inventory/hbm_contracts/ai_ipo/market_breadth)"
    ),
    evaluate: bool = Query(True, description="수집 직후 평가+신호 발사 여부"),
    _user: dict = Depends(require_admin),
):
    """관리자 수동 트리거. None=전체, 명시=단일 수집기."""
    if indicator_name:
        out = svc.run_collector(indicator_name)
    else:
        out = svc.run_all_collectors()
    if evaluate:
        out["evaluation"] = svc.evaluate_and_persist()
    return out
