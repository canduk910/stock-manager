"""REQ-ORDER-07: order_us.get_overseas_buyable 환율/원화 필드 추가 단위 테스트.

- 정상: USDKRW 환율 + deposit_krw + buyable_amount_krw 포함
- 환율 조회 실패: usd_krw_rate=None, deposit_krw=None, buyable_amount_krw=None
- 기존 USD 필드(buyable_amount, buyable_quantity, deposit, currency) 100% 보존
- KIS rt_cd != "0" → ServiceError (기존 동작)
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


def _ok_kis_resp() -> MagicMock:
    res = MagicMock()
    res.json.return_value = {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상",
        "output": {
            "frcr_ord_psbl_amt1": "10000.50",  # 가능금액 USD
            "max_buy_qty": "50",                # 가능수량
            "frcr_dncl_amt_2": "12345.67",     # 예수금 USD
        },
    }
    return res


def _err_kis_resp() -> MagicMock:
    res = MagicMock()
    res.json.return_value = {"rt_cd": "1", "msg1": "오류"}
    return res


def _currency_with_usdkrw(rate: float) -> list[dict]:
    return [
        {"symbol": "USDKRW=X", "name": "USD/KRW", "price": rate,
         "prev_close": rate, "change": 0.0, "change_pct": 0.0, "sparkline": []},
        {"symbol": "USDJPY=X", "name": "USD/JPY", "price": 150.0},
    ]


@patch("stock.macro_fetcher.fetch_currency_quotes")
@patch("services.order_us.requests.get")
def test_get_overseas_buyable_includes_krw_when_currency_ok(mock_get, mock_curr):
    from services.order_us import get_overseas_buyable

    mock_get.return_value = _ok_kis_resp()
    mock_curr.return_value = _currency_with_usdkrw(1380.0)

    result = get_overseas_buyable(
        token="t", app_key="k", app_secret="s",
        acnt_no="ACNT", acnt_prdt_cd="01",
        symbol="AAPL", price="200.10", order_type="00",
    )

    # 기존 USD 필드 보존
    assert result["buyable_amount"] == "10000.50"
    assert result["buyable_quantity"] == "50"
    assert result["deposit"] == "12345.67"
    assert result["currency"] == "USD"
    # 신규 KRW 필드
    assert result["usd_krw_rate"] == pytest.approx(1380.0)
    assert result["deposit_krw"] == pytest.approx(12345.67 * 1380.0)
    assert result["buyable_amount_krw"] == pytest.approx(10000.50 * 1380.0)


@patch("stock.macro_fetcher.fetch_currency_quotes")
@patch("services.order_us.requests.get")
def test_get_overseas_buyable_currency_failure_graceful(mock_get, mock_curr):
    """환율 조회 실패 시 KRW 필드는 None, USD 필드는 정상."""
    from services.order_us import get_overseas_buyable

    mock_get.return_value = _ok_kis_resp()
    mock_curr.side_effect = Exception("yfinance error")

    result = get_overseas_buyable(
        token="t", app_key="k", app_secret="s",
        acnt_no="ACNT", acnt_prdt_cd="01",
        symbol="AAPL", price="200.10", order_type="00",
    )

    assert result["buyable_amount"] == "10000.50"
    assert result["currency"] == "USD"
    assert result["usd_krw_rate"] is None
    assert result["deposit_krw"] is None
    assert result["buyable_amount_krw"] is None


@patch("stock.macro_fetcher.fetch_currency_quotes")
@patch("services.order_us.requests.get")
def test_get_overseas_buyable_usdkrw_missing_in_currency_list(mock_get, mock_curr):
    """USDKRW 항목이 없는 경우(JPY만 등) → KRW 필드 None, USD 필드 정상."""
    from services.order_us import get_overseas_buyable

    mock_get.return_value = _ok_kis_resp()
    mock_curr.return_value = [
        {"symbol": "USDJPY=X", "name": "USD/JPY", "price": 150.0},
    ]

    result = get_overseas_buyable(
        token="t", app_key="k", app_secret="s",
        acnt_no="ACNT", acnt_prdt_cd="01",
        symbol="AAPL", price="200.10", order_type="00",
    )

    assert result["usd_krw_rate"] is None
    assert result["deposit_krw"] is None
    assert result["buyable_amount_krw"] is None


@patch("services.order_us.requests.get")
def test_get_overseas_buyable_kis_error_raises(mock_get):
    """기존 동작 유지: rt_cd != 0 → ServiceError."""
    from services.exceptions import ServiceError
    from services.order_us import get_overseas_buyable

    mock_get.return_value = _err_kis_resp()

    with pytest.raises(ServiceError):
        get_overseas_buyable(
            token="t", app_key="k", app_secret="s",
            acnt_no="ACNT", acnt_prdt_cd="01",
            symbol="AAPL", price="200.10", order_type="00",
        )
