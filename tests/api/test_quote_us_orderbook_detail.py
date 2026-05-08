"""REQ-ROUTER-06: routers/quote.py 미국 호가/상세 REST 엔드포인트 단위 테스트.

- GET /api/quote/us/{symbol}/orderbook → 200 dict / 504(KIS 응답 None) / 503(ConfigError)
- GET /api/quote/us/{symbol}/detail → 200 dict / 504(KIS 응답 None) / 503(ConfigError)
- 인증 필요 (raw_client에서 401)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from services.exceptions import ConfigError


# ── orderbook ──────────────────────────────────────────────────────────────


def test_get_us_orderbook_200(client):
    fake_ob = {
        "asks": [{"price": 200.10, "volume": 100}],
        "bids": [{"price": 199.90, "volume": 120}],
        "total_ask_volume": 5500,
        "total_bid_volume": 6700,
        "exchange": "NAS",
    }
    with patch("routers.quote.get_kis_orderbook", return_value=fake_ob):
        r = client.get("/api/quote/us/AAPL/orderbook")
    assert r.status_code == 200
    body = r.json()
    assert body["asks"][0]["price"] == 200.10
    assert body["exchange"] == "NAS"


def test_get_us_orderbook_504_when_none(client):
    with patch("routers.quote.get_kis_orderbook", return_value=None):
        r = client.get("/api/quote/us/AAPL/orderbook")
    assert r.status_code == 504


def test_get_us_orderbook_503_on_config_error(client):
    with patch("routers.quote.get_kis_orderbook", side_effect=ConfigError("KIS key missing")):
        r = client.get("/api/quote/us/AAPL/orderbook")
    assert r.status_code == 503


def test_get_us_orderbook_requires_auth(raw_client):
    r = raw_client.get("/api/quote/us/AAPL/orderbook")
    assert r.status_code in (401, 403)


# ── detail ────────────────────────────────────────────────────────────────


def test_get_us_detail_200(client):
    fake_d = {
        "open": 199.50,
        "high": 201.20,
        "low": 198.80,
        "last": 200.10,
        "prev_close": 199.40,
        "volume": 12345678,
        "high_52w": 210.50,
        "low_52w": 150.20,
        "currency": "USD",
        "exchange": "NAS",
    }
    with patch("routers.quote.get_kis_price_detail", return_value=fake_d):
        r = client.get("/api/quote/us/AAPL/detail")
    assert r.status_code == 200
    body = r.json()
    assert body["last"] == 200.10
    assert body["high_52w"] == 210.50


def test_get_us_detail_504_when_none(client):
    with patch("routers.quote.get_kis_price_detail", return_value=None):
        r = client.get("/api/quote/us/AAPL/detail")
    assert r.status_code == 504


def test_get_us_detail_503_on_config_error(client):
    with patch("routers.quote.get_kis_price_detail", side_effect=ConfigError("KIS key missing")):
        r = client.get("/api/quote/us/AAPL/detail")
    assert r.status_code == 503


def test_get_us_detail_requires_auth(raw_client):
    r = raw_client.get("/api/quote/us/AAPL/detail")
    assert r.status_code in (401, 403)
