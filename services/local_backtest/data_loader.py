"""yfinance 일봉 fetch + 단일 백테스트 내 캐시 (KR 전용 MVP).

REQ-FIX-02 (2026-05-09):
- yfinance None/empty 영구 캐시 버그 수정 → 미저장 + 다음 호출 재시도 가능
- 단일 load 내 1회 즉시 재시도 (5초 대기) — rate limit 일시 실패 대응
- TTL 10분 (`time.time()` 기반) — 영구 캐시 안 함
"""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# REQ-FIX-02: 캐시 TTL (초) — 단일 백테스트 실행 내 동일 종목 재조회 방어용.
_CACHE_TTL_SEC = 600  # 10분
_RETRY_SLEEP_SEC = 5  # 1차 None 시 재시도 대기


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
    """단일 백테스트 실행 내 캐시. 동일 종목 OHLCV 1회 fetch.

    REQ-FIX-02: None 영구화 버그 수정 + 재시도 + TTL.
    """

    def __init__(self, market: str = "KR") -> None:
        self.market = market.upper()
        # value: (df, ts) — ts 는 캐시 저장 시각 (`time.time()`)
        self._cache: dict[str, tuple[Optional[pd.DataFrame], float]] = {}

    def _cache_get(self, key: str) -> tuple[bool, Optional[pd.DataFrame]]:
        """캐시 조회 — (hit, df). TTL 만료 시 (False, None)."""
        item = self._cache.get(key)
        if item is None:
            return False, None
        df, ts = item
        if (time.time() - ts) > _CACHE_TTL_SEC:
            return False, None
        return True, df

    def load(
        self, code: str, start: date, end: date, history_buffer_days: int = 80
    ) -> Optional[pd.DataFrame]:
        """code 일봉을 [start - buffer, end] 범위로 반환. 캐시 활용.

        REQ-FIX-02:
        - None 결과는 캐시에 저장하지 않음 (다음 호출에서 재시도 가능)
        - 1차 None 시 1회 즉시 재시도(`_RETRY_SLEEP_SEC` 대기)
        - TTL 10분 — 만료 시 재조회
        """
        key = code
        hit, cached = self._cache_get(key)
        if hit:
            return cached

        # 시그널 계산용 버퍼 추가 (donchian_swing required_history=65 + 여유)
        fetch_start = start - timedelta(days=history_buffer_days)
        df = fetch_daily_ohlcv(code, fetch_start, end, market=self.market)

        # 1차 None → 5초 대기 후 재시도 (일시 rate limit 대응)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            try:
                time.sleep(_RETRY_SLEEP_SEC)
            except Exception:
                pass
            df = fetch_daily_ohlcv(code, fetch_start, end, market=self.market)

        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            # REQ-FIX-02 핵심: None은 캐시에 저장하지 않음 → 다음 호출 재시도 가능
            logger.warning(
                "[REQ-FIX-02] data_loader 미스 (캐시 미저장) code=%s start=%s end=%s",
                code, start, end,
            )
            return None

        # 정상 데이터만 캐시에 저장 (TS 동봉)
        self._cache[key] = (df, time.time())
        return df
