"""advisory_service._build_system_prompt + _build_prompt 코멘트 가이드 검증.

R2 RED:
- user_comment 있을 때: 시스템 프롬프트 후미에 가이드 블록 (악마의 변호인 / 1~10 / overall_stance) 포함
- user_comment 없을 때(None/""): 가이드 블록 미포함 (회귀 보호)
- _build_prompt user 메시지에 코멘트 echo (있을 때만)
"""

from __future__ import annotations

import pytest


def _empty_fundamental() -> dict:
    return {
        "income_stmt": [],
        "balance_sheet": [],
        "cashflow": [],
        "metrics": {},
        "forward_estimates": {},
        "valuation_stats": {},
        "quarterly": [],
    }


def _empty_technical() -> dict:
    return {"indicators": {"current_signals": {}}}


class TestBuildSystemPromptUserComment:
    def test_no_comment_no_block(self):
        from services.advisory_service import _build_system_prompt
        prompt = _build_system_prompt("selective", "중립", None)
        assert "사용자 의견" not in prompt
        assert "악마의 변호인" not in prompt

    def test_empty_string_no_block(self):
        from services.advisory_service import _build_system_prompt
        # 빈 문자열도 코멘트 없는 것과 동일하게 처리
        prompt = _build_system_prompt("selective", "중립", None, user_comment="")
        assert "악마의 변호인" not in prompt

    def test_with_comment_includes_guide_block(self):
        from services.advisory_service import _build_system_prompt
        prompt = _build_system_prompt(
            "selective", "중립", None,
            user_comment="이 종목은 AI 사이클 수혜로 향후 12개월 강세",
        )
        # 핵심 키워드 검증
        assert "사용자 의견" in prompt
        assert "악마의 변호인" in prompt
        assert "1~10" in prompt
        assert "agree_points" in prompt
        assert "disagree_points" in prompt
        assert "overall_stance" in prompt
        assert "user_commentary_evaluation" in prompt
        # 코멘트 echo
        assert "AI 사이클 수혜" in prompt

    def test_with_comment_5_levels_listed(self):
        from services.advisory_service import _build_system_prompt
        prompt = _build_system_prompt(
            "selective", "중립", None, user_comment="가설",
        )
        for level in ["strong_agree", "agree", "balanced", "disagree", "strong_disagree"]:
            assert level in prompt


class TestBuildPromptUserCommentEcho:
    def test_no_comment_no_echo(self):
        from services.advisory_service import _build_prompt
        prompt = _build_prompt(
            "005930", "KR", "삼성전자",
            _empty_fundamental(), _empty_technical(),
            graham_data=None, macro_ctx={}, regime="selective",
            regime_desc="중립", strategy_signals=None, research_data={},
            cycle_ctx=None,
        )
        assert "사용자 코멘트 원문" not in prompt

    def test_with_comment_echo(self):
        from services.advisory_service import _build_prompt
        prompt = _build_prompt(
            "005930", "KR", "삼성전자",
            _empty_fundamental(), _empty_technical(),
            graham_data=None, macro_ctx={}, regime="selective",
            regime_desc="중립", strategy_signals=None, research_data={},
            cycle_ctx=None, user_comment="이 종목은 강세입니다",
        )
        assert "사용자 코멘트 원문" in prompt
        assert "이 종목은 강세입니다" in prompt
