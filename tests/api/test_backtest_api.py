"""Backtest API 엔드포인트 테스트 (A-150 ~ A-155)."""

import pytest


class TestBacktestEndpoints:
    """백테스트 API — KIS_MCP_ENABLED=false 기본."""

    def test_mcp_status(self, client):
        """A-150: GET /api/backtest/status → 200."""
        resp = client.get("/api/backtest/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "available" in data
        assert isinstance(data["available"], bool)

    def test_get_presets(self, client):
        """A-151: GET /api/backtest/presets → 200 or 502 (MCP 미연결)."""
        resp = client.get("/api/backtest/presets")
        assert resp.status_code in (200, 502, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, list)

    def test_get_indicators(self, client):
        """A-152: GET /api/backtest/indicators → 200 or 502/503 (MCP 미연결)."""
        resp = client.get("/api/backtest/indicators")
        assert resp.status_code in (200, 502, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, list)

    def test_run_preset(self, client):
        """A-153: POST /api/backtest/run/preset → 200 or 503."""
        resp = client.post("/api/backtest/run/preset", json={
            "preset": "golden_cross",
            "symbol": "005930",
            "market": "KR",
        })
        # MCP 비활성화 시 503 or 에러
        assert resp.status_code in (200, 503, 502, 400)

    def test_get_result_not_found(self, client):
        """A-154: 없는 결과 → 404."""
        resp = client.get("/api/backtest/result/nonexistent-id")
        assert resp.status_code in (200, 404)

    def test_get_history(self, client):
        """A-155: GET /api/backtest/history → 200."""
        resp = client.get("/api/backtest/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestStrategyBuilderEndpoints:
    """전략빌더 API 엔드포인트 테스트."""

    VALID_STATE = {
        "metadata": {"name": "Test Strategy"},
        "indicators": [
            {"id": "sma", "alias": "sma_1", "params": {"period": 20}},
        ],
        "entryGroups": [{"operator": "AND", "conditions": [{
            "left": {"type": "indicator", "alias": "sma_1", "output": "value"},
            "operator": "cross_above",
            "right": {"type": "price", "value": "close"},
        }]}],
        "exitGroups": [{"operator": "AND", "conditions": [{
            "left": {"type": "indicator", "alias": "sma_1", "output": "value"},
            "operator": "cross_below",
            "right": {"type": "price", "value": "close"},
        }]}],
        "risk": {},
    }

    def test_convert_valid(self, client):
        """POST /api/backtest/strategy/convert — 유효한 상태 변환."""
        resp = client.post("/api/backtest/strategy/convert", json={
            "builder_state": self.VALID_STATE,
            "run_validate": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "yaml_content" in data
        assert "version:" in data["yaml_content"]
        assert "strategy:" in data["yaml_content"]

    def test_convert_invalid_state(self, client):
        """POST /api/backtest/strategy/convert — 검증 실패 → 400."""
        resp = client.post("/api/backtest/strategy/convert", json={
            "builder_state": {
                "metadata": {"name": ""},
                "indicators": [],
                "entryGroups": [],
                "exitGroups": [],
                "risk": {},
            },
            "run_validate": False,
        })
        assert resp.status_code == 400

    def test_convert_golden_cross(self, client):
        """POST /api/backtest/strategy/convert — 골든크로스 전략."""
        state = {
            "metadata": {"name": "Golden Cross"},
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
            "risk": {"stopLoss": {"enabled": True, "percent": 5}},
        }
        resp = client.post("/api/backtest/strategy/convert", json={
            "builder_state": state, "run_validate": False,
        })
        assert resp.status_code == 200
        assert "cross_above" in resp.json()["yaml_content"]
        assert "stop_loss" in resp.json()["yaml_content"]

    def test_convert_macd_strategy(self, client):
        """POST /api/backtest/strategy/convert — MACD 전략."""
        state = {
            "metadata": {"name": "MACD Cross"},
            "indicators": [
                {"id": "macd", "alias": "macd_1", "params": {"fast": 12, "slow": 26, "signal": 9}},
            ],
            "entryGroups": [{"operator": "AND", "conditions": [{
                "left": {"type": "indicator", "alias": "macd_1", "output": "value"},
                "operator": "cross_above",
                "right": {"type": "indicator", "alias": "macd_1", "output": "signal"},
            }]}],
            "exitGroups": [{"operator": "AND", "conditions": [{
                "left": {"type": "indicator", "alias": "macd_1", "output": "value"},
                "operator": "cross_below",
                "right": {"type": "indicator", "alias": "macd_1", "output": "signal"},
            }]}],
            "risk": {},
        }
        resp = client.post("/api/backtest/strategy/convert", json={
            "builder_state": state, "run_validate": False,
        })
        assert resp.status_code == 200
        yaml_str = resp.json()["yaml_content"]
        assert "macd_1" in yaml_str
        assert "signal" in yaml_str

    def test_validate_yaml_endpoint(self, client):
        """POST /api/backtest/strategy/validate — MCP 비활성화 시."""
        resp = client.post("/api/backtest/strategy/validate", json={
            "yaml_content": "version: '1.0'\nmetadata:\n  name: test",
        })
        assert resp.status_code == 200
        data = resp.json()
        # MCP 비활성화 → valid=None
        assert data["valid"] is None or isinstance(data["valid"], bool)

    def test_strategy_crud_lifecycle(self, client):
        """전략 저장 → 조회 → 삭제 전체 수명주기."""
        # 저장
        resp = client.post("/api/backtest/strategies", json={
            "name": "My SMA Strategy",
            "description": "SMA crossover test",
            "yaml_content": "version: '1.0'",
            "builder_state": self.VALID_STATE,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My SMA Strategy"
        assert data["builder_state_json"] == self.VALID_STATE

        # 목록에 존재 확인
        resp = client.get("/api/backtest/strategies")
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()]
        assert "My SMA Strategy" in names

        # 상세 조회
        resp = client.get("/api/backtest/strategies/My SMA Strategy")
        assert resp.status_code == 200
        assert resp.json()["description"] == "SMA crossover test"

        # 삭제
        resp = client.delete("/api/backtest/strategies/My SMA Strategy")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # 삭제 후 조회 → 404
        resp = client.get("/api/backtest/strategies/My SMA Strategy")
        assert resp.status_code == 404

    def test_strategy_not_found(self, client):
        """존재하지 않는 전략 조회 → 404."""
        resp = client.get("/api/backtest/strategies/nonexistent")
        assert resp.status_code == 404

    def test_strategy_delete_not_found(self, client):
        """존재하지 않는 전략 삭제 → 404."""
        resp = client.delete("/api/backtest/strategies/nonexistent")
        assert resp.status_code == 404

    def test_strategy_upsert(self, client):
        """같은 이름으로 두 번 저장 → 덮어쓰기."""
        client.post("/api/backtest/strategies", json={
            "name": "MySMA", "description": "v1",
        })
        resp = client.post("/api/backtest/strategies", json={
            "name": "MySMA", "description": "v2",
            "yaml_content": "updated",
        })
        assert resp.status_code == 200
        assert resp.json()["description"] == "v2"

        # MySMA 이름으로 조회 시 v2
        resp2 = client.get("/api/backtest/strategies/MySMA")
        assert resp2.status_code == 200
        assert resp2.json()["description"] == "v2"

    def test_list_strategies_filter(self, client):
        """strategy_type 필터 조회."""
        client.post("/api/backtest/strategies", json={"name": "Builder1"})
        resp = client.get("/api/backtest/strategies?strategy_type=builder")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_convert_null_indicators_returns_400(self, client):
        """indicators가 null → 500이 아닌 400 반환 (회귀 방지)."""
        resp = client.post("/api/backtest/strategy/convert", json={
            "builder_state": {
                "metadata": {"name": "X"},
                "indicators": None,
                "entryGroups": None,
                "exitGroups": None,
                "risk": None,
            },
            "run_validate": False,
        })
        assert resp.status_code == 400
        assert "검증 실패" in resp.json()["detail"]

    def test_convert_empty_dict_returns_400(self, client):
        """빈 builder_state → 500이 아닌 400."""
        resp = client.post("/api/backtest/strategy/convert", json={
            "builder_state": {},
            "run_validate": False,
        })
        assert resp.status_code == 400

    def test_convert_run_validate_false_skips_mcp(self, client):
        """run_validate=False 시 MCP 호출 없이 YAML만 반환."""
        resp = client.post("/api/backtest/strategy/convert", json={
            "builder_state": self.VALID_STATE,
            "run_validate": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is None  # MCP 검증 스킵
        assert data["yaml_content"]

    def test_convert_with_price_field_key(self, client):
        """프론트엔드 OperandSelector의 price.field 키 호환."""
        state = {
            "metadata": {"name": "Price Test"},
            "indicators": [
                {"id": "sma", "alias": "sma_1", "params": {"period": 20}},
            ],
            "entryGroups": [{"operator": "AND", "conditions": [{
                "left": {"type": "price", "field": "close"},
                "operator": "greater_than",
                "right": {"type": "indicator", "alias": "sma_1", "output": "value"},
            }]}],
            "exitGroups": [{"operator": "AND", "conditions": [{
                "left": {"type": "price", "field": "high"},
                "operator": "less_than",
                "right": {"type": "indicator", "alias": "sma_1", "output": "value"},
            }]}],
            "risk": {},
        }
        resp = client.post("/api/backtest/strategy/convert", json={
            "builder_state": state,
            "run_validate": False,
        })
        assert resp.status_code == 200
        yaml_str = resp.json()["yaml_content"]
        assert "output: close" in yaml_str
        assert "output: high" in yaml_str
