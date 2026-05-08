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
      backtest.js         fetchMcpStatus / fetchPresets / runPresetBacktest / runCustomBacktest / runBatchBacktest / fetchBacktestResult / fetchBacktestHistory / **fetchLocalPresets** / **runLocalBacktest** (2026-05-07 신규 2개) → /api/backtest/*
      strategyBuilder.js  convertBuilderToYaml / validateBuilderState / saveStrategy / loadStrategies / loadStrategy / deleteStrategy → /api/backtest/strategy/*
      tax.js              fetchTaxSummary(year) / fetchTaxTransactions / syncTax / recalculateTax(year) / fetchTaxCalculations(year,symbol) / addTaxTransaction / deleteTaxTransaction / fetchSimulationHoldings / simulateTax → /api/tax/* (FIFO 전용, 시뮬레이션 포함)
      admin.js            fetchAiUsage / fetchMyAiUsage / fetchAiLimits / setAiLimit / deleteAiLimit / fetchAuditLog → /api/admin/* (AI 사용량 관리). **(2026-05-04 Phase 4)** fetchUsers/fetchUserById/patchUser/deleteUser/fetchPageStats 추가.
      me.js               **(신규 2026-05-04 Phase 4)** getMyKis/saveMyKis/deleteMyKis/validateMyKis → /api/me/kis (사용자 본인 KIS 자격증명 등록/검증/삭제).
      chatbot.js          **(신규 2026-05-06)** chatAboutAdvisory(code, market, reportId, messages) / chatAboutPortfolio(reportId, messages) → 자문보고서·포트폴리오 보고서 컨텍스트 stateless 챗봇.
    hooks/
      useAsyncState.js    useAsyncState(initialData) — 비동기 data/loading/error 상태 관리 공통 훅. run(asyncFn)으로 자동 관리.
      useScreener.js      { data, loading, error, search }
      useEarnings.js      { data, loading, error, load(startDate, endDate, market) }
      useBalance.js       { data, loading, error, load }
      useWatchlist.js     useWatchlist (CRUD, market 파라미터) + useDashboard (순서+reorder) + useStockInfo
      useDetail.js        useDetailReport
      useOrder.js         useOrderPlace / useBuyable(load(symbol,market,price,orderType,side)) / useOpenOrders / useExecutions / useOrderHistory / useOrderSync / useReservations
      useNotification.js  토스트 상태 관리 + 브라우저 Notification API 래퍼
      useWebSocket.js     공용 WebSocket 훅. 연결 수명주기 + 지수 백오프 재연결(500ms→10초) + visibilitychange. { connected, sendMessage }. buildWsUrl(path) 헬퍼 export. **(2026-05-08 stale-token fix)** url 인자에 함수형 추가 — `connect()` 안에서 `typeof url === 'function' ? url() : url` lazy 평가. 1008 close 후 백오프 재시도 시점에 자동으로 신선한 access_token 반영(stale-token 무한 백오프 방지). 호출자는 함수 인스턴스를 모듈 const 또는 useCallback로 안정화 필수.
      useQuote.js         실시간 호가 WebSocket 훅 (useWebSocket 기반). **(2026-05-08 KRX+NXT+SOR)** `useQuote(symbol, market='KR', exchange='auto')` 3번째 파라미터 추가. `buildUrl`에 `&exchange=auto\|UN\|KRX\|NXT` 쿼리 자동 부착. 'auto' 기본 — 백엔드 KISQuoteManager 가 KST 시계 기반 4구간 자동 분기(08~09 NXT / 09~15:30 UN / 15:30~15:40 KRX / 15:40~20:00 NXT). rAF throttle 자체 관리.
      useExecutionNotice.js  체결통보(H0STCNI0) WS 수신 훅 (useWebSocket 기반). /ws/execution-notice 연결. execution_notice 메시지 콜백. **(2026-05-08)** `mapOrdExgGb(code)` 헬퍼 + 응답에 `exchange` 필드 추가(1=KRX/2=NXT/3=SOR-KRX/4=SOR-NXT, 누락 시 KRX 폴백). 토스트 메시지 거래소 prefix 표기에 사용.
      useMarketClock.js   **(신규 2026-05-08)** KST 시계 기반 KR 거래소 4구간 자동 판정 훅. `resolvePhaseByClock(now)` 순수 함수 export(테스트용). 1분 setInterval 폴링 + `/ws/market-status` 메시지 도착 시 override(정밀 trigger). 반환: `{exchange:'UN'\|'KRX'\|'NXT', label, isHoliday, isClosed, phase}`. 휴장 1차=주말, 2차=공휴일(v2), 3차=WS market-status. OrderbookPanel 헤더 거래소 라벨에 사용.
      useUsMarketClock.js  **(신규 2026-05-08, 공휴일 v2 2026-05-09)** ET 시계 기반 미국 시장 4구간 자동 판정 훅. `resolveUsPhaseByClock(now)` 순수 함수 export. `Intl.DateTimeFormat('en-US', {timeZone:'America/New_York'})` DST 자동. 1분 setInterval. 4구간: `pre`(04:00~09:30 ET) / `regular`(09:30~16:00) / `after`(16:00~20:00) / `closed`. 반환: `{phase, label, etTime, kstTime}`. **(2026-05-09 공휴일)** `US_HOLIDAYS_ET` 2026~2028 30일 + `isUsHoliday(dateString)` 헬퍼 — 주말 OR 공휴일이면 `phase: 'closed'`+`label: '휴장 (공휴일명)'`. 공휴일 종류: New Year/MLK/Presidents/Good Friday/Memorial/Juneteenth/Independence/Labor/Thanksgiving/Christmas. 단축 거래일(Black Friday 13:00 ET 조기마감 등) v3 보류. OrderbookPanel 헤더 미국 거래시간 라벨에 사용.
      useMarketBoard.js   useMarketBoard (신고가/신저가 + sparkline + ohlc) + useDisplayStocks (관심종목+별도등록 종목 병합+순서+reorder)
      useAdvisory.js      useAdvisoryStocks / useAdvisoryData / useAdvisoryReport / useAdvisoryOhlcv
      useMacro.js         useMacroIndices / useMacroNews / useMacroSentiment / useMacroInvestorQuotes (섹션별 독립 훅)
      usePortfolioAdvisor.js  포트폴리오 AI 자문 훅. analyze/loadLatest/loadById. stale closure 해결 (loadHistory 의존성 없음).
      useReport.js           투자 보고서 훅 5개. useReports/useReportDetail/useRecommendations/usePerformance/useRegimes.
      usePortfolio.js     포트폴리오 대시보드 훅. balance+sentiment 병렬 로드 + 자산배분/안전마진등급 계산.
      useBacktest.js      백테스트 훅. useMcpStatus(MCP연결상태) / usePresets(전략목록) / useBacktest(실행+3초폴링+결과, MAX_POLLS=200=10분) / useBacktestHistory(이력조회).
      useTax.js           양도세 훅. useTaxSummary / useTaxTransactions(sync/add/remove) / useTaxCalculations(recalc) / useTaxSimulation(loadHoldings/simulate). FIFO 전용.
      useAiUsage.jsx      **(신규 2026-05-06)** AI 사용량 전역 Context Provider. `fetchMyAiUsage()` 호출 + `'ai-usage-changed'` window 이벤트 자동 갱신(폴링 없음). 로그아웃 시 usage=null 클리어. `useAiUsage()`로 `{ usage, loading, refresh }` 접근.
    components/
      layout/Header.jsx   네비게이션 바 (5개 탑레벨: 시세판|관심종목|분석▼|포트폴리오|매매▼, 그룹 구분선, 드롭다운 hover+click). 모바일: 햄버거 메뉴(md:hidden) + 세로 네비게이션 패널. **(2026-05-06)** 우측 너비 토글 좌측에 `<AiUsageGauge />` 마운트.
      common/             LoadingSpinner, ErrorAlert, EmptyState, DataTable, ToastNotification
                          WatchlistButton (code/market/alreadyAdded props, ★/+ 버튼, StockTable·FilingsTable 공용)
                          CandlestickChart (ohlcv/indicators props, 캔들+MA5/20/60+BB+거래량, PriceChartPanel·TechnicalPanel 공용)
                          **AiUsageGauge** (신규 2026-05-06) — Header 우측 가로 24px 게이지바 + `used/limit` 수치 + 80%/95% 임계 색상(amber/red). useAiUsage 훅 사용. limit≤0이면 미렌더.
                          **ReportChatBubble** (신규 2026-05-06) — 우하단 플로팅 챗봇. props: `kind('advisory'|'portfolio')`/`contextId(reportId)`/`contextLabel`/`market`/`code`/`disabled`. 닫힘=원형 💬 버튼, 열림=`w-96 max-h-[70vh]` 카드(헤더+메시지 스크롤+예시 질문 칩 3개+textarea+전송). contextId 변경 시 messages 초기화. 응답 후 `dispatchEvent('ai-usage-changed')`. 모바일 풀폭(`right-6 left-4`).
                          **UserCommentInput** (신규 2026-05-07) — AI 분석 시작 전 사용자 가설 입력 textarea. props: `value`/`onChange`/`disabled`/`maxLength=1000`. 글자 수 카운터(0/1000), 80% 초과 amber, 100% 초과 red. AIReportPanel + AdvisorPanel 양쪽 액션바 위에 마운트.
      screener/           FilterPanel (구루 프리셋 드롭다운+체제 토글+guru_top), StockTable (섹터+52H대비+서준식 기대수익률+구루점수배지+Value Trap 경고)
      earnings/           FilingsTable (국내/미국 컬럼 분기, market prop)
      balance/            PortfolioSummary, HoldingsTable, OverseasHoldingsTable, FuturesTable
      watchlist/          AddStockForm (자동완성 검색, searchStocks API 사용), WatchlistDashboard, StockInfoModal
      detail/             StockHeader, FinancialTable, ValuationChart, ReportSummary,
                          KLineChartPanel (KLineChart 캔들차트, 타임프레임/기간/기술지표 토글),
                          klineTheme.js (한국식 색상 테마: 상승=빨강, 하락=파랑)
      order/              OrderForm, OrderConfirmModal, OpenOrdersTable, ModifyOrderModal,
                          ExecutionsTable, OrderHistoryTable, ReservationForm, ReservationsTable, SyncButton,
                          OrderbookPanel (실시간 호가창),
                          **ExchangeBadge** (신규 2026-05-08): 거래소 5종 배지(■KRX/◆NXT/⚡SOR/⚡SOR→KRX/⚡SOR→NXT) + size('xs'/'sm'). OpenOrdersTable·ExecutionsTable 거래소 컬럼 + 향후 OrderHistoryTable에서 공용. NULL/legacy 값은 KRX 폴백.
      advisory/           FundamentalPanel, TechnicalPanel, AIReportPanel (v3 통합: 6대비판분석+전략+시나리오. **(2026-05-07)** UserCommentInput 액션바 위 + UserCommentaryCard 본문 최상단 마운트), ResearchDataPanel (**입력데이터 통합 미리보기 16항목**: 기본/리서치 구분 제거. 사업개요/손익·BS·CF·분기/계량지표(PER·PBR·ROE·ROA·EPS·배당수익률·주당배당금·시총)/PER·PBR 5Y/10년 밴드/포워드추정/**증권사 컨센서스(목표가 중앙값·평균·dispersion·upside·매수보유매도 분포·5단계 모멘텀·과열 경고·6개월 추이·최근 5건 PDF 링크)**/기술시그널/KIS 퀀트/경영진/자본행위/업황/거시지표+**52주 위치(고가·저가·위치%·고점대비%)**. **(2026-05-07 버그수정)** `renderSegments` 키 mismatch 수정 — 백엔드 `{segment, revenue_pct, note}` ↔ 프론트 `s.name`/`s.ratio` 불일치로 `s.name||s` 폴백이 객체 자체를 React child로 넘겨 "Objects are not valid as a React child" 크래시 발생하던 버그 해소. `s.segment||s.name||s.product`+`s.revenue_pct ?? s.ratio ?? s.percentage ?? s.pct` 순으로 키 매핑, `s.note`는 작은 회색 라벨로 표시. keywords 배열 항목이 객체일 경우도 안전 처리. `hasData` 조건에 keywords-only 케이스 추가. **`MiniStat`/`Tr` 공용 안전망**: `_safeText()` 헬퍼로 객체 value를 `JSON.stringify`로 변환 → 향후 어떤 카테고리 응답이 객체로 오더라도 페이지 크래시 없이 폴백 표시.),
                          **UserCommentaryCard** (신규 2026-05-07) — 사용자 가설 양면 평가 카드. `evaluation` prop(user_comment/overall_stance/agree_points/disagree_points/summary). 헤더: 코멘트 원문 인용 + stance 5단계 배지(strong_agree=green/agree=lime/balanced=gray/disagree=amber/strong_disagree=red). 좌(👍 녹색)/우(👎 빨강) 2컬럼 + 항목별 strength 1~10 게이지 막대 + 하단 summary. 모바일 1컬럼 스택. evaluation null 시 미렌더,
                          AnalystReportsModal (증권사별 목표가+리포트 팝업, KR=네이버리서치/US=yfinance등급이력)
      report/             ReportDetailView (체제카드+지수+섹터추천+종목추천, v1 Markdown 폴백),
                          SectorConceptTabs (3컨셉 탭: 모멘텀/역발상/3개월선점, WatchlistButton+기등록 ★ 포함),
                          ReportHistoryList (과거 보고서 이력 카드, sector_summary 표시)
      portfolio/          RegimeBanner (매크로 체제 배너), AllocationChart (자산 배분 파이),
                          ProfitChart (종목별 수익률 바), HoldingsOverview (보유종목+안전마진 등급)
      advisor/            AdvisorPanel (포트폴리오 자문 컨테이너 + **개별 종목 리포트 연계 요약 카드**(가중등급+분포바+B미만 경고; weighted_grade_avg 부재 시 숨김)),
                          DiagnosisCard (진단 카드: 점수게이지+위험도+섹터분석 바),
                          **SectorRecommendationCard** (신규 섹터 진입 추천: 섹터명+목표비중+타이밍+대표종목→DetailPage 링크),
                          RebalanceCard (리밸런싱 제안), TradeTable (매매안+주문실행),
                          TradeConfirmModal (AI 추천 주문 확인 모달)
      backtest/           StrategySelector (탭 순서: **전략 빌더(기본)**→**MCP 프리셋**→**로컬 프리셋(2026-05-07 신규)**→커스텀 YAML. 프리셋 드롭다운+상세 설명 카드(description/category/tags/**파라미터 슬라이더**(min/max→range, fallback=number input)). CATEGORY_LABELS/CATEGORY_COLORS/PARAM_KR export. **PARAM_KR**: 80+개 파라미터 한글명+비유적 설명 매핑. **로컬 프리셋 탭**: `/api/backtest/local/presets` GET → 4개 KR 단기/추세 전략(상한가 모멘텀/변동성 돌파/20일 신고가 스윙/롱테일 변동성) 카드, MCP 무관), MetricsCard (수익률/샤프/낙폭/승률),
                          **SymbolMultiInput** (신규, 2026-05-07): 1~10개 종목 칩(chip) 선택. SymbolSearchBar 재사용+✕ 제거 버튼+카운터(N/10). 로컬 프리셋 모드에서만 사용,
                          BacktestResultPanel (**캔들차트+수익률곡선 이중축 통합차트**(OHLCV advisory API 별도 조회, 좌축=주가캔들+MA5/MA20, 우축=순자산 녹색선) + **거래량 바차트** + **보유구간 ReferenceArea**(수익=빨강/손실=파랑/보유중=회색) + 사용 파라미터 한글 표시 + **포지션요약**(6카드: 보유기간/수익거래/손실거래/연승/연패/승패분포) + **연간수익률**(테이블) + **월별수익률히트맵**(6단계 색상) + 거래내역(Buy=빨강/Sell=파랑)+매도수익률 자동계산. **원화 금액 Math.floor() 절사**(가격/순자산/Y축/툴팁). OHLCV 미조회 시 수익률곡선 전용 fallback. **(2026-05-07 로컬 백테스트)** 응답에 `per_symbol_contribution` 존재 시 종목별 기여도 카드 그리드 표시, 거래내역에 symbol 컬럼 추가, 로컬 거래(entry+exit 한 행)는 매수/매도 2행으로 펼침),
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
                          YieldCurveSection (**3단 레이아웃**: 1행 4금리 카드(grid-cols-4) → 2행 SpreadCard(10Y-3M 큰 숫자+역전 경고/정상)|수익률곡선 → 3행 10Y-3M 스프레드 추이 풀폭(h-80). NBER 침체(회색) + S&P -20% 약세장(붉은색) ReferenceArea 음영. 라벨 충돌 회피는 EventLabelsOverlay 위임),
                          CreditSpreadSection (FRED HY OAS **백분위 5단계 시계추**(extreme_greed/greed/normal/fear/extreme_fear)+백분위 축 게이지+절댓값 라벨 병기+5년차트(p10/p25/p75/p90 동적 ReferenceLine) + IG OAS·HY-IG 보조카드(>5%p 정크패닉). **(2026-05-05)** HYG/LQD ETF 수익률/비율 차트 폐기. 침체/약세장 음영은 EventLabelsOverlay 공유),
                          EventLabelsOverlay (**신규 2026-05-05**: `computeEventRows(events, chartPxWidth=600)` + `makeLabelRenderer({kind, displayLabel, row, fill})`. 시간 도메인 글로벌 row 계산(라벨 픽셀폭→시간폭 환산, 같은 kind 내 그리디 row 배정) + ReferenceArea label 콜백 헬퍼(viewBox 받아 row × 13px dy 적용). 침체/약세장 라벨 충돌 원천 차단),
                          CurrencySection (4환율 카드+스파크라인), CommoditySection (5원자재 카드+스파크라인),
                          SectorHeatmapSection (11섹터×5기간(1M/3M/6M/1Y/3Y) 히트맵, 초록~빨강 그라데이션, 상단에 SectorRelativeChart 마운트),
                          SectorRelativeChart (**신규 2026-05-05 R3**: ScatterChart, x=SMA20 cross 경과일 / y=1Y z-score, **데이터 기반 동적 도메인**(`max(|값|) × 1.18`, 최소 ±30일/±0.5σ), 4분면 음영, 14개 섹터 키워드 매칭 색상+아이콘(💻🏦⚕️⚡🏭🛍️🛒💡🏠⛏️📡🔋🚗🚚), 범례, dot 크기 110)
      tax/                TaxSummaryCards (4카드: 양도차익/공제/과세표준/세액), TaxBySymbolChart (종목별 BarChart),
                          TaxTransactionsTable (매매내역+수동추가), TaxCalculationDetail (FIFO lots 상세), TaxDisclaimer (면책배너),
                          TaxSimulationPanel (가상매도 시뮬레이션: 보유종목 선택+매도가/수량 입력+예상 세액)
    pages/
      DashboardPage.jsx   /         포트폴리오 요약(체제배너+자산현황+배분차트) + 오늘 공시
      ScreenerPage.jsx    /screener   구루 프리셋 6종(한글화) + 체제 배너 + 프리셋 배지 + 구루 점수 테이블(컬럼 툴팁) + DART 프리셋 시 항상 구루 컬럼 표시
      EarningsPage.jsx    /earnings  국내/미국 탭 선택 + 기간 조회
      BalancePage.jsx     /balance
      WatchlistPage.jsx   /watchlist
      DetailPage.jsx      /detail/:symbol  탭 UI (재무분석/종합 리포트[서브탭: 요약(CAGR+PER·PBR밸류에이션)/기본적분석/기술적분석/AI자문])
      OrderPage.jsx       /order     탭 UI (주문발송/미체결/체결내역/주문이력/예약주문)
      MarketBoardPage.jsx /market-board  시세판: 신고가/신저가 Top10 + 사용자 선택 종목. 실시간 WS. 당일 OHLC+미니캔들+전일대비가격+고저가.
      MacroPage.jsx       /macro         매크로 분석: 지수+심리+뉴스+투자자 코멘트. 4섹션 독립 로딩.
      PortfolioPage.jsx   /portfolio     포트폴리오 통합: 체제배너+자산배분+수익률+AI자문(진단+리밸런싱+매매안+이력). balance+macro+advisor 통합.
      ReportPage.jsx      /reports       데일리 추천: 페이지 진입 시 KR/US 파이프라인 자동실행(중복방지). 매크로 체제 카드(공유) + KR/US 토글 + 3컨셉 탑픽 섹터(모멘텀/역발상/3개월선점) + 종목추천+관심종목 버튼(기등록 ★ 표시). 하단 이력 카드(클릭→전환).
      BacktestPage.jsx    /backtest      KIS AI Extensions 백테스트: **전략빌더(기본탭)**/MCP 프리셋/**로컬 프리셋(2026-05-07 신규)**/커스텀 4모드, 빌더에서 바로 실행 가능. 결과 차트/메트릭, 전략 비교. **국내 KRX만 지원**(markets={['KR']}). **거래비용 입력**(수수료0.015%/세금0.23%/슬리피지0.05%). 진행 현황+백그라운드 안내. **이력 테이블**(마운트 시 로드, 완료 시 새로고침, 과거 결과 "보기" 클릭 → 결과패널). MCP 비활성화 시 안내 표시(빌더/MCP/커스텀 탭만 차단). 저장 전략 직접 실행. **(2026-05-05)** 가용 기간 가이드 박스(US ≥ 1998-01-02 / KR ≥ 2000-01-04 / 권장 1년~10년) + 시작/종료일 input min/max 속성. **(2026-05-07 로컬 프리셋 + 다중 종목)** `strategyMode === 'local-preset'`일 때 `<SymbolSearchBar>` 대신 `<SymbolMultiInput>` 렌더(1~10종목 칩) → `runLocalBacktest()` 호출. 균등 배분 자체 Python 일봉 엔진(MCP 무관). MCP 미연결 시 페이지 차단 → 노란색 안내 배너로 완화(로컬 프리셋은 MCP 불필요). 4 전략: 상한가 모멘텀/변동성 돌파/20일 신고가 스윙/롱테일 변동성.
      TaxPage.jsx         /tax           해외주식 양도소득세: 4탭(요약/매매내역/계산상세/시뮬레이션). FIFO 전용, 연도 선택, KIS 적응적 동기화+자동 재계산.
      AdminPage.jsx       /admin         **(2026-05-04 Phase 4 분할)** /admin → /admin/ai redirect 진입점. 관리 페이지는 3섹션으로 분리됨.
      AdminAIPage.jsx     /admin/ai      AI 관리 (admin only): 3탭(사용량 현황/한도 설정/감사 로그). 유저별 일별 사용량+서비스별 상세. 기본/개별 한도 CRUD. **(2026-05-04 Phase 4)** LimitsTab의 user_id 입력은 사용자 검색 콤보박스로 교체(`/api/admin/users?q=` 검색).
      AdminUsersPage.jsx  /admin/users   **(신규 2026-05-04 Phase 4)** 관리자 전용 사용자 CRUD. 검색/페이지네이션, role 변경, 비밀번호 reset, 삭제. **(2026-05-05 R4)** 방문수 컬럼(누적 PageView 카운트, locale toLocaleString).
      AdminPageStatsPage.jsx /admin/page-stats **(신규 2026-05-04 Phase 4)** 페이지별 이용현황 통계. Recharts 라인/바 차트(top 20 path), 기간 필터(7d/30d/90d), 평균/p95 latency.
      SettingsKisPage.jsx /settings/kis  **(신규 2026-05-04 Phase 4)** 사용자 본인 KIS 자격증명 등록/검증/삭제. 폼 6필드(app_key/app_secret/acnt_no/prdt_stk/prdt_fno?/hts_id?). 저장 시 즉시 검증(`POST /api/me/kis`) → ✓/✗ 표시.
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
- **WatchlistDashboard**: 종목명 클릭 → `/detail/:symbol`. 통화 배지 (US=`[US]`). 삭제/편집 시 market 파라미터 포함. 섹터 컬럼(종목명 우측). **(2026-05-03 Phase 2 QW-3)** `partial_failure: list[str]` 메타필드 표시 — 외부 API 부분 실패 영역(price/metrics/financials)은 회색 + ⚠ 마커 + tooltip "데이터 일시 미수집".
- **DetailPage**: StockHeader → **KLineChartPanel**(KLineChart 캔들차트, 타임프레임/기간/기술지표 토글) → 2탭 (재무분석/종합 리포트). 종합 리포트 내 4개 서브탭 (CAGR요약/기본적분석/기술적분석/AI자문). 밸류에이션(PER/PBR)은 기술적 분석 서브탭 하단에 내장 (1d/1wk만 표시). advisory 데이터는 최초 서브탭 진입 시 lazy load
- **OrderPage**: 5탭 UI. **공유 상태**(symbol/symbolName/market) 최상단 관리. `isMounted` ref로 중복 API 호출 방지. 미체결/체결 탭 MARKET_TABS: KR/US/FNO. **10초 자동 폴링**(미체결/체결 탭), **체결통보 WS** 수신 시 토스트+자동 갱신, 주문 발송 후 3초 딜레이 갱신
- **MarketBoardPage**: `useDisplayStocks` 훅 사용 (api/ 직접 import 금지). @dnd-kit 드래그앤드롭으로 종목 카드 순서 변경 가능 (DB 영속화)
- **WatchlistDashboard**: @dnd-kit 행 DnD로 종목 순서 변경. 드래그 핸들(⠿)로 클릭/편집과 분리

### 잔고 테이블 컬럼 순서

- **HoldingsTable(국내)**: 거래소 → 종목코드 → 종목명 → 투자비중(%) → 보유수량 → 평가금액 → 매입단가 → 현재가 → 평가손익 → 수익률 → 시가총액 → PER → ROE → PBR → 배당수익률 → 주문버튼
- **OverseasHoldingsTable(해외)**: 거래소 → 종목코드 → 종목명 → 투자비중(%) → 통화 → 보유수량 → 평가금액(외화) → 매입단가 → 현재가 → 평가손익(외화) → 평가손익(원화) → 수익률 → 시가총액 → PER → ROE → PBR → 배당수익률 → 주문버튼

### 주문 컴포넌트

- **SymbolSearchBar**: 시장 드롭다운(KR/US/FNO). `markets` prop으로 표시할 시장 필터링 가능 (기본: 전체). KR·FNO=자동완성, US=티커 직접 입력 검증. `marketRef`로 async race condition 방지
- **OrderbookPanel**: `useQuote(symbol, market, 'auto')` 훅 사용 (REST 폴링 없음). **(2026-05-08~09 US 분기 활성화)** KR/FNO/US 모두 동일 호가창 그리드 — `market !== 'US'` 가드 제거 → `showOrderbook` 항상 true. US 호가는 백엔드 OverseasQuoteManager가 KIS WS HDFSASP0 우선 + REST `HHDFS76200100` 2초 폴링 폴백을 자동 전환해 broadcast(국내와 동일 `{type:"orderbook", asks, bids, total_*_volume}` shape). 호가 단계 동적 표시(`displayAsks = asks.slice(0, asks.length || 10)`). 가격 포맷 — US는 `toFixed(2)` USD, KR/FNO는 정수. 매도호가 클릭→`side='sell'`, 매수호가 클릭→`side='buy'`. KR 종목은 `useMarketClock()` 결합 헤더 거래소 라벨(🟦 통합 09:00~15:30 / 🟢 NXT 08~09 또는 15:40~20 / 🟧 KRX 15:30~15:40 / 휴장). US 종목은 `useUsMarketClock()` 결합 헤더 거래시간 라벨(🟢 정규 ET 09:30~16:00 / 🟡 프리 04:00~09:30 / 🟠 애프터 16:00~20:00 / 휴장 — 주말+공휴일 30일).
- **OrderForm**: `symbol`/`symbolName`/`market` props 외부 제어. `externalPrice`/`externalSide` prop. FNO: 지정가/시장가/조건부지정가/최유리지정가 + IOC/FOK. **(2026-05-08 KRX+NXT+SOR)** `KR_EXCHANGE_OPTIONS = [SOR(추천)/KRX/NXT]` 거래소 셀렉터(market==='KR'만 노출). `isSimulation` prop 시 SOR/NXT 비활성+안내. 선택값은 `body.exchange`로 forward. 통합(UN)은 시세 전용 코드라 셀렉터 미노출. **(2026-05-08 US 매수가능 KRW 동시 표시)** market === 'US' 매수가능 라벨에 `매수가능: $X,XXX (₩X,XXX,XXX) · 환율 ₩1,XXX/USD` 형식. `fetchBuyable` 응답의 `buyable_amount_krw`/`usd_krw_rate` 필드 사용. 환율 조회 실패 시 USD만 표시(graceful degrade).
- **OpenOrdersTable** + **ExecutionsTable**: `excg_id_dvsn_cd === 'SOR'`(HTS/MTS 주문)은 "앱취소필요" 안내. **(2026-05-08)** "거래소" 컬럼 추가 + `ExchangeBadge` 사용(orders.exchange 또는 excg_id_dvsn_cd, NULL→KRX 폴백). KR 행에서만 렌더, US/FNO 행은 빈 셀.

### Advisory 컴포넌트

- **FundamentalPanel**: **사업 개요**(BusinessOverview: #키워드 + 사업설명 + 매출비중 파이차트) → **비즈니스 모델**(BusinessModelSection — 3카드: 💰 매출 흐름 / 💵 현금 창출 / 🔬 R&D 투자, `business_model` 모든 필드 빈 값이면 미렌더, 2026-05-06 추가) → 애널리스트 추정치(매출/순이익/EPS 현재E+차기E, **목표주가 클릭→AnalystReportsModal**) → 계량지표(10개: +EPS+안전마진가격) → 손익계산서(+추정치 바 반투명) → 대차대조표 → 현금흐름표
- **TechnicalPanel**: 타임프레임(15m/60m/1d/1wk) + 기간 선택. 시그널 카드 + 캔들스틱+MA+BB → 거래량 → MACD → RSI → Stochastic → PER/PBR 밸류에이션(1d/1wk만, `valuationData` prop + `fetchDetailValuation` API)
- **AIReportPanel**: **v2 등급 카드**(SafetyGradeBadge A/B+/B/C/D + ScoreBar 3개(등급28/복합100/정합성100) + Value Trap 배너 + recommendation 배지; v1 리포트 시 카드 숨김) → 종합투자의견 배지 → 전략별평가 3컬럼 카드(안전마진가격 표시) → 기술적시그널 → 리스크/투자포인트. **(2026-05-07)** 액션바 위 `<UserCommentInput>`(onUserCommentChange prop 있을 때만), 보고서 본문 최상단 `<UserCommentaryCard>`(reportData.user_commentary_evaluation 있을 때만)

> 컴포넌트 상세 → `docs/FRONTEND_SPEC.md`
