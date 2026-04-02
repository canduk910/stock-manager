# stock/ — 관심종목 패키지

CLI와 API 라우터 양쪽에서 공용으로 사용한다. 데이터는 `~/stock-watchlist/` 디렉토리에 저장.

## 모듈 목록

| 파일 | 역할 |
|------|------|
| `db_base.py` | SQLite 공용 유틸. `connect(db_name, init_fn)` contextmanager. WAL 모드 + timeout 10s. 4개 store 공용. |
| `store.py` | 관심종목 CRUD + 순서 관리. `watchlist.db`. 복합 PK `(code, market)`. `watchlist_order` 테이블로 DnD 순서 영속화. |
| `order_store.py` | 주문 이력 + 예약주문 CRUD. `orders.db`. `orders`(`status` 파라미터: PENDING/PLACED/REJECTED 등) + `reservations` 테이블. `list_active_orders()`: PENDING/PLACED/PARTIAL 대상. |
| `advisory_store.py` | AI자문 DB. `advisory.db`. `advisory_stocks` + `advisory_cache` + `advisory_reports` 3테이블. |
| `advisory_fetcher.py` | AI자문 데이터 수집 + 기술지표 계산. |
| `utils.py` | `is_domestic(code)` — 6자리 숫자=국내. `is_fno(code)` — FNO 단축코드 판별. |
| `symbol_map.py` | 종목코드↔종목명 매핑 (7일 캐시). `code_to_name()`. |
| `market.py` | yfinance 기반 시세/시가총액/PER/PBR/배당수익률. |
| `market_board.py` | 시세판: 신고가/신저가 탐지 + sparkline. |
| `market_board_store.py` | 시세판 별도 등록 종목 CRUD + 순서 관리. `market_board.db`. `market_board_order` 테이블로 DnD 순서 영속화. |
| `dart_fin.py` | OpenDart 재무제표 조회 (최대 10년). |
| `yf_client.py` | yfinance 기반 해외주식 데이터. |
| `fno_master.py` | KIS 선물옵션 마스터파일 다운로드/파싱/검색. 인메모리 캐시(24h) → cache.db(7일) → ZIP 3단계. main.py에서 pre-warm. |
| `sec_filings.py` | SEC EDGAR 미국 10-K/10-Q 공시 조회. |
| `macro_fetcher.py` | 매크로 분석 데이터 수집: yfinance 지수/VIX/버핏/공포탐욕, feedparser RSS(뉴스/투자자), 캐시 키 `macro:*` |
| `macro_store.py` | 매크로 GPT 결과 일일 캐시. `macro.db`. KST 날짜 기반 `(category, date_kst)` PK. `get_today()`/`save_today()`. 30일 자동 정리. |
| `cache.py` | SQLite TTL 캐시. `cache.db`. NaN/Inf → None 자동 sanitize. |
| `display.py` | Rich 테이블 출력 + CSV 내보내기. |
| `cli.py` | Click CLI. `stock watch add/remove/list/memo/dashboard/info`. |

---

## DB 파일

| 파일 | 위치 | 용도 |
|------|------|------|
| `watchlist.db` | `~/stock-watchlist/` | 관심종목 목록 |
| `orders.db` | `~/stock-watchlist/` | 주문 이력 + 예약주문 |
| `advisory.db` | `~/stock-watchlist/` | AI자문 (자문종목/분석캐시/리포트) |
| `market_board.db` | `~/stock-watchlist/` | 시세판 별도 등록 종목 |
| `cache.db` | `~/stock-watchlist/` | TTL 캐시 (시세/재무/종목코드 등) |
| `macro.db` | `~/stock-watchlist/` | 매크로 GPT 결과 일일 캐시 (KST 날짜 기반) |

---

## 핵심 규칙 및 Gotcha

### db_base.py
- **WAL 모드**: `PRAGMA journal_mode=WAL` + timeout 10초. 읽기-쓰기 동시성 보장.
- `_initialized` set으로 DB init 중복 방지.

### store.py
- **마이그레이션**: `ALTER TABLE ... ADD COLUMN market TEXT NOT NULL DEFAULT 'KR'` 자동 실행. 기존 데이터는 모두 `KR`.

### market.py — yfinance 기반 (중요)
- 2026-02 KRX 서버 변경으로 pykrx 전면 yfinance 전환.
- `_kr_yf_ticker_str(code)`: `.KS`(KOSPI)/`.KQ`(KOSDAQ) suffix 자동 선택 (7일 캐시).
- `fetch_market_metrics(code)`: 시가총액·PER·PBR·ROE·배당수익률·주당배당금 (6시간 캐시).

### 배당수익률 우선순위 (중요)
1. `dividendYield` — 이미 % 형태 (0.4, 1.3). KR/US 공통. **우선 사용**
2. `trailingAnnualDividendYield × 100` — 소수점(0.004=0.4%). ADR 환율 오류 가능 (NVO 사례: 30.3% 잘못됨)
3. `dividendRate / 현재가 × 100` — 연간 주당배당금 기반 (0 < result < 50% sanity check)

적용 파일: `market.py`(`fetch_market_metrics`), `yf_client.py`(`fetch_detail_yf`)

### symbol_map.py
- `_find_latest_trading_day()`: 최근 10거래일 역순 탐색.
- `code_to_name()`: 맵 빌드 실패 시 `get_market_ticker_name()` 직접 호출 fallback.
- 종목명이 코드로 저장되는 현상 → 이 fallback 경로 확인할 것.

### advisory_fetcher.py
- **KIS 토큰 모듈 캐시**: `_kis_token_cache`로 분당 1회 발급 제한 우회.
- **yfinance interval 제한**: `15m` max 60d, `60m` max 2y, `1d`/`1wk` max 10y.
- `calc_technical_indicators()`: MACD/RSI(Wilder)/Stochastic/BB/MA/ATR/MA배열/변동성돌파 목표가. 순수 pandas, 최대 300봉.
- `fetch_segments_kr(code, name)` → `dict` 반환: `{"segments": [...], "description": "사업설명", "keywords": ["테마1", ...]}`  (GPT 1회 호출로 매출비중+설명+키워드 통합 추론)

### dart_fin.py
- **`latest_year = today.year - 1`** (월 경계 제거) — 3월에도 전년도 보고서 조회.
- **첫 배치 fallback**: 빈 결과 시 `anchor-1`로 재시도 (최신연도 미공시 기업 대응).
- `_ACCOUNT_KEYS`에 적자 기업 변형 계정명 포함 (`영업손실`, `당기순손실`, `연결당기순이익` 등).

### yf_client.py
- **제약**: 시세 15분 지연, 재무 최대 4년, 종목 검색 불가.
- `fetch_price_yf()`: `fast_info.last_price or previous_close` — 비개장일 직전 종가 반환.
- `fetch_financials_multi_year_yf`: 캐시에 전체 연도 저장, 반환 시 슬라이싱 (부분 캐시 버그 방지).
- `fetch_segments_yf(code)` → `dict` 반환: `{"segments": [...], "description": "longBusinessSummary(300자)", "keywords": ["sector", "industry"]}` (캐시키: `yf:segments_v2:`)
- NaN → None 자동 정제.

### fno_master.py
- 파이프(`|`) 구분자, CP949 인코딩, SSL 검증 우회.
- 캐시 7일.

### cache.py
- **NaN 처리**: `_sanitize()`가 get/set 양쪽에서 NaN → None 변환 보장.
- **시작 시 초기화**: `entrypoint.sh`에서 `cache.db` 전체 삭제 (구버전 캐시 방지). `watchlist.db` 등 다른 DB는 영향 없음.

### 캐시 TTL

| 키 패턴 | TTL |
|---------|-----|
| `corpCode.xml` | 30일 |
| `symbol_map` | 7일 |
| `market:metrics:` | 6시간 (장중 1시간/장외 12시간) |
| `market:period_returns:` | 1시간 |
| 시세/재무 | 24시간 |
| `yf:*` | 1~24시간 (장중/장외 분리) |
| `yf:forward:` | 6시간 |

> 함수 시그니처 상세 → `docs/STOCK_PACKAGE.md`
