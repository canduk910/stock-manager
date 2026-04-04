# frontend/ — React SPA

React 19 + Vite + Tailwind CSS v4 + Recharts. 네이티브 fetch 사용 (외부 HTTP 라이브러리 없음).

## 디렉토리 구조

```
frontend/
  index.html
  package.json
  vite.config.js          /api/* → localhost:8000 프록시, /ws → ws://localhost:8000 (WebSocket)
  src/
    main.jsx
    App.jsx               BrowserRouter + Routes
    index.css             @import "tailwindcss"
    api/
      client.js           fetch 래퍼 (에러 처리)
      screener.js
      earnings.js         fetchFilings(startDate, endDate, market="KR")
      balance.js
      watchlist.js        addToWatchlist(code, memo, market) / removeFromWatchlist(code, market) 등
      detail.js           10년 재무 + 밸류에이션 + 종합 리포트
      order.js            placeOrder / fetchOpenOrders / cancelOrder / modifyOrder / fetchExecutions /
                          fetchBuyable(symbol, market, price, orderType, side) /
                          fetchFnoPrice(symbol, mrktDiv) → GET /api/order/fno-price
      advisory.js         fetchAdvisoryStocks / addAdvisoryStock / removeAdvisoryStock /
                          refreshAdvisoryData(code, market, name) / fetchAdvisoryData / generateReport /
                          fetchReport / fetchReportHistory(code, market, limit) / fetchReportById(code, id, market) /
                          fetchAdvisoryOhlcv(code, market, interval, period)
      search.js           searchStocks(q, market) → GET /api/search
      macro.js            fetchMacroIndices / fetchMacroNews / fetchMacroSentiment / fetchMacroInvestorQuotes / fetchMacroSummary
      advisor.js          analyzePortfolio / fetchAdvisorHistory / fetchAdvisorReport → /api/portfolio-advisor/*
    hooks/
      useAsyncState.js    useAsyncState(initialData) — 비동기 data/loading/error 상태 관리 공통 훅. run(asyncFn)으로 자동 관리.
      useScreener.js      { data, loading, error, search }
      useEarnings.js      { data, loading, error, load(startDate, endDate, market) }
      useBalance.js       { data, loading, error, load }
      useWatchlist.js     useWatchlist (CRUD, market 파라미터) + useDashboard (순서+reorder) + useStockInfo
      useDetail.js        useDetailReport
      useOrder.js         useOrderPlace / useBuyable(load(symbol,market,price,orderType,side)) / useOpenOrders / useExecutions / useOrderHistory / useOrderSync / useReservations
      useNotification.js  토스트 상태 관리 + 브라우저 Notification API 래퍼
      useWebSocket.js     공용 WebSocket 훅. 연결 수명주기 + 지수 백오프 재연결(500ms→10초) + visibilitychange. { connected, sendMessage }. buildWsUrl(path) 헬퍼 export.
      useQuote.js         실시간 호가 WebSocket 훅 (useWebSocket 기반). useQuote(symbol, market='KR'). rAF throttle 자체 관리.
      useExecutionNotice.js  체결통보(H0STCNI0) WS 수신 훅 (useWebSocket 기반). /ws/execution-notice 연결. execution_notice 메시지 콜백.
      useMarketBoard.js   useMarketBoard (신고가/신저가 + sparkline) + useDisplayStocks (관심종목+별도등록 종목 병합+순서+reorder)
      useAdvisory.js      useAdvisoryStocks / useAdvisoryData / useAdvisoryReport / useAdvisoryOhlcv
      useMacro.js         useMacroIndices / useMacroNews / useMacroSentiment / useMacroInvestorQuotes (섹션별 독립 훅)
      usePortfolioAdvisor.js  포트폴리오 AI 자문 훅. analyze/loadLatest/loadById. stale closure 해결 (loadHistory 의존성 없음).
      usePortfolio.js     포트폴리오 대시보드 훅. balance+sentiment 병렬 로드 + 자산배분/안전마진등급 계산.
    components/
      layout/Header.jsx   네비게이션 바 (5개 탑레벨: 포트폴리오|분석▼|관심종목|매매▼|시세판, 드롭다운 hover)
      common/             LoadingSpinner, ErrorAlert, EmptyState, DataTable, ToastNotification
                          WatchlistButton (code/market/alreadyAdded props, ★/+ 버튼, StockTable·FilingsTable 공용)
                          CandlestickChart (ohlcv/indicators props, 캔들+MA5/20/60+BB+거래량, PriceChartPanel·TechnicalPanel 공용)
      screener/           FilterPanel, StockTable
      earnings/           FilingsTable (국내/미국 컬럼 분기, market prop)
      balance/            PortfolioSummary, HoldingsTable, OverseasHoldingsTable, FuturesTable
      watchlist/          AddStockForm, WatchlistDashboard, StockInfoModal
      detail/             StockHeader, FinancialTable, ValuationChart, ReportSummary
      order/              OrderForm, OrderConfirmModal, OpenOrdersTable, ModifyOrderModal,
                          ExecutionsTable, OrderHistoryTable, ReservationForm, ReservationsTable, SyncButton,
                          OrderbookPanel (실시간 호가창)
      advisory/           FundamentalPanel, TechnicalPanel, AIReportPanel
      portfolio/          RegimeBanner (매크로 체제 배너), AllocationChart (자산 배분 파이),
                          ProfitChart (종목별 수익률 바), HoldingsOverview (보유종목+안전마진 등급)
      advisor/            AdvisorPanel (포트폴리오 자문 컨테이너), DiagnosisCard (진단 게이지+섹터),
                          RebalanceCard (리밸런싱 제안), TradeTable (매매안+주문실행),
                          TradeConfirmModal (AI 추천 주문 확인 모달)
      macro/              IndexSection (4지수+1년스파크라인+툴팁), SentimentSection (VIX+버핏+공포탐욕),
                          NewsSection (한국+NYT 2컬럼), InvestorSection (4명 투자자 코멘트 카드)
    pages/
      DashboardPage.jsx   /         포트폴리오 요약(체제배너+자산현황+배분차트) + 오늘 공시
      ScreenerPage.jsx    /screener
      EarningsPage.jsx    /earnings  국내/미국 탭 선택 + 기간 조회
      BalancePage.jsx     /balance
      WatchlistPage.jsx   /watchlist
      DetailPage.jsx      /detail/:symbol  탭 UI (재무분석/종합 리포트[서브탭: CAGR요약/기본적분석/기술적분석(+PER·PBR)/AI자문])
      OrderPage.jsx       /order     탭 UI (주문발송/미체결/체결내역/주문이력/예약주문)
      MarketBoardPage.jsx /market-board  시세판: 신고가/신저가 Top10 + 사용자 선택 종목. 실시간 WS.
      MacroPage.jsx       /macro         매크로 분석: 지수+심리+뉴스+투자자 코멘트. 4섹션 독립 로딩.
      PortfolioPage.jsx   /portfolio     포트폴리오 통합: 체제배너+자산배분+수익률+AI자문(진단+리밸런싱+매매안+이력). balance+macro+advisor 통합.
```

---

## UI 규칙 (필수)

### 색상/포맷

- **한국 관례**: 상승 = 빨간색, 하락 = 파란색
- **시가총액 포맷**: KRW=억/조, USD=M/B/T (프론트에서 처리)
- **PER/PBR**: `Math.floor()` 정수 표시 (StockHeader, StockInfoModal 등)
- **매입단가**: 국내주식 `Math.floor()` 정수, 해외주식 소수점 2자리 고정
- **통화 단위**: FinancialTable — USD면 M USD 기준(1,000M→$B, 1,000,000M→$T), KRW는 억/조

### 공용 컴포넌트

- **DataTable**: 모든 컬럼 헤더 클릭 시 정렬 (⇅ 아이콘, asc/desc 토글, 숫자/문자 자동 구분). `renderContext` prop으로 외부 의존성 전달. `sortable: false` 설정 지원.
- **WatchlistButton**: `common/WatchlistButton` 사용 — StockTable·FilingsTable 공용
- **CandlestickChart**: `common/CandlestickChart` — PriceChartPanel·TechnicalPanel 공용

### 페이지별 규칙

- **ScreenerPage**: "조회하기" 버튼 클릭 시만 API 호출 (onChange 즉시 호출 안 함)
- **EarningsPage**: 국내/미국 탭 선택 → 조회 시 필터 초기화. 종목명/종목코드 클라이언트 사이드 필터
- **BalancePage**: 국내/해외/선물옵션 3섹션 분리. 국내는 항상 표시, FNO는 `fno_enabled`일 때 표시(빈 목록이면 EmptyState). KIS 키 없으면 안내 메시지 (에러 대신)
- **WatchlistDashboard**: 종목명 클릭 → `/detail/:symbol`. 통화 배지 (US=`[US]`). 삭제/편집 시 market 파라미터 포함
- **DetailPage**: 2탭 구조 (재무분석/종합 리포트). 종합 리포트 내 4개 서브탭 (CAGR요약/기본적분석/기술적분석/AI자문). 밸류에이션(PER/PBR)은 기술적 분석 서브탭 하단에 내장 (1d/1wk만 표시). advisory 데이터는 최초 서브탭 진입 시 lazy load
- **OrderPage**: 5탭 UI. **공유 상태**(symbol/symbolName/market) 최상단 관리. `isMounted` ref로 중복 API 호출 방지. 미체결/체결 탭 MARKET_TABS: KR/US/FNO. **10초 자동 폴링**(미체결/체결 탭), **체결통보 WS** 수신 시 토스트+자동 갱신, 주문 발송 후 3초 딜레이 갱신
- **MarketBoardPage**: `useDisplayStocks` 훅 사용 (api/ 직접 import 금지). @dnd-kit 드래그앤드롭으로 종목 카드 순서 변경 가능 (DB 영속화)
- **WatchlistDashboard**: @dnd-kit 행 DnD로 종목 순서 변경. 드래그 핸들(⠿)로 클릭/편집과 분리

### 잔고 테이블 컬럼 순서

- **HoldingsTable(국내)**: 거래소 → 종목코드 → 종목명 → 투자비중(%) → 보유수량 → 평가금액 → 매입단가 → 현재가 → 평가손익 → 수익률 → 시가총액 → PER → ROE → PBR → 배당수익률 → 주문버튼
- **OverseasHoldingsTable(해외)**: 거래소 → 종목코드 → 종목명 → 투자비중(%) → 통화 → 보유수량 → 평가금액(외화) → 매입단가 → 현재가 → 평가손익(외화) → 평가손익(원화) → 수익률 → 시가총액 → PER → ROE → PBR → 배당수익률 → 주문버튼

### 주문 컴포넌트

- **SymbolSearchBar**: 시장 드롭다운(KR/US/FNO). KR·FNO=자동완성, US=티커 직접 입력 검증. `marketRef`로 async race condition 방지
- **OrderbookPanel**: `useQuote(symbol, market)` 훅 사용 (REST 폴링 없음). KR/FNO=동일 호가창 그리드. US=현재가만. 매도호가 클릭→`side='sell'`, 매수호가 클릭→`side='buy'`
- **OrderForm**: `symbol`/`symbolName`/`market` props 외부 제어. `externalPrice`/`externalSide` prop. FNO: 지정가/시장가/조건부지정가/최유리지정가 + IOC/FOK
- **OpenOrdersTable**: `excg_id_dvsn_cd === 'SOR'`(HTS/MTS 주문)은 "앱취소필요" 안내

### Advisory 컴포넌트

- **FundamentalPanel**: **사업 개요**(BusinessOverview: #키워드 + 사업설명 + 매출비중 파이차트) → 애널리스트 추정치 → 계량지표 → 손익계산서 → 대차대조표 → 현금흐름표
- **TechnicalPanel**: 타임프레임(15m/60m/1d/1wk) + 기간 선택. 시그널 카드 + 캔들스틱+MA+BB → 거래량 → MACD → RSI → Stochastic → PER/PBR 밸류에이션(1d/1wk만, `valuationData` prop + `fetchDetailValuation` API)
- **AIReportPanel**: 종합투자의견 배지 → 전략별평가 3컬럼 카드 → 기술적시그널 → 리스크/투자포인트

> 컴포넌트 상세 → `docs/FRONTEND_SPEC.md`
