# stock/ — 관심종목 패키지

CLI와 API 라우터 양쪽에서 공용. 비즈니스 데이터는 SQLAlchemy ORM(`db/`)으로 `~/stock-watchlist/app.db` 저장. 캐시(`cache.py`)만 raw SQLite(`cache.db`).

> 변경 이력은 `docs/CHANGELOG.md`가 단일 출처. 본 문서는 모듈 책임과 영구 규칙만 기술.

## 모듈 목록

| 파일 | 역할 |
|------|------|
| `db_base.py` | SQLite 캐시 전용 유틸. `connect(db_name, init_fn)` contextmanager. WAL + timeout 10s. KST 헬퍼는 `db/utils.py`에서 re-export (caller 호환). |
| `store.py` | 관심종목 CRUD + 순서 관리. `db/repositories/watchlist_repo.py` 위임 래퍼. |
| `order_store.py` | 주문 이력 + 예약주문 CRUD. `db/repositories/order_repo.py` 위임 래퍼. |
| `advisory_store.py` | AI자문 CRUD. `db/repositories/advisory_repo.py` 위임 래퍼. `save_cache(research_data=)` + `save_research_data()` + `get_report_by_id(report_id, user_id=None)`. **2026-05-12**: `advisory_cache` 공유 캐시 전환 — PK `(code, market)`로 단일화(`user_id` nullable 유지, 1차 안정화 후 2차 마이그레이션에서 drop 예정). 호환을 위해 `save_cache(user_id, ...)` / `load_cache(user_id, ...)` 시그니처 유지, 내부에서 `user_id` 무시(공유 저장/조회). `portfolio_reports` user_id 격리도 함께 적용 — `save_portfolio_report(user_id, ...)` / `get_portfolio_report_by_id(report_id, user_id=None)` / `get_portfolio_report_history(limit, user_id=None)` / `get_latest_portfolio_report(user_id=None)`. |
| `research_collector.py` | 리서치 6카테고리 ThreadPool 병렬 수집: 거시지표/밸류에이션밴드/경영진/공시/뉴스/증권사 컨센서스. `collect_all_research()`. KR 컨센서스: `naver_research`+`analyst_pdf` 요약+영속 + 중앙값/dispersion/upside/momentum_signal/consensus_overheated. US: `fetch_upgrades_downgrades` 메타데이터. |
| `advisory_fetcher.py` | AI자문 OHLCV 수집 + 사업부문 추론 + `fetch_valuation_stats()`(PER/PBR 5년) + `fetch_business_model()`(GPT 1회 JSON, MarginAnalyst+ValueScreener 도메인 가이드 시스템 프롬프트, 캐시 7일, `service_name="advisory_business_model"`). 기술지표 계산은 `indicators.py` 위임. KIS 1분봉 4시간대 ThreadPool 병렬. `fetch_15min_ohlcv_us`는 `kis_overseas_client.get_kis_ohlcv_15min` 우선 + yfinance fallback (`_normalize_kis_15min_to_advisory` 통일). |
| `stock_info_store.py` | 종목 정보 영속 캐시. `db/repositories/stock_info_repo.py` 위임 래퍼. 영역별 TTL + write-through 패턴. |
| `indicators.py` | 기술 지표 순수 계산 (MACD/RSI Wilder/Stochastic/BB/MA/ATR/`volume_signal`/`bb_position`). 외부 의존 없음. `calc_technical_indicators(ohlcv)` 최대 300봉. |
| `utils.py` | `is_domestic(code)` 6자리 숫자=국내 / `is_fno(code)` FNO 단축코드 판별. |
| `symbol_map.py` | 종목코드↔종목명 매핑 (7일 캐시). `code_to_name()`. pykrx 실패 시 DART corpCode.xml fallback. |
| `market.py` | yfinance 기반 KR 시세/시총/PER/PBR/배당/섹터. `_kr_yf_ticker_str(code)` `.KS/.KQ` suffix 자동 (score≥1 검증). PER/PBR/ROE는 yfinance 1차 실패 시 income_stmt/대차/분기 TTM으로 직접 계산. **`fetch_prices_batch(codes, market='KR'\|'US')`** — 시세판 다중심볼 일괄 폴링. yfinance `yf.Tickers(...)` fast_info 1차 → 빈응답·예외 시 KIS REST `FHKST01010100` 폴백 (분당 한도 보호 N≤20 가드). in-memory TTL 캐시(장중 10s/장외 60s). `{code: {price, change, change_pct, prev_close, volume, sign}}` 반환, 부분 실패 부분 반환 (시세판 부분 표시 우선). |
| `market_board.py` | 시세판: 신고가/신저가 탐지 + sparkline + 당일 OHLC 배치 조회. |
| `market_board_store.py` | 시세판 별도 등록 종목 CRUD. `db/repositories/market_board_repo.py` 위임. |
| `dart_fin.py` | OpenDart 재무제표 (최대 10년) + `fetch_quarterly_financials()`(누계→분기) + `calc_interest_coverage()`. 연도별 API 호출로 각 연도 고유 `rcept_no`(보고서 링크) 보장. **업종 4-tier 분기** (REQ-SECTOR): `detect_sector_tier(items) → "insurance"\|"bank_holding"\|"securities"\|"general"` (회계과목 패턴 자동 판별, `is_insurance_company()`와 동일 위치). 금융지주 매출 = `_sum_bank_holding_revenue()` (이자수익+수수료수익+보험수익 합산, 086790 28.33조/105560 47.43조 검증). 응답에 `sector_tier` 메타 + BS 신규 필드 5개(만기별 자산/부채). 보험사·증권사·일반 제조업 회귀 가드 PASS. |
| `dart_segments.py` | 사업개요/사업별 매출비중 추출 (DART OCR/XML). 일반 제조업 키워드(`사업의 내용`/`매출에 관한 사항`) + **금융지주 키워드 보강** (`_REVENUE_TABLE_PATTERNS` 8개 + `_REVENUE_SECTION_PATTERNS` 3개: `부문별\s*영업이익`/`영업\s*부문`/`그룹의\s*사업영역`/`주요\s*자회사` 등, 086790/105560/055550 실제 헤더 검증). 부문 라벨 7카테고리 GPT hint(`_BANK_HOLDING_SEGMENTS_HINT` — 은행/카드/증권/보험/자산운용/기타금융/비금융) + `_attach_metric_field()` `revenue_share`/`operating_income_share` 분기. 캐시 키 v3 bump(자유형식 라벨 무효화). |
| `yf_client.py` | yfinance 해외 데이터. EPS/Graham. 매출추정 3단계 fallback. `fetch_quarterly_financials_yf()` / `fetch_upgrades_downgrades()` / `fetch_company_officers()` / `fetch_major_holders()` / `fetch_earnings_dates()` / `fetch_macro_indicators()` / `fetch_sector_peers()`. 미국 종목 시세(`fetch_price_yf`/`fetch_detail_yf`/`fetch_period_returns_yf`)는 KIS(`stock.kis_overseas_client`) 우선 + yfinance fallback. `fetch_detail_yf`는 가격 필드만 KIS로 덮어쓰고 PER/PBR/52주/배당/sector는 yfinance 그대로(KIS 미제공). 한국 종목은 영향 없음. **KR raw 코드 가드**: `_resolve_yf_code(code)` 헬퍼 + `_ticker()` 진입부 자동 변환 — 6자리 숫자 KR 코드(`005830` 등)는 `_kr_yf_ticker_str()`로 `.KS`/`.KQ` 자동 부착 후 yfinance 호출(이미 변환된 ticker/매크로 심볼/US 알파벳은 그대로 통과). `validate_ticker`/`fetch_company_officers`/`fetch_major_holders`/`fetch_earnings_dates`/`fetch_sector_peers` 진입부에도 명시적 가드(캐시 키 일관성). 변환 실패 시 raw 반환(yfinance 404 graceful). |
| `kis_overseas_client.py` | **KIS 해외 시세 단일 게이트웨이**. wrapper.py 직접 호출은 이 모듈에서만. Public: `get_kis_price` / `get_kis_ohlcv_daily` / `get_kis_ohlcv_15min` / `get_kis_orderbook` / `get_kis_price_detail`. `_resolve_exchange(symbol)` — `stock_info.exchange`(NAS/NYS/AMS) 캐시 우선 → 미스 시 NAS→NYS→AMS 순회 후 영속. 인증은 `routers/_kis_auth.get_kis_credentials(user_id)` 재사용. 외부 호출 실패 시 None(fallback hook), `ConfigError`(키 부재)는 raise. 텔레메트리 `kis_overseas.{*}.{success,fail}`. |
| `naver_research.py` | 네이버 증권 리서치 스크래핑. 증권사별 목표가+의견+리포트+PDF 링크. `fetch_analyst_reports()`. 캐시 6h. |
| `analyst_pdf.py` | 증권사 PDF 본문 추출+요약. `pdfplumber` 첫 5p → gpt-5.4 JSON 6항목 → 300자 결합. 다운로드 10MB·15s 한도. 캐시 키 `analyst:summary:{md5(pdf_url)}` 영구. `ai_gateway` 시스템 호출(`user_id=None`, `service_name="analyst_summary"`). |
| `fno_master.py` | KIS 선물옵션 마스터파일. 인메모리(24h) → cache.db(7d) → ZIP 3단계. main.py에서 pre-warm. 파이프 구분자, CP949 인코딩, SSL 검증 우회. |
| `sec_filings.py` | SEC EDGAR 미국 10-K/10-Q. |
| `macro_fetcher.py` | 매크로 데이터: yfinance 지수/VIX/버핏/F&G + 금리곡선(^IRX/^FVX/^TNX/^TYX) + FRED HY OAS(BAMLH0A0HYM2) + IG OAS(BAMLC0A0CM) + 환율 4쌍 + 원자재 5종 + 섹터 ETF(US 11 + KR 14 — KODEX IT(157490) 추가, 네이버/카카오/삼성SDS/엔씨/넷마블 추적). FRED CSV 실패 → JSON API(`FRED_API_KEY`) → 7일 stale 순. **HY OAS 백분위 5단계** + OAS>10% 절대 안전장치. 2026-04~ ICE BofA 라이센스 변경으로 FRED ~3년치만 반환 → `oas_history_store` FIFO 누적 store에 매일 +1일 머지(7년 후 자연 10년 시계열 도달). 응답 `oas_stats{p10..p95}` / `oas_percentile` / `oas_zscore` / `oas_history_10y` / `oas_history_5y` / `ig_current` / `ig_history_10y` / `hy_ig_spread{,_history_10y}` / `partial_failure`. 캐시 24h(키 v8). `_compute_sma20_trend_days()` / `_compute_intensity_zscore(±3 cap)` 산점도 헬퍼. credit `direction`은 `oas_momentum_6m` 부호 기반 (HYG/LQD ETF 폐기, HYG 프록시 신뢰도 부족으로 미채택). |
| `oas_history_store.py` | FRED OAS 시계열 FIFO 영속 누적 store (2026-04~ ICE BofA 라이센스 정책 변경으로 FRED 3년 한계 대응). `merge_and_persist(series_id, new_rows)` / `get_history(series_id)` / `slice_history(series_id, years)` / `cleanup(series_id)`. cache.db 키 `macro:oas_history_persist:{series_id}` (TTL 50년 = 사실상 무한). 10년(365×10일) 보존, 가장 오래된 항목 자동 제거. `_PERSIST_TTL_HOURS=24*365*50` / `_RETENTION_DAYS=365*10`. |
| `report_store.py` | 보고서 CRUD. `db/repositories/report_repo.py` 위임. |
| `macro_store.py` | 매크로 GPT 일일 캐시. `db/repositories/macro_repo.py` 위임. `get_today` / `save_today` / `cleanup_old(days=30)` / `delete_today(category)` / `delete_before_today()` (자정 cleanup, cache.db `macro:*` 미터치). |
| `strategy_store.py` | 백테스트/전략 CRUD. `db/repositories/backtest_repo.py` 위임. Job: `save_backtest_job/result/update_job_status/delete_job/get_latest_backtest_metrics/get_job_history` + `set_mcp_job_id` + `update_job_failed`. Strategy: `save_strategy/list_strategies/get_strategy/delete_strategy` (builder_state_json 포함). |
| `tax_store.py` | 양도세 매매내역/계산/FIFO lot CRUD. `db/repositories/tax_repo.py` 위임. |
| `cache.py` | SQLite TTL 캐시 (`cache.db`). NaN/Inf → None 자동 sanitize. |
| `sector_normalize.py` | 섹터명 한글 라벨 정규화 SSoT. KR 14(매크로 `_KR_SECTOR_ETFS` 자동 동기) + US 11 GICS 한글 + "기타" 폴백. `normalize_sector(raw, market, code=None, industry=None)` — KR은 코드 화이트리스트(70종) → industry 정규식 → sector 정규식 → "기타" 순. yfinance가 KR 종목에 영문 GICS(`Consumer Cyclical`/`Auto Manufacturers` 등) 반환하는 케이스 커버. `\bMedia\b` 단어경계로 `Multimedia`(IT/인터넷)와 충돌 차단. `normalize_sector_cached()` 30일 TTL wrapper(`sector_norm:{market}:{code}`). |
| `display.py` | Rich 테이블 출력 + CSV 내보내기. |
| `cli.py` | Click CLI. `stock watch add/remove/list/memo/dashboard/info`. |

---

## DB 파일

| 파일 | 위치 | 용도 | 엔진 |
|------|------|------|------|
| `app.db` | `~/stock-watchlist/` | 비즈니스 데이터 통합 | SQLAlchemy ORM |
| `cache.db` | `~/stock-watchlist/` | TTL 캐시 (시세/재무/종목코드 등) | raw SQLite |

> 기존 watchlist.db, orders.db, advisory.db, market_board.db, stock_info.db, macro.db는 app.db로 통합.
> `scripts/migrate_sqlite_data.py`로 이관. `DATABASE_URL` 환경변수로 PostgreSQL/Oracle 전환.

---

## 핵심 규칙 및 Gotcha

### Store 래퍼 패턴 (Adapter)
- `store.py` 등 위임 래퍼 7개는 `db/repositories/`에 위임. 기존 시그니처 100% 유지 — services/, routers/ 변경 없음.
- Session: `db/session.py`의 `get_session()` contextmanager (commit+rollback+close 자동).
- `store.py` 마이그레이션: `ALTER TABLE ... ADD COLUMN market TEXT NOT NULL DEFAULT 'KR'` 자동.

### db_base.py
- **cache.py 전용** — 비즈니스 store는 `db/session.py` 사용
- KST 헬퍼는 `db/utils.py`에서 re-export (`from stock.db_base import now_kst_iso` 호환)
- WAL + timeout 10s. `_initialized` set으로 init 중복 방지

### market.py — yfinance 기반
- 2026-02 KRX 서버 변경으로 pykrx → yfinance 전환
- `fetch_market_metrics(code)`: 시총·PER·PBR·ROE·배당·52주·섹터 (장중 1h / 장외 12h)
- PER fallback: `trailingPE` None 시 연간 income_stmt 직접 계산 (`forwardPE` 사용 안 함)
- PBR/ROE fallback: priceToBook/returnOnEquity None 시 분기 TTM 직접 계산

### 배당수익률 우선순위
1. `dividendYield` — 이미 % (0.4, 1.3). KR/US 공통. **우선**
2. `trailingAnnualDividendYield × 100` — ADR 환율 오류 가능 (NVO 30.3% 사례)
3. `dividendRate / 현재가 × 100` — sanity check 0 < r < 50%

적용: `market.py:fetch_market_metrics`, `yf_client.py:fetch_detail_yf`

### symbol_map.py
- `_build_map()`: pykrx 실패 시 DART corpCode.xml fallback (빈 결과 캐시 방지)
- `_find_latest_trading_day()`: 최근 10거래일 역순 탐색
- 종목명이 코드로 저장되는 현상 → fallback 경로 확인할 것

### advisory_fetcher.py
- KIS 토큰: `routers/_kis_auth.get_access_token_safe()` (모듈 자체 캐시 제거됨)
- yfinance interval 제한: `15m` max 60d, `60m` max 2y, `1d`/`1wk` max 10y
- `fetch_segments_kr(code, name)` → `dict`: `{segments, description, keywords}` (GPT 1회 통합 추론)

### dart_fin.py
- `latest_year = today.year - 1` (월 경계 제거) — 3월에도 전년도 보고서
- 첫 배치 fallback: 빈 결과 시 `anchor-1` 재시도 (최신연도 미공시 기업)
- 전체 정규식 매칭: `_ACCOUNT_REGEX`/`_BS_REGEX`/`_CF_REGEX`/`_IS_DETAIL_REGEX` 4개 + `_match_account()` 공용

### yf_client.py
- 제약: 시세 15분 지연, 재무 최대 4년, 종목 검색 불가
- `fetch_price_yf()`: `fast_info.last_price or previous_close` (비개장일 직전 종가)
- `fetch_financials_multi_year_yf`: 캐시에 전체 연도 저장 후 슬라이싱 (부분 캐시 버그 방지)
- `fetch_segments_yf(code)` → `dict`: `{segments, description, keywords}` (캐시키 `yf:segments_v2:`)
- NaN → None 자동 정제

### dart.py — 캐시 주의 (참고: screener에 있음)
- `end_date < today`인 경우만 캐시 사용. 당일 빈 결과 캐시되면 이후 제출 공시 미노출 (골프존 사례)

### cache.py
- NaN: `_sanitize()`가 get/set 양쪽에서 NaN → None
- 시작 시 초기화: `entrypoint.sh` 기본 보존, `CACHE_PURGE_ON_START=1` 시 삭제

### 캐시 TTL

| 키 패턴 | TTL |
|---------|-----|
| `corpCode.xml` | 30일 |
| `symbol_map` | 7일 |
| `dart:fin*` / `dart:income*` / `dart:bs*` / `dart:cf*` / `dart:quarterly:` | 7일 |
| `valuation_stats:{market}:{code}` | 24h |
| `advisor:52w:{market}:{code}` | 6h |
| `market:metrics:` | 장중 1h / 장외 12h |
| `market:period_returns:` | 장중 15m / 장외 6h |
| `market:price:` | 장중 5s / 장외 30m (현재가 캐시 금지 도메인 원칙, F5 dedup만) |
| `yf:*` | 1~24h (장중/장외 분리), `yf:forward:` 6h |
| `market_board:intraday_ohlc:` | 장중 6m / 장외 6h |
| `analyst:summary:` | 영구 |

### stock_info_store.py (영속 캐시)
- Docker 재시작에도 유지 (entrypoint.sh 미초기화)
- 영역별 TTL: **price (장중 5s / 장외 30m — 현재가 캐시 금지 도메인 원칙, F5 dedup 한정)**, metrics (장중 6h / 장외 24h), financials (7일), returns (장중 30m / 장외 12h)
- write-through: `market.py`/`dart_fin.py`/`yf_client.py`의 fetch 함수가 결과 자동 저장
- 대시보드 우선 조회: `watchlist_service.py`에서 stock_info 먼저 → stale 시에만 외부 API

> 함수 시그니처 상세 → `docs/STOCK_PACKAGE.md`
