---
name: refactor-audit
description: "코드 구조 감사 + 도메인 인지 리팩토링 오케스트레이터. 코드 비대/중복/레이어 위반/일관성 결여를 감사하고, 도메인 전문가에게 '왜 이렇게 되어있는가'를 확인한 후, 도메인 정합성을 보존하면서 리팩토링을 실행한다. '리팩토링 해줘', '코드 정리', '구조 개선', '중복 제거', '코드 감사', '아키텍처 리뷰' 등의 요청 시 반드시 이 스킬을 사용할 것. 새 기능 개발(→ asset-dev)이나 종목 분석(→ value-invest)과는 구분된다."
---

# 도메인 인지 리팩토링 오케스트레이터

코드 구조를 감사하고, 도메인 전문가의 확인을 거쳐 안전하게 리팩토링을 실행한다.

**실행 모드**: 에이전트 팀 (TeamCreate + SendMessage + TaskCreate)

**핵심 철학**: 중복처럼 보이는 것이 의도적 분리일 수 있다. 구조만 보고 리팩토링하면 투자 로직이 깨진다.

## Phase 1: 준비

### 1-1. 사용자 입력 파싱

사용자 요청에서 다음을 추출한다:
- **리팩토링 범위**: 전체 감사 / 특정 모듈 / 특정 파일
- **리팩토링 유형**: 구조 개선 / 중복 제거 / 성능 최적화 / 일관성 개선
- **제약 조건**: API 계약 변경 가능 여부, 의존성 추가 가능 여부

### 1-2. 워크스페이스 생성

```bash
mkdir -p _workspace/refactor
```

## Phase 2: 팀 구성

```
팀 이름: refactor-team
팀원:
  - refactor-engineer (agent: refactor-engineer.md, model: opus)
  - qa-inspector      (agent: qa-inspector.md, model: opus)
  - macro-sentinel    (agent: macro-sentinel.md, model: opus)
  - margin-analyst    (agent: margin-analyst.md, model: opus)
  - order-advisor     (agent: order-advisor.md, model: opus)
```

```
Task 1: "코드 감사"
  assignee: refactor-engineer
  description: "구조적 문제 식별 + 리팩토링 후보 목록 작성"
  depends_on: 없음

Task 2: "도메인 자문"
  assignee: refactor-engineer
  description: "리팩토링 후보에 대해 도메인 전문가에게 '왜 이렇게 되어있는가' 확인"
  depends_on: Task 1

Task 3: "리팩토링 계획 수립"
  assignee: refactor-engineer
  description: "도메인 자문 결과 반영, 안전한 리팩토링 계획 작성"
  depends_on: Task 2

Task 4: "리팩토링 실행"
  assignee: refactor-engineer
  description: "계획에 따라 점진적 리팩토링 실행"
  depends_on: Task 3

Task 5: "QA 검증"
  assignee: qa-inspector
  description: "리팩토링 후 기능 퇴행 없는지 교차 비교 검증"
  depends_on: Task 4

Task 6: "수정 + 보고"
  assignee: refactor-engineer
  description: "QA 발견 이슈 수정 + 최종 보고"
  depends_on: Task 5
```

## Phase 3: 코드 감사

### 3-1. 정량 감사

```bash
# 1. 파일 크기 분석 (500줄+ 파일 식별)
find . -name "*.py" -path "*/routers/*" -o -name "*.py" -path "*/services/*" -o -name "*.py" -path "*/stock/*" | xargs wc -l | sort -rn | head -20

find frontend/src -name "*.jsx" -o -name "*.js" | xargs wc -l | sort -rn | head -20

# 2. 함수 카운트 (비대 파일의 책임 분석)
grep -c "^def \|^async def " {target_file}
grep -c "^export \|^function \|^const .* = " {target_file}

# 3. 레이어 위반 검출
grep -rn "HTTPException" services/     # 서비스에서 HTTP 예외 직접 raise
grep -rn "from stock\." routers/       # 라우터에서 stock 패키지 직접 import (서비스 우회)
grep -rn "import sqlite" routers/      # 라우터에서 DB 직접 접근
grep -rn "import sqlite" services/     # 서비스에서 DB 직접 접근 (store 우회)

# 4. 중복 패턴 검출
grep -rn "useState.*loading" frontend/src/hooks/     # 동일 fetch 패턴
grep -rn "raise HTTPException" routers/ services/    # 예외 처리 불일치
grep -rn "is_domestic\|_validate_market" services/ stock/ routers/  # 시장 분기 분산
```

### 3-2. 구조 감사

프로젝트 특화 감사 항목:

#### 백엔드

| 감사 항목 | 확인 방법 | 기대 상태 |
|----------|----------|----------|
| 레이어 분리 | routers → services → stock/ 의존 방향 | 역방향 의존 없음 |
| 예외 계층 | 모든 서비스에서 ServiceError만 raise | HTTPException 직접 사용 0건 |
| DB 접근 | stock/*_store.py 통해서만 DB 접근 | 서비스/라우터에서 직접 SQL 0건 |
| 시장 분기 | 시장별(KR/US/FNO) 분기가 일관된 패턴 | 산발적 if-else 최소화 |
| 캐시 전략 | TTL이 명시적이고 이유가 있음 | 하드코딩 상수에 주석 존재 |
| 에러 로깅 | 일관된 로깅 레벨 (error/warning/info) | silent pass 0건 |

#### 프론트엔드

| 감사 항목 | 확인 방법 | 기대 상태 |
|----------|----------|----------|
| API 래퍼 | 모든 fetch가 apiFetch() 경유 | 직접 fetch() 0건 |
| 훅 중복 | 동일 fetch+state 패턴 반복 | 공통 훅으로 추출 가능 |
| 컴포넌트 크기 | 단일 컴포넌트 < 300줄 | 300줄+ 컴포넌트 식별 |
| props 전달 | 3단계+ prop drilling | Context 추출 후보 식별 |
| 쿼리 파라미터 | URL 구성 방식 일관성 | 동일 패턴 사용 |

### 3-3. 감사 결과 저장

`_workspace/refactor/01_audit_report.md`에 저장:

```markdown
# 코드 감사 보고서

## 요약
- 감사 범위: {전체/모듈}
- 감사 일시: {timestamp}

## 발견 사항 (우선순위순)

### [HIGH] {제목} — {파일:라인}
- 문제: {설명}
- 영향: {유지보수성/성능/일관성}
- 도메인 자문 필요: YES/NO
- 리팩토링 제안: {개요}

### [MEDIUM] ...
### [LOW] ...

## 도메인 자문 필요 항목
1. {항목} — {질문할 내용}
```

## Phase 4: 도메인 자문

감사에서 "도메인 자문 필요" 항목에 대해 전문가에게 확인한다.

### 자문 판단 기준

| 변경 유형 | 도메인 자문 | 이유 |
|----------|:---------:|------|
| 함수 이동 (같은 로직, 다른 파일) | 불필요 | 동작 변경 없음 |
| 파일 분할 (같은 로직, 여러 파일) | 불필요 | 동작 변경 없음 |
| 중복 함수 통합 | **필요** | "중복"이 의도적 분리일 수 있음 |
| 조건 분기 통합 (if KR/US) | **필요** | 시장별 미묘한 차이가 있을 수 있음 |
| 상수값 변경 (TTL, 임계값) | **필요** | 도메인 이유가 있을 수 있음 |
| 네이밍 변경 | 불필요 | 동작 변경 없음 (단, API 키명 제외) |
| 에러 처리 통일 | 불필요 | 동작 개선 |
| import 정리 | 불필요 | 동작 변경 없음 |

### 자문 메시지 형식

```
[REFACTOR 자문 요청] {대상 파일/모듈}
현재 구조: {현재 코드 구조 요약 — 함수명, 라인 수, 의존 관계}
개선 제안: {제안하는 변경 — 무엇을 어떻게}
도메인 질문: {이 변경이 투자 로직에 영향을 주는가? 현재 구조에 도메인적 이유가 있는가?}
```

자문 결과를 `_workspace/refactor/02_domain_advice.json`에 저장.

### 자문 결과 분류

| 전문가 답변 | 조치 |
|------------|------|
| "변경 OK — 도메인 이유 없음" | 리팩토링 진행 |
| "주의 — 이런 이유로 현재 구조" | 제약 조건으로 반영하여 계획 수정 |
| "변경 불가 — 필수 도메인 로직" | 해당 항목 리팩토링 제외, 사유 기록 |

## Phase 5: 리팩토링 계획

`_workspace/refactor/03_plan.md`에 작성:

```markdown
# 리팩토링 계획

## 실행 순서 (의존성 순)
1. {항목} — 영향 범위: {파일 목록} — 도메인 자문: {결과 요약}
2. ...

## 실행하지 않는 항목 + 사유
- {항목}: {도메인 전문가 답변 — 변경 불가 사유}

## 위험 관리
- 각 항목별 rollback 방법
- 의존 관계 (항목 A 실패 시 항목 B 영향 여���)
```

## Phase 6: 리팩토링 실행

### 실행 원칙

1. **한 번에 하나**: 항목별 개별 실행 + 확인
2. **빌드 확인**: 각 항목 후 `npm run build` + `python -c "import main"` 실행
3. **API 보존**: 엔드포인트 URL, 응답 shape, 에러 코드 변경 없음 확인
4. **커밋 단위**: 각 리팩토링 항목을 독립 커밋으로 분리 가능하게

### 리팩토링 패턴 (프로젝트 특화)

#### 패턴 A: 비대 서비스 분할

```python
# Before: services/order_service.py (1,338줄, 37함수)
# After:
#   services/order_service.py         — 주문 발주/정정/취소 (공개 인터페이스 유지)
#   services/order_sync_service.py    — 대사/동기화 로직
#   services/order_validation.py      — 검증 유틸리티

# 핵심: 기존 import 경로 유지 — order_service에서 re-export
```

**도메인 자문 필수**: OrderAdvisor에게 "주문→대사→검증 분리가 Write-Ahead 원자성을 깨뜨리지 않는가?"

#### 패턴 B: 프론트 공통 훅 추출

```javascript
// Before: 6개 훅에 동일한 fetch+useState+useEffect 패턴
// After: useAsyncData(fetcher, deps) 공통 훅 + 개별 훅은 래퍼

// hooks/useAsyncData.js (신규)
export function useAsyncData(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // ... 공통 로직
  return { data, loading, error, reload };
}

// hooks/useBalance.js (간소화)
export function useBalance() {
  return useAsyncData(() => fetchBalance(), []);
}
```

**도메인 자문 불필요**: 동작 변경 없음, UI 패턴 통일

#### 패턴 C: API 래퍼 일관성

```javascript
// Before: search.js가 직접 fetch() 사용
// After: apiFetch() 경유로 통일

// 주의: apiFetch의 에러 처리가 search의 "실패 시 빈 배열" 동작과 호환되는지 확인
```

**도메인 자문 불필요**: 에러 처리 통일

#### 패턴 D: 기술지표 순수 함수 분리

```python
# Before: stock/advisory_fetcher.py에 OHLCV fetch + 기술지표 계산 혼합
# After:
#   stock/advisory_fetcher.py  — OHLCV fetch만
#   stock/indicators.py        — 순수 함수 (MACD, RSI, Stochastic, BB, MA)

# 이점: indicators.py는 외부 의존 없이 단위 테스트 가능
```

**도메인 자문 필요**: MarginAnalyst에게 "기술지표 계산이 fetch context에 의존하는 부분이 있는가?"

## Phase 7: QA 검증

리팩토링 완�� 후 QA Inspector에게 검증 요청:

1. **기능 퇴행 없음**: 기존 API 엔드포인트 curl 테스트
2. **프론트 빌드 성공**: `npm run build`
3. **경계면 보존**: 리팩토링으로 API shape/라우팅이 변경되지 않았는지
4. **import 정합성**: 분할된 파일의 import가 정상 해결되는지

QA 발견 이슈 → refactor-engineer가 수정 → 재검증 루프.

## Phase 8: 최종 보고

```markdown
# 리팩토링 완료 보고

## 요약
- 리팩토링 항목: {n}건 실행 / {m}건 보류
- 변경 파일: {count}개
- 코드 증감: +{added}줄 / -{removed}줄 (순 {delta}줄)

## 실행된 리팩토링
| 항목 | 변경 파일 | 효과 | 도메인 자문 |
|------|----------|------|-----------|

## 보류된 항목 + 사유
| 항목 | 사유 (도메인 전문가 답변) |

## QA 검증 결과
- 기능 퇴행: 없음/있음 (수정 완료)
- 빌드: PASS
- API 호환성: PASS

## 도메인 전문가 자문 요약
- MacroSentinel: {요약}
- OrderAdvisor: {요약}
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| 도메인 전문가가 전체 변경 불가 판정 | 감사 보고서만 제출, 리팩토링 실행 안 함 |
| 리팩토링 후 빌드 실패 | 즉시 revert, 더 작은 단위로 재시도 |
| import 순환 의존 발생 | 분할 전략 재고, 인터페이스 계층 추가 |
| QA에서 기능 퇴행 발견 | 해당 항목 revert, 다른 접근법으로 재시도 |
| 기존 코드에 테스트 부재 | curl 기반 블랙박스 테스트로 대체 |

## 테스트 시나리오

### 정상 흐름 — 전체 감사
```
사용자: "코드 구조 감사하고 리팩토링 해줘"
→ refactor-engineer: 정량+구조 감사 → 15건 발견
→ refactor-engineer: OrderAdvisor에게 "주문 서비스 분할 가능한가?" 자문
→ OrderAdvisor: "분할 OK, 단 Write-Ahead 패턴은 order_service에 유지 필수"
→ refactor-engineer: MarginAnalyst에게 "기술지표 함수 분리 가능한가?" 자문
→ MarginAnalyst: "OK — 순수 계산 함수는 fetch와 무관"
→ refactor-engineer: 10건 실행, 5건 보류 (도메인 사유)
→ qa-inspector: 교차 비교 검증 → 1건 경계면 이슈 발견
→ refactor-engineer: 수정 → 재검증 통과
→ 최종 보고: "10건 리팩토링, -320줄, 빌드 PASS"
```

### 특정 모듈 리팩토링
```
사용자: "프론트엔드 훅 중복 좀 정리해줘"
→ refactor-engineer: 훅 감사 → 6개 동일 패턴 발견
→ 도메인 자문 불필요 (UI 패턴 변경)
→ refactor-engineer: useAsyncData 공통 훅 추출 + 6개 훅 간소화
→ qa-inspector: 빌드 + API 호출 패턴 검증
→ 최종 보고
```

### 변경 불가 판정
```
사용자: "KR/US 주문 로직이 비슷한데 합쳐줘"
→ refactor-engineer: OrderAdvisor에게 자문
→ OrderAdvisor: "변경 불가 — KR은 TTTC0802U, US는 JTTT1002U. 파라미터 규격이 다름"
→ refactor-engineer: 보류 처리, 사유 기록
→ 보고: "도메인 이유로 현행 유지 — TR_ID + 파라미터 규격 차이"
```
