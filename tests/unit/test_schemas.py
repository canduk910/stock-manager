"""services/schemas/advisory_report_v2.py Pydantic 스키마 단위 테스트."""

import pytest

from services.schemas.advisory_report_v2 import (
    validate_v2_report,
    extract_v2_fields,
    AdvisoryReportV2Schema,
)


def _make_valid_report() -> dict:
    """유효한 v2 리포트 dict."""
    return {
        "schema_version": "v2",
        "종목등급": "A",
        "등급점수": 25,
        "복합점수": 72.5,
        "체제정합성점수": 85.0,
        "종합투자의견": {
            "등급": "A",
            "요약": "강력 매수",
            "근거": ["저평가", "높은 ROE"],
        },
        "전략별평가": {
            "변동성돌파": {"신호": "매수", "근거": "돌파", "목표가": 65000},
            "안전마진": {"신호": "매수", "근거": "할인", "graham_number": 75000, "할인율": 30},
            "추세추종": {"신호": "매수", "근거": "정배열", "추세강도": "강"},
        },
        "기술적시그널": {
            "신호": "매수",
            "해석": "RSI 상승 중",
            "지표별": {"macd": "골든크로스", "rsi": "55", "stoch": "65"},
        },
        "포지션가이드": {
            "등급팩터": 1.0,
            "추천진입가": 50000,
            "손절가": 46000,
            "recommendation": "ENTER",
        },
        "리스크요인": [{"요인": "금리", "설명": "인상 위험"}],
        "투자포인트": [{"포인트": "저평가", "설명": "PBR 0.5"}],
        "Value_Trap_경고": False,
        "Value_Trap_근거": [],
    }


class TestValidateV2Report:
    def test_valid_report(self):
        success, schema, error = validate_v2_report(_make_valid_report())
        assert success is True
        assert schema is not None
        assert error is None
        assert isinstance(schema, AdvisoryReportV2Schema)

    def test_invalid_grade(self):
        report = _make_valid_report()
        report["종목등급"] = "X"
        success, schema, error = validate_v2_report(report)
        assert success is False
        assert schema is None
        assert error is not None

    def test_score_out_of_range(self):
        report = _make_valid_report()
        report["등급점수"] = 30  # max 28
        success, schema, error = validate_v2_report(report)
        assert success is False

    def test_composite_out_of_range(self):
        report = _make_valid_report()
        report["복합점수"] = 101  # max 100
        success, schema, error = validate_v2_report(report)
        assert success is False

    def test_regime_alignment_out_of_range(self):
        report = _make_valid_report()
        report["체제정합성점수"] = -1  # min 0
        success, schema, error = validate_v2_report(report)
        assert success is False

    def test_missing_required_field(self):
        report = _make_valid_report()
        del report["종합투자의견"]
        success, schema, error = validate_v2_report(report)
        assert success is False

    def test_extra_keys_allowed(self):
        report = _make_valid_report()
        report["추가_필드"] = "허용"
        success, schema, error = validate_v2_report(report)
        assert success is True

    def test_valid_all_grades(self):
        for grade in ["A", "B+", "B", "C", "D"]:
            report = _make_valid_report()
            report["종목등급"] = grade
            success, _, _ = validate_v2_report(report)
            assert success is True

    def test_boundary_scores(self):
        report = _make_valid_report()
        report["등급점수"] = 0
        report["복합점수"] = 0
        report["체제정합성점수"] = 0
        success, _, _ = validate_v2_report(report)
        assert success is True

        report["등급점수"] = 28
        report["복합점수"] = 100
        report["체제정합성점수"] = 100
        success, _, _ = validate_v2_report(report)
        assert success is True


class TestExtractV2Fields:
    def test_full_extraction(self):
        report = _make_valid_report()
        fields = extract_v2_fields(report)
        assert fields["grade"] == "A"
        assert fields["grade_score"] == 25
        assert fields["composite_score"] == 72.5
        assert fields["regime_alignment"] == 85.0
        assert fields["schema_version"] == "v2"
        assert fields["value_trap_warning"] is False

    def test_partial_data(self):
        fields = extract_v2_fields({"종목등급": "B", "등급점수": 18})
        assert fields["grade"] == "B"
        assert fields["grade_score"] == 18
        assert fields["composite_score"] is None
        assert fields["regime_alignment"] is None
        assert fields["schema_version"] == "v1"  # default
        assert fields["value_trap_warning"] is False  # default

    def test_empty_dict(self):
        fields = extract_v2_fields({})
        assert fields["grade"] is None
        assert fields["grade_score"] is None
        assert fields["schema_version"] == "v1"

    def test_value_trap_true(self):
        report = _make_valid_report()
        report["Value_Trap_경고"] = True
        report["Value_Trap_근거"] = ["ROE 하락", "FCF 음수"]
        fields = extract_v2_fields(report)
        assert fields["value_trap_warning"] is True
