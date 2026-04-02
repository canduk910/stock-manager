---
name: macro-analysis
description: "매크로 환경 분석 스킬. 버핏지수, VIX, 공포탐욕지수, 4대 지수 동향, 투자대가 발언, 시장 뉴스를 수집하여 Graham 관점의 시장 체제(accumulation/selective/cautious/defensive)를 판단한다. 매크로 분석, 시장 환경, 투자 타이밍, 매수 적기 판단 요청 시 사용."
---

# 매크로 환경 분석

시장 전체 밸류에이션과 심리 지표를 수집하여 현재 시장 체제를 Graham 가치투자 관점에서 판단한다.

## API 호출 순서

### 1단계: 심리지표 수집 (핵심)

```bash
curl -s http://localhost:8000/api/macro/sentiment
```

응답에서 추출:
- `vix.value` / `vix.level` — VIX 지수 (< 15 low, 15-25 normal, 25-35 high, > 35 extreme)
- `buffett.ratio` / `buffett.level` — 버핏지수 (< 80% 저평가, 80-100% 적정, 100-130% 고평가, > 130% 상당히 고평가)
- `fear_greed.score` / `fear_greed.label` — 공포탐욕 (0-20 극단적 공포, 20-40 공포, 40-60 중립, 60-80 탐욕, 80-100 극단적 탐욕)

### 2단계: 지수 동향 수집

```bash
curl -s http://localhost:8000/api/macro/indices
```

4대 지수(KOSPI, KOSDAQ, S&P500, NASDAQ) 현재가, 전일대비, 1년 스파크라인.

### 3단계: 투자대가 발언 수집

```bash
curl -s http://localhost:8000/api/macro/investor-quotes
```

버핏, 달리오, 하워드 막스, 켄 피셔, 파브라이, 드러켄밀러의 최근 발언.

### 4단계: 시장 뉴스

```bash
curl -s http://localhost:8000/api/macro/news
```

국내(Google News KR) + 해외(NYT) 뉴스 헤드라인.

## 체제 판단 로직

버핏지수와 공포탐욕을 교차하여 4단계 체제를 결정한다:

| 버핏지수 | 공포탐욕 ≤ 30 | 공포탐욕 30-50 | 공포탐욕 50-70 | 공포탐욕 > 70 |
|---------|-------------|-------------|-------------|-------------|
| < 80% | accumulation | accumulation | selective | selective |
| 80-100% | accumulation | selective | selective | cautious |
| 100-130% | selective | cautious | cautious | defensive |
| > 130% | cautious | defensive | defensive | defensive |

## 체제별 권장 파라미터

| 체제 | 안전마진 기준 | 최대 포지션 비중 | 총 투자한도 |
|------|------------|--------------|-----------|
| accumulation | 20%+ | 5% | 75% |
| selective | 25%+ | 4% | 65% |
| cautious | 30%+ | 3% | 50% |
| defensive | 40%+ | 0% (매수 중단) | 현금 보존 |

## 출력 형식

`_workspace/01_macro_assessment.json`에 저장:

```json
{
  "regime": "accumulation|selective|cautious|defensive",
  "buffett_indicator": {"ratio": 95.2, "level": "fair"},
  "fear_greed": {"score": 25, "label": "공포"},
  "vix": {"value": 28.5, "level": "high"},
  "indices": {
    "kospi": {"price": 2650, "change_pct": -1.2},
    "sp500": {"price": 5200, "change_pct": -0.8}
  },
  "guru_highlights": ["버핏: 현금 비중 확대 중", "달리오: 신흥국 분산 강조"],
  "recommended_margin_threshold": 25,
  "recommended_max_position_pct": 5,
  "recommended_total_invest_pct": 75,
  "analysis_summary": "시장 적정 가치 수준이나 공포 심리 확산 중. 선별적 매수 기회.",
  "timestamp": "2026-04-02T15:30:00+09:00"
}
```

## 주의사항

- 버핏지수의 GDP는 하드코딩($29T)이므로 정확도에 한계가 있다. 방향성 참고용으로만 사용한다.
- VIX가 extreme(> 35)이면 공포탐욕 점수와 무관하게 "공포 국면"으로 해석한다 — Graham의 "남들이 두려워할 때 탐욕스러워라" 원칙.
- 매크로 GPT 결과는 `macro.db`에 일일 캐싱되므로 당일 반복 호출 시 추가 토큰 소모 없다.