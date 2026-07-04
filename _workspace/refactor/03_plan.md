# 리팩토링 계획 — 메뉴 간 공유 기능/데이터 공통화 (2026-07-04)

> 감사: `01_audit_report.md` (F-1~F-9). 본 계획은 Task 3(자문 불요 4건) + Task 4(자문 반영 2건) 실행 설계.
> 원칙: API 계약 보존 / 항목당 독립 revert 가능 / 항목별 빌드·테스트 확인 / commit·push는 사용자 `/doc-commit` 시에만.

## 실행 순서 (위험 오름차순)

### 1) F-3: KST 자체 정의 13곳 → `db/utils.KST` 위임 (위험: 최소)
- 대상: services 7곳(sector_recommendation/pipeline/ai_gateway/quote_kis/advisory_jobs/_telemetry/scheduler) + stock 6곳(market + semi_collectors 5)
- 방식: `from db.utils import KST as <기존 로컬명>` — 사용처 무변경(별칭 유지, 최소 diff)
- 검증: `pytest tests/unit/ -m "not slow"` + 대상 모듈 import 스모크

### 2) F-2: 프론트 공용 포맷터 `utils/format.js` 신설 (위험: 낮음)
- 신설: `frontend/src/utils/format.js`
  - `formatPct(v, {digits=2, signed=true})` — 기존 3곳의 자릿수/부호 차이를 옵션으로 보존
  - `formatAmount(v)` (부호+억, 바이트 동일 중복 2곳 통합)
  - `formatNumber(v)` (ko-KR locale)
  - `formatDate(iso)` (backtest 2곳 통합)
  - 수급 투자자 색상 상수 `INVESTOR_COLORS` (개인/외국인/기관 — 2곳 하드코딩 통합)
- 위임 대상(확인된 중복만, 표기 결과 100% 동일 보장):
  - `components/macro/SupplyDemandSection.jsx`, `components/advisory/SupplyDemandPanel.jsx` — formatAmount
  - `components/backtest/BacktestPortfolioModal.jsx` — formatPct(digits:2)/formatNumber/formatDate
  - `components/backtest/BacktestHistoryTable.jsx` — formatPct(digits:1)/formatDate
  - `components/advisory/ForeignHoldingCard.jsx` — formatPct(signed:false)
- 범위 외(의도적): OrderbookPanel formatPrice/formatVolume(시장별 소수점 규칙 — 주문 도메인 고유), 나머지 단발 포맷터는 후속
- 검증: `cd frontend && npm run build`

### 3) F-1: `routers/_kis_auth.py` → `services/kis_auth.py` 이동 + 별칭 shim (위험: 중간)
- 방식: **sys.modules 별칭 shim** — `routers/_kis_auth.py`를
  `from services import kis_auth as _impl; sys.modules[__name__] = _impl` 2줄로 교체.
  → `routers._kis_auth`와 `services.kis_auth`가 **동일 모듈 객체**: 기존 import 경로,
  `patch("routers._kis_auth....")` monkeypatch, `_token_cache` 등 private 가변 상태까지 100% 호환.
- import 방향 교정(같은 객체이므로 동작 무변경, 선언 방향만 수정):
  - services 9파일 + stock 4파일의 `routers._kis_auth` → `services.kis_auth`
  - wrapper.py 지연 import 3곳 동일 교정
  - routers/ 내부 4파일은 shim 경유 유지(동일 레이어 — 교정 불필요)
- 근거: `__init__.py` 전부 빈 파일 — 순환 import 없음. kis_auth 자체 의존은 config/services.exceptions/requests뿐.
- 검증: `pytest tests/unit/test_kis_auth_multi_account.py tests/unit/test_kis_overseas_client.py` + 전체 unit + `python -c "import main"` 스모크
- 롤백: shim 파일 1개 + import 라인만 원복 (독립 revert)

### 4) F-5: DART HTTP 공용 클라이언트 `stock/dart_client.py` (위험: 낮음)
- 신설: `stock/dart_client.py` — screener/dart.py `_dart_get`(Connection:close + ConnectionError 3회 재시도) 승격
- 위임: `screener/dart.py:_dart_get`(본문 위임), `stock/dart_segments.py`(2곳), `stock/semi_collectors/hbm_contracts.py`(1곳)
- 파라미터 구성/응답 파싱은 각 모듈 유지 — 전송 레이어만 공용화 (도메인 로직 무변경)
- 검증: `pytest tests/unit/ -m "not slow"` 관련 테스트

## Task 4 (자문 CAUTION 승인 — 실행 완료, `02_domain_advice.json` 참조)

### F-4: 관심종목 KR 시세 배치 전환 — value-screener **CAUTION → 실행 완료**
- **감사 전제 정정 (자문 audit_correction 반영)**: 감사 보고서는 `fetch_prices_batch`가 "장중 10s/장외 60s TTL 공유 캐시"를 쓴다고 전제했으나, 2026-06-01 "현재가 캐시 금지" 강화로 현행 코드는 TTL 캐시를 **우회**하고 매 호출 외부 API를 친다. 배치와 개별 fetch_price는 신선도 동일 — **전환 이득은 순수 외부 호출 수 감소(N회 → 1회)**.
- 실행: `_prefetch_kr_prices()` 헬퍼 신설 + `get_dashboard_data`/`fetch_batch_details` 진입점 배치 1회 프리페치.
  - 제약 ① 배치 응답 shape 흡수: price→close 키 정규화 (mktcap/shares 부재 인지)
  - 제약 ② 시총은 stock_info → `fetch_market_metrics`(6h 캐시) 소싱 — `_fetch_dashboard_row`의 price.mktcap 의존 이전 + 결측 방지 가드
  - 제약 ③ 배치 누락 종목은 per-code fetch_price 폴백 → 기존 errors/partial_failure 시맨틱 보존 (조용한 결측 없음)
  - PER/PBR/ROE/배당/sector는 기존 metrics 경로 유지
- 회귀 가드: `tests/unit/test_watchlist_price_prefetch.py` 신규 7건 + 기존 테스트 2파일 fetch_prices_batch patch 보강(실네트워크 시도 제거).

### F-6: VIX/매크로 스팟 조회 통합 — macro-sentinel **CAUTION → 실행 완료**
- 실행: `macro_fetcher.get_vix_spot() -> float|None` 스칼라 승격.
  - 제약 ① 통합은 스팟 3지점만 (fetch_vix / calc_fear_greed / yf_client.fetch_macro_indicators). `macro_factor_model`의 7년 ^VIX logret 시계열(PCA용)은 **통합 금지 — 현행 유지**
  - 제약 ② 공유 캐시 TTL 0.17h(10분) 고정 — 1h 상향 금지 (VIX>35 체제 오버라이드 즉각 반응 보존)
  - 제약 ③ 실패 시 None + 캐시 미저장. fear_greed 폴백 20은 로컬 적용만 (공유 캐시 오염 금지)
  - 표시용 sparkline/level은 fetch_vix 잔류
- 회귀 가드: `tests/unit/test_macro_vix_spot.py` 신규 7건 + `test_macro_indicators_parallel.py` 계약 갱신(vix는 공유 스팟 위임).

## 보류/현행 유지 (감사 판정)
- F-7(SEC UA 상수화): F-5와 함께 처리 가능하면 포함, 아니면 후속
- F-8(ai_ipo_tracker yfinance 직접): 테스트 mock 주입용 의도적 — 현행 유지
- F-9(캐시 저장소 2중): 데이터 전략 의도적 상이 — 보류
