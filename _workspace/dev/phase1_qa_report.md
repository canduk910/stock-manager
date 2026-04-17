# Phase 1 QA 리포트 — 프롬프트 보강 + 개별↔포트폴리오 연계

**작성**: 2026-04-17 qa-inspector
**대상**: Phase 1 구현 (DevArchitect)
**플랜**: `/Users/koscom/.claude/plans/buzzing-swinging-fern.md` Phase 1 (1-1~1-6)
**Diff**: `_workspace/dev/phase1_diff.md`
**1차 검증**: 2026-04-17 (BUG-1 발견)
**2차 재검증**: 2026-04-17 (OrderAdvisor 자문 반영 + BUG-1 수정 확인)

---

## 결과 요약 (2차 재검증 완료)

| 구분 | 건수 | 비고 |
|------|------|------|
| PASS | 15 | 경계면/도메인/하위호환 + OrderAdvisor 자문 반영 확인 + BUG-1 수정 확인 |
| MAJOR 버그 | 0 | ~~BUG-1~~ **수정 완료** (L691-692 System Prompt 규칙 참조로 일원화) |
| MINOR 관찰 | 3 | 래퍼 함수 잔존 + 죽은 키 + 규칙 G 데이터 의존성(Phase 2 필수) |
| 미검증 | 2 | E2E API 호출 / GPT 응답 실측 (OPENAI_API_KEY 필요) |
| 자문 도착 | 1 | order-advisor 반영 완료. macro-sentinel/margin-analyst/value-screener 대기 중 (에이전트 원문 스펙 기반 선반영) |

**최종 판정**: **Phase 1 QA 통과 — Phase 2 진행 가능**.

### 2차 재검증 추가 확인 사항
- System Prompt 4체제 전부에 OrderAdvisor 자문 반영:
  - `최종 포지션% = 체제 종목당 한도% × grade_factor` 공식 추가 (L466) ✓
  - 매수 불가 6조건 a)~f) 추가 (L470-473): 등급/할인율/RSI/중복/한도/Value Trap ✓
- Portfolio System Prompt 4체제 전부에 신규 규칙 포함:
  - 규칙 E 강화 (4대 제약 + reasoning 2가지) ✓
  - 규칙 F 추가 (Value Trap 매도 승계 + RSI>80 신규매수 금지) ✓
  - 규칙 G 추가 (가중평균 B 미만 → 신규 편입 전면 보류) ✓
- User Prompt BUG-1 수정: "강한매수 -15%, 매수 -12%, 조건부 -10%" **완전 제거** → System Prompt 7점등급 규칙 참조로 일원화

### 2차 재검증 프롬프트 길이 (4체제)

| 체제 | System Prompt | 변화 |
|------|--------------|------|
| accumulation | 2798자 | +257자 (+80토큰, OrderAdvisor 보강) |
| selective | 2792자 | +251자 |
| cautious | 2810자 | +260자 |
| defensive | 2825자 | +275자 |
| User Prompt (빈 데이터) | 2062자 | 변화 미미 |

Portfolio System Prompt는 체제 및 역발상 규칙 포함 시 3045~4024자(8000토큰 한도 대비 여유).

---

## 1. 경계면 교차 검증

### 1-1. `macro_regime.py` 공용 모듈 (PASS)

**검증 방법**: 3개 서비스(advisory/portfolio_advisor/pipeline)의 `_determine_regime()` 호출처가 모두 공용 `determine_regime()`에 위임되는지 교차 확인.

| 서비스 | 파일:라인 | 반환 타입 | 위임 여부 | 결과 |
|--------|-----------|----------|-----------|------|
| advisory_service | advisory_service.py:365-371 | `tuple[str, str]` | ✓ 래퍼 | PASS |
| portfolio_advisor_service | portfolio_advisor_service.py:251-254 | `tuple[str, str]` | ✓ 래퍼 | PASS |
| pipeline_service | pipeline_service.py:26-45 | `dict` | ✓ 래퍼 + 하위호환 키 주입 | PASS |

**스모크 테스트** (실행 완료):
```
Low+Fear ratio=0.75/fg=25/vix=15 -> accumulation ✓
Ext+ExtGreed ratio=1.7/fg=85/vix=20 -> defensive ✓
VIX override ratio=1.1/fg=70/vix=40 -> selective / fg_level=extreme_fear ✓
Pct conversion ratio=235.2 -> 2.352 / buffett_level=extreme ✓
```

**매트릭스 완전성**: `REGIME_MATRIX` 20셀 모두 존재 (5 fg × 4 buffett), 누락 없음.

**파라미터 일관성**:
- `accumulation`: margin=20, stock_max=75, cash_min=25, single_cap=5, per_max=20, pbr_max=2.0, roe_min=5 — macro-sentinel.md 원문과 **완전 일치**
- `selective`: 30/65/35/4/15/1.5/8 — **완전 일치**
- `cautious`: 40/50/50/3/12/1.2/10 — **완전 일치**
- `defensive`: margin=999/stock_max=25/cash_min=75/single_cap=0/per_max=0/pbr_max=0 — 원문 "종목당 0%/총투자 0%/현금 100%"와 **stock_max/cash_min 불일치** (원문 0/100, 구현 25/75)

> **MINOR**: defensive 파라미터가 원문 스펙(0/100)과 다르게 25/75로 설정됨. 단, `_screen_stocks()`가 regime=="defensive"면 빈 리스트 반환하므로 실제 작동 영향 없음. macro-sentinel에 의도 자문 전송함.

### 1-2. pipeline_service 하위호환 키 (PASS)

**검증**: 기존 pipeline_service 호출부가 기대하는 키(`margin_threshold`, `max_position`, `max_invest`)가 param dict에 유지되는지.

```python
# pipeline_service.py:34-36
params["margin_threshold"] = params.get("margin", 999)  # = 40 (cautious) 정상
params["max_position"] = (params.get("single_cap", 0) or 0) / 100.0  # = 0.03
params["max_invest"] = (params.get("stock_max", 0) or 0) / 100.0  # = 0.50
```

- `margin_threshold`는 `_generate_recommendations()` L304에서 실제 소비됨 ✓
- `max_position` / `max_invest`는 **소비처 없음** (MINOR 관찰)

### 1-3. 서비스 경계면 — `_extract_report_summary()` v1 대응 (PASS)

**테스트 시나리오**: v1 리포트 JSON 구조를 portfolio 컨텍스트로 변환.

```
입력: {report: {종합투자의견: {등급, 요약 200자}, 전략별평가: {안전마진: {할인율: 25.3}}, 리스크요인: [...]}}
출력: {grade=None, summary_2lines(180자), discount_rate=25.3, risks[2개, 각 50자]}
```

- 요약 180자 초과 시 `"..."` 접미 절단 확인 ✓
- 리스크 상위 2개만 반환 ✓
- 각 리스크 50자 초과 시 `"..."` 절단 확인 ✓
- 빈 리포트 `{}` → 전 필드 None/[] 반환 ✓
- 예외 발생 시 `_fetch_latest_report_summary()`에서 안전하게 None 반환 ✓

### 1-4. 전체 앱 임포트 (PASS)

```
main.py imports OK
app: FastAPI
routes count: 71
```

모든 라우터 정상 등록, 순환 임포트 없음.

### 1-5. 프론트 경계면 (PASS, 변경 없음)

**검증**: Phase 1이 "응답 JSON 스키마 변경 없음" 원칙을 지키는지 확인 — frontend/src 전체에서 신규 필드(`latest_report_*`, `schema_version`, `종목등급` 등) 사용 여부 grep.

결과: **0건 검출**. 프론트는 Phase 1에서 전혀 접촉되지 않음. Graceful degrade 조건 충족.

---

## 2. 예외 계층 준수 검증 (PASS)

### 2-1. `HTTPException` 직접 raise 확인

```
grep HTTPException services/
→ CLAUDE.md 주석 + advisory_service.py docstring 참조 외 0건
```

**결과**: 모든 신규/변경 코드에서 `HTTPException` 직접 raise 없음. ServiceError 계층(ConfigError/NotFoundError/ExternalAPIError/PaymentRequiredError) 사용 ✓

### 2-2. macro_regime.py 예외

`determine_regime()`은 예외를 raise하지 않고 None/기본값(cautious) 반환. 데이터 누락에 robust. `ServiceError` 계층 불필요.

---

## 3. 도메인 로직 정확성 검증

### 3-1. 7점 등급 체계 — margin-analyst.md 1:1 대조 (PASS)

System Prompt (`_build_system_prompt()` L444-455) vs `.claude/agents/margin-analyst.md` L31-48:

| # | 지표 | 원문 4/3/2/1점 | System Prompt | 일치 |
|---|------|---------------|---------------|------|
| 1 | Graham 할인율 | >40% / 20-40% / 0-20% / <0% | 동일 | ✓ |
| 2 | PER vs 5년평균 | <-30% / -30~-10% / -10~+10% / >+10% | 동일 | ✓ |
| 3 | PBR 절대 | <0.7 / 0.7-1.0 / 1.0-1.5 / >1.5 | 동일 | ✓ |
| 4 | 부채비율 | <50% / 50-100% / 100-200% / >200% | 동일 | ✓ |
| 5 | 유동비율 | >2.0 / 1.5-2.0 / 1.0-1.5 / <1.0 | 동일 | ✓ |
| 6 | FCF 추세 | 3년 양수 / 2년 양수 / 1년 양수 / 음수 | "3년/2년/1년/0년" | 의미 동일 |
| 7 | 매출 CAGR | >10% / 5-10% / 0-5% / <0% | 동일 | ✓ |

등급 컷오프: A=24-28, B+=20-23, B=16-19, C=12-15, D=<12 — **완전 일치** ✓

### 3-2. 체제 매트릭스 — macro-sentinel.md 1:1 대조 (PASS)

20셀 매트릭스 전부 확인:
- `low`: ext_fear=accumulation / fear=accumulation / neutral=selective / greed=cautious / ext_greed=cautious ✓
- `normal`: ext_fear=selective / fear=selective / neutral=cautious / greed=cautious / ext_greed=defensive ✓
- `high`: ext_fear=selective / fear=cautious / neutral=cautious / greed=defensive / ext_greed=defensive ✓
- `extreme`: ext_fear=cautious / fear=defensive / neutral=defensive / greed=defensive / ext_greed=defensive ✓

**VIX>35 오버라이드** 구현 확인 (macro_regime.py:109-111). 하이스테리시스 예외로 즉각 적용 (시장 패닉 대응).

### 3-3. OrderAdvisor 손절폭/포지션 — order-advisor.md 1:1 대조 (PASS, 단 User Prompt 충돌)

System Prompt (`_build_system_prompt()` L463-468):
- 손절폭: A=-8%, B+=-10%, B=-12%, C/D=진입 금지 ✓
- grade_factor: A=1.0, B+=0.75, B=0.50, C/D=0 ✓
- 분할매수: 50/30/20 ✓
- 익절가: Graham Number, risk_reward>=2.0 ✓
- 지정가 강제 ✓

**⚠ 그러나 User Prompt(L691-692)에는 "강한매수 -15%, 매수 -12%, 조건부 -10%"로 상반된 규칙이 남아있음** → MAJOR 버그 (아래 [4. 버그 리포트] 참조).

### 3-4. Value Trap 5규칙 — 플랜 기준 대조 (PASS, 원문 확장 상태)

System Prompt L472-478의 5규칙이 플랜(buzzing-swinging-fern.md:54)과 **완전 일치**. 단, `.claude/agents/value-screener.md` 원문은 3규칙만 명시 — 플랜에서 margin-analyst/order-advisor 도메인을 통합하여 확장한 상태. value-screener 에이전트에 원문 업데이트 자문 전송함.

---

## 4. 버그 리포트

### BUG-1 [MAJOR] ~~System Prompt ↔ User Prompt 손절폭 규칙 충돌~~ **[RESOLVED]**

**심각도**: MAJOR → **RESOLVED (2026-04-17)**

**위치**:
- 경계면: `services/advisory_service.py:463-464` (System Prompt) ↔ `services/advisory_service.py:691-692` (User Prompt JSON 스펙)

**문제 (1차 검증 시점)**:
```
System Prompt: "- 손절폭: A=-8%, B+=-10%, B=-12%, C/D=진입 금지."
User Prompt:   "손절근거": "손절가 산정 근거 (등급별 차등: 강한매수 -15%, 매수 -12%, 조건부 -10%)"
```

두 메시지가 상반된 손절폭 규칙을 GPT에게 동시 전달 → `stop_loss` 값 예측 불가.

**해결 (2차 재검증 시점)**:
DevArchitect가 User Prompt L691-692를 수정:
```python
# After (현재):
    "손절가": System Prompt 7점등급 손절폭 규칙(A=-8%/B+=-10%/B=-12%)에 따른 정수,
    "손절근거": "손절가 산정 근거 (System Prompt 7점등급 손절폭 규칙을 적용)",
    ...
    "리스크보상비율": (익절가-진입가)/(진입가-손절가) 소수점1자리 (<2.0이면 매수 보류),
    "분할매수제안": "1차 50%(진입가) - 2차 30%(1차-3%) - 3차 20%(1차-6%)"
```

**재검증 스모크 테스트**:
- "강한매수 -15%" 문구 잔존 검사: **0건** ✓
- "System Prompt 7점등급 손절폭" 참조 확인: **있음** ✓
- 3전략 프레임워크 등급(매수/중립/매도)과 7점 등급(A/B+/B/C/D)이 각자 역할로 분리됨 — 손절 계산은 7점 등급, 신호 판단은 3전략 등급 ✓

**조치 완료**: 수정 확인 후 Task #2 통과 처리.

---

## 5. 관찰 사항 (MINOR, 설계상 수용 가능)

### OBS-1 [MINOR] `_determine_regime()` 래퍼 함수 잔존

**위치**:
- `services/advisory_service.py:365-371`
- `services/portfolio_advisor_service.py:251-254`

**관찰**: 플랜(buzzing-swinging-fern.md:44)은 "_determine_regime() 삭제 → macro_regime.determine_regime() 호출"을 명시했으나, 구현은 2줄 래퍼로 유지됨.

**판정**: 호출부 영향 최소화 목적으로 의도된 설계 (Diff 문서 명시). 본 래퍼는 내부 로직 없이 단순 위임이므로 죽은 코드 아님. **허용**. 단, 플랜 텍스트와 정확히 일치하려면 래퍼 제거 + 호출부 2곳(`advisory_service.py:61`, `portfolio_advisor_service.py:453`)을 `_shared_determine_regime()` 직접 호출로 전환 권장.

### OBS-2 [MINOR] `max_position` / `max_invest` 키 미사용

**위치**: `services/pipeline_service.py:35-36`

**관찰**: params 딕셔너리에 `max_position` (single_cap/100) 과 `max_invest` (stock_max/100) 추가하지만 코드 전체에서 소비 없음.

**판정**: 하위호환 의도 — Diff 문서에도 "하위호환 params 키" 명시. 단, 사용처가 없으면 오해의 소지 있으므로 **주석 추가 권장**:
```python
# 하위호환 전용 — 과거 pipeline 코드의 params 키 기대. 현재 소비처 없음.
params["max_position"] = ...
params["max_invest"] = ...
```

---

## 6. 하위 호환성 검증

| 항목 | 검증 방법 | 결과 |
|------|----------|------|
| 응답 JSON 스키마 변경 없음 | `_build_prompt()` 649-701 JSON 예시 grep | PASS — 기존 6개 섹션 유지 |
| DB 스키마 변경 없음 | db/models/advisory.py diff 없음 | PASS |
| `_determine_regime()` 시그니처 유지 | advisory/portfolio 튜플 반환, pipeline dict 반환 | PASS (런타임 테스트 통과) |
| v1 리포트 grade=None graceful | `_extract_report_summary(v1)` 테스트 | PASS |
| 빈 리포트 처리 | `_extract_report_summary({})` 테스트 | PASS |
| `_fetch_latest_report_summary` 예외 안전 | try/except 확인 | PASS |

---

## 7. 프롬프트 품질 검증

### System Prompt 길이

| 체제 | 문자수 | 예상 토큰 | 핵심 규칙 포함 |
|------|--------|----------|---------------|
| accumulation | 2798자 | ~1000 tok | 7grade✓ matrix✓ stop_loss✓ valuetrap✓ |
| selective | 2792자 | ~1000 tok | ✓ ✓ ✓ ✓ |
| cautious | 2810자 | ~1000 tok | ✓ ✓ ✓ ✓ |
| defensive | 2825자 | ~1000 tok | ✓ ✓ ✓ ✓ |

### 3종 샘플 User Prompt (Diff 문서 인용)

| 종목 | 합계 | 대비 max_completion_tokens=8000 |
|------|------|------------------------------|
| 삼성전자 (005930) | 4911자 ≈ 1500 tok | 응답 6500 tok 여유 |
| NVDA | ~4817자 | 여유 확보 |
| 골프존 (215000) | ~4783자 | 여유 확보 |

**판정**: 토큰 한도 대비 여유 충분. Phase 2 신규 섹션 추가 시에도 여유 확보.

### 개별→포트폴리오 주입 확인

`_build_context()`에서 각 holding에 `latest_report_grade/summary/discount_rate/risks` 4개 필드 주입 확인. 10종목 × (요약 180자 + 리스크 2개×50자 = 280자) = 최대 2800자 ≈ 1000토큰 추가. 포트폴리오 프롬프트 총 6000~7000자 수준 예상 — 8000토큰 한도 이내.

System Prompt 규칙 A~E(L361-365)에서 "상충 시 reasoning에 명시" 원칙 포함 — reasoning에 개별 리포트 인용이 발생하도록 유도.

---

## 8. 미검증 항목 (후속 검증 필요)

### NV-1. E2E API 호출 검증

**범위**:
- `POST /api/advisory/005930/analyze` (국내)
- `POST /api/advisory/NVDA/analyze` (해외)
- `POST /api/advisory/215000/analyze` (적자 기업)
- `POST /api/portfolio-advisor/analyze` (포트폴리오)

**사유**: OPENAI_API_KEY 및 실제 시장 데이터 접속 필요. QA 환경에서 모의 실행 불가.

**대응**: 프로덕션 배포 전 수동 검증 필수 (Phase 3 완료 시점 통합 QA에서 수행).

### NV-2. GPT 응답 품질 수동 확인

**범위**:
- 포트폴리오 reasoning에 개별 종목 AI 리포트 인용 여부 (플랜 1-4 핵심 목표)
- System Prompt 7점 등급 규칙이 실제 응답에 반영되는지
- Value Trap 경고가 해당 조건에서 실제 발생하는지

**대응**: Phase 2 구현 직전 3종 샘플로 실증 검증 요구.

---

## 9. 자문 발송/수신 내역

| 에이전트 | 주제 | 상태 |
|---------|------|------|
| margin-analyst | 7점 등급 임계값 + 미계산 지표 처리 방식 (2점 vs 만점조정) | 대기 중 |
| macro-sentinel | 하이스테리시스 ±5/±0.05, previous_regime 역추적, 백분율 경계, defensive params | 대기 중 |
| **order-advisor** | 손절폭 System/User 충돌, 포트폴리오↔개별 우선순위 | **응답 도착 2026-04-17** |
| value-screener | Value Trap 5규칙 확장, 임계 "2개 이상", 배당 중단 처리 | 대기 중 |

### OrderAdvisor 응답 분석 (2026-04-17)

#### 응답 1: 손절폭 판정 — **BUG-1 FAIL 확인 → 수정 완료 ✓**
- **System Prompt(A=-8/B+=-10/B=-12)가 정확한 스펙**임을 공식 확인
- 근거: `.claude/agents/order-advisor.md:55` 원문 `stop_pct: A=8%, B+=10%, B=12%`
- `plans/buzzing-swinging-fern.md:357` "(-8/-10/-12%) + grade_factor(1.0/0.75/0.5)"
- GPT-4o 상충 프롬프트 실측 패턴 3가지(a=User 우선, b=System 우선, c=평균값) 모두 비결정적 — 수정 필수 확인
- "강한매수/매수/조건부" 라벨이 A/B+/B 7점 체계와 불일치 → 제거 필수 (DevArchitect 수정으로 완료 ✓)
- **Phase 2 권고 (JSON 스펙 확장)**: `등급팩터`, `최종포지션_pct`, `분할매수 배열` 필드 구조화 → **Phase 2-7 이월**

#### 응답 2: 포트폴리오 우선순위 (규칙 E/F/G) — **PASS**
Graham "Intelligent Investor" 교리 3가지(안전마진/분산/현금버퍼) 중 2번·3번은 포트폴리오 수준 판단이므로 "포트폴리오 > 개별 리포트" 우선순위는 **Graham 원칙에 부합**.

fundamental 악화 5가지 케이스 현행 규칙으로 이미 보호됨을 확인:

| 케이스 | 현행 규칙 처리 | 평가 |
|--------|--------------|------|
| Value Trap 경고 + 개별 매도 | 규칙 F-1 (매도 필수 승계) | ✓ |
| RSI>80 극단 과매수 + 개별 매도 | 규칙 F-2 (신규매수 금지) | ✓ |
| 할인율<0 (Graham 고평가) | 규칙 B (reduce/exit 우선) | ✓ |
| 리스크 2개 이상 | 규칙 D (priority=1 재검토) | ✓ |
| 등급 C/D | 규칙 G (신규편입 보류 + 우선 정리) | ✓ |

#### 응답 3: 규칙 F 구멍 지적 — **Phase 2 이월 (ISSUE-1)**
긴급 리스크 키워드 미처리:
- 분식회계/횡령/상장폐지/감사의견 거절/자본잠식/회계이상 등 **즉시 청산 사유**는 Value Trap(점진적 악화)과 다르게 처리 필요
- 현재 규칙 F는 이 케이스 누락
- OrderAdvisor 권고 F-3 신규 조항:
  ```
  3) `latest_report_risks`에 다음 키워드 포함 시 긴급도 immediate + 매도(exit) 필수 승계:
     "분식회계", "횡령", "상장폐지", "감사의견 거절/한정", "자본잠식", "회계이상"
     → 포트폴리오 집중도·체제와 무관하게 즉시 청산 권고
  ```
- 판정: Phase 1 범위 밖 → **Phase 2 이월 이슈로 트래킹**

---

## 9-1. Phase 2 이월 이슈

### ISSUE-1 [ADVISORY → Phase 2] portfolio_advisor 규칙 F-3 (긴급 리스크 키워드)

**출처**: OrderAdvisor 자문 응답 (2026-04-17)

**영향 범위**: `services/portfolio_advisor_service.py:368-370` `_build_system_prompt()` 규칙 F

**권고 조치**: Phase 2 또는 Phase 3 UI 작업과 함께 규칙 F-3 추가:
```python
# 현재 F (L368-370):
F. 개별 신호를 뒤집지 않는 예외 2건 (필수 승계):
   1) latest_report_risks에 "Value Trap"/"가치 함정" + 개별 AI "매도" → 매도(exit) 필수
   2) RSI>80 + 개별 AI 매도 시그널 → "신규 매수" 금지

# 추가 제안:
   3) latest_report_risks에 다음 키워드 포함 시 → immediate + exit 강제:
      "분식회계", "횡령", "상장폐지", "감사의견 거절/한정", "자본잠식", "회계이상"
      (포트폴리오 집중도·체제·가중등급과 무관하게 즉시 청산)
```

**근거**: Value Trap은 **점진적 악화**로 포트폴리오 최적화 맥락에서 재평가 가능하지만, 위 키워드는 **즉시 청산 사유**로 어떤 맥락 재평가도 부적절함.

**우선순위**: Phase 2 추가 권장 (portfolio System Prompt 확장 시 자연스럽게 포함 가능).

---

## 10. 최종 판정

### Phase 1 합격 여부

| 항목 | 기준 | 결과 |
|------|------|------|
| 경계면 정합성 | 3서비스 위임 + 시그니처 호환 | PASS |
| 예외 계층 | HTTPException 0건 | PASS |
| 도메인 로직 | 원문 에이전트 스펙과 1:1 일치 | PASS (손절폭 User Prompt 제외) |
| 하위 호환성 | 응답/DB/시그니처 변경 없음, v1 graceful | PASS |
| 프롬프트 품질 | 토큰 한도 내, 규칙 완비 | PASS (손절폭 일관성 결함) |

**조건부 합격**: BUG-1 (손절폭 System/User Prompt 충돌) 수정 후 Phase 2 진행.

### Phase 2 선행 조건

1. BUG-1 수정 완료 (DevArchitect)
2. 자문 응답 도착 시 스펙 조정 여부 판단
3. Phase 2 시작 시 `compute_grade_7point()`가 `_calc_safety_grade()` 로직과 정합성 유지 확인 (Phase 1의 System Prompt 7점 규칙과 동일한 임계값 사용 필요)

---

**작성자**: qa-inspector
**최종 갱신**: 2026-04-17
