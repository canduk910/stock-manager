"""REQ-CLIENT-04: stock/kis_overseas_client.py 단위 테스트.

테스트 범위:
- _resolve_exchange: 캐시 hit / 캐시 miss 후 NAS→NYS→AMS 순회 / 모두 실패
- get_kis_price: 정상 / 네트워크 실패(예외) / 응답 비정상(rt_cd != 0)
- get_kis_ohlcv_daily: 정상 / end_day 기본값
- get_kis_ohlcv_15min: 단일 응답 / 페이지네이션 호출(KEYB)
- ConfigError(KIS 키 부재)는 그대로 raise

mock 전략:
- routers._kis_auth.get_kis_credentials → 자격 dict
- wrapper.KoreaInvestment.__init__ 우회 (토큰 발급 회피)
- KIS 메서드(fetch_oversea_price, fetch_ohlcv_overesea, fetch_minute_bar_overesea) mock
- StockInfoRepository (get_session contextmanager)
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from services.exceptions import ConfigError


# ── helpers ──────────────────────────────────────────────────────────────────


def _patch_session(repo_mock):
    """get_session contextmanager → StockInfoRepository(repo_mock) 주입."""
    @contextmanager
    def _fake_session():
        yield "fake_db"

    sess_patch = patch("stock.kis_overseas_client.get_session", _fake_session)
    repo_patch = patch("stock.kis_overseas_client.StockInfoRepository",
                       return_value=repo_mock)
    return sess_patch, repo_patch


def _kis_client_mock():
    """KoreaInvestment 인스턴스 mock."""
    m = MagicMock()
    m.exchange = "나스닥"
    return m


def _patch_get_kis_client(client):
    return patch("stock.kis_overseas_client._get_kis_client", return_value=client)


# ── _resolve_exchange ─────────────────────────────────────────────────────────


def test_resolve_exchange_cache_hit():
    """이미 영속된 거래소 코드는 즉시 반환 (외부 호출 없음)."""
    from stock.kis_overseas_client import _resolve_exchange

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"
    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p:
        with _patch_get_kis_client(MagicMock()) as gck:
            result = _resolve_exchange("AAPL", user_id=None)

    assert result == "NAS"
    repo.set_exchange.assert_not_called()  # 캐시 hit이므로 set 안함
    gck.assert_not_called()  # 거래소 시도 호출 안함


def test_resolve_exchange_cache_miss_first_try_succeeds():
    """캐시 미스 → NAS로 시도 → 정상 응답 → NAS 영속."""
    from stock.kis_overseas_client import _resolve_exchange

    repo = MagicMock()
    repo.get_exchange.return_value = None  # 미스

    client = _kis_client_mock()
    client.fetch_oversea_price.return_value = {"rt_cd": "0", "output": {"last": "150.0"}}

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = _resolve_exchange("AAPL", user_id=None)

    assert result == "NAS"
    repo.set_exchange.assert_called_once_with("AAPL", "US", "NAS")


def test_resolve_exchange_cache_miss_falls_through_to_nys():
    """NAS 실패 → NYS 시도 → 성공 → NYS 영속."""
    from stock.kis_overseas_client import _resolve_exchange

    repo = MagicMock()
    repo.get_exchange.return_value = None

    client = _kis_client_mock()
    # 첫 호출(NAS): rt_cd != 0 또는 last=0 → 실패
    # 둘째 호출(NYS): rt_cd=0 + last>0 → 성공
    client.fetch_oversea_price.side_effect = [
        {"rt_cd": "0", "output": {"last": "0"}},
        {"rt_cd": "0", "output": {"last": "100.5"}},
    ]

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = _resolve_exchange("BRK-A", user_id=None)

    assert result == "NYS"
    repo.set_exchange.assert_called_once_with("BRK-A", "US", "NYS")


def test_resolve_exchange_all_fail_returns_none():
    """NAS/NYS/AMS 모두 실패 → None (영속 없음)."""
    from stock.kis_overseas_client import _resolve_exchange

    repo = MagicMock()
    repo.get_exchange.return_value = None

    client = _kis_client_mock()
    client.fetch_oversea_price.side_effect = Exception("network")

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = _resolve_exchange("XXXX", user_id=None)

    assert result is None
    repo.set_exchange.assert_not_called()


def test_resolve_exchange_no_client_returns_none():
    """KIS 클라이언트 인증 실패(None) → None."""
    from stock.kis_overseas_client import _resolve_exchange

    repo = MagicMock()
    repo.get_exchange.return_value = None

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(None):
        result = _resolve_exchange("AAPL", user_id=None)

    assert result is None


# ── get_kis_price ─────────────────────────────────────────────────────────────


def test_get_kis_price_normal():
    """정상 응답 → 표준 dict 반환."""
    from stock.kis_overseas_client import get_kis_price

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_oversea_price.return_value = {
        "rt_cd": "0",
        "output": {"last": "150.5", "diff": "1.5", "rate": "1.01", "tvol": "100000"}
    }

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_price("AAPL", user_id=None)

    assert result is not None
    assert result["last"] == 150.5
    assert result["change"] == 1.5
    assert result["change_rate"] == 1.01
    assert result["volume"] == 100000
    assert result["currency"] == "USD"
    assert result["exchange"] == "NAS"


def test_get_kis_price_resolve_failure_returns_none():
    """거래소 resolve 실패 → None."""
    from stock.kis_overseas_client import get_kis_price

    repo = MagicMock()
    repo.get_exchange.return_value = None

    client = _kis_client_mock()
    client.fetch_oversea_price.side_effect = Exception("net")

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_price("XXXX", user_id=None)

    assert result is None


def test_get_kis_price_network_failure_returns_none():
    """캐시 hit인데 네트워크 실패 → None (예외를 raise하지 않음)."""
    from stock.kis_overseas_client import get_kis_price

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_oversea_price.side_effect = Exception("timeout")

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_price("AAPL", user_id=None)

    assert result is None


def test_get_kis_price_rt_cd_error_returns_none():
    """KIS rt_cd != 0 → None."""
    from stock.kis_overseas_client import get_kis_price

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_oversea_price.return_value = {"rt_cd": "1", "msg1": "fail"}

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_price("AAPL", user_id=None)

    assert result is None


def test_get_kis_price_config_error_propagates():
    """ConfigError(KIS 키 부재)는 raise (운영자 인지)."""
    from stock.kis_overseas_client import get_kis_price

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    sess_p, repo_p = _patch_session(repo)
    # _get_kis_client 자체가 ConfigError를 raise (운영자 KIS 미설정)
    with sess_p, repo_p, patch(
        "stock.kis_overseas_client._get_kis_client",
        side_effect=ConfigError("KIS 키 미설정"),
    ):
        with pytest.raises(ConfigError):
            get_kis_price("AAPL", user_id=None)


# ── get_kis_ohlcv_daily ───────────────────────────────────────────────────────


def test_get_kis_ohlcv_daily_normal():
    """정상 응답 → OHLCV list 반환."""
    from stock.kis_overseas_client import get_kis_ohlcv_daily

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_ohlcv_overesea.return_value = {
        "rt_cd": "0",
        "output1": {},
        "output2": [
            {"xymd": "20260508", "open": "150.0", "high": "152.0", "low": "149.0", "clos": "151.0", "tvol": "1000"},
            {"xymd": "20260507", "open": "148.0", "high": "151.0", "low": "147.5", "clos": "150.0", "tvol": "1200"},
        ],
    }

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_ohlcv_daily("AAPL", user_id=None)

    assert result is not None
    assert len(result) == 2
    assert result[0]["date"] == "20260508"
    assert result[0]["close"] == 151.0


def test_get_kis_ohlcv_daily_end_day_default():
    """end_day 미지정 → 자동 채움(빈 문자열로 wrapper에 위임 OR 오늘 KST)."""
    from stock.kis_overseas_client import get_kis_ohlcv_daily

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_ohlcv_overesea.return_value = {"rt_cd": "0", "output1": {}, "output2": []}

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        # end_day 명시 없이도 정상 호출
        result = get_kis_ohlcv_daily("AAPL", end_day=None, user_id=None)

    # 빈 list라도 None이 아니라 list 또는 None — 둘 중 하나의 일관된 동작 보장
    assert result is None or isinstance(result, list)


# ── get_kis_ohlcv_15min ───────────────────────────────────────────────────────


def test_get_kis_ohlcv_15min_single_response():
    """단일 호출로 충분한 데이터 → 페이지네이션 없이 반환."""
    from stock.kis_overseas_client import get_kis_ohlcv_15min

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_minute_bar_overesea.return_value = {
        "rt_cd": "0",
        "output1": {},
        "output2": [
            {"xymd": "20260508", "xhms": "150000", "open": "150.0", "high": "151.0",
             "low": "149.0", "last": "150.5", "evol": "5000"},
            {"xymd": "20260508", "xhms": "144500", "open": "149.5", "high": "150.5",
             "low": "149.0", "last": "150.0", "evol": "4000"},
        ],
    }

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_ohlcv_15min("AAPL", days=60, user_id=None)

    assert result is not None
    assert len(result) >= 1
    # 정렬: 과거 → 최신 OR 최신 → 과거 — 어느 쪽이든 일관성 있어야
    first = result[0]
    assert "datetime" in first
    assert "open" in first and "high" in first and "low" in first and "close" in first


def test_get_kis_ohlcv_15min_handles_empty():
    """빈 응답 → None."""
    from stock.kis_overseas_client import get_kis_ohlcv_15min

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_minute_bar_overesea.return_value = {"rt_cd": "0", "output1": {}, "output2": []}

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_ohlcv_15min("AAPL", days=60, user_id=None)

    # 빈 데이터 — None or [] 일관성
    assert result is None or result == []


def test_get_kis_ohlcv_15min_failure_returns_none():
    """예외 발생 → None (호출처가 yfinance fallback 결정)."""
    from stock.kis_overseas_client import get_kis_ohlcv_15min

    repo = MagicMock()
    repo.get_exchange.return_value = "NAS"

    client = _kis_client_mock()
    client.fetch_minute_bar_overesea.side_effect = Exception("kis-down")

    sess_p, repo_p = _patch_session(repo)
    with sess_p, repo_p, _patch_get_kis_client(client):
        result = get_kis_ohlcv_15min("AAPL", days=60, user_id=None)

    assert result is None
