"""REQ-WRAPPER-01: KoreaInvestment.fetch_oversea_asking_price 단위 테스트.

- HHDFS76200100 TR_ID 검증
- 거래소 코드(NAS/NYS/AMS) 인자 처리
- 파라미터 페이로드(AUTH/EXCD/SYMB) 검증
- rt_cd != "0" → ExternalAPIError
- API 경로 검증
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from wrapper import KoreaInvestment
from services.exceptions import ExternalAPIError


def _make_inst() -> KoreaInvestment:
    """KoreaInvestment 인스턴스를 토큰 발급 우회로 생성."""
    inst = KoreaInvestment.__new__(KoreaInvestment)
    inst.base_url = "https://openapi.koreainvestment.com:9443"
    inst.api_key = "APP_KEY_X"
    inst.api_secret = "APP_SECRET_X"
    inst.access_token = "Bearer DUMMY"
    inst.exchange = "나스닥"
    inst.mock = False
    return inst


def _ok_resp(output1: dict | None = None, output2: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상",
        "output1": output1 or {"rsym": "DNASAAPL", "zdiv": "4", "base": "200.0"},
        "output2": output2 or {
            "pask1": "200.10", "pbid1": "199.90",
            "vask1": "100",   "vbid1": "120",
            "pask2": "200.20", "pbid2": "199.80",
            "vask2": "200",   "vbid2": "220",
            "pask3": "200.30", "pbid3": "199.70",
            "vask3": "300",   "vbid3": "320",
        },
    }
    return resp


@patch("wrapper.requests.get")
def test_fetch_oversea_asking_price_normal(mock_get):
    """정상 응답: rt_cd=0 → output1+output2 dict 반환."""
    mock_get.return_value = _ok_resp()
    inst = _make_inst()
    result = inst.fetch_oversea_asking_price("AAPL", "NAS")
    assert isinstance(result, dict)
    assert "output1" in result and "output2" in result
    assert result["output2"]["pask1"] == "200.10"


@patch("wrapper.requests.get")
def test_fetch_oversea_asking_price_uses_correct_tr_id(mock_get):
    mock_get.return_value = _ok_resp()
    inst = _make_inst()
    inst.fetch_oversea_asking_price("AAPL", "NAS")
    headers = mock_get.call_args.kwargs.get("headers") or {}
    assert headers.get("tr_id") == "HHDFS76200100"
    assert headers.get("appKey") == "APP_KEY_X"
    assert headers.get("appSecret") == "APP_SECRET_X"
    assert headers.get("authorization") == "Bearer DUMMY"


@patch("wrapper.requests.get")
def test_fetch_oversea_asking_price_uses_correct_path(mock_get):
    mock_get.return_value = _ok_resp()
    inst = _make_inst()
    inst.fetch_oversea_asking_price("AAPL", "NAS")
    args, kwargs = mock_get.call_args
    url = args[0] if args else kwargs.get("url")
    assert "/uapi/overseas-price/v1/quotations/inquire-asking-price" in url


@patch("wrapper.requests.get")
def test_fetch_oversea_asking_price_payload_excd_symb(mock_get):
    """페이로드에 EXCD/SYMB가 인자대로 포함되는지."""
    mock_get.return_value = _ok_resp()
    inst = _make_inst()
    inst.fetch_oversea_asking_price("MSFT", "NYS")
    params = mock_get.call_args.kwargs.get("params") or {}
    assert params.get("EXCD") == "NYS"
    assert params.get("SYMB") == "MSFT"
    assert "AUTH" in params  # 빈 문자열 가능


@patch("wrapper.requests.get")
def test_fetch_oversea_asking_price_ams_exchange(mock_get):
    mock_get.return_value = _ok_resp()
    inst = _make_inst()
    inst.fetch_oversea_asking_price("SPY", "AMS")
    params = mock_get.call_args.kwargs.get("params") or {}
    assert params.get("EXCD") == "AMS"


@patch("wrapper.requests.get")
def test_fetch_oversea_asking_price_error_raises(mock_get):
    """rt_cd != "0" → ExternalAPIError raise."""
    bad = MagicMock()
    bad.json.return_value = {"rt_cd": "1", "msg1": "조회 실패", "msg_cd": "EGW00123"}
    mock_get.return_value = bad
    inst = _make_inst()
    with pytest.raises(ExternalAPIError):
        inst.fetch_oversea_asking_price("AAPL", "NAS")


@patch("wrapper.requests.get")
def test_fetch_oversea_asking_price_invalid_json_raises(mock_get):
    """JSON 파싱 실패 → ExternalAPIError."""
    bad = MagicMock()
    bad.json.side_effect = ValueError("invalid")
    mock_get.return_value = bad
    inst = _make_inst()
    with pytest.raises(ExternalAPIError):
        inst.fetch_oversea_asking_price("AAPL", "NAS")
