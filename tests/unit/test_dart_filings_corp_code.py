"""screener.dart.fetch_filings() corp_code 파라미터 회귀 테스트.

corp_code 없이 365일 호출 시 DART 정책 위반(status=100)으로 실패하던
버그(2026-05-09 DB손해보험 005830 진단)의 근본 수정 가드 검증.
"""

from unittest.mock import MagicMock, patch

from screener import dart


def _make_mock_response(items=None, status="000"):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "status": status,
        "list": items or [],
        "total_page": 1,
    }
    return resp


def test_fetch_filings_includes_corp_code_in_params():
    """corp_code 키워드 인자는 DART API params에 포함된다."""
    captured_params = {}

    def fake_get(url, params, timeout):
        captured_params.update(params)
        return _make_mock_response(items=[])

    with patch("screener.dart._dart_get", side_effect=fake_get), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"):
        dart.fetch_filings("20250101", "20251231", corp_code="00126380")

    assert captured_params.get("corp_code") == "00126380"
    assert captured_params.get("bgn_de") == "20250101"
    assert captured_params.get("end_de") == "20251231"


def test_fetch_filings_omits_corp_code_when_none():
    """corp_code 미지정 시 params에 키 자체가 없어야 한다 (백워드 호환)."""
    captured_params = {}

    def fake_get(url, params, timeout):
        captured_params.update(params)
        return _make_mock_response(items=[])

    with patch("screener.dart._dart_get", side_effect=fake_get), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"):
        dart.fetch_filings("20250101", "20250131")  # corp_code 미지정

    assert "corp_code" not in captured_params


def test_fetch_filings_cache_key_includes_corp_code():
    """corp_code 별로 캐시 키가 분리되어야 한다 (다른 회사 = 다른 결과)."""
    from screener import cache as dart_cache

    saved_keys: list[str] = []

    def fake_set_cached(key, value):
        saved_keys.append(key)

    with patch("screener.dart._dart_get", return_value=_make_mock_response(items=[])), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached", side_effect=fake_set_cached):
        # 과거 날짜 (use_cache=True 트리거)
        dart.fetch_filings("20240101", "20240131", corp_code="00126380")
        dart.fetch_filings("20240101", "20240131", corp_code="00164742")
        dart.fetch_filings("20240101", "20240131")  # corp_code None

    assert any("00126380" in k for k in saved_keys)
    assert any("00164742" in k for k in saved_keys)
    # corp_code None은 suffix 없음
    assert any(k.endswith("20240101:20240131") for k in saved_keys)


def test_fetch_filings_backward_compat_positional():
    """기존 호출자(routers/earnings.py 등)는 키워드 인자 없이 호출. 정상 동작."""
    with patch("screener.dart._dart_get", return_value=_make_mock_response(items=[])), \
         patch("screener.dart._get_api_key", return_value="dummy"):
        # 예외 없이 빈 리스트 반환
        result = dart.fetch_filings("20250101", "20250131")
        assert result == []
