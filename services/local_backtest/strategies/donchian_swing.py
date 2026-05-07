"""20일 신고가 스윙 전략 (`donchian_swing`).

룰 (plan ai-sleepy-pancake — 단순화):
  매수: 종가가 직전 20일 고가 돌파
        + 60일 EMA 5일 변화율 ≥ 0
        + 당일 거래대금 ≥ 20일 평균×1.5
        + 갭 +3% 미만 (시가/전일종가 - 1 < 3%)
  매수가: 당일 종가
  매도: 종가 ≤ 직전 20일 저가
  매도가: 당일 종가
  손절: 종가 ≤ 매수가×0.93
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


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


class DonchianSwingStrategy(Strategy):
    id = "donchian_swing"
    default_params = {
        "channel_period": 20,
        "ema_period": 60,
        "ema_change_window": 5,
        "volume_factor": 1.5,
        "gap_max": 0.03,
        "stop_loss_pct": 0.93,
    }

    def required_history_days(self) -> int:
        # 60일 EMA + 직전 20일 채널 → 60+5=65 안전 margin
        return 65

    def check_entry(
        self, df: pd.DataFrame, idx: int, params: dict
    ) -> Optional[EntrySignal]:
        ch = params.get("channel_period", 20)
        ema_p = params.get("ema_period", 60)
        ema_w = params.get("ema_change_window", 5)
        vol_f = params.get("volume_factor", 1.5)
        gap_max = params.get("gap_max", 0.03)

        if idx < max(ch, ema_p) + ema_w:
            return None

        # 직전 ch일 고가 (idx-ch ~ idx-1)
        prev_window = df.iloc[idx - ch : idx]
        prev_high_max = float(prev_window["high"].max())
        prev_low_min = float(prev_window["low"].min())
        prev_close = float(df["close"].iloc[idx - 1])
        today_open = float(df["open"].iloc[idx])
        today_close = float(df["close"].iloc[idx])
        today_volume = float(df["volume"].iloc[idx])

        # 1) 종가 > 직전 20일 고가
        if today_close <= prev_high_max:
            return None

        # 2) 60일 EMA 5일 변화율 ≥ 0
        ema_series = _ema(df["close"].astype(float), ema_p)
        if idx - ema_w < 0:
            return None
        ema_now = float(ema_series.iloc[idx])
        ema_prev = float(ema_series.iloc[idx - ema_w])
        if ema_prev <= 0:
            return None
        if (ema_now - ema_prev) / ema_prev < 0:
            return None

        # 3) 거래대금 ≥ 20일 평균×1.5 (단순화: 거래량 비교, 가격 가중 무관)
        vol_window = df.iloc[idx - ch : idx]
        avg_volume = float(vol_window["volume"].mean())
        if avg_volume <= 0:
            return None
        if today_volume < avg_volume * vol_f:
            return None

        # 4) 갭 < +3%
        if prev_close > 0:
            gap = (today_open - prev_close) / prev_close
            if gap >= gap_max:
                return None

        # _ = prev_low_min  # 미사용 — exit에서 사용
        return EntrySignal(price=today_close, reason="donchian_breakout")

    def check_exit(
        self, df: pd.DataFrame, idx: int, position: Position, params: dict
    ) -> Optional[ExitSignal]:
        ch = params.get("channel_period", 20)
        stop_pct = params.get("stop_loss_pct", 0.93)
        if idx < ch:
            return None
        if idx >= len(df):
            return None

        today_close = float(df["close"].iloc[idx])
        # 직전 ch일 저가
        prev_window = df.iloc[idx - ch : idx]
        prev_low_min = float(prev_window["low"].min())
        stop_price = position.entry_price * stop_pct

        # 손절가 도달 (종가 기준): 손절 / 채널 이탈 둘 다 동가매도
        if today_close <= stop_price:
            return ExitSignal(price=today_close, reason="stop_loss")
        if today_close <= prev_low_min:
            return ExitSignal(price=today_close, reason="channel_break")
        return None
