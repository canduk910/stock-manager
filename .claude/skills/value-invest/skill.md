---
name: value-invest
description: "Graham 안전마진 가치투자 오케스트레이터. 매크로 환경 판단 → 종목 스크리닝 → 심층 분석 → 주문 추천의 전체 파이프라인을 조율한다. '종목 발굴해줘', '매수할 종목 찾아줘', '저평가 종목', '안전마진 분석', '투자 분석', '가치투자' 등의 요청 시 반드시 이 스킬을 사용할 것. 단순 잔고 조회나 주문 발송과는 구분된다."
---

# Graham 안전마진 가치투자 오케스트레이터

매크로 환경 판단 → 종목 스크리닝 → 심층 분석 → 주문 추천의 전체 파이프라인을 조율한다.

**실행 모드**: 에이전트 팀 (TeamCreate + SendMessage + TaskCreate)

## Phase 1: 준비

### 1-1. 사용자 입력 파싱

사용자 요청에서 다음을 추출한다:
- **시장**: KR(KOSPI/KOSDAQ) / US / 지정 없으면 KR 전체
- **안전마진 기준**: 사용자 지정 또는 매크로 체제 자동 연동
- **분석 대상**: 전체 스크리닝 / 특정 종목 리스트 / 관심종목
- **주문까지 진행 여부**: 분석만 / 주문 추천까지

### 1-2. 워크스페이스 생성

```bash
mkdir -p _workspace/03_analyses
```

`_workspace/00_input.json`에 파싱된 사용자 요청 저장:

```json
{
  "market": "KR",
  "user_margin_threshold": null,
  "target_stocks": null,
  "include_order_recommendation": true,
  "timestamp": "2026-04-02T15:30:00+09:00"
}
```

## Phase 2: 팀 구성

TeamCreate로 4명의 에이전트 팀을 구성한다:

```
팀 이름: value-invest-team
팀원:
  - macro-sentinel (agent: macro-sentinel.md, model: opus)
  - value-screener (agent: value-screener.md, model: opus)
  - margin-analyst (agent: margin-analyst.md, model: opus)
  - order-advisor  (agent: order-advisor.md, model: opus)
```

TaskCreate로 파이프라인 작업을 등록한다:

```
Task 1: "매크로 환경 분석"
  assignee: macro-sentinel
  description: "매크로 데이터 수집 + 시장 체제 판단 → _workspace/01_macro_assessment.json 저장"
  depends_on: 없음

Task 2: "가치투자 종목 스크리닝"
  assignee: value-screener
  description: "매크로 체제 연동 필터로 후보 종목 발굴 → _workspace/02_screened_candidates.json 저장"
  depends_on: Task 1

Task 3: "안전마진 심층 분석"
  assignee: margin-analyst
  description: "후보 종목별 Graham Number + 재무 건전성 + 기술적 타이밍 분석 → _workspace/03_analyses/ 저장"
  depends_on: Task 2

Task 4: "주문 추천 생성"
  assignee: order-advisor
  description: "포트폴리오 확인 + 포지션 사이징 + 매수 추천서 생성 → _workspace/05_recommendations.json 저장"
  depends_on: Task 3
```

## Phase 3: 파이프라인 실행

### 3-1. MacroSentinel 실행

SendMessage로 macro-sentinel에게 분석 시작 지시. 완료 후 `_workspace/01_macro_assessment.json`을 확인한다.

**게이트 1**: regime === "defensive"이면 Task 2~4를 건너뛰고 Phase 4로 직행.
```
→ "현재 시장은 방어적 체제입니다. 버핏지수 {ratio}%(상당히 고평가),
   탐욕 지수 {score}. 신규 매수를 자제하고 현금 보존을 권고합니다."
```

### 3-2. ValueScreener 실행

SendMessage로 value-screener에게 체제 + 필터 파라미터 전달. 완료 후 `_workspace/02_screened_candidates.json`을 확인한다.

**게이트 2**: candidates 배열이 비어있으면 Task 3~4를 건너뛰고 Phase 4로 직행.
```
→ "현재 Graham 기준(PER<{per_max}, PBR<{pbr_max}, ROE>{roe_min})을
   충족하는 종목이 없습니다. 필터 완화 또는 시장 조정을 기다리세요."
```

**특정 종목 분석 모드**: 사용자가 특정 종목을 지정한 경우 스크리닝을 건너뛰고, 해당 종목을 직접 `02_screened_candidates.json`에 넣어 Task 3으로 진행.

### 3-3. MarginAnalyst 실행

SendMessage로 margin-analyst에게 후보 리스트 전달. 종목별 순차 분석 (API 호출 부하 관리). 완료 후 `_workspace/03_analyses/` 파일들을 확인한다.

**게이트 3**: 안전마진 기준(recommended_margin_threshold) 충족 종목이 0개이면 Task 4를 건너뛰고 Phase 4로 직행.
```
→ "분석 완료: {n}종목 중 안전마진 {threshold}% 이상 충족 종목이 없습니다.
   가장 근접한 종목: {name} (할인율 {rate}%)"
```

### 3-4. OrderAdvisor 실행

SendMessage로 order-advisor에게 분석 완료 통보. 포트폴리오 확인 후 주문 추천서 생성. 완료 후 `_workspace/05_recommendations.json`을 확인한다.

**KIS 키 미설정 시**: 포지션 사이징/수량 계산 없이 등급+추천가만 보고.

## Phase 4: 결과 종합 + 투자 보고서

`_workspace/` 산출물을 종합하여 사용자에게 보고한다:

### 보고서 구조

```markdown
## 📊 Graham 안전마진 투자 분석 보고서

### 시장 환경
- 체제: {regime} | 버핏지수: {ratio}% | 공포탐욕: {score} ({label})
- 권장 안전마진: {threshold}%+ | 포지션 한도: {max_pct}%

### 스크리닝 결과
- 분석 대상: {universe_size}종목 → 필터 통과: {passed}종목 → 최종 분석: {analyzed}종목

### 매수 추천 (안전마진 순)
| 순위 | 종목 | 등급 | Graham 할인율 | PER | PBR | 추천가 | 수량 | 금액 |
|------|------|------|-------------|-----|-----|--------|------|------|
| 1 | 삼성전자 | A | 30.9% | 8.5 | 0.9 | 54,000 | 37주 | 199만 |

### 상세 분석 (종목별)
- 삼성전자(005930): Graham Number 72,000원. 부채비율 35%, FCF 3년 양수...

### 주의사항
- 모든 추천은 참고용이며 최종 투자 판단은 사용자의 책임입니다.
- 예약주문 등록을 원하시면 종목명을 말씀해 주세요.
```

## Phase 5: 정리

1. SendMessage로 모든 팀원에게 종료 요청
2. `_workspace/` 폴더는 보존 (감사 추적 + 향후 참조)
3. 사용자에게 결과 요약 제시

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| MacroSentinel 실패 | selective 체제 기본값으로 진행 |
| ValueScreener 실패 (KRX 불가) | 관심종목 기반 분석으로 대체 |
| 특정 종목 분석 실패 | 해당 종목 스킵, 나머지 계속 |
| OrderAdvisor 실패 (KIS 불가) | 분석까지만 보고, 주문 추천 생략 |
| 전체 파이프라인 실패 | 실패 원인 명시 + 수동 분석 가이드 제공 |

## 테스트 시나리오

### 정상 흐름
```
사용자: "KOSPI에서 안전마진 30% 이상 저평가 종목 찾아줘"
→ MacroSentinel: selective 체제 판단
→ ValueScreener: PER<15, PBR<1.5, ROE>8% 필터 → 8종목 선정
→ MarginAnalyst: 8종목 분석 → 3종목 할인율 30%+ 통과
→ OrderAdvisor: 3종목 매수 추천서 (지정가, 수량, 손절/익절)
→ 보고서 제시 → 사용자 "삼성전자 예약주문 해줘" → 예약주문 등록
```

### 에러 흐름
```
사용자: "저평가 종목 분석해줘"
→ MacroSentinel: defensive 체제 (버핏지수 135%)
→ 게이트 1 차단: "현금 보존 권고" 직접 반환
→ 보고서: "현재 시장 과열 상태. 신규 매수 자제, 현금 비중 확대 권고"
```

### 특정 종목 분석
```
사용자: "삼성전자 안전마진 분석해줘"
→ MacroSentinel: selective 체제
→ ValueScreener 건너뜀 (특정 종목 지정)
→ MarginAnalyst: 삼성전자 단일 종목 심층 분석
→ OrderAdvisor: 매수 추천 또는 "안전마진 부족" 보고
```
