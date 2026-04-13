"""투자 파이프라인 API 라우터."""

import threading

from fastapi import APIRouter

from services.scheduler_service import get_scheduler_status

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# 실행 중 상태 추적
_running = {"KR": False, "US": False}
_last_result = {"KR": None, "US": None}


@router.post("/run")
def run_pipeline(market: str = "KR"):
    """수동 파이프라인 실행 (비동기 — 즉시 응답)."""
    market = market.upper()
    if market not in ("KR", "US"):
        return {"error": f"지원하지 않는 시장: {market}. KR 또는 US만 가능합니다."}

    if _running.get(market):
        return {"status": "already_running", "market": market, "message": f"{market} 파이프라인이 이미 실행 중입니다."}

    def _run():
        from services.pipeline_service import run_pipeline as _run_impl
        _running[market] = True
        try:
            result = _run_impl(market)
            _last_result[market] = result
        except Exception as e:
            _last_result[market] = {"error": str(e)}
        finally:
            _running[market] = False

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "market": market, "message": f"{market} 파이프라인 실행을 시작했습니다."}


@router.post("/run-sync")
def run_pipeline_sync(market: str = "KR"):
    """수동 파이프라인 동기 실행 (완료까지 대기)."""
    from services.pipeline_service import run_pipeline as _run_impl
    market = market.upper()
    if market not in ("KR", "US"):
        return {"error": f"지원하지 않는 시장: {market}"}

    result = _run_impl(market)
    _last_result[market] = result
    return result


@router.get("/status")
def get_status():
    """스케줄러 상태 + 실행 상태."""
    scheduler = get_scheduler_status()
    return {
        "scheduler": scheduler,
        "running": {k: v for k, v in _running.items()},
        "last_result": {k: v for k, v in _last_result.items() if v},
    }
