"""변동성 돌파 전략 (`volatility_breakout`).

룰 (plan ai-sleepy-pancake — 단순화):
  K20 = 직전 20일 평균 노이즈 비율
        노이즈 비율 = 1 - |Close - Open| / (High - Low)
        - Range=0(도지)인 날은 평균에서 제외
        - 횡보장(흔들림만 큼) → noise≈1 → 진입 장벽 ↑ (가짜 돌파 방어)
        - 추세장(시가→종가 일직선) → noise≈0 → 진입 장벽 ↓ (빠른 추격)
  타겟가 = 당일 시가 + 전일Range × K20 (Range = 전일 고가 - 전일 저가)
  매수 조건: 당일 고가 ≥ 타겟가
  매수가: 타겟가
  매도: 당일 종가 강제 청산
  매도가: 당일 종가
  손절: 당일 저가 ≤ 매수가×0.97 → 매수가×0.97 (손절 우선)
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from services.local_backtest.strategies._base import (
    EntrySignal,
    ExitSignal,
    Position,
    Strategy,
)


def _compute_target(df: pd.DataFrame, idx: int, k_window: int = 20) -> Optional[float]:
    """idx일 타겟가 = 시가 + 전일Range × K20(노이즈 비율 평균)."""
    if idx < k_window:
        return None
    today_open = float(df["open"].iloc[idx])
    if today_open <= 0:
        return None

    window = df.iloc[idx - k_window : idx]
    opens = window["open"].astype(float).values
    highs = window["high"].astype(float).values
    lows = window["low"].astype(float).values
    closes = window["close"].astype(float).values
    if len(opens) < k_window:
        return None

    noise_ratios = []
    for o, h, l, c in zip(opens, highs, lows, closes):
        rng = h - l
        if rng <= 0:
            continue
        body = abs(c - o)
        noise_ratios.append(1.0 - body / rng)
    if not noise_ratios:
        return None
    k20 = sum(noise_ratios) / len(noise_ratios)

    prev_high = float(df["high"].iloc[idx - 1])
    prev_low = float(df["low"].iloc[idx - 1])
    prev_range = prev_high - prev_low
    if prev_range <= 0:
        return None
    target = today_open + prev_range * k20
    return target


class VolatilityBreakoutStrategy(Strategy):
    id = "volatility_breakout"
    default_params = {
        "k_window": 20,
        "stop_loss_pct": 0.97,  # 매수가×0.97
    }

    def required_history_days(self) -> int:
        return 20

    def check_entry(
        self, df: pd.DataFrame, idx: int, params: dict
    ) -> Optional[EntrySignal]:
        k_window = params.get("k_window", 20)
        target = _compute_target(df, idx, k_window=k_window)
        if target is None:
            return None
        today_high = float(df["high"].iloc[idx])
        if today_high >= target:
            return EntrySignal(price=target, reason="vb_breakout")
        return None

    def check_exit(
        self, df: pd.DataFrame, idx: int, position: Position, params: dict
    ) -> Optional[ExitSignal]:
        if idx < 0 or idx >= len(df):
            return None
        today_low = float(df["low"].iloc[idx])
        today_close = float(df["close"].iloc[idx])
        stop_pct = params.get("stop_loss_pct", 0.97)
        stop_price = position.entry_price * stop_pct

        # 손절 우선
        if today_low <= stop_price:
            return ExitSignal(price=stop_price, reason="stop_loss")
        # 당일 종가 강제 청산
        return ExitSignal(price=today_close, reason="close_same_day")
