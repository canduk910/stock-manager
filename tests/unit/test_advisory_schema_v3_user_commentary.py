"""사용자 코멘트 평가 Pydantic 스키마 검증.

R1 RED: AgreePoint/DisagreePoint/UserCommentaryEvaluation 모델 + AdvisoryReportV3Schema 통합.
- strength 1~10 범위 검증 (0/11=ValidationError, 1/10=통과)
- overall_stance Literal 5단계
- agree_points/disagree_points 0~5개 제한
- AdvisoryReportV3Schema에서 user_commentary_evaluation Optional (누락 통과)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestAgreePointSchema:
    def test_valid_strength_1(self):
        from services.schemas.advisory_report_v3 import AgreePoint
        ap = AgreePoint(point="P", evidence="E", strength=1)
        assert ap.strength == 1

    def test_valid_strength_10(self):
        from services.schemas.advisory_report_v3 import AgreePoint
        ap = AgreePoint(point="P", evidence="E", strength=10)
        assert ap.strength == 10

    def test_invalid_strength_zero(self):
        from services.schemas.advisory_report_v3 import AgreePoint
        with pytest.raises(ValidationError):
            AgreePoint(point="P", evidence="E", strength=0)

    def test_invalid_strength_eleven(self):
        from services.schemas.advisory_report_v3 import AgreePoint
        with pytest.raises(ValidationError):
            AgreePoint(point="P", evidence="E", strength=11)


class TestDisagreePointSchema:
    def test_valid(self):
        from services.schemas.advisory_report_v3 import DisagreePoint
        dp = DisagreePoint(point="반박", evidence="근거", strength=7)
        assert dp.strength == 7

    def test_invalid_strength_negative(self):
        from services.schemas.advisory_report_v3 import DisagreePoint
        with pytest.raises(ValidationError):
            DisagreePoint(point="반박", evidence="근거", strength=-1)


class TestUserCommentaryEvaluationSchema:
    def test_valid_minimal(self):
        from services.schemas.advisory_report_v3 import UserCommentaryEvaluation
        uce = UserCommentaryEvaluation(
            user_comment="가설",
            overall_stance="balanced",
            agree_points=[],
            disagree_points=[],
            summary="요약",
        )
        assert uce.overall_stance == "balanced"
        assert uce.agree_points == []
        assert uce.disagree_points == []

    def test_valid_full(self):
        from services.schemas.advisory_report_v3 import (
            AgreePoint, DisagreePoint, UserCommentaryEvaluation,
        )
        uce = UserCommentaryEvaluation(
            user_comment="AI 사이클 수혜",
            overall_stance="strong_agree",
            agree_points=[AgreePoint(point="P1", evidence="E1", strength=8)],
            disagree_points=[DisagreePoint(point="P2", evidence="E2", strength=4)],
            summary="동의 우위",
        )
        assert uce.agree_points[0].strength == 8
        assert uce.disagree_points[0].strength == 4

    def test_invalid_overall_stance(self):
        from services.schemas.advisory_report_v3 import UserCommentaryEvaluation
        with pytest.raises(ValidationError):
            UserCommentaryEvaluation(
                user_comment="x",
                overall_stance="not_a_stance",
                agree_points=[],
                disagree_points=[],
                summary="s",
            )

    def test_overall_stance_all_5_levels(self):
        from services.schemas.advisory_report_v3 import UserCommentaryEvaluation
        for stance in ["strong_agree", "agree", "balanced", "disagree", "strong_disagree"]:
            uce = UserCommentaryEvaluation(
                user_comment="x",
                overall_stance=stance,
                agree_points=[],
                disagree_points=[],
                summary="s",
            )
            assert uce.overall_stance == stance


class TestAdvisoryReportV3SchemaUserCommentary:
    """AdvisoryReportV3Schema에 user_commentary_evaluation Optional 통합."""

    def _base_payload(self) -> dict:
        return {
            "schema_version": "v3",
            "종목등급": "B",
            "등급점수": 18,
            "복합점수": 60.0,
            "체제정합성점수": 70.0,
            "종합투자의견": {"등급": "중립", "요약": "요약", "근거": ["근거1"]},
            "전략별평가": {
                "변동성돌파": {"신호": "중립", "근거": "ATR 평이"},
                "안전마진": {"신호": "중립", "근거": "Graham 5%"},
                "추세추종": {"신호": "중립", "근거": "MA 횡보", "추세강도": "약"},
            },
            "기술적시그널": {
                "신호": "중립",
                "해석": "보합",
                "지표별": {"macd": "중립", "rsi": "중립", "stoch": "중립"},
            },
            "리스크요인": [],
            "투자포인트": [],
        }

    def test_user_commentary_missing_passes(self):
        """user_commentary_evaluation 누락 → Optional이므로 검증 통과."""
        from services.schemas.advisory_report_v3 import AdvisoryReportV3Schema
        payload = self._base_payload()
        schema = AdvisoryReportV3Schema.model_validate(payload)
        assert schema.user_commentary_evaluation is None

    def test_user_commentary_present_passes(self):
        from services.schemas.advisory_report_v3 import AdvisoryReportV3Schema
        payload = self._base_payload()
        payload["user_commentary_evaluation"] = {
            "user_comment": "가설",
            "overall_stance": "agree",
            "agree_points": [
                {"point": "P1", "evidence": "재무", "strength": 7},
            ],
            "disagree_points": [
                {"point": "P2", "evidence": "매크로", "strength": 4},
            ],
            "summary": "동의 우위",
        }
        schema = AdvisoryReportV3Schema.model_validate(payload)
        assert schema.user_commentary_evaluation is not None
        assert schema.user_commentary_evaluation.overall_stance == "agree"
        assert schema.user_commentary_evaluation.agree_points[0].strength == 7

    def test_user_commentary_strength_out_of_range_fails(self):
        from services.schemas.advisory_report_v3 import AdvisoryReportV3Schema
        payload = self._base_payload()
        payload["user_commentary_evaluation"] = {
            "user_comment": "가설",
            "overall_stance": "agree",
            "agree_points": [
                {"point": "P1", "evidence": "재무", "strength": 11},
            ],
            "disagree_points": [],
            "summary": "summary",
        }
        with pytest.raises(ValidationError):
            AdvisoryReportV3Schema.model_validate(payload)
