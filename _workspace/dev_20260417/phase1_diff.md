# Phase 1 — 프롬프트 보강 + 개별↔포트폴리오 연계 (Diff 리포트)

**작성**: 2026-04-16 DevArchitect
**플랜**: `/Users/koscom/.claude/plans/buzzing-swinging-fern.md`
**QA 피드백 반영**: 2026-04-16 (QA Inspector MAJOR 1건 + MINOR 2건)

---

## QA 피드백 반영 내역 (2026-04-16)

### MAJOR 수정 — System Prompt vs User Prompt 손절폭 규칙 충돌 해소

**문제**: System Prompt는 `A=-8%/B+=-10%/B=-12%` (신규), User Prompt는 `"강한매수 -15%, 매수 -12%, 조건부 -10%"` (기존). GPT가 상반된 규칙을 동시에 받아 응답 손절가 값이 예측 불가능.

**수정** (`services/advisory_service.py:691-696`):
```python
# Before
"손절가": 진입가 대비 -10~-15% 정수,
"손절근거": "손절가 산정 근거 (등급별 차등: 강한매수 -15%, 매수 -12%, 조건부 -10%)",
"리스크보상비율": (익절가-진입가)/(진입가-손절가) 소수점1자리,
"분할매수제안": "1차 50%(현재) - 2차 30%(지지선-3%) - 3차 20%(전저점)"

# After
"손절가": System Prompt 7점등급 손절폭 규칙(A=-8%/B+=-10%/B=-12%)에 따른 정수,
"손절근거": "손절가 산정 근거 (System Prompt 7점등급 손절폭 규칙을 적용)",
"리스크보상비율": (익절가-진입가)/(진입가-손절가) 소수점1자리 (<2.0이면 매수 보류),
"분할매수제안": "1차 50%(진입가) - 2차 30%(1차-3%) - 3차 20%(1차-6%)"
```

User Prompt가 System Prompt를 참조하는 형태로 변경 → 규칙 단일 출처 확보. `risk_reward < 2.0` 보류 규칙과 분할매수 가격 공식도 User Prompt에 명시.

### MINOR 반영 — pipeline_service 하위호환 키 주석 명시

`services/pipeline_service.py:_determine_regime()` docstring에 key 매핑 의도 상세 기록:
- `margin_threshold ← margin` (스크리닝 할인율 임계값, `_generate_recommendations` L388에서 소비)
- `max_position ← single_cap` (종목당 한도, 현재 소비처 없음 — 향후 포지션 사이징 확장 대비)
- `max_invest ← stock_max` (총투자 한도, 동일)

### MINOR 유지 — advisory/portfolio_advisor 단순 래퍼

`_determine_regime()` 2줄 래퍼 유지. 호출부 시그니처(tuple 반환) 최소 변경 목적. QA 제안대로 제거해도 무방하지만 리스크 없음 → 현재 상태 유지.

### QA 합격 항목
- `macro_regime.py` 20셀 매트릭스 원문 1:1 일치
- 7점 등급 System Prompt ↔ `margin-analyst.md` 완전 일치
- Value Trap 5규칙 스펙 일치
- 3서비스 import 정상, FastAPI app 71 routes 기동 정상
- v1 리포트 graceful 처리 (`_extract_report_summary`) 테스트 통과
- 52주 고가 캐시 키 형식/TTL 정상

### 최종 프롬프트 길이 (QA 수정 반영 후)

| 항목 | 크기 |
|------|------|
| System Prompt (개별 종목) | 2792자 ≈ 698 토큰 |
| User Prompt (최소 입력) | 2062자 ≈ 516 토큰 |
| 총 입력 | ~4854자 ≈ 1213 토큰 |
| `max_completion_tokens=8000` 여유 | 6787 토큰 |

---

## 파일 변경 요약

| 파일 | +/- | 비고 |
|------|-----|------|
| `services/macro_regime.py` | **+223 신규** | 공용 체제 판단 모듈 (16셀 매트릭스 + VIX 오버라이드 + 하이스테리시스) |
| `services/pipeline_service.py` | -73 / +26 | 로컬 REGIME_MATRIX/PARAMS 제거, 공용 모듈 위임. 하위호환 params 키(margin_threshold/max_position/max_invest) 유지 |
| `services/advisory_service.py` | +90 | `_determine_regime()` 공용 위임 + System Prompt 강화 (7점등급표/체제매트릭스/손절폭/ValueTrap) + Forward Estimates 섹션 |
| `services/portfolio_advisor_service.py` | +118 | `_fetch_52w_high()` 6h 캐시, 각 holding에 `latest_report_*` 필드, `_build_system_prompt()` 개별 리포트 연계 규칙 |

---

## 1-1. 공용 체제 판단 (macro_regime.py) — 신규

### 핵심 기능
- `REGIME_MATRIX`: 버핏지수(low/normal/high/extreme) × 공포탐욕(extreme_fear/fear/neutral/greed/extreme_greed) = 20셀
- `REGIME_PARAMS`: 4체제별 margin/stock_max/cash_min/single_cap/per_max/pbr_max/roe_min
- `determine_regime(sentiment, previous_regime=None)` — VIX>35 오버라이드 + 하이스테리시스 ±5점(FG) / ±0.05(Buffett)

### 검증 결과
| 케이스 | 입력 | buffett_level / fg_level | regime |
|--------|------|--------------------------|--------|
| 저평+공포 | ratio=0.75, fg=25, vix=15 | low / fear | accumulation |
| 극고평+극탐욕 | ratio=1.7, fg=85, vix=20 | extreme / extreme_greed | defensive |
| VIX 오버라이드 | ratio=1.1, fg=70, vix=40 | normal / extreme_fear | selective |
| 백분율 변환 | ratio=235.2 | extreme (→ 2.352) | - |
| 하이스테리시스 | score=42, prev=cautious | fear→neutral 유지 | cautious |

---

## 1-2. 개별 종목 System Prompt 강화 (advisory_service.py)

### Before (이전)
```
【전략 1: 변동성 돌파】 ...
【전략 2: 안전마진】 할인율 >30%: 강한 매수, 10~30%: 매수, 0~10%: 중립, 음수: 고평가
【전략 3: 추세추종】 MA5>MA20>MA60 정배열 + MACD ...
【재무 건전성】 부채비율>200% 위험 ...
```

총 길이 약 1100자

### After (Phase 1)
```
【전략 1: 변동성 돌파】 ... (유지)
【전략 2: 안전마진】 ... (유지)
【전략 3: 추세추종】 ... (유지)

【7점 등급 체계 (MarginAnalyst, 28점 만점)】
| # | 지표           | 4점   | 3점      | 2점      | 1점   |
| 1 | Graham 할인율   | >40%  | 20-40%   | 0-20%    | <0%   |
| 2 | PER vs 5년평균  | <-30% | -30~-10% | -10~+10% | >+10% |
| 3 | PBR 절대값      | <0.7  | 0.7-1.0  | 1.0-1.5  | >1.5  |
| 4 | 부채비율        | <50%  | 50-100%  | 100-200% | >200% |
| 5 | 유동비율        | >2.0  | 1.5-2.0  | 1.0-1.5  | <1.0  |
| 6 | FCF 양수 연수   | 3년   | 2년      | 1년      | 0년   |
| 7 | 매출 CAGR(3년)  | >10%  | 5-10%    | 0-5%     | <0%   |
등급 컷오프: A=24-28점, B+=20-23, B=16-19, C=12-15, D=<12
PER/PBR 데이터 없는 지표는 2점(중립) 처리

【MacroSentinel 체제 매트릭스 요약】
버핏지수(low<0.8 / normal<1.2 / high<1.6 / extreme>=1.6)
× 공포탐욕(extreme_fear<20 / fear<40 / neutral<60 / greed<80 / extreme_greed>=80)
VIX > 35: 공포탐욕 무시하고 extreme_fear로 강제 오버라이드

【OrderAdvisor 등급별 손절폭 및 포지션】
- 손절폭: A=-8%, B+=-10%, B=-12%, C/D=진입 금지
- grade_factor: A=1.0, B+=0.75, B=0.50, C/D=0
- 분할매수: 1차 50% → 2차 30% → 3차 20%
- 익절가: Graham Number. risk_reward >= 2.0 아니면 매수 보류
- 지정가만 (시장가 금지)

【재무 건전성】 ... (유지)

【ValueScreener Value Trap 5규칙】
아래 5개 중 2개 이상 해당하면 '⚠ Value Trap 경고' 명시:
1. 매출 CAGR<0% 이면서 PER<5
2. 영업이익률 3년 연속 하락
3. FCF 3년 연속 음수
4. 부채비율 전년 대비 30%p 이상 급증
5. 배당 중단
```

총 길이 약 2541자 (1400자 증가 ≈ +500 토큰 상당)

---

## 1-3. Forward Estimates 섹션 (advisory_service.py)

### Before
User Prompt 섹션: 손익/대차/현금흐름/계량지표/기술시그널/변동성돌파/안전마진/추세추종/매크로

### After
위 섹션 + 신규 `## 포워드 가이던스` 섹션:
```
## 포워드 가이던스 (국내종목은 대부분 N/A)
- Forward PE: {forward_pe}
- Forward EPS: {forward_eps}
- 애널리스트 목표가(평균): {target_mean}
- 투자의견 점수(1=Strong Buy ~ 5=Strong Sell): {recommendation}
- 애널리스트 수: {num_analysts}
```

데이터 소스: `fetch_forward_estimates_yf()` — 기존 `_collect_fundamental_kr/us()` 에서 이미 수집 중. 국내는 전 필드 None → "N/A" graceful.

---

## 1-4. 포트폴리오 개별 리포트 연계 (portfolio_advisor_service.py)

### holding 엔트리 신규 필드
```python
{
    # ... 기존 필드 (name, code, market, quantity, avg_price, profit_rate, per, pbr, roe, high_52, drop_from_high 등)
    "latest_report_grade": None,              # v1 리포트는 None (Phase 3에서 v2 등급 저장 예정)
    "latest_report_summary": "180자 요약",    # v1 리포트의 종합투자의견.요약 (180자 절단)
    "latest_report_discount_rate": -7.1,      # v1 리포트의 전략별평가.안전마진.할인율
    "latest_report_risks": ["리스크1", ...],  # 상위 2개, 각 50자 절단
}
```

### 신규 헬퍼 함수
- `_extract_report_summary(report_data)` — v1 리포트 JSON 구조에서 4개 필드 파싱
- `_fetch_latest_report_summary(code, market)` — `advisory_store.get_latest_report()` 래퍼, 예외 안전

### System Prompt 추가 규칙 (A~E 5개)
- A. 개별 리포트와 상충 시 reasoning에 동의/반대 근거 명시
- B. `discount_rate < 0` 종목 → 비중 축소/매도 우선
- C. `discount_rate > 30` 종목 → 체제 허용 시 비중 확대 후보
- D. `risks` 2개 이상 → 해당 종목 priority=1 재검토
- E. **우선순위**: 포트폴리오 집중도/체제 현금비중 규칙이 개별 리포트보다 우선. 단, 상충 시 reasoning 명시 필수.

---

## 1-5. 52주 고가 캐시 (portfolio_advisor_service.py)

### Before
```python
def _fetch_52w_high(code, market):
    # 매번 외부 API 호출 (KR=fetch_market_metrics, US=yfinance fast_info)
```

### After
```python
def _fetch_52w_high(code, market):
    cache_key = f"advisor:52w:{market}:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached.get("value") if isinstance(cached, dict) else cached
    # ... API 호출 ...
    set_cached(cache_key, {"value": value}, ttl_hours=6)
```

- TTL: 6시간
- 키 포맷: `advisor:52w:{KR|US}:{code}`
- None 값도 캐싱(중복 호출 방지) — `{"value": None}` 형태로 래핑
- cache.py의 `_sanitize()`가 NaN 처리 보장

---

## 3종 샘플 프롬프트 길이 (토큰 한도 검증)

| 종목 | System Prompt | User Prompt | 합계 |
|------|--------------|-------------|------|
| 삼성전자 (005930, KR) | 2541자 | 2370자 | 4911자 ≈ 1500 토큰 |
| NVDA (US) | 2541자 | ~2400자 (추정) | ~4950자 |
| 골프존 (215000, 적자) | 2541자 | ~2400자 | ~4950자 |

`max_completion_tokens=8000` 한도 대비 **입력 프롬프트는 1500토큰 수준** — 응답 6500토큰 여유 확보. Phase 2에서 추가 섹션 투입 시에도 충분한 여유.

> 주: OpenAI 토큰 계산은 4자 ≈ 1토큰 근사치 기준. 한글은 더 많은 토큰을 소비하므로 실제 측정은 tiktoken 권장 (Phase 2 구현 시 검증).

---

## 하위 호환성 점검

### 응답 JSON 스키마
- **변경 없음** (Phase 1 원칙)
- 기존 필드: 종합투자의견/전략별평가/기술적시그널/포지션가이드/리스크요인/투자포인트 그대로

### DB 스키마
- **변경 없음** (Phase 1 원칙)

### 기존 함수 시그니처
- `advisory_service._determine_regime(sentiment) -> tuple[str, str]` — 유지
- `portfolio_advisor_service._determine_regime(sentiment) -> tuple[str, str]` — 유지
- `pipeline_service._determine_regime(sentiment) -> dict` — 유지 (params에 margin_threshold/max_position/max_invest 키 포함, 하위호환)

### v1 리포트 대응
- `_extract_report_summary()` — grade=None 허용, v1 JSON 구조에서 요약/할인율/리스크만 추출
- `latest_report_grade=None` 전달되면 GPT는 "리포트 없음"으로 처리

---

## 검증 체크리스트

- [x] 공용 모듈 단위 테스트 (5개 케이스, 매트릭스+오버라이드+하이스테리시스+백분율)
- [x] 3개 서비스 import 정상
- [x] 기존 함수 시그니처 (tuple/dict 반환) 호환성
- [x] System Prompt 길이 < 8000 토큰 (여유 6500토큰)
- [x] v1 리포트 grade=None graceful 처리
- [x] 52주 고가 캐시 키/TTL 설정
- [ ] E2E API 호출 검증 (수동 테스트 필요 — uvicorn 기동 + POST /api/advisory/005930/analyze, POST /api/portfolio-advisor/analyze)
- [ ] 포트폴리오 reasoning에 개별 리포트 인용 여부 (GPT 호출 필요)

---

## 도메인 자문 내역

| 자문 대상 | 질의 내용 | 상태 | 반영 |
|----------|----------|------|------|
| macro-sentinel | REGIME_MATRIX 16셀 + VIX>35 + 하이스테리시스 ±5 적정성 | 응답 대기 | 원문 스펙 기반 구현 |
| margin-analyst | 7점 등급 7지표 × 4점 임계값 + A/B+/B/C/D 경계 | 응답 대기 | 원문 스펙 기반 구현 |
| **order-advisor** | 등급별 손절폭 + grade_factor + 포트폴리오 상충 원칙 | **수신 완료** | **추가 반영** (아래) |
| value-screener | Value Trap 5규칙 + 경고 임계 "2개 이상" | 응답 대기 | 원문 스펙 기반 구현 |

### OrderAdvisor 응답 추가 반영 (Phase 1 재개정)

1. **손절폭/grade_factor 확정** — 기존 스펙 100% 일치, 변경 없음
   - A=-8%, B+=-10%, B=-12%, C/D 진입 금지
   - grade_factor A=1.0, B+=0.75, B=0.5, C/D=0

2. **advisory_service System Prompt 보강** (길이: 2541자 → 2792자)
   - `최종 포지션% = 체제 종목당 한도% × grade_factor` 계산식 삽입
   - **매수 불가 조건 6가지** 추가:
     a) 등급 B 미만 / b) 할인율 부족 / c) RSI>80 극단 과매수
     d) 미체결 중복 / e) 포지션 한도 초과 / f) Value Trap 경고

3. **portfolio_advisor_service System Prompt 보강** (+약 300자)
   - 규칙 E 강화 — 4대 제약(집중도/체제 현금비중/가중평균 등급/섹터 편중) 우선, 상충 시 reasoning 2가지 필수 (동의 근거 + 반대 근거 + 제약 유형)
   - **규칙 F 신규** — 개별 신호 뒤집기 금지 예외 2건:
     1) Value Trap + 개별 AI 매도 권고 → 매도 필수 승계
     2) RSI>80 + 기술 매도 시그널 → 신규 매수 금지 (기존 보유 유지 허용)
   - **규칙 G 신규** — 포트폴리오 가중 평균 등급 B 미만 또는 C/D 과반 → 신규 편입 전면 보류 + C/D 우선 정리 (체제 무관)

### 최종 프롬프트 길이 (자문 반영 후)

| 항목 | 크기 | 토큰(근사) |
|------|------|-----------|
| System Prompt (개별 종목) | 2792자 | ~698 |
| User Prompt (평균) | ~2300자 | ~575 |
| 총 입력 | ~5100자 | ~1290 |
| 한도(max_completion_tokens=8000) 여유 | — | 6710 |

> 에이전트 원문 스펙(`.claude/agents/*.md`)과 1:1 대조 검증 완료. OrderAdvisor 응답은 원문 스펙과 완전 일치하며, 추가 **포지션 계산식/매수 불가 조건/상충 예외 2건/B미만 전면 보류**가 새로 반영됨.
