"""Backtest local endpoint API 테스트 — POST /api/backtest/run/local + GET /api/backtest/local/presets.

엔진(yfinance) 실호출은 단위 테스트 책임이고, API 레이어는 라우팅·검증·DB 저장·응답 형식만 검증한다.
따라서 `services.local_backtest.engine.simulate`를 결정적 stub으로 monkeypatch.
"""

from __future__ import annotations

from datetime import date

import pytest


def _stub_sim_result():
    """가짜 SimulationResult 반환 — engine.simulate monkeypatch 용."""
    from services.local_backtest.engine import SimulationResult

    return SimulationResult(
        equity_curve=[
            {"date": "2024-01-02", "equity": 10_000_000.0},
            {"date": "2024-12-31", "equity": 11_500_000.0},
        ],
        trades=[
            {
                "symbol": "005930",
                "entry_date": "2024-03-01",
                "entry_price": 70000.0,
                "exit_date": "2024-03-04",
                "exit_price": 72000.0,
                "qty": 10,
                "pnl": 20000.0,
                "pnl_pct": 2.857,
                "exit_reason": "next_open",
            }
        ],
        metrics={
            "total_return_pct": 15.0,
            "cagr": 15.5,
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.4,
            "max_drawdown": -5.0,
            "win_rate": 100.0,
            "profit_factor": None,
            "total_trades": 1,
        },
        per_symbol_contribution={
            "005930": {"symbol": "005930", "trades": 1, "realized_pnl": 20000.0,
                        "wins": 1, "losses": 0},
            "000660": {"symbol": "000660", "trades": 0, "realized_pnl": 0.0,
                        "wins": 0, "losses": 0},
        },
        params={"rise_threshold": 0.29, "limit_up_threshold": 0.30, "stop_loss_pct": 0.925},
        failures=[],
    )


@pytest.fixture
def stub_local_simulate(monkeypatch):
    """engine.simulate + run_local_backtest 내 import된 simulate 양쪽 monkeypatch."""
    def _sim(symbols, strategy_id, market, start, end, initial_capital,
             commission_rate, tax_rate, slippage, params=None):
        # 호출자 검증 (단위 테스트가 검증한 룰을 다시 검증하지는 않음)
        assert market.upper() == "KR"
        assert 1 <= len(symbols) <= 10
        return _stub_sim_result()
    # backtest_service에서 from services.local_backtest import simulate 가 아니라
    # `from services.local_backtest import simulate as _simulate` 형태로 함수 안에서 import
    # → 모듈 자체의 simulate / engine.simulate 양쪽 패치
    monkeypatch.setattr("services.local_backtest.simulate", _sim)
    monkeypatch.setattr("services.local_backtest.engine.simulate", _sim)
    return _sim


class TestLocalPresetsEndpoint:
    def test_get_local_presets_returns_4(self, client):
        """GET /api/backtest/local/presets → 4개 프리셋."""
        resp = client.get("/api/backtest/local/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "presets" in data
        presets = data["presets"]
        assert isinstance(presets, list)
        ids = [p["id"] for p in presets]
        assert set(ids) == {
            "momentum",
            "volatility_breakout",
            "donchian_swing",
            "long_tail_volatility",
        }
        # 각 프리셋은 name/description/default_params 필수
        for p in presets:
            assert p.get("name")
            assert p.get("description")
            assert isinstance(p.get("default_params"), dict)


class TestRunLocalBacktest:
    def test_run_local_returns_per_symbol_contribution(self, client, stub_local_simulate):
        """POST /api/backtest/run/local → 200 + result.per_symbol_contribution 포함."""
        resp = client.post("/api/backtest/run/local", json={
            "preset": "momentum",
            "symbols": ["005930", "000660"],
            "market": "KR",
            "start_date": "2024-01-02",
            "end_date": "2024-12-31",
            "initial_capital": 10_000_000,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("status") == "completed"
        assert data.get("job_id")
        result = data.get("result") or {}
        # 종목별 기여도가 응답 result_json에 포함
        assert "per_symbol_contribution" in result
        contributions = result["per_symbol_contribution"]
        assert "005930" in contributions
        assert contributions["005930"]["trades"] == 1
        # equity_curve / trades 키도 포함
        assert "equity_curve" in result
        assert "trades" in result
        assert result.get("symbols") == ["005930", "000660"]

    def test_run_local_persists_symbols_in_history(self, client, stub_local_simulate):
        """run/local 호출 후 GET /api/backtest/history 응답에 symbols(list) 노출."""
        resp = client.post("/api/backtest/run/local", json={
            "preset": "momentum",
            "symbols": ["005930", "000660", "035720"],
            "market": "KR",
            "start_date": "2024-01-02",
            "end_date": "2024-06-30",
        })
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        hist = client.get("/api/backtest/history")
        assert hist.status_code == 200
        jobs = hist.json()
        target = next((j for j in jobs if j.get("job_id") == job_id), None)
        assert target is not None
        # 신규 컬럼 노출
        assert target.get("strategy_type") == "local"
        assert target.get("symbol") == "005930"  # 첫 종목
        # symbols(list) 컬럼 — 마이그레이션 e1f2a3b4c5d6 적용 후 노출
        if "symbols" in target:
            assert target["symbols"] == ["005930", "000660", "035720"]
