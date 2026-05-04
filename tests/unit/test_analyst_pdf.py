"""REQ-ANALYST-01/02/03/12: PDF 본문 요약 모듈 단위 테스트.

Mock: requests.get, pdfplumber.open, ai_gateway.call_openai_chat.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-01: 시스템 프롬프트 6항목 + 환각 방지 + 300자
# ────────────────────────────────────────────────────────────────────────────


def test_system_prompt_has_six_extraction_items():
    """시스템 프롬프트에 6개 추출 항목 명시 + 환각 방지 + 300자 한도."""
    from stock.analyst_pdf import _SUMMARY_SYSTEM_PROMPT
    p = _SUMMARY_SYSTEM_PROMPT
    # 6항목
    assert "catalyst" in p
    assert "risk" in p
    assert "tp_basis" in p or "목표가" in p
    assert "eps_revision" in p or "EPS" in p
    # 환각 방지
    assert "본문에 명시된" in p or "추정" in p or "외삽" in p
    # 300자 한도 강제
    assert "300" in p


def test_response_is_json_format():
    """JSON 형식 응답을 시스템 프롬프트가 강제."""
    from stock.analyst_pdf import _SUMMARY_SYSTEM_PROMPT
    assert "JSON" in _SUMMARY_SYSTEM_PROMPT or "json" in _SUMMARY_SYSTEM_PROMPT


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-02: 길이 임계 + 캐시 (영구)
# ────────────────────────────────────────────────────────────────────────────


def _mock_pdf_bytes(content_type: str = "application/pdf", length: int = 1000):
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"Content-Type": content_type, "Content-Length": str(length)}
    resp.iter_content = lambda chunk_size=8192: [b"%PDF-FAKE\n" * 200]
    resp.raise_for_status = lambda: None
    resp.close = lambda: None
    resp.__enter__ = lambda self: self
    resp.__exit__ = lambda self, *a: None
    return resp


def _mock_pdf_pages(text_chunks):
    """pdfplumber.open(...).__enter__() → pages list of fake pages."""
    pdf = MagicMock()
    pdf.pages = []
    for txt in text_chunks:
        page = MagicMock()
        page.extract_text = MagicMock(return_value=txt)
        pdf.pages.append(page)
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=pdf)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_short_pdf_skips_openai_call():
    """본문 100자 미만 → summary='' + OpenAI 호출 0회."""
    from stock import analyst_pdf

    with patch.object(analyst_pdf, "get_cached", return_value=None), \
         patch.object(analyst_pdf, "set_cached"), \
         patch.object(analyst_pdf.requests, "get", return_value=_mock_pdf_bytes()), \
         patch.object(analyst_pdf.pdfplumber, "open",
                      return_value=_mock_pdf_pages(["Short"])), \
         patch("services.ai_gateway.call_openai_chat") as mock_ai:
        result = analyst_pdf.summarize_one("https://example.com/short.pdf")
        assert result == ""
        mock_ai.assert_not_called()


def test_empty_pdf_returns_empty_summary():
    """빈 PDF → summary=''."""
    from stock import analyst_pdf

    with patch.object(analyst_pdf, "get_cached", return_value=None), \
         patch.object(analyst_pdf, "set_cached"), \
         patch.object(analyst_pdf.requests, "get", return_value=_mock_pdf_bytes()), \
         patch.object(analyst_pdf.pdfplumber, "open",
                      return_value=_mock_pdf_pages([""])), \
         patch("services.ai_gateway.call_openai_chat") as mock_ai:
        result = analyst_pdf.summarize_one("https://example.com/empty.pdf")
        assert result == ""
        mock_ai.assert_not_called()


def test_cache_hit_returns_without_download():
    """캐시 히트 시 다운로드/OpenAI 호출 0회."""
    from stock import analyst_pdf

    cached_summary = "캐시된 요약 본문"
    with patch.object(analyst_pdf, "get_cached", return_value=cached_summary), \
         patch.object(analyst_pdf.requests, "get") as mock_req, \
         patch("services.ai_gateway.call_openai_chat") as mock_ai:
        result = analyst_pdf.summarize_one("https://example.com/cached.pdf")
        assert result == cached_summary
        mock_req.assert_not_called()
        mock_ai.assert_not_called()


def test_cache_key_uses_md5_of_url():
    """캐시 키는 analyst:summary:{md5(pdf_url)}."""
    import hashlib
    from stock import analyst_pdf

    url = "https://example.com/some.pdf"
    expected_key = f"analyst:summary:{hashlib.md5(url.encode()).hexdigest()}"

    captured_keys = []

    def fake_get_cached(key):
        captured_keys.append(key)
        return None

    with patch.object(analyst_pdf, "get_cached", side_effect=fake_get_cached), \
         patch.object(analyst_pdf, "set_cached"), \
         patch.object(analyst_pdf.requests, "get", return_value=_mock_pdf_bytes()), \
         patch.object(analyst_pdf.pdfplumber, "open",
                      return_value=_mock_pdf_pages(["Short"])):
        analyst_pdf.summarize_one(url)
    assert expected_key in captured_keys


def test_long_pdf_calls_openai_once_and_caches():
    """본문 100자 이상 PDF → OpenAI 1회 호출 + 캐시 set 1회."""
    from stock import analyst_pdf

    long_text = "삼성전자는 메모리 가격 반등으로 영업이익 증가 전망. " * 20  # 600+ chars
    json_resp = {
        "catalyst": ["메모리 가격 반등", "HBM 점유율 확대"],
        "risk": ["글로벌 수요 둔화", "부채비율 상승"],
        "tp_basis": "DCF 12% 할인율",
        "eps_revision": "+5% 상향",
    }

    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock()]
    fake_resp.choices[0].message.content = json.dumps(json_resp)
    fake_resp.choices[0].finish_reason = "stop"

    with patch.object(analyst_pdf, "get_cached", return_value=None), \
         patch.object(analyst_pdf, "set_cached") as mock_set, \
         patch.object(analyst_pdf.requests, "get", return_value=_mock_pdf_bytes()), \
         patch.object(analyst_pdf.pdfplumber, "open",
                      return_value=_mock_pdf_pages([long_text])), \
         patch("services.ai_gateway.call_openai_chat",
               return_value=fake_resp) as mock_ai:
        result = analyst_pdf.summarize_one("https://example.com/long.pdf")
        assert result != ""
        mock_ai.assert_called_once()
        mock_set.assert_called_once()


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-03: 시스템 호출 모드 — user_id=None, check_quota=False
# ────────────────────────────────────────────────────────────────────────────


def test_openai_called_as_system_call():
    """ai_gateway 호출 인자 검증: user_id=None, check_quota=False, model=gpt-5.4."""
    from stock import analyst_pdf

    long_text = "본문 내용. " * 50
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock()]
    fake_resp.choices[0].message.content = json.dumps({
        "catalyst": ["a", "b"], "risk": ["c", "d"],
        "tp_basis": "x", "eps_revision": "",
    })
    fake_resp.choices[0].finish_reason = "stop"

    with patch.object(analyst_pdf, "get_cached", return_value=None), \
         patch.object(analyst_pdf, "set_cached"), \
         patch.object(analyst_pdf.requests, "get", return_value=_mock_pdf_bytes()), \
         patch.object(analyst_pdf.pdfplumber, "open",
                      return_value=_mock_pdf_pages([long_text])), \
         patch("services.ai_gateway.call_openai_chat",
               return_value=fake_resp) as mock_ai:
        analyst_pdf.summarize_one("https://example.com/x.pdf")

        kwargs = mock_ai.call_args.kwargs
        assert kwargs.get("user_id") is None
        assert kwargs.get("check_quota") is False
        assert kwargs.get("service_name") == "analyst_summary"
        assert kwargs.get("model") == "gpt-5.4"


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-12: 보안/안정성 가드 — 모든 예외는 빈 요약으로 흡수
# ────────────────────────────────────────────────────────────────────────────


def test_pdf_too_large_returns_empty():
    """Content-Length > 10MB → summary=''."""
    from stock import analyst_pdf

    with patch.object(analyst_pdf, "get_cached", return_value=None), \
         patch.object(analyst_pdf, "set_cached"), \
         patch.object(analyst_pdf.requests, "get",
                      return_value=_mock_pdf_bytes(length=20 * 1024 * 1024)), \
         patch("services.ai_gateway.call_openai_chat") as mock_ai:
        result = analyst_pdf.summarize_one("https://example.com/huge.pdf")
        assert result == ""
        mock_ai.assert_not_called()


def test_pdf_wrong_content_type_returns_empty():
    """Content-Type != application/pdf → summary=''."""
    from stock import analyst_pdf

    with patch.object(analyst_pdf, "get_cached", return_value=None), \
         patch.object(analyst_pdf, "set_cached"), \
         patch.object(analyst_pdf.requests, "get",
                      return_value=_mock_pdf_bytes(content_type="text/html")), \
         patch("services.ai_gateway.call_openai_chat") as mock_ai:
        result = analyst_pdf.summarize_one("https://example.com/notpdf.pdf")
        assert result == ""
        mock_ai.assert_not_called()


def test_pdf_http_error_returns_empty():
    """HTTP 503 → summary=''."""
    from stock import analyst_pdf

    err_resp = MagicMock()
    err_resp.status_code = 503
    err_resp.headers = {}
    err_resp.raise_for_status = MagicMock(side_effect=Exception("503 Service Unavailable"))
    err_resp.close = lambda: None
    err_resp.__enter__ = lambda self: self
    err_resp.__exit__ = lambda self, *a: None

    with patch.object(analyst_pdf, "get_cached", return_value=None), \
         patch.object(analyst_pdf, "set_cached"), \
         patch.object(analyst_pdf.requests, "get", return_value=err_resp), \
         patch("services.ai_gateway.call_openai_chat") as mock_ai:
        result = analyst_pdf.summarize_one("https://example.com/err.pdf")
        assert result == ""
        mock_ai.assert_not_called()


def test_pdfplumber_exception_returns_empty():
    """pdfplumber 파싱 예외(암호화/손상) → summary=''."""
    from stock import analyst_pdf

    bad_cm = MagicMock()
    bad_cm.__enter__ = MagicMock(side_effect=Exception("PDF corrupted"))
    bad_cm.__exit__ = MagicMock(return_value=False)

    with patch.object(analyst_pdf, "get_cached", return_value=None), \
         patch.object(analyst_pdf, "set_cached"), \
         patch.object(analyst_pdf.requests, "get", return_value=_mock_pdf_bytes()), \
         patch.object(analyst_pdf.pdfplumber, "open", return_value=bad_cm), \
         patch("services.ai_gateway.call_openai_chat") as mock_ai:
        result = analyst_pdf.summarize_one("https://example.com/corrupt.pdf")
        assert result == ""
        mock_ai.assert_not_called()


def test_blank_or_invalid_url_returns_empty():
    """빈 URL/None → summary=''."""
    from stock import analyst_pdf

    assert analyst_pdf.summarize_one("") == ""
    assert analyst_pdf.summarize_one(None) == ""


def test_user_agent_header_present():
    """User-Agent 헤더 명시."""
    from stock import analyst_pdf

    captured_headers = {}

    def fake_get(url, **kwargs):
        captured_headers.update(kwargs.get("headers") or {})
        return _mock_pdf_bytes()

    with patch.object(analyst_pdf, "get_cached", return_value=None), \
         patch.object(analyst_pdf, "set_cached"), \
         patch.object(analyst_pdf.requests, "get", side_effect=fake_get), \
         patch.object(analyst_pdf.pdfplumber, "open",
                      return_value=_mock_pdf_pages(["Short"])), \
         patch("services.ai_gateway.call_openai_chat"):
        analyst_pdf.summarize_one("https://example.com/x.pdf")

    ua = captured_headers.get("User-Agent", "")
    assert "Mozilla" in ua or "stock-manager" in ua
