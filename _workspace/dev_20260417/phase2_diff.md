# Phase 2 — 데이터 보강 + 정량 필드 (Diff 리포트)

**작성**: 2026-04-17 DevArchitect

---

## 파일 변경 요약

| 파일 | 상태 | 비고 |
|------|------|------|
| `stock/indicators.py` | 수정 | volume_signal/volume_5d_avg/volume_20d_avg/bb_position 추가 (2-1) |
| `stock/advisory_fetcher.py` | 수정 | `fetch_valuation_stats()` 신규 (2-2) |
| `stock/yf_client.py` | 수정 | `fetch_quarterly_financials_yf()` 신규 (2-3) |
| `stock/dart_fin.py` | 수정 | `fetch_quarterly_financials()` 신규 (2-3) |
| `services/safety_grade.py` | **신규** | 7점등급/복합점수/체제정합성/포지션사이징 공유 모듈 (2-4) |
| `services/advisory_service.py` | 수정 | 데이터수집 병합(2-5) + User Prompt 4섹션(2-6) + JSON v2 스키마(2-7) |
| `services/portfolio_advisor_service.py` | 수정 | 가중 등급 집계(2-8) + 체제 정합성 주입 |
| `services/pipeline_service.py` | 수정 | `_calc_safety_grade()` → safety_grade 모듈 위임 |

---

## Phase 2 구현 상세

### 2-1 기술 지표 확장 (indicators.py)
- `current_signals` 신규 키: `volume_signal`, `volume_5d_avg`, `volume_20d_avg`, `bb_position`
- volume_signal = 최신 거래량 / 직전 5봉 평균 (배수)
- bb_position = (close - BB_lower) / (BB_upper - BB_lower) × 100 (0~100)

### 2-2 PER/PBR 5년 통계 (advisory_fetcher.py)
- `fetch_valuation_stats(code, market)` → 평균/최대/최소/현재/편차%
- 내부: `fetch_valuation_history_yf(code, years=5)` 재사용
- 캐시: `valuation_stats:{market}:{code}` 24h TTL

### 2-3 분기 실적
- **DART** `fetch_quarterly_financials(stock_code, quarters=4)`:
  - reprt_code 4종 (11013/11012/11014/11011) 누계 → 개별 분기 환산
  - Q2 = 반기 - Q1, Q3 = 3분기누계 - 반기, Q4 = 연간 - 3분기누계
  - 캐시: `dart:quarterly:{code}:{quarters}` 7일 TTL
- **yfinance** `fetch_quarterly_financials_yf(code, quarters=4)`:
  - `Ticker.quarterly_financials` 파싱 → 매출/영업이익/순이익/마진

### 2-4 7점 등급 공유 모듈 (safety_grade.py, 신규)
- `compute_grade_7point()` — margin-analyst.md 7지표×4점 임계값 100% 일치
- `compute_composite_score()` — ValueScreener 공식 정확 반영
- `compute_regime_alignment()` — 등급 정합(40%) + FCF(30%) + 주식비중(30%)
- `compute_position_size()` — OrderAdvisor 가이드 반영 (grade_factor × 체제 한도)
- `compute_stop_loss()` — A=-8%, B+=-10%, B=-12%, C/D=None
- `compute_risk_reward()` — (target-entry)/(entry-stop)
- `GRADE_FACTOR`, `GRADE_STOP_LOSS_PCT` 상수 export
- `valid_entry: bool` 필드 (C/D → False)
- pipeline_service._calc_safety_grade() → 내부 safety_grade.compute_grade_7point() 위임

### 2-5 데이터 수집 병합 (advisory_service.py)
- KR: ThreadPoolExecutor 5→7 workers, `f_val_stats`/`f_quarterly` 추가
- US: ThreadPoolExecutor 6→8 workers, 동일
- fundamental에 `valuation_stats`, `quarterly` 필드 추가

### 2-6 User Prompt 추가 섹션 4개
1. `## PER/PBR 5년 히스토리 비교` — 현재/평균/범위/편차%
2. `## 분기 실적 추세 (최근 4분기)` — 매출/영업이익/순이익/마진
3. `## 거래량·변동성 신호` — volume_signal, bb_position
4. `## 7점 등급 사전 계산값` — 사전 계산 등급/세부/복합/정합성 + "단순 복사 금지" 지침

### 2-7 응답 JSON v2 스키마
신규 필수 필드:
- `schema_version: "v2"`
- `종목등급: "A"/"B+"/"B"/"C"/"D"`
- `등급점수: 0~28`
- `복합점수: 0~100`
- `체제정합성점수: 0~100`
- `Value_Trap_경고: bool`
- `Value_Trap_근거: [str]`
- `포지션가이드.등급팩터: float`
- `포지션가이드.recommendation: "ENTER"/"HOLD"/"SKIP"`

기존 필드 모두 유지 (종합투자의견/전략별평가/기술적시그널/포지션가이드/리스크요인/투자포인트).

### 2-8 포트폴리오 가중 등급 집계
- `_build_context()` 반환에 `portfolio_grade_weighted_avg`, `grade_distribution`, `stock_total_pct`, `regime_alignment_score` 추가
- `analyze_portfolio()`에서 체제 결정 후 `compute_regime_alignment()` 호출하여 주입
- v1 리포트(grade=None)에서는 `portfolio_grade_weighted_avg=None`, 모두 "unknown" — graceful

---

## 검증 결과

### 단위 테스트 통과
- indicators.py: bb_position=91.2, volume_signal=1.1 (40봉 테스트)
- safety_grade.py: A등급 28/28, D등급 8/28, composite=58, regime_alignment=80
- position_size: B+/selective → 30주(3M/10만), C → 0주 SKIP
- stop_loss: B+ → 90000(-10%), risk_reward → 3.0

### 프롬프트 길이 (최종)
| 항목 | 크기 |
|------|------|
| System Prompt | 2792자 ≈ 698 토큰 |
| User Prompt (삼성전자 v2) | 3623자 ≈ 906 토큰 |
| 총 입력 | 6415자 ≈ 1603 토큰 |
| max_completion_tokens=8000 여유 | 6397 토큰 |

Phase 1 대비 User Prompt +1200자 증가 (4섹션 추가). 여전히 충분한 여유.

### 하위 호환
- DB 스키마 변경 없음 (Phase 3 범위)
- v1 리포트 JSON에 v2 필드 없어도 기존 UI 정상
- 기존 API 응답 구조 호환 (신규 필드는 추가만)

---

## 도메인 자문

| 자문 대상 | 질의 | 상태 |
|----------|------|------|
| MarginAnalyst | 해외 매출 CAGR USD vs KRW 기준 | 전송됨 (가설 A=USD 기준 적용) |
| OrderAdvisor | Phase 2 사전 가이드 | **수신+반영 완료** (safety_grade.py에 반영) |
