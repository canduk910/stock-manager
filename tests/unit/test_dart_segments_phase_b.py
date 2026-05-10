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
    """헤더 매칭 + 종료 헤더까지 추출. 목차/본문 분리(2000자 가드)는 별도 검증."""
    # 본문 섹션 본문이 충분히 길어 다음 섹션 헤더가 2000자 이상 떨어진 상태
    long_body = "본문 매출 데이터 " * 500  # 약 5000자
    xml = (
        "<DOCUMENT>...prefix..."
        "<TITLE>2. 영업의 현황</TITLE>"
        "<TABLE>매출 데이터 표</TABLE>"
        + long_body +
        "<TITLE>III. 재무에 관한 사항</TITLE>"
        "...suffix..."
        "</DOCUMENT>"
    )
    section = dart_segments._extract_revenue_section(xml)
    assert section is not None
    assert "영업의 현황" in section
    assert "매출 데이터 표" in section
    # 다음 섹션 헤더는 제외 (충분히 떨어져 있어 종료 헤더로 인식)
    assert "III. 재무에 관한 사항" not in section


def test_extract_revenue_section_skips_toc_when_body_far():
    """목차의 헤더 + 본문의 헤더 중 본문 우선(rfind 가장 마지막 매칭)."""
    xml = (
        "<DOCUMENT>"
        # 목차 (짧게 등장)
        "<TITLE>II. 사업의 내용</TITLE>"
        "<TITLE>III. 재무에 관한 사항</TITLE>"
        + "...목차 내용 짧음..." +
        # 본문 실체 (멀리)
        "X" * 30000 +
        "<TITLE>II. 사업의 내용</TITLE>"
        "<TABLE>실제 매출 표</TABLE>"
        + "본문 데이터 " * 500 +
        "<TITLE>III. 재무에 관한 사항</TITLE>"
        "</DOCUMENT>"
    )
    section = dart_segments._extract_revenue_section(xml)
    assert section is not None
    # 본문 매출 표 포함 (목차의 짧은 섹션 회피)
    assert "실제 매출 표" in section


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


def test_fetch_segments_history_dart_unified_flow():
    """5년치 통합 정규화 — _normalize_history_unified 1회 호출 (사용자 결정 2026-05-10)."""
    def fake_extract(corp_code, year):
        if year >= 2023:
            return [f"### {year}년 표 텍스트"]
        return []

    normalized = {
        "years": {
            2023: [{"segment": "주력", "revenue_pct": 100, "raw_amount": None, "note": "DART실측"}],
            2024: [{"segment": "주력", "revenue_pct": 100, "raw_amount": None, "note": "DART실측"}],
            2025: [{"segment": "주력", "revenue_pct": 100, "raw_amount": None, "note": "DART실측"}],
        },
        "description": "테스트 회사 사업 설명",
        "keywords": ["테스트", "주력사업"],
    }

    with patch("stock.dart_segments.get_cached", return_value=None), \
         patch("stock.dart_segments.set_cached"), \
         patch("stock.dart_segments._fetch_corp_code", return_value="00159102"), \
         patch("stock.dart_segments._extract_year_tables", side_effect=fake_extract), \
         patch("stock.dart_segments._normalize_history_unified", return_value=normalized) as norm_mock:
        result = dart_segments.fetch_segments_history_dart("005830", "DB손해보험", years=5)

    assert norm_mock.call_count == 1  # 통합 정규화 정확히 1회
    assert result["covered_years"] == 3
    assert all(y["year"] >= 2023 for y in result["years_data"])
    assert result["source"] == "dart_parsed"
    # 사업 개요 + 키워드 포함 (2026-05-10 통합 응답)
    assert result["description"] == "테스트 회사 사업 설명"
    assert "주력사업" in result["keywords"]


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


def test_advisory_fetcher_no_gpt_fallback_when_dart_fails():
    """2026-05-10: DART 실패 시 GPT fallback 제거. 빈 결과 반환 + GPT 호출 0건."""
    from stock import advisory_fetcher

    dart_empty = {"years_data": [], "highlights": {"growing": [], "shrinking": []},
                  "confidence": "high", "source": "dart_parsed", "covered_years": 0}

    with patch("stock.cache.get_cached", return_value=None), \
         patch("stock.cache.set_cached"), \
         patch("stock.dart_segments.fetch_segments_history_dart", return_value=dart_empty), \
         patch("services.ai_gateway.call_openai_chat") as gpt_mock:
        result = advisory_fetcher.fetch_segments_history_kr("005830", "DB손해보험", years=5)

    assert result["years_data"] == []
    assert result["source"] == "dart_parsed"  # fallback 제거 — 항상 DART
    gpt_mock.assert_not_called()  # GPT 호출 0건


def test_normalize_history_unified_calls_gpt_once():
    """5년치 표를 1회 GPT 호출로 통합 정규화 (연도별 명칭 일관성 강제)."""
    from stock import dart_segments

    tables_per_year = {
        2022: ["사업부문 | 매출액\n경유 | 100\n무연휘발유 | 50"],
        2023: ["사업부문 | 매출액\n석유사업 | 150"],
        2025: ["사업부문 | 매출액\n석유사업 | 160"],
    }

    gpt_response = json.dumps({
        "years_data": [
            {"year": 2022, "segments": [{"segment": "석유사업", "revenue_pct": 100}]},
            {"year": 2023, "segments": [{"segment": "석유사업", "revenue_pct": 100}]},
            {"year": 2025, "segments": [{"segment": "석유사업", "revenue_pct": 100}]},
        ],
        "description": "SK이노베이션은 정유 사업을 영위.",
        "keywords": ["정유", "에너지"],
    })

    with patch("stock.dart_segments.OPENAI_API_KEY", "sk-test"), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response(gpt_response)) as gpt_mock:
        result = dart_segments._normalize_history_unified(tables_per_year, "SK이노베이션", user_id=1)

    # GPT 정확히 1회 호출 (5년치 통합 + description + keywords)
    assert gpt_mock.call_count == 1
    # 모든 연도가 동일한 부문명 ("석유사업")
    assert result["years"][2022][0]["segment"] == "석유사업"
    assert result["years"][2023][0]["segment"] == "석유사업"
    assert result["years"][2025][0]["segment"] == "석유사업"
    # description/keywords 포함
    assert "정유" in result["description"]
    assert "정유" in result["keywords"]


def test_normalize_history_unified_renormalizes_when_total_exceeds_100():
    """SK이노 2022 결함 — 합계 158% 응답 시 비례 재정규화 (가드)."""
    from stock import dart_segments

    tables_per_year = {2022: ["dummy"]}
    bad_response = json.dumps({
        "years_data": [{"year": 2022, "segments": [
            {"segment": "석유", "revenue_pct": 17.7},
            {"segment": "기타", "revenue_pct": 40.5},
            {"segment": "기초유화", "revenue_pct": 69.7},
            {"segment": "화학소재", "revenue_pct": 30.3},
        ]}],
        "description": "",
        "keywords": [],
    })

    with patch("stock.dart_segments.OPENAI_API_KEY", "sk-test"), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response(bad_response)):
        result = dart_segments._normalize_history_unified(tables_per_year, "SK이노", user_id=1)

    # 비례 재정규화 후 합계 100 (반올림 ±1 허용)
    total = sum(s["revenue_pct"] for s in result["years"][2022])
    assert 99.0 <= total <= 100.5
