"""백테스트 서비스 — MCP 서버 연동 오케스트레이션.

KIS AI Extensions MCP 서버의 백테스트 도구를 호출하여 전략 실행 결과를 반환한다.
결과는 strategy_store(DB)에 저장하여 이력 관리 및 AI 자문 연동에 활용한다.

MCP 도구 매핑 테이블:
| 함수                    | MCP 도구                      | 용도                     |
|-------------------------|-------------------------------|--------------------------|
| list_presets()          | list_presets_tool              | 프리셋 전략 목록 조회     |
| list_indicators()      | list_indicators_tool           | 사용 가능 지표 목록 조회  |
| run_preset_backtest()  | run_preset_backtest_tool       | 프리셋 전략 백테스트 실행 |
| run_custom_backtest()  | validate_yaml_tool             | YAML 전략 검증 (1단계)   |
|                         | run_custom_backtest_tool       | 커스텀 전략 백테스트 (2단계) |
| get_strategy_signals() | run_preset_backtest_tool ×3    | AI 자문용 전략 신호 생성  |

의존 관계:
- services/mcp_client.py → MCPClient (JSON-RPC 통신)
- stock/strategy_store.py → 백테스트 job/결과 DB CRUD
- advisory_service.py에서 get_strategy_signals() 호출

MCP 비활성화(KIS_MCP_ENABLED=false) 시:
- list_presets/run_* 함수 → ConfigError (MCPClient._check_enabled에서 raise)
- get_strategy_signals() → None 반환 (graceful degrade)
"""

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
    """프리셋 전략 백테스트 실행.

    실행 흐름:
    1) UUID job_id 생성 → DB에 작업 메타데이터 선행 기록
    2) MCP run_preset_backtest_tool 호출 (최대 5분 소요 가능)
    3) 완료 시 _save_if_completed()로 메트릭 8개 추출 → DB 결과 저장
    4) 예외 발생 시 ExternalAPIError로 래핑하여 상위 전파
    """
    client = get_mcp_client()
    # UUID로 고유한 작업 ID 생성 — 결과 조회/이력 추적에 사용
    job_id = str(uuid.uuid4())

    # DB에 작업 기록 (Write-Ahead: MCP 호출 전 선행 저장)
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
    """커스텀 YAML 전략 백테스트 실행.

    2단계 실행:
    1) validate_yaml_tool로 YAML 구문 및 스키마 검증 (실패 시 즉시 ExternalAPIError)
    2) run_custom_backtest_tool로 실제 백테스트 실행
    """
    client = get_mcp_client()

    # 1단계: YAML 검증 — 구문 오류나 지원하지 않는 지표 사용 시 조기 실패
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

    대표 3전략 배치 실행 후 합의(consensus)를 도출한다.
    MCP 비활성화 시 None 반환 (advisory_service에서 graceful degrade).

    대표 3전략 선택 근거:
    - sma_crossover: 추세 추종 (이동평균 교차 — 가장 기본적인 추세 판별)
    - momentum: 모멘텀 (가격 변동률 기반 — 단기 방향성)
    - trend_filter_signal: 복합 추세 필터 (추세+필터 조합 — 노이즈 제거)
    이 3가지로 추세/모멘텀/복합 관점을 균형 있게 커버한다.
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

    # 합의 도출 — 과반수 투표 방식 (3전략 중 2개 이상 동일 신호 시 채택)
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
    """MCP 결과에서 전략 신호 추출.

    수익률 → 신호 변환 로직:
    - total_return_pct >  5% → BUY  (강도 = 수익률/20, 최대 1.0)
    - total_return_pct < -5% → SELL (강도 = |수익률|/20, 최대 1.0)
    - -5% ~ +5%              → HOLD (강도 = 0.5, 중립)

    임계값 5%: 거래비용+슬리피지를 감안한 유의미한 수익률 기준.
    강도 스케일: 20%를 최대(1.0)로 설정 — 전략 1회 실행으로 20% 이상이면 강한 신호.
    """
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
    """MCP 결과가 완료 상태면 DB에 저장.

    MCP 응답에서 메트릭 8개를 추출하여 strategy_store에 저장한다:
    - total_return_pct: 총 수익률(%)
    - cagr: 연평균 복합 성장률(%)
    - sharpe_ratio: 샤프 비율 (위험 조정 수익률)
    - sortino_ratio: 소르티노 비율 (하방 위험만 고려)
    - max_drawdown: 최대 낙폭(%)
    - win_rate: 승률(%)
    - profit_factor: 총이익/총손실 비율
    - total_trades: 총 거래 횟수
    """
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
