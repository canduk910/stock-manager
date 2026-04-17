"""백테스트 서비스 — MCP 서버 연동 오케스트레이션."""

import logging
import uuid
from typing import Optional

from config import KIS_MCP_ENABLED
from db.utils import now_kst_iso
from services.exceptions import ExternalAPIError, NotFoundError
from services.mcp_client import get_mcp_client
from stock import strategy_store

logger = logging.getLogger(__name__)


def list_presets() -> list:
    """MCP list_presets_tool 호출."""
    client = get_mcp_client()
    result = client.call_tool("list_presets_tool", {})
    return result.get("content", result) if isinstance(result, dict) else result


def list_indicators() -> list:
    """MCP list_indicators_tool 호출."""
    client = get_mcp_client()
    result = client.call_tool("list_indicators_tool", {})
    return result.get("content", result) if isinstance(result, dict) else result


def run_preset_backtest(
    preset: str,
    symbol: str,
    market: str = "KR",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_cash: int = 10_000_000,
) -> dict:
    """프리셋 전략 백테스트 실행."""
    client = get_mcp_client()
    job_id = str(uuid.uuid4())

    # DB에 작업 기록
    strategy_store.save_backtest_job(
        job_id=job_id,
        strategy_name=preset,
        symbol=symbol,
        market=market,
        strategy_type="preset",
        submitted_at=now_kst_iso(),
    )

    params = {
        "preset": preset,
        "symbol": symbol,
        "market": market,
        "initial_cash": initial_cash,
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    try:
        result = client.call_tool("run_preset_backtest_tool", params)
        _save_if_completed(job_id, result)
        return {"job_id": job_id, "status": "completed", "result": result}
    except ExternalAPIError:
        raise
    except Exception as e:
        logger.error("백테스트 실행 실패: %s", e)
        raise ExternalAPIError(f"백테스트 실행 실패: {e}")


def run_custom_backtest(
    yaml_content: str,
    symbol: str,
    market: str = "KR",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_cash: int = 10_000_000,
) -> dict:
    """커스텀 YAML 전략 백테스트 실행."""
    client = get_mcp_client()

    # YAML 검증
    try:
        client.call_tool("validate_yaml_tool", {"yaml_content": yaml_content})
    except ExternalAPIError as e:
        raise ExternalAPIError(f"YAML 검증 실패: {e}")

    job_id = str(uuid.uuid4())
    strategy_store.save_backtest_job(
        job_id=job_id,
        strategy_name="custom",
        symbol=symbol,
        market=market,
        strategy_type="custom",
        submitted_at=now_kst_iso(),
    )

    params = {
        "yaml_content": yaml_content,
        "symbol": symbol,
        "market": market,
        "initial_cash": initial_cash,
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    try:
        result = client.call_tool("run_custom_backtest_tool", params)
        _save_if_completed(job_id, result)
        return {"job_id": job_id, "status": "completed", "result": result}
    except ExternalAPIError:
        raise
    except Exception as e:
        logger.error("커스텀 백테스트 실행 실패: %s", e)
        raise ExternalAPIError(f"커스텀 백테스트 실행 실패: {e}")


def get_backtest_result(job_id: str) -> dict:
    """백테스트 결과 조회."""
    job = strategy_store.get_job(job_id)
    if not job:
        raise NotFoundError(f"백테스트 작업을 찾을 수 없습니다: {job_id}")
    return job


def run_batch_backtest(
    presets: list[str],
    symbol: str,
    market: str = "KR",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_cash: int = 10_000_000,
) -> dict:
    """배치 비교 (여러 전략)."""
    results = {}
    for preset in presets:
        try:
            result = run_preset_backtest(
                preset=preset,
                symbol=symbol,
                market=market,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash,
            )
            results[preset] = result
        except Exception as e:
            results[preset] = {"error": str(e)}
    return {"symbol": symbol, "market": market, "results": results}


def get_strategy_signals(code: str, market: str) -> Optional[dict]:
    """종목별 전략 신호 생성 (AI 자문 연동용).

    대표 3전략(sma_crossover/momentum/trend_filter_signal) 배치 실행.
    MCP 비활성화 시 None 반환.
    """
    if not KIS_MCP_ENABLED:
        return None

    representative_presets = ["sma_crossover", "momentum", "trend_filter_signal"]
    signals = []
    metrics_list = []

    client = get_mcp_client()

    for preset in representative_presets:
        try:
            result = client.call_tool("run_preset_backtest_tool", {
                "preset": preset,
                "symbol": code,
                "market": market,
                "initial_cash": 10_000_000,
            })
            content = result.get("content", result) if isinstance(result, dict) else result

            # 신호 추출
            signal = _extract_signal(preset, content)
            signals.append(signal)

            # 메트릭 추출
            if isinstance(content, dict):
                metrics_list.append({
                    "strategy": preset,
                    "total_return_pct": content.get("total_return_pct"),
                    "sharpe_ratio": content.get("sharpe_ratio"),
                    "max_drawdown": content.get("max_drawdown"),
                })
        except Exception as e:
            logger.warning("전략 신호 생성 실패 (%s): %s", preset, e)
            signals.append({"strategy": preset, "signal": "HOLD", "strength": 0.0, "error": str(e)})

    # 합의 도출
    buy_count = sum(1 for s in signals if s.get("signal") == "BUY")
    sell_count = sum(1 for s in signals if s.get("signal") == "SELL")
    total = len(signals)

    if buy_count > total / 2:
        consensus = "BUY"
    elif sell_count > total / 2:
        consensus = "SELL"
    else:
        consensus = "HOLD"

    strengths = [s.get("strength", 0.0) for s in signals if isinstance(s.get("strength"), (int, float))]
    avg_strength = sum(strengths) / len(strengths) if strengths else 0.0

    return {
        "signals": signals,
        "consensus": consensus,
        "avg_strength": round(avg_strength, 2),
        "backtest_metrics": metrics_list,
    }


def _extract_signal(preset: str, content) -> dict:
    """MCP 결과에서 전략 신호 추출."""
    signal = "HOLD"
    strength = 0.0

    if isinstance(content, dict):
        total_return = content.get("total_return_pct", 0)
        if isinstance(total_return, (int, float)):
            if total_return > 5:
                signal = "BUY"
                strength = min(total_return / 20, 1.0)
            elif total_return < -5:
                signal = "SELL"
                strength = min(abs(total_return) / 20, 1.0)
            else:
                signal = "HOLD"
                strength = 0.5

    return {"strategy": preset, "signal": signal, "strength": round(strength, 2)}


def _save_if_completed(job_id: str, result) -> None:
    """MCP 결과가 완료 상태면 DB에 저장."""
    if not isinstance(result, dict):
        return
    content = result.get("content", result)
    if not isinstance(content, dict):
        return

    metrics = {
        "total_return_pct": content.get("total_return_pct"),
        "cagr": content.get("cagr"),
        "sharpe_ratio": content.get("sharpe_ratio"),
        "sortino_ratio": content.get("sortino_ratio"),
        "max_drawdown": content.get("max_drawdown"),
        "win_rate": content.get("win_rate"),
        "profit_factor": content.get("profit_factor"),
        "total_trades": content.get("total_trades"),
    }
    strategy_store.save_backtest_result(
        job_id=job_id,
        metrics=metrics,
        result_json=content,
        completed_at=now_kst_iso(),
    )
