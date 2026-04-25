"""전략빌더 서비스 단위 테스트 — BuilderState → YAML 변환 검증.

다양한 전략 구성(단일지표, 복합조건, 리스크, 캔들패턴, 엣지케이스)에 대해
변환된 YAML이 MCP .kis.yaml 스펙에 부합하는지 확인한다.
"""

import pytest
import yaml

from services.strategy_builder_service import (
    convert_builder_to_yaml,
    validate_builder_state,
    extract_strategy_summary,
    _to_snake_case,
    _convert_indicators,
    _convert_single_condition,
    _convert_risk,
)
from services.exceptions import ServiceError


# ═══════════════════════════════════════════════════════════════════════════════
# 헬퍼: 최소 유효 BuilderState 생성
# ═══════════════════════════════════════════════════════════════════════════════

def _make_state(
    name="Test Strategy",
    indicators=None,
    entry_conditions=None,
    exit_conditions=None,
    risk=None,
):
    """테스트용 최소 유효 BuilderState 딕셔너리 생성."""
    if indicators is None:
        indicators = [{"id": "sma", "alias": "sma_1", "params": {"period": 20}}]
    if entry_conditions is None:
        entry_conditions = [{
            "left": {"type": "indicator", "alias": "sma_1", "output": "value"},
            "operator": "cross_above",
            "right": {"type": "price", "value": "close"},
        }]
    if exit_conditions is None:
        exit_conditions = [{
            "left": {"type": "indicator", "alias": "sma_1", "output": "value"},
            "operator": "cross_below",
            "right": {"type": "price", "value": "close"},
        }]
    return {
        "metadata": {"name": name},
        "indicators": indicators,
        "entryGroups": [{"operator": "AND", "conditions": entry_conditions}],
        "exitGroups": [{"operator": "AND", "conditions": exit_conditions}],
        "risk": risk or {},
    }


def _parse_yaml(yaml_str):
    """YAML 문자열 → 딕셔너리."""
    return yaml.safe_load(yaml_str)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. _to_snake_case 단위 테스트
# ═══════════════════════════════════════════════════════════════════════════════

class TestToSnakeCase:
    def test_english(self):
        assert _to_snake_case("Golden Cross Strategy") == "golden_cross_strategy"

    def test_korean_only(self):
        assert _to_snake_case("골든크로스") == "custom_strategy"

    def test_mixed_korean_english(self):
        assert _to_snake_case("My 골든크로스 Strategy") == "my_strategy"

    def test_special_chars(self):
        assert _to_snake_case("RSI + MACD (v2)") == "rsi_macd_v2"

    def test_empty(self):
        assert _to_snake_case("") == "custom_strategy"

    def test_numbers(self):
        assert _to_snake_case("SMA 5 20 Crossover") == "sma_5_20_crossover"

    def test_camel_case(self):
        # CamelCase → 전부 소문자
        assert _to_snake_case("GoldenCross") == "goldencross"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. validate_builder_state 검증 테스트
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateBuilderState:
    def test_valid_state(self):
        state = _make_state()
        errors = validate_builder_state(state)
        assert errors == []

    def test_empty_name(self):
        state = _make_state(name="")
        errors = validate_builder_state(state)
        assert any("전략명" in e for e in errors)

    def test_whitespace_name(self):
        state = _make_state(name="   ")
        errors = validate_builder_state(state)
        assert any("전략명" in e for e in errors)

    def test_no_indicators(self):
        state = _make_state(indicators=[])
        errors = validate_builder_state(state)
        assert any("지표" in e for e in errors)

    def test_duplicate_alias(self):
        inds = [
            {"id": "sma", "alias": "sma_1", "params": {"period": 5}},
            {"id": "sma", "alias": "sma_1", "params": {"period": 20}},
        ]
        state = _make_state(indicators=inds)
        errors = validate_builder_state(state)
        assert any("중복" in e for e in errors)

    def test_no_entry_conditions(self):
        state = _make_state(entry_conditions=[])
        # entryGroups는 있지만 conditions가 비어있음
        errors = validate_builder_state(state)
        assert any("진입" in e for e in errors)

    def test_no_exit_conditions(self):
        state = _make_state(exit_conditions=[])
        errors = validate_builder_state(state)
        assert any("청산" in e for e in errors)

    def test_dangling_alias_reference(self):
        """진입 조건에서 존재하지 않는 지표를 참조."""
        state = _make_state(
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "nonexistent", "output": "value"},
                "operator": "greater_than",
                "right": {"type": "number", "value": 70},
            }],
        )
        errors = validate_builder_state(state)
        assert any("nonexistent" in e for e in errors)

    def test_multiple_errors(self):
        """동시에 여러 검증 실패."""
        state = {
            "metadata": {"name": ""},
            "indicators": [],
            "entryGroups": [{"operator": "AND", "conditions": []}],
            "exitGroups": [{"operator": "AND", "conditions": []}],
            "risk": {},
        }
        errors = validate_builder_state(state)
        assert len(errors) >= 3  # 전략명 + 지표 + 진입조건(or 청산)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SMA 골든크로스 전략 — 가장 기본적인 시나리오
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoldenCrossStrategy:
    @pytest.fixture
    def state(self):
        return {
            "metadata": {"name": "Golden Cross", "description": "SMA 5/20 교차"},
            "indicators": [
                {"id": "sma", "alias": "sma_short", "params": {"period": 5}},
                {"id": "sma", "alias": "sma_long", "params": {"period": 20}},
            ],
            "entryGroups": [{"operator": "AND", "conditions": [{
                "left": {"type": "indicator", "alias": "sma_short", "output": "value"},
                "operator": "cross_above",
                "right": {"type": "indicator", "alias": "sma_long", "output": "value"},
            }]}],
            "exitGroups": [{"operator": "AND", "conditions": [{
                "left": {"type": "indicator", "alias": "sma_short", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "sma_long", "output": "value"},
            }]}],
            "risk": {
                "stopLoss": {"enabled": True, "percent": 5.0},
                "takeProfit": {"enabled": True, "percent": 10.0},
                "trailingStop": {"enabled": False, "percent": 3.0},
            },
        }

    def test_yaml_structure(self, state):
        result = convert_builder_to_yaml(state)
        doc = _parse_yaml(result)

        assert doc["version"] == "1.0"
        assert doc["metadata"]["name"] == "Golden Cross"
        assert doc["strategy"]["id"] == "golden_cross"

    def test_indicators(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        inds = doc["strategy"]["indicators"]
        assert len(inds) == 2
        assert inds[0]["id"] == "sma"
        assert inds[0]["alias"] == "sma_short"
        assert inds[0]["params"]["period"] == 5
        assert inds[1]["alias"] == "sma_long"
        assert inds[1]["params"]["period"] == 20

    def test_entry_condition(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        conds = doc["strategy"]["entry"]["conditions"]
        assert len(conds) == 1
        c = conds[0]
        assert c["indicator"] == "sma_short"
        assert c["output"] == "value"
        assert c["operator"] == "cross_above"
        assert c["compare_to"] == "sma_long"
        assert c["compare_output"] == "value"

    def test_exit_condition(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        conds = doc["strategy"]["exit"]["conditions"]
        assert len(conds) == 1
        assert conds[0]["operator"] == "cross_below"

    def test_risk_block(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        risk = doc["risk"]
        assert risk["stop_loss"]["enabled"] is True
        assert risk["stop_loss"]["percent"] == 5.0
        assert risk["take_profit"]["enabled"] is True
        assert risk["take_profit"]["percent"] == 10.0
        assert risk["trailing_stop"]["enabled"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RSI 과매도 반등 전략
# ═══════════════════════════════════════════════════════════════════════════════

class TestRsiOversoldStrategy:
    @pytest.fixture
    def state(self):
        return _make_state(
            name="RSI Oversold Bounce",
            indicators=[
                {"id": "rsi", "alias": "rsi_1", "params": {"period": 14}},
            ],
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "rsi_1", "output": "value"},
                "operator": "less_than",
                "right": {"type": "number", "value": 30},
            }],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "rsi_1", "output": "value"},
                "operator": "greater_than",
                "right": {"type": "number", "value": 70},
            }],
        )

    def test_entry_numeric_comparison(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][0]
        assert c["indicator"] == "rsi_1"
        assert c["operator"] == "less_than"
        assert c["value"] == 30.0
        assert "compare_to" not in c

    def test_exit_numeric_comparison(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["exit"]["conditions"][0]
        assert c["operator"] == "greater_than"
        assert c["value"] == 70.0

    def test_no_risk(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        # risk 블록은 항상 존재 (MCP 필수), 모두 disabled
        assert doc["risk"]["stop_loss"]["enabled"] is False
        assert doc["risk"]["take_profit"]["enabled"] is False
        assert doc["risk"]["trailing_stop"]["enabled"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MACD 골든크로스 전략 — 다중 출력 지표
# ═══════════════════════════════════════════════════════════════════════════════

class TestMacdStrategy:
    @pytest.fixture
    def state(self):
        return _make_state(
            name="MACD Golden Cross",
            indicators=[
                {"id": "macd", "alias": "macd_1", "params": {"fast": 12, "slow": 26, "signal": 9}},
            ],
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "macd_1", "output": "value"},
                "operator": "cross_above",
                "right": {"type": "indicator", "alias": "macd_1", "output": "signal"},
            }],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "macd_1", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "macd_1", "output": "signal"},
            }],
        )

    def test_macd_params(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        ind = doc["strategy"]["indicators"][0]
        assert ind["params"] == {"fast": 12, "slow": 26, "signal": 9}

    def test_same_alias_different_outputs(self, state):
        """같은 지표의 서로 다른 출력(value vs signal) 비교."""
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][0]
        assert c["indicator"] == "macd_1"
        assert c["output"] == "value"
        assert c["compare_to"] == "macd_1"
        assert c["compare_output"] == "signal"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. 볼린저밴드 전략 — 다중 출력 + 가격 비교
# ═══════════════════════════════════════════════════════════════════════════════

class TestBollingerStrategy:
    @pytest.fixture
    def state(self):
        return _make_state(
            name="Bollinger Squeeze",
            indicators=[
                {"id": "bollinger", "alias": "bb_1", "params": {"period": 20, "std_dev": 2}},
            ],
            entry_conditions=[{
                "left": {"type": "price", "value": "close"},
                "operator": "less_than",
                "right": {"type": "indicator", "alias": "bb_1", "output": "lower"},
            }],
            exit_conditions=[{
                "left": {"type": "price", "value": "close"},
                "operator": "greater_than",
                "right": {"type": "indicator", "alias": "bb_1", "output": "upper"},
            }],
        )

    def test_price_as_left_operand(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][0]
        assert c["indicator"] == "price"
        assert c["output"] == "close"
        assert c["compare_to"] == "bb_1"
        assert c["compare_output"] == "lower"

    def test_bollinger_outputs(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        exit_c = doc["strategy"]["exit"]["conditions"][0]
        assert exit_c["compare_output"] == "upper"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. 복합 조건 전략 — 여러 지표 AND 조건
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiConditionStrategy:
    @pytest.fixture
    def state(self):
        """ADX 추세 필터 + EMA 크로스 + RSI 과매도 (3개 AND 조건)."""
        return _make_state(
            name="ADX Trend Filter",
            indicators=[
                {"id": "adx", "alias": "adx_1", "params": {"period": 14}},
                {"id": "ema", "alias": "ema_short", "params": {"period": 10}},
                {"id": "ema", "alias": "ema_long", "params": {"period": 30}},
                {"id": "rsi", "alias": "rsi_1", "params": {"period": 14}},
            ],
            entry_conditions=[
                {
                    "left": {"type": "indicator", "alias": "adx_1", "output": "adx"},
                    "operator": "greater_than",
                    "right": {"type": "number", "value": 25},
                },
                {
                    "left": {"type": "indicator", "alias": "ema_short", "output": "value"},
                    "operator": "cross_above",
                    "right": {"type": "indicator", "alias": "ema_long", "output": "value"},
                },
                {
                    "left": {"type": "indicator", "alias": "rsi_1", "output": "value"},
                    "operator": "less_than",
                    "right": {"type": "number", "value": 70},
                },
            ],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "ema_short", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "ema_long", "output": "value"},
            }],
            risk={
                "stopLoss": {"enabled": True, "percent": 3.0},
                "takeProfit": {"enabled": True, "percent": 15.0},
                "trailingStop": {"enabled": True, "percent": 2.0},
            },
        )

    def test_three_entry_conditions(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        conds = doc["strategy"]["entry"]["conditions"]
        assert len(conds) == 3

    def test_adx_output_field(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][0]
        assert c["indicator"] == "adx_1"
        assert c["output"] == "adx"
        assert c["value"] == 25.0

    def test_four_indicators(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert len(doc["strategy"]["indicators"]) == 4

    def test_all_three_risk_enabled(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        risk = doc["risk"]
        assert "stop_loss" in risk
        assert "take_profit" in risk
        assert "trailing_stop" in risk
        assert risk["trailing_stop"]["percent"] == 2.0


# ═══════════════════════════════════════════════════════════════════════════════
# 8. 복수 조건 그룹 (OR 결합)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultipleGroups:
    @pytest.fixture
    def state(self):
        """2개 그룹: (RSI 과매도) OR (SMA 골든크로스)."""
        return {
            "metadata": {"name": "Multi Group OR"},
            "indicators": [
                {"id": "rsi", "alias": "rsi_1", "params": {"period": 14}},
                {"id": "sma", "alias": "sma_5", "params": {"period": 5}},
                {"id": "sma", "alias": "sma_20", "params": {"period": 20}},
            ],
            "entryGroups": [
                {"operator": "AND", "conditions": [{
                    "left": {"type": "indicator", "alias": "rsi_1", "output": "value"},
                    "operator": "less_than",
                    "right": {"type": "number", "value": 30},
                }]},
                {"operator": "AND", "conditions": [{
                    "left": {"type": "indicator", "alias": "sma_5", "output": "value"},
                    "operator": "cross_above",
                    "right": {"type": "indicator", "alias": "sma_20", "output": "value"},
                }]},
            ],
            "exitGroups": [{"operator": "AND", "conditions": [{
                "left": {"type": "indicator", "alias": "rsi_1", "output": "value"},
                "operator": "greater_than",
                "right": {"type": "number", "value": 70},
            }]}],
            "risk": {},
        }

    def test_groups_flattened(self, state):
        """복수 그룹의 조건이 하나의 conditions 배열로 평탄화."""
        doc = _parse_yaml(convert_builder_to_yaml(state))
        conds = doc["strategy"]["entry"]["conditions"]
        assert len(conds) == 2

    def test_first_condition_rsi(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][0]
        assert c["indicator"] == "rsi_1"
        assert c["value"] == 30.0

    def test_second_condition_sma_cross(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][1]
        assert c["indicator"] == "sma_5"
        assert c["compare_to"] == "sma_20"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. 스토캐스틱 전략 — 다중 출력 (k, d)
# ═══════════════════════════════════════════════════════════════════════════════

class TestStochasticStrategy:
    @pytest.fixture
    def state(self):
        return _make_state(
            name="Stochastic KD Cross",
            indicators=[
                {"id": "stochastic", "alias": "stoch_1", "params": {"k_period": 14, "d_period": 3, "smooth_k": 3}},
            ],
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "stoch_1", "output": "k"},
                "operator": "cross_above",
                "right": {"type": "indicator", "alias": "stoch_1", "output": "d"},
            }],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "stoch_1", "output": "k"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "stoch_1", "output": "d"},
            }],
        )

    def test_stochastic_outputs(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][0]
        assert c["output"] == "k"
        assert c["compare_output"] == "d"

    def test_stochastic_params(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        params = doc["strategy"]["indicators"][0]["params"]
        assert params["k_period"] == 14
        assert params["d_period"] == 3
        assert params["smooth_k"] == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 10. ATR 변동성 돌파 전략 — 가격 + 지표 혼합
# ═══════════════════════════════════════════════════════════════════════════════

class TestAtrBreakoutStrategy:
    @pytest.fixture
    def state(self):
        return _make_state(
            name="ATR Breakout",
            indicators=[
                {"id": "atr", "alias": "atr_1", "params": {"period": 14}},
                {"id": "sma", "alias": "sma_20", "params": {"period": 20}},
            ],
            entry_conditions=[
                {
                    "left": {"type": "price", "value": "close"},
                    "operator": "greater_than",
                    "right": {"type": "indicator", "alias": "sma_20", "output": "value"},
                },
                {
                    "left": {"type": "indicator", "alias": "atr_1", "output": "value"},
                    "operator": "greater_than",
                    "right": {"type": "number", "value": 1000},
                },
            ],
            exit_conditions=[{
                "left": {"type": "price", "value": "close"},
                "operator": "less_than",
                "right": {"type": "indicator", "alias": "sma_20", "output": "value"},
            }],
        )

    def test_price_vs_indicator(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][0]
        assert c["indicator"] == "price"
        assert c["output"] == "close"
        assert c["compare_to"] == "sma_20"

    def test_indicator_vs_number(self, state):
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][1]
        assert c["indicator"] == "atr_1"
        assert c["value"] == 1000.0


# ═══════════════════════════════════════════════════════════════════════════════
# 11. 이격도(Disparity) + OBV 전략 — 추세 + 거래량 결합
# ═══════════════════════════════════════════════════════════════════════════════

class TestDisparityObvStrategy:
    @pytest.fixture
    def state(self):
        return _make_state(
            name="Disparity OBV",
            indicators=[
                {"id": "disparity", "alias": "disp_1", "params": {"period": 20}},
                {"id": "obv", "alias": "obv_1", "params": {}},
                {"id": "sma", "alias": "obv_ma", "params": {"period": 20}},
            ],
            entry_conditions=[
                {
                    "left": {"type": "indicator", "alias": "disp_1", "output": "value"},
                    "operator": "less_than",
                    "right": {"type": "number", "value": -5},
                },
            ],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "disp_1", "output": "value"},
                "operator": "greater_than",
                "right": {"type": "number", "value": 5},
            }],
        )

    def test_no_params_indicator(self, state):
        """OBV처럼 params가 빈 지표."""
        doc = _parse_yaml(convert_builder_to_yaml(state))
        obv = [i for i in doc["strategy"]["indicators"] if i["id"] == "obv"][0]
        assert "params" not in obv

    def test_negative_number_value(self, state):
        """음수 값 비교."""
        doc = _parse_yaml(convert_builder_to_yaml(state))
        c = doc["strategy"]["entry"]["conditions"][0]
        assert c["value"] == -5.0


# ═══════════════════════════════════════════════════════════════════════════════
# 12. 모든 연산자 테스트
# ═══════════════════════════════════════════════════════════════════════════════

class TestAllOperators:
    OPERATORS = [
        "greater_than", "less_than", "cross_above", "cross_below",
        "equals", "not_equal", "breaks",
    ]

    @pytest.mark.parametrize("op", OPERATORS)
    def test_operator_preserved(self, op):
        state = _make_state(
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "sma_1", "output": "value"},
                "operator": op,
                "right": {"type": "number", "value": 50},
            }],
        )
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["strategy"]["entry"]["conditions"][0]["operator"] == op


# ═══════════════════════════════════════════════════════════════════════════════
# 13. 리스크 관리 조합 테스트
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskCombinations:
    def test_no_risk(self):
        state = _make_state(risk={})
        doc = _parse_yaml(convert_builder_to_yaml(state))
        # risk 블록은 항상 존재 (MCP 필수), 모두 disabled
        assert doc["risk"]["stop_loss"]["enabled"] is False
        assert doc["risk"]["take_profit"]["enabled"] is False
        assert doc["risk"]["trailing_stop"]["enabled"] is False

    def test_all_disabled(self):
        state = _make_state(risk={
            "stopLoss": {"enabled": False, "percent": 5.0},
            "takeProfit": {"enabled": False, "percent": 10.0},
            "trailingStop": {"enabled": False, "percent": 3.0},
        })
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["risk"]["stop_loss"]["enabled"] is False
        assert doc["risk"]["take_profit"]["enabled"] is False
        assert doc["risk"]["trailing_stop"]["enabled"] is False

    def test_only_stop_loss(self):
        state = _make_state(risk={
            "stopLoss": {"enabled": True, "percent": 3.5},
        })
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["risk"]["stop_loss"]["enabled"] is True
        assert doc["risk"]["stop_loss"]["percent"] == 3.5
        assert doc["risk"]["take_profit"]["enabled"] is False
        assert doc["risk"]["trailing_stop"]["enabled"] is False

    def test_only_trailing_stop(self):
        state = _make_state(risk={
            "trailingStop": {"enabled": True, "percent": 2.0},
        })
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["risk"]["trailing_stop"]["enabled"] is True
        assert doc["risk"]["trailing_stop"]["percent"] == 2.0

    def test_risk_default_values(self):
        """percent 미지정 시 기본값."""
        state = _make_state(risk={
            "stopLoss": {"enabled": True},
        })
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["risk"]["stop_loss"]["percent"] == 5.0  # 기본값


# ═══════════════════════════════════════════════════════════════════════════════
# 14. _convert_single_condition 엣지케이스
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvertSingleCondition:
    def test_empty_condition(self):
        assert _convert_single_condition({}) is None

    def test_missing_operator(self):
        assert _convert_single_condition({
            "left": {"type": "indicator", "alias": "a", "output": "value"},
            "right": {"type": "number", "value": 10},
        }) is None

    def test_missing_right(self):
        assert _convert_single_condition({
            "left": {"type": "indicator", "alias": "a", "output": "value"},
            "operator": "greater_than",
        }) is None

    def test_unknown_left_type(self):
        """left 타입이 indicator/price 이외인 경우."""
        result = _convert_single_condition({
            "left": {"type": "unknown", "value": "x"},
            "operator": "greater_than",
            "right": {"type": "number", "value": 10},
        })
        assert result is None

    def test_number_value_as_string(self):
        """숫자가 문자열로 전달된 경우 → float 변환."""
        result = _convert_single_condition({
            "left": {"type": "indicator", "alias": "rsi", "output": "value"},
            "operator": "less_than",
            "right": {"type": "number", "value": "30"},
        })
        assert result["value"] == 30.0

    def test_number_value_invalid(self):
        """변환 불가능한 숫자 → None 반환."""
        result = _convert_single_condition({
            "left": {"type": "indicator", "alias": "rsi", "output": "value"},
            "operator": "less_than",
            "right": {"type": "number", "value": "abc"},
        })
        assert result is None

    def test_default_output(self):
        """output 미지정 시 기본값 'value'."""
        result = _convert_single_condition({
            "left": {"type": "indicator", "alias": "sma_1"},
            "operator": "greater_than",
            "right": {"type": "number", "value": 100},
        })
        assert result["output"] == "value"

    def test_price_fields(self):
        """다양한 가격 필드 (open, high, low)."""
        for field in ["open", "high", "low", "volume"]:
            result = _convert_single_condition({
                "left": {"type": "price", "value": field},
                "operator": "greater_than",
                "right": {"type": "number", "value": 100},
            })
            assert result["output"] == field

    def test_price_right_operand(self):
        """오른쪽 피연산자가 price인 경우."""
        result = _convert_single_condition({
            "left": {"type": "indicator", "alias": "sma_1", "output": "value"},
            "operator": "greater_than",
            "right": {"type": "price", "value": "high"},
        })
        assert result["compare_to"] == "price"
        assert result["compare_output"] == "high"

    def test_price_field_key(self):
        """프론트엔드 OperandSelector는 'field' 키를 사용."""
        result = _convert_single_condition({
            "left": {"type": "price", "field": "close"},
            "operator": "greater_than",
            "right": {"type": "indicator", "alias": "sma_1", "output": "value"},
        })
        assert result["indicator"] == "price"
        assert result["output"] == "close"

    def test_price_field_right(self):
        """오른쪽 price 피연산자도 'field' 키 지원."""
        result = _convert_single_condition({
            "left": {"type": "indicator", "alias": "sma_1", "output": "value"},
            "operator": "less_than",
            "right": {"type": "price", "field": "low"},
        })
        assert result["compare_to"] == "price"
        assert result["compare_output"] == "low"


# ═══════════════════════════════════════════════════════════════════════════════
# 15. _convert_indicators 엣지케이스
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvertIndicators:
    def test_empty_params(self):
        result = _convert_indicators([{"id": "obv", "alias": "obv_1", "params": {}}])
        assert len(result) == 1
        assert "params" not in result[0]

    def test_no_params_key(self):
        result = _convert_indicators([{"id": "ibs", "alias": "ibs_1"}])
        assert len(result) == 1
        assert "params" not in result[0]


# ═══════════════════════════════════════════════════════════════════════════════
# 16. convert_builder_to_yaml 검증 실패 시 ServiceError
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvertValidationError:
    def test_raises_service_error(self):
        """검증 실패 시 ServiceError 발생."""
        with pytest.raises(ServiceError) as exc_info:
            convert_builder_to_yaml({
                "metadata": {"name": ""},
                "indicators": [],
                "entryGroups": [],
                "exitGroups": [],
                "risk": {},
            })
        assert "검증 실패" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# 16-b. None 필드 방어 테스트 (500 에러 회귀 방지)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNullFieldDefense:
    """프론트엔드에서 None/null이 전달될 때 500 대신 ServiceError(400) 발생."""

    def test_null_indicators(self):
        with pytest.raises(ServiceError):
            convert_builder_to_yaml({
                "metadata": {"name": "X"},
                "indicators": None,
                "entryGroups": [{"operator": "AND", "conditions": []}],
                "exitGroups": [{"operator": "AND", "conditions": []}],
                "risk": {},
            })

    def test_null_entry_groups(self):
        with pytest.raises(ServiceError):
            convert_builder_to_yaml({
                "metadata": {"name": "X"},
                "indicators": [{"id": "sma", "alias": "sma_1", "params": {"period": 20}}],
                "entryGroups": None,
                "exitGroups": [{"operator": "AND", "conditions": [{"left": {"type": "indicator", "alias": "sma_1", "output": "value"}, "operator": "cross_above", "right": {"type": "price", "field": "close"}}]}],
                "risk": {},
            })

    def test_null_exit_groups(self):
        with pytest.raises(ServiceError):
            convert_builder_to_yaml({
                "metadata": {"name": "X"},
                "indicators": [{"id": "sma", "alias": "sma_1", "params": {"period": 20}}],
                "entryGroups": [{"operator": "AND", "conditions": [{"left": {"type": "indicator", "alias": "sma_1", "output": "value"}, "operator": "cross_above", "right": {"type": "price", "field": "close"}}]}],
                "exitGroups": None,
                "risk": {},
            })

    def test_null_risk(self):
        """risk가 None이어도 기본 risk 블록 포함 (MCP 필수)."""
        state = _make_state(risk=None)
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["risk"]["stop_loss"]["enabled"] is False
        assert doc["risk"]["take_profit"]["enabled"] is False
        assert doc["risk"]["trailing_stop"]["enabled"] is False

    def test_null_metadata(self):
        with pytest.raises(ServiceError):
            convert_builder_to_yaml({
                "metadata": None,
                "indicators": [],
                "entryGroups": [],
                "exitGroups": [],
                "risk": {},
            })

    def test_all_fields_null(self):
        with pytest.raises(ServiceError):
            convert_builder_to_yaml({
                "metadata": None,
                "indicators": None,
                "entryGroups": None,
                "exitGroups": None,
                "risk": None,
            })

    def test_completely_empty_dict(self):
        with pytest.raises(ServiceError):
            convert_builder_to_yaml({})

    def test_null_conditions_in_group(self):
        """그룹 내 conditions가 None."""
        with pytest.raises(ServiceError):
            convert_builder_to_yaml({
                "metadata": {"name": "X"},
                "indicators": [{"id": "sma", "alias": "sma_1", "params": {"period": 20}}],
                "entryGroups": [{"operator": "AND", "conditions": None}],
                "exitGroups": [{"operator": "AND", "conditions": [{"left": {"type": "indicator", "alias": "sma_1", "output": "value"}, "operator": "cross_above", "right": {"type": "price", "field": "close"}}]}],
                "risk": {},
            })


# ═══════════════════════════════════════════════════════════════════════════════
# 17. YAML 포맷 무결성 테스트
# ═══════════════════════════════════════════════════════════════════════════════

class TestYamlFormatIntegrity:
    def test_yaml_is_valid(self):
        """생성된 YAML이 파싱 가능한지 확인."""
        state = _make_state()
        result = convert_builder_to_yaml(state)
        doc = _parse_yaml(result)
        assert isinstance(doc, dict)

    def test_version_field(self):
        state = _make_state()
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["version"] == "1.0"

    def test_strategy_id_is_string(self):
        state = _make_state()
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert isinstance(doc["strategy"]["id"], str)

    def test_conditions_are_lists(self):
        state = _make_state()
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert isinstance(doc["strategy"]["entry"]["conditions"], list)
        assert isinstance(doc["strategy"]["exit"]["conditions"], list)

    def test_unicode_name_preserved(self):
        """한글 전략명이 metadata에 보존."""
        state = _make_state(name="골든크로스 전략")
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["metadata"]["name"] == "골든크로스 전략"

    def test_required_top_level_keys(self):
        """MCP 필수 최상위 키 존재 확인."""
        state = _make_state()
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert "version" in doc
        assert "metadata" in doc
        assert "strategy" in doc

    def test_required_strategy_keys(self):
        """strategy 블록 필수 키 확인."""
        state = _make_state()
        doc = _parse_yaml(convert_builder_to_yaml(state))
        s = doc["strategy"]
        assert "id" in s
        assert "indicators" in s
        assert "entry" in s
        assert "exit" in s


# ═══════════════════════════════════════════════════════════════════════════════
# 18. 프리셋 빌더 상태 변환 테스트 (프론트엔드 BUILDER_PRESETS 시뮬레이션)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuilderPresets:
    """프론트엔드 BUILDER_PRESETS에 정의된 6개 프리셋 구조를 시뮬레이션."""

    def test_golden_cross_preset(self):
        state = {
            "metadata": {"name": "골든크로스", "category": "trend", "tags": ["이동평균"]},
            "indicators": [
                {"id": "sma", "alias": "sma_short", "params": {"period": 5}},
                {"id": "sma", "alias": "sma_long", "params": {"period": 20}},
            ],
            "entryGroups": [{"operator": "AND", "conditions": [{
                "left": {"type": "indicator", "alias": "sma_short", "output": "value"},
                "operator": "cross_above",
                "right": {"type": "indicator", "alias": "sma_long", "output": "value"},
            }]}],
            "exitGroups": [{"operator": "AND", "conditions": [{
                "left": {"type": "indicator", "alias": "sma_short", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "sma_long", "output": "value"},
            }]}],
            "risk": {"stopLoss": {"enabled": True, "percent": 5}, "takeProfit": {"enabled": True, "percent": 10}, "trailingStop": {"enabled": False, "percent": 3}},
        }
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert len(doc["strategy"]["indicators"]) == 2
        assert doc["strategy"]["entry"]["conditions"][0]["operator"] == "cross_above"

    def test_rsi_oversold_preset(self):
        state = _make_state(
            name="RSI Oversold",
            indicators=[{"id": "rsi", "alias": "rsi_1", "params": {"period": 14}}],
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "rsi_1", "output": "value"},
                "operator": "cross_above",
                "right": {"type": "number", "value": 30},
            }],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "rsi_1", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "number", "value": 70},
            }],
            risk={"stopLoss": {"enabled": True, "percent": 7}},
        )
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["risk"]["stop_loss"]["percent"] == 7

    def test_macd_preset(self):
        state = _make_state(
            name="MACD Cross",
            indicators=[{"id": "macd", "alias": "macd_1", "params": {"fast": 12, "slow": 26, "signal": 9}}],
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "macd_1", "output": "value"},
                "operator": "cross_above",
                "right": {"type": "indicator", "alias": "macd_1", "output": "signal"},
            }],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "macd_1", "output": "histogram"},
                "operator": "less_than",
                "right": {"type": "number", "value": 0},
            }],
        )
        doc = _parse_yaml(convert_builder_to_yaml(state))
        # histogram 출력 검증
        exit_c = doc["strategy"]["exit"]["conditions"][0]
        assert exit_c["output"] == "histogram"
        assert exit_c["value"] == 0.0

    def test_bollinger_preset(self):
        state = _make_state(
            name="BB Bounce",
            indicators=[{"id": "bollinger", "alias": "bb_1", "params": {"period": 20, "std_dev": 2}}],
            entry_conditions=[{
                "left": {"type": "price", "value": "close"},
                "operator": "breaks",
                "right": {"type": "indicator", "alias": "bb_1", "output": "lower"},
            }],
            exit_conditions=[{
                "left": {"type": "price", "value": "close"},
                "operator": "greater_than",
                "right": {"type": "indicator", "alias": "bb_1", "output": "middle"},
            }],
        )
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["strategy"]["entry"]["conditions"][0]["operator"] == "breaks"

    def test_trend_filter_preset(self):
        state = _make_state(
            name="Trend Filter",
            indicators=[
                {"id": "adx", "alias": "adx_1", "params": {"period": 14}},
                {"id": "ema", "alias": "ema_10", "params": {"period": 10}},
                {"id": "ema", "alias": "ema_30", "params": {"period": 30}},
            ],
            entry_conditions=[
                {
                    "left": {"type": "indicator", "alias": "adx_1", "output": "adx"},
                    "operator": "greater_than",
                    "right": {"type": "number", "value": 25},
                },
                {
                    "left": {"type": "indicator", "alias": "ema_10", "output": "value"},
                    "operator": "cross_above",
                    "right": {"type": "indicator", "alias": "ema_30", "output": "value"},
                },
            ],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "ema_10", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "ema_30", "output": "value"},
            }],
        )
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert len(doc["strategy"]["entry"]["conditions"]) == 2
        assert doc["strategy"]["indicators"][0]["params"]["period"] == 14

    def test_volatility_breakout_preset(self):
        state = _make_state(
            name="Volatility Breakout",
            indicators=[
                {"id": "atr", "alias": "atr_1", "params": {"period": 14}},
                {"id": "sma", "alias": "sma_20", "params": {"period": 20}},
            ],
            entry_conditions=[{
                "left": {"type": "price", "value": "high"},
                "operator": "greater_than",
                "right": {"type": "indicator", "alias": "sma_20", "output": "value"},
            }],
            exit_conditions=[{
                "left": {"type": "price", "value": "close"},
                "operator": "less_than",
                "right": {"type": "indicator", "alias": "sma_20", "output": "value"},
            }],
            risk={
                "stopLoss": {"enabled": True, "percent": 3},
                "trailingStop": {"enabled": True, "percent": 2},
            },
        )
        doc = _parse_yaml(convert_builder_to_yaml(state))
        assert doc["strategy"]["entry"]["conditions"][0]["output"] == "high"
        assert doc["risk"]["stop_loss"]["percent"] == 3
        assert doc["risk"]["trailing_stop"]["percent"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 19. extract_strategy_summary 테스트
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractStrategySummary:
    def test_full_yaml(self):
        """정상 YAML에서 전체 요약 추출."""
        state = _make_state(
            name="Golden Cross",
            indicators=[
                {"id": "sma", "alias": "sma_short", "params": {"period": 5}},
                {"id": "sma", "alias": "sma_long", "params": {"period": 20}},
            ],
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "sma_short", "output": "value"},
                "operator": "cross_above",
                "right": {"type": "indicator", "alias": "sma_long", "output": "value"},
            }],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "sma_short", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "sma_long", "output": "value"},
            }],
            risk={
                "stopLoss": {"enabled": True, "percent": 5.0},
                "takeProfit": {"enabled": True, "percent": 10.0},
                "trailingStop": {"enabled": False, "percent": 3.0},
            },
        )
        yaml_str = convert_builder_to_yaml(state)
        summary = extract_strategy_summary(yaml_str)

        assert summary["name"] == "Golden Cross"
        assert summary["strategy_id"] == "golden_cross"
        assert len(summary["indicators"]) == 2
        assert summary["indicators"][0]["id"] == "sma"
        assert summary["indicators"][0]["params"]["period"] == 5
        assert summary["entry_count"] == 1
        assert summary["exit_count"] == 1
        assert summary["risk"]["stop_loss"] == 5.0
        assert summary["risk"]["take_profit"] == 10.0
        assert "trailing_stop" not in summary["risk"]

    def test_no_risk_enabled(self):
        """모든 리스크 비활성 → risk 키 없음."""
        state = _make_state(risk={})
        yaml_str = convert_builder_to_yaml(state)
        summary = extract_strategy_summary(yaml_str)
        assert "risk" not in summary

    def test_invalid_yaml(self):
        """잘못된 YAML → 빈 딕셔너리 반환 (에러 없음)."""
        assert extract_strategy_summary("not: [valid: yaml: {{{") == {}

    def test_empty_string(self):
        assert extract_strategy_summary("") == {}

    def test_non_dict_yaml(self):
        """리스트 YAML → 빈 딕셔너리."""
        assert extract_strategy_summary("- item1\n- item2") == {}

    def test_roundtrip(self):
        """BuilderState → YAML → extract_summary → 원본과 일치."""
        state = _make_state(
            name="MACD Cross",
            indicators=[
                {"id": "macd", "alias": "macd_1", "params": {"fast": 12, "slow": 26, "signal": 9}},
            ],
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "macd_1", "output": "value"},
                "operator": "cross_above",
                "right": {"type": "indicator", "alias": "macd_1", "output": "signal"},
            }],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "macd_1", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "macd_1", "output": "signal"},
            }],
        )
        yaml_str = convert_builder_to_yaml(state)
        summary = extract_strategy_summary(yaml_str)

        assert summary["indicators"][0]["params"]["fast"] == 12
        assert summary["entry_count"] == 1
        assert summary["exit_count"] == 1

    def test_summary_values_are_serializable(self):
        """요약 결과의 모든 값이 JSON 직렬화 가능 (React 렌더링 호환).

        React error #31 회귀 방지: indicators 등 객체가 JSX에 직접
        렌더링되면 에러가 발생하므로, 요약 값의 타입을 검증한다.
        """
        state = _make_state(
            name="Render Test",
            indicators=[
                {"id": "sma", "alias": "sma_1", "params": {"period": 5}},
                {"id": "macd", "alias": "macd_1", "params": {"fast": 12, "slow": 26, "signal": 9}},
            ],
            entry_conditions=[{
                "left": {"type": "indicator", "alias": "sma_1", "output": "value"},
                "operator": "cross_above",
                "right": {"type": "indicator", "alias": "macd_1", "output": "signal"},
            }],
            exit_conditions=[{
                "left": {"type": "indicator", "alias": "sma_1", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "macd_1", "output": "signal"},
            }],
            risk={"stopLoss": {"enabled": True, "percent": 5.0}},
        )
        yaml_str = convert_builder_to_yaml(state)
        summary = extract_strategy_summary(yaml_str)

        # indicators는 리스트여야 함
        assert isinstance(summary["indicators"], list)
        for ind in summary["indicators"]:
            assert isinstance(ind, dict)
            assert isinstance(ind["id"], str)
            assert isinstance(ind["alias"], str)
            # params의 값은 모두 숫자/문자열 (객체 아님)
            for pv in (ind.get("params") or {}).values():
                assert isinstance(pv, (int, float, str)), f"param value {pv} is {type(pv)}"

        # entry_count/exit_count는 정수
        assert isinstance(summary["entry_count"], int)
        assert isinstance(summary["exit_count"], int)

        # risk의 값은 숫자
        if "risk" in summary:
            for rv in summary["risk"].values():
                assert isinstance(rv, (int, float)), f"risk value {rv} is {type(rv)}"
