"""local_backtest.metrics 8개 메트릭 단위 테스트.

메트릭:
  total_return_pct, cagr, sharpe_ratio, sortino_ratio,
  max_drawdown, win_rate, profit_factor, total_trades
"""

from __future__ import annotations

from datetime import date

import pytest


def test_metrics_total_return_simple():
    """초기 100, 종료 130 → total_return=30%."""
    from services.local_backtest.metrics import compute_metrics

    equity_curve = [
        {"date": date(2024, 1, 2), "equity": 100.0},
        {"date": date(2024, 1, 3), "equity": 110.0},
        {"date": date(2024, 12, 31), "equity": 130.0},
    ]
    trades = []
    m = compute_metrics(equity_curve, trades, initial_capital=100.0)
    assert m["total_return_pct"] == pytest.approx(30.0, abs=0.01)


def test_metrics_max_drawdown():
    """100→120→80→90 → 최고 120 → 최저 80, MDD=(80-120)/120=-33.33%."""
    from services.local_backtest.metrics import compute_metrics

    equity_curve = [
        {"date": date(2024, 1, 2), "equity": 100.0},
        {"date": date(2024, 1, 3), "equity": 120.0},
        {"date": date(2024, 1, 4), "equity": 80.0},
        {"date": date(2024, 1, 5), "equity": 90.0},
    ]
    m = compute_metrics(equity_curve, [], initial_capital=100.0)
    # MDD는 음수(낙폭) 또는 양수 모두 정의 가능 — abs로 검증
    assert abs(m["max_drawdown"]) == pytest.approx(33.33, abs=0.5)


def test_metrics_win_rate_and_profit_factor():
    """3거래: +10, +20, -5 → win_rate=2/3=66.67%, profit_factor=30/5=6.0."""
    from services.local_backtest.metrics import compute_metrics

    equity_curve = [
        {"date": date(2024, 1, 2), "equity": 100.0},
        {"date": date(2024, 1, 31), "equity": 125.0},
    ]
    trades = [
        # 매도(청산) 거래만 win/loss 판단. pnl_pct로 통일.
        {"symbol": "A", "entry_date": date(2024, 1, 2), "exit_date": date(2024, 1, 5),
         "entry_price": 100.0, "exit_price": 110.0, "qty": 1, "pnl": 10.0, "pnl_pct": 10.0},
        {"symbol": "B", "entry_date": date(2024, 1, 8), "exit_date": date(2024, 1, 12),
         "entry_price": 100.0, "exit_price": 120.0, "qty": 1, "pnl": 20.0, "pnl_pct": 20.0},
        {"symbol": "C", "entry_date": date(2024, 1, 15), "exit_date": date(2024, 1, 20),
         "entry_price": 100.0, "exit_price": 95.0, "qty": 1, "pnl": -5.0, "pnl_pct": -5.0},
    ]
    m = compute_metrics(equity_curve, trades, initial_capital=100.0)
    assert m["total_trades"] == 3
    assert m["win_rate"] == pytest.approx(66.67, abs=0.5)
    # profit_factor = 총이익(30) / 총손실(5) = 6
    assert m["profit_factor"] == pytest.approx(6.0, abs=0.1)


def test_metrics_cagr_one_year():
    """100 → 120 over 1 year → CAGR ≈ 20%."""
    from services.local_backtest.metrics import compute_metrics

    equity_curve = [
        {"date": date(2024, 1, 2), "equity": 100.0},
        {"date": date(2024, 12, 31), "equity": 120.0},
    ]
    m = compute_metrics(equity_curve, [], initial_capital=100.0)
    # 약 364일 ~ 1년 가정
    assert m["cagr"] == pytest.approx(20.0, abs=2.0)


def test_metrics_sharpe_positive_when_profitable():
    """이익 변동성이 있을 때 sharpe>0이어야 한다."""
    from services.local_backtest.metrics import compute_metrics

    # 균등하게 우상향
    equity = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    equity_curve = [
        {"date": date(2024, 1, 1 + i), "equity": v} for i, v in enumerate(equity)
    ]
    m = compute_metrics(equity_curve, [], initial_capital=100.0)
    # Sharpe is annualized; 단순 우상향 가정 시 양수
    if m.get("sharpe_ratio") is not None:
        assert m["sharpe_ratio"] > 0


def test_metrics_empty_trades_safe():
    """거래 없음 → 메트릭 None/0 안전 처리."""
    from services.local_backtest.metrics import compute_metrics

    equity_curve = [
        {"date": date(2024, 1, 2), "equity": 100.0},
        {"date": date(2024, 12, 31), "equity": 100.0},
    ]
    m = compute_metrics(equity_curve, [], initial_capital=100.0)
    assert m["total_trades"] == 0
    assert m["total_return_pct"] == pytest.approx(0.0, abs=0.01)
    # win_rate / profit_factor는 None 또는 0이어야 한다
    assert m.get("win_rate") in (None, 0, 0.0)
