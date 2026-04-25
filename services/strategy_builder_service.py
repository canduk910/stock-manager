"""전략빌더 서비스 — BuilderState -> KIS .kis.yaml 변환 + 요약 추출.

프론트엔드 빌더 UI에서 생성된 BuilderState JSON을 MCP가 이해하는
.kis.yaml 포맷으로 변환한다. 변환된 YAML은 기존 run_custom_backtest()
경로로 실행된다.

extract_strategy_summary()는 YAML 문자열에서 지표/조건/리스크 요약을
추출하여 이력 테이블에 표시할 메타데이터를 생성한다.
"""

import re
import logging

import yaml

from services.exceptions import ServiceError

logger = logging.getLogger(__name__)


def convert_builder_to_yaml(builder_state: dict) -> str:
    """BuilderState -> .kis.yaml 문자열 변환."""
    errors = validate_builder_state(builder_state)
    if errors:
        raise ServiceError(f"빌더 상태 검증 실패: {'; '.join(errors)}")

    metadata = builder_state.get("metadata") or {}
    indicators = builder_state.get("indicators") or []
    entry_groups = builder_state.get("entryGroups") or []
    exit_groups = builder_state.get("exitGroups") or []
    risk = builder_state.get("risk") or {}

    # strategy ID 생성 (한글 제거, snake_case)
    name = metadata.get("name", "custom_strategy")
    strategy_id = _to_snake_case(name)

    # YAML 구조 생성
    doc = {
        "version": "1.0",
        "metadata": {"name": name},
        "strategy": {
            "id": strategy_id,
            "indicators": _convert_indicators(indicators),
            "entry": {"conditions": _convert_condition_groups(entry_groups)},
            "exit": {"conditions": _convert_condition_groups(exit_groups)},
        },
    }

    # risk 블록 (strategy 외부 — MCP 필수)
    doc["risk"] = _convert_risk(risk)

    return yaml.dump(
        doc, allow_unicode=True, default_flow_style=False, sort_keys=False,
    )


def extract_strategy_summary(yaml_content: str) -> dict:
    """YAML 문자열에서 전략 요약 정보를 추출.

    Returns:
        {
            "name": "전략명",
            "strategy_id": "snake_case_id",
            "indicators": [
                {"id": "sma", "alias": "sma_1", "params": {"period": 20}},
                ...
            ],
            "entry_count": 2,
            "exit_count": 1,
            "risk": {"stop_loss": 5.0, "take_profit": 10.0}  # enabled된 것만
        }

    실패 시 빈 딕셔너리 반환 (절대 에러 raise 안 함).
    """
    try:
        doc = yaml.safe_load(yaml_content)
        if not isinstance(doc, dict):
            return {}

        result = {}

        # metadata
        metadata = doc.get("metadata") or {}
        result["name"] = metadata.get("name", "")

        # strategy
        strategy = doc.get("strategy") or {}
        result["strategy_id"] = strategy.get("id", "")

        # indicators
        raw_indicators = strategy.get("indicators") or []
        indicators = []
        for ind in raw_indicators:
            item = {"id": ind.get("id", ""), "alias": ind.get("alias", "")}
            params = ind.get("params")
            if params:
                item["params"] = params
            indicators.append(item)
        result["indicators"] = indicators

        # entry/exit condition counts
        entry = strategy.get("entry") or {}
        exit_ = strategy.get("exit") or {}
        result["entry_count"] = len(entry.get("conditions") or [])
        result["exit_count"] = len(exit_.get("conditions") or [])

        # risk — enabled된 항목만 추출
        risk_block = doc.get("risk") or {}
        risk_summary = {}
        for key in ("stop_loss", "take_profit", "trailing_stop"):
            item = risk_block.get(key) or {}
            if item.get("enabled"):
                risk_summary[key] = item.get("percent")
        if risk_summary:
            result["risk"] = risk_summary

        return result
    except Exception as e:
        logger.debug("YAML 요약 추출 실패: %s", e)
        return {}


def validate_builder_state(builder_state: dict) -> list[str]:
    """빌더 상태 기본 검증. 에러 메시지 리스트 반환 (빈 리스트 = 통과)."""
    errors: list[str] = []

    metadata = builder_state.get("metadata") or {}
    if not metadata.get("name", "").strip():
        errors.append("전략명이 비어있습니다")

    indicators = builder_state.get("indicators") or []
    if not indicators:
        errors.append("지표를 최소 1개 이상 추가해야 합니다")

    # alias 중복 체크
    aliases = [ind.get("alias", "") for ind in indicators]
    if len(aliases) != len(set(aliases)):
        errors.append("지표 별칭(alias)이 중복됩니다")

    entry_groups = builder_state.get("entryGroups") or []
    has_entry = any(
        len(g.get("conditions") or []) > 0 for g in entry_groups
    )
    if not has_entry:
        errors.append("진입 조건을 최소 1개 이상 설정해야 합니다")

    exit_groups = builder_state.get("exitGroups") or []
    has_exit = any(
        len(g.get("conditions") or []) > 0 for g in exit_groups
    )
    if not has_exit:
        errors.append("청산 조건을 최소 1개 이상 설정해야 합니다")

    # 조건에서 참조하는 alias가 indicators에 존재하는지 확인
    alias_set = set(aliases)
    for groups, label in [(entry_groups, "진입"), (exit_groups, "청산")]:
        for g in groups:
            for cond in g.get("conditions") or []:
                for side in ["left", "right"]:
                    operand = cond.get(side) or {}
                    if operand.get("type") == "indicator":
                        ref_alias = operand.get("alias", "")
                        if ref_alias and ref_alias not in alias_set:
                            errors.append(
                                f"{label} 조건에서 존재하지 않는 지표 "
                                f"'{ref_alias}'를 참조합니다"
                            )

    return errors


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────


def _to_snake_case(name: str) -> str:
    """전략명 -> snake_case ID. 한글/특수문자 제거."""
    # 한글 제거
    ascii_only = re.sub(r'[^\x00-\x7F]+', '', name)
    # 특수문자 -> 공백
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', ascii_only)
    # 연속 공백 -> 단일
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if not cleaned:
        return "custom_strategy"
    # 공백 -> underscore, 소문자
    return cleaned.lower().replace(' ', '_')


def _convert_indicators(indicators: list) -> list:
    """BuilderState indicators -> YAML indicators 배열."""
    result = []
    for ind in indicators:
        item = {
            "id": ind["id"],
            "alias": ind["alias"],
        }
        params = ind.get("params", {})
        if params:
            item["params"] = params
        result.append(item)
    return result


def _convert_condition_groups(groups: list) -> list:
    """BuilderState 조건 그룹 -> YAML conditions 배열.

    단일 AND 그룹: conditions 배열 직접 반환
    복수 그룹: 각 그룹의 조건을 모두 평탄화 (MCP는 단일 conditions 배열)
    """
    conditions = []
    for group in groups:
        for cond in group.get("conditions", []):
            converted = _convert_single_condition(cond)
            if converted:
                conditions.append(converted)
    return conditions


def _convert_single_condition(cond: dict) -> dict | None:
    """개별 조건 -> YAML condition 딕셔너리."""
    left = cond.get("left", {})
    operator = cond.get("operator", "")
    right = cond.get("right", {})

    if not left or not operator or not right:
        return None

    result = {}

    # Left operand (항상 indicator 또는 price)
    if left.get("type") == "indicator":
        result["indicator"] = left["alias"]
        result["output"] = left.get("output", "value")
    elif left.get("type") == "price":
        result["indicator"] = "price"
        # 프론트엔드: {type:'price', field:'close'} 또는 {type:'price', value:'close'}
        result["output"] = left.get("field") or left.get("value", "close")
    else:
        return None

    result["operator"] = operator

    # Right operand
    if right.get("type") == "indicator":
        result["compare_to"] = right["alias"]
        result["compare_output"] = right.get("output", "value")
    elif right.get("type") == "price":
        result["compare_to"] = "price"
        result["compare_output"] = right.get("field") or right.get("value", "close")
    elif right.get("type") == "number":
        val = right.get("value")
        if val is not None:
            try:
                result["value"] = float(val)
            except (ValueError, TypeError):
                return None

    return result


def _convert_risk(risk: dict) -> dict:
    """BuilderState risk -> YAML risk 블록.

    MCP 서버는 risk 블록이 없으면 파싱 에러를 발생시키므로,
    항상 3개 항목을 포함한 risk 블록을 반환한다.
    """
    risk = risk or {}

    sl = risk.get("stopLoss") or {}
    tp = risk.get("takeProfit") or {}
    ts = risk.get("trailingStop") or {}

    return {
        "stop_loss": {
            "enabled": bool(sl.get("enabled")),
            "percent": sl.get("percent", 5.0),
        },
        "take_profit": {
            "enabled": bool(tp.get("enabled")),
            "percent": tp.get("percent", 10.0),
        },
        "trailing_stop": {
            "enabled": bool(ts.get("enabled")),
            "percent": ts.get("percent", 3.0),
        },
    }
