---
name: graham-analysis
description: "개별 종목 Graham 안전마진 심층 분석. Graham Number(내재가치) 산출, 재무 건전성(부채비율/유동비율/FCF) 점검, PER/PBR 히스토리 대비 현재 위치, 기술적 매수 타이밍(RSI/MACD/MA/BB) 판단을 수행한다. 종목 분석, 내재가치, 안전마진 계산, 재무 건전성, 기술적 분석 요청 시 사용."
---

# Graham 안전마진 심층 분석

개별 종목의 내재가치를 산출하고, 재무 건전성을 점검하며, 기술적 매수 타이밍을 판단한다.

## 입력

`_workspace/02_screened_candidates.json`의 후보 종목 리스트와 `_workspace/01_macro_assessment.json`의 안전마진 기준(recommended_margin_threshold).

## API 호출 순서 (종목당)

### 1단계: 기본적+기술적 데이터 수집

```bash
curl -s -X POST "http://localhost:8000/api/advisory/{code}/refresh?market={market}&name={name}"
```

이 호출이 수집하는 데이터:
- DART 재무 3종(IS/BS/CF) 5년치 — EPS, 부채비율, 유동비율, FCF
- pykrx/yfinance 계량지표 — PER, PBR, ROE, PSR, 시가총액
- 15분봉 기술지표 — MACD, RSI, Stochastic, MA, BB, ATR
- 사업 개요 — 키워드, 사업설명, 매출비중

### 2단계: 캐시된 분석 데이터 조회

```bash
curl -s "http://localhost:8000/api/advisory/{code}/data?market={market}"
```

응답 구조:
- `fundamental.income_stmt` — 연도별 매출/영업이익/순이익/EPS
- `fundamental.balance_sheet` — 자산/부채/자본/유동자산/유동부채
- `fundamental.cashflow` — 영업CF/투자CF/FCF
- `fundamental.metrics` — PER/PBR/ROE/PSR/EV_EBITDA/부채비율/유동비율
- `technical.current_signals` — 현재 MACD/RSI/Stochastic/MA정배열/BB위치
- `technical.graham_number` — Graham Number + 할인율 (있을 경우)

### 3단계: 10년 재무 + CAGR

```bash
curl -s "http://localhost:8000/api/detail/{code}/report?market={market}"
```

- `summary.rev_cagr` / `summary.op_cagr` / `summary.net_cagr` — 매출/영업이익/순이익 CAGR
- `summary.per_vs_avg` / `summary.pbr_vs_avg` — 현재 PER/PBR vs 기간 평균 괴리율

### 4단계: PER/PBR 히스토리 차트

```bash
curl -s "http://localhost:8000/api/detail/{code}/valuation?market={market}"
```

5년 월별 PER/PBR 추이. 현재가 역사적으로 어느 분위수에 있는지 판단.

### 5단계: 일봉 기술 차트 (선택)

```bash
curl -s "http://localhost:8000/api/advisory/{code}/ohlcv?market={market}&interval=1d&period=1y"
```

1년 일봉 + MA5/20/60 + BB + MACD + RSI. 지지/저항선 파악용.

### 6단계: GPT 3전략 리포트 (선택, OpenAI 키 필요)

```bash
curl -s -X POST "http://localhost:8000/api/advisory/{code}/analyze?market={market}&name={name}"
```

변동성 돌파 + 안전마진 + 추세추종 통합 AI 리포트.

## 안전마진 평가 프레임워크

### Graham Number 계산

```
Graham Number = √(22.5 × EPS × BPS)
할인율 = (Graham Number - 현재가) / 현재가 × 100
```

- EPS: 최근 연도 기본주당이익 (income_stmt[-1].eps)
- BPS: price / PBR 역산 (직접 BPS 데이터 없는 경우)

### 종합 등급 산정

| 지표 | 강력매수(4점) | 매수(3점) | 중립(2점) | 회피(1점) |
|------|-------------|---------|---------|---------|
| Graham 할인율 | > 40% | 20-40% | 0-20% | < 0% |
| PER vs 5년 평균 | < -30% | -30~-10% | -10~+10% | > +10% |
| PBR 절대값 | < 0.7 | 0.7-1.0 | 1.0-1.5 | > 1.5 |
| 부채비율 | < 50% | 50-100% | 100-200% | > 200% |
| 유동비율 | > 2.0 | 1.5-2.0 | 1.0-1.5 | < 1.0 |
| FCF 추세 | 3년 양수 | 2년 양수 | 1년 양수 | 음수 |
| 매출 CAGR | > 10% | 5-10% | 0-5% | 음수 |

**종합 점수** = 7개 지표 합산 (최대 28점)
- 24-28: A (강력매수)
- 20-23: B+ (매수)
- 16-19: B (조건부 매수)
- 12-15: C (중립)
- < 12: D (회피)

### 기술적 진입 판단

| 시그널 | 의미 | 행동 |
|--------|------|------|
| MA 역배열 + RSI < 30 | 항복 국면 | 분할 매수 1차 진입 |
| MACD 골든크로스 + RSI 30-50 | 반등 초기 | 2차 추가 매수 |
| BB 하단 이탈 | 단기 과매도 | 단기 반등 매수 |
| MA 정배열 + RSI 50-70 | 상승 추세 | 풀 포지션 |
| RSI > 70 | 과매수 | 매수 보류 |

## 출력 형식

종목별 `_workspace/03_analyses/{code}_analysis.json`에 저장:

```json
{
  "code": "005930",
  "name": "삼성전자",
  "market": "KR",
  "graham_number": 72000,
  "current_price": 55000,
  "discount_rate": 30.9,
  "safety_margin_grade": "A",
  "fundamental_score": 24,
  "financial_health": {
    "debt_ratio": 35.2,
    "current_ratio": 2.1,
    "fcf_trend": "positive_3y",
    "revenue_cagr_5y": 8.5,
    "op_margin_latest": 15.2,
    "roe": 12.3
  },
  "valuation_position": {
    "current_per": 8.5,
    "avg_per_5y": 12.3,
    "per_vs_avg": -30.9,
    "current_pbr": 0.9,
    "avg_pbr_5y": 1.4,
    "pbr_vs_avg": -35.7,
    "per_percentile": 15,
    "pbr_percentile": 10
  },
  "technical_entry": {
    "signal": "favorable",
    "ma_alignment": "혼합",
    "rsi": 35.2,
    "macd_cross": "golden_cross_recent",
    "bb_position": "near_lower",
    "suggested_entry": "분할 매수 1차 진입"
  },
  "recommendation": "STRONG_BUY",
  "target_entry_price": 54000,
  "stop_loss_price": 48000,
  "reasoning": [
    "Graham Number 72,000원 대비 30.9% 할인",
    "부채비율 35% — 재무 우량",
    "PER 8.5 (5년 평균 12.3 대비 -31%)",
    "매출 CAGR 5년 8.5% 안정 성장"
  ],
  "ai_report_available": true,
  "timestamp": "2026-04-02T15:40:00+09:00"
}
```

## 주의사항

- Graham Number BPS는 `price / PBR` 역산이므로 PBR이 None이면 계산 불가. 해당 종목은 Graham 할인율 = null로 표기하고 나머지 지표로만 평가한다.
- 국내 PER/PBR이 yfinance에서 None인 경우가 많다(KRX 서버 변경 이후). 이 경우 히스토리 비교도 불가하므로 절대값 기준으로만 판단한다.
- `POST /api/advisory/{code}/refresh`는 외부 API(DART, KIS, yfinance)를 호출하므로 종목당 5-10초 소요. 10종목 분석 시 50-100초 예상.
- OpenAI 키 미설정 시 6단계(GPT 리포트) 생략. 정량 분석만으로도 투자 판단 가능.