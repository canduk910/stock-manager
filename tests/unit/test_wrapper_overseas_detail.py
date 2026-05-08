"""REQ-WRAPPER-02: KoreaInvestment.fetch_oversea_price_detail 단위 테스트.

- HHDFS76200200 TR_ID 검증
- 거래소 코드(NAS/NYS/AMS) 인자 처리
- 페이로드(AUTH/EXCD/SYMB) 검증
- rt_cd != "0" → ExternalAPIError
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from wrapper import KoreaInvestment
from services.exceptions import ExternalAPIError


def _make_inst() -> KoreaInvestment:
    inst = KoreaInvestment.__new__(KoreaInvestment)
    inst.base_url = "https://openapi.koreainvestment.com:9443"
    inst.api_key = "APP_KEY_X"
    inst.api_secret = "APP_SECRET_X"
    inst.access_token = "Bearer DUMMY"
    inst.exchange = "나스닥"
    inst.mock = False
    return inst


def _ok_resp(output: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상",
        "output": output or {
            "rsym": "DNASAAPL",
            "open": "199.50",
            "high": "201.20",
            "low": "198.80",
            "last": "200.10",
            "base": "199.40",
            "tvol": "12345678",
            "h52p": "210.50",
            "h52d": "20260301",
            "l52p": "150.20",
            "l52d": "20260101",
        },
    }
    return resp


@patch("wrapper.requests.get")
def test_fetch_oversea_price_detail_normal(mock_get):
    mock_get.return_value = _ok_resp()
    inst = _make_inst()
    result = inst.fetch_oversea_price_detail("AAPL", "NAS")
    assert isinstance(result, dict)
    assert "output" in result
    assert result["output"]["last"] == "200.10"
    assert result["output"]["h52p"] == "210.50"


@patch("wrapper.requests.get")
def test_fetch_oversea_price_detail_uses_correct_tr_id(mock_get):
    mock_get.return_value = _ok_resp()
    inst = _make_inst()
    inst.fetch_oversea_price_detail("AAPL", "NAS")
    headers = mock_get.call_args.kwargs.get("headers") or {}
    assert headers.get("tr_id") == "HHDFS76200200"


@patch("wrapper.requests.get")
def test_fetch_oversea_price_detail_uses_correct_path(mock_get):
    mock_get.return_value = _ok_resp()
    inst = _make_inst()
    inst.fetch_oversea_price_detail("AAPL", "NAS")
    args, kwargs = mock_get.call_args
    url = args[0] if args else kwargs.get("url")
    assert "/uapi/overseas-price/v1/quotations/price-detail" in url


@patch("wrapper.requests.get")
def test_fetch_oversea_price_detail_payload(mock_get):
    mock_get.return_value = _ok_resp()
    inst = _make_inst()
    inst.fetch_oversea_price_detail("MSFT", "NYS")
    params = mock_get.call_args.kwargs.get("params") or {}
    assert params.get("EXCD") == "NYS"
    assert params.get("SYMB") == "MSFT"


@patch("wrapper.requests.get")
def test_fetch_oversea_price_detail_error_raises(mock_get):
    bad = MagicMock()
    bad.json.return_value = {"rt_cd": "1", "msg1": "조회 실패"}
    mock_get.return_value = bad
    inst = _make_inst()
    with pytest.raises(ExternalAPIError):
        inst.fetch_oversea_price_detail("AAPL", "NAS")


@patch("wrapper.requests.get")
def test_fetch_oversea_price_detail_invalid_json(mock_get):
    bad = MagicMock()
    bad.json.side_effect = ValueError("invalid")
    mock_get.return_value = bad
    inst = _make_inst()
    with pytest.raises(ExternalAPIError):
        inst.fetch_oversea_price_detail("AAPL", "NAS")
