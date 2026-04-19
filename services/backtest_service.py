"""백테스트 서비스 — MCP 서버 연동 오케스트레이션.

KIS AI Extensions MCP 서버의 백테스트 도구를 호출하여 전략 실행 결과를 반환한다.
결과는 strategy_store(DB)에 저장하여 이력 관리 및 AI 자문 연동에 활용한다.

MCP 도구 매핑 테이블 (비동기 2단계):
| 함수                    | MCP 도구 (1단계)              | MCP 도구 (2단계)              |
|-------------------------|-------------------------------|-------------------------------|
| list_presets()          | list_presets_tool              | -                             |
| list_indicators()      | list_indicators_tool           | -                             |
| run_preset_backtest()  | run_preset_backtest_tool       | get_backtest_result_tool      |
| run_custom_backtest()  | validate_yaml_tool + run_backtest_tool | get_backtest_result_tool |
| run_batch_backtest()   | run_batch_backtest_tool        | (내장 대기)                    |
| get_strategy_signals() | run_preset_backtest_tool ×3    | get_backtest_result_tool ×3   |

MCP 파라미터 스키마:
- run_preset_backtest_tool: strategy_id(str), symbols(list[str]), initial_capital(num), start_date, end_date
- run_backtest_tool: yaml_content(str), symbols(list[str]), initial_capital(num), start_date, end_date
- get_backtest_result_tool: job_id(str), wait(bool=true), timeout(num=300)
- run_batch_backtest_tool: items(list[dict]), start_date, end_date, initial_capital(num)

MCP 응답 메트릭 구조:
  data.result.metrics.basic: total_return, annual_return, max_drawdown
  data.result.metrics.risk: sharpe_ratio, sortino_ratio
  data.result.metrics.trading: total_orders, win_rate, profit_loss_ratio, avg_win, avg_loss

의존 관계:
- services/mcp_client.py → MCPClient (JSON-RPC 통신)
- stock/strategy_store.py → 백테스트 job/결과 DB CRUD
- advisory_service.py에서 get_strategy_signals() 호출

MCP 비활성화(KIS_MCP_ENABLED=false) 시:
- list_presets/run_* 함수 → ConfigError (MCPClient._check_enabled에서 raise)
- get_strategy_signals() → None 반환 (graceful degrade)
"""

import json
import logging
import uuid
from typing import Optional

from config import KIS_MCP_ENABLED
from db.utils import now_kst_iso
from services.exceptions import ExternalAPIError, NotFoundError
from services.mcp_client import get_mcp_client
from stock import strategy_store

logger = logging.getLogger(__name__)


def _extract_mcp_content(result: dict | list) -> any:
    """MCP Streamable HTTP 응답에서 실제 데이터 추출.

    MCP content 구조: {"content": [{"type":"text","text":"...JSON..."}]}
    text 안의 JSON에 {"success": true, "data": [...]} 형태가 있으면 data만 반환.
    """
    if isinstance(result, dict):
        content = result.get("content", [])
        if isinstance(content, list) and content:
            text = content[0].get("text", "")
            if text:
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        # success: false → 에러 raise (data 유무 무관)
                        if parsed.get("success") is False:
                            error_msg = parsed.get("error", "알 수 없는 오류")
                            raise ExternalAPIError(f"MCP 백테스트 실패: {error_msg}")
                        # {"success": true, "data": [...]} 구조면 data만 반환
                        if "data" in parsed:
                            return parsed["data"]
                    return parsed
                except (json.JSONDecodeError, TypeError):
                    return text
        return content if content else result
    return result


def _extract_metrics(data: dict) -> dict:
    """MCP 결과 데이터에서 메트릭 8개 추출.

    MCP 응답 구조:
      data.result.metrics.basic: total_return, annual_return, max_drawdown
      data.result.metrics.risk: sharpe_ratio, sortino_ratio
      data.result.metrics.trading: total_orders, win_rate, profit_loss_ratio
    """
    result = data.get("result", data) if isinstance(data, dict) else {}
    m = result.get("metrics", {}) if isinstance(result, dict) else {}
    basic = m.get("basic", {})
    risk = m.get("risk", {})
    trading = m.get("trading", {})

    return {
        "total_return_pct": basic.get("total_return"),
        "cagr": basic.get("annual_return"),
        "sharpe_ratio": risk.get("sharpe_ratio"),
        "sortino_ratio": risk.get("sortino_ratio"),
        "max_drawdown": basic.get("max_drawdown"),
        "win_rate": trading.get("win_rate"),
        "profit_factor": trading.get("profit_loss_ratio"),
        "total_trades": trading.get("total_orders"),
    }


def _run_and_wait(client, tool_name: str, params: dict, timeout: int = 280) -> dict:
    """MCP 비동기 2단계 실행: 도구 호출 → job_id 획득 → 결과 대기.

    1단계: tool_name 호출 → 즉시 job_id 반환
    2단계: get_backtest_result_tool(job_id, wait=true) → 완료 대기
    """
    # 1단계: 백테스트 제출 → job_id
    result1 = client.call_tool(tool_name, params)
    data1 = _extract_mcp_content(result1)
    if not isinstance(data1, dict) or "job_id" not in data1:
        raise ExternalAPIError(f"MCP 응답에서 job_id를 찾을 수 없습니다: {data1}")
    mcp_job_id = data1["job_id"]
    logger.info("MCP 백테스트 제출 완료: %s (MCP job: %s)", tool_name, mcp_job_id)

    # 2단계: 결과 대기
    result2 = client.call_tool("get_backtest_result_tool", {
        "job_id": mcp_job_id,
        "wait": True,
        "timeout": timeout,
    })
    data2 = _extract_mcp_content(result2)
    return data2


def list_presets() -> list:
    """MCP list_presets_tool 호출."""
    client = get_mcp_client()
    result = client.call_tool("list_presets_tool", {})
    return _extract_mcp_content(result)


def list_indicators() -> list:
    """MCP list_indicators_tool 호출."""
    client = get_mcp_client()
    result = client.call_tool("list_indicators_tool", {})
    return _extract_mcp_content(result)


def run_preset_backtest(
    preset: str,
    symbol: str,
    market: str = "KR",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_cash: int = 10_000_000,
    params: Optional[dict] = None,
    preset_name: Optional[str] = None,
) -> dict:
    """프리셋 전략 백테스트 실행.

    비동기 2단계:
    1) run_preset_backtest_tool → 즉시 MCP job_id 반환
    2) get_backtest_result_tool(wait=true) → 완료 대기 후 결과
    """
    client = get_mcp_client()
    job_id = str(uuid.uuid4())

    # DB에 작업 기록 (Write-Ahead)
    strategy_store.save_backtest_job(
        job_id=job_id,
        strategy_name=preset,
        symbol=symbol,
        market=market,
        strategy_type="preset",
        submitted_at=now_kst_iso(),
        params=params,
        strategy_display_name=preset_name,
    )

    mcp_params = {
        "strategy_id": preset,
        "symbols": [symbol],
        "initial_capital": initial_cash,
    }
    if start_date:
        mcp_params["start_date"] = start_date
    if end_date:
        mcp_params["end_date"] = end_date
    if params:
        mcp_params["param_overrides"] = params

    try:
        data = _run_and_wait(client, "run_preset_backtest_tool", mcp_params)
        _save_completed(job_id, data)
        return {"job_id": job_id, "status": "completed", "result": data}
    except ExternalAPIError:
        strategy_store.update_job_status(job_id, "failed")
        raise
    except Exception as e:
        strategy_store.update_job_status(job_id, "failed")
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
    """커스텀 YAML 전략 백테스트 실행.

    3단계:
    1) validate_yaml_tool로 YAML 검증
    2) run_backtest_tool → 즉시 MCP job_id 반환
    3) get_backtest_result_tool(wait=true) → 완료 대기
    """
    client = get_mcp_client()

    # 1단계: YAML 검증
    try:
        val_result = client.call_tool("validate_yaml_tool", {"yaml_content": yaml_content})
        _extract_mcp_content(val_result)  # success:false 시 ExternalAPIError raise
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
        "symbols": [symbol],
        "initial_capital": initial_cash,
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    try:
        data = _run_and_wait(client, "run_backtest_tool", params)
        _save_completed(job_id, data)
        return {"job_id": job_id, "status": "completed", "result": data}
    except ExternalAPIError:
        strategy_store.update_job_status(job_id, "failed")
        raise
    except Exception as e:
        strategy_store.update_job_status(job_id, "failed")
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
    """배치 비교 (여러 전략). 내부적으로 순차 실행."""
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

    대표 3전략 배치 실행 후 합의(consensus)를 도출한다.
    MCP 비활성화 시 None 반환 (advisory_service에서 graceful degrade).

    대표 3전략:
    - sma_crossover: 추세 추종 (이동평균 교차)
    - momentum: 모멘텀 (가격 변동률)
    - trend_filter_signal: 복합 추세 필터
    """
    if not KIS_MCP_ENABLED:
        return None

    representative_presets = ["sma_crossover", "momentum", "trend_filter_signal"]
    signals = []
    metrics_list = []

    client = get_mcp_client()

    for preset in representative_presets:
        try:
            data = _run_and_wait(client, "run_preset_backtest_tool", {
                "strategy_id": preset,
                "symbols": [code],
                "initial_capital": 10_000_000,
            }, timeout=120)

            # 메트릭 추출
            metrics = _extract_metrics(data)
            total_return = metrics.get("total_return_pct", 0) or 0

            # 신호 추출
            signal = _extract_signal(preset, total_return)
            signals.append(signal)

            metrics_list.append({
                "strategy": preset,
                "total_return_pct": total_return,
                "sharpe_ratio": metrics.get("sharpe_ratio"),
                "max_drawdown": metrics.get("max_drawdown"),
            })
        except Exception as e:
            logger.warning("전략 신호 생성 실패 (%s): %s", preset, e)
            signals.append({"strategy": preset, "signal": "HOLD", "strength": 0.0, "error": str(e)})

    # 합의 도출 — 과반수 투표
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


def _extract_signal(preset: str, total_return: float) -> dict:
    """수익률 → 신호 변환.

    - > 5% → BUY (강도 = 수익률/20, 최대 1.0)
    - < -5% → SELL (강도 = |수익률|/20, 최대 1.0)
    - -5% ~ +5% → HOLD (강도 = 0.5)
    """
    if not isinstance(total_return, (int, float)):
        return {"strategy": preset, "signal": "HOLD", "strength": 0.0}

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


def _save_completed(job_id: str, data) -> None:
    """MCP 결과를 DB에 저장."""
    if not isinstance(data, dict):
        return

    metrics = _extract_metrics(data)
    strategy_store.save_backtest_result(
        job_id=job_id,
        metrics=metrics,
        result_json=data,
        completed_at=now_kst_iso(),
    )
