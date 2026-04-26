"""AI 자문 리포트 v2 응답 JSON Pydantic 검증 스키마.

GPT가 반환한 JSON을 검증하여 타입/범위 오류를 감지.
검증 실패 시 v1 폴백 (기존 동작 유지).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class StrategySignal(BaseModel):
    """전략별 평가 공통."""
    신호: str
    근거: str


class VolatilityBreakout(StrategySignal):
    목표가: Optional[float] = None


class SafetyMargin(StrategySignal):
    graham_number: Optional[float] = None
    할인율: Optional[float] = None


class TrendFollowing(StrategySignal):
    추세강도: str


class StrategyEvaluation(BaseModel):
    변동성돌파: VolatilityBreakout
    안전마진: SafetyMargin
    추세추종: TrendFollowing


class TechnicalIndicatorDetail(BaseModel):
    macd: str
    rsi: str
    stoch: str
    volume: Optional[str] = None
    bb: Optional[str] = None


class TechnicalSignal(BaseModel):
    신호: str
    해석: str
    지표별: TechnicalIndicatorDetail


class PositionGuide(BaseModel):
    등급팩터: Optional[float] = Field(None, ge=0, le=1)
    추천진입가: Optional[float] = None
    진입가근거: Optional[str] = None
    손절가: Optional[float] = None
    손절근거: Optional[str] = None
    # 1차익절가 → JSON 키가 한글이라 alias 불필요 (dict 직접 파싱)
    익절근거: Optional[str] = None
    리스크보상비율: Optional[float] = None
    분할매수제안: Optional[str] = None
    recommendation: Optional[Literal["ENTER", "HOLD", "SKIP"]] = None

    class Config:
        extra = "allow"  # 1차익절가 등 추가 키 허용


class MacroAnalysis(BaseModel):
    """매크로 환경 분석."""
    시장체제해석: str
    금리영향: Optional[str] = None
    섹터전망: Optional[str] = None
    매크로리스크: Optional[str] = None


class ValuationDeepDive(BaseModel):
    """밸류에이션 심화 분석."""
    적정가치: Optional[float] = None
    산출방법: Optional[str] = None
    업종대비: Optional[str] = None
    PEG분석: Optional[str] = None
    밸류에이션판단: str


class ScenarioCase(BaseModel):
    """시나리오 분석 개별 케이스."""
    목표가: Optional[float] = None
    확률: Optional[float] = Field(None, ge=0, le=100)
    근거: str


class ScenarioAnalysis(BaseModel):
    """시나리오 분석 (낙관/기본/비관)."""
    낙관: ScenarioCase
    기본: ScenarioCase
    비관: ScenarioCase


class InvestmentAlternative(BaseModel):
    """관련 투자 대안."""
    유형: str  # ETF, 지수, 원자재, 채권 등
    종목명: str
    코드: Optional[str] = None
    사유: str


class RiskFactor(BaseModel):
    요인: str
    설명: str


class InvestmentPoint(BaseModel):
    포인트: str
    설명: str


class Opinion(BaseModel):
    등급: str
    요약: str
    근거: list[str]


class AdvisoryReportV2Schema(BaseModel):
    """AI 자문 리포트 v2 전체 스키마."""
    schema_version: Literal["v2"] = "v2"
    종목등급: Literal["A", "B+", "B", "C", "D"]
    등급점수: int = Field(ge=0, le=28)
    복합점수: float = Field(ge=0, le=100)
    체제정합성점수: float = Field(ge=0, le=100)
    종합투자의견: Opinion
    전략별평가: StrategyEvaluation
    기술적시그널: TechnicalSignal
    포지션가이드: PositionGuide
    리스크요인: list[RiskFactor]
    투자포인트: list[InvestmentPoint]
    매크로환경분석: Optional[MacroAnalysis] = None
    밸류에이션심화: Optional[ValuationDeepDive] = None
    시나리오분석: Optional[ScenarioAnalysis] = None
    관련투자대안: Optional[list[InvestmentAlternative]] = Field(default_factory=list)
    Value_Trap_경고: bool = False
    Value_Trap_근거: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"  # GPT가 추가 키를 넣을 수 있으므로 허용

    @field_validator("등급점수")
    @classmethod
    def validate_grade_score(cls, v: int) -> int:
        if v < 0 or v > 28:
            raise ValueError(f"등급점수 범위 초과: {v} (0~28)")
        return v

    @field_validator("복합점수", "체제정합성점수")
    @classmethod
    def validate_score_100(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError(f"점수 범위 초과: {v} (0~100)")
        return v


def validate_v2_report(report_dict: dict) -> tuple[bool, Optional[AdvisoryReportV2Schema], Optional[str]]:
    """v2 리포트 검증.

    Returns:
        (success, schema_obj, error_msg)
        - 성공: (True, AdvisoryReportV2Schema, None)
        - 실패: (False, None, "에러 메시지")
    """
    try:
        schema = AdvisoryReportV2Schema.model_validate(report_dict)
        return True, schema, None
    except Exception as e:
        return False, None, str(e)


def extract_v2_fields(report_dict: dict) -> dict:
    """v2 리포트에서 DB 저장용 정량 필드 추출.

    Pydantic 검증 통과 여부와 무관하게, dict에서 키를 직접 추출.
    DB에 저장할 최소 필드만 반환.
    """
    return {
        "grade": report_dict.get("종목등급"),
        "grade_score": report_dict.get("등급점수"),
        "composite_score": report_dict.get("복합점수"),
        "regime_alignment": report_dict.get("체제정합성점수"),
        "schema_version": report_dict.get("schema_version", "v1"),
        "value_trap_warning": report_dict.get("Value_Trap_경고", False),
    }
