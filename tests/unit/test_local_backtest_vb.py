"""local_backtest.strategies.volatility_breakout (변동성 돌파) 단위 테스트.

룰:
  매수 시그널: 당일 고가 ≥ 타겟가 (타겟=시가 + 전일Range × K20)
    K20 = 20일 평균 노이즈 비율
          노이즈 비율 = 1 - |Close - Open| / (High - Low)
          (Range=0 도지는 평균에서 제외)
  매수가: 타겟가
  매도: 당일 종가 강제 청산
  매도가: 당일 종가
  손절: 당일 저가 ≤ 매수가×0.97 → 매수가×0.97
"""

from __future__ import annotations

import pandas as pd
import pytest


def _make_df(rows):
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


def _build_choppy_history(num_days: int = 20):
    """횡보장(노이즈 ≈ 1.0): 시가=종가=100, 고가 101, 저가 99 → body=0, range=2 → noise=1.0."""
    rows = []
    base = 100.0
    for i in range(num_days):
        d = f"2024-{1 + i // 28:02d}-{(i % 28) + 1:02d}"
        rows.append((d, base, base + 1.0, base - 1.0, base, 1000))
    return rows


def _build_trend_history(num_days: int = 20):
    """추세장(노이즈 ≈ 0.0): 시가 99, 종가 101, 고가 101, 저가 99 → body=2, range=2 → noise=0.0."""
    rows = []
    for i in range(num_days):
        d = f"2024-{1 + i // 28:02d}-{(i % 28) + 1:02d}"
        rows.append((d, 99.0, 101.0, 99.0, 101.0, 1000))
    return rows


def test_vb_entry_target_breakout_choppy_high_k():
    """횡보장(K20≈1.0)에선 타겟이 매우 높아 진입 장벽 ↑.

    히스토리: body=0, range=2 → 노이즈=1.0 → K20=1.0
    진입일: 시가 200, 전일 H-L=2 → 타겟=200 + 2×1.0 = 202.0.
    고가 210 ≥ 202 → 매수 성공.
    """
    from services.local_backtest.strategies import volatility_breakout as vb

    rows = _build_choppy_history(num_days=20)
    rows.append(("2024-02-01", 200.0, 210.0, 199.0, 205.0, 5000))
    df = _make_df(rows)
    strat = vb.VolatilityBreakoutStrategy()
    sig = strat.check_entry(df, idx=len(df) - 1, params=strat.default_params)
    assert sig is not None
    assert sig.price == pytest.approx(202.0, abs=0.05)


def test_vb_entry_trend_low_k_lowers_target():
    """추세장(K20≈0.0)에선 타겟이 시가에 근접 → 빠른 추격 가능.

    히스토리: body=2, range=2 → 노이즈=0.0 → K20=0.0
    진입일: 시가 200, 전일 H-L=2 → 타겟=200 + 2×0.0 = 200.0.
    """
    from services.local_backtest.strategies import volatility_breakout as vb

    rows = _build_trend_history(num_days=20)
    rows.append(("2024-02-01", 200.0, 210.0, 199.0, 205.0, 5000))
    df = _make_df(rows)
    strat = vb.VolatilityBreakoutStrategy()
    sig = strat.check_entry(df, idx=len(df) - 1, params=strat.default_params)
    assert sig is not None
    assert sig.price == pytest.approx(200.0, abs=0.05)


def test_vb_entry_no_breakout():
    """타겟 미달 시 매수 스킵. K20=1.0 → 타겟=시가+2.0=202, 고가 199.5 미달."""
    from services.local_backtest.strategies import volatility_breakout as vb

    rows = _build_choppy_history(num_days=20)
    # 진입일: 시가 200, 고가 199.5 < 타겟 202.0
    rows.append(("2024-02-01", 200.0, 199.5, 198.0, 199.0, 5000))
    df = _make_df(rows)
    strat = vb.VolatilityBreakoutStrategy()
    sig = strat.check_entry(df, idx=len(df) - 1, params=strat.default_params)
    assert sig is None


def test_vb_exit_close_same_day():
    """동일 일봉 종가에 청산 (손절 미발동)."""
    from services.local_backtest.strategies import volatility_breakout as vb
    from services.local_backtest.strategies._base import Position

    df = _make_df([
        ("2024-02-01", 200.0, 210.0, 199.0, 205.0, 5000),
    ])
    pos = Position(symbol="005930", entry_date=df.index[0].date(), entry_price=204.0, qty=10)
    strat = vb.VolatilityBreakoutStrategy()
    # idx=0인 같은 봉(진입봉)에서 종가 청산 호출
    sig = strat.check_exit(df, idx=0, position=pos, params=strat.default_params)
    assert sig is not None
    assert sig.price == pytest.approx(205.0)


def test_vb_exit_stop_loss_priority():
    """저가 ≤ 매수가×0.97 → 손절가에 체결 (종가 청산보다 우선)."""
    from services.local_backtest.strategies import volatility_breakout as vb
    from services.local_backtest.strategies._base import Position

    # 매수가 200, 손절가=200×0.97=194. 당일 저가 193 ≤ 194 → 손절
    df = _make_df([
        ("2024-02-01", 200.0, 210.0, 193.0, 199.0, 5000),
    ])
    pos = Position(symbol="005930", entry_date=df.index[0].date(), entry_price=200.0, qty=10)
    strat = vb.VolatilityBreakoutStrategy()
    sig = strat.check_exit(df, idx=0, position=pos, params=strat.default_params)
    assert sig is not None
    assert sig.price == pytest.approx(200.0 * 0.97)
    assert sig.reason in {"stop_loss", "stop"}


def test_vb_required_history_at_least_20():
    """K20 계산을 위해 최소 20일 과거 필요."""
    from services.local_backtest.strategies import volatility_breakout as vb

    strat = vb.VolatilityBreakoutStrategy()
    assert strat.required_history_days() >= 20
