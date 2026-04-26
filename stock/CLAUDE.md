# stock/ — 관심종목 패키지

CLI와 API 라우터 양쪽에서 공용으로 사용한다. 비즈니스 데이터는 SQLAlchemy ORM(`db/` 패키지)으로 `~/stock-watchlist/app.db`에 저장. 캐시(`cache.py`)만 raw SQLite(`cache.db`) 유지.

## 모듈 목록

| 파일 | 역할 |
|------|------|
| `db_base.py` | SQLite 캐시 전용 유틸. `connect(db_name, init_fn)` contextmanager. WAL 모드 + timeout 10s. `cache.py` 공용. KST 헬퍼는 `db/utils.py`에서 re-export (기존 caller 호환). |
| `store.py` | 관심종목 CRUD + 순서 관리. `db/repositories/watchlist_repo.py` 위임 래퍼. 기존 함수 시그니처 100% 유지. |
| `order_store.py` | 주문 이력 + 예약주문 CRUD. `db/repositories/order_repo.py` 위임 래퍼. 기존 함수 시그니처 100% 유지. |
| `advisory_store.py` | AI자문 CRUD. `db/repositories/advisory_repo.py` 위임 래퍼. 기존 함수 시그니처 100% 유지. |
| `advisory_fetcher.py` | AI자문 OHLCV 수집 + 사업부문 추론 + **`fetch_valuation_stats()`**(PER/PBR 5년 통계). 기술지표 계산은 indicators.py 위임. KIS 1분봉 4시간대 병렬 수집(ThreadPoolExecutor). |
| `stock_info_store.py` | 종목 정보 영속 캐시. `db/repositories/stock_info_repo.py` 위임 래퍼. 시세/지표/재무/수익률 영역별 TTL. write-through 패턴. |
| `indicators.py` | 기술적 지표 순수 계산 (MACD/RSI/Stochastic/BB/MA/ATR/**volume_signal**/**bb_position**). 외부 의존 없음. |
| `utils.py` | `is_domestic(code)` — 6자리 숫자=국내. `is_fno(code)` — FNO 단축코드 판별. |
| `symbol_map.py` | 종목코드↔종목명 매핑 (7일 캐시). `code_to_name()`. |
| `market.py` | yfinance 기반 시세/시가총액/PER/PBR/배당수익률. |
| `market_board.py` | 시세판: 신고가/신저가 탐지 + sparkline + 당일 OHLC 배치 조회. |
| `market_board_store.py` | 시세판 별도 등록 종목 CRUD + 순서 관리. `db/repositories/market_board_repo.py` 위임 래퍼. |
| `dart_fin.py` | OpenDart 재무제표 조회 (최대 10년) + **`fetch_quarterly_financials()`**(DART 누계→분기 환산, 최근 4분기). |
| `yf_client.py` | yfinance 기반 해외주식 데이터. EPS/Graham Number 지표 제공. 매출추정 3단계 fallback. **`fetch_quarterly_financials_yf()`**(분기 실적). |
| `fno_master.py` | KIS 선물옵션 마스터파일 다운로드/파싱/검색. 인메모리 캐시(24h) → cache.db(7일) → ZIP 3단계. main.py에서 pre-warm. |
| `sec_filings.py` | SEC EDGAR 미국 10-K/10-Q 공시 조회. |
| `macro_fetcher.py` | 매크로 분석 데이터 수집: yfinance 지수/VIX/버핏/공포탐욕, feedparser RSS(**다중 피드 + 중복 제거 + 최신순 정렬**: 한국=비즈니스토픽+시장키워드, 해외=NYT+Google News US, 투자자=최신순), 캐시 키 `macro:*` |
| `report_store.py` | 보고서 CRUD (추천 이력/체제 이력/일일 보고서). `db/repositories/report_repo.py` 위임 래퍼. 다른 6개 store와 동일 패턴. |
| `macro_store.py` | 매크로 GPT 결과 일일 캐시. `db/repositories/macro_repo.py` 위임 래퍼. `get_today()`/`save_today()`/`cleanup_old()`. |
| `strategy_store.py` | 백테스트/전략 CRUD. `db/repositories/backtest_repo.py` 위임 래퍼. Job: `save_backtest_job()`/`save_backtest_result()`/`update_job_status()`/`delete_job()`/`get_latest_backtest_metrics()`/`get_job_history()`. Strategy: `save_strategy()`/`list_strategies()`/`get_strategy()`/`delete_strategy()` (전략빌더 저장/로드/삭제, builder_state_json 포함). |
| `tax_store.py` | 양도세 매매내역/계산/FIFO lot CRUD. `db/repositories/tax_repo.py` 위임 래퍼. `insert_transaction()`/`list_transactions()`/`insert_calculation()`/`list_calculations()`/`insert_fifo_lot()`/`list_fifo_lots()`/`delete_fifo_lots_by_year()`. |
| `cache.py` | SQLite TTL 캐시. `cache.db`. NaN/Inf → None 자동 sanitize. |
| `display.py` | Rich 테이블 출력 + CSV 내보내기. |
| `cli.py` | Click CLI. `stock watch add/remove/list/memo/dashboard/info`. |

---

## DB 파일

| 파일 | 위치 | 용도 | 엔진 |
|------|------|------|------|
| `app.db` | `~/stock-watchlist/` | 비즈니스 데이터 통합 (12 테이블) | SQLAlchemy ORM |
| `cache.db` | `~/stock-watchlist/` | TTL 캐시 (시세/재무/종목코드 등) | raw SQLite |

> 기존 watchlist.db, orders.db, advisory.db, market_board.db, stock_info.db, macro.db는 app.db로 통합됨.
> `scripts/migrate_sqlite_data.py`로 기존 데이터 이관 가능. `DATABASE_URL` 환경변수로 PostgreSQL/Oracle 전환.

---

## 핵심 규칙 및 Gotcha

### db_base.py
- **cache.py 전용**: `connect()` contextmanager는 cache.py에서만 사용. 비즈니스 store는 `db/session.py` 사용.
- **KST 헬퍼**: `db/utils.py`에서 re-export. `from stock.db_base import now_kst_iso` 형태로 기존 caller 호환.
- **WAL 모드**: `PRAGMA journal_mode=WAL` + timeout 10초. 읽기-쓰기 동시성 보장.
- `_initialized` set으로 DB init 중복 방지.

### Store 래퍼 패턴 (Adapter)
- 7개 store 모듈(`store.py`, `order_store.py`, `report_store.py` 등)은 `db/repositories/` Repository에 위임하는 래퍼.
- 기존 함수 시그니처 100% 유지 — services/, routers/ 변경 없음.
- Session 관리: `db/session.py`의 `get_session()` contextmanager 사용 (commit+rollback+close 자동).

### store.py
- **마이그레이션**: `ALTER TABLE ... ADD COLUMN market TEXT NOT NULL DEFAULT 'KR'` 자동 실행. 기존 데이터는 모두 `KR`.

### market.py — yfinance 기반 (중요)
- 2026-02 KRX 서버 변경으로 pykrx 전면 yfinance 전환.
- `_kr_yf_ticker_str(code)`: `.KS`(KOSPI)/`.KQ`(KOSDAQ) suffix 자동 선택 (7일 캐시). score ≥ 1 필수 (mktcap 또는 shares 1개 이상). score=0(price만 존재)은 잘못된 suffix로 판정.
- `fetch_market_metrics(code)`: 시가총액·PER·PBR·ROE·배당수익률·주당배당금·52주고가·52주저가 (6시간 캐시). PBR fallback: `priceToBook` None 시 대차대조표 자본총계/주식수로 직접 계산. ROE fallback: `returnOnEquity` None 시 분기 TTM순이익/자기자본으로 직접 계산.

### 배당수익률 우선순위 (중요)
1. `dividendYield` — 이미 % 형태 (0.4, 1.3). KR/US 공통. **우선 사용**
2. `trailingAnnualDividendYield × 100` — 소수점(0.004=0.4%). ADR 환율 오류 가능 (NVO 사례: 30.3% 잘못됨)
3. `dividendRate / 현재가 × 100` — 연간 주당배당금 기반 (0 < result < 50% sanity check)

적용 파일: `market.py`(`fetch_market_metrics`), `yf_client.py`(`fetch_detail_yf`)

### symbol_map.py
- `_build_map()`: pykrx 실패 시 DART corpCode.xml fallback 추가 (빈 결과 캐시 방지).
- `_find_latest_trading_day()`: 최근 10거래일 역순 탐색.
- `code_to_name()`: 맵 빌드 실패 시 `get_market_ticker_name()` 직접 호출 fallback.
- 종목명이 코드로 저장되는 현상 → 이 fallback 경로 확인할 것.

### advisory_fetcher.py
- **KIS 토큰**: `routers/_kis_auth.get_access_token_safe()` 사용 (모듈 내 자체 캐시 제거됨).
- **yfinance interval 제한**: `15m` max 60d, `60m` max 2y, `1d`/`1wk` max 10y.
- 기술지표 계산은 `indicators.py`의 `calc_technical_indicators()`에 위임. `fetch_ohlcv_by_interval()`에서 자동 호출.
- `fetch_segments_kr(code, name)` → `dict` 반환: `{"segments": [...], "description": "사업설명", "keywords": ["테마1", ...]}`  (GPT 1회 호출로 매출비중+설명+키워드 통합 추론)

### indicators.py
- 순수 계산 함수 8개: `_ema`, `_sma`, `_rsi`, `_stoch`, `_bollinger`, `_atr`, `_safe_val`, `calc_technical_indicators`
- 외부 의존성 없음 (`math`, `typing.Optional`만 사용)
- `calc_technical_indicators(ohlcv)`: MACD/RSI(Wilder)/Stochastic/BB/MA/ATR/MA배열/변동성돌파 목표가 + **`volume_signal`**(최신/5일평균 비율) + **`bb_position`**(BB밴드 내 위치 0~100). 최대 300봉.
- `advisory_fetcher.py`의 `fetch_ohlcv_by_interval()`에서 자동 호출

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
| `dart:fin*` / `dart:income*` / `dart:bs*` / `dart:cf*` | **7일 (168시간)** |
| `valuation_stats:{market}:{code}` | 24시간 |
| `dart:quarterly:{code}` | 7일 |
| `advisor:52w:{market}:{code}` | 6시간 |
| `market:metrics:` | 장중 1시간 / 장외 12시간 |
| `market:period_returns:` | 장중 15분 / 장외 6시간 |
| `market:price:` | 장중 6분 / 장외 6시간 |
| `yf:*` | 1~24시간 (장중/장외 분리) |
| `yf:forward:` | 6시간 |
| `market_board:intraday_ohlc:` | 장중 6분 / 장외 6시간 |

### stock_info_store.py (영속 캐시)
- **Docker 재시작에도 유지**: `stock_info.db`는 `entrypoint.sh`에서 초기화하지 않음
- **영역별 TTL**: price(10분/6시간), metrics(2시간/12시간), financials(7일), returns(30분/6시간)
- **write-through**: `market.py`, `dart_fin.py`, `yf_client.py`의 fetch 함수가 결과를 자동 저장
- **대시보드 우선 조회**: `watchlist_service.py`에서 stock_info 먼저 조회, stale 시에만 외부 API 호출

> 함수 시그니처 상세 → `docs/STOCK_PACKAGE.md`
