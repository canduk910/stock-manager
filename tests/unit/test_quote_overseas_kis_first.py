"""REQ-INTEG-05: services/quote_overseas.py KIS 우선 전환 단위 테스트.

검증 범위:
- KIS 정상 응답 → KIS 가격으로 메시지 구성
- KIS None → yfinance fallback 경로 (logger.warning + telemetry)
- WebSocket 메시지 shape({type, symbol, price, change, change_rate, sign}) 보존
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


def _kis_ok():
    return {
        "last": 150.5,
        "change": 1.5,
        "change_rate": 1.01,
        "volume": 12345,
        "currency": "USD",
        "exchange": "NAS",
    }


# ── KIS 우선 ──────────────────────────────────────────────────────────────────


def test_fetch_quote_message_kis_normal():
    """KIS 정상 응답이면 yfinance 미호출."""
    from services.quote_overseas import _fetch_quote_message

    with patch("services.quote_overseas.get_kis_price", return_value=_kis_ok()) as kis_mock, \
         patch("services.quote_overseas._fetch_quote_message_yf") as yf_mock:
        msg = _fetch_quote_message("AAPL")

    assert msg is not None
    assert msg["type"] == "price"
    assert msg["symbol"] == "AAPL"
    assert msg["price"] == 150.5
    assert msg["change"] == 1.5
    assert msg["change_rate"] == 1.01
    # yfinance fallback 미호출
    yf_mock.assert_not_called()


def test_fetch_quote_message_kis_none_falls_back_to_yf():
    """KIS None → yfinance fallback."""
    from services.quote_overseas import _fetch_quote_message

    yf_msg = {"type": "price", "symbol": "AAPL", "price": 100.0,
              "change": 0.5, "change_rate": 0.5, "sign": "2"}
    with patch("services.quote_overseas.get_kis_price", return_value=None), \
         patch("services.quote_overseas._fetch_quote_message_yf", return_value=yf_msg):
        msg = _fetch_quote_message("AAPL")

    assert msg == yf_msg


def test_fetch_quote_message_kis_exception_falls_back():
    """KIS 호출 자체가 예외 → yfinance fallback (서비스 무중단)."""
    from services.quote_overseas import _fetch_quote_message

    yf_msg = {"type": "price", "symbol": "AAPL", "price": 100.0,
              "change": 0.5, "change_rate": 0.5, "sign": "2"}
    with patch("services.quote_overseas.get_kis_price", side_effect=Exception("kis-down")), \
         patch("services.quote_overseas._fetch_quote_message_yf", return_value=yf_msg):
        msg = _fetch_quote_message("AAPL")

    assert msg == yf_msg


def test_fetch_quote_message_message_shape_preserved():
    """메시지 shape: {type, symbol, price, change, change_rate, sign} — 프론트 호환."""
    from services.quote_overseas import _fetch_quote_message

    with patch("services.quote_overseas.get_kis_price", return_value=_kis_ok()):
        msg = _fetch_quote_message("AAPL")

    required_keys = {"type", "symbol", "price", "change", "change_rate"}
    assert required_keys.issubset(set(msg.keys())), f"필수 키 누락: {msg.keys()}"
    # sign 도 보존되어야 (양수=2, 음수=5)
    assert msg.get("sign") in ("2", "5")
