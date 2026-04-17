# Stock-Manager AI 자문 시스템 심층 분석

**분석 일시**: 2026-04-17
**대상 모듈**: advisory_service.py, portfolio_advisor_service.py, advisory_fetcher.py, macro_regime.py, safety_grade.py, pipeline_service.py

---

## 1. 전체 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI 라우터 진입점                        │
│   routers/advisory.py → routers/portfolio_advisor.py            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼──────────────┐    ┌────────▼─────────────┐
│ advisory_service.py  │    │portfolio_advisor_    │
│ (개별 종목 분석)      │    │service.py (포트폴리오)│
└───────┬──────────────┘    └────────┬─────────────┘
        │                             │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   데이터 수집 & OpenAI 호출  │
        │  advisory_fetcher.py        │
        │  macro_service.py           │
        │  + macro_regime.py (체제)    │
        │  + safety_grade.py (등급)    │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    외부 데이터 소스           │
        │  • stock/dart_fin.py        │
        │  • stock/yf_client.py       │
        │  • stock/market.py          │
        │  • stock/indicators.py      │
        │  • stock/symbol_map.py      │
        └─────────────────────────────┘
```

---

## 2. 데이터 수집 흐름 (GPT 호출 전 단계)

### 2.1 개별 종목 분석 (`advisory_service.refresh_stock_data()`)

#### 국내 (KR)
```python
# 7개 독립 소스 병렬 수집 (ThreadPoolExecutor, max_workers=7)

1. dart_fin.fetch_income_detail_annual(code, 5)
   → 손익계산서: [{year, revenue, operating_income, net_income, oi_margin, net_margin, eps}, ...]

2. dart_fin.fetch_bs_cf_annual(code, 5)
   → 대차대조표: [{year, total_assets, total_equity, debt_ratio, current_ratio}, ...]
   → 현금흐름: [{year, operating_cf, free_cf}, ...]

3. stock/market.fetch_market_metrics(code)
   → {market_type, mktcap, per, pbr, roe, dividend_yield}
   → 6시간 캐시

4. advisory_fetcher.fetch_segments_kr(code, name)
   → OpenAI GPT: 사업부문 매출비중 추론
   → {segments: [{segment, revenue_pct, note}], description, keywords}

5. stock/yf_client.fetch_forward_estimates_yf(code, True)
   → yfinance forward estimates (국내는 대부분 N/A)

6. advisory_fetcher.fetch_valuation_stats(code, "KR")
   → PER/PBR 5년 평균/최대/최소/현재/편차%
   → yfinance 월봉 히스토리 기반

7. dart_fin.fetch_quarterly_financials(code, 4)
   → 최근 4분기 분기별 실적: [{year, quarter, revenue, oi_margin, net_margin}, ...]
```

#### 해외 (US)
```python
# 8개 독립 소스 병렬 수집 (ThreadPoolExecutor, max_workers=8)

1-2. yf_client: fetch_income_detail_yf, fetch_balance_sheet_yf, fetch_cashflow_yf (각 5년)
3. fetch_metrics_yf(code)
4. fetch_segments_yf(code) → GPT 불필요, yfinance 내장 sector/industry
5. fetch_forward_estimates_yf(code, False)
6. advisory_fetcher.fetch_valuation_stats(code, "US")
7. yf_client.fetch_quarterly_financials_yf(code, 4)
```

### 2.2 기술적 분석 데이터 수집

```python
# advisory_service._collect_technical(code, market)

KR: advisory_fetcher.fetch_15min_ohlcv_kr(code)
    ① KIS REST API FHKST03010200 (1분봉, 4시간 병렬)
    ② 30봉 미만 시 yfinance fallback

US: advisory_fetcher.fetch_15min_ohlcv_us(code)
    → yfinance 15분봉 (최대 60일)

결과: [{time, open, high, low, close, volume}, ...] 최근 300봉

↓

indicators.calc_technical_indicators(ohlcv)
→ {
    "current_signals": {
        "macd_cross": "golden|dead|none",
        "macd_value": float,
        "rsi_value": float,
        "rsi_signal": "overbought|neutral|oversold",
        "stoch_k": float,
        "stoch_signal": "overbought|neutral|oversold",
        "above_ma20": bool,
        "ma5": float, "ma20": float, "ma60": float,
        "ma_alignment": "정배열|역배열|혼합",
        "atr": float,
        "current_price": float,
        "volatility_target_k03": float,  # K=0.3
        "volatility_target_k05": float,  # K=0.5
        "volatility_target_k07": float,  # K=0.7
        "volume_signal": float,  # 최신/5일평균 비율
        "volume_5d_avg": float,
        "volume_20d_avg": float,
        "bb_position": float,  # 0(하단)~100(상단)
        ...
    },
    "volatility_target_k03": ...,  # 중복 (신호용)
    ...
}
```

### 2.3 Graham Number 계산

```python
# advisory_service._calc_graham_number(fundamental, market)

Graham Number = sqrt(22.5 × EPS × BPS)

입력:
- EPS: 손익계산서 최신 연도에서 추출
- BPS:
  ① 재무제표 직접 제공 시 사용
  ② 없으면 PER/PBR 역산: BPS = (EPS × PER) / PBR

할인율 = (Graham Number - 현재가) / 현재가 × 100
  ① 양수: 저평가
  ② 음수: 고평가
```

### 2.4 매크로 컨텍스트 수집

```python
# advisory_service._get_macro_context()

macro_service.get_sentiment()
→ {
    "vix": {"value": float},
    "fear_greed": {"score|value": float},  # 0~100
    "buffett": {"ratio": float},  # 0.0 ~ 3.0+
    ... (뉴스, 투자자 코멘트 등)
}

↓

macro_regime.determine_regime(sentiment)
→ {
    "regime": "accumulation|selective|cautious|defensive",
    "regime_desc": "축적 (탐욕 매수)|선별 (중립 적극)|...",
    "params": {
        "margin": int (% 요구 안전마진),
        "stock_max": int (% 총 주식 한도),
        "cash_min": int (% 현금 최소 비중),
        "single_cap": int (% 종목당 한도),
        "per_max": float,
        "pbr_max": float,
        "roe_min": float,
    },
    "vix": float | None,
    "buffett_ratio": float | None,
    "fear_greed_score": float | None,
    "buffett_level": "low|normal|high|extreme",
    "fg_level": "extreme_fear|fear|neutral|greed|extreme_greed",
}
```

---

## 3. System Prompt 구조 (Phase 1 기본 + Phase 2 확장)

### 3.1 기본 영역 (advisory_service._build_system_prompt)

```
┌─────────────────────────────────────────────────────┐
│  당신은 전문 주식 애널리스트입니다.                   │
│  다음 세 가지 전략 프레임워크를 평가하세요.           │
└─────────────────────────────────────────────────────┘

【전략 1】 변동성 돌파 전략 (Larry Williams)
- 당일 시가 + (전일 고저 범위 × K값) 돌파 시 매수
- K=0.3/0.5/0.7 기준값
- ATR 기반 변동성 수준 판단

【전략 2】 안전마진 전략 (Benjamin Graham)
- Graham Number = sqrt(22.5 × EPS × BPS)
- 할인율 >30%: 강한 매수
- 할인율 10-30%: 매수
- 할인율 0-10%: 중립
- 할인율 <0%: 고평가
- 적자 기업 처리 규칙

【전략 3】 추세추종 전략
- MA5 > MA20 > MA60 정배열 (골든크로스)
- MACD 방향 확인
- RSI 모멘텀 (50↑ = 상승 모멘텀)

【7점 등급 체계】 (28점 만점)

| # | 지표        | 4점      | 3점        | 2점        | 1점    |
| 1 | Graham할인율 | >40%    | 20-40%    | 0-20%      | <0%    |
| 2 | PER vs 5yr  | <-30%   | -30~-10%  | -10~+10%   | >+10%  |
| 3 | PBR절대값    | <0.7    | 0.7-1.0   | 1.0-1.5    | >1.5   |
| 4 | 부채비율     | <50%    | 50-100%   | 100-200%   | >200%  |
| 5 | 유동비율     | >2.0    | 1.5-2.0   | 1.0-1.5    | <1.0   |
| 6 | FCF양수연수  | 3년     | 2년       | 1년        | 0년    |
| 7 | 매출CAGR    | >10%    | 5-10%     | 0-5%       | <0%    |

등급 컷오프:
- A: 24-28점 (강력매수)
- B+: 20-23점 (매수)
- B: 16-19점 (조건부)
- C: 12-15점 (비추천)
- D: <12점 (부적격)

【MacroSentinel 매트릭스】 (20셀)
버핏지수(low/normal/high/extreme) × 공포탐욕(fear/neutral/greed)
→ regime: accumulation|selective|cautious|defensive
→ VIX >35: extreme_fear 강제 오버라이드

【OrderAdvisor 손절/포지션】
- A등급: -8% 손절, 1.0 팩터
- B+등급: -10% 손절, 0.75 팩터
- B등급: -12% 손절, 0.5 팩터
- C/D등급: 진입 금지

【재무 건전성 체크리스트】
- 부채비율 >200% → 위험
- 유동비율 <100% → 위험
- FCF 3년 연속 음수 → 위험
→ 2개 이상 위험 시 매수 판정 금지 + Value Trap 경고

【ValueScreener Value Trap 5규칙】
1. 매출 CAGR < 0% ∧ PER < 5
2. 영업이익률 3년 연속 하락
3. FCF 3년 연속 음수
4. 부채비율 전년 대비 ≥30%p 급증
5. 배당 중단 (과거 지급 후 현재 중단)
→ 2개 이상 = Value Trap 경고

【매크로 환경】
체제별 투자 원칙:
- accumulation: 안전마진 20% 이상 적극 매수, 현금 25% 유지
- selective: 안전마진 30% 이상, 현금 35% 유지
- cautious: 안전마진 40% 이상, 현금 50% 유지
- defensive: 【중요】 매수 등급 부여 금지! 최대 '관망'만 허용, 현금 75% 유지

【종합 지침】
- 매크로 체제가 defensive: 어떤 경우에도 '매수' 등급 금지
- 7점 등급 C/D: 매수 추천 금지 (최대 '관망')
```

### 3.2 User Prompt 구조 (기본적 분석 섹션)

```
다음은 {name}({code}, {market}) 종목의 분석 데이터입니다.

## 손익계산서 (최근 3년)
{연도별 매출, 영업이익, 순이익, 마진율}

## 대차대조표 (최근 3년)
{자산, 자본, 부채비율, 유동비율}

## 현금흐름표 (최근 3년)
{영업CF, FCF}

## 계량지표
PER, PBR, ROE, PSR, EV/EBITDA

## 기술적 시그널 (15분봉)
- MACD: 상태 + 해석
- RSI: 값 + 신호
- 스토캐스틱: K값 + 신호
- MA20 상회: bool

## 변동성 돌파 전략 데이터
- 현재가
- ATR(14)
- K=0.3/0.5/0.7 목표가 (실현 여부)

## 안전마진 분석 (Graham Number)
- GN 값
- EPS, BPS (구성 방식)
- 현재가 대비 할인율 (양수=저평가)

## 추세추종 전략 데이터
- MA 정렬 상태 (MA5, MA20, MA60)
- MACD 크로스
- RSI

## Forward Estimates (국내는 대부분 N/A)
- Forward PE
- Forward EPS
- 애널리스트 목표가 + 점수 + 수

## 【Phase 2-2】 PER/PBR 5년 히스토리
- PER: 현재 / 5년 평균 / 범위 / 편차%
- PBR: 현재 / 5년 평균 / 범위 / 편차%
- 편차 <-20%: 저평가 / >+20%: 고평가

## 【Phase 2-3】 분기 실적 (최근 4분기)
{분기별 매출, 영업이익, 순이익, 마진}

## 거래량·변동성 신호
- 거래량 신호 (최신/5일평균 비율)
- 볼린저밴드 위치 (0=하단~100=상단)

## 7점 등급 사전 계산값
{각 지표별 점수, 합계, 등급}
복합 점수: {ValueScreener 공식}
체제 정합성: {regime별 정렬}
※ 참고용이며 GPT는 독립적 판단 수행. 불일치 시 근거 명시
```

---

## 4. Response JSON Schema (v2)

### 4.1 Pydantic v2 정의 (schemas/advisory_report_v2.py)

```python
# 최상위 구조
{
    "schema_version": "v2",  # 버전 관리용

    # 【등급 & 점수】
    "종목등급": "A|B+|B|C|D",  # MarginAnalyst 7점 등급
    "등급점수": 0-28,         # 7개 지표 합산 정수
    "복합점수": 0-100,        # ValueScreener 공식 실수
    "체제정합성점수": 0-100,  # 현재 매크로 체제 대비 정렬도

    # 【종합 의견】
    "종합투자의견": {
        "등급": "매수|중립|매도",
        "요약": "2-3문장 요약",
        "근거": ["근거1", "근거2", "근거3"]
    },

    # 【전략별 평가 (3전략)】
    "전략별평가": {
        "변동성돌파": {
            "신호": "매수|관망",
            "목표가": K=0.5 목표가 | null,
            "근거": "돌파 여부 + ATR 변동성"
        },
        "안전마진": {
            "신호": "매수|중립|매도",
            "graham_number": GN 값 | null,
            "할인율": 할인율(%) | null,
            "근거": "GN 해석 + 안전마진"
        },
        "추세추종": {
            "신호": "매수|관망|매도",
            "추세강도": "강|중|약",
            "근거": "MA/MACD/RSI 조합"
        }
    },

    # 【기술적 시그널】
    "기술적시그널": {
        "신호": "매수|관망|매도",
        "해석": "2-3문장 기술적 분석",
        "지표별": {
            "macd": "해석",
            "rsi": "해석",
            "stoch": "해석",
            "volume": "거래량 급증/정상/감소",
            "bb": "BB 하단 지지/중간/상단 저항"
        }
    },

    # 【포지션 가이드】
    "포지션가이드": {
        "등급팩터": 1.0|0.75|0.5|0,
        "추천진입가": 정수,
        "진입가근거": "최근가|기술적 지지선 등",
        "손절가": 정수,
        "손절근거": "등급별 기준 또는 기술적 저항",
        "1차익절가": 정수,
        "익절근거": "GN 또는 목표가",
        "리스크보상비율": (익절-진입)/(진입-손절),
        "분할매수제안": "1차 50%(진입) - 2차 30%(...) - 3차 20%(...)",
        "recommendation": "ENTER|HOLD|SKIP"
    },

    # 【리스크 & 투자포인트】
    "리스크요인": [
        {"요인": "리스크명", "설명": "설명"},
        ...
    ],
    "투자포인트": [
        {"포인트": "포인트명", "설명": "설명"},
        ...
    ],

    # 【Value Trap 경고】 (Phase 2-4)
    "Value_Trap_경고": true|false,
    "Value_Trap_근거": ["규칙번호+근거", ...] or []
}
```

### 4.2 검증 로직 (validate_v2_report, extract_v2_fields)

```python
# validate_v2_report(report: dict) → (bool, dict, str)

검증 항목:
✓ schema_version 필수 (v2 확인)
✓ 종목등급 ∈ {A, B+, B, C, D}
✓ 등급점수 ∈ [0, 28]
✓ 복합점수 ∈ [0, 100]
✓ 체제정합성점수 ∈ [0, 100]
✓ 종합투자의견 필수
  - 등급 ∈ {매수, 중립, 매도}
  - 요약 길이 > 0
  - 근거 배열 길이 ≥ 1
✓ 전략별평가, 기술적시그널 필수
✓ 포지션가이드 권장
  - recommendation ∈ {ENTER, HOLD, SKIP}
  - 리스크보상비율 < 2.0 시 SKIP
✓ Value_Trap_경고 boolean

→ (success, valid_dict, error_message)

# extract_v2_fields(report: dict) → dict

추출 항목:
- grade: 종목등급 (A/B+/B/C/D)
- grade_score: 등급점수 (0-28)
- composite_score: 복합점수 (0-100)
- regime_alignment: 체제정합성점수 (0-100)
- schema_version: "v2" | "v1"
- value_trap_warning: true|false (경고 발동 여부)
```

### 4.3 DB 저장 흐름

```python
# advisory_service.generate_ai_report()

1. OpenAI 호출 (최대 10000 토큰)
2. JSON 파싱 (_parse_report)
3. Pydantic v2 검증 (validate_v2_report)
   ├─ 실패 시: 1회 재시도 (12000 토큰)
   └─ 성공 시: 계속
4. 정량 필드 추출 (extract_v2_fields)
5. DB 저장 (advisory_store.save_report):
   - report_id
   - code, market, model
   - report (전체 JSON)
   - grade: Literal["A", "B+", "B", "C", "D"] | None
   - grade_score: int 0-28 | None
   - composite_score: float 0-100 | None
   - regime_alignment: float 0-100 | None
   - schema_version: "v2" | "v1"
   - value_trap_warning: bool | None
   - created_at: timestamp
```

---

## 5. 포트폴리오 자문 시스템 (portfolio_advisor_service.py)

### 5.1 컨텍스트 구성 (잔고 데이터 → 프롬프트)

```python
# _build_context(balance_data: dict)

1. 평가금액 분석
   - total_evaluation_krw
   - domestic/overseas 비중(%)
   - stock/cash 비중(%)

2. 보유 종목 상세 (국내 + 해외)
   {
       "name", "code", "market", "exchange",
       "quantity", "avg_price", "current_price",
       "profit_rate", "eval_amount", "weight_pct(%)",

       "per", "pbr", "roe", "dividend_yield",
       "high_52", "drop_from_high(%)",

       # 【개별 AI 리포트 연계】
       "latest_report_grade": "A|B+|B|C|D",
       "latest_report_summary": "요약 180자",
       "latest_report_discount_rate": 할인율,
       "latest_report_risks": ["위험1", "위험2"]
   }

3. 포트폴리오 지표
   - num_holdings
   - top3_concentration_pct
   - hhi (허쉬만 지수)
   - portfolio_grade_weighted_avg (가중평균 등급)
   - grade_distribution (A/B+/B/C/D 개수)
   - regime_alignment_score (체제 정합성)
```

### 5.2 포트폴리오 전용 System Prompt

```
당신은 한국 주식시장 전문 포트폴리오 투자자문 AI입니다.

JSON 응답 형식:
{
  "diagnosis": {
    "summary": "진단 요약 (2~3문장)",
    "risk_level": "high|medium|low",
    "total_score": 0~100,
    "concentration_risk": "평가",
    "sector_analysis": [
      {"sector": "섹터명", "weight_pct": %, "assessment": "편중/적정/부족"}
    ],
    "currency_exposure": "평가"
  },
  "rebalancing": [
    {
      "stock_name": "종목명", "stock_code": "코드",
      "action": "increase|reduce|hold|exit",
      "current_weight": %, "suggested_weight": %,
      "priority": 1~5,
      "reason": "근거"
    }
  ],
  "trades": [
    {
      "stock_name": "종목명", "stock_code": "코드", "market": "KR|US",
      "action": "buy|sell",
      "qty": 수량, "target_price": 목표가, "stop_loss": 손절가,
      "position_pct": 예상 비중, "urgency": "immediate|this_week|this_month",
      "urgency_reason": "근거",
      "reason": "매매 근거"
    }
  ],
  "market_context": "시장 상황 코멘트",
  "disclaimer": "AI 생성 참고용"
}

【분석 원칙】
1. 단일 섹터 >40% → 경고 필수
2. 손실 중인 종목 → 손절/물타기/홀딩 명확히
3. 상위 3종목 ≥60% → 집중도 위험
4. PER/PBR/ROE/배당수익률 활용
5. 국내/해외 통화 분산도 평가
6. 리밸런싱/매매는 종목명+코드 필수

【개별 AI 리포트 연계】
A. latest_report_summary + latest_report_risks 우선 참고
B. latest_report_discount_rate < 0 → reduce|exit 우선
C. latest_report_discount_rate > 30 → increase 후보
D. latest_report_risks ≥2개 → priority=1 재검토

【역발상 매수 (Contrarian Buy)】
(cautious/selective 체제만 허용)
- 조건: -30%↓ + PBR<1.0 + 부채<100% + 영업이익 흑자 + FCF양수
- 제외: 분기 적자 전환 / 부채 30%p 급증 / 구조적 쇠퇴 / 2년 연속 적자
- 손절: -20% (일반보다 넓음)
- 포지션: selective=3%, cautious=1.5%
- 분할: 1차 30% → 2차 30%(-10%) → 3차 40%(-20%)

【포지션 사이징】
- 단일 종목: 포트폴리오의 5% 초과 금지
- 1회 주문: 예수금의 30% 초과 금지
- 주식 비중: 체제별 max 준수 (accumulation=75%, selective=65%, cautious=50%, defensive=25%)
- 현금: 체제별 min 준수
```

### 5.3 캐싱 & 저장

```python
# 캐시 (cache.db, 30분 TTL)
cache_key = f"advisor:portfolio:{SHA256(종목구성)}"
→ {"data": analysis_dict, "analyzed_at": timestamp, "report_id": id}

# 영구 저장 (advisory.db)
portfolio_reports 테이블:
  - report_id, model, report (JSON)
  - weighted_grade_avg (v2 신규)
  - regime (v2 신규)
  - schema_version ("v2" | "v1")
  - created_at
```

---

## 6. 공용 모듈 (체제 판단 & 등급 계산)

### 6.1 macro_regime.py (3개 서비스 공유)

```python
# determine_regime(sentiment: dict, previous_regime: str | None) → dict

입력:
  sentiment = macro_service.get_sentiment()
  → {
    "vix": {"value": float} | float,
    "fear_greed": {"score|value": float},
    "buffett": {"ratio": float},
    ...
  }

처리:
  1. VIX > 35 → extreme_fear 강제 오버라이드
  2. 버핏지수 분류: _classify_buffett(ratio)
     - <0.8: low
     - 0.8-1.2: normal
     - 1.2-1.6: high
     - ≥1.6: extreme
  3. 공포탐욕 분류: _classify_fear_greed(score, vix)
     - <20: extreme_fear
     - 20-40: fear
     - 40-60: neutral
     - 60-80: greed
     - ≥80: extreme_greed
  4. 하이스테리시스 ±5점(공포탐욕) / ±0.05(버핏) 적용
  5. REGIME_MATRIX[버핏레벨][공포탐욕레벨] → regime

REGIME_MATRIX (20셀):
  low + fear → accumulation
  low + greed → cautious
  normal + fear → selective
  normal + extreme_greed → defensive
  high + greed → defensive
  extreme + * → cautious|defensive
  ... (20개 조합)

반환:
  {
    "regime": "accumulation|selective|cautious|defensive",
    "regime_desc": "축적|선별|신중|방어",
    "params": {
      "margin": 20|30|40|999 (요구 안전마진%),
      "stock_max": 75|65|50|25 (최대 주식비중%),
      "cash_min": 25|35|50|75 (최소 현금비중%),
      "single_cap": 5|4|3|0 (종목당 한도%),
      "per_max": 20|15|12|0,
      "pbr_max": 2.0|1.5|1.2|0,
      "roe_min": 5|8|10|0,
    },
    "vix": float,
    "buffett_ratio": float,
    "fear_greed_score": float,
    "buffett_level": "low|normal|high|extreme",
    "fg_level": "extreme_fear|fear|neutral|greed|extreme_greed",
  }
```

### 6.2 safety_grade.py (등급 & 점수 계산)

```python
# compute_grade_7point(
#   metrics, balance_sheet, cashflow, income_stmt,
#   valuation_stats=None, graham_number=None, current_price=None
# ) → dict

7개 지표별 점수 (각 4점 만점):

1. _score_discount(discount: float)
   - >40%: 4점
   - 20-40%: 3점
   - 0-20%: 2점
   - ≤0%: 1점

2. _score_per_vs_avg(per, per_avg)
   - <-30%: 4점
   - -30%-10%: 3점
   - -10%-+10%: 2점
   - >+10%: 1점

3. _score_pbr(pbr)
   - <0.7: 4점
   - 0.7-1.0: 3점
   - 1.0-1.5: 2점
   - >1.5: 1점

4. _score_debt_ratio(ratio)
   - <50: 4점
   - 50-100: 3점
   - 100-200: 2점
   - >200: 1점

5. _score_current_ratio(ratio)
   - >2.0: 4점
   - 1.5-2.0: 3점
   - 1.0-1.5: 2점
   - <1.0: 1점

6. _score_fcf_trend(years_positive)
   - ≥3년: 4점
   - 2년: 3점
   - 1년: 2점
   - 0년: 1점

7. _score_revenue_cagr(cagr)
   - >10%: 4점
   - 5-10%: 3점
   - 0-5%: 2점
   - <0%: 1점

합산 (0-28점) → 등급:
- ≥24: A
- 20-23: B+
- 16-19: B
- 12-15: C
- <12: D

팩터:
- A: 1.0
- B+: 0.75
- B: 0.5
- C: 0.0
- D: 0.0

반환:
  {
    "score": 0-28,
    "grade": "A|B+|B|C|D",
    "grade_factor": 1.0|0.75|0.5|0,
    "valid_entry": True|False,
    "details": {
      "discount": {"value": float, "points": 1-4},
      "per_vs_avg": {"value": float, "avg": float, "points": 1-4},
      ...
    }
  }
```

```python
# compute_composite_score(metrics: dict) → float 0-100

공식: (1/PER × 0.3 + 1/PBR × 0.3 + ROE/100 × 0.25 + 배당수익률/100 × 0.15) × 100

배당수익률 정규화:
- >1 이면 % 형태 (3.5) → /100
- ≤1 이면 소수점 (0.035) → 그대로

```

```python
# compute_regime_alignment(
#   regime, grade_score, fcf_years_positive, stock_pct=None
# ) → float 0-100

체제별 기대 등급:
- accumulation: 20점 (B+ 기대)
- selective: 20점
- cautious: 24점 (A 기대)
- defensive: 28점 (A만)

가중치:
- 등급 정합 (40%): 기대와 비교
- FCF 정합 (30%): 3년 양수=100, 2년=75, 1년=50, 0년=25
- 주식비중 정합 (30%): ±5%p=100, ±20%p=0 (선택)

→ 정합성_점수 = 0~100
```

---

## 7. 투자 파이프라인 (pipeline_service.py)

### 7.1 실행 흐름

```
Step 1: 매크로 체제 판단
└─ macro_service.get_sentiment() → macro_regime.determine_regime()

Step 2: 종목 스크리닝 (defensive 체제 제외)
└─ 체제별 PER/PBR/ROE 필터 → 상위 20개

Step 3: 심층 분석 (상위 10개)
└─ 병렬 분석 (ThreadPoolExecutor, max_workers=3)
   - refresh_stock_data() 호출
   - _calc_graham_number() 계산
   - _extract_financial_metrics() 추출
   - _calc_safety_grade() 등급 계산

Step 4: 추천 생성
└─ 등급 B+ 이상 + 할인율 ≥ regime.margin 필터
└─ R:R ≥ 2.0 검증

Step 5: DB 저장 & 보고서 생성
└─ 추천 이력 (recommendations 테이블)
└─ 체제 이력 (macro_regime_history 테이블)
└─ 일일 보고서 (daily_reports 테이블)
```

### 7.2 추천 생성 로직 (주요 필터)

```python
def _generate_recommendations(analyses, regime_data):

    조건 1: 등급 B+ 이상만
    if grade not in ("A", "B+"):
        continue

    조건 2: 할인율이 체제 임계값 이상
    if discount < margin_threshold:
        continue

    조건 3: 손절/익절 설정
    - A등급: -8% 손절
    - B+등급: -10% 손절
    - 익절가: Graham Number

    조건 4: Risk/Reward ≥ 2.0
    if (take_profit - entry) / (entry - stop_loss) < 2.0:
        continue

    → 최대 5종목 반환
```

---

## 8. 현재 구현의 한계점 & 개선 기회

### 8.1 데이터 수집 측면

| 한계점 | 원인 | 영향 | 개선 방안 |
|--------|------|------|----------|
| yfinance 15분 지연 | yfinance 제약 | 국내 개장일 분석 부정확 | KIS WS 강화 (현재 4시간 병렬로 제한적) |
| 해외 재무 4년 한계 | yfinance 제약 | 장기 추세 분석 부족 | SEC EDGAR 직접 파싱 (현재 10-K/10-Q만) |
| Forward 추정치 대부분 N/A | yfinance 한계 | 미래 성장성 판단 부족 | Seeking Alpha / FactSet 연동 고려 |
| DART 계정명 편차 | 공시 표준 미준수 | 일부 종목 재무 데이터 누락 | OCR 기반 계정 매핑 강화 필요 |
| Segment 정보 GPT 추론 | DART에 segment 미분류 | 사업 다각화 분석 추정치 의존 | 공시 본문 텍스트 분석 고려 |

### 8.2 GPT 프롬프트 & 스키마 측면

| 한계점 | 원인 | 영향 | 개선 방안 |
|--------|------|------|----------|
| v1 리포트 등급 미정의 | 기존 레거시 | 포트폴리오 가중 등급 계산 불가 | 일괄 v2 강제 변환 (1주일 소요) |
| 적자 기업 Value Trap 판별 약함 | System Prompt 간단함 | 구조적 부실 기업도 B 등급 가능 | 산업 수명주기 + 경영 신용도 추가 |
| Order Advisor 손절폭 고정 | -8%/-10%/-12% | 변동성 높은 종목 손절 너무 빨리 | ATR 기반 동적 손절폭 계산 추가 |
| Value Trap 경고 5규칙만 | 정량 규칙 중심 | 정성적 위험 (경영진 변동, 분식) 미포착 | CEO 스캔들 / 감사의견 정보 API 연동 |
| 배당수익률 fallback 3단계 | dividendYield 미신뢰 | 일부 종목 배당 과대 평가 | 배당금 지급 공시 직접 확인 로직 |

### 8.3 포트폴리오 자문 측면

| 한계점 | 원인 | 영향 | 개선 방안 |
|--------|------|------|----------|
| 역발상 매수 손절 -20% | 고정 규칙 | 급락장에서 손절 재진입 불가 | 트레일링 손절 또는 시간 기반 재평가 |
| 분할 매수 수학적 근거 없음 | 직관적 규칙 | 최적 배분인지 검증 불가 | Kelly Criterion 또는 Markowitz 최적화 |
| 섹터 집중도 경고만 함 | 경고 레벨만 | 구체적 리밸런싱 제안 부족 | 섹터별 상관관계 분석 추가 |
| 통화 헤지 미제공 | 구현 부재 | 원달러 변동성 미반영 | 환율 통계 + 수익률 조정 제안 추가 |

### 8.4 시스템 운영 측면

| 한계점 | 원인 | 영향 | 개선 방안 |
|--------|------|------|----------|
| OpenAI 토큰 비용 증가 | max_completion_tokens=12000 | 월 비용 급증 가능 | 프롬프트 압축 또는 Claude 3.5 Sonnet 전환 |
| 7개 병렬 데이터 수집 (KR) | ThreadPoolExecutor 제약 | 종목당 30-40초 소요 | 캐시 효율 향상 + 개별 API 호출 최소화 |
| FNO 심화 시세 yfinance 폴링 | WS 미지원 | 2초 지연 누적 | KIS WS FNO 채널 확대 |
| 매크로 뉴스 RSS 제약 | feedparser + GPT 번역 | 속보성 떨어짐 | Bloomberg / Refinitiv API 고려 |

### 8.5 개선 우선순위

**긴급 (1주)**
1. v1 → v2 전환 완료 (기존 리포트 등급 마이그레이션)
2. 적자 기업 Value Trap 규칙 강화

**높음 (2주)**
3. DART 계정명 매핑 정확도 향상
4. 배당 공시 직접 확인 로직 추가
5. 역발상 매수 손절폭 동적화

**중간 (1개월)**
6. 포트폴리오 분할 매수 최적화 (Kelly Criterion)
7. CEO 스캔들 / 감사의견 API 연동
8. Forward 추정치 대체 데이터 소스 (Seeking Alpha)

**낮음 (2개월+)**
9. Claude 3.5 Sonnet 전환 + 프롬프트 압축
10. 통화 헤지 제안 기능
11. 섹터 상관관계 분석 추가
12. 매크로 뉴스 API 고도화

---

## 9. KIS API 활용 현황

### 9.1 현재 사용 중인 TR_ID

**시세 & 기술지표 수집**
- `FHKST03010200`: 국내 1분봉 (advisory_fetcher.py)
- 실시간: KIS WS (quote_kis.py)

**주문 관련** (order_service.py)
- `TTTC0802U`/`TTTC0801U`: 국내 매수/매도
- `TTTC0803U`: 정정/취소
- 미체결/체결: `TTTC8036R`/`TTTC8001R`

### 9.2 미사용 TR_ID (개선 기회)

| TR_ID | 용도 | 사용처 | 활용 가능성 |
|-------|------|--------|-----------|
| `TTTC8908R` | 국내 매수가능금액 | 포지션 사이징 | 높음 (현재 order_service만 사용) |
| `FHKST01010100` | 국내 현재가 (REST) | quote_kis.py fallback | 이미 사용 |
| `JTTS0202R` | 해외 현재가 | quote_overseas.py | 현재 yfinance/Finnhub만 |
| `TTTO5201R` | 선물옵션 체결 조회 | order_fno.py | 이미 사용 |
| `FHMIF10000000` | 선물옵션 현재가 | order_service.get_fno_price | 이미 사용 |

### 9.3 KIS API 제약사항

```python
# 국내 1분봉 수집
- 제약: 호출당 30봉만 반환 → 4시간대 병렬 호출 (153000, 143000, 133000, 123000)
- 토큰: 분당 1회 발급 제한 (캐싱으로 해결)
- 시간: 15분 리샘플 → 기술지표 계산용
- 폴백: 30봉 미만 시 yfinance 재조회

# 해외주식 현재가
- KIS JTTS0202R: 미지원 또는 지연 심각
- 대체: yfinance fast_info (30초 폴링) + Finnhub WS (30 심볼)

# 선물옵션
- KIS_ACNT_PRDT_CD_FNO 미설정 시 기능 자동 비활성화 (503)
- WS: 야간 세션 TR_ID 별도 (`STTN1101U`)
```

---

## 10. 전체 데이터 흐름 (요약 다이어그램)

```
사용자 요청
    │
    ├─ /api/advisory/{code}/refresh
    │   └─ advisory_fetcher + 기술지표
    │       └─ advisory_store (캐시)
    │
    ├─ /api/advisory/{code}/analyze
    │   └─ 캐시 읽기
    │   └─ _get_macro_context() → macro_regime.determine_regime()
    │   └─ _calc_graham_number()
    │   └─ _build_system_prompt(regime)
    │   └─ _build_prompt(regime, 재무, 기술)
    │   └─ OpenAI GPT-4o
    │   └─ Pydantic v2 검증 (extract_v2_fields)
    │   └─ advisory_store.save_report()
    │
    ├─ /api/portfolio-advisor/analyze
    │   └─ /api/balance (KIS 잔고)
    │   └─ _build_context() (52주 고가 캐시)
    │   └─ _fetch_latest_report_summary() (개별 AI 연계)
    │   └─ _get_macro_context() → regime
    │   └─ _build_system_prompt(regime, cash_pct)
    │   └─ OpenAI GPT-4o
    │   └─ cache.db 30분 TTL (+ advisory.db 영구)
    │
    └─ /api/pipeline/run
        └─ macro_service.get_sentiment()
        └─ macro_regime.determine_regime()
        └─ _screen_stocks() (체제별 필터)
        └─ _analyze_candidates() (병렬)
        └─ safety_grade.compute_grade_7point()
        └─ _generate_recommendations()
        └─ report_service.save_daily_report()

외부 데이터 소스:
    KIS OpenAPI (1분봉, 잔고, 주문)
    ├─ wrapper.py (REST)
    └─ services/quote_kis.py (WebSocket)

    DART API (손익, 대차, 현금흐름, 분기)
    └─ stock/dart_fin.py

    yfinance (해외 시세, 재무, 지표)
    └─ stock/yf_client.py

    OpenAI API (GPT-4o)
    └─ advisory_service.py + portfolio_advisor_service.py

    매크로 데이터 (VIX, 버핏, RSS 뉴스)
    └─ stock/macro_fetcher.py + macro_service.py
```

---

## 11. 추천 검토 사항

### 11.1 코드 레벨
- ✅ 데이터 수집 7-8 병렬: ThreadPoolExecutor 효율적
- ✅ GPT 재시도: 토큰 잘림 + Pydantic 검증 실패 대응
- ✅ 캐싱 전략: TTL별 3계층 (cache.db 6h ~ macro.db 1일)
- ⚠️ 적자 기업 Value Trap: System Prompt 규칙만으로 부족
- ⚠️ 포트폴리오 역발상: 손절폭 고정 → ATR 동적화 고려

### 11.2 아키텍처 레벨
- ✅ 체제 판단 중앙화 (macro_regime.py)
- ✅ 등급 계산 중앙화 (safety_grade.py)
- ✅ 개별 AI 리포트 포트폴리오 연계
- ⚠️ Forward 추정치 대체 데이터 필요
- ⚠️ 통화 헤지 제안 기능 부재

### 11.3 운영 레벨
- ✅ 10000→12000 토큰 재시도로 응답 완성도 높음
- ⚠️ OpenAI 비용: 월별 추적 필요
- ⚠️ v1 리포트 마이그레이션: 대량 이력 처리 필요
- ⚠️ KIS API 처리량: 30초+ 종목당 지연 누적

---

**분석 완료**
이 문서는 AI 자문 시스템의 전체 구조를 종합적으로 정리하였습니다.
특히 GPT 호출 이전의 데이터 흐름과 System/User Prompt 구조, v2 스키마 검증 로직을 상세히 기록했으므로 향후 개선 시 참고 자료로 활용하시기 바랍니다.
