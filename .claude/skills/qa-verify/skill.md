---
name: qa-verify
description: "통합 정합성 QA 검증. DevArchitect가 구현한 코드의 API↔프론트 shape 일치, 라우팅 정합성, DB→API→UI 데이터 흐름, 예외 계층 준수, 투자 도메인 로직 정확성을 교차 비교 검증한다. QA Inspector 에이전트 전용. '코드 검증', 'QA', '테스트', '정합성 검사' 요청 시 사용."
---

# 통합 정합성 QA 검증

DevArchitect가 구현한 코드의 경계면 불일치를 체계적으로 검출한다.

## 입력

- DevArchitect의 구현 완료 보고 (변경 파일 목록)
- `_workspace/dev/01_domain_advice.json` (도메인 자문 결과)
- `_workspace/dev/02_design.md` (설계 문서)

## 검증 프로세스

### Step 1: 변경 파일 분류

DevArchitect가 보고한 변경 파일을 레이어별로 분류한다:

```
DB:        stock/{module}_store.py
서비스:     services/{module}_service.py
라우터:     routers/{module}.py
등록:       main.py (include_router)
프론트API:  frontend/src/api/{module}.js
프론트훅:   frontend/src/hooks/use{Module}.js
컴포넌트:   frontend/src/components/{module}/*.jsx
페이지:     frontend/src/pages/{Module}Page.jsx
라우팅:     frontend/src/App.jsx
네비:       frontend/src/components/common/Header.jsx
```

### Step 2: 경계면 교차 비교 (핵심)

#### 2-1. API 응답 shape ↔ 프론트 훅

**방법**: 라우터의 return dict 키와 프론트 코드의 접근 패턴을 대조한다.

```bash
# 1. 라우터에서 return 패턴 추출
# routers/{module}.py 에서 return { ... } 또는 return ResponseModel 찾기

# 2. 프론트 API 모듈에서 fetch URL + 응답 접근 추출
# frontend/src/api/{module}.js 에서 fetch('/api/...') 패턴 찾기

# 3. 프론트 훅에서 상태 접근 패턴 추출
# frontend/src/hooks/use{Module}.js 에서 data.{field} 접근 찾기
```

**검증 항목:**
- [ ] API 반환 dict의 모든 키가 프론트에서 접근되는가 (미사용 필드 식별)
- [ ] 프론트가 접근하는 모든 키가 API 반환에 존재하는가 (**핵심 — 런타임 에러 원인**)
- [ ] 중첩 구조 일치 (`{ items: [...] }` vs 배열 직접 반환)
- [ ] None/null 처리: API에서 None 반환 가능한 필드를 프론트가 optional chaining으로 접근하는가
- [ ] 숫자 타입: API의 float/int 구분이 프론트 표시(소수점, %, 원)와 일치하는가

**이 프로젝트 특유 패턴:**
```python
# 백엔드: snake_case dict 반환 (이 프로젝트의 기본 패턴)
return {"total_evaluation": 50000000, "stock_list": [...]}

# 프론트: 그대로 snake_case 접근 (이 프로젝트는 camelCase 변환 안 함)
const { total_evaluation, stock_list } = data;
```
> 이 프로젝트는 snake_case를 프론트까지 그대로 사용한다. camelCase 변환 레이어가 없으므로 API 키명을 정확히 맞춰야 한다.

#### 2-2. 라우트 등록 ↔ 프론트 경로

```
검증 항목:
1. main.py에 include_router(module.router) 등록되었는가
2. routers/{module}.py의 prefix="/api/{module}" 확인
3. App.jsx에 <Route path="/{module}" /> 추가되었는가
4. Header.jsx에 네비게이션 링크 추가되었는가
5. 프론트 api/{module}.js의 fetch URL이 실제 prefix와 일치하는가
```

**체크:**
- [ ] `main.py` include_router 추가됨
- [ ] `App.jsx` Route path 추가됨
- [ ] `Header.jsx` 네비 링크 추가됨
- [ ] 프론트 fetch URL prefix === 라우터 prefix
- [ ] 페이지 내 navigate/Link 경로가 실제 Route와 매칭

#### 2-3. DB → 서비스 → API 데이터 흐름

```
검증 항목:
1. CREATE TABLE 컬럼명 → store 함수 반환 dict 키 매핑
2. store 반환 → service 가공 → router 반환까지 필드명 추적
3. 타입 변환 누락 확인 (SQLite TEXT → Python str → JSON string)
4. row_to_dict() 사용 시 컬럼 순서 정확성
```

**체크:**
- [ ] DB 컬럼명이 최종 API 응답까지 일관되게 전달됨
- [ ] JSON 직렬화 필드(`*_json` 컬럼)가 서비스에서 `json.loads()` 변환됨
- [ ] datetime 필드가 ISO 8601 문자열로 변환됨
- [ ] NULL 컬럼이 API에서 `None` → JSON `null`로 정상 변환됨

#### 2-4. 예외 계층 준수

```bash
# 신규 서비스 파일에서 raise 패턴 검색
# 허용: raise NotFoundError(...), raise ExternalAPIError(...), raise ConfigError(...), raise PaymentRequiredError(...)
# 금지: raise HTTPException(...)
```

**체크:**
- [ ] 모든 서비스에서 `ServiceError` 하위 클래스만 raise
- [ ] `HTTPException` 직접 raise 없음
- [ ] 적절한 하위 클래스 선택 (404=NotFoundError, 502=ExternalAPIError, 503=ConfigError)
- [ ] 에러 메시지가 사용자에게 유용한 정보를 포함

### Step 3: 도메인 로직 검증

구현된 투자 로직을 도메인 전문가에게 코드 발췌와 함께 검증 요청한다.

**검증 메시지 형식:**
```
[QA 검증 요청] {검증 대상}
파일: {파일경로}:{라인 범위}
구현 코드:
```python
{핵심 로직 발췌 — 10줄 이내}
```
질문: 이 구현이 {Graham 규칙/포지션 사이징/안전마진 계산}에 부합하는가?
우려: {불일치 의심 포인트, 있으면}
```

**모듈별 도메인 검증 항목:**

| 모듈 | 검증 로직 | 자문 대상 |
|------|----------|----------|
| 포트폴리오 | 체제별 배너 색상/메시지 매핑 | MacroSentinel |
| 포트폴리오 | 안전마진 등급 뱃지 기준 (A/B+/B/C/D 점수 범위) | MarginAnalyst |
| 리밸런싱 | 체제별 목표 배분 (75%/65%/50%/0%) | OrderAdvisor |
| 리밸런싱 | 매도 수량 = (현재비중 - 목표비중) × 총자산 / 현재가 | OrderAdvisor |
| 리밸런싱 | 매도 우선 → 현금 확보 → 매수 순서 | OrderAdvisor |
| 리스크 | HHI = sum(w²) × 10000, 임계값 1000/1800 | OrderAdvisor |
| 리스크 | 안전마진 하락 알림 조건 (등급 변화 or 절대 하락 %) | MarginAnalyst |
| 성과 | TWR 계산 (외부 현금흐름 제거) | OrderAdvisor |
| 성과 | 벤치마크 비교 기준일/기준가 | MacroSentinel |

### Step 4: 빌드 + 실행 테스트

```bash
# 1. 프론트엔드 빌드 (정적 오류 검출)
cd frontend && npm run build

# 2. 서버 실행 테스트
uvicorn main:app --host 0.0.0.0 --port 8000 &
sleep 3

# 3. 신규 API 엔드포인트 curl 테스트
curl -s http://localhost:8000/api/{module}/... | python -m json.tool

# 4. 응답 shape 실제 확인 (프론트 기대와 대조)
```

### Step 5: 검증 리포트 작성

`_workspace/dev/qa_report.md`에 작성:

```markdown
# QA 검증 리포트

## 요약
- 검증 일시: {timestamp}
- 대상 모듈: {module_name}
- 변경 파일: {count}개

## 결과
- PASS: {n}건
- FAIL: {m}건
- SKIP: {k}건 (검증 불가)

## 경계면 검증

### API ↔ 프론트엔드
| 엔드포인트 | API shape | 프론트 접근 | 결과 |
|-----------|-----------|-----------|------|
| GET /api/portfolio/overview | {키 목록} | {접근 패턴} | PASS/FAIL |

### 라우팅
| 경로 | main.py | App.jsx | Header | fetch URL | 결과 |
|------|---------|---------|--------|-----------|------|

### 데이터 흐름
| 필드 | DB 컬럼 | 서비스 | API 응답 | 프론트 | 결과 |
|------|---------|--------|---------|--------|------|

### 예외 계층
| 파일 | raise 패턴 | 결과 |
|------|-----------|------|

## 도메인 로직 검증

### {로직명}
- 코드 위치: {파일:라인}
- 전문가 확인: {MacroSentinel/MarginAnalyst/OrderAdvisor}
- 결과: PASS/FAIL
- 비고: {자문 결과 요약}

## 버그 목록

### BUG-001: {1줄 요약} [CRITICAL/MAJOR/MINOR]
- 위치: {파일:라인}
- 경계면: {생산자} ↔ {소비자}
- 문제: {상세}
- 수정 제안: {구체적 변경}

## 빌드/실행 테스트
- npm run build: PASS/FAIL
- uvicorn 실행: PASS/FAIL
- API curl 테스트: {결과}
```

## 검증 체크리스트 (전체)

### API ↔ 프론트엔드 연결
- [ ] 모든 API 엔드포인트의 반환 shape과 프론트 접근 패턴이 일치
- [ ] 래핑된 응답은 프론트에서 올바르게 unwrap
- [ ] snake_case 키명이 프론트까지 일관 (이 프로젝트는 변환 없음)
- [ ] None/null 필드에 대한 프론트 방어 코드 존재
- [ ] 모든 API 엔드포인트에 대응하는 프론트 fetch 함수가 존재하고 호출됨

### 라우팅 정합성
- [ ] main.py에 새 라우터가 include_router로 등록됨
- [ ] App.jsx에 새 Route path가 추가됨
- [ ] Header.jsx에 네비게이션 링크가 추가됨
- [ ] 프론트 내 모든 navigate/Link 경로가 실제 Route와 매칭

### 데이터 흐름 정합성
- [ ] DB 컬럼명 → store → service → router → frontend까지 필드명 추적 완료
- [ ] JSON 직렬화/역직렬화 누락 없음
- [ ] 타입 변환 (datetime, float, None) 정상

### 예외 처리
- [ ] 신규 서비스에서 HTTPException 직접 raise 없음
- [ ] ServiceError 적절한 하위 클래스 사용
- [ ] 프론트 에러 핸들링이 status code별로 적절

### 투자 도메인 로직
- [ ] Graham 공식 (안전마진, Graham Number) 정확성 — MarginAnalyst 확인
- [ ] 포지션 사이징 규칙 (체제별 한도) — OrderAdvisor 확인
- [ ] 리밸런싱 규칙 (매도 우선, 현금 버퍼) — OrderAdvisor 확인
- [ ] 리스크 지표 (HHI, 손절 기준) — OrderAdvisor 확인
- [ ] 매크로 체제 표시 (색상, 문구, 임계값) — MacroSentinel 확인
- [ ] 수익률 계산 (TWR, 배당 포함) — OrderAdvisor 확인
