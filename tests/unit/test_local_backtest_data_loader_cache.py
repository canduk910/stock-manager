"""REQ-FIX-02: data_loader 캐시 None 영구화 버그 + 재시도 + TTL 10분.

기존 `DataLoader._cache[key] = df` 가 None도 영구 저장 → 후속 호출 모두 None.
포트폴리오 일부 종목 데이터 부재 시 후속 호출 재시도 불가능.

본 fix:
- yfinance None/empty → 캐시 저장 안 함 (조기 return)
- yfinance 1회 재시도 (5초 대기는 0초로 mock 가능)
- TTL 10분 — `time.time()` 기반 dict
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from services.local_backtest.data_loader import DataLoader


def _mk_df(n=10):
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [110.0] * n,
            "low": [90.0] * n,
            "close": [105.0] * n,
            "volume": [1000] * n,
        },
        index=idx,
    )


def test_cache_hit_on_second_load_when_success(monkeypatch):
    """(a) yfinance 정상 → 캐시 저장 + 두번째 호출 캐시 적중(외부 호출 없음)."""
    calls = {"n": 0}
    df_ok = _mk_df()

    def fake_fetch(code, fetch_start, end, market="KR"):
        calls["n"] += 1
        return df_ok

    monkeypatch.setattr(
        "services.local_backtest.data_loader.fetch_daily_ohlcv", fake_fetch
    )

    loader = DataLoader(market="KR")
    out1 = loader.load("005930", date(2024, 1, 1), date(2024, 1, 31))
    out2 = loader.load("005930", date(2024, 1, 1), date(2024, 1, 31))

    assert out1 is not None
    assert out2 is not None
    assert calls["n"] == 1  # 두번째 호출은 캐시 적중


def test_none_not_cached_permanently_retries_next_call(monkeypatch):
    """(b) yfinance None → 캐시 저장 안 함 + 두번째 호출 재시도(외부 호출 발생)."""
    calls = {"n": 0}

    def fake_fetch(code, fetch_start, end, market="KR"):
        calls["n"] += 1
        return None  # 항상 None

    monkeypatch.setattr(
        "services.local_backtest.data_loader.fetch_daily_ohlcv", fake_fetch
    )

    loader = DataLoader(market="KR")
    out1 = loader.load("005930", date(2024, 1, 1), date(2024, 1, 31))
    out2 = loader.load("005930", date(2024, 1, 1), date(2024, 1, 31))

    assert out1 is None
    assert out2 is None
    # None 영구화 X — 두번째 호출도 외부 fetch 시도(재시도 1회 포함하면 ≥2)
    assert calls["n"] >= 2


def test_immediate_retry_on_first_none_then_success(monkeypatch):
    """(c) 1차 None → 즉시 재시도 → 2차 정상 → 정상 데이터 반환 (단일 load 안에서 재시도)."""
    calls = {"n": 0}
    df_ok = _mk_df()

    def fake_fetch(code, fetch_start, end, market="KR"):
        calls["n"] += 1
        return None if calls["n"] == 1 else df_ok

    monkeypatch.setattr(
        "services.local_backtest.data_loader.fetch_daily_ohlcv", fake_fetch
    )
    # sleep 즉시 통과
    monkeypatch.setattr("services.local_backtest.data_loader.time.sleep", lambda *_: None)

    loader = DataLoader(market="KR")
    out = loader.load("005930", date(2024, 1, 1), date(2024, 1, 31))
    assert out is not None
    assert calls["n"] == 2  # 1차 None + 2차 성공


def test_cache_ttl_expires(monkeypatch):
    """(d) TTL 만료 → 캐시 무효화 → 재조회."""
    calls = {"n": 0}
    df_ok = _mk_df()

    def fake_fetch(code, fetch_start, end, market="KR"):
        calls["n"] += 1
        return df_ok

    monkeypatch.setattr(
        "services.local_backtest.data_loader.fetch_daily_ohlcv", fake_fetch
    )

    # 시간 컨트롤
    fake_now = {"t": 1_000.0}

    def fake_time():
        return fake_now["t"]

    monkeypatch.setattr("services.local_backtest.data_loader.time.time", fake_time)

    loader = DataLoader(market="KR")
    loader.load("005930", date(2024, 1, 1), date(2024, 1, 31))
    fake_now["t"] += 11 * 60  # 11분 경과 (TTL 10분 초과)
    loader.load("005930", date(2024, 1, 1), date(2024, 1, 31))

    assert calls["n"] == 2  # TTL 만료 → 재조회
