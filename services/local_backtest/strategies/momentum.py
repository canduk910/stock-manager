"""상한가 모멘텀 전략 (`momentum`).

룰 (plan ai-sleepy-pancake — 단순화):
  매수: 전일 종가 대비 당일 종가 +29% 이상 AND 종가 < 전일×1.30
  매수가: 당일 종가
  매도: 익일 시가 전량
  매도가: 익일 시가
  손절: 익일 저가 ≤ 매수가×0.925 → 매수가×0.925 (손절 우선)
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


class MomentumStrategy(Strategy):
    id = "momentum"
    default_params = {
        "rise_threshold": 0.29,  # +29%
        "limit_up_threshold": 0.30,  # +30% 도달 시 제외
        "stop_loss_pct": 0.925,  # 매수가×0.925
    }

    def required_history_days(self) -> int:
        # 전일 종가 1봉만 필요 (idx-1)
        return 1

    def check_entry(
        self, df: pd.DataFrame, idx: int, params: dict
    ) -> Optional[EntrySignal]:
        if idx < 1 or idx >= len(df):
            return None
        prev_close = float(df["close"].iloc[idx - 1])
        today_close = float(df["close"].iloc[idx])
        if prev_close <= 0:
            return None

        rise = (today_close - prev_close) / prev_close
        rise_thr = params.get("rise_threshold", 0.29)
        limit_thr = params.get("limit_up_threshold", 0.30)

        # +29% 이상 AND 종가 < 전일×1.30 (상한가 도달 제외)
        if rise >= rise_thr and today_close < prev_close * (1 + limit_thr):
            return EntrySignal(price=today_close, reason="rise_29pct")
        return None

    def check_exit(
        self, df: pd.DataFrame, idx: int, position: Position, params: dict
    ) -> Optional[ExitSignal]:
        # idx는 익일 (진입일 + 1) 평가
        if idx < 0 or idx >= len(df):
            return None
        next_open = float(df["open"].iloc[idx])
        next_low = float(df["low"].iloc[idx])
        stop_pct = params.get("stop_loss_pct", 0.925)
        stop_price = position.entry_price * stop_pct

        # 손절 우선: 익일 저가가 손절가 이하면 손절가 체결
        if next_low <= stop_price:
            return ExitSignal(price=stop_price, reason="stop_loss")
        # 그 외 익일 시가 매도
        return ExitSignal(price=next_open, reason="next_open")
