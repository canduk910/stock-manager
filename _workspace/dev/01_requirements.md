# 기능 요건서: 외국인 보유율 추이 기간 확장 (V1.6 — V2 후속 #4 발진)

## 개요

사용자 요청: 「소진율 추이 30일이 최대야? 반년정도 보고 싶은데.」

직전 V1.5(`_workspace/dev_20260515_foreign_holding/`)는 KIS `FHKST01010400`(주식현재가 일자별) 최근 30거래일 한도 내에서 외국인 보유율 추이 카드(`ForeignHoldingCard`)를 도입했다. 본 요건은 V2 후속 메모 #4의 **"30일 초과 누적 추세: macro_store 일자별 append 패턴으로 90일/180일 누적"** 항목을 발진시킨다.

**범위**:
- 종목 상세 페이지(`SupplyDemandPanel` → `ForeignHoldingCard`) 기간 확장. 기존 V1.5 카드 위에 **데이터 수집/누적 + 슬라이더 범위만** 변경.
- KIS API는 30일 한도 그대로 사용. 누적은 일별 백필 cron + 영속 저장으로 실현.
- 사용자 요구 "반년" → 기본 120거래일 / 슬라이더 30~180일 step 30.

**V2.1 이후 분리 항목** (본 요건 범위 외):
- 매크로 페이지 시장 단위 외국인 보유 비중 누적 (V2 후속 #1)
- 외국인 보유율 ±2%p 알림 (V2 후속 #2)
- 매크로 체제 결합 경고 (V2 후속 #3)
- 스크리너 필터 노출 (V2 후속 #5)
- 일관성 검증 텔레메트리 (V2 후속 #6)
- 활성 종목 자동 확장(advisory_stocks 전체 cron 대상화)

---

## 컨텍스트 — KIS TR 재검증 결과 (2026-05-15 도메인팀장 직접 확인)

### 1. 외국인 소진율 일별 장기 시계열 TR — **미존재 재확인**

검색 전략(LLM 카탈로그 + docs/kis/ grep 병행):

| 검색 키 | 결과 |
|--------|------|
| `mcp__kis-code-assistant-mcp__search_domestic_stock_api(description="외국인 보유 추이 일별 시계열")` | 0건 |
| `function_name="foreign"` | 1건 — `foreign_institution_total`(매매종목 가집계, 외국인 보유율 시계열 X) |
| `response="외국인 보유"` | 156건 전수 검토 — `hts_frgn_ehrt` 일자별 array를 제공하는 TR 없음 |
| `function_name="investor_trend_estimate"` | 1건 — `종목별 외인기관 추정가집계`(추정치, 현재값만) |
| `function_name="frgnmem_pchs_trend"` | 1건 — `종목별 외국계 순매수추이`(외국계 회원사 단위, 보유율 없음) |
| `function_name="inquire_daily_itemchartprice"` (FHKST03010100) | 일자/기간 지정 + 100건/회 가능. **단 output2(일자별 array) COLUMN_MAPPING에 `hts_frgn_ehrt` 부재** — chk 예제 검증 |
| `function_name="investor_trade_by_stock_daily"` (FHPTJ04160001, V1 사용) | 일자별 array에 `frgn_ntby_qty`만 존재, `hts_frgn_ehrt` 부재 (docs/kis/07 chk COLUMN_MAPPING 검증) |

### 2. KIS TR 재검증 결론

**외국인 소진율(`hts_frgn_ehrt`)을 일자별 array로 30일 초과 제공하는 KIS TR은 존재하지 않는다.**

- `FHKST01010400`(주식현재가 일자별) output2: 일별 `hts_frgn_ehrt` 제공, **30거래일 한도**
- `FHKST01010100`(주식현재가 시세) output: 스냅샷 `hts_frgn_ehrt` 단일값
- 그 외 TR: 외국인 순매수 수량(`frgn_ntby_qty`)은 시계열로 제공되나 **소진율(%) 형태 시계열은 미제공**

### 3. 우회 경로 후보 평가

| 경로 | 신뢰도 | 비용 | 채택 여부 |
|------|--------|------|-----------|
| (a) Lazy 백필 — 첫 진입 30일 즉시 + 매일 cron으로 새 일자만 append, N일 후 자연 누적 | ★★★★★ (KIS 공식 값) | cron 1회/일 | **채택** |
| (b) 사용자 안내 — "데이터 누적 중" 안내, 신규 사용자 N일 대기 | ★★★★★ | UI 메시지만 | 부속 적용 |
| (c) pykrx 외국인 매매 폴백 | ★★ — KRX 서버 로그인 필수(2026-02~), market.py가 pykrx→yfinance 전환 사유와 동일 | 불안정 | 미채택 |
| (d) 순매수 누적 역산 — `FHKST01010400` `frgn_ntby_qty` 30일 + 시계열 역산 | ★★★ — MarginAnalyst 자문 ±5% 노이즈 허용(외국인 등록/비등록 변환, 펀드 자체 거래) | 정확도 손실 | 미채택(V1.5에서 일별 보유수량은 이미 `한도수량×소진율`로 역산 — 동일 식 재사용) |

→ **(a) Lazy 백필 + (b) UI 안내** 조합 채택. (d)는 백필 폴백 검토 시 V2.1에 후속.

---

## 도메인 자문 합의 (3인 토론 결과)

### MacroSentinel 자문 결론

- **기간 확장 정당성**: 외국인 보유율은 매크로 수급 보조 지표(체제 판단 직접 입력 금지 — V1.5 결론 유지). 반년 추세는 매크로 페이지의 OAS 6개월 모멘텀과 동일한 정밀도. 사용자 가시화 목적에 정합.
- **슬라이더 권장값**: 30/60/90/120/180일 step 30 (5단계 stepper). **기본 120일** — 사용자 요구 "반년"이 약 120거래일(5×26주)이며 정확.
  - 슬라이더 30~180 step 10 안(ii)은 일일 cron 정상 누적 전 N일(180일)간 빈 차트가 노출되므로 stepper(i) 채택.
- **x축 포맷 조정**: 30일 = MM-DD / 60~180일 = MM-DD + 격주 라벨(`interval` 자동) / 툴팁은 YYYY-MM-DD 일관(`makeTooltipFormatter` 재사용)
- **임계값 4단계 ReferenceLine 유지** (50/80/95) — V1.5와 동일 색상/위치.
- **신호 보조 텍스트 강화**:
  - 30일: "30일 변화: 53.85% → 54.00% (+0.15%p)" 단순
  - 60일+: "120일 변화: 50.20% → 54.00% (+3.80%p)" + **±3.0%p 이상 시 보조 경고 텍스트** (참고용 — 매매 신호 아님, OrderAdvisor 안전 정책)
    - "최근 120일간 외국인 보유율 +3.8%p 급증 (정상 범위 ±2%p)" 노란 작은 텍스트
- **체제 결합은 V2.1 후속** (본 요건 미포함). 이유: V2 후속 #3과의 통합 검토는 슬라이더 확장 자체와 분리되어야 우선순위 명확.
- **휴장일 처리**: x축에 거래일만 표시 (`dot={false}` + 일자 array 그대로). 빈 일자 보간 X.

### MarginAnalyst 자문 결론 (Graham 원칙)

- **누적 데이터 모델 권장**: **(가) macro_store list append** 채택.
  - 이유 1: V1.5 캐시 패턴(`foreign_holding:snapshot:{code}` / `foreign_holding:daily:{code}`) 일관성 — 기존 영속 캐시가 이미 list[dict]를 KST 일자 키로 저장. append 패턴 자연 확장.
  - 이유 2: 마이그레이션 비용 0 (별도 SQLAlchemy 테이블 도입 시 Alembic + 모델 + Repository 3중 변경 vs macro_store 키 추가만으로 가능).
  - 이유 3: 동시성 — single-row JSON append이므로 race condition은 일자 단위 last-write-wins (cron + 사용자 진입 충돌 가능성 낮음, sync 보호 필요 시 `_REFRESH_LOCKS` 패턴 차용).
- **별도 테이블(나) 채택 시점**: 활성 종목 200개 이상으로 cron 부하 증가 + 사용자별 격리 필요 시점 (V2.1 이후, 본 요건 범위 외).
- **신규 상장/거래정지 처리**:
  - 신규 상장 종목 — 첫 진입 시 KIS 응답이 7일 등 짧음 → daily 배열 그대로 저장 (V1.5와 동일).
  - 거래정지 — KIS는 정지일을 응답에서 누락 → daily 배열 빈 일자 둠. UI는 `dot={false}` + 라인 연결(거래일만 표시이므로 시각적 단절 없음).
- **데이터 무결성 가드 (V1.5 `_is_defective_fh_daily` 확장)**:
  - 누적 저장 시 새 row의 `hts_frgn_ehrt`가 None이면 append 거부(영속 결함 데이터 차단).
  - 누적 데이터에서 동일 일자가 2개 이상이면 마지막 1개만 유지(dedup by date).
  - 누적 보존 기간 상한: **최대 250거래일(약 1년)** — 슬라이더 180일을 안전하게 커버하면서 무한 누적 방지.
- **양면성 advisory_note 유지** — V1.5 문구 변경 없음. 6개월 추세 보더라도 "한도 포화 ≠ 매수 강도 강함" 원칙 동일.
- **등급(SafetyGrade) 미편입** — V1.5 결론 유지. 외국인 보유율은 가치 지표가 아니며 표시 전용.

### OrderAdvisor 자문 결론

- **백필 cron 안전 정책**:
  - 자동 매수/매도 트리거 절대 금지 (V1.5와 동일). cron은 데이터 수집 전용.
  - cron 실패 시 logger.error만 기록, `raise` 금지 (다른 lifespan 작업 보호).
  - **활성 종목 정의(MVP 좁힘)**: V2 후속 #4 정의는 "advisory_stocks + watchlist"였으나 OrderAdvisor 안전 제약상 본 요건은 **`advisory_stocks` 전체 + watchlist 등록된 국내 종목만**으로 시작 (분당 호출 부하 가시화). 추후 부하 데이터 기반 확장.
  - **부하 추정**: 국내 종목당 2회 KIS 호출(snapshot 1 + daily 1). KIS rate limit(초당 2회 안정선). 활성 종목 N개 × 2회 / 2 = N초 소요. N=50 종목 = 50초, N=200 종목 = 200초. 매일 1회 cron이므로 부하 수용 가능.
  - **휴장일 cron skip**: KIS `chk_holiday` TR(`docs/kis/05_KR_SECTOR_ETC.md`)로 휴장일 사전 확인. 토/일 + 공휴일은 cron 본문 진입부에서 즉시 return. 실패 시 KST 토/일 단순 스킵(공휴일은 catch-up 다음 영업일).
  - **cron 시각**: KST **18:00** (장 마감 15:30 + 데이터 확정 30분 여유 + KIS 야간 부하 회피). MacroSentinel cron(00:05)과 시간대 충돌 없음.
- **누적 데이터 백필 안전**:
  - 첫 진입 종목 — 즉시 KIS 30일 fetch + 응답 저장. 사용자는 30일 차트 즉시 노출.
  - 슬라이더 180일 선택 + 누적 데이터 60일밖에 없음 → UI 안내 "데이터 누적 중 (60일 / 180일), 매일 자동 채워집니다". 빈 일자 보간 X.
  - 누적 데이터 N일 + KIS 신규 30일 머지 시 dedup(`date` 키) — `_merge_fh_daily()` 헬퍼.
- **잔여 매수여력 시계열**:
  - daily의 `frgn_hldn_man_estimated`(역산 보유수량)는 V1.5 식 그대로(`한도수량 × 일별 소진율 / 100`). 장기 누적이라도 식 변경 없음.
  - 한도수량은 **스냅샷 단일값** 모델 유지 (V1.5 합의). 한도 수량은 거의 변하지 않음(유상증자/액면분할 시점만). 일자별 한도 추적은 V2.1 후속.
- **응답에 매매 액션 키 금지** 검증 테스트 유지 (V1.5와 동일 — `recommendation`/`action`/`buy_signal`/`signal` 4개 키 부재).
- **MacroSentinel 보조 경고 텍스트(±3%p 급변)**는 텍스트 표시만, 응답 JSON에 별도 매매 액션 키 없이 차트 메타로만 노출. 응답 키 `change_alert: {abs_change_pct: 3.8, threshold: 3.0, breached: true, color: "warning"}` 단일 객체 추가.

### 전문가 간 합의 (3인 일치)

| 항목 | 합의 |
|------|------|
| 누적 데이터 모델 | (가) macro_store list append + 누적 키 신설 `foreign_holding:daily_history:{code}` |
| 백필 전략 | (a) Lazy + 일별 cron (b) UI 누적 안내 병행 |
| cron 시각 | KST 18:00 평일(주말/공휴일 skip) |
| 활성 종목 정의 | advisory_stocks 전체 + watchlist 등록 국내 종목 (분당 부하 가시화 후 V2.1 확장) |
| 누적 보존 상한 | 최대 250거래일 |
| 슬라이더 | 30/60/90/120/180 stepper, 기본 120 |
| 매매 액션 키 | 부재 검증 유지 |
| 임계값 색상 | 4단계 ReferenceLine 유지 (50/80/95) |
| advisory_note | V1.5 문구 변경 없음 |
| 음수 보호 / 한도 초과 | V1.5 정책 유지 |

### 합의 불일치 → 부서장 결정 요청 (3건)

1. **MVP cron 활성 종목 범위**
   - (A) **권장**: advisory_stocks 전체 + watchlist 국내 종목 (가장 자주 본 종목 우선)
   - (B) advisory_stocks 전체만 (워치리스트 제외 — 부하 더 낮음, 사용자 가치 약함)
   - (C) 매일 cron 대신 종목 첫 진입 시 lazy fetch만 (cron 없음 — 누적 미실현, "반년" 요구 충족 불가)
   - 도메인팀 권장: **(A)**. 부서장 결정 필요.

2. **`change_alert` ±3%p 임계값**
   - (A) **권장**: ±3.0%p (MacroSentinel 정상 범위 외 보수 기준)
   - (B) ±2.0%p (V2 후속 #2 알림 정책과 동일 — 더 민감, 노이즈 위험)
   - (C) 표시 안 함 (보조 텍스트 자체 생략)
   - 도메인팀 권장: **(A) ±3.0%p**. V2 후속 #2 알림은 ±2%p로 별도 분리 운영 가능 (알림은 즉시성 / 보조 텍스트는 차트 동반).

3. **누적 보존 상한 250거래일 vs 365거래일**
   - (A) **권장**: 250거래일 (180일 슬라이더 안전 커버 + 1년 미달, macro_store 행 1개 크기 ≤ 50KB 추정)
   - (B) 365거래일 (정확히 1년, 부하 ×1.46배)
   - 도메인팀 권장: **(A) 250거래일**.

---

## 요건 항목

### FH-EXT-API: KIS wrapper (변경 없음)

#### [REQ-FH-EXT-API-01] (해당 없음 — KIS 신규 TR 미발견)

KIS TR 재검증 결과 외국인 소진율 장기 시계열 TR이 존재하지 않으므로 wrapper.py 신규 추가 없음. 기존 V1.5의 `get_foreign_holding_snapshot` / `get_foreign_holding_daily(days=30)` 그대로 사용.

수용 기준: wrapper.py 변경 없음 (회귀 가드).

---

### FH-EXT-STORE: 누적 캐시 모델

#### [REQ-FH-EXT-STORE-01] `macro_store` 누적 키 도입

설명: V1.5 영속 캐시 `foreign_holding:daily:{code}`(요청 시점 최신 30일)와 별도로, **일별 누적 시계열을 보관하는 신규 키** `foreign_holding:daily_history:{code}` 도입.

수용 기준:
- 카테고리 키: `foreign_holding:daily_history:{code}` (예: `foreign_holding:daily_history:005930`).
- 저장 값: `list[dict]` — 각 row는 V1.5 `get_foreign_holding_daily()` row와 동일 shape:
  ```python
  {
    "date": "2026-04-15",                # YYYY-MM-DD
    "close": 71500,                       # int
    "hts_frgn_ehrt": 53.85,               # float | None
    "frgn_ntby_qty": 152000,              # int (부호 보존)
  }
  ```
- 저장 항목 ascending(`date` 오름차순) + dedup(`date` 키 중복 시 마지막 row 유지).
- **보존 상한 250거래일** — 250건 초과 시 가장 오래된 row 제거(FIFO).
- macro_store `save_today` 사용 시 KST 일자 갱신이지만 본 키는 **누적 카테고리**이므로 매일 호출되어도 day-cap을 무한히 유지하는 데 문제없음 (macro_store는 카테고리당 1행 last-write-wins).
- `_merge_fh_daily(existing: list[dict], new_rows: list[dict]) -> list[dict]` 신규 헬퍼:
  - existing + new_rows 결합 → date 기준 dict-merge → ascending sort → 250건 cap → list 반환.
  - new_rows의 `hts_frgn_ehrt is None` row는 결합에서 제외(MarginAnalyst 가드).
- DB 마이그레이션 0건 (macro_gpt_cache 테이블 재사용).

테스트 힌트:
- 빈 누적 + 새 30일 → 30건 저장.
- 누적 200건 + 새 30일(겹침 10) → 220건 저장(dedup).
- 누적 240건 + 새 30일(전부 신규) → 250건 + 가장 오래된 20건 제거.
- 새 row `hts_frgn_ehrt=None` → merge에서 제외.
- 동일 date 2개 row → 마지막 1개 유지.
- KST 다음날 호출 → 영속 캐시 다른 카테고리(`daily:`)와 분리, 충돌 없음.

도메인 근거:
- MarginAnalyst: 누적 데이터 모델 (가) macro_store 채택, 250거래일 상한, 결함 row append 거부.
- 기존 V1.5 영속 캐시 패턴 일관성 (`_cache_get`/`_cache_save`).
레이어: unit
관련 전문가: MarginAnalyst

---

### FH-EXT-SERVICE: 서비스 레이어 확장

#### [REQ-FH-EXT-SERVICE-01] `fetch_foreign_holding` 기간 확장 + 누적 조회

설명: 기존 `services/supply_demand_service.fetch_foreign_holding(code, days=30)`의 days 범위를 5~180으로 확장하고, 누적 캐시 조회 로직 추가. 호출 흐름:

1. 누적 캐시 `foreign_holding:daily_history:{code}` 조회.
2. (장중/장후 무관) 신선도 검증 — 마지막 row의 `date`가 **최근 영업일** 또는 그 이전이면 즉시 30일 KIS fetch + merge + save (Lazy 백필).
   - `최근 영업일` 판정: KST 오늘 weekday < 5 + 14:30 이후라면 KST 오늘, 아니면 KST 오늘 -1 weekday 보정 (월요일이면 금요일).
3. KIS 30일 fetch는 V1.5 `wrapper_get_foreign_holding_daily(code, days=30)` 그대로.
4. merge 결과를 누적 키 + V1.5의 `foreign_holding:daily:{code}` 양쪽에 저장 (V1.5 30일 응답 호환).
5. snapshot은 V1.5 그대로 `foreign_holding:snapshot:{code}` 사용.
6. 요청 days만큼 누적 데이터에서 끝에서 잘라 반환 (`daily_history[-days:]`).

수용 기준:
- 함수 시그니처 변경: `fetch_foreign_holding(code: str, days: int = 120) -> dict` — 기본값 30 → 120.
- `days` 범위: **5 ≤ days ≤ 180**. 범위 외 `ServiceError(400)`.
- 다른 V1.5 정책(`is_domestic` 검증, `ConfigError` KIS 키, `NotFoundError` 종목 미존재, `ExternalAPIError` KIS 오류 + 결함 가드) 모두 유지.
- 응답 shape 변경 사항:
  - `days`: 요청값 (기본 120) — V1.5와 동일 키, 값 변경.
  - `daily`: 누적에서 끝 N일 슬라이스 — V1.5와 row shape 동일 (`date`/`close`/`frgn_ehrt_pct`/`frgn_ntby_qty`/`frgn_hldn_man_estimated`).
  - **신규 키** `daily_history_total_days`: 누적 보유 일수(정수). UI "누적 중 N/180" 안내용.
  - **신규 키** `change_alert`: 변화 보조 경고 객체.
    ```python
    {
      "first_date": "2025-11-15",
      "first_ehrt_pct": 50.20,
      "last_date": "2026-05-15",
      "last_ehrt_pct": 54.00,
      "abs_change_pct_point": 3.80,        # 절대값 (부호 분리)
      "signed_change_pct_point": 3.80,     # 부호 보존
      "threshold_pct_point": 3.0,
      "breached": true,                    # abs >= threshold
      "color": "warning"                   # "warning" | "neutral"
    }
    ```
    - `first_ehrt_pct`/`last_ehrt_pct` 둘 중 하나라도 None이면 객체 전체 생략 (응답 키 없음).
    - `threshold_pct_point` 기본 3.0(부서장 결정 권장값 (A)). 환경변수 `FH_CHANGE_ALERT_THRESHOLD` 미사용 — 코드 상수 `_FH_CHANGE_ALERT_THRESHOLD = 3.0`.
  - `snapshot`/`color_map`/`advisory_note` V1.5 그대로 유지.
- 매매 액션 키 부재 검증 유지: `recommendation`/`action`/`buy_signal`/`signal` 모두 응답 JSON에 없음.
- snapshot 가드 / 결함 응답 폐기 / 빈 응답 처리 V1.5 정책 모두 유지.
- 누적 캐시에 한 일자 row의 `hts_frgn_ehrt`가 None이면 daily 응답에서 제외 (UI 차트 단절 방지).

테스트 힌트:
- `fetch_foreign_holding("005930", 30)` → 기존 V1.5 동작 (회귀 가드).
- `fetch_foreign_holding("005930", 120)` → 누적이 30건이면 daily 30개 + `daily_history_total_days=30`, change_alert 생성.
- `fetch_foreign_holding("005930", 180)` → 누적이 250건이면 daily 180개.
- `fetch_foreign_holding("005930", 4)` → ServiceError.
- `fetch_foreign_holding("005930", 181)` → ServiceError.
- `fetch_foreign_holding("AAPL", 120)` → ServiceError (국내만).
- 누적 빈 상태 + KIS 정상 응답 30일 → 누적 저장 + daily 30개 반환.
- 누적 240건 + KIS 신규 30일(겹침 10) → 누적 260→250건(FIFO).
- 누적 데이터 일부에 `hts_frgn_ehrt=None` row 포함 → daily 응답에서 제외.
- 응답 JSON `recommendation`/`action`/`buy_signal`/`signal` 키 부재 검증.
- `change_alert.breached` 경계: 변화 +2.99%p → false, +3.0%p → true, -3.5%p → true(abs).
- 30일 차이만 있는 누적(120일 요청) → `change_alert.first_date`/`last_date`는 누적 양 끝(아닌 days 슬라이스 양 끝). 명세 — `daily` 슬라이스 첫/마지막 일자 기준으로 변화 계산.
- 신규 상장 7일 종목 → daily 7개 + `daily_history_total_days=7`, change_alert는 first=last가 다르면 생성, 같으면 생략.

도메인 근거:
- MacroSentinel: 슬라이더 180일 / change_alert ±3%p / 휴장일 처리.
- MarginAnalyst: 누적 데이터 헬퍼 / 결함 row 제외.
- OrderAdvisor: lazy 백필 / 매매 액션 키 금지 / 잔여여력 시계열 식 유지.

레이어: unit / integration
관련 전문가: MacroSentinel, MarginAnalyst, OrderAdvisor

---

### FH-EXT-CRON: 일별 백필 cron

#### [REQ-FH-EXT-CRON-01] APScheduler 일별 백필 잡

설명: `services/scheduler_service.py`에 신규 cron 잡 추가. 활성 국내 종목(advisory_stocks + watchlist) 외국인 보유 데이터를 KST 18:00 자동 fetch + 누적 저장.

수용 기준:
- 잡 함수: `_run_foreign_holding_backfill_job()` (services/scheduler_service.py).
- 트리거: `CronTrigger(hour=18, minute=0)`, id="foreign_holding_backfill", name="외국인 보유 추이 백필 (18:00)".
- 활성 종목 수집:
  - `advisory_store.all_stocks_all_users()` (전 사용자 advisory_stocks 코드 dedup) + `watchlist_store.all_codes()` 결합 + dedup.
  - `is_domestic(code)` True인 것만 (해외 종목 제외).
  - 50개 초과 시 안전상 50개로 truncate + logger.warning (단계적 부하 가시화 — MVP 좁힘).
- 부하 제어:
  - 종목당 `fetch_foreign_holding(code, days=30)` 1회 호출 (snapshot 1 + daily 1, V1.5 함수 그대로). days=30이면 누적 + V1.5 캐시 양쪽 갱신.
  - 각 종목 호출 간 `time.sleep(0.5)` (KIS 초당 2회 안정선) — 50종목 = 25초.
  - 종목별 try/except — 실패 시 logger.warning만 기록 + 다음 종목 진행 (절대 raise 안 함, 다른 lifespan 작업 보호).
- 휴장일 cron skip:
  - 함수 진입부 KST `weekday()` 5 이상(토/일)이면 즉시 return + logger.info.
  - KIS `chk_holiday` 호출 시도, 실패 시 silent pass(주말 가드만으로 충분).
  - 평일 공휴일은 catch-up 다음 영업일에 새 일자 1개만 누적되므로 무방.
- 실행 결과 로깅: `[스케줄러] 외국인 보유 백필 완료: 성공 N건, 실패 M건, 소요 K초`.
- 기존 `setup_scheduler()`에 `add_job` 추가 + `_run_macro_cleanup_job`/`_run_macro_prewarm_job` 등록 패턴 차용.

테스트 힌트:
- 모킹 테스트 (실 KIS 호출 없이):
  - 토요일 mock(`now_kst().weekday()=5`) → return + KIS mock 호출 0회.
  - 평일 mock + activated_codes=[`005930`, `000660`] → KIS mock 호출 2회 + `time.sleep` 1회.
  - 종목 1개 실패(예외) mock → 다른 종목 정상 진행 + logger.warning 호출.
  - 50개 초과 mock → 50개로 truncate 검증.
- 통합 테스트 (실제 KIS 환경 외 — 회귀 가드):
  - `setup_scheduler()` 호출 시 `foreign_holding_backfill` 잡 등록 확인.
- 수동 검증:
  - 운영 환경 18:00 cron 1회 실행 로그 확인 (`docker logs` SSM).

도메인 근거:
- OrderAdvisor: cron 안전(raise 금지/휴장일 skip/raise-loop 방지), 활성 종목 MVP 50개 좁힘.
- MacroSentinel: 18:00 (장 마감 + 30분 여유), 매크로 cron(00:05)과 시간대 분리.
- MarginAnalyst: 종목당 1회 fetch_foreign_holding 위임으로 결함 가드(`_is_defective_fh_daily`) 자동 적용.

레이어: integration
관련 전문가: OrderAdvisor, MacroSentinel

---

### FH-EXT-ROUTER: 라우터 days 범위 확장

#### [REQ-FH-EXT-ROUTER-01] `GET /api/advisory/{code}/foreign-holding` days 확장

설명: 기존 V1.5 엔드포인트의 days 검증 범위만 확장. 응답 shape는 service 응답 그대로 위임(추가 키 자동 노출).

수용 기준:
- 메서드/경로: `GET /api/advisory/{code}/foreign-holding` (변경 없음).
- 쿼리 파라미터: `days: int = 120` (기본 30 → 120 변경, 5~180).
- 응답: REQ-FH-EXT-SERVICE-01 dict 그대로 (`daily_history_total_days`/`change_alert` 키 추가됨).
- 예외 매핑 V1.5 유지: `ServiceError → 400`, `NotFoundError → 404`, `ConfigError → 503`, `ExternalAPIError → 502`.
- HTTPException 직접 raise 금지 (V1.5 유지).
- 응답 키 `advisory_note` 반드시 포함 (V1.5 유지).
- 매매 액션 키 부재 검증 유지.

테스트 힌트:
- `GET /api/advisory/005930/foreign-holding` (days 미지정) → 200, daily 길이 ≤ 120, daily_history_total_days 키 존재.
- `GET /api/advisory/005930/foreign-holding?days=180` → 200, daily 길이 ≤ 180.
- `GET /api/advisory/005930/foreign-holding?days=30` → 200, V1.5 호환 동작 (회귀 가드).
- `GET /api/advisory/005930/foreign-holding?days=181` → 400.
- `GET /api/advisory/005930/foreign-holding?days=4` → 400.
- `GET /api/advisory/AAPL/foreign-holding?days=120` → 400.
- 응답 JSON에 `recommendation`/`action`/`buy_signal` 키 부재.

도메인 근거: 라우터는 service 위임만 — V1.5 패턴 그대로.
레이어: api
관련 전문가: 없음 (위임)

---

### FH-EXT-UI: 프론트엔드 슬라이더 + 차트 확장

#### [REQ-FH-EXT-UI-01] `ForeignHoldingCard.jsx` 슬라이더/차트 확장 + 누적 상태 안내

설명: 기존 `ForeignHoldingCard.jsx` 컴포넌트의 슬라이더 범위 + 차트 x축 포맷 + 보조 텍스트 변경. 카드 레이아웃(좌 도넛 + 우 라인) 유지.

수용 기준:

**파일 변경**:
- `frontend/src/components/advisory/ForeignHoldingCard.jsx` — 슬라이더 범위 + x축 포맷 + 보조 텍스트
- `frontend/src/hooks/useAdvisory.js` — `useForeignHolding` 기본 days 30 → 120
- `frontend/src/api/advisory.js` — `fetchForeignHolding(code, days=120)` 기본값 변경 (정렬용, 옵셔널)

**슬라이더 변경**:
- 후보 (i) **stepper 30/60/90/120/180일** 채택 (MacroSentinel 권장).
- 기본값: 120일.
- 라벨: "기간: 30일 / 60일 / 90일 / 120일 / 180일".
- 슬라이더 컴포넌트 5단계 stepper로 변경 (예: 5개 버튼 그룹) 또는 native `<input type="range" min=0 max=4 step=1 />` + 인덱스 매핑.

**차트 변경**:
- x축 라벨 자동:
  - 30일: MM-DD 매일 (변경 없음).
  - 60~90일: MM-DD `interval={Math.floor(days/8)}` (recharts 자동 솎기).
  - 120~180일: MM-DD `interval={Math.floor(days/10)}` 또는 월말 라벨만.
- 툴팁: YYYY-MM-DD (V1.5 `makeTooltipFormatter` 재사용, 변경 없음).
- y축 도메인 V1.5 `[min-2, min(100, max+2)]` 유지.
- ReferenceLine 50/80/95 유지.
- 한도 라인(100%, `#9CA3AF` 점선) 유지.

**보조 텍스트 (`change_alert` 활용)**:
- 응답 `change_alert.breached === true` → 차트 상단에 노란색 작은 텍스트:
  - "최근 {days}일 외국인 보유율 {signed_change_pct_point > 0 ? '+' : ''}{value}%p 변화 (정상 범위 ±3.0%p)"
- `breached === false` 또는 객체 부재 → 기존 보조 텍스트 그대로:
  - "{days}일 변화: {first_ehrt_pct}% → {last_ehrt_pct}% ({signed_change_pct_point > 0 ? '+' : ''}{value}%p)"
- `change_alert` 객체 자체 부재(데이터 부족) → 보조 텍스트 생략.

**누적 데이터 안내** (사용자 첫 진입 시 누적 부족 케이스):
- 응답 `daily_history_total_days < days` 시 차트 하단 작은 회색 텍스트:
  - "데이터 누적 중: {daily_history_total_days} / {days}일. 매일 자동 채워집니다."
- `daily_history_total_days >= days`이면 표시 안 함.

**도넛 게이지 (V1.5)**: 변경 없음. 슬라이더 변경 무관(snapshot 단일값).

**부분 실패 격리** (V1.5): 변경 없음.

테스트 힌트 (수동 검증):
- 005930 진입 → 슬라이더 기본 120일 + 차트 노출.
- 슬라이더 30/60/90/120/180 5단계 클릭 → debounce 300ms 후 새 fetch + 차트 재렌더.
- 첫 진입 종목(누적 30일만 있음) + 슬라이더 180 → 차트 30일 + "데이터 누적 중: 30/180일" 안내.
- 6개월 이상 운영 후(누적 200건) 슬라이더 180일 → 차트 180일 + 보조 텍스트 정상.
- `change_alert.breached=true` mock → 노란 색 강조 텍스트.
- 한도 미설정 종목 → 도넛 회색 점선 + "한도 미설정" 배지 (V1.5 유지).
- 해외 종목 진입 → 카드 미렌더 (V1.5 유지).

도메인 근거:
- MacroSentinel: 5단계 stepper, x축 포맷 자동, 기본 120일.
- OrderAdvisor: 누적 안내(매매 액션 없음), `change_alert` 텍스트 표시만(매매 신호 X).
- MarginAnalyst: 결측 row 차트 단절 방지(service 단에서 제외).
- 사용자 요구: 반년 가시화 명확화.

레이어: ui (수동 검증)
관련 전문가: MacroSentinel, OrderAdvisor

---

## 교차 검토 체크리스트

- [x] **KIS TR 재검증**: 외국인 소진율 장기 시계열 TR 미존재 재확인 (LLM 카탈로그 + docs/kis grep 양방향) → wrapper 신규 추가 없음, 누적 캐시 우회 채택.
- [x] **누적 데이터 모델**: macro_store list append (MarginAnalyst 합의), DB 마이그레이션 0건.
- [x] **백필 전략**: Lazy + 일별 cron 18:00, OrderAdvisor 안전 정책(raise 금지/휴장일 skip/MVP 50개 좁힘).
- [x] **슬라이더 5단계 stepper**: 30/60/90/120/180일, 기본 120일 (사용자 요구 "반년").
- [x] **누적 보존 상한 250거래일**: FIFO, 무한 누적 방지, macro_gpt_cache 행 ≤ 50KB 추정.
- [x] **데이터 무결성**: 결함 row append 거부(`hts_frgn_ehrt=None`), dedup by date.
- [x] **회귀 가드**: V1.5 V1 동작 호환 (days=30/응답 shape 추가키만, snapshot/advisory_note/도넛 게이지/한도 미설정 처리 등).
- [x] **자동 주문 트리거 금지**: 응답 매매 액션 키 부재 검증 유지, cron 데이터 수집 전용.
- [x] **DB 마이그레이션 0건**: macro_gpt_cache 재사용.
- [x] **부분 실패 격리**: KIS 키 미설정/외부 API 실패/미존재 종목 → V1.5 정책 유지.
- [x] **휴장일 처리**: cron 주말 skip + 차트 거래일만 표시 (휴장일 보간 X).
- [x] **defensive 체제 예외**: 본 기능은 가시화만 — 투자 중단 로직 무관 (V1.5 유지).
- [x] **단일 책임 / 변경 최소**: wrapper 0건 + DB 0건 + 라우터 1줄(default값) + service 1함수 확장 + scheduler 1잡 추가 + UI 슬라이더 1개.
- [x] **MacroSentinel/MarginAnalyst/OrderAdvisor 3인 일치**: 9건 합의 + 불일치 3건 부서장 결정 요청.

---

## 통합 테스트 매트릭스

| 시나리오 | 기대 결과 |
|----------|----------|
| 첫 진입 + days=30 | V1.5 회귀(daily 30 + snapshot + daily_history_total_days=30) |
| 첫 진입 + days=120 | daily 30(KIS 한도) + daily_history_total_days=30 + "데이터 누적 중 30/120일" |
| 누적 200건 + days=120 | daily 120 + daily_history_total_days=200 + 안내 미표시 |
| 누적 250건 + KIS 신규 30(겹침 5) | merge 후 250건 cap (가장 오래된 25건 제거) |
| days=181 | 400 ServiceError |
| days=4 | 400 ServiceError |
| 해외 종목 days=120 | 400 ServiceError |
| change_alert 변화 +3.8%p | breached=true + 노란 강조 텍스트 |
| change_alert 변화 +1.5%p | breached=false + 일반 텍스트 |
| 신규 상장 7일 종목 days=30 | daily 7 + daily_history_total_days=7 + change_alert(first=last 다르면 생성) |
| 누적 row에 hts_frgn_ehrt=None 일자 | daily에서 제외, 차트 단절 없음 |
| KIS 키 미설정 days=120 | 503 + 카드 안내 (V1.5 호환) |
| 매매 액션 키 응답 | 부재 검증(recommendation/action/buy_signal/signal) |
| cron 토요일 실행 | KIS 호출 0건 + return logger.info |
| cron 평일 50종목 활성 | 50종목 처리 + sleep 0.5s × 50 = 25초 + 종목별 try/except |
| cron 활성 종목 51개+ | 50개 truncate + logger.warning |
| cron 종목 1개 KIS 5xx | logger.warning + 다른 종목 정상 진행 |
| 슬라이더 30→180 | debounce 300ms + 새 fetch + 차트 재렌더 |
| 6개월 운영 후 사용자 진입 | daily 180개 정상 노출 + 매일 1일씩 자연 누적 |

---

## 부서장 결정 요청 사항 (최종 정리)

도메인팀 권장과 함께 부서장 결정 필요:

1. **MVP cron 활성 종목 범위** → 권장 **(A) advisory_stocks 전체 + watchlist 국내** (50개 cap).
2. **`change_alert` 임계값** → 권장 **(A) ±3.0%p** (V2 후속 #2 알림 ±2%p와 별도 운영 가능).
3. **누적 보존 상한** → 권장 **(A) 250거래일**.
4. **슬라이더 stepper 형태** → 권장 5단계 stepper (30/60/90/120/180). 모바일/lg 모두 동일 UI.
5. **본 요건의 V2 후속 다른 항목과의 결합**:
   - 매크로 페이지 시장 단위 누적(V2 후속 #1) → 별도 작업 추천 (시장 TR이 다름).
   - 알림(V2 후속 #2) → 별도 작업 추천 (Notification/email API 별도 인프라).
   - 체제 결합 경고(V2 후속 #3) → 별도 작업 추천 (advisory_service 영향 큼).
   - **본 요건은 슬라이더 확장 + 누적만** — 단일 책임 / 최소 변경 / V1.5 회귀 가드 우선.

부서장 결정 후 개발팀장이 RED→GREEN→VERIFY 사이클 진행하면 됩니다.
