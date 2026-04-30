"""AI 자문 리포트 v3 통합 응답 스키마.

v2의 중복 필드를 통합하여 하나의 완성형 보고서 구조를 정의한다.
- 밸류에이션심화 + 밸류에이션밴드분석 → 밸류에이션분석
- 매크로환경분석 + 매크로사이클분석 → 매크로및산업분석
- 포지션가이드 + 최종매매전략 → 최종매매전략
"""

from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ── 공통 모델 (v2에서 가져옴) ──

class StrategySignal(BaseModel):
    신호: str
    근거: str
    class Config:
        extra = "allow"

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

class Opinion(BaseModel):
    등급: str
    요약: str
    근거: list[str]

class ScenarioCase(BaseModel):
    목표가: Optional[float] = None
    확률: Optional[float] = Field(None, ge=0, le=100)
    근거: str

class ScenarioAnalysis(BaseModel):
    낙관: ScenarioCase
    기본: ScenarioCase
    비관: ScenarioCase

class InvestmentAlternative(BaseModel):
    유형: str
    종목명: str
    코드: Optional[str] = None
    사유: str

class RiskFactor(BaseModel):
    요인: str
    설명: str

class InvestmentPoint(BaseModel):
    포인트: str
    설명: str


# ── v3 통합 모델 ──

class FinancialHealthAnalysis(BaseModel):
    """1. 재무 건전성 및 리스크 판단."""
    ocf_vs_net_income: Optional[str] = None
    debt_ratio_analysis: Optional[str] = None
    interest_coverage_analysis: Optional[str] = None
    risk_level: Optional[str] = None  # 안전/주의/위험/심각
    summary: Optional[str] = None
    class Config:
        extra = "allow"

class ValuationAnalysis(BaseModel):
    """2. 밸류에이션 분석 (v2 심화 + v3 밴드 통합)."""
    적정가치: Optional[float] = None
    산출방법: Optional[str] = None
    per_band_position: Optional[str] = None
    pbr_band_position: Optional[str] = None
    업종대비: Optional[str] = None
    PEG분석: Optional[str] = None
    밸류에이션판단: Optional[str] = None
    class Config:
        extra = "allow"

class MacroIndustryAnalysis(BaseModel):
    """3. 매크로 및 산업 분석 (v2 매크로환경 + v3 사이클 통합)."""
    시장체제해석: Optional[str] = None
    금리영향: Optional[str] = None
    섹터전망: Optional[str] = None
    매크로리스크: Optional[str] = None
    peak_out_assessment: Optional[str] = None
    industry_cycle_phase: Optional[str] = None
    class Config:
        extra = "allow"

class ManagementTrackRecord(BaseModel):
    """4. 경영진 트랙 레코드 및 자본 배분."""
    ma_track_record: Optional[str] = None
    capital_allocation_grade: Optional[str] = None
    dividend_policy: Optional[str] = None
    governance_assessment: Optional[str] = None
    class Config:
        extra = "allow"

class ValueTrapDeepAnalysis(BaseModel):
    """5. 신저가 함정 vs 안전마진 분석."""
    is_structural_decline: Optional[bool] = None
    decline_type: Optional[str] = None
    evidence: Optional[list[str]] = Field(default_factory=list)
    safety_margin_assessment: Optional[str] = None
    class Config:
        extra = "allow"

class FutureGrowthDrivers(BaseModel):
    """7. 미래성장동력 — catalyst·턴어라운드·산업 순풍 (forward-looking)."""
    catalysts: Optional[list[str]] = Field(default_factory=list)
    turning_points: Optional[list[str]] = Field(default_factory=list)
    industry_tailwinds: Optional[str] = None
    peak_out_signals: Optional[list[str]] = Field(default_factory=list)
    growth_horizon: Optional[str] = None  # 단기/중기/장기
    confidence: Optional[str] = None      # 높음/보통/낮음
    class Config:
        extra = "allow"


class ContrarianView(BaseModel):
    """8. 역발상관점 — 시장 오해·차별화 인사이트·컨센서스 반박."""
    contrarian_thesis: Optional[str] = None
    market_misperception: Optional[str] = None
    edge: Optional[str] = None
    rebut_consensus: Optional[str] = None
    asymmetric_payoff: Optional[str] = None
    class Config:
        extra = "allow"


class TradingStrategy(BaseModel):
    """6. 최종 매매 전략 (v2 포지션가이드 + v3 최종매매전략 통합)."""
    # v2 포지션가이드 필드
    등급팩터: Optional[float] = Field(None, ge=0, le=1)
    추천진입가: Optional[float] = None
    진입가근거: Optional[str] = None
    손절가: Optional[float] = None
    손절근거: Optional[str] = None
    리스크보상비율: Optional[float] = None
    분할매수제안: Optional[str] = None
    recommendation: Optional[str] = None  # ENTER/HOLD/SKIP
    # v3 추가 필드
    적정가치: Optional[float] = None
    적정가치산출: Optional[str] = None
    upside_pct: Optional[float] = None
    downside_pct: Optional[float] = None
    worst_scenario: Optional[str] = None
    action: Optional[str] = None  # 적극매수/분할매수/관망/분할매도/전량매도
    class Config:
        extra = "allow"


# ── v3 전체 스키마 ──

class AdvisoryReportV3Schema(BaseModel):
    """AI 자문 리포트 v3 통합 스키마."""
    schema_version: Literal["v3"] = "v3"

    # 등급/점수
    종목등급: Literal["A", "B+", "B", "C", "D"]
    등급점수: int = Field(ge=0, le=28)
    복합점수: float = Field(ge=0, le=100)
    체제정합성점수: float = Field(ge=0, le=100)

    # 종합 투자 의견
    종합투자의견: Opinion

    # 6대 비판적 분석
    재무건전성분석: Optional[FinancialHealthAnalysis] = None
    밸류에이션분석: Optional[ValuationAnalysis] = None
    매크로및산업분석: Optional[MacroIndustryAnalysis] = None
    경영진트랙레코드: Optional[ManagementTrackRecord] = None
    가치함정분석: Optional[ValueTrapDeepAnalysis] = None
    최종매매전략: Optional[TradingStrategy] = None
    미래성장동력: Optional[FutureGrowthDrivers] = None
    역발상관점: Optional[ContrarianView] = None

    # 전략별 정량 평가
    전략별평가: StrategyEvaluation
    기술적시그널: TechnicalSignal

    # 시나리오/리스크/대안
    시나리오분석: Optional[ScenarioAnalysis] = None
    리스크요인: list[RiskFactor] = Field(default_factory=list)
    투자포인트: list[InvestmentPoint] = Field(default_factory=list)
    관련투자대안: Optional[list[InvestmentAlternative]] = Field(default_factory=list)

    # Value Trap
    Value_Trap_경고: bool = False
    Value_Trap_근거: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"

    @field_validator("등급점수")
    @classmethod
    def validate_grade_score(cls, v: int) -> int:
        if v < 0 or v > 28:
            raise ValueError(f"등급점수 범위 초과: {v}")
        return v

    @field_validator("복합점수", "체제정합성점수")
    @classmethod
    def validate_score_100(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError(f"점수 범위 초과: {v}")
        return v


def validate_v3_report(report_dict: dict) -> tuple[bool, Optional[AdvisoryReportV3Schema], Optional[str]]:
    """v3 리포트 검증."""
    try:
        schema = AdvisoryReportV3Schema.model_validate(report_dict)
        return True, schema, None
    except Exception as e:
        return False, None, str(e)


def extract_v3_fields(report_dict: dict) -> dict:
    """v3 리포트에서 DB 저장용 필드 추출."""
    return {
        "grade": report_dict.get("종목등급"),
        "grade_score": report_dict.get("등급점수"),
        "composite_score": report_dict.get("복합점수"),
        "regime_alignment": report_dict.get("체제정합성점수"),
        "schema_version": "v3",
        "value_trap_warning": report_dict.get("Value_Trap_경고", False),
    }
