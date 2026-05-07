"""yfinance 일봉 fetch + 단일 백테스트 내 캐시 (KR 전용 MVP)."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _resolve_kr_ticker(code: str) -> Optional[str]:
    """KR 종목코드 → yfinance ticker (`.KS` 또는 `.KQ`).

    `stock.market._kr_yf_ticker_str()`을 재사용 (7일 캐시 + score≥1 검증).
    """
    try:
        from stock.market import _kr_yf_ticker_str

        return _kr_yf_ticker_str(code)
    except Exception as e:
        logger.warning("KR ticker resolve 실패 code=%s err=%s", code, e)
        return None


def fetch_daily_ohlcv(
    code: str,
    start: date,
    end: date,
    market: str = "KR",
) -> Optional[pd.DataFrame]:
    """일봉 OHLCV DataFrame 반환. index=DatetimeIndex(KST 날짜), columns=[open,high,low,close,volume].

    실패 시 None.
    """
    if market.upper() != "KR":
        raise ValueError(f"local_backtest MVP는 KR만 지원: {market}")

    ticker_str = _resolve_kr_ticker(code)
    if not ticker_str:
        return None

    try:
        # required_history_days를 위해 시작일 이전 데이터도 필요함 → 호출자가 start를 충분히 빼서 전달
        from stock.yf_client import _ticker

        tk = _ticker(ticker_str)
        # yfinance.history는 end exclusive — +1일
        hist = tk.history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=False,
        )
    except Exception as e:
        logger.warning("yf history 실패 code=%s err=%s", code, e)
        return None

    if hist is None or hist.empty:
        return None

    df = hist.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )[["open", "high", "low", "close", "volume"]].copy()
    # tz 제거 (날짜 비교 용이)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df.sort_index()
    return df


class DataLoader:
    """단일 백테스트 실행 내 캐시. 동일 종목 OHLCV 1회 fetch."""

    def __init__(self, market: str = "KR") -> None:
        self.market = market.upper()
        self._cache: dict[str, Optional[pd.DataFrame]] = {}

    def load(
        self, code: str, start: date, end: date, history_buffer_days: int = 80
    ) -> Optional[pd.DataFrame]:
        """code 일봉을 [start - buffer, end] 범위로 반환. 캐시 활용."""
        key = code
        if key in self._cache:
            return self._cache[key]
        # 시그널 계산용 버퍼 추가 (donchian_swing required_history=65 + 여유)
        fetch_start = start - timedelta(days=history_buffer_days)
        df = fetch_daily_ohlcv(code, fetch_start, end, market=self.market)
        self._cache[key] = df
        return df
