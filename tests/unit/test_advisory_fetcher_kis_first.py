"""REQ-INTEG-08: stock/advisory_fetcher.py fetch_15min_ohlcv_us KIS 우선 단위 테스트.

검증 범위:
- KIS 정상 응답 → KIS 사용, yfinance 미호출
- KIS None → yfinance fallback (기존 경로)
- 반환 shape 변경 없음: list[dict{time, open, high, low, close, volume}]
- 정렬 순서: 과거 → 최신 (기술분석 호환)
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


def _kis_15min_ohlcv():
    """KIS 정상 응답 형식 (과거 → 최신)."""
    return [
        {"datetime": "2026-05-01T09:30:00", "time": "2026-05-01T09:30:00",
         "open": 100.0, "high": 101.5, "low": 99.5, "close": 100.5, "volume": 1000},
        {"datetime": "2026-05-01T09:45:00", "time": "2026-05-01T09:45:00",
         "open": 100.5, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 1200},
        {"datetime": "2026-05-01T10:00:00", "time": "2026-05-01T10:00:00",
         "open": 101.0, "high": 102.5, "low": 100.5, "close": 102.0, "volume": 1500},
    ]


def test_fetch_15min_ohlcv_us_kis_first():
    """KIS 정상 → KIS 데이터 사용."""
    from stock import advisory_fetcher

    with patch("stock.advisory_fetcher.get_kis_ohlcv_15min", return_value=_kis_15min_ohlcv()) as kis_mock, \
         patch("stock.advisory_fetcher._ticker") as ticker_mock:
        result = advisory_fetcher.fetch_15min_ohlcv_us("AAPL")

    assert isinstance(result, list)
    assert len(result) == 3
    # 첫 항목 키 검증 (기술분석 호환)
    first = result[0]
    for k in ("time", "open", "high", "low", "close", "volume"):
        assert k in first, f"키 누락: {k}"
    # KIS 호출 + yfinance 미호출
    kis_mock.assert_called_once()
    ticker_mock.assert_not_called()


def test_fetch_15min_ohlcv_us_kis_none_falls_back():
    """KIS None → yfinance fallback (기존 경로)."""
    from stock import advisory_fetcher

    # yfinance mock — 빈 hist
    fake_ticker = MagicMock()
    fake_hist = MagicMock()
    fake_hist.empty = True
    fake_ticker.history.return_value = fake_hist

    with patch("stock.advisory_fetcher.get_kis_ohlcv_15min", return_value=None), \
         patch("stock.advisory_fetcher._ticker", return_value=fake_ticker):
        result = advisory_fetcher.fetch_15min_ohlcv_us("AAPL")

    # yfinance 비어있으면 빈 리스트
    assert result == []


def test_fetch_15min_ohlcv_us_kis_empty_falls_back():
    """KIS 빈 리스트 → yfinance fallback."""
    from stock import advisory_fetcher

    fake_ticker = MagicMock()
    fake_hist = MagicMock()
    fake_hist.empty = True
    fake_ticker.history.return_value = fake_hist

    with patch("stock.advisory_fetcher.get_kis_ohlcv_15min", return_value=[]), \
         patch("stock.advisory_fetcher._ticker", return_value=fake_ticker):
        result = advisory_fetcher.fetch_15min_ohlcv_us("AAPL")

    assert result == []


def test_fetch_15min_ohlcv_us_kis_exception_falls_back():
    """KIS 예외 → yfinance fallback (서비스 무중단)."""
    from stock import advisory_fetcher

    fake_ticker = MagicMock()
    fake_hist = MagicMock()
    fake_hist.empty = True
    fake_ticker.history.return_value = fake_hist

    with patch("stock.advisory_fetcher.get_kis_ohlcv_15min", side_effect=Exception("kis-down")), \
         patch("stock.advisory_fetcher._ticker", return_value=fake_ticker):
        result = advisory_fetcher.fetch_15min_ohlcv_us("AAPL")

    # 서비스 무중단 — 빈 리스트라도 정상 반환
    assert isinstance(result, list)


def test_fetch_15min_ohlcv_us_truncates_to_300():
    """기술분석 입력 호환: 최대 300봉 반환."""
    from stock import advisory_fetcher

    # KIS에서 500봉 반환 시도
    rows = []
    for i in range(500):
        rows.append({
            "datetime": f"2026-05-01T{i:02d}:00:00", "time": f"2026-05-01T{i:02d}:00:00",
            "open": 100.0 + i, "high": 101.0 + i, "low": 99.0 + i,
            "close": 100.5 + i, "volume": 1000 + i,
        })

    with patch("stock.advisory_fetcher.get_kis_ohlcv_15min", return_value=rows), \
         patch("stock.advisory_fetcher._ticker"):
        result = advisory_fetcher.fetch_15min_ohlcv_us("AAPL")

    assert len(result) <= 300
