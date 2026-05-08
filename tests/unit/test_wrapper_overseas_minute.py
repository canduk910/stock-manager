"""REQ-WRAPPER-01: KoreaInvestment.fetch_minute_bar_overesea 단위 테스트.

- HHDFS76950200 TR_ID 검증
- 거래소 코드(NAS/NYS/AMS) 인자 처리
- 파라미터 페이로드(EXCD/SYMB/NMIN/PINC/NEXT/NREC/FILL/KEYB) 검증
- rt_cd != "0" → ExternalAPIError
- KEYB 인자(연속조회 키) 페이지네이션 지원
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
    inst.exchange = "나스닥"  # 다른 메서드 호환용; 본 메서드는 인자 우선
    inst.mock = False
    return inst


def _ok_resp(output1: dict | None = None, output2: list | None = None) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상",
        "output1": output1 or {"prdy_vrss": "0.5"},
        "output2": output2 or [
            {"xymd": "20260508", "xhms": "150000", "open": "100.0", "high": "101.0", "low": "99.5", "close": "100.5", "tvol": "12345"}
        ],
    }
    return resp


# ── 정상 응답 ────────────────────────────────────────────────────────────────


@patch("wrapper.requests.get")
def test_fetch_minute_bar_overesea_normal(mock_get):
    """정상 응답: rt_cd=0 → output1+output2 dict 반환."""
    mock_get.return_value = _ok_resp()
    inst = _make_inst()

    result = inst.fetch_minute_bar_overesea("AAPL", "NAS", time_period="60")

    assert isinstance(result, dict)
    assert "output1" in result and "output2" in result
    assert result["output2"][0]["close"] == "100.5"


@patch("wrapper.requests.get")
def test_fetch_minute_bar_overesea_uses_correct_tr_id(mock_get):
    """TR_ID = HHDFS76950200 가 헤더에 정확히 들어가는지."""
    mock_get.return_value = _ok_resp()
    inst = _make_inst()

    inst.fetch_minute_bar_overesea("AAPL", "NAS")

    args, kwargs = mock_get.call_args
    headers = kwargs.get("headers") or {}
    assert headers.get("tr_id") == "HHDFS76950200"


@patch("wrapper.requests.get")
def test_fetch_minute_bar_overesea_uses_correct_path(mock_get):
    """API 경로 검증."""
    mock_get.return_value = _ok_resp()
    inst = _make_inst()

    inst.fetch_minute_bar_overesea("AAPL", "NAS")

    args, kwargs = mock_get.call_args
    url = args[0] if args else kwargs.get("url")
    assert "/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice" in url


@patch("wrapper.requests.get")
def test_fetch_minute_bar_overesea_params_payload(mock_get):
    """params 페이로드: EXCD/SYMB/NMIN/PINC/NEXT/NREC/FILL/KEYB."""
    mock_get.return_value = _ok_resp()
    inst = _make_inst()

    inst.fetch_minute_bar_overesea("AAPL", "NYS", time_period="15")

    _, kwargs = mock_get.call_args
    params = kwargs.get("params") or {}
    assert params.get("EXCD") == "NYS"  # 인자 그대로
    assert params.get("SYMB") == "AAPL"
    assert params.get("NMIN") == "15"
    # KIS 분봉 계약 필드
    for key in ("PINC", "NEXT", "NREC", "FILL", "KEYB"):
        assert key in params, f"params 페이로드에 {key} 필드 누락"


@patch("wrapper.requests.get")
def test_fetch_minute_bar_overesea_default_period_60(mock_get):
    """time_period 기본값 60분."""
    mock_get.return_value = _ok_resp()
    inst = _make_inst()

    inst.fetch_minute_bar_overesea("AAPL", "NAS")

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["NMIN"] == "60"


@patch("wrapper.requests.get")
def test_fetch_minute_bar_overesea_keyb_pagination(mock_get):
    """KEYB(연속조회 키) 인자 페이지네이션 지원."""
    mock_get.return_value = _ok_resp()
    inst = _make_inst()

    inst.fetch_minute_bar_overesea("AAPL", "NAS", keyb="20260507120000")

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["KEYB"] == "20260507120000"


# ── 에러 케이스 ───────────────────────────────────────────────────────────────


@patch("wrapper.requests.get")
def test_fetch_minute_bar_overesea_rt_cd_error_raises(mock_get):
    """rt_cd != '0' → ExternalAPIError raise."""
    resp = MagicMock()
    resp.json.return_value = {"rt_cd": "1", "msg1": "조회 실패", "msg_cd": "ERR9999"}
    mock_get.return_value = resp
    inst = _make_inst()

    with pytest.raises(ExternalAPIError):
        inst.fetch_minute_bar_overesea("XXXX", "NAS")


# ── 거래소 코드 검증 ──────────────────────────────────────────────────────────


@patch("wrapper.requests.get")
@pytest.mark.parametrize("exchange_code", ["NAS", "NYS", "AMS"])
def test_fetch_minute_bar_overesea_exchange_codes(mock_get, exchange_code):
    """NAS/NYS/AMS 모두 그대로 EXCD에 전달."""
    mock_get.return_value = _ok_resp()
    inst = _make_inst()

    inst.fetch_minute_bar_overesea("AAPL", exchange_code)

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["EXCD"] == exchange_code
