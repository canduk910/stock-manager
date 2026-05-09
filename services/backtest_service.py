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
from services import _telemetry as _tel
from services.exceptions import ExternalAPIError, NotFoundError, ServiceError
from services.mcp_client import get_mcp_client
from stock import strategy_store

logger = logging.getLogger(__name__)


def _classify_local_failure(exc: Exception) -> str:
    """REQ-FIX-06: 로컬 백테스트 실패 원인 분류 → telemetry suffix."""
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "operationalerror" in name or "programmingerror" in name or "integrityerror" in name:
        return "db_error"
    if "json" in msg or "encode" in msg or "serializ" in msg:
        return "serialize"
    if "timeout" in msg:
        return "timeout"
    if "data" in msg or "load" in msg or "yfinance" in msg or "ticker" in msg:
        return "data_load"
    return "unknown"


# REQ-FIX-05: 외부 backtester 에러 메시지를 사용자 친화 메시지로 변환.
# 진단 결과(2026-05-09): 'vps' KeyError 는 backtester EC2 의
#   ~/KIS/config/kis_devlp.yaml 에서 KIS 모의투자 모드 식별자(`vps:` 섹션) 가
#   누락되었거나 다른 키(예: `vts:`)로 잘못 작성되어 KIS 인증 단계에서 발생.
# - kis_backtest/providers/kis/auth.py:158 → svr = "vps" if is_paper else "prod"
# - 사용자 측 fix: `sed -i 's/^vts:/vps:/' ~/KIS/config/kis_devlp.yaml` 후 MCP 재기동
#
# 'vps' 단독 패턴은 yaml 설정 가이드를 노출, 그 외 데이터 준비 실패는 종목/날짜 가이드.
_VPS_KEY_PATTERN = "'vps'"
_DATA_PREP_PATTERNS = ("데이터 준비 실패", "data preparation failed")
_VPS_KEY_FRIENDLY_MESSAGE = (
    "백테스트 인증 설정 오류: backtester 서버의 ~/KIS/config/kis_devlp.yaml 에 "
    "KIS 모의투자(`vps:`) 섹션이 누락되었습니다. 운영자 조치 필요. "
    "(임시: 로컬 백테스트 사용 권고)"
)
_DATA_PREP_FRIENDLY_MESSAGE = (
    "백테스트 데이터 조회 실패: 종목 코드를 확인하거나 다른 날짜 범위로 재시도하세요. "
    "(외부 backtester 데이터 준비 실패)"
)


def _classify_backtester_error(error_msg: str) -> Optional[str]:
    """외부 backtester error 메시지를 분류.

    Returns:
        "vps_key_missing" — KIS yaml `vps:` 섹션 누락(인증 단계 KeyError)
        "data_prep"       — 그 외 데이터 준비 실패(종목/날짜 가이드)
        None              — 분류 불가, 원본 메시지 노출
    """
    if not error_msg:
        return None
    if _VPS_KEY_PATTERN in error_msg:
        return "vps_key_missing"
    low = error_msg.lower()
    if any(p.lower() in low for p in _DATA_PREP_PATTERNS):
        return "data_prep"
    return None


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
                            # REQ-FIX-05: 패턴 분류 후 사용자 친화 메시지 매핑.
                            # 원본은 logger.warning 으로 보존(운영 디버깅).
                            kind = _classify_backtester_error(error_msg)
                            if kind == "vps_key_missing":
                                logger.warning(
                                    "MCP backtester yaml `vps:` key missing: %s",
                                    error_msg,
                                )
                                raise ExternalAPIError(_VPS_KEY_FRIENDLY_MESSAGE)
                            if kind == "data_prep":
                                logger.warning(
                                    "MCP backtester data preparation error: %s",
                                    error_msg,
                                )
                                raise ExternalAPIError(_DATA_PREP_FRIENDLY_MESSAGE)
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
    """MCP 비동기 2단계 실행 (동기 대기) — `get_strategy_signals`/`run_batch_backtest` 전용.

    fire-and-poll로 전환되지 않은 흐름(짧은 신호 도출/배치)에서만 사용.
    POST /run/preset, /run/custom 은 `_submit_mcp_job` + `poll_backtest_job` 으로 분리됨.
    """
    mcp_job_id = _submit_mcp_job(client, tool_name, params)
    result2 = client.call_tool("get_backtest_result_tool", {
        "job_id": mcp_job_id,
        "wait": True,
        "timeout": timeout,
    })
    return _extract_mcp_content(result2)


def _submit_mcp_job(client, tool_name: str, params: dict) -> str:
    """MCP 1단계만 호출 — `tool_name` 제출 후 즉시 mcp_job_id 반환.

    fire-and-poll 패턴: POST 진입점에서 호출, 결과 대기는 `poll_backtest_job` 위임.
    """
    result1 = client.call_tool(tool_name, params)
    data1 = _extract_mcp_content(result1)
    if not isinstance(data1, dict) or "job_id" not in data1:
        raise ExternalAPIError(f"MCP 응답에서 job_id를 찾을 수 없습니다: {data1}")
    mcp_job_id = data1["job_id"]
    logger.info("MCP 백테스트 제출 완료: %s (MCP job: %s)", tool_name, mcp_job_id)
    return mcp_job_id


def _fetch_mcp_result_nowait(client, mcp_job_id: str) -> Optional[dict]:
    """MCP 결과 즉시 조회 (wait=False, timeout=0). 미완료면 None 반환.

    완료(`status: "completed"` 또는 result 존재) → dict 반환.
    실패(`success: false`) → ExternalAPIError raise (메시지 분류 후 친화 변환).
    진행 중 → None.
    """
    res = client.call_tool("get_backtest_result_tool", {
        "job_id": mcp_job_id,
        "wait": False,
        "timeout": 0,
    })
    data = _extract_mcp_content(res)
    if not isinstance(data, dict):
        return None
    # MCP 응답 status 필드 — backtester 정의에 따라 progress/running/completed 등
    status = data.get("status") or (data.get("result") or {}).get("status")
    if status in ("running", "submitted", "pending", "queued", "in_progress"):
        return None
    # result 페이로드가 명시적으로 존재하면 완료로 간주
    if "result" in data or "metrics" in data:
        return data
    # status 미정인데 metrics 없음 → 진행 중으로 보수 처리
    if status is None:
        return None
    return data


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
    commission_rate: Optional[float] = None,
    tax_rate: Optional[float] = None,
    slippage: Optional[float] = None,
    user_id: int = 1,
) -> dict:
    """프리셋 전략 백테스트 — fire-and-poll 즉시 반환.

    1) BacktestJob status='running' Write-Ahead
    2) MCP run_preset_backtest_tool 제출 → mcp_job_id 받아서 DB에 영속
    3) 즉시 {job_id, status:'running', mcp_job_id} 반환 (결과 대기 없음)
    4) 클라이언트가 GET /api/backtest/result/{job_id} 로 폴링 → poll_backtest_job 트리거
    """
    client = get_mcp_client()
    job_id = str(uuid.uuid4())

    strategy_store.save_backtest_job(
        user_id=user_id,
        job_id=job_id,
        strategy_name=preset,
        symbol=symbol,
        market=market,
        strategy_type="preset",
        submitted_at=now_kst_iso(),
        params=params,
        strategy_display_name=preset_name,
    )
    strategy_store.update_job_status(job_id, "running")

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
    if commission_rate is not None:
        mcp_params["commission_rate"] = commission_rate
    if tax_rate is not None:
        mcp_params["tax_rate"] = tax_rate
    if slippage is not None:
        mcp_params["slippage"] = slippage

    try:
        mcp_job_id = _submit_mcp_job(client, "run_preset_backtest_tool", mcp_params)
        strategy_store.set_mcp_job_id(job_id, mcp_job_id)
        return {"job_id": job_id, "status": "running", "mcp_job_id": mcp_job_id}
    except ExternalAPIError as e:
        strategy_store.update_job_failed(job_id, str(e))
        raise
    except Exception as e:
        strategy_store.update_job_failed(job_id, f"백테스트 제출 실패: {e}")
        logger.error("백테스트 제출 실패: %s", e, exc_info=True)
        raise ExternalAPIError(f"백테스트 제출 실패: {e}")


def run_custom_backtest(
    yaml_content: str,
    symbol: str,
    market: str = "KR",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_cash: int = 10_000_000,
    commission_rate: Optional[float] = None,
    tax_rate: Optional[float] = None,
    slippage: Optional[float] = None,
    strategy_display_name: Optional[str] = None,
    builder_state: Optional[dict] = None,
    user_id: int = 1,
) -> dict:
    """커스텀 YAML 전략 백테스트 실행.

    3단계:
    1) validate_yaml_tool로 YAML 검증
    2) run_backtest_tool → 즉시 MCP job_id 반환
    3) get_backtest_result_tool(wait=true) → 완료 대기

    builder_state가 있으면 전략빌더에서 생성된 YAML로 판단하여
    strategy_name="builder", params에 지표/조건 요약을 저장한다.
    """
    from services.strategy_builder_service import extract_strategy_summary

    client = get_mcp_client()

    # 1단계: YAML 검증
    try:
        val_result = client.call_tool("validate_yaml_tool", {"yaml_content": yaml_content})
        _extract_mcp_content(val_result)  # success:false 시 ExternalAPIError raise
    except ExternalAPIError as e:
        raise ExternalAPIError(f"YAML 검증 실패: {e}")

    # 전략 요약 추출
    summary = extract_strategy_summary(yaml_content)
    is_builder = builder_state is not None
    job_strategy_name = "builder" if is_builder else "custom"
    job_display_name = strategy_display_name or summary.get("name") or None
    job_params = summary if summary else None

    job_id = str(uuid.uuid4())
    strategy_store.save_backtest_job(
        user_id=user_id,
        job_id=job_id,
        strategy_name=job_strategy_name,
        symbol=symbol,
        market=market,
        strategy_type=job_strategy_name,
        submitted_at=now_kst_iso(),
        params=job_params,
        strategy_display_name=job_display_name,
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
    if commission_rate is not None:
        params["commission_rate"] = commission_rate
    if tax_rate is not None:
        params["tax_rate"] = tax_rate
    if slippage is not None:
        params["slippage"] = slippage

    strategy_store.update_job_status(job_id, "running")
    try:
        mcp_job_id = _submit_mcp_job(client, "run_backtest_tool", params)
        strategy_store.set_mcp_job_id(job_id, mcp_job_id)
        return {"job_id": job_id, "status": "running", "mcp_job_id": mcp_job_id}
    except ExternalAPIError as e:
        strategy_store.update_job_failed(job_id, str(e))
        raise
    except Exception as e:
        strategy_store.update_job_failed(job_id, f"커스텀 백테스트 제출 실패: {e}")
        logger.error("커스텀 백테스트 제출 실패: %s", e, exc_info=True)
        raise ExternalAPIError(f"커스텀 백테스트 제출 실패: {e}")


def get_backtest_result(job_id: str) -> dict:
    """백테스트 결과 조회 — fire-and-poll lazy MCP polling 트리거.

    DB 행 status가 'running'/'submitted'면 MCP 측에 wait=False로 1회 조회 후
    완료/실패 시 DB 갱신. 그 외(completed/failed)는 DB 행 그대로 반환.
    """
    return poll_backtest_job(job_id)


def _surface_error(job: dict) -> dict:
    """failed 상태 행의 result_json.error_message를 top-level `error`로 expose.

    프론트 `useBacktest.js`가 `res.error`를 직접 사용하기 때문.
    """
    if (job.get("status") or "").lower() == "failed":
        rj = job.get("result_json") if isinstance(job.get("result_json"), dict) else {}
        msg = (rj or {}).get("error_message")
        if msg and "error" not in job:
            job = {**job, "error": msg}
    return job


def poll_backtest_job(job_id: str, _user_id: Optional[int] = None) -> dict:
    """fire-and-poll 진입점. DB 행 + MCP lazy poll로 상태/결과 회수.

    상태별 동작:
    - completed/failed: DB 행 그대로 반환 (MCP 호출 안 함)
    - running/submitted + mcp_job_id 존재 + MCP 활성: MCP wait=False 1회 조회
        - MCP 완료 → save_backtest_result + status="completed"
        - MCP 실패 → update_job_failed + 친화 메시지
        - MCP 진행 중 → DB 행 그대로 반환 (status="running")
    - running + mcp_job_id 부재(alembic 미적용 환경): DB 행 그대로 반환 (graceful)
    """
    job = strategy_store.get_job(job_id)
    if not job:
        raise NotFoundError(f"백테스트 작업을 찾을 수 없습니다: {job_id}")

    status = (job.get("status") or "").lower()
    if status in ("completed", "failed"):
        return _surface_error(job)
    if status not in ("running", "submitted"):
        return _surface_error(job)

    mcp_job_id = job.get("mcp_job_id")
    if not mcp_job_id or not KIS_MCP_ENABLED:
        return job

    try:
        client = get_mcp_client()
        data = _fetch_mcp_result_nowait(client, mcp_job_id)
    except ExternalAPIError as e:
        strategy_store.update_job_failed(job_id, str(e))
        return _surface_error(strategy_store.get_job(job_id) or job)
    except Exception as e:
        logger.warning("MCP 폴링 일시 실패 — 상태 유지(다음 폴링 재시도): %s", e)
        return job

    if data is None:
        return job

    _save_completed(job_id, data)
    return _surface_error(strategy_store.get_job(job_id) or job)


def run_batch_backtest(
    presets: list[str],
    symbol: str,
    market: str = "KR",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_cash: int = 10_000_000,
    user_id: int = 1,
) -> dict:
    """배치 비교 (여러 전략). 내부 동기 흐름 — 전체 결과를 한 응답에 묶어 반환.

    fire-and-poll 적용 외 — `run_preset_backtest`가 즉시 반환으로 바뀌었으므로
    batch는 `_run_and_wait`을 직접 호출해 동기 결과 회수. nginx 310s 가드 유지.
    """
    client = get_mcp_client()
    results = {}
    for preset in presets:
        job_id = str(uuid.uuid4())
        try:
            strategy_store.save_backtest_job(
                user_id=user_id,
                job_id=job_id,
                strategy_name=preset,
                symbol=symbol,
                market=market,
                strategy_type="preset",
                submitted_at=now_kst_iso(),
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
            data = _run_and_wait(client, "run_preset_backtest_tool", mcp_params)
            _save_completed(job_id, data)
            results[preset] = {"job_id": job_id, "status": "completed", "result": data}
        except ExternalAPIError as e:
            strategy_store.update_job_failed(job_id, str(e))
            results[preset] = {"job_id": job_id, "error": str(e)}
        except Exception as e:
            strategy_store.update_job_failed(job_id, f"배치 실행 실패: {e}")
            results[preset] = {"job_id": job_id, "error": str(e)}
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


# ── 로컬 백테스트 (services/local_backtest 패키지, MCP 미사용) ──────────────────

def list_local_presets() -> list[dict]:
    """로컬 4개 KR 전략 프리셋 메타데이터 (즉시 반환, MCP 호출 없음).

    응답 키는 기존 MCP `list_presets()`와 동일: id/name/description/category/tags
    /default_params/param_schema. params는 MCP 호환을 위해 default_params를 그대로 노출.
    """
    from services.local_backtest.presets import LOCAL_PRESETS

    out: list[dict] = []
    for p in LOCAL_PRESETS:
        # MCP 응답과 동일 형태: parameters는 schema. params는 default 값 모음.
        params_view: dict = {}
        for k, v in (p.get("param_schema") or {}).items():
            params_view[k] = v
        out.append({
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "category": p.get("category"),
            "tags": p.get("tags", []),
            "default_params": dict(p.get("default_params") or {}),
            "params": params_view,  # 프론트 슬라이더 렌더용 (StrategySelector PARAM_KR)
            "param_schema": params_view,
        })
    return out


def run_local_backtest(
    preset: str,
    symbols: list[str],
    market: str = "KR",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_capital: float = 10_000_000,
    commission_rate: float = 0.0015,
    tax_rate: float = 0.0023,
    slippage: float = 0.001,
    params: Optional[dict] = None,
    user_id: int = 1,
) -> dict:
    """로컬 4개 전략 + 균등 배분 포트폴리오 일봉 백테스트.

    plan ai-sleepy-pancake.md — 일봉 단순화. 외부 MCP 미사용. KR market만 지원(MVP).

    검증:
      - 1 ≤ len(symbols) ≤ 10 (Pydantic도 검증하지만 서비스 레이어 방어적 가드)
      - 동일 코드 중복 제거 (입력 순서 보존)
      - market == "KR"
      - 시작일/종료일 형식

    저장:
      - BacktestJob (strategy_type="local", symbol=symbols[0], symbols=전체 list)
      - result_json: {equity_curve, trades, per_symbol_contribution, params, failures}
    """
    from datetime import date as _date_cls
    from services.local_backtest import simulate as _simulate
    from services.local_backtest.presets import get_preset

    # ── 검증 ──────────────────────────────────────────────────────────
    if not symbols:
        raise ServiceError("symbols 비어있음")
    # 중복 제거 (입력 순서 보존)
    deduped: list[str] = []
    seen = set()
    for s in symbols:
        if not isinstance(s, str):
            continue
        s_clean = s.strip().upper()
        if not s_clean or s_clean in seen:
            continue
        seen.add(s_clean)
        deduped.append(s_clean)
    if not deduped:
        raise ServiceError("symbols에 유효한 종목 코드가 없습니다")
    if len(deduped) > 10:
        raise ServiceError("로컬 백테스트는 최대 10종목까지 지원합니다")
    if (market or "").upper() != "KR":
        raise ServiceError("로컬 백테스트는 KR market만 지원합니다 (MVP)")

    try:
        preset_meta = get_preset(preset)
    except KeyError:
        raise ServiceError(f"알 수 없는 로컬 프리셋: {preset}")

    # 날짜 파싱 (기본: 시작=1년전, 종료=오늘)
    from datetime import date as _d, timedelta as _td
    today = _d.today()
    try:
        sd = _d.fromisoformat(start_date) if start_date else today - _td(days=365)
        ed = _d.fromisoformat(end_date) if end_date else today
    except ValueError:
        raise ServiceError("start_date/end_date 형식 오류 (YYYY-MM-DD)")
    if sd >= ed:
        raise ServiceError("start_date는 end_date보다 이전이어야 합니다")

    job_id = str(uuid.uuid4())

    # REQ-FIX-06: entry 로그
    logger.info(
        "[backtest.local.entry] preset=%s symbols=%s market=%s start=%s end=%s user_id=%s job_id=%s",
        preset, deduped, "KR", sd.isoformat(), ed.isoformat(), user_id, job_id,
    )
    import time as _t
    _t0 = _t.perf_counter()

    # Write-Ahead 저장 (REQ-FIX-01: SQL 에러 → ServiceError 변환, raw 500 회피)
    try:
        strategy_store.save_backtest_job(
            user_id=user_id,
            job_id=job_id,
            strategy_name=preset,
            symbol=deduped[0],
            symbols=deduped,
            market="KR",
            strategy_type="local",
            submitted_at=now_kst_iso(),
            params=params,
            strategy_display_name=preset_meta.get("name"),
        )
    except ServiceError as e:
        _tel.record_event(f"backtest.local.fail.{_classify_local_failure(e)}")
        raise
    except Exception as e:
        logger.error("[REQ-FIX-01] save_backtest_job 실패: %s", e, exc_info=True)
        _tel.record_event(f"backtest.local.fail.{_classify_local_failure(e)}")
        raise ServiceError(
            f"백테스트 작업 등록 실패 (DB 마이그레이션 필요할 수 있음): {e}"
        )

    try:
        sim = _simulate(
            symbols=deduped,
            strategy_id=preset,
            market="KR",
            start=sd,
            end=ed,
            initial_capital=float(initial_capital),
            commission_rate=float(commission_rate),
            tax_rate=float(tax_rate),
            slippage=float(slippage),
            params=params,
        )
    except ValueError as e:
        strategy_store.update_job_status(job_id, "failed")
        _tel.record_event("backtest.local.fail.data_load")
        raise ServiceError(str(e))
    except Exception as e:
        strategy_store.update_job_status(job_id, "failed")
        logger.error("로컬 백테스트 실패: %s", e, exc_info=True)
        _tel.record_event(f"backtest.local.fail.{_classify_local_failure(e)}")
        raise ExternalAPIError(f"로컬 백테스트 실패: {e}")

    result_json = {
        "preset": preset,
        "symbols": deduped,
        "market": "KR",
        "start_date": sd.isoformat(),
        "end_date": ed.isoformat(),
        "params": sim.params,
        "equity_curve": sim.equity_curve,
        "trades": sim.trades,
        "per_symbol_contribution": sim.per_symbol_contribution,
        "failures": sim.failures,
        "result": {
            "metrics": {
                "basic": {
                    "total_return": sim.metrics.get("total_return_pct"),
                    "annual_return": sim.metrics.get("cagr"),
                    "max_drawdown": sim.metrics.get("max_drawdown"),
                },
                "risk": {
                    "sharpe_ratio": sim.metrics.get("sharpe_ratio"),
                    "sortino_ratio": sim.metrics.get("sortino_ratio"),
                },
                "trading": {
                    "total_orders": sim.metrics.get("total_trades"),
                    "win_rate": sim.metrics.get("win_rate"),
                    "profit_loss_ratio": sim.metrics.get("profit_factor"),
                },
            },
            "equity_curve": sim.equity_curve,
            "trades": sim.trades,
        },
    }

    # REQ-FIX-04: numpy/pandas 잔재 한 번 더 정제 (FastAPI JSON 인코딩 안전망)
    from services.local_backtest.engine import _to_jsonable
    try:
        result_json = _to_jsonable(result_json)
    except Exception as e:
        _tel.record_event("backtest.local.fail.serialize")
        logger.error("[REQ-FIX-04] 결과 직렬화 실패: %s", e, exc_info=True)
        raise ExternalAPIError(f"결과 직렬화 실패: {e}")

    strategy_store.save_backtest_result(
        job_id=job_id,
        metrics=_to_jsonable(sim.metrics),
        result_json=result_json,
        completed_at=now_kst_iso(),
    )

    # REQ-FIX-06: success telemetry + exit 로그
    _tel.record_event("backtest.local.success")
    _duration_ms = (_t.perf_counter() - _t0) * 1000.0
    _tel.observe("backtest.local.duration_ms", _duration_ms)
    logger.info(
        "[backtest.local.exit] job_id=%s status=completed duration_ms=%.1f trades=%d",
        job_id, _duration_ms, len(sim.trades) if sim.trades else 0,
    )
    return {"job_id": job_id, "status": "completed", "result": result_json}
