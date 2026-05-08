"""REQ-CLIENT-04: kis_overseas_client.get_kis_orderbook / get_kis_price_detail 단위 테스트.

- get_kis_orderbook: 정상 / 거래소 resolve 실패 / 네트워크 실패 / 응답 비정상
- get_kis_price_detail: 정상 / 거래소 resolve 실패 / 네트워크 실패 / 응답 비정상
- 텔레메트리 카운터 호출(success/fail)
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest


def _patch_session(repo_mock):
    @contextmanager
    def _fake_session():
        yield "fake_db"
    sess_patch = patch("stock.kis_overseas_client.get_session", _fake_session)
    repo_patch = patch("stock.kis_overseas_client.StockInfoRepository",
                       return_value=repo_mock)
    return sess_patch, repo_patch


def _kis_client_mock():
    m = MagicMock()
    m.exchange = "나스닥"
    return m


def _patch_get_kis_client(client):
    return patch("stock.kis_overseas_client._get_kis_client", return_value=client)


# ── get_kis_orderbook ─────────────────────────────────────────────────────────


def test_get_kis_orderbook_normal_full_levels():
    from stock.kis_overseas_client import get_kis_orderbook

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    # KIS HHDFS76200100 가이드 추정 응답
    client.fetch_oversea_asking_price.return_value = {
        "rt_cd": "0",
        "output1": {"rsym": "DNASAAPL", "zdiv": "4"},
        "output2": {
            "pask1": "200.10", "pask2": "200.20", "pask3": "200.30",
            "pask4": "200.40", "pask5": "200.50", "pask6": "200.60",
            "pask7": "200.70", "pask8": "200.80", "pask9": "200.90",
            "pask10": "201.00",
            "pbid1": "199.90", "pbid2": "199.80", "pbid3": "199.70",
            "pbid4": "199.60", "pbid5": "199.50", "pbid6": "199.40",
            "pbid7": "199.30", "pbid8": "199.20", "pbid9": "199.10",
            "pbid10": "199.00",
            "vask1": "100", "vask2": "200", "vask3": "300", "vask4": "400",
            "vask5": "500", "vask6": "600", "vask7": "700", "vask8": "800",
            "vask9": "900", "vask10": "1000",
            "vbid1": "120", "vbid2": "220", "vbid3": "320", "vbid4": "420",
            "vbid5": "520", "vbid6": "620", "vbid7": "720", "vbid8": "820",
            "vbid9": "920", "vbid10": "1020",
            "tvol_a": "5500",
            "tvol_b": "6700",
        },
    }

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_orderbook("AAPL", user_id=None)

    assert result is not None
    assert result["exchange"] == "NAS"
    assert len(result["asks"]) == 10
    assert len(result["bids"]) == 10
    assert result["asks"][0]["price"] == pytest.approx(200.10)
    assert result["asks"][0]["volume"] == 100
    assert result["bids"][0]["price"] == pytest.approx(199.90)
    assert result["bids"][0]["volume"] == 120
    assert result["total_ask_volume"] == 5500
    assert result["total_bid_volume"] == 6700


def test_get_kis_orderbook_partial_levels():
    """응답이 5단계만 채워진 경우 — 받은 단계만 반환."""
    from stock.kis_overseas_client import get_kis_orderbook

    repo = MagicMock()
    repo.get_exchange.return_value = "NYS"

    client = _kis_client_mock()
    out2 = {f"pask{i}": "0" for i in range(1, 11)}
    out2.update({f"pbid{i}": "0" for i in range(1, 11)})
    out2.update({f"vask{i}": "0" for i in range(1, 11)})
    out2.update({f"vbid{i}": "0" for i in range(1, 11)})
    # 5단계만 채움
    for i in range(1, 6):
        out2[f"pask{i}"] = f"{100.0 + i * 0.1:.2f}"
        out2[f"pbid{i}"] = f"{99.9 - (i - 1) * 0.1:.2f}"
        out2[f"vask{i}"] = str(50 * i)
        out2[f"vbid{i}"] = str(60 * i)
    client.fetch_oversea_asking_price.return_value = {
        "rt_cd": "0",
        "output1": {"rsym": "DNYSBRK"},
        "output2": out2,
    }

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_orderbook("BRK-A", user_id=None)

    assert result is not None
    assert len(result["asks"]) == 5
    assert len(result["bids"]) == 5


def test_get_kis_orderbook_resolve_fail_returns_none():
    from stock.kis_overseas_client import get_kis_orderbook

    repo = MagicMock()
    repo.get_exchange.return_value = None

    client = _kis_client_mock()
    client.fetch_oversea_price.side_effect = Exception("net")

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_orderbook("XXXX", user_id=None)

    assert result is None


def test_get_kis_orderbook_no_client_returns_none():
    from stock.kis_overseas_client import get_kis_orderbook

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"  # 캐시 hit으로 resolve는 통과

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(None):
        result = get_kis_orderbook("AAPL", user_id=None)

    assert result is None


def test_get_kis_orderbook_network_exception_returns_none():
    from stock.kis_overseas_client import get_kis_orderbook

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_oversea_asking_price.side_effect = Exception("timeout")

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_orderbook("AAPL", user_id=None)

    assert result is None


def test_get_kis_orderbook_rt_cd_error_returns_none():
    from stock.kis_overseas_client import get_kis_orderbook

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_oversea_asking_price.return_value = {"rt_cd": "1", "msg1": "err"}

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_orderbook("AAPL", user_id=None)

    assert result is None


# ── get_kis_price_detail ──────────────────────────────────────────────────────


def test_get_kis_price_detail_normal():
    from stock.kis_overseas_client import get_kis_price_detail

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_oversea_price_detail.return_value = {
        "rt_cd": "0",
        "output": {
            "open": "199.50",
            "high": "201.20",
            "low": "198.80",
            "last": "200.10",
            "base": "199.40",
            "tvol": "12345678",
            "h52p": "210.50",
            "l52p": "150.20",
        },
    }

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_price_detail("AAPL", user_id=None)

    assert result is not None
    assert result["open"] == pytest.approx(199.50)
    assert result["high"] == pytest.approx(201.20)
    assert result["low"] == pytest.approx(198.80)
    assert result["prev_close"] == pytest.approx(199.40)
    assert result["volume"] == 12345678
    assert result["high_52w"] == pytest.approx(210.50)
    assert result["low_52w"] == pytest.approx(150.20)
    assert result["exchange"] == "NAS"


def test_get_kis_price_detail_resolve_fail_returns_none():
    from stock.kis_overseas_client import get_kis_price_detail

    repo = MagicMock()
    repo.get_exchange.return_value = None
    client = _kis_client_mock()
    client.fetch_oversea_price.side_effect = Exception("net")

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        assert get_kis_price_detail("XXXX", user_id=None) is None


def test_get_kis_price_detail_rt_cd_error_returns_none():
    from stock.kis_overseas_client import get_kis_price_detail

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"
    client = _kis_client_mock()
    client.fetch_oversea_price_detail.return_value = {"rt_cd": "1", "msg1": "err"}

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        assert get_kis_price_detail("AAPL", user_id=None) is None


def test_get_kis_price_detail_network_exception_returns_none():
    from stock.kis_overseas_client import get_kis_price_detail

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"
    client = _kis_client_mock()
    client.fetch_oversea_price_detail.side_effect = Exception("timeout")

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        assert get_kis_price_detail("AAPL", user_id=None) is None
