---
name: value-screening
description: "Graham 가치투자 기준 멀티팩터 종목 스크리닝. PER/PBR/ROE 필터를 매크로 체제에 따라 동적 조절하여 저평가 후보 종목을 발굴한다. 종목 발굴, 스크리닝, 저평가 종목 찾기, 가치주 탐색 요청 시 사용."
---

# Graham 가치투자 종목 스크리닝

매크로 체제에 연동된 동적 필터로 저평가 종목을 발굴한다.

## 입력

MacroSentinel의 `_workspace/01_macro_assessment.json`에서 체제(regime)와 권장 파라미터를 읽는다.

## 체제별 동적 필터 임계값

| 필터 | accumulation | selective | cautious | defensive |
|------|-------------|-----------|---------|-----------|
| `per_max` | 20 | 15 | 12 | 10 |
| `pbr_max` | 2.0 | 1.5 | 1.2 | 1.0 |
| `roe_min` | 5 | 8 | 10 | 12 |
| `sort_by` | PBR asc | PER asc | ROE desc | ROE desc, PBR asc |
| `top` | 20 | 15 | 10 | 5 |

defensive 체제에서는 스크리닝 자체를 건너뛰고 "현금 보존 권고"를 반환한다.

## API 호출

### 1단계: 스크리너 실행

```bash
curl -s "http://localhost:8000/api/screener/stocks?per_max={per_max}&pbr_max={pbr_max}&roe_min={roe_min}&market={market}&sort_by={sort_by}&top={top}"
```

- `market`: 사용자 지정 없으면 빈 값(전체). KOSPI/KOSDAQ 지정 가능.
- 적자 기업(PER 음수)은 자동 제외됨.

> **KRX 인증 필수**: `KRX_ID`/`KRX_PASSWORD` 환경변수 미설정 시 스크리너 불가. 이 경우 관심종목(watchlist) 기반 분석으로 대체한다.

### 2단계: 관심종목 fallback (스크리너 실패 시)

```bash
curl -s "http://localhost:8000/api/watchlist/dashboard"
```

관심종목 중 PER/PBR/ROE 조건을 클라이언트 사이드에서 필터링한다.

### 3단계: 상위 후보 CAGR 확인 (선택)

상위 5~10종목에 대해 CAGR 성장성을 추가 확인:

```bash
curl -s "http://localhost:8000/api/detail/{code}/report?market={market}"
```

응답의 `summary.rev_cagr`(매출 CAGR)와 `summary.op_cagr`(영업이익 CAGR)가 양수인 종목을 우선한다.

## 후보 랭킹 기준

Graham 복합점수 = PER 역수(정규화) × 0.3 + PBR 역수(정규화) × 0.3 + ROE(정규화) × 0.25 + 배당수익률(정규화) × 0.15

accumulation 체제에서는 PBR 가중치를 높이고(자산가치 중시), cautious 체제에서는 ROE 가중치를 높인다(수익성 중시).

## 출력 형식

`_workspace/02_screened_candidates.json`에 저장:

```json
{
  "regime": "selective",
  "filters_applied": {"per_max": 15, "pbr_max": 1.5, "roe_min": 8, "market": "KOSPI"},
  "universe_size": 2300,
  "passed_filter": 45,
  "candidates": [
    {
      "rank": 1,
      "code": "005930",
      "name": "삼성전자",
      "market": "KR",
      "exchange": "KOSPI",
      "per": 8.5,
      "pbr": 0.9,
      "roe": 12.3,
      "mktcap": 3500000,
      "dividend_yield": 2.5,
      "composite_score": 87.5,
      "rev_cagr": 8.2,
      "preliminary_note": "저PBR + 적정ROE + 배당 지원"
    }
  ],
  "fallback_used": false,
  "timestamp": "2026-04-02T15:35:00+09:00"
}
```

## 주의사항

- pykrx KRX 서버 변경(2026-02-27)으로 yfinance fallback 사용 중. 국내 PER/PBR이 None인 종목이 있을 수 있다.
- 스크리너 결과에 PER/PBR이 None인 종목은 필터링에서 자동 제외된다.
- 해외 종목(US)은 별도 스크리너가 없으므로, 사용자가 관심종목에 등록한 해외주식만 분석 가능하다.