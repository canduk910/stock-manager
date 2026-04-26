"""백테스트 API 라우터."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from config import KIS_MCP_ENABLED
from services.auth_deps import get_current_user
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
    commission_rate: Optional[float] = None
    tax_rate: Optional[float] = None
    slippage: Optional[float] = None


class CustomBacktestBody(BaseModel):
    yaml_content: str
    symbol: str
    market: str = "KR"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_cash: int = Field(default=10_000_000, ge=100_000)
    commission_rate: Optional[float] = None
    tax_rate: Optional[float] = None
    slippage: Optional[float] = None
    strategy_display_name: Optional[str] = None
    builder_state: Optional[dict] = None


class BatchBacktestBody(BaseModel):
    presets: list[str]
    symbol: str
    market: str = "KR"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_cash: int = Field(default=10_000_000, ge=100_000)


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("/status")
def mcp_status(_user: dict = Depends(get_current_user)):
    """MCP 서버 연결 상태."""
    if not KIS_MCP_ENABLED:
        return {"available": False, "reason": "KIS_MCP_ENABLED=false"}
    client = get_mcp_client()
    healthy = client.health_check()
    return {"available": healthy}


@router.get("/presets")
def get_presets(_user: dict = Depends(get_current_user)):
    """프리셋 전략 목록."""
    return backtest_service.list_presets()


@router.get("/indicators")
def get_indicators(_user: dict = Depends(get_current_user)):
    """사용 가능한 기술 지표 목록."""
    return backtest_service.list_indicators()


@router.post("/run/preset")
def run_preset(body: PresetBacktestBody, user: dict = Depends(get_current_user)):
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
        commission_rate=body.commission_rate,
        tax_rate=body.tax_rate,
        slippage=body.slippage,
        user_id=user["id"],
    )


@router.post("/run/custom")
def run_custom(body: CustomBacktestBody, user: dict = Depends(get_current_user)):
    """커스텀 YAML 전략 백테스트 실행."""
    return backtest_service.run_custom_backtest(
        yaml_content=body.yaml_content,
        symbol=body.symbol,
        market=body.market,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_cash=body.initial_cash,
        commission_rate=body.commission_rate,
        tax_rate=body.tax_rate,
        slippage=body.slippage,
        strategy_display_name=body.strategy_display_name,
        builder_state=body.builder_state,
        user_id=user["id"],
    )


@router.post("/run/batch")
def run_batch(body: BatchBacktestBody, _user: dict = Depends(get_current_user)):
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
def get_result(job_id: str, _user: dict = Depends(get_current_user)):
    """백테스트 결과 조회."""
    return backtest_service.get_backtest_result(job_id)


@router.get("/history")
def get_history(symbol: Optional[str] = None, market: Optional[str] = None, limit: int = 20, user: dict = Depends(get_current_user)):
    """백테스트 작업 이력."""
    jobs = strategy_store.get_job_history(user["id"], symbol=symbol, market=market, limit=limit)
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
def delete_history(job_id: str, _user: dict = Depends(get_current_user)):
    """백테스트 이력 삭제."""
    ok = strategy_store.delete_job(job_id)
    if not ok:
        raise NotFoundError(f"백테스트 작업을 찾을 수 없습니다: {job_id}")
    return {"deleted": True}


# ── 전략빌더 엔드포인트 ───────────────────────────────────────────────────────


class BuilderConvertBody(BaseModel):
    builder_state: dict
    run_validate: bool = True


class StrategySaveBody(BaseModel):
    name: str
    description: Optional[str] = None
    yaml_content: Optional[str] = None
    builder_state: Optional[dict] = None


class StrategyValidateBody(BaseModel):
    yaml_content: str


@router.post("/strategy/convert")
def convert_strategy(body: BuilderConvertBody, _user: dict = Depends(get_current_user)):
    """BuilderState -> YAML 변환."""
    from services.strategy_builder_service import convert_builder_to_yaml

    yaml_content = convert_builder_to_yaml(body.builder_state)

    result = {"yaml_content": yaml_content, "valid": None, "errors": []}

    if body.run_validate and KIS_MCP_ENABLED:
        try:
            client = get_mcp_client()
            client.call_tool("validate_yaml_tool", {"yaml_content": yaml_content})
            result["valid"] = True
        except Exception as e:
            result["valid"] = False
            result["errors"] = [str(e)]

    return result


@router.post("/strategy/validate")
def validate_yaml(body: StrategyValidateBody, _user: dict = Depends(get_current_user)):
    """YAML MCP 검증."""
    if not KIS_MCP_ENABLED:
        return {"valid": None, "reason": "MCP 비활성화"}
    client = get_mcp_client()
    try:
        client.call_tool("validate_yaml_tool", {"yaml_content": body.yaml_content})
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "errors": [str(e)]}


@router.get("/strategies")
def list_strategies(strategy_type: Optional[str] = None, user: dict = Depends(get_current_user)):
    """저장된 전략 목록."""
    return strategy_store.list_strategies(user["id"], strategy_type)


@router.post("/strategies")
def save_strategy(body: StrategySaveBody, user: dict = Depends(get_current_user)):
    """전략 저장."""
    return strategy_store.save_strategy(
        user["id"],
        name=body.name,
        strategy_type="builder",
        description=body.description,
        yaml_content=body.yaml_content,
        builder_state=body.builder_state,
    )


@router.get("/strategies/{name}")
def get_strategy(name: str, user: dict = Depends(get_current_user)):
    """전략 조회."""
    s = strategy_store.get_strategy(user["id"], name)
    if not s:
        raise NotFoundError(f"전략을 찾을 수 없습니다: {name}")
    return s


@router.delete("/strategies/{name}")
def delete_strategy(name: str, user: dict = Depends(get_current_user)):
    """전략 삭제."""
    ok = strategy_store.delete_strategy(user["id"], name)
    if not ok:
        raise NotFoundError(f"전략을 찾을 수 없습니다: {name}")
    return {"deleted": True}
