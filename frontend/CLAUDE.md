# frontend/ — React SPA

React 19 + Vite + Tailwind CSS v4 + Recharts. 네이티브 fetch 사용 (외부 HTTP 라이브러리 없음).

> 변경 이력은 `docs/CHANGELOG.md`가 단일 출처. 본 문서는 디렉토리 구조와 영구 UI 규칙만 기술.

## 디렉토리 구조

```
frontend/
  index.html
  package.json
  vite.config.js          /api/* → localhost:8000 프록시, /ws → ws://localhost:8000
  src/
    main.jsx
    App.jsx               BrowserRouter + Routes + AiUsageProvider
    index.css             @import "tailwindcss"
```

### `src/api/` — REST 모듈 (fetch 래퍼)

| 파일 | 엔드포인트 |
|------|-----------|
| `client.js` | fetch 래퍼 + 401 인터셉터 자동 token refresh |
| `screener.js` | /api/screener |
| `earnings.js` | fetchFilings(startDate, endDate, market) |
| `balance.js` | `fetchBalance(accountLabel?)` — null/undefined 시 합산 모드 (/api/balance), 라벨 지정 시 단독 (`?account_label=`) |
| `watchlist.js` | CRUD + market 파라미터 |
| `detail.js` | 10년 재무 + 밸류에이션 + 종합 리포트 |
| `order.js` | placeOrder/fetchOpenOrders/cancelOrder/modifyOrder/fetchExecutions/fetchBuyable/fetchFnoPrice |
| `advisory.js` | fetchAdvisoryStocks/addAdvisoryStock/refreshAdvisoryData/generateReport(userComment)/fetchReport/fetchReportHistory/fetchReportById/fetchAdvisoryOhlcv/**fetchStockSupplyDemand**(code, days)/**fetchForeignHolding**(code, days=120) |
| `search.js` | searchStocks(q, market) |
| `macro.js` | fetchMacroIndices/fetchMacroNews/fetchMacroSentiment/fetchMacroInvestorQuotes/fetchMacroSummary/**fetchSupplyDemand**(market, days) |
| `advisor.js` | analyzePortfolio(userComment)/fetchAdvisorHistory/fetchAdvisorReport |
| `backtest.js` | fetchMcpStatus/fetchPresets/runPresetBacktest/runCustomBacktest/runBatchBacktest/fetchBacktestResult/fetchBacktestHistory/fetchLocalPresets/runLocalBacktest |
| `strategyBuilder.js` | convert/validate/save/load/list/delete (/api/backtest/strategy/*) |
| `tax.js` | fetchTaxSummary/fetchTaxTransactions/syncTax/recalculateTax/fetchTaxCalculations/addTaxTransaction/deleteTaxTransaction/fetchSimulationHoldings/simulateTax |
| `admin.js` | fetchAiUsage/fetchMyAiUsage/fetchAiLimits/setAiLimit/deleteAiLimit/fetchAuditLog/fetchUsers/fetchUserById/patchUser/deleteUser/fetchPageStats/**fetchUserAccessHistory(user_id, days, top_paths)** |
| `me.js` | **멀티 계좌**: `listAccounts/createAccount/updateAccount(label)/deleteAccount(label)/setDefaultAccount(label)/validateAccount(label)` + 백워드 호환 `getMyKis/saveMyKis/deleteMyKis/validateMyKis` (/api/me/kis) |
| `chatbot.js` | chatAboutAdvisory(code, market, reportId, messages)/chatAboutPortfolio(reportId, messages) |

### `src/hooks/`

| 파일 | 책임 |
|------|------|
| `useAsyncState.js` | data/loading/error 공통 훅. `run(asyncFn)` 자동 관리 |
| `useScreener/useEarnings/useBalance/useWatchlist/useDetail/useOrder/useNotification` | 각 도메인 데이터 훅. **`useDetailBundle(symbol, market)`** (in `useDetail.js`) — DetailPage 마운트 시 `/api/detail/{symbol}/bundle` 1회 호출로 모든 섹션 일괄 수신, 부분 실패는 `data.partial_failure`로 표시 (기존 N+1 useDetailReport 패턴 대체) |
| `useWebSocket.js` | 공용 WS 훅. 지수 백오프 재연결(500ms→10s) + visibilitychange. **url 인자에 함수형 지원** — `connect()` 안에서 lazy 평가, 1008 close 후 재시도 시 신선한 access_token 자동 반영 (stale-token 무한 백오프 방지). 호출자는 모듈 함수 또는 useCallback로 안정 reference 전달. **2026-05-18: 1008 자동 logout 가드** — `_tryRefreshForWs()` 모듈 싱글톤 promise로 refresh 시도 → 성공 시 backoff 리셋 + 즉시 재연결 / 실패 시 localStorage 클리어 + `/login` 리다이렉트 (client.js 401 정책과 일치, JWT 만료 stale-token 무한 백오프 차단) |
| `useQuote.js` | 실시간 호가 WS. `useQuote(symbol, market='KR', exchange='auto')`. exchange 쿼리 자동 부착. rAF throttle 자체 관리. `type:"error"` 메시지 수신 시 `errorMessage` state 노출 (백엔드 KIS 키 미설정 등 silent failure 차단) |
| `useExecutionNotice.js` | 체결통보(H0STCNI0) WS 수신. `mapOrdExgGb(code)` 헬퍼로 응답에 `exchange` 필드 (1=KRX/2=NXT/3=SOR-KRX/4=SOR-NXT, NULL→KRX 폴백) |
| `useMarketClock.js` | KST 4구간 KR 거래소 자동 판정 (`UN`/`KRX`/`NXT`). `resolvePhaseByClock(now)` 순수 함수 export. 1분 setInterval **단독 (WS override 제거 — `/ws/market-status` 폐지로 시계 폴백만 사용)** |
| `useUsMarketClock.js` | ET 4구간 미국 시장 (`pre`/`regular`/`after`/`closed`). `Intl.DateTimeFormat('en-US', {timeZone:'America/New_York'})` DST 자동. `US_HOLIDAYS_ET` 2026~2028 30일 + `isUsHoliday()` 헬퍼 (주말+공휴일) |
| `useMarketBoard.js` | useMarketBoard (신고가/신저가 + sparkline + ohlc) + useDisplayStocks (관심+별도등록 병합+순서) + **usePricePolling(codes, market)** — `fetchPricesBatch` 폴링(`useMarketClock` phase 기반 장중 15s / 장외 60s 자동 조정). 기존 WS prices shape 호환 (`{[code]: {price, change, change_pct, prev_close, volume, sign}}`) |
| `useAdvisory.js` | useAdvisoryStocks/useAdvisoryData/useAdvisoryReport/useAdvisoryOhlcv/**useStockSupplyDemand**(code, days)/**useForeignHolding**(code, days=120) |
| `useMacro.js` | 섹션별 독립 훅 (Indices/News/Sentiment/InvestorQuotes/**SupplyDemand(market, days)**). 부분 실패 격리 |
| `usePortfolioAdvisor.js` | analyze/loadLatest/loadById. stale closure 해결 (loadHistory 의존성 없음) |
| `useReport.js` | 5개 훅 (Reports/ReportDetail/Recommendations/Performance/Regimes) |
| `usePortfolio.js` | balance+sentiment 병렬 + 자산배분/안전마진 등급 계산 |
| `useBacktest.js` | useMcpStatus/usePresets/useBacktest(3초 폴링 MAX_POLLS=200=10분)/useBacktestHistory/useLocalPresets/runLocal |
| `useTax.js` | useTaxSummary/useTaxTransactions/useTaxCalculations/useTaxSimulation. FIFO 전용 |
| `useAiUsage.jsx` | AI 사용량 전역 Context. `fetchMyAiUsage()` + `'ai-usage-changed'` window 이벤트 자동 갱신(폴링 없음). 로그아웃 시 클리어 |

### `src/components/`

**layout/**
- `Header.jsx` — 5개 탑레벨 네비 (시세판/관심종목/분석▼/포트폴리오/매매▼). 모바일 햄버거. 우측 너비 토글 좌측에 `<AiUsageGauge />`. `<header>` sticky `top-0 z-40`

**common/**
- `LoadingSpinner`, `ErrorAlert`, `EmptyState`, `DataTable`, `ToastNotification`
- `WatchlistButton` (code/market/alreadyAdded props, ★/+, StockTable·FilingsTable 공용)
- `CandlestickChart` (캔들+MA5/20/60+BB+거래량, PriceChartPanel·TechnicalPanel 공용)
- `AiUsageGauge` — 가로 24px 게이지바 + `used/limit` + 80% amber/95% red. limit≤0 미렌더
- `ReportChatBubble` — 우하단 플로팅 챗봇. props: `kind('advisory'|'portfolio')`/`contextId`/`contextLabel`/`market`/`code`/`disabled`. 응답 후 `ai-usage-changed` dispatch. 모바일 풀폭
- `UserCommentInput` — AI 분석 시작 전 사용자 가설 textarea. `maxLength=1000` 카운터, 80%/100% 임계 amber/red

**screener/** FilterPanel + StockTable
**earnings/** FilingsTable (KR/US 컬럼 분기)
**balance/** PortfolioSummary, HoldingsTable, OverseasHoldingsTable, FuturesTable
**watchlist/** AddStockForm (자동완성), WatchlistDashboard, StockInfoModal
**detail/** StockHeader, FinancialTable, ValuationChart, ReportSummary, KLineChartPanel + klineTheme.js (한국식: 상승=빨강, 하락=파랑)

**order/**
- OrderForm, OrderConfirmModal, OpenOrdersTable, ModifyOrderModal, ExecutionsTable, OrderHistoryTable, ReservationForm, ReservationsTable, SyncButton
- OrderbookPanel (실시간 호가창)
- `ExchangeBadge` — 거래소 5종 배지(■KRX/◆NXT/⚡SOR/⚡SOR→KRX/⚡SOR→NXT) + size('xs'/'sm'). NULL/legacy → KRX 폴백
- `SymbolSearchBar`, `SymbolMultiInput`(1~10 칩, 로컬 백테스트용)

**advisory/**
- FundamentalPanel, TechnicalPanel
- AIReportPanel — v3 통합 (6대 비판분석+전략+시나리오). `<UserCommentInput>` 액션바 위 + `<UserCommentaryCard>` 본문 최상단
- ResearchDataPanel — 입력데이터 16카테고리 통합 미리보기. `_safeText()` 객체 안전 렌더 + `renderSegments` 키 매핑(`s.segment||s.name||s.product`)
- `UserCommentaryCard` — 사용자 가설 양면 평가. stance 5단계 배지 + 좌(👍 녹색)/우(👎 빨강) 2컬럼 + strength 1~10 게이지. evaluation null 미렌더
- AnalystReportsModal (KR=네이버리서치/US=yfinance 등급이력)
- **SupplyDemandPanel** — 종합리포트 5번째 서브탭("수급/투자자") 본체. Recharts ComposedChart(개인/외국인/기관 일별 막대 + 누적 라인). 상단 advisory_note 노란 배너(통일 문구). 매수/매도 분리 토글. 해외종목 진입 시 "국내 전용" 안내. KIS 키 미설정 503 → 안내 카드. 하단에 `<ForeignHoldingCard />` 통합
- **ForeignHoldingCard** — 외국인 보유율 + 추가 매수여력. 좌(도넛 게이지 스냅샷, 임계값 4단계 색상 safe/caution/warning/saturated + unlimited/exceeded 배지 + 4지표 그리드: 보유/상장/한도/잔여여력) + 우(소진율 추이 라인 차트, 30일 이하 MM-DD / 90일 이상 YYYY-MM 자동 포맷 + 임계값 ReferenceLine). 5단계 stepper(30/60/90/120/180, 기본 120). `change_alert.breached` 시 라인 #F97316 강조 + 배지. 콜드스타트(`daily_history_total_days < days`) 시 "데이터 누적 중" 노란 안내(매일 18:00 cron으로 자연 누적). 해외 종목 미렌더. KIS 키 503/외부 502/404 부분 실패 격리(V1 차트 무영향)

**report/** ReportDetailView, SectorConceptTabs(3컨셉 + WatchlistButton + 기등록 ★), ReportHistoryList
**portfolio/** RegimeBanner, AllocationChart, ProfitChart, HoldingsOverview
- **ProfitChart**: 보유 종목 수익률 가로 막대(이익 빨강/손실 파랑). 전체 종목 표시(slice 제거) + 동적 height(`Math.max(260, len*26+20)`) + Y축 너비 자동(`min(200, max(80, maxNameLen*11+12))`)으로 종목명 잘림 차단. `YAxis interval={0}` 모든 라벨 강제. 헤더에 `(N종목)` 카운트
**advisor/** AdvisorPanel, DiagnosisCard, SectorRecommendationCard, RebalanceCard, TradeTable, TradeConfirmModal
- **DiagnosisCard**: 점수 게이지 + 위험도 + 요약 + 집중도/통화/섹터. **섹터 분석은 도넛 파이차트 + 평가 리스트 좌우 분할** (md:flex-row, 모바일 세로 스택). 14색 cycle 팔레트, Tooltip에 섹터/비중/assessment 동시 표시, 외부 라벨 `${sector} ${weight_pct}%` (truncate 제거로 잘림 없음). **우측 범례 두 그룹 구성**: ① 보유 섹터 — `classifyAssessment()`로 편중("편중/과잉/과다" → orange ⚠)/부족("부족/미흡/낮음" → yellow ↓)/적정(기본 → green ✓) 배지 색상 코딩. ② ⭐ 신규 편입 추천 — `recommendations` prop(`analysis.sector_recommendations`)에서 보유 섹터 차감한 미보유 섹터만 표시, 점선 emerald 테두리 + 목표 비중 + 진입 타이밍(immediate/this_week/this_month) 배지 + 추천 근거 line-clamp-2

**backtest/**
- StrategySelector — 4탭 순서: 전략빌더(기본) → MCP 프리셋 → 로컬 프리셋 → 커스텀 YAML. 프리셋 드롭다운+상세(파라미터 슬라이더). `PARAM_KR` 80+ 한글명 매핑. **`allowedModes` prop** — 단위 토글(종목/포트폴리오)이 화이트리스트 전달, 외 탭 자동 숨김
- MetricsCard, BacktestResultPanel (캔들+수익률곡선 이중축 + 거래량 바 + 보유구간 ReferenceArea + 포지션요약 6카드 + 연간/월별 수익률 + 거래내역. `per_symbol_contribution` 시 종목별 카드. 원화 `Math.floor()` 절사)
- backtestUtils.js (computeAnnualReturns/computeMonthlyReturns/computePositionSummary)
- AnnualReturnsTable, MonthlyReturnsHeatmap, PositionSummary, BatchCompareTable
- BacktestHistoryTable (일시/종목/카테고리/전략/수익률/샤프/낙폭/상태/파라미터/삭제/보기). 다종목(`symbols.length>1`)이면 종목 컬럼에 "포트폴리오 (N종목)" + 앞 3개 칩 미리보기 + "보기" → 모달
- **BacktestPortfolioModal** — 다종목 백테스트 상세. 헤더(일시·전략·기간·수익률·샤프·MDD 4메트릭) → 종목 칩 리스트(`symbols_names` 기반 코드+명) → per_symbol_contribution 테이블(거래수/수익률/기여도) → 파라미터 JSON. ESC + 백드롭 클릭 닫기. 단일 종목 행은 기존 동작 유지

**strategy-builder/**
- StrategyBuilder (5단계 스테퍼, 리스크 최소1개 필수)
- StepMetadata/StepIndicators/StepConditions/StepRisk/StepPreview
- IndicatorCard/IndicatorPickerModal (83개 지표 + 66종 캔들패턴)
- ConditionCard/ConditionGroupCard/OperandSelector
- StrategyListPanel (저장된 전략 + 프리셋 6개)
- strategyBuilderConstants.js, useStrategyBuilder.js

**macro/**
- IndexSection, SentimentSection (VIX+버핏+F&G), NewsSection (한국+NYT 2컬럼), InvestorSection
- **SupplyDemandSection** — 코스피/코스닥 토글(SectorHeatmap KR/US 패턴 차용) + 10~60일 슬라이더. Recharts ComposedChart(개인/외국인/기관 일별 막대 + 누적 라인) + 당일 요약 칩(외국인 +X억 / 기관 -Y억 / 개인 +Z억). KIS 키 미설정 503/외부 API 502 → 부분 실패 안내 카드(다른 섹션 무영향). IndexSection 직후 마운트
- MacroCycleSection (4단계 + 투자체제 나란히 + 괴리설명 + confidence + 지표카드)
- YieldCurveSection — 3단 레이아웃: 4금리 카드 → SpreadCard|곡선 → **10Y-3M 스프레드 + 10Y 금리 듀얼 축 추이** 풀폭 (h-80, ComposedChart). 좌축=스프레드 Area(0% ReferenceLine), 우축=10Y 금리 Line(#6366f1), Legend 자동 구분. NBER 침체+S&P 약세장 ReferenceArea 음영(spread 좌축 yAxisId)
- CreditSpreadSection — HY OAS 백분위 5단계 시계추 + 5년차트(p10/p25/p75/p90 ReferenceLine) + IG OAS·HY-IG 보조카드(>5%p 정크패닉)
- EventLabelsOverlay — `computeEventRows` + `makeLabelRenderer`. 글로벌 row 계산으로 침체/약세장 라벨 충돌 차단
- CurrencySection (4환율), CommoditySection (5원자재)
- SectorHeatmapSection — 상단 KR/US 토글(ReportPage 패턴) + 부제로 분류 기준 명시. 좌(산점도) + 우(히트맵 테이블) `lg:grid-cols-2` 좌우 분할(모바일은 세로 스택). 시장 전환 시 펼친 섹터 자동 닫힘. 섹터명 클릭 시 대표종목 5개 펼침
- SectorRelativeChart (산점도, x=`🟢 골든크로스/🔴 데드크로스 N일째`, y=`평균 대비 ±σ`, 동적 도메인). 4분면 한국식 라벨: ↗ 추세 가속 / ↖ 전환 직전 / ↘ 추세 약화 / ↙ 약세 가속. 각 분면 안쪽에 큰 컨셉 라벨 + 우상단 2x2 범례 + 하단 회색 박스 정의 설명
- sectorRepresentatives.js — KR_SECTOR_REPS(KODEX/TIGER ETF 14개 직접 매핑) + SECTOR_REPS(US GICS 11카테고리). KR은 ETF symbol 직접 룩업 우선, US는 GICS 카테고리. `getPrimaryReps(sector)` / `getAllReps(sector)` / `resolveCategory(sector)` 공용 헬퍼

**tax/** TaxSummaryCards (4카드), TaxBySymbolChart, TaxTransactionsTable, TaxCalculationDetail (FIFO lots), TaxDisclaimer, TaxSimulationPanel

### `src/pages/`

| 페이지 | 라우트 | 비고 |
|--------|--------|------|
| DashboardPage | `/` | 포트폴리오 요약 + 오늘 공시 |
| ScreenerPage | `/screener` | 구루 프리셋 6종 + 체제 배너 |
| EarningsPage | `/earnings` | KR/US 탭 |
| BalancePage | `/balance` | **상단 탭 [전체\|라벨1\|라벨2\|...]** + KR/US/FNO 3섹션. 탭 라벨은 마운트 시 `listAccounts()`로 별도 fetch(단독 탭 응답 메타 1개로 탭 사라짐 방지). 전체 탭=합산(useBalance(null)), 라벨 탭=단독(useBalance(label)). 합산 시 종목 row에 `accounts:['주식','연금']` 메타 표시 |
| WatchlistPage | `/watchlist` | |
| DetailPage | `/detail/:symbol` | 재무분석/종합 리포트 (서브탭 5개: 요약/기본적/기술적/AI자문/**수급·투자자**) |
| OrderPage | `/order` | 5탭 (주문/미체결/체결/이력/예약) |
| MarketBoardPage | `/market-board` | 시세판 (**REST 일괄 폴링** — yfinance 일괄 → KIS REST 폴백. `useMarketBoardWS` 폐지 → `usePricePolling`로 교체, 장중 15s / 장외 60s) |
| MacroPage | `/macro` | 매크로 분석 |
| PortfolioPage | `/portfolio` | 통합 (체제+배분+수익+AI자문) |
| ReportPage | `/reports` | 데일리 추천 (KR/US 토글, 3컨셉 탑픽) |
| BacktestPage | `/backtest` | **단위 토글(종목/포트폴리오)** segment control이 전략 탭 자동 제한: 종목→빌더/MCP/커스텀 3탭+SymbolSearchBar(단일), 포트폴리오→로컬프리셋 단독+SymbolMultiInput(1~10). 전환 시 state 보존(재전환 시 복원). KR만. 거래비용 입력. 가용 기간 가이드 (US ≥ 1998-01-02 / KR ≥ 2000-01-04) |
| TaxPage | `/tax` | 4탭 (요약/매매/계산/시뮬레이션) |
| AdminPage | `/admin` | → `/admin/ai` redirect |
| AdminAIPage | `/admin/ai` | 3탭 (사용량/한도/감사). LimitsTab user_id는 사용자 검색 콤보 |
| AdminUsersPage | `/admin/users` | CRUD + 방문수 컬럼. **방문수 셀 클릭 또는 "이력" 버튼 → `UserAccessHistoryModal`** (사용자별 일별 접속현황 — Recharts ComposedChart로 PV 막대 + 고유 path 라인 보조축, 7/30/90/180일 토글, 상위 path 리스트) |
| AdminPageStatsPage | `/admin/page-stats` | Recharts (top 20 path), 7d/30d/90d, 평균/p95 latency |
| SettingsKisPage | `/settings/kis` | **멀티 계좌 카드 그리드** + 모달 등록/수정/삭제 + 기본 계좌 지정 + 재검증. 카드: 라벨/마스킹 계좌번호/검증 상태/"기본" 배지. 라벨 + 6필드(app_key, app_secret, acnt_no, acnt_prdt_cd_stk, acnt_prdt_cd_fno?, hts_id?, base_url). **계좌상품코드 default 제거** — 사용자가 의식적으로 입력(일반 01 / 연금·IRP·ISA 02·22 등 KIS 발급값) |

---

## UI 규칙 (필수)

### 색상/포맷
- **한국 관례**: 상승 = 빨강, 하락 = 파랑
- **시가총액**: KRW=억/조, USD=M/B/T
- **PER/PBR**: `Math.floor()` 정수 표시
- **매입단가**: KR 정수, US 소수점 2자리 고정
- **통화**: FinancialTable — USD면 M USD 기준(1,000M→$B, 1,000,000M→$T), KRW는 억/조

### 공용 컴포넌트
- **DataTable**: 헤더 클릭 정렬 (⇅, asc/desc, 숫자/문자 자동). `renderContext` prop으로 외부 의존 전달. `sortable: false` 지원. `stickyHeader` prop(default false): true 시 부모 `overflow-x-auto` 제거 + `<thead>` `sticky top-14 z-20 shadow-sm` (페이지 헤더 56px 아래 고정). 가로 스크롤 필요한 테이블은 비활성. ScreenerPage `StockTable`에서 활성화.
- **WatchlistButton**: `common/WatchlistButton` — StockTable·FilingsTable 공용
- **CandlestickChart**: `common/CandlestickChart` — PriceChartPanel·TechnicalPanel 공용

### 페이지별 규칙
- **ScreenerPage**: "조회하기" 버튼 클릭 시만 호출 (onChange 즉시 X). 구루 프리셋(greenblatt/neff/seo) 선택 시 DART enrichment 자동. 체제 연계(regime_aware) 기본 ON
- **EarningsPage**: KR/US 탭 → 조회 시 필터 초기화. 클라이언트 사이드 필터
- **BalancePage**: KR/US/FNO 3섹션. KR 항상 표시, FNO는 `fno_enabled`일 때. KIS 키 없으면 안내 메시지 (에러 대신). **멀티 계좌 탭**: `listAccounts()`로 탭 라벨 별도 fetch(`data.accounts` 의존 X — 단독 모드 응답은 메타 1개라 탭 사라짐), useBalance(activeTab) 분기. partial_failure 노란 배너 표시
- **WatchlistDashboard**: 종목명 클릭 → `/detail/:symbol`. 통화 배지 (US=`[US]`). `partial_failure` 표시 — 외부 API 부분 실패 영역(price/metrics/financials)은 회색 + ⚠ + tooltip "데이터 일시 미수집". @dnd-kit 드래그핸들(⠿) 행 DnD
- **DetailPage**: StockHeader → KLineChartPanel → 2탭. 종합 리포트 5개 서브탭(요약/기본적/기술적/AI자문/수급·투자자). advisory + 수급은 lazy load
- **OrderPage**: 5탭. 공유 상태(symbol/symbolName/market) 최상단. `isMounted` ref 중복 호출 방지. 10초 자동 폴링(미체결/체결), 체결통보 WS 수신 시 토스트+갱신, 발송 후 3초 딜레이 갱신
- **MarketBoardPage**: `useDisplayStocks` 훅 (api/ 직접 import 금지). @dnd-kit 카드 순서 (DB 영속). **가격 갱신은 `usePricePolling(polledCodes, 'KR')` REST 폴링** — KIS WS 다중구독 폐지(자동매매 동시구독 41건 충돌 해소)

### 잔고 테이블 컬럼 순서
- **HoldingsTable(KR)**: 거래소 → 종목코드 → 종목명 → 비중 → 보유수량 → 평가금액 → 매입단가 → 현재가 → 평가손익 → 수익률 → 시총 → PER → ROE → PBR → 배당수익률 → 주문
- **OverseasHoldingsTable(US)**: 거래소 → 종목코드 → 종목명 → 비중 → 통화 → 보유수량 → 평가금액(외화) → 매입단가 → 현재가 → 평가손익(외화) → 평가손익(원화) → 수익률 → 시총 → PER → ROE → PBR → 배당수익률 → 주문

### 주문 컴포넌트
- **SymbolSearchBar**: 시장 드롭다운(KR/US/FNO). `markets` prop으로 필터. KR·FNO=자동완성, US=티커 직접 입력. `marketRef` async race 방지
- **OrderbookPanel**: `useQuote(symbol, market, 'auto')`. KR/FNO/US 모두 동일 그리드 (US 가드 제거). 호가 단계 동적(`displayAsks = asks.slice(0, asks.length || 10)`). US `toFixed(2)` USD, KR/FNO 정수. 매도호가 클릭→sell, 매수호가 클릭→buy. KR=`useMarketClock()` 헤더 거래소 라벨, US=`useUsMarketClock()` 거래시간 라벨. **`errorMessage` 수신 시 헤더 위 빨간 ⚠ 배너** (`bg-red-50 border-red-200`) — 백엔드 KIS 키 미설정 등 silent 빈 호가창 차단
- **OrderForm**: `symbol`/`symbolName`/`market` props 외부 제어. `externalPrice`/`externalSide`. FNO: 지정/시장/조건부지정/최유리지정 + IOC/FOK. `KR_EXCHANGE_OPTIONS = [SOR(추천)/KRX/NXT]` (market==='KR'만). `isSimulation` 시 SOR/NXT 비활성. US 매수가능 라벨에 `$X (₩X) · 환율 ₩1,XXX/USD` (graceful degrade)
- **OpenOrdersTable + ExecutionsTable**: `excg_id_dvsn_cd === 'SOR'`(HTS/MTS 주문)은 "앱취소필요" 안내. "거래소" 컬럼 + `ExchangeBadge` (orders.exchange/excg_id_dvsn_cd, NULL→KRX). KR 행에서만 렌더

### Advisory 컴포넌트
- **FundamentalPanel**: 사업개요(BusinessOverview: #키워드+설명+매출비중 파이) → 비즈니스 모델(BusinessModelSection 3카드: 💰 매출 흐름 / 💵 현금 창출 / 🔬 R&D, 모든 필드 빈 값이면 미렌더) → 애널리스트 추정치(목표가 클릭→AnalystReportsModal) → 계량지표 10개(+EPS+안전마진가격) → 손익(+추정치 바 반투명) → BS → CF. **금융지주/금융업 행 숨김 분기** (`sector_tier`): IS의 `매출원가`/`매출총이익` + BS의 `유동자산`/`비유동자산`/`유동부채`/`비유동부채` 5+2행은 `sector_tier ∈ {insurance, bank_holding, securities}`일 때 미렌더. FinancialTable도 동일 prop 분기
- **TechnicalPanel**: 타임프레임(15m/60m/1d/1wk) + 기간. 시그널 카드 + 캔들+MA+BB → 거래량 → MACD → RSI → Stochastic → PER/PBR 밸류에이션(1d/1wk만, `valuationData` prop)
- **AIReportPanel**: v3 등급 카드(SafetyGradeBadge A~D + ScoreBar 3개 + Value Trap 배너 + recommendation 배지) → 종합투자의견 → 전략별평가 3컬럼(안전마진가격) → 기술 시그널 → 리스크/투자포인트. `<UserCommentInput>` 액션바 위 (onUserCommentChange prop 있을 때만), `<UserCommentaryCard>` 본문 최상단 (reportData.user_commentary_evaluation 있을 때만)

> 컴포넌트 상세 → `docs/FRONTEND_SPEC.md`
