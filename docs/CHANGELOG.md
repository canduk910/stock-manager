# 변경 이력

## 2026-04-04 — 역발상 매수 전략 + 밸류에이션 차트 확장 + UI 개선

### 프롬프트 개선
- 포트폴리오 AI자문: cautious/selective 체제에서 역발상 매수 규칙 10개 추가 (규칙 19~28)
- 역발상 매수 5대 적격 조건 (52주 -30%+, PBR<1.0, 부채비율<100%, 영업이익 흑자, FCF 양수)
- 보유종목 vs 신규종목 판단 분리, 포지션 한도 (cautious 1.5%/7.5%)
- 포트폴리오 자문 컨텍스트에 종목별 52주 고가·하락률 추가

### 신규 기능
- 스크리너 API: `drop_from_high` 쿼리 파라미터 추가 (52주 고점 대비 하락률 필터)
- 스크리너 enrichment: `high_52`, `low_52`, `drop_from_high` 필드 추가
- FilterPanel: "52주 고점 대비 (%)" 입력 필드 추가

### UI 개선
- 메뉴바 순서 변경: 시세판→관심종목→분석▼→포트폴리오→매매▼, 그룹 구분선 3개
- ValuationChart: 시가총액 추이(보라) + 발행주식수 추이(주황) 차트 추가
- 발행주식수: 분기별 시계열 반영 (자사주 소각 등 변동 추적)

### 버그 수정
- EPS fallback: DART EPS 미제공 종목(SK하이닉스 등)에서 net_income/shares로 직접 계산
- PBR fallback: yfinance priceToBook None 시 대차대조표 자본총계/주식수로 계산 (골프존 등)
- yf_client: tz-aware/tz-naive 비교 버그 수정 (밸류에이션 히스토리 빈 배열 반환)
- KRX 경로: pykrx 빈 결과 시 yfinance fallback 전환
- fetch_market_metrics: high_52/low_52 필드 추가

### UI 개선 (자동완성)
- AddStockForm에 자동완성 검색 추가 (KR: 400ms debounce + 드롭다운, US: 티커 직접 입력)
- 기존 searchStocks API 재사용, 외부 클릭 닫기, 시장 변경 시 상태 초기화

## 2026-04-04 — SQLAlchemy ORM 마이그레이션

### 리팩토링
- SQLite 직접 접근 → SQLAlchemy ORM 전환 (6개 비즈니스 DB → 단일 `app.db` 통합)
- `db/` 패키지 신규: `base.py`(DeclarativeBase) + `session.py`(Engine/Session) + `models/`(12개 모델) + `repositories/`(6개 Repository)
- 기존 6개 store 모듈(`store.py`, `order_store.py` 등)은 Repository 위임 래퍼로 전환 (함수 시그니처 100% 유지)
- Alembic 마이그레이션 도입 (`alembic/`): 스키마 버전 관리, `render_as_batch=True` (SQLite 호환)
- `config.py`에 `DATABASE_URL` 환경변수 추가 (기본값: SQLite, PostgreSQL/Oracle 전환 가능)
- `main.py` lifespan + `entrypoint.sh`에서 `alembic upgrade head` 자동 실행
- `scripts/migrate_sqlite_data.py` 신규: 기존 6개 DB → app.db 데이터 이관 스크립트
- cache.db, screener_cache.db는 raw SQLite 유지 (ORM 이점 없는 TTL 캐시)
- services/, routers/, frontend/ 변경 없음

## 2026-04-04 — 계량지표 확장 + 포워드차트 + 매출추정 개선

### 기본적분석 개선
- 계량지표 8개→10개 확장: EPS + 안전마진가격(Graham Number) 추가 (MarginAnalyst 자문)
- MetricCard integer prop: 부채/자본, 유동비율, EPS, 안전마진가격 소수점 제거
- 프론트엔드 "Graham" 표기 → "안전마진/안전마진가격"으로 통일 (백엔드 키명 유지)
- ForwardEstimatesSection: 매출/순이익 현재E+차기E sub 텍스트 추가
- IncomeChart: 추정치 연도(xxE) 반투명 바 추가 (매출E+순이익E, opacity 0.35)

### 버그 수정
- fetch_market_metrics()에 shares 필드 누락 → Graham Number 계산 불가 수정
- 매출 추정치 수집 3단계 fallback: revenue_estimate(신API) → analysis(레거시) → totalRevenue×growth

## 2026-04-04 — 성능 최적화 리팩토링 (DB 캐시 + 병렬화)

### 성능 최적화
- `stock/stock_info_store.py` 신규: 종목 정보 영속 캐시 DB (`stock_info.db`). Docker 재시작에도 유지
- `watchlist_service.py`: stock_info DB 우선 조회 → stale 영역만 외부 API 호출 (대시보드 응답 속도 개선)
- `advisory_service.py`: `_collect_fundamental_kr/us` 5~6개 데이터 소스 ThreadPoolExecutor 병렬 수집
- `advisory_fetcher.py`: KIS 1분봉 4시간대 순차→병렬 수집 (최악 80초→20초)
- `macro_service.py`: sparkline 병렬 결과 미사용 버그 수정 (결과 버려지고 순차 재호출되던 문제)
- `dart_fin.py`: 재무 캐시 TTL 24시간→7일(168시간) 확장 (사업보고서 분기 변동 주기에 맞춤)
- `market.py`/`yf_client.py`: write-through 패턴으로 stock_info DB에 시세/지표/재무 자동 저장

### DB 인덱스 추가
- `order_store.py`: orders 테이블에 status, order_no+market, symbol+market 인덱스 3개 추가
- `advisory_store.py`: advisory_reports 테이블에 code+market+generated_at 인덱스 추가

### 프론트엔드 최적화
- `OrderPage.jsx`: 탭/마켓 전환 useEffect 분리 — market 변경 시 현재 활성 탭만 리로드

## 2026-04-04 — 메뉴바 드롭다운 + 대시보드 재설계 + doc-commit 스킬

### UI 개선
- Header.jsx: 9개 평면 메뉴 → 5개 드롭다운 (포트폴리오|분석▼(매크로/스크리너/공시)|관심종목|매매▼(주문/잔고)|시세판)
- 드롭다운 hover 영역: `mt-1` gap → `pt-1` 투명 패딩으로 마우스 이탈 방지
- DashboardPage.jsx: 포트폴리오 요약(체제배너+자산현황+배분차트) + 오늘 공시로 재설계

### 스킬 신규
- `.claude/skills/doc-commit/`: 문서 반영 + 커밋 + compact 자동화 스킬

---

## 2026-04-04 — AI자문 프롬프트 고도화 + 포트폴리오 통합 + 버그 수정

### AI자문 프롬프트 고도화 (도메인 전문가 3명 자문)
- `advisory_service.py` 시스템 프롬프트: 재무 건전성 체크리스트, 적자 기업 규칙, PBR 역산 한계, 업종 상대평가, 체제별 투자 원칙 동적 삽입
- `advisory_service.py` 유저 프롬프트: `## 매크로 환경` 섹션 추가 (VIX/버핏/공포탐욕/체제/요구 안전마진)
- `advisory_service.py` 출력: `포지션가이드` 섹션 추가 (진입가/손절가/익절가/R:R/분할매수)
- `portfolio_advisor_service.py`: `_SYSTEM_PROMPT` → `_build_system_prompt(regime, cash_pct)` 함수화
  - 포지션 사이징 규칙 (단일 5%, 1회 30%, 현금 체제별), 손실 종목 3단계, urgency 3단계
  - 체제별 현금 비중 동적 삽입 (accumulation 25%/selective 35%/cautious 50%/defensive 75%)
  - trades JSON 확장: stop_loss, position_pct, urgency_reason
- `AIReportPanel.jsx`: 포지션가이드 4카드 섹션 (PosGuideCard 컴포넌트)
- `TradeTable.jsx`: 손절가/비중/긴급도 근거 컬럼 추가 (하위 호환)

### "AI자문" + "포트폴리오" 메뉴 통합
- `PortfolioPage.jsx` 재작성: 매크로 배너 + 자산 요약 + 차트 + AdvisorPanel(진단+리밸런싱+매매안) 통합
- `AdvisorPage.jsx` 라우트 제거 (App.jsx, Header.jsx)
- `BalancePage.jsx`: AdvisorPanel 제거 → "포트폴리오에서 AI 자문 보기 →" 링크
- Header: "AI자문" 메뉴 제거 (9개 메뉴)

### usePortfolioAdvisor 훅 재설계 (stale closure 버그 수정)
- `loadHistory()`: `[result]` 의존성 제거 → 이력 목록만 가져옴 (자동 리포트 로드 제거)
- `loadLatest()`: 마운트 시 최신 리포트 자동 로드 (신규)
- `analyze()`: `setResult(res)` 후 `loadHistory()` fire-and-forget (await 제거, 덮어쓰기 방지)

### max_completion_tokens 부족 버그 수정
- `advisory_service.py` + `portfolio_advisor_service.py`: 3500 → 8000
- 토큰 제한 잘림 감지 (`finish_reason == "length"` 로깅)
- JSON 파싱 실패 시 `ExternalAPIError` 반환 (빈 화면 대신 에러 메시지)
- `AdvisorPanel.jsx`: `analysis.raw` 존재 시 "다시 시도" 안내 표시

### 기타 버그 수정
- `cache.py`: aware/naive datetime 비교 TypeError → `.replace(tzinfo=None)` 통일
- `RegimeBanner.jsx`: `sentiment.buffett` → `sentiment.buffett_indicator` 필드명 수정
- `RegimeBanner.jsx`: `fg?.value` → `fg?.score` 우선 (실제 백엔드 필드)
- `TradeTable.jsx`: 매매근거 `truncate` 제거 → `whitespace-pre-line` 전체 표시
- `AdvisorPanel.jsx`: 링크 `/advisor` → `/portfolio`

---

## 2026-04-03 — 포트폴리오 대시보드

### 포트폴리오 대시보드 (`/portfolio`) 신규
- `PortfolioPage.jsx` — 5개 섹션 대시보드 (매크로 배너 + 자산 요약 + 배분 차트 + 수익률 바 + 보유종목)
- `usePortfolio.js` — balance + macro sentiment 병렬 로드 + Graham 안전마진 등급 프론트 계산
- `RegimeBanner.jsx` — 공포탐욕지수 기반 매크로 체제 배너 (공포/신중/중립/탐욕 4단계)
- `AllocationChart.jsx` — Recharts PieChart 자산 배분 (국내/해외/현금)
- `ProfitChart.jsx` — Recharts BarChart 종목별 수익률 비교
- `HoldingsOverview.jsx` — 보유 종목 테이블 + 안전마진 등급(A~D) + PER/PBR/ROE
- 신규 백엔드 없음 — 기존 `/api/balance` + `/api/macro/sentiment` API 100% 재활용
- Header 메뉴 추가 (10개)

---

## 2026-04-03 — AI 포트폴리오 자문 + 인프라 개선

### AI 포트폴리오 자문 기능 신규
- `services/portfolio_advisor_service.py` — 잔고 데이터 기반 GPT 포트폴리오 분석 (진단/리밸런싱/매매안)
- `routers/portfolio_advisor.py` — `POST /analyze`, `GET /history`, `GET /history/{id}` 3개 엔드포인트
- `stock/advisory_store.py` — `portfolio_reports` 테이블 추가 (자문 이력 영구 저장)
- `config.py` — `ADVISOR_CACHE_TTL_HOURS` 환경변수 (기본 0.5=30분)
- `stock/cache.py` — `ttl_hours` 타입 `int → float` (30분 TTL 지원)
- 프론트엔드: `AdvisorPage`(/advisor) + `AdvisorPanel`/`DiagnosisCard`/`RebalanceCard`/`TradeTable`/`TradeConfirmModal` 5개 컴포넌트
- `BalancePage` 하단에 AdvisorPanel 통합 + "AI자문 페이지에서 이력 보기" 링크
- 페이지 진입 시 최신 리포트 자동 로드 (이력 있으면 버튼 클릭 불필요)
- Header에 "AI자문" 메뉴 추가 (9개 메뉴)

### KST 타임존 통일
- `stock/db_base.py` — `KST`, `now_kst()`, `now_kst_iso()` 공용 헬퍼 신규
- `stock/cache.py` — `datetime.utcnow()` → `now_kst()` (캐시 만료 비교/저장)
- `stock/order_store.py` — `_now()` → `now_kst_iso()`
- `stock/advisory_store.py` — `datetime.now()` 4곳 → `now_kst_iso()`
- `stock/macro_store.py` — 자체 `_KST` 상수 제거, `db_base.KST` 공용 사용
- `services/macro_service.py` — `datetime.now(timezone.utc)` → `now_kst_iso()`
- `services/portfolio_advisor_service.py` — `datetime.now()` → `now_kst_iso()`
- 프론트: `EarningsPage`/`WatchlistDashboard` — `.toISOString()` → 로컬 날짜 헬퍼

### 관심종목 대시보드 속도 개선
- `services/watchlist_service.py` — 순차 for 루프 → `ThreadPoolExecutor` 병렬 (max 10 workers)
- `_fetch_dashboard_row()` 함수 추출, `time.sleep(0.05)` 제거
- 10종목 기준 12-30초 → 2-4초로 단축

### 기타
- `TradeTable` 매매근거 텍스트 잘림 수정 (`truncate` → `whitespace-pre-line`)
- `AdvisorPage` 불필요한 "잔고 새로고침" 버튼 제거

---

## 2026-04-03 — 시스템 리팩토링

### 시스템 리팩토링 (2026-04-03)

**HIGH (5건)**
- H1: `search.js`/`marketBoard.js` → `apiFetch()` 경유로 에러 처리 통일
- H2: `useAsyncState` 공통 훅 추출, 15개 훅 보일러플레이트 제거
- H3: `order_service.py`(1,338줄) → 4파일 분할 (order_service + order_kr/us/fno). Write-Ahead 패턴 dispatcher 중앙화
- H4: `quote_service.py`(964줄) → 3파일 분할 (quote_service + quote_kis + quote_overseas)
- H5: KIS 토큰 캐시 3곳 → `_kis_auth.py` 단일화 + TTL 관리

**MEDIUM (3건)**
- M2: `watchlist_service.py` silent `except: pass` 7건 → `logger.debug` 전환
- M5: 라우터 HTTPException 22건 → ServiceError 계층 통일. `ConflictError(409)` 신규
- M6: `advisory_fetcher.py` 기술지표 8개 순수 함수 → `stock/indicators.py` 분리

**LOW (1건)**
- L4: 미사용 import 정리 (Optional, math 등)

---

## 2026-04-03 — AI 에이전트 팀 (하네스) 구성

### 에이전트 7명 (`.claude/agents/`)

**도메인 전문가 4명:**
- `macro-sentinel.md` — 매크로 환경 분석 (버핏지수/VIX/공포탐욕 → 시장 체제 판단)
- `value-screener.md` — Graham 기준 PER/PBR/ROE 동적 필터 스크리닝
- `margin-analyst.md` — Graham Number + 재무 건전성 + 기술적 타이밍 심층 분석
- `order-advisor.md` — 포지션 사이징 + 지정가/손절/익절 주문 추천 (자동 주문 금지)

**빌더 3명:**
- `dev-architect.md` — 통합자산관리 풀스택 개발 (도메인 전문가 자문 기반)
- `qa-inspector.md` — 경계면 교차 비교 통합 정합성 검증
- `refactor-engineer.md` — 도메인 인지 리팩토링 (도메인 전문가 확인 후 변경)

### 스킬 9개 (`.claude/skills/`)
- `macro-analysis/` — MacroSentinel 전용: 매크로 데이터 수집 + 체제 판단
- `value-screening/` — ValueScreener 전용: Graham 멀티팩터 스크리닝
- `graham-analysis/` — MarginAnalyst 전용: 내재가치 + 재무 건전성 + 기술적 분석
- `portfolio-check/` — OrderAdvisor 전용: 포트폴리오 상태 + 포지션 사이징
- `order-recommend/` — OrderAdvisor 전용: 주문 추천 생성 + 예약주문 보조
- `value-invest/` — 오케스트레이터: 분석 파이프라인 (Macro→Screener→Analyst→Advisor)
- `asset-dev/` — 오케스트레이터: 개발 파이프라인 (자문→설계→구현→QA→보고)
- `qa-verify/` — QA Inspector 전용: 교차 비교 검증 체크리스트
- `refactor-audit/` — 오케스트레이터: 리팩토링 파이프라인 (감사→자문→실행→QA)

### 특징
- 기존 서비스 코드 변경 없음 — 에이전트는 기존 API 엔드포인트를 HTTP로 호출
- 도메인 전문가 4명이 분석/개발/리팩토링 3개 파이프라인 모두에서 자문 역할
- 워크스페이스 산출물: `_workspace/` 디렉토리에 단계별 JSON 파일 저장

---

## 2026-04-01 — 매크로 분석 페이지 신규

### 매크로 분석 (Macro Analysis) 메뉴 추가
- `stock/macro_fetcher.py`: yfinance 지수(KOSPI/KOSDAQ/S&P500/NASDAQ), RSS 뉴스, VIX/버핏지수/공포탐욕 심리지표, Google News 투자자 코멘트
- `services/macro_service.py`: 병렬 수집(ThreadPoolExecutor) + GPT 번역/추출 + 캐싱 오케스트레이션
- `routers/macro.py`: 5개 GET 엔드포인트 (`/api/macro/indices|news|sentiment|investor-quotes|summary`)
- `main.py`: macro 라우터 등록
- `requirements.txt`: `feedparser` 추가 (RSS 파싱)
- 프론트엔드: MacroPage + IndexSection(1년 스파크라인+툴팁) + SentimentSection + NewsSection + InvestorSection
- 데이터 소스: yfinance(지수/VIX/버핏), Google News RSS(한국 뉴스), NYT RSS + GPT 번역, Google News + GPT 추출(투자자 코멘트)
- 새 API 키 불필요 (기존 OPENAI_API_KEY만 활용, 없으면 영문 표시 graceful degradation)

---

## 2026-03-30 — FNO 캐싱 + 예약주문 수정 + DnD 순서변경

### FNO 마스터 인메모리 캐싱
- `stock/fno_master.py`: 인메모리 캐시(24h TTL) → cache.db(7일) → ZIP 다운로드 3단계 캐싱
- `main.py` lifespan: FNO pre-warm 추가 (기존 symbol_map 스레드에 병합)

### 예약주문 국내 시세 버그 수정
- `services/reservation_service.py`: `_fetch_current_price()` pykrx → `stock.market.fetch_price()` 교체
- pykrx KRX 서버 변경(2026-02-27) 이후 국내 가격조건 예약주문이 실패하던 문제 해결

### 시세판 드래그앤드롭 순서 변경
- `stock/market_board_store.py`: `market_board_order` 테이블 + `get_order()`/`save_order()`
- `routers/market_board.py`: `GET/PUT /api/market-board/order`
- 프론트엔드: `@dnd-kit/core` + `@dnd-kit/sortable` — 카드 그리드 DnD (`rectSortingStrategy`)
- `useDisplayStocks()`: orderMap 기반 정렬 + `reorder()` 낙관적 업데이트

### 관심종목 드래그앤드롭 순서 변경
- `stock/store.py`: `watchlist_order` 테이블 + `get_order()`/`save_order()`
- `routers/watchlist.py`: `GET/PUT /api/watchlist/order`
- 프론트엔드: 테이블 행 DnD (`verticalListSortingStrategy`) + 드래그 핸들(⠿)
- `useDashboard()`: orderMap 기반 정렬 + `reorder()` 낙관적 업데이트

---

## 시세 수신 개선 이력 (Phase 1 → Phase 4)

### Phase 1 (2026-03 완료)
- rAF throttle (`useQuote.js`): 고빈도 WS 메시지 → 최대 60fps 렌더링
- OrderbookPanel `useMemo` + `memo`: asks/bids/maxVolume 재계산 방지
- 지수 백오프 재연결 (클라이언트 500ms→10초, KIS WS 1→30초)
- `visibilitychange` 탭 복귀 즉시 재연결
- `OverseasQuoteManager`: 심볼당 단일 yfinance 폴링 태스크 (N 클라이언트 → 1 호출)
- 100ms 메시지 병합: 국내 WS 고빈도 메시지 → 최대 10건/초
- 장중/장외 TTL 분리 (`stock/market.py`): 국내 `fetch_price` 6분/6시간, `fetch_market_metrics` 1시간/12시간

### Phase 2 (2026-03 완료)
- `_is_us_trading_hours()` (`stock/market.py`): DST 자동 반영 (zoneinfo)
- `stock/yf_client.py` 장중 TTL 분리: `fetch_price_yf` 2분/30분, `fetch_detail_yf` 30분/6시간, `fetch_metrics_yf` 30분/6시간, `fetch_period_returns_yf` 15분/6시간
- **KIS REST fallback** (`KISQuoteManager`): WS 끊김 시 `FHKST01010100` 5초 폴링 자동 전환, WS 재연결 시 자동 해제. `_rest_fallback_loop()` + `_fetch_rest_price()`. 심볼 간 0.2초 throttle.
- **Finnhub WS** (`FinnhubWSClient` + `OverseasQuoteManager`): `FINNHUB_API_KEY` 설정 시 해외주식 실시간 체결가 수신 (무료 플랜 30 심볼). 한도 초과 심볼은 yfinance 폴링 fallback. 전일종가 prefetch로 change 계산.

### 환경변수 추가
- `FINNHUB_API_KEY`: 해외주식 실시간 시세 (선택). 미설정 시 yfinance 2초 폴링(15분 지연) 유지.

### Phase 3 (2026-03 완료)
- **신고가/신저가 그리드 밀도 개선** (`NewHighLowSection.jsx`): `md:grid-cols-4`, `lg:grid-cols-3` 추가. 외부 2컬럼 래퍼 안에서도 충분한 카드 밀도 확보.
- **비개장일 국내 시세 fallback** (`KISQuoteManager`): `subscribe()` 호출 즉시 `asyncio.create_task(_push_initial_price())` — yfinance `fetch_price(symbol)`로 직전 거래일 가격 queue push. `_fetch_rest_price()` KIS 반환 `price=0` 시 yfinance fallback.
- **비개장일 해외 시세 fallback** (`OverseasQuoteManager`): `_prefetch_and_subscribe()`에서 `fi.last_price or fi.previous_close` 패턴. `_poll_loop()`도 동일 패턴 적용, p=None이면 broadcast skip.
- **`fetch_price_yf()` fallback** (`stock/yf_client.py`): `close = _safe(fi.last_price) or _safe(fi.previous_close)` — 관심종목·잔고·AI자문용 해외 시세도 비개장일 직전 종가 반환.
- **FNO 실시간 WebSocket** (`KISQuoteManager` + `routers/quote.py`): FNO 심볼에 KIS WS 실시간 호가 지원 추가. `_FNO_TR_IDS` 상수 딕셔너리 + `_resolve_fno_type(symbol)` + `_send_subscribe_fno()`. `routers/quote.py`에 `?market=FNO` 쿼리 파라미터 추가 → `_stream_fno()` 핸들러로 분기. `useQuote(symbol, market='KR')` 시그니처 변경으로 프론트엔드 market 전달.
- **FNO 주문유형 확장** (`OrderForm.jsx`): 지정가만 지원하던 FNO 주문을 지정가/시장가/조건부지정가/최유리지정가 + IOC/FOK 조건으로 확장. `mapFnoOrderCodes()` 함수로 `ORD_DVSN_CD` 자동 계산. `OrderbookPanel`에서 FNO REST 폴링 제거 → `useQuote` 훅으로 통합.
- **`stock/utils.py` `is_fno(code)` 추가**: FNO 단축코드 식별 함수 추가.

### Phase 4 — 구조 개선 + WS 효율화 (2026-03 완료)
- **주문 도메인 계층 분리**: `routers/order.py`에서 `order_store` 직접 import 완전 제거. 이력 조회·예약주문·FNO 시세 모두 `order_service` 경유. 예약주문 `create_reservation()` 도메인 규칙 검증 추가.
- **주문 즉시 동기화**: `cancel_order()` → 로컬 DB 즉시 CANCELLED + `local_synced`/`order_status` 응답. `modify_order()` → 가격/수량 즉시 반영 + `local_synced`. `place_order()` → `balance_stale: true`.
- **대사 로직 강화**: `sync_orders()` → 체결+미체결 양쪽 조회, 양쪽 다 없으면 CANCELLED 자동 감지. `get_order_history()` 반환 전 자동 대사(best-effort).
- **SQLite WAL 모드**: `db_base.py`, `cache.py` — `PRAGMA journal_mode=WAL` + timeout 10초. 읽기-쓰기 동시성 향상.
- **예외 통일**: `_kis_auth.py`, `balance.py` — `HTTPException` → `ConfigError`/`ExternalAPIError` (ServiceError 계층 통일).
- **프론트엔드 계층 분리**: `MarketBoardPage.jsx` — api/ 직접 import 제거 → `useDisplayStocks()` 훅 사용.
- **Approval Key TTL**: `_get_approval_key()` — 12시간 TTL, 만료 시 자동 재발급.
- **REST Token TTL**: `_get_rest_token_sync()` — 12시간 TTL, 동일 패턴.
- **REST Fallback 최적화**: 폴링 주기 5초→3초, 심볼 간 throttle 0.2초→0.1초.
- **FNO 타입 캐싱**: `_fetch_fno_rest_price_sync()`에서 `_fno_types` dict 캐시 미스 시 결과 저장.
- **Queue Overflow 로깅**: `_broadcast()`에서 큐 만재 시 100건마다 경고 로그.
- **시세판 배칭 단축**: `market_board.py` — 500ms→200ms (호가 100ms와의 격차 축소).

---

## 버그 수정

### DART 공시 캐시 버그 수정 (2026-03)
- **원인**: `screener/cache.py`는 TTL 없는 영구 캐시. 당일 오전 조회 시 빈 결과가 캐시되면 이후 제출 공시가 보이지 않음 (골프존 3/19 사업보고서 미노출 사례)
- **수정**: `screener/dart.py`의 `fetch_filings()`에서 `end_date < today`인 경우만 캐시 사용. 오늘 이상 날짜 포함 범위는 항상 DART API 직접 호출.
