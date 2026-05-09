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


class LocalBacktestBody(BaseModel):
    """로컬 4개 KR 전략 + 다중 종목(최대 10) 백테스트 입력."""

    preset: str
    symbols: list[str] = Field(min_length=1, max_length=10)
    market: str = "KR"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = Field(default=10_000_000.0, ge=100_000.0)
    commission_rate: float = Field(default=0.0015, ge=0.0, le=0.1)
    tax_rate: float = Field(default=0.0023, ge=0.0, le=0.1)
    slippage: float = Field(default=0.001, ge=0.0, le=0.1)
    params: Optional[dict] = None


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
    logger.info(
        "[backtest.preset.entry] preset=%s symbol=%s market=%s start=%s end=%s user_id=%s",
        body.preset, body.symbol, body.market, body.start_date, body.end_date, user["id"],
    )
    out = backtest_service.run_preset_backtest(
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
    logger.info(
        "[backtest.preset.exit] job_id=%s status=%s",
        out.get("job_id") if isinstance(out, dict) else None,
        out.get("status") if isinstance(out, dict) else None,
    )
    return out


@router.post("/run/custom")
def run_custom(body: CustomBacktestBody, user: dict = Depends(get_current_user)):
    """커스텀 YAML 전략 백테스트 실행."""
    logger.info(
        "[backtest.custom.entry] symbol=%s market=%s start=%s end=%s user_id=%s",
        body.symbol, body.market, body.start_date, body.end_date, user["id"],
    )
    out = backtest_service.run_custom_backtest(
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
    logger.info(
        "[backtest.custom.exit] job_id=%s status=%s",
        out.get("job_id") if isinstance(out, dict) else None,
        out.get("status") if isinstance(out, dict) else None,
    )
    return out


@router.post("/run/batch")
def run_batch(body: BatchBacktestBody, user: dict = Depends(get_current_user)):
    """배치 비교 (여러 전략)."""
    logger.info(
        "[backtest.batch.entry] presets=%s symbol=%s market=%s",
        body.presets, body.symbol, body.market,
    )
    out = backtest_service.run_batch_backtest(
        presets=body.presets,
        symbol=body.symbol,
        market=body.market,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_cash=body.initial_cash,
        user_id=user["id"],
    )
    logger.info(
        "[backtest.batch.exit] symbol=%s presets=%d",
        body.symbol, len(body.presets),
    )
    return out


# ── 로컬 백테스트 (services/local_backtest 패키지, MCP 미사용) ──────────────────


@router.get("/local/presets")
def get_local_presets(_user: dict = Depends(get_current_user)):
    """로컬 4개 KR 전략 프리셋 목록 (즉시 반환).

    `KIS_MCP_ENABLED`와 무관하게 항상 사용 가능. 응답 형식은 기존 MCP `/presets`와 호환.
    """
    return {"presets": backtest_service.list_local_presets()}


@router.post("/run/local")
def run_local(body: LocalBacktestBody, user: dict = Depends(get_current_user)):
    """로컬 4개 전략 + 균등 배분 포트폴리오 일봉 백테스트 (KR 전용 MVP)."""
    logger.info(
        "[backtest.local.router_entry] preset=%s symbols_n=%d market=%s start=%s end=%s user_id=%s",
        body.preset, len(body.symbols), body.market, body.start_date, body.end_date, user["id"],
    )
    out = backtest_service.run_local_backtest(
        preset=body.preset,
        symbols=body.symbols,
        market=body.market,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=body.initial_capital,
        commission_rate=body.commission_rate,
        tax_rate=body.tax_rate,
        slippage=body.slippage,
        params=body.params,
        user_id=user["id"],
    )
    logger.info(
        "[backtest.local.router_exit] job_id=%s status=%s",
        out.get("job_id") if isinstance(out, dict) else None,
        out.get("status") if isinstance(out, dict) else None,
    )
    return out


@router.get("/result/{job_id}")
def get_result(job_id: str, user: dict = Depends(get_current_user)):
    """백테스트 결과 조회 — fire-and-poll lazy MCP 폴링 트리거.

    DB 행이 running/submitted면 MCP `get_backtest_result_tool(wait=False)` 1회 조회 후
    완료/실패 시 DB 갱신. 프론트가 3초 간격으로 호출하면 자연스럽게 진행 상태가 갱신됨.
    """
    return backtest_service.poll_backtest_job(job_id, user_id=user["id"])


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
