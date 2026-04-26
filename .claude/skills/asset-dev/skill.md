---
name: asset-dev
description: "부서장 오케스트레이터. 모든 개발·리팩토링·QA 요청의 단일 진입점. 사용자 요청을 분석하여 도메인팀장(domain-lead)과 개발팀장(dev-lead)에게 업무를 지시하고 결과를 취합한다. 코드 변경이 수반되는 모든 요청 시 반드시 이 스킬을 사용할 것. '만들어줘', '개발', '구현', '추가', '리팩토링', '코드 정리', 'QA', '검증', '테스트', '파이프라인', '대시보드', '연동', '기능 개발', '구조 개선', '중복 제거', '코드 감사', '수정', '보완', '업데이트' 등 모든 개발 요청 시 사용."
---

# 부서장 오케스트레이터

모든 개발 요청의 단일 진입점. 사용자 요청을 분석하여 도메인팀장과 개발팀장에게 업무를 배분하고, 결과를 취합하여 보고한다.

## 조직 구조

```
부서장 (이 스킬 = 당신)
├── 도메인팀장 (domain-lead)
│   ├── MacroSentinel — 매크로/체제
│   ├── MarginAnalyst — 안전마진/등급
│   ├── OrderAdvisor — 주문/포지션
│   └── ValueScreener — 스크리닝/필터
└── 개발팀장 (dev-lead)
    ├── TestEngineer — TDD 테스트
    ├── BackendDev — FastAPI 백엔드
    ├── FrontendDev — React 프론트
    ├── QA Inspector — 경계면 검증
    └── RefactorEngineer — 리팩토링
```

## Phase 0: 요청 분석 + 라우팅

사용자 요청을 분석하여 작업 유형을 결정한다:

| 유형 | 트리거 키워드 | 라우팅 |
|------|-------------|--------|
| **A: 기능 개발** | "만들어줘", "추가", "개발", "구현", "파이프라인", "대시보드", "연동", "기능" | 도메인팀장 → 개발팀장 (순차) |
| **B: 리팩토링** | "리팩토링", "코드 정리", "구조 개선", "중복 제거", "코드 감사" | 개발팀장 (도메인 자문 필요 시 도메인팀장) |
| **C: QA/검증** | "QA", "검증", "테스트", "정합성 검사" | 개발팀장 (도메인 검증 시 도메인팀장) |
| **D: 소규모 수정** | 단일 파일 수정, 간단한 버그 수정 | 직접 처리 (팀 구성 불필요) |

### 규모 판단 기준

- 변경 예상 파일 ≤ 3개, 새 엔드포인트/페이지 없음 → **유형 D** (직접 처리)
- 새 API 엔드포인트 또는 새 페이지 필요 → **유형 A**
- 기존 코드 구조 변경 → **유형 B**
- 기존 코드 정합성 확인 → **유형 C**

### 컨텍스트 확인

1. `_workspace/dev/` 디렉토리 존재 여부 확인
2. **미존재** → 초기 실행
3. **존재 + 부분 수정 요청** → 기존 요건서 기반 해당 요건만 재실행
4. **존재 + 새 입력** → `_workspace/dev/`를 `_workspace/dev_{timestamp}/`로 이동

---

## 유형 A: 기능 개발 (도메인팀장 → 개발팀장)

### Phase 1: 도메인팀장에게 요건 정의 지시

도메인팀장(domain-lead) 에이전트를 호출한다:

```
Agent(
  subagent_type: "domain-lead",
  name: "domain-lead",
  prompt: """
  [부서장 → 도메인팀장] 요건 정의 지시

  사용자 요청: {사용자 원문}
  개발 대상: {모듈명}
  범위: {백엔드/프론트/풀스택}

  도메인 전문가 팀(MacroSentinel, MarginAnalyst, OrderAdvisor, ValueScreener)을 구성하여
  기능 요건을 정의하라. 전문가 간 교차 토론을 통해 정합성을 확보하고,
  _workspace/dev/01_requirements.md에 통합 요건서를 산출하라.

  프로젝트 참조:
  - CLAUDE.md (프로젝트 구조, 레이어, 예외 계층)
  - .claude/skills/asset-dev/references/feature-specs.md (기존 모듈 상세 스펙)

  요건서 형식: [REQ-{영역}-{번호}] 제목 + 설명 + 수용 기준(구체적 수치) + 테스트 힌트 + 레이어
  요건서 산출 후 팀을 정리하고, 요건 요약을 보고하라.
  """
)
```

**사용자 승인**: 요건서 요약을 사용자에게 보여주고 승인을 받는다. 수정 요청 시 도메인팀장을 재호출한다.

### Phase 2: 개발팀장에게 TDD 개발 지시

개발팀장(dev-lead) 에이전트를 호출한다:

```
Agent(
  subagent_type: "dev-lead",
  name: "dev-lead",
  prompt: """
  [부서장 → 개발팀장] TDD 개발 지시

  요건서: _workspace/dev/01_requirements.md
  작업 유형: TDD 개발

  개발 팀(TestEngineer, BackendDev, FrontendDev, QA Inspector)을 구성하여
  요건 항목별로 RED→GREEN→VERIFY TDD 사이클을 실행하라.

  TDD 사이클:
    R_i마다: test-engineer RED → backend-dev GREEN → frontend-dev 구현 → qa-inspector VERIFY
  회귀 방지: 각 R_i 후 pytest tests/ -v 전체 실행
  도메인 자문 필요 시: 해당 도메인 전문가를 Agent로 개별 호출하여 확인

  프로젝트 참조:
  - CLAUDE.md (레이어 구성, 예외 계층, DB 시스템)
  - 기존 서비스 재사용: services/ 내 기존 함수 직접 호출

  완료 후 팀을 정리하고, 결과를 보고하라.
  """
)
```

### Phase 3: 결과 취합 + 보고

양 팀장의 결과를 통합하여 사용자에게 보고:

```markdown
## 작업 완료 보고

### 요청
{사용자 원문 요약}

### 도메인 요건 (도메인팀장)
- 요건 {n}개 수립
- 주요 내용: {핵심 요건 목록}

### 개발 결과 (개발팀장)
| 요건 ID | 제목 | RED | GREEN | VERIFY | 상태 |
|---------|------|-----|-------|--------|------|

### 테스트 결과
- 전체: {total} pass / {fail} fail

### 신규 API 엔드포인트
- {목록}

### 변경 파일
- 신규: {file_list}
- 수정: {file_list}

### QA 검증
- 경계면: PASS/FAIL
- 빌드: OK/FAIL
```

---

## 유형 B: 리팩토링 (개발팀장, 도메인 자문 시 도메인팀장)

### Phase 1: 개발팀장에게 리팩토링 지시

```
Agent(
  subagent_type: "dev-lead",
  name: "dev-lead",
  prompt: """
  [부서장 → 개발팀장] 리팩토링 지시

  사용자 요청: {사용자 원문}
  작업 유형: 리팩토링

  RefactorEngineer + QA Inspector를 구성하여:
  1. 코드 감사 → 리팩토링 후보 목록
  2. 도메인 자문 필요 시 해당 전문가를 Agent로 호출하여 확인
  3. 자문 결과 반영 → 계획 수립 → 점진적 실행
  4. QA Inspector가 기능 퇴행 검증

  참조: .claude/skills/refactor-audit/references/project-hotspots.md (기존 핫스팟 목록)
  
  완료 후 결과를 보고하라.
  """
)
```

### Phase 2: 결과 취합 + 보고

리팩토링 결과를 사용자에게 보고 (변경 파일, 코드 증감, QA 결과).

---

## 유형 C: QA 검증 (개발팀장, 도메인 검증 시 도메인팀장)

### Phase 1: 개발팀장에게 QA 지시

```
Agent(
  subagent_type: "dev-lead",
  name: "dev-lead",
  prompt: """
  [부서장 → 개발팀장] QA 검증 지시

  검증 대상: {대상 모듈/파일}
  작업 유형: QA 검증

  QA Inspector를 호출하여 경계면 교차 비교 검증을 수행하라:
  - API 응답 shape ↔ 프론트 접근 패턴
  - 라우트 등록 ↔ 프론트 경로
  - DB 스키마 ↔ API 필드
  - 예외 계층 준수

  도메인 로직 검증 필요 시 해당 전문가를 Agent로 호출하라.
  
  완료 후 QA 리포트를 보고하라.
  """
)
```

### Phase 2: 결과 취합 + 보고

QA 리포트를 사용자에게 보고 (PASS/FAIL, 발견 이슈, 수정 상태).

---

## 유형 D: 소규모 수정 (직접 처리)

팀 구성 없이 직접 코드를 수정한다. 에이전트 오버헤드가 작업량보다 크기 때문.

필요 시 단일 도메인 전문가를 Agent로 호출하여 자문받을 수 있다.

---

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
| 도메인 전문가 합의 불가 | 부서장이 보수적 입장(Graham 원칙) 기반 결정 |
| 테스트 반복 실패 (3회+) | 개발팀장이 접근법 재검토 + 요건 수용 기준 재확인 |
| 기존 테스트 회귀 | 다음 요건 중지, 회귀 수정 후 재개 |
| 프론트 빌드 실패 | 에러 분석 + 수정 후 재빌드 |
| 규모 판단 오류 | 유형 D → A/B/C로 에스컬레이션 가능 |
| 도메인 자문 필요 (개발 중) | 개발팀장이 해당 전문가를 Agent로 직접 호출 |

## 테스트 시나리오

### 정상 흐름 — 기능 개발 (유형 A)
```
사용자: "포트폴리오 대시보드 만들어줘"
→ Phase 0: 유형 A 판정 (새 페이지 + 새 API)
→ Phase 1: domain-lead 호출 → 도메인 전문가 팀 구성 → 요건서 산출
→ 사용자 승인
→ Phase 2: dev-lead 호출 → TDD 팀 구성 → R_1~R_n RED→GREEN→VERIFY
→ Phase 3: 결과 취합 + 보고
```

### 리팩토링 (유형 B)
```
사용자: "프론트엔드 훅 중복 정리해줘"
→ Phase 0: 유형 B 판정
→ Phase 1: dev-lead 호출 → refactor-engineer 감사 → qa-inspector 검증
→ Phase 2: 결과 취합 + 보고
```

### 소규모 수정 (유형 D)
```
사용자: "Header에 포트폴리오 링크 추가해줘"
→ Phase 0: 유형 D 판정 (파일 2개 수정)
→ 직접 Header.jsx + App.jsx 수정
```
