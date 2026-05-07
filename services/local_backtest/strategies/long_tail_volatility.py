"""롱테일 변동성 전략 (`long_tail_volatility`).

룰 (plan ai-sleepy-pancake — 단순화):
  매수: VB 매수 조건 (당일 고가 ≥ 타겟가)
        + 추가 필터: 전일 종가 대비 당일 종가 +3% 이상
  매수가: 타겟가
  매도:
    (a) 당일 +29% 도달 (고가 ≥ 전일종가×1.29) → 익일 시가 매도
    (b) 그 외 → 당일 종가 매도
  손절: 보유 당일 저가 ≤ 매수가×0.97 → 손절가 매도
        익일까지 보유 시 익일 저가 ≤ 매수가×0.95 → 손절가 매도
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
from services.local_backtest.strategies.volatility_breakout import _compute_target


class LongTailVolatilityStrategy(Strategy):
    id = "long_tail_volatility"
    default_params = {
        "k_window": 20,
        "rise_filter": 0.03,  # 전일 대비 당일 종가 +3% 이상
        "spike_threshold": 0.29,  # +29% 도달 → 익일 시가 매도
        "stop_loss_same_day": 0.97,  # 매수가×0.97
        "stop_loss_next_day": 0.95,  # 매수가×0.95
    }

    def required_history_days(self) -> int:
        return 20

    def check_entry(
        self, df: pd.DataFrame, idx: int, params: dict
    ) -> Optional[EntrySignal]:
        if idx < 1:
            return None
        k_window = params.get("k_window", 20)
        target = _compute_target(df, idx, k_window=k_window)
        if target is None:
            return None
        today_high = float(df["high"].iloc[idx])
        if today_high < target:
            return None

        # 추가 필터: 전일 종가 대비 당일 종가 +3% 이상
        prev_close = float(df["close"].iloc[idx - 1])
        today_close = float(df["close"].iloc[idx])
        if prev_close <= 0:
            return None
        rise = (today_close - prev_close) / prev_close
        if rise < params.get("rise_filter", 0.03):
            return None

        return EntrySignal(price=target, reason="long_tail_breakout")

    def check_exit(
        self, df: pd.DataFrame, idx: int, position: Position, params: dict
    ) -> Optional[ExitSignal]:
        if idx < 0 or idx >= len(df):
            return None

        # 보유 1일차 (진입봉) vs 익일 평가 분기
        is_same_day = position.entry_date == df.index[idx].date()
        today_low = float(df["low"].iloc[idx])
        today_high = float(df["high"].iloc[idx])
        today_close = float(df["close"].iloc[idx])
        today_open = float(df["open"].iloc[idx])

        if is_same_day:
            stop_pct = params.get("stop_loss_same_day", 0.97)
            stop_price = position.entry_price * stop_pct
            if today_low <= stop_price:
                return ExitSignal(price=stop_price, reason="stop_loss")
            # +29% 도달: 다음날까지 보유, 익일 시가 매도 → 진입봉에서는 청산 안함
            # 보유 마킹은 extra에 저장
            if idx >= 1:
                prev_close = float(df["close"].iloc[idx - 1])
                if prev_close > 0 and today_high >= prev_close * (
                    1 + params.get("spike_threshold", 0.29)
                ):
                    position.extra["spike_today"] = True
                    return None
            # spike 미발생 → 당일 종가 청산
            return ExitSignal(price=today_close, reason="close_same_day")
        else:
            # 익일 (보유 2일차)
            # spike 마킹된 경우 익일 시가 매도
            if position.extra.get("spike_today"):
                # 익일 손절도 우선 평가
                stop_pct = params.get("stop_loss_next_day", 0.95)
                stop_price = position.entry_price * stop_pct
                if today_low <= stop_price:
                    return ExitSignal(price=stop_price, reason="stop_loss_next_day")
                return ExitSignal(price=today_open, reason="next_open_after_spike")
            # spike 미발생인데 익일까지 와있다 = 호출자 실수. 종가 청산
            stop_pct = params.get("stop_loss_next_day", 0.95)
            stop_price = position.entry_price * stop_pct
            if today_low <= stop_price:
                return ExitSignal(price=stop_price, reason="stop_loss_next_day")
            return ExitSignal(price=today_close, reason="close_next_day")
