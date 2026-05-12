# Phase 2 QA 리포트 — 데이터 보강 + 정량 필드

**작성**: 2026-04-17 qa-inspector
**대상**: Phase 2 구현 (DevArchitect)
**플랜**: Phase 2 (2-1~2-9)

---

## 결과 요약

| 구분 | 건수 | 비고 |
|------|------|------|
| PASS | 14 | 공식정확/임계값일관/v2필드/graceful/예외계층 |
| MAJOR 버그 | 0 | 없음 |
| MINOR 관찰 | 1 | 경계값 strict < 해석 (좌폐우개, 실무 영향 미미) |
| 미검증 | 2 | E2E API + GPT 실응답 (Phase 3 통합 QA 이월) |

**최종 판정**: **Phase 2 QA 통과 — Phase 3 진행 가능**.

---

## 1. 공식 정확성 검증

### 1-1. `compute_grade_7point()` — margin-analyst.md 1:1 대조 (PASS)

| # | 지표 | 원문 4/3/2/1점 | 코드 구현 | 일치 |
|---|------|---------------|----------|------|
| 1 | Graham 할인율 | >40/20-40/0-20/<0 | `>40→4, >20→3, >0→2, else→1` | ✓ |
| 2 | PER vs 5년평균 | <-30/-30~-10/-10~+10/>+10 | `<-30→4, <-10→3, <10→2, else→1` | ✓ |
| 3 | PBR 절대 | <0.7/0.7-1.0/1.0-1.5/>1.5 | `<0.7→4, <1.0→3, <1.5→2, else→1` | ✓ |
| 4 | 부채비율 | <50/50-100/100-200/>200 | `<50→4, <100→3, <200→2, else→1` | ✓ |
| 5 | 유동비율 | >2.0/1.5-2.0/1.0-1.5/<1.0 | `>2.0→4, >1.5→3, >1.0→2, else→1` + %→배수 자동변환 | ✓ |
| 6 | FCF 양수연수 | 3/2/1/0 | `≥3→4, ≥2→3, ≥1→2, else→1` | ✓ |
| 7 | 매출 CAGR | >10/5-10/0-5/<0 | `>10→4, >5→3, >0→2, else→1` | ✓ |

**등급 컷오프**: A≥24, B+≥20, B≥16, C≥12, D<12 ✓
**데이터 없는 지표**: 2점 중립 (Graham 할인율은 1점, FCF 0년도 1점) ✓
**유동비율 % vs 배수**: `>10이면 /100 변환` — 실무에서 150(%)과 1.5(배수) 모두 정확 처리 ✓

**스모크 테스트 결과**:
- 전지표 최고점: score=28, grade=A ✓
- 전지표 None: score=12 (1+2+2+2+2+1+2), grade=C ✓
- 가상 삼성전자(PER=12,PBR=1.3,부채80%,유동1.5,FCF3년,CAGR8%,할인25%): score=20, grade=B+ ✓

### 1-2. `compute_composite_score()` — value-screener.md 대조 (PASS)

**공식**: `(1/PER×0.3 + 1/PBR×0.3 + ROE/100×0.25 + dividend_yield/100×0.15) × 100`

검증: PER=10, PBR=1.0, ROE=15, DY=3.0
- 수동 계산: (0.1×0.3 + 1.0×0.3 + 0.15×0.25 + 0.03×0.15) × 100 = 37.2
- 코드 결과: 37.2 ✓

PER/PBR None → 해당 항목 0점 처리, 전체 점수는 정상 계산 ✓
배당수익률 %(3.5) vs 소수(0.035) 자동 판별 (`>1이면 %`) ✓
범위: `min(max(score, 0), 100)` → 0~100 보장 ✓

### 1-3. `compute_regime_alignment()` — 정합성 로직 (PASS)

- accumulation + A(26점) + FCF3년 → 100.0 (최고)
- defensive + D(8점) + FCF0년 → 최저 (정상)
- 주식비중 파라미터 없으면 등급+FCF 2항목 가중(50/50)
- 주식비중 제공 시 3항목 가중(40/30/30)
- 범위 0~100 보장 ✓

### 1-4. OrderAdvisor 상수 대조 (PASS)

| 상수 | order-advisor.md 원문 | 코드 | 일치 |
|------|---------------------|------|------|
| GRADE_FACTOR | A=1.0/B+=0.75/B=0.5/C·D=0 | `{"A":1.0,"B+":0.75,"B":0.5,"C":0.0,"D":0.0}` | ✓ |
| GRADE_STOP_LOSS_PCT | A=8%/B+=10%/B=12%/C·D=진입금지 | `{"A":0.08,"B+":0.10,"B":0.12,"C":None,"D":None}` | ✓ |

`compute_stop_loss(A,10000)=9200`, `(B+,10000)=9000`, `(B,10000)=8800`, `(C,10000)=None` ✓
`compute_risk_reward(10000,9200,13000)=3.75` ✓, `(entry==stop)=None` ✓
`compute_position_size(B+, 4%, 1억, 3000만, 56000) → qty=53, pct=3.0%, ENTER` ✓

---

## 2. Phase 1↔Phase 2 임계값 일관성 검증 (PASS)

Phase 1 `_build_system_prompt()`의 7점 등급 규칙(문자열) vs Phase 2 `compute_grade_7point()`(파이썬 함수)의 임계값 자동 대조 결과:

- 7개 지표 × 4점 임계값 12개 문자열: 모두 System Prompt에 존재 ✓
- 5개 등급 컷오프 (A=24-28 ~ D=<12): 모두 일치 ✓
- 3개 손절폭 (A=-8% ~ B=-12%): 모두 일치 ✓
- v2 JSON 필수 필드 9개: 모두 User Prompt에 존재 ✓
- 사전계산 단순 복사 금지 지침: 존재 ✓

---

## 3. v2 응답 JSON 스키마 완결성 (PASS)

| 필드 | 타입/범위 | User Prompt 존재 | 비고 |
|------|----------|----------------|------|
| `schema_version` | `"v2"` | ✓ | |
| `종목등급` | A/B+/B/C/D | ✓ | "사전 계산값 참고" 명시 |
| `등급점수` | 0-28 정수 | ✓ | |
| `복합점수` | 0-100 실수 | ✓ | |
| `체제정합성점수` | 0-100 실수 | ✓ | |
| `Value_Trap_경고` | true/false | ✓ | "5규칙 중 2개 이상" |
| `Value_Trap_근거` | string[] | ✓ | "경고=false면 빈 배열" |
| `포지션가이드.등급팩터` | 0~1.0 | ✓ | A=1.0/B+=0.75/B=0.5/C·D=0 |
| `포지션가이드.recommendation` | ENTER/HOLD/SKIP | ✓ | C·D/VT/R:R<2.0 → SKIP |

기존 v1 필드(종합투자의견/전략별평가/기술적시그널/포지션가이드/리스크요인/투자포인트) 모두 유지 ✓.
신규 기술적시그널 세부(`volume`, `bb`): 포함 ✓.

---

## 4. 예외 계층 준수 (PASS)

변경 파일 5개에서 `HTTPException` 검색: **0건** ✓
- `services/safety_grade.py`: 예외 raise 없음 (순수 계산 함수)
- `stock/indicators.py`, `stock/advisory_fetcher.py`, `stock/dart_fin.py`, `stock/yf_client.py`: HTTPException 없음

---

## 5. 하위 호환성 검증 (PASS)

| 항목 | 결과 |
|------|------|
| DB 스키마 변경 없음 | ✓ (Phase 3 범위) |
| `pipeline_service._calc_safety_grade()` 시그니처 유지 | ✓ (내부에서 safety_grade 위임) |
| v1 리포트 grade=None 시 `portfolio_grade_weighted_avg=None` | ✓ (graded_weight_sum=0 → None) |
| v1 리포트 `grade_distribution["unknown"]` 카운트 | ✓ (1건 이상) |
| `indicators.calc_technical_indicators()` 기존 키 보존 | ✓ (volume_signal/bb_position 추가만) |
| `main.py` 임포트 정상 (71 routes) | ✓ |

---

## 6. 포트폴리오 가중 등급 (Phase 2-8) 검증 (PASS)

**GRADE_SCORE_MAP**: `{"A":26, "B+":21.5, "B":17.5, "C":13.5, "D":8.0}` — 등급 구간 중심값으로 가중 평균 계산. 합리적 설계.

**가중 평균 계산 공식**: `Σ(weight_pct × GRADE_SCORE_MAP[grade]) / Σ(weight_pct) for graded holdings only`
- v2 리포트 없는(grade=None) 종목은 제외 → `graded_weight_sum=0`이면 `None` ✓
- `grade_distribution` 딕셔너리 정상 카운트 ✓

**체제 정합성**: `_build_context()`에서 `regime_alignment_score=None`으로 초기화 → `analyze_portfolio()`에서 체제 결정 후 `compute_regime_alignment()` 호출하여 주입 ✓

---

## 7. 데이터 수집 병합 (Phase 2-5) 검증 (PASS)

`_collect_fundamental_kr()`:
- `pool.submit(advisory_fetcher.fetch_valuation_stats, code, "KR")` ✓
- `pool.submit(dart_fin.fetch_quarterly_financials, code, 4)` ✓
- 반환 dict에 `valuation_stats`/`quarterly` 키 추가 ✓

`_collect_fundamental_us()`:
- `pool.submit(advisory_fetcher.fetch_valuation_stats, code, "US")` ✓
- `pool.submit(fetch_quarterly_financials_yf, code, 4)` ✓
- 반환 dict에 `valuation_stats`/`quarterly` 키 추가 ✓

**graceful degrade**: `fetch_valuation_stats()` 실패 시 빈 dict 반환, `fetch_quarterly_financials()` 실패 시 빈 list 반환 → 전체 수집 중단 없음.

---

## 8. 기술 지표 확장 (Phase 2-1) 검증 (PASS)

`calc_technical_indicators()` 반환 `current_signals`에 신규 키:
- `volume_signal`: 최신 거래량 / 직전 5봉 평균 (배수)
- `volume_5d_avg`, `volume_20d_avg`
- `bb_position`: `(close - bb_lower) / (bb_upper - bb_lower) × 100` (0~100)

기존 키 (`macd_cross`, `rsi_value`, `above_ma20` 등) 보존 확인 ✓.

---

## 9. 분기 실적 (Phase 2-3) 검증 (PASS)

**DART 분기 환산 공식** (`stock/dart_fin.py:794-809`):
- Q1 = 11013 thstrm (Q1 직접)
- Q2 = 반기(11012) - Q1
- Q3 = 3분기누계(11014) - 반기
- Q4 = 연간(11011) - 3분기누계

직전 누계 없으면 당기 값 그대로 사용(Q1 또는 graceful) ✓.
마진 계산: `oi_margin = oi / rev * 100`, `net_margin = ni / rev * 100` (rev=0이면 None) ✓.
캐시: `dart:quarterly:{code}:{quarters}` TTL 7일 ✓.
미공시 분기 건너뜀(graceful) ✓.

---

## 10. 관찰 사항

### OBS-1 [MINOR] 경계값 strict < 해석

모든 점수 함수가 **strict inequality**(`<`, `>`)를 사용합니다. 예를 들어:
- Graham 할인율 정확히 40.0% → 3점 (>40이 아니므로)
- PER 편차 정확히 -30.0% → 3점 (<-30이 아니므로)
- 유동비율 정확히 2.0 → 3점 (>2.0이 아니므로)

이는 margin-analyst.md 원문의 표기 `<-30% | -30~-10% | ...`와 좌폐우개(left-closed, right-open) 해석으로 일관됩니다. 실무 영향은 경계 정확히 1점 차이뿐이며 등급 경계를 넘기는 경우도 극히 드뭅니다.

**판정**: 허용 (일관적 해석).

---

## 11. 프롬프트 품질

| 항목 | 값 |
|------|-----|
| System Prompt | 2792자 (~930 토큰) |
| User Prompt (빈 데이터) | 3358자 (~1120 토큰) |
| 합계 | 6150자 (~2050 토큰) |
| max_completion_tokens=8000 대비 여유 | ~5950 토큰 |

Phase 1 대비 User Prompt +1300자 증가 (4섹션 추가: PER/PBR 5년, 분기실적, 거래량/BB, 7점사전계산). 한도 대비 여유 충분.

**사전계산 → GPT 독립판단 지침**: "위는 데이터 기반 사전 계산이며, GPT는 추세·매크로·기술시그널을 종합해 최종 등급을 부여할 것. 사전 계산을 단순 복사하지 말고, 독립적 판단을 내리되 불일치 시 reasoning에 근거 명시." ✓

---

## 12. 최종 판정

| 항목 | 기준 | 결과 |
|------|------|------|
| 공식 정확성 | margin-analyst/value-screener/order-advisor 1:1 일치 | PASS |
| 임계값 일관성 | Phase 1 System Prompt = Phase 2 코드 | PASS |
| v2 JSON 필드 완결성 | 9개 필수 필드 + 기존 유지 | PASS |
| 예외 계층 | HTTPException 0건 | PASS |
| 하위 호환성 | DB/시그니처/v1 graceful | PASS |
| 포트폴리오 가중 등급 | v1 only → None, grade_distribution 정상 | PASS |
| 프롬프트 품질 | 토큰 한도 여유, 단순복사 금지 지침 | PASS |

**Phase 2 QA 통과 — Phase 3 진행 가능**.

---

**작성자**: qa-inspector
**최종 갱신**: 2026-04-17
