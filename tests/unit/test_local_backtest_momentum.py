"""local_backtest.strategies.momentum (상한가 모멘텀) 단위 테스트.

룰 (plan ai-sleepy-pancake):
  매수: 전일 종가 대비 당일 종가 +29% 이상 AND 종가 < 전일×1.30 (상한가 도달 제외)
  매수가: 당일 종가
  매도: 익일 시가 전량 매도
  매도가: 익일 시가
  손절: 익일 저가 ≤ 매수가×0.925 → 매수가×0.925 (손절가 우선)
"""

from __future__ import annotations

import pandas as pd
import pytest


def _make_df(rows):
    """헬퍼: [(date, open, high, low, close, volume), ...] → DataFrame."""
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


def test_momentum_entry_normal_29pct_buy_close():
    """전일 종가 100 → 당일 종가 130 (+30% 미만이지만 +29% 이상): 매수."""
    from services.local_backtest.strategies import momentum

    df = _make_df([
        ("2024-01-02", 100, 100, 100, 100, 1000),
        ("2024-01-03", 110, 132, 105, 129, 5000),  # +29.0%, 종가 129 < 전일×1.30=130
    ])
    strat = momentum.MomentumStrategy()
    sig = strat.check_entry(df, idx=1, params=strat.default_params)
    assert sig is not None
    assert sig.price == pytest.approx(129.0)


def test_momentum_entry_skip_when_limit_up():
    """종가 == 전일×1.30 (상한가 도달): 매수 스킵."""
    from services.local_backtest.strategies import momentum

    df = _make_df([
        ("2024-01-02", 100, 100, 100, 100, 1000),
        ("2024-01-03", 110, 130, 105, 130, 5000),  # 종가 130 == 전일×1.30 → 스킵
    ])
    strat = momentum.MomentumStrategy()
    sig = strat.check_entry(df, idx=1, params=strat.default_params)
    assert sig is None


def test_momentum_entry_skip_when_below_29pct():
    """+29% 미달: 매수 스킵."""
    from services.local_backtest.strategies import momentum

    df = _make_df([
        ("2024-01-02", 100, 100, 100, 100, 1000),
        ("2024-01-03", 110, 130, 105, 128, 5000),  # +28% → 스킵
    ])
    strat = momentum.MomentumStrategy()
    sig = strat.check_entry(df, idx=1, params=strat.default_params)
    assert sig is None


def test_momentum_exit_normal_next_open():
    """진입 다음 날 시가에 매도 (손절 미발동)."""
    from services.local_backtest.strategies import momentum
    from services.local_backtest.strategies._base import Position

    # 매수가 100, 익일 저가 95 (>92.5 = 100×0.925) → 손절 안 걸림 → 시가 매도
    df = _make_df([
        ("2024-01-02", 100, 100, 100, 100, 1000),  # 진입일 (비교용)
        ("2024-01-03", 105, 110, 95, 102, 5000),   # 익일: 시가=105, 저가=95
    ])
    pos = Position(symbol="005930", entry_date=df.index[0].date(), entry_price=100.0, qty=10)
    strat = momentum.MomentumStrategy()
    sig = strat.check_exit(df, idx=1, position=pos, params=strat.default_params)
    assert sig is not None
    assert sig.price == pytest.approx(105.0)
    assert sig.reason in {"next_open", "exit"}


def test_momentum_exit_stop_loss_priority():
    """익일 저가 ≤ 매수가×0.925 → 시가 매도 대신 손절가에 체결."""
    from services.local_backtest.strategies import momentum
    from services.local_backtest.strategies._base import Position

    # 매수가 100 → 손절가 92.5. 익일 저가 92.0 (≤92.5) → 손절 우선
    df = _make_df([
        ("2024-01-02", 100, 100, 100, 100, 1000),
        ("2024-01-03", 105, 108, 92, 95, 5000),  # 시가 105, 저가 92
    ])
    pos = Position(symbol="005930", entry_date=df.index[0].date(), entry_price=100.0, qty=10)
    strat = momentum.MomentumStrategy()
    sig = strat.check_exit(df, idx=1, position=pos, params=strat.default_params)
    assert sig is not None
    assert sig.price == pytest.approx(92.5)  # 100 × 0.925
    assert sig.reason in {"stop_loss", "stop"}


def test_momentum_required_history_minimum_2():
    """모멘텀 전략은 최소 전일 1봉만 있으면 됨 (전일 종가 비교)."""
    from services.local_backtest.strategies import momentum

    strat = momentum.MomentumStrategy()
    assert strat.required_history_days() >= 1
