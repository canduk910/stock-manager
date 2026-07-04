# QA 검증 리포트 — 메뉴 간 공유 기능/데이터 공통화 리팩토링 (2026-07-05)

> 검증 주체: QA Inspector (본 리포트가 오케스트레이터의 임시 리포트를 대체 — 독립 재검증 수행, 결론 일치).
> 대상: `_workspace/refactor/03_plan.md`의 F-1~F-6 실행분 (42 files, +676 −1016, 커밋 전 working tree).
> 방식: "양쪽 동시 읽기" — git diff의 변경 전(-) 표기와 변경 후 구현을 항목별 교차 비교 + 런타임 검증(shim assert / import main / pytest / npm build).

## 결과 요약: **전체 PASS** (7/7 항목, 차단 이슈 0건, 비차단 관찰 4건)

| # | 항목 | 결과 | 근거 |
|---|------|------|------|
| 1 | F-2 프론트 포맷터 표기 보존 | PASS | 5개 컴포넌트 diff 전/후 출력 동일성 확인 + `npm run build` 성공 |
| 2 | F-1 kis_auth shim 경계면 | PASS | 코드 100% 동일(독스트링만 상이) + shim 동일성 assert + kis_auth 테스트 12건 PASS |
| 3 | F-4 watchlist shape/자문 제약 | PASS | 응답 dict 키 무변경 + value-screener 제약 3건 코드 반영 확인 |
| 4 | F-6 VIX 스팟 제약 준수 | PASS | TTL 0.17h / 실패 None+캐시 미저장 / 폴백 20 로컬 한정 / factor_model 미변경 |
| 5 | F-5 dart_client 재시도 동등성 | PASS | 재시도 정책 동일(3회, 1s/2s 대기) + 3개 호출부 파라미터/응답 처리 무변경 |
| 6 | F-3 KST 잔존 자체 정의 | PASS | `services/_telemetry.py:49` 1곳만 잔존 (stdlib-only 의도적 예외, 주석 명기) |
| 7 | 전체 회귀 (pytest + import) | PASS | 25 failed / 1704 passed — baseline 환경성 25건과 동일 구성 |

---

## 항목별 상세

### 1. F-2 — 프론트 공용 포맷터 (`frontend/src/utils/format.js` 신설)

변경 전(-) 로컬 함수 vs 신규 공용 함수 출력 교차 비교:

| 컴포넌트 | 기존 → 위임 | 표기 동일성 |
|----------|-------------|------------|
| `BacktestPortfolioModal.jsx` | formatDate/formatPct(2)/formatNumber | byte-identical 이동. `formatPct(v, 2)` → `formatPct(v)` (digits 기본 2) 동일 |
| `BacktestHistoryTable.jsx` | formatPct(1자리+부호) → `formatPct(v, {digits:1})` | 동일 (signed 기본 true). formatDate는 `DATE_OPTS`(연도 없음 MM-DD HH:MM) — 기존 `toLocaleDateString`+시간옵션과 `toLocaleString`+동일 Intl 옵션은 출력 동일 |
| `SupplyDemandSection.jsx` / `SupplyDemandPanel.jsx` | formatAmount + color_map fallback → `formatAmount`/`INVESTOR_COLORS` | 함수 본문/색상 hex 값 byte-identical |
| `ForeignHoldingCard.jsx` | formatPct(부호 없음) → `formatPct(v, {digits, signed:false})` 별칭 | '+' 미부착 보존 확인 (주석으로 의도 명기) |

- 빌드: `cd frontend && npm run build` → 성공 (기존 chunk-size 경고만, 에러 0).

### 2. F-1 — `routers/_kis_auth.py` → `services/kis_auth.py` + sys.modules shim

- **코드 동일성**: `git show HEAD:routers/_kis_auth.py` vs `services/kis_auth.py` diff → 독스트링 4줄만 상이, **코드 100% 동일**.
- **shim 동일성**: `import routers._kis_auth as a, services.kis_auth as b; a is b` → **True**. legacy 경로 import(`get_access_token`/`get_kis_credentials`/`BASE_URL`/`_token_cache` private 상태 포함) 정상.
- **역방향 import 교정**: services 9 + stock 4 + wrapper.py 3곳 전환 완료. 잔존 `routers._kis_auth` 문자열은 주석/독스트링뿐 (grep 전수 확인). routers/ 내부 4파일(quote/me_kis/order/balance)은 shim 경유 유지 — 계획대로.
- **테스트**: `pytest -k "kis_auth or auth"` → 12 passed. `test_kis_auth_multi_account.py` + `test_kis_overseas_client.py` 포함 세트 39건 PASS.
- `python -c "import main"` → OK (라우터 등록 경로 무손상, API 엔드포인트 무변경).

### 3. F-4 — 관심종목 KR 시세 배치 프리페치 (`services/watchlist_service.py`)

- **응답 shape 무변경**: 대시보드 row 키(`price/change/change_pct/market_cap/dividend_yield/sector/revenue/.../partial_failure`) 및 `fetch_batch_details` detail 키(`currency/price/.../sector`) 변경 전과 동일 — 프론트 watchlist 훅 접근 패턴과 일치.
- **자문 제약 대조** (`02_domain_advice.json` F-4, value-screener CAUTION):
  - "mktcap은 metrics 소싱": `_fetch_dashboard_row` — prefetch 사용 시 `info.mktcap`(stock_info 영속) → metrics 경로 → metrics_fresh 시 별도 보충까지 3중 가드 (`services/watchlist_service.py:180-206`). `fetch_batch_details`는 기존 `price.mktcap or metrics.mktcap` 폴백 유지 (`:391`). 단위도 raw→`_awk` 일관. **충족**
  - "부분 실패 시맨틱 보존": 배치 누락/실패 종목은 per-code `fetch_price` 폴백 → 그래도 실패 시 기존 `partial_failure`/`errors` 기록 경로 그대로. `_prefetch_kr_prices`는 배치 예외 시 빈 dict(전면 폴백). 결측 값(`price is None`)은 prefetch에서 필터되어 유입 차단. **충족**
  - "PER/PBR/ROE/배당/sector는 metrics 경로 유지": 무변경. **충족**
- 키 정규화: 배치 `price` → `close` 정규화로 소비측 분기 없음.
- 신규 테스트 `tests/unit/test_watchlist_price_prefetch.py` PASS. 기존 batch 테스트 3파일은 `fetch_prices_batch` mock 추가만 (검증 로직 무변경).

### 4. F-6 — `get_vix_spot()` 통합 (`stock/macro_fetcher.py`)

macro-sentinel CAUTION 제약 4건 대조:
- **통합 범위 스팟 3지점 한정**: fetch_vix / calc_fear_greed / `stock/yf_client.py:fetch_macro_indicators` 3곳 위임 확인. `services/macro_factor_model.py`는 **git status 미변경** (시계열 D 지점 통합 금지 준수). 충족
- **TTL**: `set_cached(key, value, ttl_hours=0.17)` — 자문 "권장: 현행 0.17h 유지" 그대로. 충족
- **실패 처리**: 조회 실패/None 시 `return None`, `set_cached` 미호출 (캐시 미저장). 충족
- **폴백 오염 방지**: `calc_fear_greed`의 `get_vix_spot() or 20` — 20은 로컬 변수로만 사용, 공유 키 `macro:vix_spot`에 저장 안 됨. 충족
- yf_client: `_fetch_vix_spot` lazy import 위임 + 실패 시 None (기존 shape `float|None` 유지, `_EXPECTED_KEYS` 테스트 PASS).
- 신규 테스트 `tests/unit/test_macro_vix_spot.py` PASS.

### 5. F-5 — `stock/dart_client.py` 신설

- 재시도 정책: `retries=3`, ConnectionError 한정, `sleep(2**attempt)` = 1s/2s 대기(3회 시도) + `Connection: close` — 기존 `screener/dart.py:_dart_get`과 **동등** (본문 승격).
- 호출부 3곳: `screener/dart.py`(import 위임), `stock/dart_segments.py` 2곳(params/timeout 15·30 무변경), `stock/semi_collectors/hbm_contracts.py`(params/timeout 20/`raise_for_status`/status 해석 무변경). dart_segments·hbm_contracts는 재시도+close 헤더가 추가되는 방향 — 계획 명시("재시도 정책 승격")대로.

### 6. F-3 — KST 위임

- `grep "timezone(timedelta(hours=9))|ZoneInfo" services/ stock/ routers/ screener/` → **`services/_telemetry.py:49` 1곳만 잔존** (stdlib-only 제약 주석 명기, 의도적 예외). `db/utils.py`는 SSoT 원본.
- import 정리 고아 검사: KST 위임 12개 파일에서 `timedelta`/`timezone` 잔존 사용처 전수 grep — 사용 파일은 import 유지(scheduler_service/market/ai_ipo_tracker), 제거 파일은 사용처 0. NameError 리스크 없음.

### 7. 전체 회귀

- `pytest tests/unit/ -q -m "not slow"` → **25 failed / 1704 passed / 8 skipped**. 실패 25건 = baseline 환경성과 동일 구성:
  - `test_analyst_*` 16건: `pdfplumber` 미설치 (ModuleNotFoundError)
  - `test_quote_overseas_kis_*` 9건: `pytest-asyncio` 플러그인 미설치 — 수집 단계 실패(0.01s)로 **코드 실행 전 실패임을 개별 실행으로 직접 확인** (F-1이 수정한 `services/quote_overseas.py`와 무관)
- API 엔드포인트 URL/응답 shape 변경: **0건** (routers/ diff는 shim 1파일뿐, 서비스 응답 키 무변경).

---

## 비차단 관찰 (수정 불요, 기록용)

- **A (MINOR)** `ForeignHoldingCard.jsx` — NaN 입력 시 기존 "NaN%" → 공용 포맷터 '-'. 프로젝트 관례(null→'-')와 일치하는 방어 개선, 실경로(null/number만 유입) 영향 없음.
- **B (INFO)** `get_vix_spot` TTL 0.17h(612s)는 자문 "≤600s" 문구와 12초 차이 — 자문이 0.17h를 권장값으로 명시했으므로 준수 판정.
- **C (INFO)** `fetch_vix` — value(공유 캐시, 최대 10분 전) vs prev(신규 `fast_info` 조회) 시점차로 change 필드에 미세 오차 가능. 표시용 필드, 영향 미미.
- **D (문서, 해소됨)** `stock/CLAUDE.md:24`의 dart_client 재시도 표기는 "3회 시도, 대기 1s/2s"로 코드와 일치 확인 — 추가 조치 불요.

## 판정

기능 퇴행 없음 / 빌드 PASS / API 계약(엔드포인트 URL·응답 shape·에러 코드) 무변경 / 도메인 자문 제약(`02_domain_advice.json`) 전 항목 이행 확인.
