# 코드 감사 보고서 — 메뉴 간 공유 기능/데이터 공통화

## 요약

- 감사 일시: 2026-07-04 / 감사자: refactor-engineer
- 감사 범위: `routers/` `services/` `stock/` `screener/` + `frontend/src/` — 메뉴(시세판/관심종목/잔고/주문/스크리너/공시/종목상세/매크로/백테스트/세금/반도체/관리자) 간 중복 구현·중복 데이터 fetch 식별
- 발견: **HIGH 3 / MEDIUM 3 / LOW 3** (도메인 자문 필요 2건)
- 기준선 재확인 (이미 공통화 완료 — 재작업 불필요):
  - `stock/market.py:fetch_price / fetch_market_metrics` — screener·watchlist·balance·advisory·detail·portfolio_advisor·research_collector 7개 경로가 단일 함수 공유 (6h 캐시 포함) ✓
  - `stock/indicators.py:calc_technical_indicators` — advisory_fetcher가 위임 (헤더 주석에 분리 이력 명시) ✓
  - `services/ai_gateway.py` OpenAI 단일 진입점 ✓
  - 프론트 `hooks/useAsyncState.js` — 10개 메뉴 훅이 사용 ✓ / `hooks/useWebSocket.js` — useQuote·useExecutionNotice가 베이스로 재사용 ✓ / `api/client.js(apiFetch)` 경유 (raw fetch는 auth refresh 루프 방지용 3곳만 — 의도적) ✓
  - `SymbolSearchBar` 공용 컴포넌트 ✓
  - advisory_cache 공유 전환(2026-05-12 트랙)은 별도 완료 이력 확인 (`_workspace/dev_20260512_shared_cache/`)
- 의도적 분리로 판정 (변경 금지):
  - `services/order_kr.py / order_us.py / order_fno.py` — KIS TR_ID·파라미터 규격 상이, 도메인 분리
  - `services/quote_kis.py / quote_overseas.py` — WS 브릿지 vs polling, 데이터 소스 상이
  - `hooks/useMarketClock.js / useUsMarketClock.js` — KR 4구간(NXT/UN/KRX)과 US 세션(pre/regular/after, DST)은 규칙 자체가 다름
  - `components/macro/SupplyDemandSection.jsx` vs `components/advisory/SupplyDemandPanel.jsx` — 시장 수급(REQ-SUPPLY-UI-01) vs 종목 수급(REQ-SUPPLY-UI-02), 요건·훅·데이터가 다름. 컴포넌트 통합은 부적절. 단 내부의 동일 유틸(formatAmount 등)은 아래 F-2에서 추출.
  - `screener_cache.db` 날짜키 무만료 vs `cache.db` TTL — CLAUDE.md에 문서화된 캐시 전략 차이. 데이터 병합 대상 아님 (구현 공유만 F-9 LOW).

---

## 발견 사항 (우선순위순)

### [HIGH] F-1. KIS 인증 공통 모듈이 routers/에 위치 — 레이어 역전 17개소 — `routers/_kis_auth.py`

- 문제: KIS 토큰/자격증명/헤더의 단일 공통 모듈 `routers/_kis_auth.py`를 **services 9개 파일 + stock 4개 파일이 역방향 import**.
  - services: `balance_service.py:26`, `order_service.py:34`, `order_kr.py:17`, `order_us.py:12`, `order_fno.py:13`, `quote_kis.py:28`, `quote_overseas.py:291`, `tax_service.py:131,365,469,940`, `auth_deps.py:28`
  - stock: `kis_overseas_client.py:54`, `advisory_fetcher.py:29`, `order_store.py:19,28`, `tax_store.py:17`
  - 잔고/주문/세금/호가/AI자문/해외시세 등 KIS를 쓰는 **모든 메뉴가 공유하는 코어가 라우터 레이어에 있는 것**이 원인. `config → wrapper → db → routers → services → stock` 선언 구조와 어긋나며, 순환 import 위험(현재는 지연 import로 회피 중 — `quote_overseas.py:291`, `auth_deps.py:28` 등 함수 내부 import가 그 증거).
- 영향: 유지보수성(의존 방향 혼란, 신규 서비스가 routers를 import하는 패턴 고착), 테스트 격리 어려움.
- 도메인 자문 필요: **NO** — 로직 무변경 순수 이동. 단 주문 3서비스가 걸려 있으므로 이동 후 QA 스모크(주문/잔고/세금 경로) 필수.
- 공통화 제안: 모듈을 `services/kis_auth.py`(또는 `core/kis_auth.py`)로 이동, `routers/_kis_auth.py`는 `from services.kis_auth import *` re-export shim으로 유지(기존 import 경로 100% 호환 → 점진 전환, 롤백 1커밋).

### [HIGH] F-2. 프론트 포맷터/등락색 유틸 중복 — 공용 `utils/format.js` 부재

- 문제: 메뉴별 컴포넌트가 동일/유사 포맷터를 각자 정의. `frontend/src/utils/`에는 `pdfExport.js`만 존재.
  - **완전 동일 중복**: `formatAmount`(부호+억 단위) — `components/macro/SupplyDemandSection.jsx:24` ↔ `components/advisory/SupplyDemandPanel.jsx:22` (바이트 단위 동일, 매크로 메뉴 ↔ 종목상세 메뉴)
  - **유사 중복 + 일관성 결여**: `formatPct` 3곳 — `backtest/BacktestPortfolioModal.jsx:30`(toFixed(2)+부호), `backtest/BacktestHistoryTable.jsx:76`(toFixed(1)+부호), `advisory/ForeignHoldingCard.jsx:68`(toFixed(2), **+부호 없음**). 같은 "퍼센트"가 메뉴마다 다른 표기.
  - 기타: `formatDate` 2곳(backtest 2파일), `formatNumber`, `formatVolume/formatPrice`(order/OrderbookPanel.jsx:20,28), `formatMan`, `formatValue`, `formatLastSeen` 등 17개 정의 분산.
  - 등락색 조건(`text-red-500/text-blue-500`)도 20+ 컴포넌트가 각자 삼항 연산 (`OrderbookPanel.jsx:56 priceColor` 등). 수급 색상 상수(개인 #EF4444/외국인 #3B82F6/기관 #10B981)도 2곳 하드코딩.
- 영향: 일관성(같은 수치가 메뉴마다 다른 표기), 유지보수성(표기 정책 변경 시 17곳 수정).
- 도메인 자문 필요: **NO** — 표시 레이어. 단 formatPct의 자릿수/부호 차이가 화면별 의도인지는 통합 시 화면별 옵션 인자(digits, signed)로 보존하면 도메인 판단 자체가 불필요.
- 공통화 제안: `frontend/src/utils/format.js` 신설 — `formatPct(v, {digits, signed})`, `formatAmount`, `formatNumber`, `formatDate`, `changeColorClass(v)`, 수급 색상 상수. 완전 동일 중복(formatAmount)부터 위임, 유사 중복은 옵션 인자로 흡수.

### [HIGH] F-3. KST 타임존 자체 정의 13곳 — `db/utils.py` SSoT 위반

- 문제: CLAUDE.md가 `db/utils.py`(`KST`, `now_kst`, `now_kst_iso`)를 KST 정의 원본으로 명시하는데, 13개 모듈이 `timezone(timedelta(hours=9))`를 자체 정의:
  - services: `sector_recommendation_service.py:103`, `pipeline_service.py:48`, `ai_gateway.py:32`, `quote_kis.py:31`, `advisory_jobs.py:34`, `_telemetry.py:48`, `scheduler_service.py:13`
  - stock: `market.py:27`, `semi_collectors/` 5개 파일(hbm_contracts/market_breadth/memory_inventory/hyperscaler_capex/ai_ipo_tracker)
- 영향: 값은 동일해 현재 버그는 아니나, 시간 정책 변경·mock 테스트 시 13곳 분산. `pipeline_service.py`, `stock/db_base.py` 등 일부는 이미 `db.utils` 사용 — 반쪽 위임 상태.
- 도메인 자문 필요: **NO** — 상수 치환 (동작 동일).
- 공통화 제안: 전부 `from db.utils import KST, now_kst`로 치환. stock/→db/ 의존은 기존 선례 있음(`stock/db_base.py`).

### [MEDIUM] F-4. 관심종목 KR 시세 N건 개별 조회 vs 시세판 배치 조회 — `services/watchlist_service.py:312`

- 문제: 같은 "KR 현재가 다건" 데이터를 두 메뉴가 다른 경로로 조회.
  - 시세판: `routers/market_board.py:155` → `stock/market.py:fetch_prices_batch()` — yfinance `Tickers` 일괄 1회 + KIS REST 폴백 + 장중 10s/장외 60s 인메모리 TTL 캐시(`market.py:574`)
  - 관심종목: `watchlist_service.get_batch_details()` — ThreadPool(4)로 **종목별 `fetch_price()` 개별 호출** (N+1). 관심종목 50개면 yfinance 50회.
- 영향: 성능(중복 외부 API 호출, yfinance rate limit 위험), 동일 종목이 시세판·관심종목 양쪽에 있으면 같은 가격을 2경로로 fetch.
- 도메인 자문 필요: **YES** — value-screener: 관심종목 대시보드의 가격 신선도 요건상 시세판과 동일한 10s(장중)/60s(장외) TTL 배치 캐시를 공유해도 되는가? (관심종목은 관찰·스크리닝 목적이므로 허용 예상이나 확인 필요)
- 공통화 제안: `get_batch_details()`의 KR price 경로를 `fetch_prices_batch()` 재사용으로 전환 (change/change_pct 포함 여부 shape 확인 필요 — `market.py:734`). metrics(PER/PBR 등)는 기존 `fetch_market_metrics` 6h 캐시 유지.

### [MEDIUM] F-5. DART HTTP 호출 3중 구현 — 공시/종목상세/반도체 메뉴

- 문제: 동일 `https://opendart.fss.or.kr/api/list.json` 호출을 3개 메뉴가 각자 구현.
  - 공시(스크리너): `screener/dart.py:26` — `_dart_get()` 재시도 헬퍼 + `_DART_HEADERS` + 키 검증
  - 종목상세 사업개요: `stock/dart_segments.py:120,170` — raw `requests.get` (재시도 없음)
  - 반도체 HBM 수주: `stock/semi_collectors/hbm_contracts.py:70` — raw `requests.get` (재시도 없음)
  - `corpCode.xml`은 `stock/dart_fin.py:92,130` 한 곳에 모여 있어 양호(symbol_map이 위임).
- 영향: 일관성(재시도/타임아웃/에러 처리 3색), DART rate limit 대응 정책이 한 곳(screener)에만 존재.
- 도메인 자문 필요: **NO** — 전송 레이어(HTTP GET + 재시도 + status 체크)만 공용화. 각 메뉴의 파라미터 구성·응답 파싱은 그대로 유지하므로 도메인 로직 무변경.
- 공통화 제안: `stock/dart_client.py` 신설 (`dart_get(path, params, timeout, retries)` — 키 검증 + 재시도 + `ConfigError`). screener/dart.py의 기존 `_dart_get`을 표준으로 승격.

### [MEDIUM] F-6. VIX/매크로 스팟 시세 다중 조회 — 매크로 메뉴 내 3개 기능

- 문제: `^VIX` 등 매크로 심볼을 3개 모듈이 각자 `yf.Ticker`로 조회.
  - 심리지표(공포탐욕): `stock/macro_fetcher.py:150,258` — 자체 조회 (모듈 내에서도 2곳)
  - 거시 팩터 모델: `services/macro_factor_model.py:36` — `^VIX` logret 시계열 자체 조회
  - 매크로 스팟 quotes: `stock/yf_client.py:1331` — `^VIX` 포함 7심볼 fast_info 병렬 + 자체 캐시
- 영향: 성능(동일 스팟 값 중복 fetch), 일관성(캐시 TTL 제각각 → 같은 화면에서 VIX 값이 섹션마다 다를 수 있음).
- 도메인 자문 필요: **YES** — macro-sentinel: (1) 공포탐욕(스팟 실시간) / 팩터모델(일별 시계열) / yf_client quotes(스팟+캐시)의 신선도·기간 요건이 달라 의도적 분리인가? (2) 스팟 조회만이라도 단일 진입 함수(공유 캐시)로 묶으면 체제 판단(VIX 오버라이드)에 왜곡이 생기는가?
- 공통화 제안 (자문 결과 조건부): 스팟 조회를 `stock/macro_fetcher.py` 단일 함수로 승격 + 짧은 TTL 공유 캐시. 시계열(logret)은 용도가 달라 현행 유지.

### [LOW] F-7. SEC EDGAR User-Agent 문자열 3곳 조립

- 문제: `f"stock-manager/1.0 (contact={SEC_EDGAR_USER_AGENT_CONTACT})"` 조립이 `stock/sec_filings.py:18`, `stock/semi_collectors/ai_ipo_tracker.py:65`, `stock/semi_collectors/hyperscaler_capex.py:56(_user_agent())` 3곳. SEC 정책상 UA 형식이 바뀌면 3곳 수정.
- 영향: 일관성 (미미).
- 도메인 자문 필요: NO.
- 공통화 제안: `config.py`에 `SEC_EDGAR_USER_AGENT` 완성 문자열 상수 1개 정의, 3곳 위임.

### [LOW] F-8. ai_ipo_tracker의 yfinance 직접 호출

- 문제: `stock/semi_collectors/ai_ipo_tracker.py:44`가 `stock/market.py`/`yf_client.py`를 거치지 않고 yfinance 직접 호출.
- 판정: 파일 주석에 "yfinance 의존 분리. 테스트에서 mock 주입"이 명시 — **의도적 설계로 보임**. 현행 유지 권고. 공용 경로 전환 시 mock 주입 지점이 사라지므로 실익 없음.
- 도메인 자문 필요: NO (현행 유지).

### [LOW] F-9. 캐시 저장소 raw SQLite 구현 2중 — `screener/cache.py` vs `stock/cache.py`

- 문제: `get_cached/set_cached` 동일 인터페이스의 raw SQLite 캐시가 2벌. 단 **데이터 전략은 의도적으로 다름**(screener: 날짜키 무만료 / stock: TTL + NaN sanitize + WAL — CLAUDE.md 문서화). 데이터 병합 대상 아님.
- 영향: 구현 유지보수 중복 (59줄 vs 94줄, 소규모).
- 도메인 자문 필요: NO.
- 공통화 제안: 실익 낮음 — 보류 권고. 굳이 한다면 공용 베이스 함수 추출만 (DB 파일·키 전략은 분리 유지).

---

## 도메인 자문 필요 항목

1. **F-4 관심종목 배치 시세 전환** — 대상: **value-screener** — 질문: "관심종목 대시보드 KR 현재가를 시세판과 동일한 `fetch_prices_batch`(장중 10s/장외 60s TTL 공유 캐시)로 조회해도 관찰·스크리닝 용도에 신선도 문제가 없는가? 종목별 개별 조회를 유지해야 할 도메인 이유가 있는가?"
2. **F-6 VIX/매크로 스팟 조회 통합** — 대상: **macro-sentinel** — 질문: "공포탐욕(macro_fetcher 스팟), 거시 팩터모델(일별 logret 시계열), yf_client 매크로 quotes(스팟+캐시)가 각자 VIX를 조회하는 것이 신선도·기간 요건 차이에 따른 의도적 분리인가? 스팟 조회를 단일 함수+공유 캐시로 묶으면 체제 판단(VIX 오버라이드)이나 심리지표 산출에 왜곡 위험이 있는가? 허용 가능한 스팟 캐시 TTL은?"

## 리팩토링 우선순위 제안 (다음 Task 참고용)

1. F-3 KST 치환 (위험 최소, 즉시 가능)
2. F-2 프론트 format.js 신설 + 완전 동일 중복부터 위임
3. F-1 kis_auth 이동 + re-export shim (QA 스모크 동반)
4. F-5 dart_client 공용화
5. F-4 / F-6 — 도메인 자문 결과 수신 후
6. F-7 (F-5와 함께 처리 가능) / F-8, F-9 현행 유지·보류
