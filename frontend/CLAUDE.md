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
      backtest.js         fetchMcpStatus / fetchPresets / runPresetBacktest / runCustomBacktest / runBatchBacktest / fetchBacktestResult / fetchBacktestHistory → /api/backtest/*
      strategyBuilder.js  convertBuilderToYaml / validateBuilderState / saveStrategy / loadStrategies / loadStrategy / deleteStrategy → /api/backtest/strategy/*
      tax.js              fetchTaxSummary(year) / fetchTaxTransactions / syncTax / recalculateTax(year) / fetchTaxCalculations(year,symbol) / addTaxTransaction / deleteTaxTransaction / fetchSimulationHoldings / simulateTax → /api/tax/* (FIFO 전용, 시뮬레이션 포함)
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
      useMarketBoard.js   useMarketBoard (신고가/신저가 + sparkline + ohlc) + useDisplayStocks (관심종목+별도등록 종목 병합+순서+reorder)
      useAdvisory.js      useAdvisoryStocks / useAdvisoryData / useAdvisoryReport / useAdvisoryOhlcv
      useMacro.js         useMacroIndices / useMacroNews / useMacroSentiment / useMacroInvestorQuotes (섹션별 독립 훅)
      usePortfolioAdvisor.js  포트폴리오 AI 자문 훅. analyze/loadLatest/loadById. stale closure 해결 (loadHistory 의존성 없음).
      useReport.js           투자 보고서 훅 5개. useReports/useReportDetail/useRecommendations/usePerformance/useRegimes.
      usePortfolio.js     포트폴리오 대시보드 훅. balance+sentiment 병렬 로드 + 자산배분/안전마진등급 계산.
      useBacktest.js      백테스트 훅. useMcpStatus(MCP연결상태) / usePresets(전략목록) / useBacktest(실행+3초폴링+결과, MAX_POLLS=200=10분) / useBacktestHistory(이력조회).
      useTax.js           양도세 훅. useTaxSummary / useTaxTransactions(sync/add/remove) / useTaxCalculations(recalc) / useTaxSimulation(loadHoldings/simulate). FIFO 전용.
    components/
      layout/Header.jsx   네비게이션 바 (5개 탑레벨: 시세판|관심종목|분석▼|포트폴리오|매매▼, 그룹 구분선, 드롭다운 hover+click). 모바일: 햄버거 메뉴(md:hidden) + 세로 네비게이션 패널
      common/             LoadingSpinner, ErrorAlert, EmptyState, DataTable, ToastNotification
                          WatchlistButton (code/market/alreadyAdded props, ★/+ 버튼, StockTable·FilingsTable 공용)
                          CandlestickChart (ohlcv/indicators props, 캔들+MA5/20/60+BB+거래량, PriceChartPanel·TechnicalPanel 공용)
      screener/           FilterPanel (구루 프리셋 드롭다운+체제 토글+guru_top), StockTable (섹터+52H대비+서준식 기대수익률+구루점수배지+Value Trap 경고)
      earnings/           FilingsTable (국내/미국 컬럼 분기, market prop)
      balance/            PortfolioSummary, HoldingsTable, OverseasHoldingsTable, FuturesTable
      watchlist/          AddStockForm (자동완성 검색, searchStocks API 사용), WatchlistDashboard, StockInfoModal
      detail/             StockHeader, FinancialTable, ValuationChart, ReportSummary,
                          KLineChartPanel (KLineChart 캔들차트, 타임프레임/기간/기술지표 토글),
                          klineTheme.js (한국식 색상 테마: 상승=빨강, 하락=파랑)
      order/              OrderForm, OrderConfirmModal, OpenOrdersTable, ModifyOrderModal,
                          ExecutionsTable, OrderHistoryTable, ReservationForm, ReservationsTable, SyncButton,
                          OrderbookPanel (실시간 호가창)
      advisory/           FundamentalPanel, TechnicalPanel, AIReportPanel (v3 통합: 6대비판분석+전략+시나리오), ResearchDataPanel (입력데이터 미리보기)
      report/             ReportDetailView (체제카드+지수+섹터추천+종목추천, v1 Markdown 폴백),
                          SectorConceptTabs (3컨셉 탭: 모멘텀/역발상/3개월선점, WatchlistButton 포함),
                          ReportHistoryList (과거 보고서 이력 카드, sector_summary 표시)
      portfolio/          RegimeBanner (매크로 체제 배너), AllocationChart (자산 배분 파이),
                          ProfitChart (종목별 수익률 바), HoldingsOverview (보유종목+안전마진 등급)
      advisor/            AdvisorPanel (포트폴리오 자문 컨테이너 + **개별 종목 리포트 연계 요약 카드**(가중등급+분포바+B미만 경고; weighted_grade_avg 부재 시 숨김)),
                          DiagnosisCard (진단 카드: 점수게이지+위험도+섹터분석 바),
                          **SectorRecommendationCard** (신규 섹터 진입 추천: 섹터명+목표비중+타이밍+대표종목→DetailPage 링크),
                          RebalanceCard (리밸런싱 제안), TradeTable (매매안+주문실행),
                          TradeConfirmModal (AI 추천 주문 확인 모달)
      backtest/           StrategySelector (탭 순서: **전략 빌더(기본)**→프리셋 전략→커스텀 YAML. 프리셋 드롭다운+상세 설명 카드(description/category/tags/**파라미터 슬라이더**(min/max→range, fallback=number input)). CATEGORY_LABELS/CATEGORY_COLORS/PARAM_KR export. **PARAM_KR**: 80+개 파라미터 한글명+비유적 설명 매핑), MetricsCard (수익률/샤프/낙폭/승률),
                          BacktestResultPanel (**캔들차트+수익률곡선 이중축 통합차트**(OHLCV advisory API 별도 조회, 좌축=주가캔들+MA5/MA20, 우축=순자산 녹색선) + **거래량 바차트** + **보유구간 ReferenceArea**(수익=빨강/손실=파랑/보유중=회색) + 사용 파라미터 한글 표시 + **포지션요약**(6카드: 보유기간/수익거래/손실거래/연승/연패/승패분포) + **연간수익률**(테이블) + **월별수익률히트맵**(6단계 색상) + 거래내역(Buy=빨강/Sell=파랑)+매도수익률 자동계산. **원화 금액 Math.floor() 절사**(가격/순자산/Y축/툴팁). OHLCV 미조회 시 수익률곡선 전용 fallback),
                          backtestUtils.js (순수 계산 유틸: computeAnnualReturns/computeMonthlyReturns/computePositionSummary),
                          AnnualReturnsTable, MonthlyReturnsHeatmap, PositionSummary (결과 상세 컴포넌트),
                          BatchCompareTable (전략 비교),
                          BacktestHistoryTable (이력 테이블: 일시/종목(**코드+이름**)/카테고리(**한글배지**)/전략(**MCP display name 우선**)/수익률/샤프/낙폭/상태/**파라미터 펼침**/삭제/보기. builder/custom 전략은 지표+파라미터 형식으로 표시)
      strategy-builder/   StrategyBuilder (5단계 스테퍼 메인 컨테이너, 리스크 최소1개 필수 검증, 전략완성→전략저장 하단 네비 통합), StepMetadata/StepIndicators/StepConditions/StepRisk/StepPreview (각 단계 UI, StepPreview는 요약+YAML+검증결과만 표시),
                          IndicatorCard/IndicatorPickerModal (지표 카드+모달, 83개 지표+66종 캔들패턴),
                          ConditionCard/ConditionGroupCard/OperandSelector (조건 빌더),
                          StrategyListPanel (저장된 전략 목록+프리셋 6개),
                          strategyBuilderConstants.js (지표/캔들패턴 카탈로그, 연산자, 프리셋),
                          useStrategyBuilder.js (빌더 상태 관리 훅)
      macro/              IndexSection (4지수+1년스파크라인+툴팁), SentimentSection (VIX+버핏+공포탐욕),
                          NewsSection (한국+NYT 2컬럼), InvestorSection (4명 투자자 코멘트 카드),
                          MacroCycleSection (4단계 경기국면 다이어그램+**투자체제 나란히 표시**+괴리설명+confidence+지표카드+hover 툴팁),
                          YieldCurveSection (수익률곡선 LineChart+스프레드 시계열 AreaChart),
                          CreditSpreadSection (HYG/LQD 스프레드+비율 시계열),
                          CurrencySection (4환율 카드+스파크라인), CommoditySection (5원자재 카드+스파크라인),
                          SectorHeatmapSection (11섹터×4기간 히트맵, 초록~빨강 그라데이션)
      tax/                TaxSummaryCards (4카드: 양도차익/공제/과세표준/세액), TaxBySymbolChart (종목별 BarChart),
                          TaxTransactionsTable (매매내역+수동추가), TaxCalculationDetail (FIFO lots 상세), TaxDisclaimer (면책배너),
                          TaxSimulationPanel (가상매도 시뮬레이션: 보유종목 선택+매도가/수량 입력+예상 세액)
    pages/
      DashboardPage.jsx   /         포트폴리오 요약(체제배너+자산현황+배분차트) + 오늘 공시
      ScreenerPage.jsx    /screener   구루 프리셋 6종(한글화) + 체제 배너 + 프리셋 배지 + 구루 점수 테이블(컬럼 툴팁) + DART 프리셋 시 항상 구루 컬럼 표시
      EarningsPage.jsx    /earnings  국내/미국 탭 선택 + 기간 조회
      BalancePage.jsx     /balance
      WatchlistPage.jsx   /watchlist
      DetailPage.jsx      /detail/:symbol  탭 UI (재무분석/종합 리포트[서브탭: CAGR요약/기본적분석/기술적분석(+PER·PBR)/AI자문])
      OrderPage.jsx       /order     탭 UI (주문발송/미체결/체결내역/주문이력/예약주문)
      MarketBoardPage.jsx /market-board  시세판: 신고가/신저가 Top10 + 사용자 선택 종목. 실시간 WS. 당일 OHLC+미니캔들+전일대비가격+고저가.
      MacroPage.jsx       /macro         매크로 분석: 지수+심리+뉴스+투자자 코멘트. 4섹션 독립 로딩.
      PortfolioPage.jsx   /portfolio     포트폴리오 통합: 체제배너+자산배분+수익률+AI자문(진단+리밸런싱+매매안+이력). balance+macro+advisor 통합.
      ReportPage.jsx      /reports       투자 보고서: 페이지 진입 시 KR/US 파이프라인 자동실행(중복방지). 매크로 체제 카드(공유) + KR/US 토글 + 3컨셉 탑픽 섹터(모멘텀/역발상/3개월선점) + 종목추천+관심종목 버튼. 하단 이력 카드(클릭→전환).
      BacktestPage.jsx    /backtest      KIS AI Extensions 백테스트: **전략빌더(기본탭)**/프리셋/커스텀 3모드, 빌더에서 바로 실행 가능. 결과 차트/메트릭, 전략 비교. **국내 KRX만 지원**(markets={['KR']}). **거래비용 입력**(수수료0.015%/세금0.23%/슬리피지0.05%). 진행 현황+백그라운드 안내. **이력 테이블**(마운트 시 로드, 완료 시 새로고침, 과거 결과 "보기" 클릭 → 결과패널). MCP 비활성화 시 안내 표시. 저장 전략 직접 실행.
      TaxPage.jsx         /tax           해외주식 양도소득세: 4탭(요약/매매내역/계산상세/시뮬레이션). FIFO 전용, 연도 선택, KIS 적응적 동기화+자동 재계산.
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

- **ScreenerPage**: "조회하기" 버튼 클릭 시만 API 호출 (onChange 즉시 호출 안 함). 구루 프리셋(greenblatt/neff/seo) 선택 시 DART enrichment 자동 활성화. 체제 연계(regime_aware) 기본 ON → 상단 체제 배너 표시. 서준식 기대수익률은 항상 컬럼 표시, 구루 점수/Value Trap은 DART enrichment 시에만 표시
- **EarningsPage**: 국내/미국 탭 선택 → 조회 시 필터 초기화. 종목명/종목코드 클라이언트 사이드 필터
- **BalancePage**: 국내/해외/선물옵션 3섹션 분리. 국내는 항상 표시, FNO는 `fno_enabled`일 때 표시(빈 목록이면 EmptyState). KIS 키 없으면 안내 메시지 (에러 대신)
- **WatchlistDashboard**: 종목명 클릭 → `/detail/:symbol`. 통화 배지 (US=`[US]`). 삭제/편집 시 market 파라미터 포함. 섹터 컬럼(종목명 우측)
- **DetailPage**: StockHeader → **KLineChartPanel**(KLineChart 캔들차트, 타임프레임/기간/기술지표 토글) → 2탭 (재무분석/종합 리포트). 종합 리포트 내 4개 서브탭 (CAGR요약/기본적분석/기술적분석/AI자문). 밸류에이션(PER/PBR)은 기술적 분석 서브탭 하단에 내장 (1d/1wk만 표시). advisory 데이터는 최초 서브탭 진입 시 lazy load
- **OrderPage**: 5탭 UI. **공유 상태**(symbol/symbolName/market) 최상단 관리. `isMounted` ref로 중복 API 호출 방지. 미체결/체결 탭 MARKET_TABS: KR/US/FNO. **10초 자동 폴링**(미체결/체결 탭), **체결통보 WS** 수신 시 토스트+자동 갱신, 주문 발송 후 3초 딜레이 갱신
- **MarketBoardPage**: `useDisplayStocks` 훅 사용 (api/ 직접 import 금지). @dnd-kit 드래그앤드롭으로 종목 카드 순서 변경 가능 (DB 영속화)
- **WatchlistDashboard**: @dnd-kit 행 DnD로 종목 순서 변경. 드래그 핸들(⠿)로 클릭/편집과 분리

### 잔고 테이블 컬럼 순서

- **HoldingsTable(국내)**: 거래소 → 종목코드 → 종목명 → 투자비중(%) → 보유수량 → 평가금액 → 매입단가 → 현재가 → 평가손익 → 수익률 → 시가총액 → PER → ROE → PBR → 배당수익률 → 주문버튼
- **OverseasHoldingsTable(해외)**: 거래소 → 종목코드 → 종목명 → 투자비중(%) → 통화 → 보유수량 → 평가금액(외화) → 매입단가 → 현재가 → 평가손익(외화) → 평가손익(원화) → 수익률 → 시가총액 → PER → ROE → PBR → 배당수익률 → 주문버튼

### 주문 컴포넌트

- **SymbolSearchBar**: 시장 드롭다운(KR/US/FNO). `markets` prop으로 표시할 시장 필터링 가능 (기본: 전체). KR·FNO=자동완성, US=티커 직접 입력 검증. `marketRef`로 async race condition 방지
- **OrderbookPanel**: `useQuote(symbol, market)` 훅 사용 (REST 폴링 없음). KR/FNO=동일 호가창 그리드. US=현재가만. 매도호가 클릭→`side='sell'`, 매수호가 클릭→`side='buy'`
- **OrderForm**: `symbol`/`symbolName`/`market` props 외부 제어. `externalPrice`/`externalSide` prop. FNO: 지정가/시장가/조건부지정가/최유리지정가 + IOC/FOK
- **OpenOrdersTable**: `excg_id_dvsn_cd === 'SOR'`(HTS/MTS 주문)은 "앱취소필요" 안내

### Advisory 컴포넌트

- **FundamentalPanel**: **사업 개요**(BusinessOverview: #키워드 + 사업설명 + 매출비중 파이차트) → 애널리스트 추정치(매출/순이익/EPS 현재E+차기E) → 계량지표(10개: +EPS+안전마진가격) → 손익계산서(+추정치 바 반투명) → 대차대조표 → 현금흐름표
- **TechnicalPanel**: 타임프레임(15m/60m/1d/1wk) + 기간 선택. 시그널 카드 + 캔들스틱+MA+BB → 거래량 → MACD → RSI → Stochastic → PER/PBR 밸류에이션(1d/1wk만, `valuationData` prop + `fetchDetailValuation` API)
- **AIReportPanel**: **v2 등급 카드**(SafetyGradeBadge A/B+/B/C/D + ScoreBar 3개(등급28/복합100/정합성100) + Value Trap 배너 + recommendation 배지; v1 리포트 시 카드 숨김) → 종합투자의견 배지 → 전략별평가 3컬럼 카드(안전마진가격 표시) → 기술적시그널 → 리스크/투자포인트

> 컴포넌트 상세 → `docs/FRONTEND_SPEC.md`
