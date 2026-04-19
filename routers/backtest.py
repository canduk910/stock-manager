"""백테스트 API 라우터."""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config import KIS_MCP_ENABLED
from services import backtest_service
from services.exceptions import NotFoundError
from services.mcp_client import get_mcp_client
from stock import strategy_store
from stock.utils import is_domestic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


# ── Pydantic Body 모델 ───────────────────────────────────────────────────────

class PresetBacktestBody(BaseModel):
    preset: str
    symbol: str
    market: str = "KR"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_cash: int = Field(default=10_000_000, ge=100_000)
    params: Optional[dict] = None
    preset_name: Optional[str] = None


class CustomBacktestBody(BaseModel):
    yaml_content: str
    symbol: str
    market: str = "KR"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_cash: int = Field(default=10_000_000, ge=100_000)


class BatchBacktestBody(BaseModel):
    presets: list[str]
    symbol: str
    market: str = "KR"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_cash: int = Field(default=10_000_000, ge=100_000)


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("/status")
def mcp_status():
    """MCP 서버 연결 상태."""
    if not KIS_MCP_ENABLED:
        return {"available": False, "reason": "KIS_MCP_ENABLED=false"}
    client = get_mcp_client()
    healthy = client.health_check()
    return {"available": healthy}


@router.get("/presets")
def get_presets():
    """프리셋 전략 목록."""
    return backtest_service.list_presets()


@router.get("/indicators")
def get_indicators():
    """사용 가능한 기술 지표 목록."""
    return backtest_service.list_indicators()


@router.post("/run/preset")
def run_preset(body: PresetBacktestBody):
    """프리셋 전략 백테스트 실행."""
    return backtest_service.run_preset_backtest(
        preset=body.preset,
        symbol=body.symbol,
        market=body.market,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_cash=body.initial_cash,
        params=body.params,
        preset_name=body.preset_name,
    )


@router.post("/run/custom")
def run_custom(body: CustomBacktestBody):
    """커스텀 YAML 전략 백테스트 실행."""
    return backtest_service.run_custom_backtest(
        yaml_content=body.yaml_content,
        symbol=body.symbol,
        market=body.market,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_cash=body.initial_cash,
    )


@router.post("/run/batch")
def run_batch(body: BatchBacktestBody):
    """배치 비교 (여러 전략)."""
    return backtest_service.run_batch_backtest(
        presets=body.presets,
        symbol=body.symbol,
        market=body.market,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_cash=body.initial_cash,
    )


@router.get("/result/{job_id}")
def get_result(job_id: str):
    """백테스트 결과 조회."""
    return backtest_service.get_backtest_result(job_id)


@router.get("/history")
def get_history(symbol: Optional[str] = None, market: Optional[str] = None, limit: int = 20):
    """백테스트 작업 이력."""
    jobs = strategy_store.get_job_history(symbol=symbol, market=market, limit=limit)
    for job in jobs:
        sym = job.get("symbol", "")
        if is_domestic(sym):
            try:
                from stock.symbol_map import code_to_name
                job["symbol_name"] = code_to_name(sym) or sym
            except Exception:
                job["symbol_name"] = sym
        else:
            job["symbol_name"] = sym
    return jobs


@router.delete("/history/{job_id}")
def delete_history(job_id: str):
    """백테스트 이력 삭제."""
    ok = strategy_store.delete_job(job_id)
    if not ok:
        raise NotFoundError(f"백테스트 작업을 찾을 수 없습니다: {job_id}")
    return {"deleted": True}
