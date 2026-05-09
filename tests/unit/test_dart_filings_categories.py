"""screener.dart.fetch_filings (Phase 2A) 카테고리 다중 필터 회귀 테스트.

2026-05-10 ValueScreener 자문: pblntf_ty 다중 카테고리 — A/B/D/F default ON.
- 백워드 호환: pblntf_types 미지정 → ['A'] 단독 (기존 동작 보존)
- 응답 dict에 category_code/category 키 추가
- 카테고리별 별도 호출 후 머지 + rcept_no 중복 제거
"""

from unittest.mock import MagicMock, patch

import pytest

from screener import dart


def _make_mock_response(items=None, status="000", total_page=1):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "status": status,
        "list": items or [],
        "total_page": total_page,
    }
    return resp


# ── 백워드 호환 ──────────────────────────────────────────────────

def test_default_call_uses_pblntf_ty_A():
    """pblntf_types 미지정 → 단일 호출, params에 pblntf_ty='A' (기존 동작)."""
    captured_params = []

    def fake_get(url, params, timeout):
        captured_params.append(dict(params))
        return _make_mock_response(items=[])

    with patch("screener.dart._dart_get", side_effect=fake_get), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"):
        dart.fetch_filings("20250101", "20250131")

    assert len(captured_params) == 1
    assert captured_params[0]["pblntf_ty"] == "A"


def test_backward_compat_no_category_field_when_default():
    """기존 호출 결과에도 category_code/category 키 추가 (응답 shape 진화)."""
    item = {
        "stock_code": "005930", "corp_name": "삼성전자",
        "report_nm": "사업보고서 (2024.12)", "rcept_no": "20250320000001",
        "rcept_dt": "20250320", "flr_nm": "삼성전자",
    }
    with patch("screener.dart._dart_get", return_value=_make_mock_response(items=[item])), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"):
        result = dart.fetch_filings("20250101", "20250131")
    assert len(result) == 1
    assert result[0]["category_code"] == "A"
    assert result[0]["category"] == "정기공시"
    assert result[0]["report_type"] == "사업보고서"


# ── 카테고리 다중 호출 ───────────────────────────────────────────

def test_multi_categories_call_per_type():
    """pblntf_types=['A','B','F'] → 카테고리별 3회 호출 (DART API 단일만 받음)."""
    called_types = []

    def fake_get(url, params, timeout):
        called_types.append(params["pblntf_ty"])
        return _make_mock_response(items=[])

    with patch("screener.dart._dart_get", side_effect=fake_get), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"), \
         patch("screener.dart.time.sleep"):
        dart.fetch_filings("20250101", "20250131", pblntf_types=["A", "B", "F"])

    assert sorted(called_types) == ["A", "B", "F"]


def test_multi_categories_dedupe_by_rcept_no():
    """카테고리 간 동일 rcept_no 중복 제거."""
    item = {
        "stock_code": "005930", "corp_name": "삼성전자",
        "report_nm": "[기재정정]사업보고서", "rcept_no": "20250101000001",
        "rcept_dt": "20250101", "flr_nm": "삼성전자",
    }

    def fake_get(url, params, timeout):
        # 동일 rcept_no가 A, B 양쪽에 등장하는 시뮬레이션
        return _make_mock_response(items=[dict(item)])

    with patch("screener.dart._dart_get", side_effect=fake_get), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"), \
         patch("screener.dart.time.sleep"):
        result = dart.fetch_filings("20250101", "20250131", pblntf_types=["A", "B"])

    assert len(result) == 1
    # 첫 번째 호출(A)이 sorted된 카테고리 순서로 먼저 → A로 분류됨
    assert result[0]["category_code"] == "A"


def test_response_includes_category_code_and_label():
    """카테고리 코드 + 한글 라벨 응답 키 추가."""
    item_b = {
        "stock_code": "005930", "corp_name": "삼성전자",
        "report_nm": "유상증자결정", "rcept_no": "20250115000001",
        "rcept_dt": "20250115", "flr_nm": "삼성전자",
    }

    with patch("screener.dart._dart_get", return_value=_make_mock_response(items=[item_b])), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"), \
         patch("screener.dart.time.sleep"):
        result = dart.fetch_filings("20250101", "20250131", pblntf_types=["B"])

    assert len(result) == 1
    assert result[0]["category_code"] == "B"
    assert result[0]["category"] == "주요사항보고"
    # 비-A 카테고리는 report_nm을 그대로 노출 (정기공시 키워드 없으므로)
    assert result[0]["report_type"] == "유상증자결정"


def test_non_a_category_preserves_report_nm_when_no_keyword_match():
    """비-A 카테고리는 _classify_report 키워드 매칭 안 돼도 report_nm 그대로."""
    item = {
        "stock_code": "005930", "corp_name": "삼성전자",
        "report_nm": "주요사항보고서(자기주식취득결정)", "rcept_no": "20250120000001",
        "rcept_dt": "20250120", "flr_nm": "삼성전자",
    }
    with patch("screener.dart._dart_get", return_value=_make_mock_response(items=[item])), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"), \
         patch("screener.dart.time.sleep"):
        result = dart.fetch_filings("20250101", "20250131", pblntf_types=["B"])
    assert result[0]["report_type"] == "주요사항보고서(자기주식취득결정)"


def test_a_category_filters_non_periodic_reports():
    """A 카테고리는 사업/반기/분기 키워드 외 제외 (기존 동작 보존)."""
    items = [
        {"stock_code": "005930", "report_nm": "유상증자결정",
         "rcept_no": "1", "corp_name": "삼성", "rcept_dt": "20250101", "flr_nm": "삼성"},
        {"stock_code": "005930", "report_nm": "사업보고서 (2024.12)",
         "rcept_no": "2", "corp_name": "삼성", "rcept_dt": "20250320", "flr_nm": "삼성"},
    ]
    with patch("screener.dart._dart_get", return_value=_make_mock_response(items=items)), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"):
        result = dart.fetch_filings("20250101", "20250331", pblntf_types=["A"])
    assert len(result) == 1
    assert result[0]["report_type"] == "사업보고서"


# ── 캐시 키 분리 ─────────────────────────────────────────────────

def test_cache_key_separates_by_categories():
    """['A'] vs ['A','B'] vs 미지정 — 캐시 키 분리."""
    saved_keys: list[str] = []

    with patch("screener.dart._dart_get", return_value=_make_mock_response(items=[])), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached", side_effect=lambda k, v: saved_keys.append(k)), \
         patch("screener.dart.time.sleep"):
        # 과거 날짜로 use_cache=True 트리거
        dart.fetch_filings("20240101", "20240131")
        dart.fetch_filings("20240101", "20240131", pblntf_types=["A"])
        dart.fetch_filings("20240101", "20240131", pblntf_types=["A", "B"])

    # 미지정 → suffix 없음
    assert any(k == "dart_filings:20240101:20240131" for k in saved_keys)
    # 명시 ['A'] → cats 포함
    assert any("cats=A" in k for k in saved_keys if "cats=" in k)
    # ['A','B'] → cats=A,B
    assert any("cats=A,B" in k for k in saved_keys)


def test_invalid_categories_silently_filtered():
    """무효 코드는 silent skip (라우터에서 422로 차단되므로 함수 레벨은 graceful)."""
    captured_types = []

    def fake_get(url, params, timeout):
        captured_types.append(params["pblntf_ty"])
        return _make_mock_response(items=[])

    with patch("screener.dart._dart_get", side_effect=fake_get), \
         patch("screener.dart._get_api_key", return_value="dummy"), \
         patch("screener.dart.get_cached", return_value=None), \
         patch("screener.dart.set_cached"), \
         patch("screener.dart.time.sleep"):
        # Z는 무효 → A만 남음, 빈 리스트 되면 ['A'] fallback
        dart.fetch_filings("20250101", "20250131", pblntf_types=["Z", "A"])

    assert "A" in captured_types
    assert "Z" not in captured_types


def test_default_categories_constant():
    """ValueScreener 권고 default ON 카테고리 — 코드 상수 검증."""
    assert dart.DEFAULT_CATEGORIES == ("A", "B", "D", "F")
    assert "A" in dart.ALLOWED_CATEGORIES
    assert "Z" not in dart.ALLOWED_CATEGORIES
    assert dart.CATEGORY_LABELS["F"] == "외부감사관련"
