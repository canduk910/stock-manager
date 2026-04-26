---
name: asset-dev
description: "TDD 애자일 개발 오케스트레이터. 도메인 전문가 팀이 토론으로 요건을 수립하고, TestEngineer+BackendDev+FrontendDev+QA가 요건 항목별 RED-GREEN-VERIFY 사이클을 반복하여 투자 자동화 시스템을 개발한다. '파이프라인 만들어줘', '시스템 개발', '자동화 구현', '대시보드 만들어줘', 'Telegram 연동', '스케줄러 설정', '기능 추가', '기능 개발' 등 시스템 개발 요청 시 반드시 이 스킬을 사용할 것. 후속 작업: 다시 실행, 재실행, 업데이트, 수정, 보완, 이전 결과 개선, 테스트 추가, 요건 수정 요청 시에도 사용."
---

# TDD 애자일 개발 오케스트레이터

도메인 전문가 팀이 요건을 수립하고, TDD 개발 팀이 요건 항목별로 테스트 선행 → 구현 → 즉시 검증 사이클을 반복하여 투자 자동화 기능을 개발한다.

**실행 모드**: 하이브리드 (Phase 1: 에이전트 팀 → Phase 2: 에이전트 팀 재구성)

## 워크플로우 개요

```
Phase 0: 컨텍스트 확인
Phase 1: 도메인 전문가 팀 → 구조화된 요건서
  ├── macro-sentinel ──┐
  ├── margin-analyst ──┼── 토론 + 합의 → 요건서
  ├── order-advisor  ──┤
  └── value-screener ──┘
       │
Phase 2: TDD 개발 팀 → 요건 항목별 RED-GREEN-VERIFY
  ├── test-engineer  (RED)           ──┐
  ├── backend-dev    (BACKEND GREEN) ──┼── 요건 R_i마다 반복
  ├── frontend-dev   (FRONTEND)      ──┤
  └── qa-inspector   (VERIFY)        ──┘
```

## Phase 0: 컨텍스트 확인

1. `_workspace/dev/` 디렉토리 존재 여부 확인
2. 실행 모드 결정:
   - **미존재** → 초기 실행. Phase 1부터 진행
   - **존재 + 부분 수정 요청** → 기존 요건서 기반으로 해당 요건만 재실행
   - **존재 + 새 입력** → `_workspace/dev/`를 `_workspace/dev_{timestamp}/`로 이동 후 Phase 1

## Phase 1: 도메인 전문가 팀 — 요건 정의

**실행 모드:** 에이전트 팀

### 1-1. 사용자 입력 파싱

사용자 요청에서 추출:
- **개발 대상 모듈**: 포트폴리오 대시보드 / 리밸런싱 / 리스크 모니터링 / 성과 추적 / 투자 일지 / 파이프라인 / 전체
- **범위**: 백엔드만 / 프론트엔드만 / 풀스택
- **우선순위**: 단일 모듈 / 전체 시스템 점진 개발

`_workspace/dev/00_request.json`에 파싱된 요청 저장.

### 1-2. 도메인 전문가 팀 구성

```
TeamCreate(
  team_name: "domain-consultation",
  members: [
    { name: "macro-sentinel", agent_type: "macro-sentinel", model: "opus",
      prompt: "사용자가 '{기능}'을 요청했다. 이 기능의 매크로/체제 관련 요건을 다른 전문가와 토론하여 수립하라. 요건서 형식: [REQ-MACRO-{번호}] 제목 + 설명 + 수용 기준 + 테스트 힌트. _workspace/dev/01_requirements.md에 작성." },
    { name: "margin-analyst", agent_type: "margin-analyst", model: "opus",
      prompt: "사용자가 '{기능}'을 요청했다. 이 기능의 안전마진/등급 관련 요건을 다른 전문가와 토론하여 수립하라." },
    { name: "order-advisor", agent_type: "order-advisor", model: "opus",
      prompt: "사용자가 '{기능}'을 요청했다. 이 기능의 주문/포지션 관련 요건을 다른 전문가와 토론하여 수립하라. 안전 규칙 누락 여부를 반드시 점검." },
    { name: "value-screener", agent_type: "value-screener", model: "opus",
      prompt: "사용자가 '{기능}'을 요청했다. 이 기능의 스크리닝/필터 관련 요건을 다른 전문가와 토론하여 수립하라." }
  ]
)
```

> ValueScreener는 스크리닝과 무관한 기능(예: 투자 일지)이면 생략 가능.

### 1-3. 요건 정의 작업 등록

```
TaskCreate(tasks: [
  { title: "매크로/체제 관련 요건 수립",
    assignee: "macro-sentinel",
    description: "체제 판단, VIX/버핏지수 임계값, 체제별 파라미터 관련 요건 항목 작성" },
  { title: "안전마진/등급 관련 요건 수립",
    assignee: "margin-analyst",
    description: "Graham Number, 7점 등급, 재무건전성 관련 요건 항목 작성" },
  { title: "주문/포지션 관련 요건 수립",
    assignee: "order-advisor",
    description: "포지션 사이징, 손절/익절, 안전 규칙 관련 요건 항목 작성" },
  { title: "스크리닝/필터 관련 요건 수립",
    assignee: "value-screener",
    description: "복합 점수, value trap, 업종 분산 관련 요건 항목 작성" },
  { title: "요건 교차 검토 + 통합",
    description: "각 전문가의 요건을 교차 검토하여 불일치/누락을 해소하고, 최종 요건서를 _workspace/dev/01_requirements.md에 통합",
    depends_on: ["매크로/체제 관련 요건 수립", "안전마진/등급 관련 요건 수립", "주문/포지션 관련 요건 수립", "스크리닝/필터 관련 요건 수립"] }
])
```

### 1-4. 도메인 전문가 토론 규칙

**팀원 간 통신:**
- 각 전문가는 자기 영역 요건을 작성하면서, 다른 영역에 영향을 주는 부분을 SendMessage로 알린다
- 예: MacroSentinel이 "defensive 체제에서 투자 중단" 요건 → OrderAdvisor에게 "포지션 한도 0% 확인 필요" 전달
- 상충 발견 시 직접 토론하여 합의안 도출

**교차 검토 체크리스트:**
- 체제별 파라미터가 모든 전문가 요건에서 일관되는가?
- 등급 기준과 스크리닝 점수 간 정합성이 있는가?
- 안전 규칙(자동 주문 금지, Write-Ahead)이 주문 관련 모든 요건에 포함되었는가?
- 데이터 부족 시 처리(None, 기본값)가 명시되었는가?

### 1-5. 요건서 산출물 형식

```markdown
# 기능 요건서: {기능명}

## 개요
{기능 설명}

## 요건 항목

### [REQ-MACRO-001] {제목}
설명: {무엇을 구현해야 하는지}
수용 기준:
  - {검증 가능한 조건 1 — 구체적 수치}
  - {검증 가능한 조건 2}
테스트 힌트:
  - 입력: {params} → 기대 출력: {result}
도메인 근거: {Graham 원칙/매트릭스 기반}
레이어: unit / integration / api
관련 전문가: MacroSentinel, OrderAdvisor

### [REQ-MARGIN-001] ...
### [REQ-ORDER-001] ...
### [REQ-SCREEN-001] ...

## 비기능 요건
- 예외 계층: ServiceError 하위만 사용
- DB: SQLAlchemy ORM + Alembic
- 프론트: Tailwind CSS v4 + Recharts
```

### 1-6. Phase 1 완료

1. 리더가 모든 전문가 작업 완료 확인 (TaskGet)
2. `_workspace/dev/01_requirements.md` 통합 완성 확인
3. 도메인 전문가 팀 정리 (TeamDelete)
4. 사용자에게 요건서 요약 보고 + 승인 요청

> **사용자 승인 후** Phase 2 진행. 사용자가 요건 수정을 요청하면 Phase 1을 재실행한다.

## Phase 2: TDD 개발 팀 — RED-GREEN-VERIFY 사이클

**실행 모드:** 에이전트 팀 (Phase 1 팀 정리 후 새 팀 구성)

### 2-1. TDD 팀 구성

```
TeamCreate(
  team_name: "tdd-dev",
  members: [
    { name: "test-engineer", agent_type: "test-engineer", model: "opus",
      prompt: "_workspace/dev/01_requirements.md를 읽고, 요건 항목 순서대로 테스트를 선행 작성하라(RED). 각 요건의 수용 기준을 pytest 테스트로 변환. 테스트 작성 후 backend-dev에게 구현 요청. 백엔드 GREEN 후 프론트 빌드 검증." },
    { name: "backend-dev", agent_type: "backend-dev", model: "opus",
      prompt: "_workspace/dev/01_requirements.md를 읽고, test-engineer가 작성한 테스트를 통과하는 백엔드 코드를 구현하라(GREEN). FastAPI+SQLAlchemy 레이어 패턴 준수. GREEN 후 frontend-dev에게 API shape 명세 전달." },
    { name: "frontend-dev", agent_type: "frontend-dev", model: "opus",
      prompt: "_workspace/dev/01_requirements.md를 읽고, backend-dev의 API shape 명세를 받아 프론트엔드를 구현하라. React+Tailwind+Recharts 패턴 준수. 구현 후 npm run build 검증." },
    { name: "qa-inspector", agent_type: "qa-inspector", model: "opus",
      prompt: "test-engineer가 GREEN을 확인할 때마다 경계면 교차 비교 검증을 수행하라(VERIFY). 특히 backend-dev API 응답 shape ↔ frontend-dev fetch/훅 접근 패턴을 교차 비교." }
  ]
)
```

### 2-2. TDD 사이클 작업 등록

요건서의 각 항목 R_i에 대해 4개 작업을 등록한다:

```
요건 R_1에 대해:
  Task: "R_1 테스트 작성 (RED)"
    assignee: test-engineer
    description: "[REQ-XXX-001] {제목}의 수용 기준을 pytest로 작성"

  Task: "R_1 백엔드 구현 (GREEN)"
    assignee: backend-dev
    description: "test-engineer 테스트를 통과하는 백엔드 코드 구현 + API shape 명세 작성"
    depends_on: "R_1 테스트 작성 (RED)"

  Task: "R_1 프론트엔드 구현"
    assignee: frontend-dev
    description: "backend-dev API shape 명세 기반 프론트엔드 구현"
    depends_on: "R_1 백엔드 구현 (GREEN)"

  Task: "R_1 경계면 검증 (VERIFY)"
    assignee: qa-inspector
    description: "백엔드 API shape ↔ 프론트 접근 패턴 교차 비교"
    depends_on: "R_1 프론트엔드 구현"

요건 R_2에 대해:
  (동일 패턴, R_1 VERIFY 완료 후 시작)
  ...
```

> 요건 간 의존성: R_i+1의 RED는 R_i의 VERIFY 완료 후 시작 (순차 보장).
> 단, 독립적인 요건(예: 서로 다른 모듈)은 병렬 진행 가능.
> 백엔드 전용 요건(API만)은 프론트엔드 Task 생략 가능.

### 2-3. RED-GREEN-VERIFY 사이클 상세

```
┌──────────────────────────────────────────────────────┐
│ 요건 R_i                                              │
│                                                        │
│  [RED] test-engineer:                                  │
│    1. 요건 R_i의 수용 기준 → pytest 테스트 작성         │
│    2. → backend-dev: "백엔드 테스트 완료, 구현 요청"     │
│                                                        │
│  [BACKEND GREEN] backend-dev:                          │
│    3. 테스트 파일 Read → 함수 시그니처 파악              │
│    4. 백엔드 코드 구현 (DB → 서비스 → 라우터)            │
│    5. → test-engineer: "백엔드 구현 완료, 테스트 실행"    │
│    6. test-engineer: pytest 실행                        │
│       ├─ FAIL → backend-dev 수정 → 4로 복귀             │
│       └─ PASS → backend-dev가 API shape을 frontend-dev에 전달 │
│                                                        │
│  [FRONTEND] frontend-dev:                              │
│    7. API shape 명세 기반 프론트엔드 구현                │
│    8. → test-engineer: "프론트 구현 완료"                │
│    9. test-engineer: npm run build 검증                 │
│       ├─ FAIL → frontend-dev 수정 → 7로 복귀            │
│       └─ PASS → qa-inspector에게 경계면 검증 요청        │
│                                                        │
│  [VERIFY] qa-inspector:                                │
│   10. API shape ↔ 프론트 접근 패턴 교차 비교             │
│       ├─ 이슈 → backend-dev 또는 frontend-dev 수정       │
│       └─ PASS → R_i 완료, R_i+1 진행                    │
│                                                        │
└──────────────────────────────────────────────────────┘
```

### 2-4. 팀 통신 흐름

```
test-engineer ──[RED 완료]──→ backend-dev
backend-dev   ──[GREEN 완료]──→ test-engineer
test-engineer ──[PASS]──→ (backend-dev가 API shape → frontend-dev)
backend-dev   ──[API SHAPE]──→ frontend-dev
frontend-dev  ──[구현 완료]──→ test-engineer (빌드 검증)
test-engineer ──[전체 PASS]──→ qa-inspector (경계면 검증)
qa-inspector  ──[VERIFY PASS]──→ 리더 (다음 요건 진행)
qa-inspector  ──[이슈 발견]──→ backend-dev / frontend-dev (수정)
```

도메인 전문가 자문이 필요한 경우 (구현 중 불명확):
```
backend-dev ──[자문 요청]──→ 도메인 전문가 (별도 서브 에이전트로 호출)
```

> Phase 2에서 도메인 전문가는 팀원이 아님. 필요 시 리더가 서브 에이전트로 호출하여 답변 전달.

### 2-5. 회귀 방지

각 R_i GREEN 후 **전체 테스트 스위트를 실행**하여 기존 테스트가 깨지지 않았는지 확인:
```bash
pytest tests/ -v  # 전체 회귀 테스트
```

회귀 발견 시:
1. test-engineer가 깨진 테스트 상세를 dev-architect에게 보고
2. dev-architect가 수정 후 전체 재실행
3. 전체 GREEN 확인 후 다음 요건 진행

## Phase 3: 최종 통합 + 보고

### 3-1. 통합 검증

모든 요건 완료 후:
1. `pytest tests/ -v` 전체 테스트 실행
2. `cd frontend && npm run build` 프론트 빌드 검증
3. qa-inspector가 전체 경계면 종합 검증
4. 누락된 라우팅, Header 네비게이션, App.jsx Route 확인

### 3-2. 최종 보고서

```markdown
## TDD 개발 완료 보고

### 요건 이행 현황
| 요건 ID | 제목 | RED | GREEN | VERIFY | 상태 |
|---------|------|-----|-------|--------|------|
| REQ-MACRO-001 | ... | O | O | O | 완료 |
| REQ-MARGIN-001 | ... | O | O | O | 완료 |

### 변경 파일
- 신규: {file_list}
- 수정: {file_list}

### 테스트 결과
- 단위: {n} pass / {m} fail
- 통합: {n} pass / {m} fail
- API: {n} pass / {m} fail
- 전체: {total} pass / {total_fail} fail

### 신규 API 엔드포인트
- GET /api/{module}/... — 설명

### QA 검증 결과
- 경계면 검증: {n}건 PASS / {m}건 수정 완료
- 도메인 로직: 요건서 수용 기준 기반 검증 완료
- 빌드: OK/FAIL
```

### 3-3. 팀 정리
1. tdd-dev 팀 정리 (TeamDelete)
2. `_workspace/dev/` 보존 (사후 검증용)
3. 사용자에게 결과 보고

## 기존 API 재활용 맵

| 기능 | 기존 API | 용도 |
|------|---------|------|
| 잔고/보유종목 | `GET /api/balance` | 포트폴리오 현황 |
| 매수가능금액 | `GET /api/order/buyable` | 리밸런싱 매수 여력 |
| 미체결주문 | `GET /api/order/open` | 중복 주문 방지 |
| 예약주문 | `POST /api/order/reserve` | 리밸런싱 실행 |
| 체결내역 | `GET /api/order/executions` | 성과 추적 |
| 매크로 심리 | `GET /api/macro/sentiment` | 체제 배너 |
| 매크로 지수 | `GET /api/macro/indices` | 벤치마크 |
| 종목 분석 | `GET /api/advisory/{code}/data` | 안전마진/등급 |
| 관심종목 | `GET /api/watchlist` | 모니터링 대상 |

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| Phase 1 전문가 합의 불가 | 리더가 보수적 입장(Graham 원칙) 기반으로 결정, 불일치 사항 요건서에 명시 |
| Phase 2 테스트 반복 실패 (3회 이상) | dev-architect 구현 접근법 재검토 + 요건 수용 기준 재확인 |
| Phase 2 도메인 자문 필요 | 리더가 해당 도메인 전문가를 서브 에이전트로 호출하여 답변 전달 |
| 기존 테스트 회귀 | 다음 요건 진행 중지, 회귀 수정 후 전체 GREEN 확인 후 재개 |
| 프론트 빌드 실패 | 에러 분석 + 수정 후 재빌드 |
| KIS 키 미설정 | 모의 데이터로 테스트, 실제 연동은 키 설정 후 |

## 테스트 시나리오

### 정상 흐름 — 포트폴리오 대시보드
```
사용자: "포트폴리오 대시보드 만들어줘"
→ Phase 1: domain-consultation 팀 구성
  → macro-sentinel: REQ-MACRO-001 "체제 배너 표시" 요건
  → margin-analyst: REQ-MARGIN-001 "종목별 안전마진 등급 뱃지" 요건
  → order-advisor: REQ-ORDER-001 "자산 배분 기준" 요건
  → 교차 검토 + 통합 → 01_requirements.md
→ 사용자 승인
→ Phase 2: tdd-dev 팀 구성
  → R_1(체제 배너): test-engineer RED → dev-architect GREEN → 테스트 PASS → qa-inspector VERIFY
  → R_2(등급 뱃지): test-engineer RED → dev-architect GREEN → 테스트 PASS → qa-inspector VERIFY
  → R_3(자산 배분): ...
→ Phase 3: 전체 테스트 + 빌드 + 종합 보고
```

### 에러 흐름 — 테스트 실패
```
→ Phase 2 R_2:
  → test-engineer: RED 테스트 작성 (Graham Number 계산)
  → dev-architect: GREEN 구현
  → test-engineer: 실행 → 2/5 FAIL (경계값 처리 오류)
  → dev-architect: 수정 + 재실행 요청
  → test-engineer: 재실행 → 5/5 PASS
  → qa-inspector: VERIFY → PASS
  → R_3로 진행
```
