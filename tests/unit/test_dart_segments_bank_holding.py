"""REQ-SEGMENT-01/02/03 — 금융지주 사업개요/매출비중 키워드 + GPT 부문 사전.

도메인 결정 §D-5/D-6 (요건서 _workspace/dev/01_requirements.md).
- §D-5: 8개 키워드 정규식 추가 (부문별 영업이익, 영업 부문 등)
- §D-6: GPT 프롬프트에 금융지주 부문 사전(은행/증권/보험/카드/캐피탈/자산운용/기타) hint
- §D-6: `metric` 필드로 revenue_share / operating_income_share 분기
"""
from __future__ import annotations

import pytest


# ── REQ-SEGMENT-01: 금융지주 키워드 정규식 ─────────────────────────────────

class TestRevenueTablePatternsBankHolding:
    """REQ-SEGMENT-01: 금융지주 사업보고서 표 헤더 키워드 패턴."""

    def test_pattern_부문별_영업이익_matches(self):
        from stock.dart_segments import _REVENUE_TABLE_PATTERNS
        text = "부문별 영업이익 | 은행 | 증권 | 보험"
        assert any(p.search(text) for p in _REVENUE_TABLE_PATTERNS), \
            "부문별 영업이익 헤더가 매칭되어야 함 (KB금융 케이스)"

    def test_pattern_부문별_영업손익_matches(self):
        from stock.dart_segments import _REVENUE_TABLE_PATTERNS
        text = "부문별 영업 손익 변동표"
        assert any(p.search(text) for p in _REVENUE_TABLE_PATTERNS)

    def test_pattern_부문별_총영업이익_matches(self):
        from stock.dart_segments import _REVENUE_TABLE_PATTERNS
        text = "부문별 총영업이익 (단위: 백만원)"
        assert any(p.search(text) for p in _REVENUE_TABLE_PATTERNS)

    def test_pattern_영업_부문_정보_matches(self):
        """IFRS 8 표준 헤더."""
        from stock.dart_segments import _REVENUE_TABLE_PATTERNS
        text = "영업 부문 정보 (당기)"
        assert any(p.search(text) for p in _REVENUE_TABLE_PATTERNS)

    def test_pattern_주요_자회사_matches(self):
        """KB금융 케이스: 주요 자회사 표."""
        from stock.dart_segments import _REVENUE_TABLE_PATTERNS
        text = "주요 자회사 | KB국민은행 | KB증권"
        assert any(p.search(text) for p in _REVENUE_TABLE_PATTERNS)

    def test_pattern_부문별_요약_재무정보_matches(self):
        from stock.dart_segments import _REVENUE_TABLE_PATTERNS
        text = "부문별 요약 재무정보"
        assert any(p.search(text) for p in _REVENUE_TABLE_PATTERNS)

    def test_pattern_그룹_사업_영역_matches(self):
        """신한지주 케이스."""
        from stock.dart_segments import _REVENUE_TABLE_PATTERNS
        text = "그룹 사업 영역 안내"
        assert any(p.search(text) for p in _REVENUE_TABLE_PATTERNS)

    def test_pattern_세그먼트_matches(self):
        from stock.dart_segments import _REVENUE_TABLE_PATTERNS
        text = "세그먼트 정보"
        assert any(p.search(text) for p in _REVENUE_TABLE_PATTERNS)

    def test_general_manufacturing_pattern_still_works_005930_regression(self):
        """삼성전자 등 일반 제조업의 기존 키워드 (제품별/사업부문)도 그대로 매칭."""
        from stock.dart_segments import _REVENUE_TABLE_PATTERNS
        # 기존 패턴 유지 검증
        for text in ["제품별 매출 현황", "사업 부문 정보", "주요 매출 비중"]:
            assert any(p.search(text) for p in _REVENUE_TABLE_PATTERNS), \
                f"일반 제조업 키워드 회귀: {text}"


class TestRevenueSectionPatternsBankHolding:
    """REQ-SEGMENT-01: 섹션 헤더 키워드 패턴."""

    def test_section_pattern_영업_부문_matches(self):
        from stock.dart_segments import _REVENUE_SECTION_PATTERNS
        text = "(2) 영업 부문 구성 안내"
        assert any(p.search(text) for p in _REVENUE_SECTION_PATTERNS)

    def test_section_pattern_세그먼트_정보_matches(self):
        from stock.dart_segments import _REVENUE_SECTION_PATTERNS
        text = "세그먼트 정보"
        assert any(p.search(text) for p in _REVENUE_SECTION_PATTERNS)

    def test_section_pattern_부문별_재무_matches(self):
        from stock.dart_segments import _REVENUE_SECTION_PATTERNS
        text = "부문별 재무 현황"
        assert any(p.search(text) for p in _REVENUE_SECTION_PATTERNS)

    def test_section_existing_pattern_still_works(self):
        """기존 섹션 패턴 (II. 사업의 내용, 영업의 현황) 유지 — 005930 회귀."""
        from stock.dart_segments import _REVENUE_SECTION_PATTERNS
        for text in ["II. 사업의 내용", "Ⅱ. 사업의 내용", "영업의 현황", "사업의 개요"]:
            assert any(p.search(text) for p in _REVENUE_SECTION_PATTERNS), \
                f"기존 섹션 패턴 회귀: {text}"


# ── REQ-SEGMENT-03: metric 필드 분기 ────────────────────────────────────────

class TestMetricFieldInSegments:
    """REQ-SEGMENT-03: segments 응답 metric 필드 분기.

    분기:
      `revenue_share`           — 매출 기준 비중 (일반 기본값)
      `operating_income_share`  — 영업이익 기준 비중 (금융지주 표가 영업이익만 있는 경우)
    """

    def test_normalize_segments_includes_metric_default_revenue_share(self):
        """metric 미지정/일반 케이스 → revenue_share."""
        from stock.dart_segments import _attach_metric_field
        segments = [{"segment": "메모리", "revenue_pct": 60.0}]
        out = _attach_metric_field(segments, metric="revenue_share")
        assert out[0]["metric"] == "revenue_share"

    def test_normalize_segments_includes_metric_operating_income_share(self):
        """금융지주 영업이익 비중인 경우."""
        from stock.dart_segments import _attach_metric_field
        segments = [{"segment": "은행", "revenue_pct": 40.0}]
        out = _attach_metric_field(segments, metric="operating_income_share")
        assert out[0]["metric"] == "operating_income_share"

    def test_metric_default_when_missing(self):
        """metric 미전달 → revenue_share 기본."""
        from stock.dart_segments import _attach_metric_field
        out = _attach_metric_field([{"segment": "A", "revenue_pct": 100}])
        assert out[0]["metric"] == "revenue_share"


# ── REQ-SEGMENT-02: GPT 프롬프트 sector_tier hint ──────────────────────────

class TestGptPromptBankHoldingHint:
    """REQ-SEGMENT-02: sector_tier="bank_holding" 시 GPT 프롬프트 hint 주입.

    프롬프트 빌더에 sector_tier 인자 추가 → bank_holding이면 hint string 포함.
    실제 GPT 호출은 mock으로 회피, 프롬프트 문자열만 검증.
    """

    def test_build_segments_prompt_includes_bank_holding_hint(self):
        from stock.dart_segments import _build_segments_system_prompt
        prompt = _build_segments_system_prompt(sector_tier="bank_holding")
        # 7개 카테고리 명시 hint 검증
        for category in ["은행", "증권", "보험", "카드", "캐피탈", "자산운용", "기타"]:
            assert category in prompt, \
                f"bank_holding hint에 {category} 카테고리 누락"

    def test_build_segments_prompt_no_hint_for_general(self):
        """일반 종목은 기존 hint 없음 (자유 추출)."""
        from stock.dart_segments import _build_segments_system_prompt
        prompt = _build_segments_system_prompt(sector_tier="general")
        # 금융지주 hint 미포함 (회귀 가드)
        assert "은행/증권/보험/카드/캐피탈/자산운용/기타" not in prompt

    def test_build_segments_prompt_no_hint_when_sector_tier_none(self):
        """sector_tier None → 기존 동작."""
        from stock.dart_segments import _build_segments_system_prompt
        prompt = _build_segments_system_prompt(sector_tier=None)
        assert "은행/증권/보험/카드/캐피탈/자산운용/기타" not in prompt
