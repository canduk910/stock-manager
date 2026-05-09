"""yf_client._resolve_yf_code() 회귀 테스트.

KR raw 코드(6자리 숫자)가 yfinance에 그대로 전달되어 404가 발생하던 버그
(2026-05-09 DB손해보험 005830 진단)의 근본 수정 가드 검증.
"""

from unittest.mock import patch

from stock import yf_client


def test_us_ticker_passthrough():
    """US 알파벳 ticker는 그대로 통과."""
    assert yf_client._resolve_yf_code("AAPL") == "AAPL"
    assert yf_client._resolve_yf_code("aapl") == "AAPL"
    assert yf_client._resolve_yf_code("BRK.B") == "BRK.B"


def test_macro_symbol_passthrough():
    """매크로 심볼(`^`, `=`, `.`)은 그대로 통과."""
    assert yf_client._resolve_yf_code("^TNX") == "^TNX"
    assert yf_client._resolve_yf_code("GC=F") == "GC=F"
    assert yf_client._resolve_yf_code("USDKRW=X") == "USDKRW=X"


def test_already_resolved_kr_ticker_passthrough():
    """이미 .KS/.KQ suffix가 있는 코드는 그대로 통과 (무한 재귀 방지)."""
    assert yf_client._resolve_yf_code("005930.KS") == "005930.KS"
    assert yf_client._resolve_yf_code("293490.KQ") == "293490.KQ"


def test_kr_raw_code_resolves_to_ks():
    """6자리 KR raw 코드는 _kr_yf_ticker_str로 변환."""
    with patch("stock.market._kr_yf_ticker_str", return_value="005830.KS"):
        assert yf_client._resolve_yf_code("005830") == "005830.KS"


def test_kr_raw_code_resolves_to_kq():
    """KOSDAQ도 정상 변환."""
    with patch("stock.market._kr_yf_ticker_str", return_value="293490.KQ"):
        assert yf_client._resolve_yf_code("293490") == "293490.KQ"


def test_kr_resolve_failure_returns_raw():
    """변환 실패 시 raw code 반환 (yfinance가 404 처리, graceful)."""
    with patch("stock.market._kr_yf_ticker_str", return_value=None):
        assert yf_client._resolve_yf_code("999999") == "999999"


def test_kr_resolve_exception_returns_raw():
    """예외 발생 시도 raw code 반환 (graceful)."""
    with patch("stock.market._kr_yf_ticker_str", side_effect=RuntimeError("boom")):
        assert yf_client._resolve_yf_code("005830") == "005830"


def test_empty_input_passthrough():
    """빈 문자열/None은 그대로 반환 (변환 시도 안 함)."""
    assert yf_client._resolve_yf_code("") == ""
    assert yf_client._resolve_yf_code(None) is None


def test_non_six_digit_number_passthrough():
    """6자리가 아닌 숫자는 그대로 반환 (KR 형식 아님)."""
    assert yf_client._resolve_yf_code("12345") == "12345"
    assert yf_client._resolve_yf_code("1234567") == "1234567"


def test_ticker_helper_applies_resolve():
    """_ticker()가 _resolve_yf_code를 거치는지 확인 — KR raw 코드 자동 보호."""
    captured = {}

    def fake_uncached(code):
        captured["code"] = code
        class Dummy:
            pass
        return Dummy()

    with patch("stock.market._kr_yf_ticker_str", return_value="005830.KS"), \
         patch.object(yf_client, "_ticker_cached", side_effect=fake_uncached):
        yf_client._ticker("005830")

    assert captured["code"] == "005830.KS"
