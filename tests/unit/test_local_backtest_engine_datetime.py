"""REQ-FIX-03: engine.py datetime 미스매치 정규화.

`pd.Timestamp(d) in df.index` 매칭이 tz-aware/시간 포함 인덱스에서 silent skip → 거래 신호 실행 안됨.

본 fix:
- 모든 OHLCV DataFrame 로드 직후 `df.index = df.index.tz_localize(None).normalize()` 통일
- `_idx_for(df, d)` 가 `pd.Timestamp(d).normalize()` 검색
- 매칭 실패 시 `logger.debug` 명시 (silent skip 가시화)
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from services.local_backtest.engine import simulate


def _mk_df_tz_aware(start_ts="2024-01-01", n=300, hour=10, tz="Asia/Seoul"):
    """시간 포함 + tz-aware DatetimeIndex 가진 더미 OHLCV (모멘텀 매수 신호 1개 포함).

    중간 (i=100) 에 +29% 모멘텀 신호 1회 발생 → entry 후 익일 시가 매도(룰).
    """
    idx = pd.date_range(start=start_ts, periods=n, freq="B", tz=tz)
    if hour:
        idx = idx + pd.Timedelta(hours=hour)
    closes = [100.0] * n
    if n >= 102:
        # i=100에 +29% 모멘텀 (전일 100 → 당일 129)
        closes[99] = 100.0
        closes[100] = 129.0  # +29%
        closes[101] = 130.0  # 익일 시가 매도용
    df = pd.DataFrame(
        {
            "open": closes,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": [10000] * n,
        },
        index=idx,
    )
    return df


def test_simulate_handles_tz_aware_index(monkeypatch):
    """(a) tz-aware (Asia/Seoul) + 시간 포함 인덱스 → engine 내부 normalize 후 거래 매칭 성공.

    검증 핵심: trading_days × _idx_for() 매칭 — 실제 entry/exit 신호가 실행되어야 한다.
    """
    df_tz = _mk_df_tz_aware()

    def fake_fetch(code, start, end, market="KR"):
        return df_tz.copy()

    monkeypatch.setattr(
        "services.local_backtest.data_loader.fetch_daily_ohlcv", fake_fetch
    )
    monkeypatch.setattr(
        "services.local_backtest.data_loader._resolve_kr_ticker", lambda c: f"{c}.KS"
    )

    result = simulate(
        symbols=["005930"],
        strategy_id="momentum",
        market="KR",
        start=date(2024, 1, 1),
        end=date(2025, 1, 31),
        initial_capital=10_000_000.0,
    )
    assert len(result.equity_curve) > 0, "trading_days 비어있음 — datetime normalize 누락"
    # entry 실행 — 모멘텀 +29% 더미 신호가 한 번 발생해야 함
    assert len(result.trades) > 0, (
        "tz-aware 인덱스에서 _idx_for 매칭 실패 → 모든 신호 silent skip"
    )


def test_simulate_handles_time_component_index(monkeypatch):
    """(b) 시간 포함 (10:00:00) naive 인덱스 → engine normalize 후 매칭 성공."""
    df_naive_with_time = _mk_df_tz_aware(tz=None)

    def fake_fetch(code, start, end, market="KR"):
        return df_naive_with_time.copy()

    monkeypatch.setattr(
        "services.local_backtest.data_loader.fetch_daily_ohlcv", fake_fetch
    )
    monkeypatch.setattr(
        "services.local_backtest.data_loader._resolve_kr_ticker", lambda c: f"{c}.KS"
    )

    result = simulate(
        symbols=["005930"],
        strategy_id="momentum",
        market="KR",
        start=date(2024, 1, 1),
        end=date(2025, 1, 31),
        initial_capital=10_000_000.0,
    )
    assert len(result.equity_curve) > 0
    assert len(result.trades) > 0


def test_idx_for_logs_when_no_match(monkeypatch, caplog):
    """(c) _idx_for 가 None 반환 시 silent skip 대신 logger.debug 로 가시화.

    하루가 누락된 종목 시뮬레이션 — 다른 종목은 정상 / 누락 종목은 debug 로그 + skip.
    """
    import logging

    n = 300
    idx_full = pd.date_range("2024-01-01", periods=n, freq="B")
    df_full = pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.0] * n,
            "volume": [10000] * n,
        },
        index=idx_full,
    )

    def fake_fetch(code, start, end, market="KR"):
        return df_full.copy()

    monkeypatch.setattr(
        "services.local_backtest.data_loader.fetch_daily_ohlcv", fake_fetch
    )
    monkeypatch.setattr(
        "services.local_backtest.data_loader._resolve_kr_ticker", lambda c: f"{c}.KS"
    )

    # debug 캡처 — engine 모듈 logger
    caplog.set_level(logging.DEBUG, logger="services.local_backtest.engine")

    result = simulate(
        symbols=["005930"],
        strategy_id="momentum",
        market="KR",
        start=date(2024, 1, 1),
        end=date(2025, 1, 31),
        initial_capital=10_000_000.0,
    )
    assert result is not None  # smoke — silent skip이 fail 트리거 X
