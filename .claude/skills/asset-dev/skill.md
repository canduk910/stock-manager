---
name: asset-dev
description: "통합자산관리 시스템 개발 오케스트레이터. 포트폴리오 대시보드, 자산배분 차트, 리밸런싱 엔진, 리스크 모니터링, 성과 추적, 투자 일지 등 자산관리 기능을 개발한다. 도메인 전문가 에이전트(MacroSentinel/MarginAnalyst/OrderAdvisor)에게 투자 로직을 자문받으며 FastAPI+React 코드를 작성한다. '대시보드 만들어줘', '포트폴리오 관리 기능', '리밸런싱 기능', '자산관리 시스템 개발', '성과 추적', '투자 일지', '리스크 모니터링' 등 자산관리 관련 개발 요청 시 반드시 이 스킬을 사용할 것. 단순 잔고 조회나 종목 분석(→ value-invest)과는 구분된다."
---

# 통합자산관리 시스템 개발 오케스트레이터

도메인 전문가 에이전트의 자문을 받으며 통합자산관리 기능을 개발하는 파이프라인을 조율한다.

**실행 모드**: 에이전트 팀 (TeamCreate + SendMessage + TaskCreate)

## Phase 1: 준비

### 1-1. 사용자 입력 파싱

사용자 요청에서 다음을 추출한다:
- **개발 대상 모듈**: 포트폴리오 대시보드 / 리밸런싱 / 리스크 모니터링 / 성과 추적 / 투자 일지 / 전체
- **범위**: 백엔드만 / 프론트엔드만 / 풀스택
- **우선순위**: 단일 모듈 / 전체 시스템 점진 개발

### 1-2. 워크스페이스 생성

```bash
mkdir -p _workspace/dev
```

`_workspace/dev/00_request.json`에 파싱된 요청 저장.

## Phase 2: 팀 구성

TeamCreate로 개발팀을 구성한다:

```
팀 이름: asset-dev-team
팀원:
  - dev-architect  (agent: dev-architect.md, model: opus)
  - qa-inspector   (agent: qa-inspector.md, model: opus)
  - macro-sentinel (agent: macro-sentinel.md, model: opus)
  - margin-analyst (agent: margin-analyst.md, model: opus)
  - order-advisor  (agent: order-advisor.md, model: opus)
```

> ValueScreener는 스크리닝 UI 개발 시에만 추가한다.

TaskCreate로 개발 작업을 등록한다:

```
Task 1: "도메인 자문 수집"
  assignee: dev-architect
  description: "개발 대상 기능에 필요한 투자 로직을 도메인 전문가에게 자문"
  depends_on: 없음

Task 2: "설계 문서 작성"
  assignee: dev-architect
  description: "자문 결과 + 코드 분석 기반 설계 (API, DB, UI)"
  depends_on: Task 1

Task 3: "백엔드 구현"
  assignee: dev-architect
  description: "DB store → 서비스 → 라우터 순차 구현"
  depends_on: Task 2

Task 4: "백엔드 QA 검증"
  assignee: qa-inspector
  description: "DB→서비스→API 데이터 흐름 + 예외 계층 + 도메인 로직 교차 비교 검증"
  depends_on: Task 3

Task 5: "프론트엔드 구현"
  assignee: dev-architect
  description: "API 모듈 → 훅 → 컴포넌트 → 페이지 순차 구현. Task 4 버그 수정 포함"
  depends_on: Task 4

Task 6: "통합 QA 검증"
  assignee: qa-inspector
  description: "API↔프론트 shape + 라우팅 + 전체 데이터 흐름 + 빌드 테스트 교차 비교 검증"
  depends_on: Task 5

Task 7: "최종 수정 + 보고"
  assignee: dev-architect
  description: "Task 6 버그 수정 + 서버 실행 + 결과 보고"
  depends_on: Task 6
```

## Phase 3: 도메인 자문 수집

dev-architect가 관련 도메인 전문가에게 자문을 요청한다.

### 모듈별 자문 매트릭스

| 모듈 | MacroSentinel | MarginAnalyst | OrderAdvisor |
|------|:---:|:---:|:---:|
| 포트폴리오 대시보드 | 체제 배너 표시 기준 | 종목별 안전마진 등급 표시 | 자산 배분 기준, 현금 비중 규칙 |
| 리밸런싱 엔진 | 체제별 목표 배분 비율 | 안전마진 하락 종목 매도 기준 | 매도/매수 수량 계산, 거래 비용 |
| 리스크 모니터링 | VIX/버핏지수 경고 임계값 | 등급 하락 알림 조건 | 집중도 한도, 손절 근접 판단 |
| 성과 추적 | 벤치마크 지수 데이터 | - | 수익률 계산 방식, 배당 반영 |
| 투자 일지 | 체제 기록 | 매매 시점 등급/안전마진 | 주문 이력 데이터 구조 |

자문 결과를 `_workspace/dev/01_domain_advice.json`에 저장.

### 자문 메시지 형식

```
[DEV 자문 요청] {모듈명}
질문: {구체적 질문}
맥락: {현재 구현 중인 내용}
필요한 것: {데이터 구조 / 계산 공식 / 비즈니스 규칙 / API 추천}
```

## Phase 4: 설계 + 구현

### 4-1. 설계 문서 작성

dev-architect가 자문 결과 + 기존 코드 분석을 종합하여 설계 문서를 작성한다:
- `_workspace/dev/02_design.md` — API 엔드포인트, DB 스키마, UI 와이어프레임

### 4-2. 구현 순서

1. **DB 레이어** (필요 시): `stock/{module}_store.py` — db_base.py 패턴
2. **서비스 레이어**: `services/{module}_service.py` — 비즈니스 로직
3. **API 레이어**: `routers/{module}.py` + `main.py` 라우터 등록
4. **프론트엔드 API**: `frontend/src/api/{module}.js`
5. **프론트엔드 훅**: `frontend/src/hooks/use{Module}.js`
6. **프론트엔드 컴포넌트**: `frontend/src/components/{module}/`
7. **프론트엔드 페이지**: `frontend/src/pages/{Module}Page.jsx` + `App.jsx` 라우트

### 4-3. 구현 중 실시간 자문

도메인 로직 구현 중 불확실한 부분이 발견되면 즉시 SendMessage로 도메인 전문가에게 자문:

```
[DEV 자문 요청] 리밸런싱 매도 수량 계산
질문: 과대비중 종목 매도 시 목표 비중까지 줄이는 수량 계산 공식은?
맥락: rebalance_service.py 구현 중 — calculate_sell_quantity() 함수
필요한 것: 계산 공식 + 소수점 처리 + 최소 거래단위 규칙
```

### 4-4. 개발 컨벤션

#### 백엔드
- 라우터: `APIRouter(prefix="/api/{module}", tags=["{Module}"])`
- 예외: `ServiceError` 계층만 사용 (`services/exceptions.py`). HTTPException 직접 raise 금지
- DB: `stock/db_base.py`의 `connect()` 사용, WAL 모드 + timeout 10초
- DB 위치: `~/stock-watchlist/{module}.db` 또는 기존 DB에 테이블 추가

#### 프론트엔드
- 페이지: `{Name}Page.jsx` — 레이아웃 + 데이터 훅 연결
- 컴포넌트: 재사용 가능한 단위로 분리, Tailwind CSS v4 유틸리티
- 훅: `use{Name}.js` — fetch + 상태 + 에러 핸들링 패턴
- 차트: Recharts 사용 (이미 프로젝트 의존성)
- 라우팅: `App.jsx`에 `<Route path="/{module}" element={<{Module}Page />} />` 추가
- Header: `frontend/src/components/common/Header.jsx`에 네비게이션 링크 추가

## Phase 5: 점진적 QA (Incremental QA)

**전체 완성 후가 아니라, 백엔드/프론트엔드 각 구현 직후 검증한다.**

### 5-1. 백엔드 QA (Task 4)

qa-inspector가 백엔드 구현 직후 검증:
- DB → 서비스 → API 데이터 흐름 정합성
- 예외 계층 준수 (ServiceError만 사용, HTTPException 금지)
- 도메인 전문가에게 투자 로직 정확성 검증
- 버그 발견 시 DevArchitect에게 **파일:라인 + 수정 방법** 구체적 지시

### 5-2. 통합 QA (Task 6)

qa-inspector가 프론트엔드 구현 직후 전체 검증:
- API 응답 shape ↔ 프론트 훅 접근 패턴 교차 비교
- 라우트 등록 (main.py + App.jsx + Header.jsx + fetch URL) 일관성
- npm run build + curl 테스트
- 검증 리포트를 `_workspace/dev/qa_report.md`에 작성

### 5-3. 버그 수정 루프

```
qa-inspector → [버그 리포트] → dev-architect → [수정] → qa-inspector → [재검증]
```

재검증은 수정된 영역만 대상으로 한다.

## Phase 6: 최종 보고

최종 보고서 구조:
```markdown
## 개발 완료 보고

### 변경 파일
- 신규: {file_list}
- 수정: {file_list}

### 신규 API 엔드포인트
- GET /api/{module}/... — 설명
- POST /api/{module}/... — 설명

### 신규 페이지
- /{path} — 기능 설명

### 도메인 전문가 자문 내역
- MacroSentinel: {요약}
- OrderAdvisor: {요약}

### QA 검증 결과
- 경계면 검증: {n}건 PASS / {m}건 수정 완료
- 도메인 로직: 전문가 확인 완료
- 빌드: OK/FAIL
- API 테스트: OK/FAIL (상세)
```

## 기능 모듈 명세

개발 대상 모듈은 `references/feature-specs.md`에 상세 기술한다. 핵심 모듈 요약:

### Module 1: 포트폴리오 대시보드 (`/portfolio`)
- 전체 자산 현황 카드 (총 평가금액, 수익률, 현금 비중)
- 자산 배분 파이 차트 (종목별/섹터별, Recharts PieChart)
- 수익률 추이 라인 차트 (일/주/월 기간 선택)
- 매크로 체제 연동 상단 배너 (체제 색상 + 권고 요약)
- 보유 종목별 안전마진 등급 뱃지 (A/B+/B/C/D)
- **기존 API 활용**: `/api/balance` + `/api/macro/sentiment` + `/api/advisory/{code}/data`

### Module 2: 리밸런싱 엔진 (`/rebalance`)
- 목표 자산배분 설정 UI (종목당 5% 상한, 현금 25% 하한 — Graham 규칙)
- 현재 vs 목표 비교 테이블 (편차 하이라이트)
- 리밸런싱 제안 생성 (과대비중 매도 + 과소비중/신규 매수)
- 원클릭 예약주문 등록 (사용자 승인 필수 — OrderAdvisor 원칙 준수)
- **신규 서비스 필요**: `services/rebalance_service.py`

### Module 3: 리스크 모니터링 (`/risk`)
- 포트폴리오 집중도 HHI 지수 (허핀달-허쉬만)
- 종목별 안전마진 변화 추적 타임라인
- 매크로 체제 변화 히스토리
- 손절선 근접 종목 경고 (현재가 vs 손절가 대비 %)
- **신규 store 필요**: `stock/risk_store.py` (안전마진 스냅샷 이력)

### Module 4: 성과 추적 (`/performance`)
- 기간별 수익률 (일/주/월/연, 라인차트)
- 벤치마크(KOSPI/S&P500) 대비 초과수익률
- 종목별 기여도 분석 (워터폴 차트)
- 배당 수익 포함 총수익률 (TWR 방식)
- **기존 API 활용**: `/api/balance` 이력 + `/api/macro/indices`

### Module 5: 투자 일지 (`/journal`)
- 매매 이력 타임라인 (체결 내역 기반)
- 매매 시점 컨텍스트 (체제/안전마진/등급 스냅샷)
- 의사결정 회고 메모 (사용자 입력)
- 성과 연동 학습 포인트
- **신규 store 필요**: `stock/journal_store.py`

## 기존 API 재활용 맵

| 기능 | 기존 API | 용도 |
|------|---------|------|
| 잔고/보유종목 | `GET /api/balance` | 포트폴리오 현황, 자산 배분 |
| 매수가능금액 | `GET /api/order/buyable` | 리밸런싱 매수 여력 |
| 미체결주문 | `GET /api/order/open` | 중복 주문 방지 |
| 예약주문 등록 | `POST /api/order/reserve` | 리밸런싱 실행 |
| 체결내역 | `GET /api/order/executions` | 성과 추적, 투자 일지 |
| 주문이력 | `GET /api/order/history` | 투자 일지 |
| 매크로 심리 | `GET /api/macro/sentiment` | 체제 배너, 리스크 모니터링 |
| 매크로 지수 | `GET /api/macro/indices` | 벤치마크, 성과 비교 |
| 종목 분석 데이터 | `GET /api/advisory/{code}/data` | 안전마진/등급 정보 |
| 종목 재무 | `GET /api/detail/{code}/report` | 재무 건전성 |
| 종목 시세 | `GET /api/advisory/{code}/ohlcv` | 가격 추이 |
| 관심종목 | `GET /api/watchlist` | 모니터링 대상 |

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| 도메인 자문 실패 | 기존 코드 패턴에서 추론 + TODO 주석으로 표기 |
| 기존 API 호환성 문제 | 새 엔드포인트로 분리, 기존 API 유지 |
| 프론트엔드 빌드 실패 | 에러 분석 + 수정 후 재빌드, 의존성 문제면 사용자 승인 후 추가 |
| DB 스키마 충돌 | 새 DB 파일 분리 (기존 watchlist.db/orders.db 변경 최소화) |
| KIS 키 미설정 | 잔고 조회 불가 시 모의 데이터로 UI 개발, 실제 연동은 키 설정 후 |

## 테스트 시나리오

### 정상 흐름 — 포트폴리오 대시보드
```
사용자: "포트폴리오 대시보드 만들어줘"
→ dev-architect: MacroSentinel에게 "대시보드 매크로 배너 표시 기준 자문"
→ dev-architect: OrderAdvisor에게 "자산 배분 기준, 현금 비중 규칙 자문"
→ dev-architect: MarginAnalyst에게 "종목별 안전마진 등급 뱃지 표시 기준 자문"
→ dev-architect: 설계 문서 작성 (_workspace/dev/02_design.md)
→ dev-architect: 백엔드 — services/portfolio_service.py + routers/portfolio.py
→ dev-architect: 프론트엔드 — api/portfolio.js + hooks/usePortfolio.js + PortfolioPage.jsx
→ dev-architect: main.py 라우터 등록 + App.jsx 라우트 추가 + Header 네비 추가
→ dev-architect: 테스트 + 보고
```

### 특정 기능 추가
```
사용자: "보유 종목 안전마진 변화를 추적하는 기능 추가해줘"
→ dev-architect: MarginAnalyst에게 "안전마진 재계산 방식, 변화 추적 주기 자문"
→ dev-architect: 기존 advisory 데이터 활용 방안 설계
→ dev-architect: stock/risk_store.py (스냅샷 저장) + services/risk_service.py
→ dev-architect: 프론트엔드 컴포넌트 구현
→ dev-architect: 테스트 + 보고
```

### 에러 흐름
```
사용자: "리밸런싱 기능 개발해줘"
→ dev-architect: OrderAdvisor에게 자문 요청 → 응답 지연
→ dev-architect: 기존 portfolio-check 스킬 패턴에서 포지션 사이징 규칙 추론
→ dev-architect: 추론 기반 구현 + TODO 주석 ("OrderAdvisor 자문 후 검증 필요")
→ dev-architect: 불확실한 부분 명시하여 보고
```
