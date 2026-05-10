"""dart_segments (Phase B — DART 사업보고서 본문 파싱) 회귀 테스트.

2026-05-10 ValueScreener: GPT 추정(Phase A)의 신빙성 한계 해소.
DART document.xml → 영업의 현황 섹션 → 부문별 매출 표 추출 → GPT 정규화.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from stock import dart_segments


def _mock_chat_response(content: str) -> MagicMock:
    msg = MagicMock(); msg.content = content
    choice = MagicMock(); choice.message = msg
    resp = MagicMock(); resp.choices = [choice]
    return resp


@pytest.fixture(autouse=True)
def _clear_cache():
    yield
    try:
        from stock.cache import delete_prefix
        delete_prefix("dart:segments:")
        delete_prefix("advisor:segments_history_dart:")
    except Exception:
        pass


# ── 섹션/표 추출 헬퍼 ────────────────────────────────────────────

def test_extract_revenue_section_finds_header():
    """'영업의 현황' 헤더 매칭 + 다음 큰 섹션 헤더까지 추출."""
    xml = (
        "<DOCUMENT>...prefix..."
        "<TITLE>2. 영업의 현황</TITLE>"
        "<TABLE>매출 데이터 표</TABLE>"
        "<TITLE>III. 재무에 관한 사항</TITLE>"
        "...suffix..."
        "</DOCUMENT>"
    )
    section = dart_segments._extract_revenue_section(xml)
    assert section is not None
    assert "영업의 현황" in section
    assert "매출 데이터 표" in section
    # 다음 섹션 헤더는 제외
    assert "재무에 관한 사항" not in section


def test_extract_revenue_section_returns_none_when_no_header():
    """헤더 없으면 None."""
    xml = "<DOCUMENT>일반 텍스트만</DOCUMENT>"
    assert dart_segments._extract_revenue_section(xml) is None


def test_table_to_text_strips_tags():
    """<TABLE> XML → 행/열 평탄화 텍스트 (`|` 구분)."""
    table_xml = """
<TABLE>
<TBODY>
<TR><TD>구분</TD><TD>매출액</TD><TD>비중</TD></TR>
<TR><TD>장기보험</TD><TD>10,000</TD><TD>50%</TD></TR>
<TR><TD>자동차보험</TD><TD>5,000</TD><TD>25%</TD></TR>
</TBODY>
</TABLE>
"""
    text = dart_segments._table_to_text(table_xml)
    assert "구분 | 매출액 | 비중" in text
    assert "장기보험 | 10,000 | 50%" in text
    assert "자동차보험 | 5,000 | 25%" in text
    # 태그 제거 확인
    assert "<" not in text
    assert ">" not in text


def test_extract_table_candidates_filters_by_keyword():
    """키워드(매출/사업부문/장기보험 등) 포함 표만 후보."""
    section = """
<TABLE><TBODY>
<TR><TD>일반 정보 표</TD><TD>값1</TD></TR>
<TR><TD>일반 정보2</TD><TD>값2</TD></TR>
<TR><TD>일반 정보3</TD><TD>값3</TD></TR>
<TR><TD>일반 정보4</TD><TD>값4</TD></TR>
<TR><TD>일반 정보5</TD><TD>값5</TD></TR>
</TBODY></TABLE>
<TABLE><TBODY>
<TR><TD>사업부문</TD><TD>매출액</TD></TR>
<TR><TD>장기보험</TD><TD>10000</TD></TR>
<TR><TD>자동차보험</TD><TD>5000</TD></TR>
<TR><TD>일반보험</TD><TD>2000</TD></TR>
<TR><TD>합계</TD><TD>17000</TD></TR>
</TBODY></TABLE>
"""
    candidates = dart_segments._extract_table_candidates(section)
    assert len(candidates) == 1
    assert "장기보험" in candidates[0]
    # 키워드 없는 첫 표는 제외
    assert "일반 정보 표" not in candidates[0]


def test_extract_table_candidates_skips_too_small_or_large():
    """행 5개 미만 또는 4000자 초과 표는 제외."""
    section_small = "<TABLE><TBODY><TR><TD>매출 단일행</TD></TR></TBODY></TABLE>"
    candidates = dart_segments._extract_table_candidates(section_small)
    assert candidates == []


# ── GPT 정규화 ──────────────────────────────────────────────────

def test_normalize_with_gpt_parses_segments():
    """GPT JSON 응답 → segments 리스트 정상 파싱."""
    gpt_json = json.dumps({
        "segments": [
            {"segment": "장기보험", "revenue_pct": 60, "raw_amount": 6000000000000},
            {"segment": "자동차보험", "revenue_pct": 25, "raw_amount": 2500000000000},
            {"segment": "일반보험", "revenue_pct": 15, "raw_amount": 1500000000000},
        ]
    })
    with patch("stock.dart_segments.OPENAI_API_KEY", "sk-test"), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response(gpt_json)):
        result = dart_segments._normalize_with_gpt(["테이블 텍스트"], 2024, "DB손해보험", user_id=1)
    assert len(result) == 3
    assert result[0]["segment"] == "장기보험"
    assert result[0]["revenue_pct"] == 60.0
    assert result[0]["note"] == "DART실측"
    assert result[0]["raw_amount"] == 6000000000000


def test_normalize_with_gpt_returns_none_when_no_api_key():
    """OPENAI_API_KEY 없으면 None."""
    with patch("stock.dart_segments.OPENAI_API_KEY", ""):
        assert dart_segments._normalize_with_gpt(["x"], 2024, "x", user_id=1) is None


def test_normalize_with_gpt_handles_empty_segments():
    """GPT가 빈 segments 반환 → None."""
    gpt_json = json.dumps({"segments": []})
    with patch("stock.dart_segments.OPENAI_API_KEY", "sk-test"), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response(gpt_json)):
        result = dart_segments._normalize_with_gpt(["x"], 2024, "x", user_id=1)
    assert result is None


# ── 단일 연도 통합 ───────────────────────────────────────────────

def test_fetch_segments_dart_single_no_corp_code():
    """corp_code None → 즉시 None (네트워크 호출 없음)."""
    assert dart_segments.fetch_segments_dart_single("", "x", 2024) is None


def test_fetch_segments_dart_single_uses_cache():
    """캐시 hit 시 재호출 없이 반환."""
    cached_segs = [{"segment": "장기보험", "revenue_pct": 60, "raw_amount": None, "note": "DART실측"}]
    with patch("stock.dart_segments.get_cached", return_value=cached_segs), \
         patch("stock.dart_segments._find_business_report_rcept") as rcept_mock:
        result = dart_segments.fetch_segments_dart_single("00159102", "DB손해보험", 2024)
    assert result == cached_segs
    rcept_mock.assert_not_called()


def test_fetch_segments_dart_single_no_rcept_fallback():
    """rcept_no 미발견 → None + 1일 stale 캐시."""
    saved = []
    with patch("stock.dart_segments.get_cached", return_value=None), \
         patch("stock.dart_segments.set_cached", side_effect=lambda k, v, **kw: saved.append((k, v))), \
         patch("stock.dart_segments._find_business_report_rcept", return_value=None):
        result = dart_segments.fetch_segments_dart_single("00159102", "DB손해보험", 2024)
    assert result is None
    assert saved and saved[0][1] == []  # stale empty 저장


# ── 5년치 진입점 ─────────────────────────────────────────────────

def test_fetch_segments_history_dart_no_corp_code():
    """corp_code 미존재 → 빈 결과 (네트워크 호출 없음)."""
    with patch("stock.dart_segments.get_cached", return_value=None), \
         patch("stock.dart_segments._fetch_corp_code", return_value=None):
        result = dart_segments.fetch_segments_history_dart("999999", "Unknown", years=5)
    assert result["years_data"] == []
    assert result["covered_years"] == 0
    assert result["source"] == "dart_parsed"


def test_fetch_segments_history_dart_partial_success():
    """일부 연도만 DART 파싱 성공 → covered_years 정확."""
    def fake_single(corp_code, name, year, user_id=None):
        if year >= 2023:
            return [{"segment": "장기보험", "revenue_pct": 60, "raw_amount": None, "note": "DART실측"}]
        return None  # 과거 연도 실패

    with patch("stock.dart_segments.get_cached", return_value=None), \
         patch("stock.dart_segments.set_cached"), \
         patch("stock.dart_segments._fetch_corp_code", return_value="00159102"), \
         patch("stock.dart_segments.fetch_segments_dart_single", side_effect=fake_single):
        result = dart_segments.fetch_segments_history_dart("005830", "DB손해보험", years=5)

    assert result["covered_years"] >= 1
    assert all(y["year"] >= 2023 for y in result["years_data"])
    assert result["source"] == "dart_parsed"


# ── advisory_fetcher 흐름 통합 (Phase A → Phase B 우선) ───────────

def test_advisory_fetcher_uses_dart_first_when_available():
    """DART 파싱 성공 시 GPT 호출 안 함 (Phase B 우선)."""
    from stock import advisory_fetcher

    dart_result = {
        "years_data": [{"year": 2024, "segments": [{"segment": "x", "revenue_pct": 100, "raw_amount": None, "note": "DART실측"}]}],
        "highlights": {"growing": [], "shrinking": []},
        "confidence": "high",
        "source": "dart_parsed",
        "covered_years": 1,
    }
    with patch("stock.cache.get_cached", return_value=None), \
         patch("stock.cache.set_cached"), \
         patch("stock.dart_segments.fetch_segments_history_dart", return_value=dart_result), \
         patch("services.ai_gateway.call_openai_chat") as gpt_mock:
        result = advisory_fetcher.fetch_segments_history_kr("005830", "DB손해보험", years=5)

    assert result["source"] == "dart_parsed"
    assert result["confidence"] == "high"
    gpt_mock.assert_not_called()


def test_advisory_fetcher_falls_back_to_gpt_on_dart_failure():
    """DART 파싱 실패 (years_data 빈 배열) → GPT fallback."""
    from stock import advisory_fetcher

    dart_empty = {"years_data": [], "highlights": {"growing": [], "shrinking": []},
                  "confidence": "high", "source": "dart_parsed", "covered_years": 0}
    gpt_json = json.dumps({"years_data": [
        {"year": 2024, "segments": [{"segment": "주력", "revenue_pct": 100}]}
    ]})

    with patch("stock.cache.get_cached", return_value=None), \
         patch("stock.cache.set_cached"), \
         patch("stock.dart_segments.fetch_segments_history_dart", return_value=dart_empty), \
         patch("stock.advisory_fetcher.OPENAI_API_KEY", "sk-test"), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response(gpt_json)):
        result = advisory_fetcher.fetch_segments_history_kr("005830", "DB손해보험", years=5)

    assert result["source"] == "gpt_inference"
    assert result["confidence"] == "low"
    assert len(result["years_data"]) == 1
