# 프론트엔드 아키텍처

React 19 + Vite + Tailwind CSS v4 + Recharts SPA. 네이티브 fetch 사용 (외부 HTTP 라이브러리 없음).

---

## 기술 스택

| 항목 | 라이브러리 | 용도 |
|------|-----------|------|
| UI | React 19 | 컴포넌트 |
| 빌드 | Vite 6 | 개발 서버 + 프로덕션 빌드 |
| 스타일 | Tailwind CSS v4 | 유틸리티 CSS |
| 라우팅 | react-router-dom v7 | SPA 라우팅 |
| 차트 | Recharts | PER/PBR 시계열 차트 |
| HTTP | fetch (네이티브) | API 호출 |

---

## 디렉토리 구조

```
frontend/
  index.html                 진입 HTML
  package.json
  vite.config.js             /api/* → localhost:8000 프록시, /ws → ws://localhost:8000 (WebSocket 프록시)
  src/
    main.jsx                 ReactDOM.createRoot 진입점
    App.jsx                  BrowserRouter + Routes 정의
    index.css                @import "tailwindcss"
```

---

## 라우팅

| 경로 | 페이지 | 설명 |
|-----|-------|------|
| `/` | DashboardPage | 잔고 요약 + 오늘 공시 5건 + 시총 상위 10종목 |
| `/screener` | ScreenerPage | 필터 패널 + 스크리닝 결과 테이블 |
| `/earnings` | EarningsPage | 기간 선택 + 공시 목록 |
| `/balance` | BalancePage | 보유종목 + 평가금액 |
| `/watchlist` | WatchlistPage | 관심종목 CRUD + 시세/재무 대시보드 |
| `/detail/:symbol` | DetailPage | 탭 UI: 재무분석 / 밸류에이션 / 종합 리포트 (서브탭: CAGR요약 / 기본적분석 / 기술적분석 / AI자문) |
| `/order` | OrderPage | 탭 UI: 주문발송 / 미체결 / 체결내역 / 주문이력 / 예약주문 |
| `/market-board` | MarketBoardPage | 시세판: 신고가/신저가 + 사용자 선택 종목. 실시간 WS. |

---

## API 레이어 (`src/api/`)

| 파일 | 함수 | 호출 엔드포인트 |
|------|------|----------------|
| `client.js` | `apiFetch(path, options)` | fetch 래퍼 (에러 처리, Content-Type 설정) |
| `screener.js` | `fetchStocks(params)` | `GET /api/screener/stocks` |
| `earnings.js` | `fetchFilings(startDate, endDate)` | `GET /api/earnings/filings` |
| `balance.js` | `fetchBalance()` | `GET /api/balance` |
| `watchlist.js` | `fetchWatchlist()`, `addToWatchlist()`, `removeFromWatchlist()`, `updateMemo()`, `fetchDashboard()`, `fetchStockInfo()` | `/api/watchlist/*` |
| `detail.js` | `fetchDetailFinancials()`, `fetchDetailValuation()`, `fetchDetailReport()` | `/api/detail/*` |
| `order.js` | `placeOrder()`, `fetchBuyable()`, `fetchOpenOrders()`, `cancelOrder()`, `modifyOrder()`, `fetchExecutions()`, `fetchOrderHistory()`, `syncOrders()`, `createReservation()`, `fetchReservations()`, `deleteReservation()` | `/api/order/*` |
| `advisory.js` | `fetchAdvisoryStocks()`, `addAdvisoryStock()`, `removeAdvisoryStock()`, `refreshAdvisoryData(code, market, name)`, `fetchAdvisoryData()`, `generateReport()`, `fetchReport()`, `fetchReportHistory(code, market, limit)`, `fetchReportById(code, reportId, market)`, `fetchAdvisoryOhlcv(code, market, interval, period)` | `/api/advisory/*` |
| `search.js` | `searchStocks(q, market)` | `GET /api/search` |
| `marketBoard.js` | `fetchNewHighsLows(top)`, `fetchSparklines(items)` | `GET /api/market-board/new-highs-lows`, `POST /api/market-board/sparklines` |

---

## 커스텀 훅 (`src/hooks/`)

| 파일 | 훅 | 반환값 |
|------|-----|-------|
| `useScreener.js` | `useScreener()` | `{ data, loading, error, search }` |
| `useEarnings.js` | `useEarnings()` | `{ data, loading, error, load }` — `load(startDate, endDate)` |
| `useBalance.js` | `useBalance()` | `{ data, loading, error, load }` |
| `useWatchlist.js` | `useWatchlist()` | `{ items, loading, error, load, add, remove, memo }` |
| | `useDashboard()` | `{ stocks, loading, error, load }` |
| | `useStockInfo()` | `{ data, loading, error, load, reset }` |
| `useDetail.js` | `useDetailReport()` | `{ data, loading, error, load }` — `load(symbol, years)` |
| `useOrder.js` | `useOrderPlace()`, `useBuyable()`, `useOpenOrders()`, `useExecutions()`, `useOrderHistory()`, `useOrderSync()`, `useReservations()` | 각각 `{ loading, error, ... }` + 액션 함수 |
| `useNotification.js` | `useNotification()` | `{ toasts, notify, dismiss }` — 토스트 상태 + 브라우저 Notification API |
| `useWebSocket.js` | `useWebSocket(url, { onMessage, onOpen })` | `{ connected, sendMessage }` — 공용 WS 연결 수명주기. 지수 백오프 재연결(500ms→10초), visibilitychange 탭 복귀 재연결. url=null이면 연결 안 함. `buildWsUrl(path)` 헬퍼도 export. |
| `useQuote.js` | `useQuote(symbol, market='KR')` | `{ price, change, changeRate, sign, asks, bids, totalAskVolume, totalBidVolume, connected }` — `useWebSocket` 기반. `market` 파라미터를 WS URL `?market=` 쿼리로 전달 (`KR`/`FNO`/`US`). 자체 rAF throttle(pendingRef + rafRef)으로 60fps 렌더링 제어. symbol 변경 시 state 초기화. |
| `useAdvisory.js` | `useAdvisoryStocks()` | `{ stocks, loading, error, load, add, remove }` — 자문종목 목록 CRUD |
| | `useAdvisoryData()` | `{ data, loading, error, load, refresh }` — 분석 데이터 조회/새로고침. `refresh(code, market, name)` |
| | `useAdvisoryReport()` | `{ report, history, loading, error, load, generate, loadById }` — AI 리포트 조회/생성/히스토리. `history`: 목록(본문 제외). `loadById(code, id, market)`: 특정 리포트 로드. |
| | `useAdvisoryOhlcv()` | `{ result, loading, error, load }` — 타임프레임별 OHLCV+지표 조회. `load(code, market, interval, period)` → `{ ohlcv, indicators, interval, period }` |
| `useMarketBoard.js` | `useMarketBoard()` | `{ data, sparklines, loading, error, load, loadSparklines }` — 신고가/신저가 REST 로드 + sparkline 배치 로드 |
| `useMarketBoardWS.js` | `useMarketBoardWS()` | `{ prices, connected, subscribe, unsubscribe }` — `useWebSocket` 기반. subscribe/unsubscribe 시 WS 구독 메시지 전송. 재연결 시 기존 구독 자동 복원. prices: `{ [symbol]: { price, change_pct, sign } }` |

---

## 컴포넌트

### 공통 (`src/components/common/`)

| 컴포넌트 | 설명 |
|---------|------|
| `DataTable` | 범용 테이블. `columns` 배열과 `data` 배열을 받아 렌더링. 컬럼별 `render` 함수 지원. `renderContext` prop으로 외부 의존성(`navigate` 등) 전달. `sortable: false`로 정렬 비활성화 가능. |
| `ToastNotification` | 화면 우상단 고정 토스트 알림 컨테이너. `App.jsx`에서 `useNotification` 훅과 함께 마운트. success/error/info 타입 지원. |
| `WatchlistButton` | 관심종목 추가/표시 버튼. Props: `code`, `market`(기본 'KR'), `alreadyAdded`. 이미 추가된 종목이면 `★ 관심종목` 표시, 미추가 시 `+ 관심` 버튼. `StockTable`, `FilingsTable`에서 공용으로 import. |
| `CandlestickChart` | 캔들스틱 차트 공용 컴포넌트. Props: `ohlcv`, `indicators`, `interval`, `height`, `volumeHeight`, `showMA60`, `showVolume`, `extraChartData`, `xTickDivisor`. 캔들+MA5/MA20/MA60+볼린저밴드+거래량 렌더링. `INTERVAL_OPTS`, `PERIOD_OPTIONS`, `makeTickFormatter` 상수/유틸도 export. `PriceChartPanel`, `TechnicalPanel`에서 공용으로 import. |
| `LoadingSpinner` | 로딩 스피너 |
| `ErrorAlert` | 에러 메시지 배너 |
| `EmptyState` | 데이터 없음 상태 메시지 |

### 레이아웃 (`src/components/layout/`)

| 컴포넌트 | 설명 |
|---------|------|
| `Header` | 상단 네비게이션 바. 로고 "DK STOCK". `NAV_ITEMS` 배열로 7개 메뉴 렌더링 (대시보드/스크리너/공시/잔고/관심종목/시세판/주문). AI자문 메뉴는 DetailPage 내 탭으로 통합되어 제거됨. `NavLink`의 `isActive`로 현재 페이지 강조. |

### 스크리너 (`src/components/screener/`)

| 컴포넌트 | 설명 |
|---------|------|
| `FilterPanel` | 시장/PER/PBR/ROE/정렬 등 필터 입력 폼. "조회하기" 버튼 클릭 시 API 호출 (onChange 즉시 호출 안 함). |
| `StockTable` | 스크리닝 결과 테이블. 마운트 시 관심종목 목록 조회 → 이미 추가된 종목은 `★ 관심종목` 표시, 미추가 종목은 `+ 관심` 버튼(WatchlistButton). 컬럼: 관심종목 / 순위 / 종목코드 / 종목명 / 시장(배지) / **전일종가** / **현재가** / **당일%** / **3개월%** / **6개월%** / **1년%** / **배당수익률** / PER / PBR / ROE / 시가총액. 시가총액 억/조 포맷팅. 퍼센트 컬럼 한국 관례 색상(상승=빨강, 하락=파랑). |

### 공시 (`src/components/earnings/`)

| 컴포넌트 | 설명 |
|---------|------|
| `FilingsTable` | 정기보고서 목록 테이블. 마운트 시 관심종목 목록 조회 → 이미 추가된 종목은 `★ 관심종목` 표시, 미추가 종목은 `+ 관심` 버튼(WatchlistButton, market 파라미터 포함). 컬럼: 관심종목 / 종목코드 / 종목명 / 당일·3개월·6개월·1년 수익률(`ReturnCell`) / 매출액·영업이익(`FinCell`, YoY 포함) / 보고서 종류(색상 배지: 사업=보라, 반기=파랑, 분기=청록) / 보고서명(DART 링크) / 제출일 / 제출인. |

### 잔고 (`src/components/balance/`)

| 컴포넌트 | 설명 |
|---------|------|
| `PortfolioSummary` | 총평가금액/주식평가/예수금 카드. 해외주식·외화 보유 시 카드 하단에 국내/해외(원화환산) 세부 분류 표시. |
| `HoldingsTable` | 국내주식 보유종목 테이블. 컬럼: 거래소/종목코드/종목명/투자비중/보유수량/평가금액/매입단가(정수)/현재가/평가손익/수익률/시가총액/PER/ROE/PBR/**배당수익률**/주문버튼. 매입단가 소수점 절사(`Math.floor`). |
| `OverseasHoldingsTable` | 해외주식 보유종목 테이블. 거래소·통화 컬럼 포함. 매입단가 소수점 2자리 고정. `평가손익(외화)` + `평가손익(원화)` 두 컬럼 표시. PBR 뒤에 **배당수익률** 컬럼. 마지막 컬럼에 매도/매수 버튼. |
| `FuturesTable` | 국내선물옵션 포지션 테이블. 포지션 뱃지(매수=빨강, 매도=파랑). 미결제수량 표시. |

### 관심종목 (`src/components/watchlist/`)

| 컴포넌트 | 설명 |
|---------|------|
| `AddStockForm` | 종목 추가 폼 (코드/종목명 + 메모). 인라인 에러 표시. |
| `WatchlistDashboard` | 관심종목 시세/재무 테이블. 컬럼: 종목코드/종목명/현재가/전일대비/시가총액/매출액/영업이익/순이익/영업이익률/**배당수익률**/보고서기준/메모/삭제. 종목명 클릭 → `/detail/:symbol` 이동. CSV 다운로드. 인라인 메모 편집(`MemoCell`). 삭제 확인 팝업. |
| `StockInfoModal` | 단일 종목 상세 모달. 기본정보 그리드(현재가/전일대비/시가총액/상장주식수/PER/PBR/**ROE**/**배당수익률**/**주당배당금(DPS)**/52주고가/저가/시장·거래소/업종) + 최대 10년 재무 테이블(매출액/영업이익/**영업이익률**/당기순이익/**순이익률**, 연도 클릭→DART 링크) + 메모 편집. ESC로 닫기. `MarginRow` 컴포넌트로 영업이익률·순이익률 표시(서브행, 회색 배경, 이익률 수준별 색상). |

### 주문 (`src/components/order/`)

| 컴포넌트 | 설명 |
|---------|------|
| `SymbolSearchBar` | 주문 페이지 공용 종목 검색 바 (신규 컴포넌트). 시장 드롭다운(KR/US) + 종목 검색 입력 + 자동완성. Props: `market`, `onMarketChange`, `symbol`, `symbolName`, `onSymbolSelect`, `defaultQuery`. KR=자동완성 드롭다운(400ms debounce, 2글자 이상, `GET /api/search`), US=티커 검증(500ms debounce). 시장 변경 시 검색 상태 완전 초기화(대기 중 debounce 취소 포함). `marketRef`로 async 완료 시점 시장 변경 감지(US→KR 먹통 방지). |
| `OrderForm` | 매매구분/가격/수량 입력 폼. `symbol`, `symbolName`, `market` props로 종목/시장을 외부에서 제어. 잔고 페이지 URL 파라미터 `defaultValues` prop으로 반영. 매수가능 조회 버튼. `externalPrice` prop → 지정가 자동 세팅(호가창 연동). `externalSide` prop → 매매방향 자동 세팅(호가 클릭 연동). **FNO**: `FNO_ORDER_TYPE_OPTIONS`(지정가/시장가/조건부지정가/최유리지정가) + `FNO_CONDITION_OPTIONS`(없음/IOC/FOK). `mapFnoOrderCodes(orderType, condition)` → `{nmpr_type_cd, krx_nmpr_cndt_cd, ord_dvsn_cd}` 자동 매핑. 가격 step=0.01. |
| `OrderbookPanel` | 실시간 호가창. `symbol`+`market` prop. **KR/FNO 모두 `useQuote(symbol, market)` 훅 사용** (REST 폴링 제거). KR=KIS WS 10호가(실시간), FNO=KIS FNO WS 호가(실시간, 5 또는 10레벨), US=현재가만 표시(호가 미지원 안내). KR/FNO는 동일한 호가창 그리드 렌더링 공유(매도↑매수↓, 잔량 배경바). **매도호가(asks) 클릭 → `onPriceSelect(price, 'sell')`, 매수호가(bids) 클릭 → `onPriceSelect(price, 'buy')`**. 연결 상태 배지(녹색/회색). symbol 없으면 플레이스홀더 표시. `useMemo([asks, bids, market])`으로 `displayAsks` / `displayBids` / `maxVolume` 재계산 방지. `export default memo(OrderbookPanel)`으로 props 미변경 시 리렌더 차단. |
| `PriceChartPanel` | 가격 차트 패널. Props: `symbol`, `market`. `useAdvisoryOhlcv` 훅 사용. 타임프레임(15m/60m/1d/1wk) + 기간 선택 UI. `CandlestickChart` 컴포넌트로 차트 렌더링. symbol 변경 시 500ms debounce. |
| `OrderConfirmModal` | 주문 확인 모달. 종목/수량/가격/매매구분 재확인 후 발송. |
| `OpenOrdersTable` | 미체결 주문 테이블. `api_cancellable` 기준으로 API 주문은 정정/취소 버튼, HTS/MTS 주문은 "앱취소필요" 표시. |
| `ModifyOrderModal` | 주문 정정 모달 (가격/수량 변경). |
| `ExecutionsTable` | 당일 체결 내역 테이블. |
| `OrderHistoryTable` | 로컬 DB 주문 이력 테이블. 날짜/종목/상태 필터 지원. |
| `ReservationForm` | 예약주문 등록 폼. 조건 유형(가격 이하/이상/지정 시각) + 주문 정보 입력. |
| `ReservationsTable` | 예약주문 목록. WAITING 상태만 삭제 가능. |
| `SyncButton` | 대사 동기화 버튼. 클릭 시 `POST /api/order/sync` 호출, 갱신 건수 표시. |

### 시세판 (`src/components/market-board/`)

| 컴포넌트 | 설명 |
|---------|------|
| `MarketBoardCard` | 종목 1개 카드 (컴팩트). 신고가/신저가 배지, 현재가+등락률(WS 실시간), 미니 스파크라인(`height` prop). 시총·52주 고저 미표시. 클릭 시 `/detail/:symbol` 이동. |
| `SparklineChart` | Recharts AreaChart 기반 미니 차트. `data=[{date,close}]`, `trend='up'|'down'|null`, `height=48`. React `useId()`로 SVG gradient ID 고유화. |
| `NewHighLowSection` | 신고가(빨강)/신저가(파랑) 2컬럼 그리드. 각 10종목. 카드 그리드: `grid-cols-2 sm:3 xl:4 2xl:5`. |
| `CustomStockSection` | 시세판 하단 종목 목록. **stocks/onAdd/onRemove props 기반**. `_source='watchlist'` → ★ 배지(X 없음), `_source='custom'` → X 버튼. 별도 추가 최대 **30**개. 그리드: `grid-cols-3 sm:4 md:5 lg:6 xl:8 2xl:10`. |
| `AddStockSlot` | "+" 빈 슬롯 버튼. 클릭 시 `MarketBoardSearchModal` 오픈. |
| `MarketBoardSearchModal` | 종목 추가 모달. `SymbolSearchBar` 재사용. KR/US 시장 선택 + 종목 검색 + 추가 버튼. |

### AI자문 (`src/components/advisory/`)

| 컴포넌트 | 설명 |
|---------|------|
| `FundamentalPanel` | 기본적 분석 탭. **① ForwardEstimatesSection**: `forward_estimates` 있을 때만 표시 — EPS/매출/순이익 추정치 + 목표주가 + 투자의견 카드. ② 계량지표 카드 그리드 (PER/PBR/PSR/EV·EBITDA/ROE/ROA/부채비율/유동비율) ③ 손익계산서 테이블+BarChart (매출/영업이익/순이익 + `{fyYear}E`/`{fyYear+1}E` 추정 열, 인디고 스타일) ④ 대차대조표 테이블 ⑤ 현금흐름표 테이블+BarChart (영업CF vs FCF) ⑥ 사업별 매출비중 PieChart (KR: "AI추정" 배지). |
| `TechnicalPanel` | 기술적 분석 탭. `data`, `symbol`, `market` props. 타임프레임 선택(15분/60분/1일/1주) + 기간 선택. interval/period 변경 시 `fetchAdvisoryOhlcv()` 자동 호출. 시그널 배지 카드: MACD/RSI/Stochastic/MA20 상회 + 변동성돌파 목표가(K=0.5) + **ATR(14)** + **MA배열** (정배열=빨강/역배열=파랑/혼합=회색) + **K=0.3·0.5·0.7 목표가** (보라 배지). 차트: ComposedChart (종가봉+MA5/20/60+BB) + 거래량 BarChart + MACD + RSI(70/30) + Stochastic(80/20). |
| `AIReportPanel` | AI자문 탭. Props: `report`, `history`, `loading`, `error`, `onGenerate`, `onSelectHistory`. "AI 분석 생성" 버튼 + 리포트 2개 이상 시 날짜 드롭다운 + 종합투자의견(등급 배지+요약+근거) + **전략별평가 3컬럼 카드** (변동성돌파/안전마진/추세추종, 구 리포트에는 미표시) + 기술적시그널(신호 배지+지표별) + 리스크 요인 + 투자 포인트. JSON 파싱 실패 시 원문 텍스트 fallback. |

### 종목 상세 (`src/components/detail/`)

| 컴포넌트 | 설명 |
|---------|------|
| `StockHeader` | 현재가/전일대비 + PER/PBR 배지 (평균 대비 저평가/고평가 색상 표시) + 시장/업종/시총 정보. |
| `FinancialTable` | 가로 스크롤 10년 재무 테이블. 연도 헤더는 DART 사업보고서 링크. 매출/영업이익/영업이익률/순이익 행. YoY 증감률 색상 표시. 첫 열(항목명) sticky. **`forward` prop**: 오른쪽에 `{fyYear}E`/`{fyYear+1}E` 추정 열 추가 (인디고 계열 스타일, 매출·순이익 추정값, 영업이익 `-`). 상단에 `ForwardSection` 카드 (포워드 PER/EPS/매출/목표가/투자의견, 데이터 없으면 숨김). |
| `ValuationChart` | Recharts `LineChart`로 PER/PBR 월별 시계열 차트. `ReferenceLine`으로 기간 평균선 표시. 연도 변경 시에만 X축 레이블 표시. 커스텀 Tooltip. |
| `ReportSummary` | CAGR 카드(매출/영업이익/순이익 연평균 성장률) + 밸류에이션 진단(현재 PER/PBR vs 평균, 저평가/고평가 판정) + 최근 실적 요약 카드. |

---

## 페이지별 동작

### DashboardPage (`/`)
- 마운트 시 잔고 + 공시 + 스크리닝 3개 API 동시 호출
- KIS 키 없으면 잔고 섹션만 비활성화, 나머지 정상 표시

### ScreenerPage (`/screener`)
- FilterPanel에서 조건 입력 후 "조회하기" 버튼 클릭 시 API 호출
- 첫 호출 시 수초~수십초 소요 안내 문구 표시 (KRX 데이터 수집)

### EarningsPage (`/earnings`)
- 시작/종료 날짜 입력 + "오늘/1주/1개월" 단축 버튼
- "조회" 버튼 클릭 시 API 호출
- 클라이언트 사이드 필터: 종목명/종목코드 텍스트 검색 (추가 API 호출 없음). 조회 버튼 클릭 시 필터 초기화.
- 결과 건수 표시 + "상장종목만" 배지 (백엔드에서 이미 필터링됨)

### BalancePage (`/balance`)
- KIS 키 없으면 에러 대신 안내 메시지 표시
- 국내주식 / 해외주식 / 국내선물옵션 3개 섹션으로 분리. 해외주식·선물 보유분이 있을 때만 해당 섹션 표시

### WatchlistPage (`/watchlist`)
- 마운트 시 목록 + 대시보드 동시 로드
- 추가/삭제/메모저장 후 대시보드 자동 새로고침
- 종목명 클릭 → `/detail/:symbol` 네비게이션

### DetailPage (`/detail/:symbol`)
- 마운트 시 `/api/detail/report/{symbol}` 호출
- 상위 탭 UI: 재무분석(FinancialTable) / 밸류에이션(ValuationChart) / 종합 리포트
- 종합 리포트 탭 내 서브탭 4개:
  - **CAGR 요약**: ReportSummary (기존과 동일, advisory 데이터 불필요)
  - **기본적 분석**: FundamentalPanel (재무제표 3종 + 계량지표 + 파이차트)
  - **기술적 분석**: TechnicalPanel (타임프레임 선택 + 차트 묶음)
  - **AI 자문**: AIReportPanel (GPT-4o 리포트)
- advisory 데이터: cagr 외 서브탭 최초 진입 시 lazy load (loadAdvData + loadReport 동시 호출)
- cagr 서브탭에서는 [새로고침] 버튼 숨김. AI자문 서브탭에서만 [AI분석 생성] 버튼 표시.
- "← 관심종목으로" 뒤로가기 링크

### OrderPage (`/order`)
- 5탭 UI: 주문발송 / 미체결 / 체결내역 / 주문이력 / 예약주문
- URL 파라미터(`?symbol=&symbol_name=&market=&side=&quantity=`)로 잔고 페이지 매도/매수 버튼과 연계 → 상태 초기값 + `quoteSymbol` 자동 채움
- **공유 상태**: `symbol`, `symbolName`, `market`을 OrderPage 최상단에서 관리. `SymbolSearchBar`로 제어, `OrderForm`/`OrderbookPanel`/`PriceChartPanel`에 props로 전달.
- **주문발송 탭**:
  - 상단: `SymbolSearchBar` (시장+종목 선택 — 신규주문/정정취소 양쪽 공유)
  - 서브탭: [신규 주문 | 정정/취소 N건]
  - xl 이상에서 2컬럼 grid. 왼쪽=`OrderbookPanel`(호가창), 오른쪽=주문폼(OrderForm 또는 OrderPanelOpenOrders)
  - 호가 클릭 → `selectedPrice` + `selectedSide` state → `OrderForm.externalPrice`/`externalSide` 전달 + 신규주문 탭 자동 전환
  - 하단: `PriceChartPanel` (타임프레임/기간 선택 + 차트)
- **정정/취소 서브탭 (`OrderPanelOpenOrders`)**: `openOrders`를 `quoteSymbol`로 클라이언트 필터링. 정정 → `ModifyOrderModal`, 취소 → confirm 후 `handleCancelOrder`. `api_cancellable === false`이면 "앱취소필요" 표시.
- `isMounted` ref 가드로 mount 시 중복 `loadOpen()` 호출 방지
- 미체결 탭: 국내/미국 탭 선택, 새로고침 버튼, 동기화 버튼(`SyncButton`)
- 주문 발송 성공 시 토스트 알림 (`notify()`)
- 예약주문 탭: 등록 폼 + 목록 (좌우 분할 레이아웃)

### MarketBoardPage (`/market-board`)
- 마운트 시 `GET /api/market-board/new-highs-lows` 호출 (최초 조회 시 수십 초 소요, 이후 캐시)
- 신고가/신저가 종목 확정 후 sparkline 배치 로드 (`POST /api/market-board/sparklines`)
- `useMarketBoardWS`로 단일 WS 연결, 신고가/신저가 + 사용자 종목 일괄 구독
- **마운트 시 병렬 조회**: `fetchWatchlist()` + `fetchCustomStocks()` → watchlistStocks/customStocks 상태 세팅
- **하단 표시 = 관심종목(★) + 별도 등록 종목(X)**: `displayStocks = useMemo(...)` 중복 제거 합산
  - `_source: 'watchlist'` → ★ 배지, X 버튼 없음 (관심종목에서 삭제 시 자동 제거)
  - `_source: 'custom'` → X 버튼으로 DB 삭제 가능 (GET/POST/DELETE `/api/market-board/custom-stocks`)
- custom 종목 추가/삭제 시 DB API 호출 + 상태 업데이트 + WS subscribe/unsubscribe + sparkline 요청
- 새로고침 버튼으로 수동 갱신 가능
- 연결 상태 배지(초록/회색) + 기준 시각 + 스캔 종목 수 표시

---

## UI 규칙

- 한국 관례: **상승 = 빨간색** (`text-red-600`), **하락 = 파란색** (`text-blue-600`)
- 시가총액: 억/조 포맷팅은 프론트에서 처리 (1조 이상은 `X.Y조`, 미만은 `X,XXX억`)
- 변동: 상승 시 `▲` + `+`, 하락 시 `▼`
- DART 링크: `target="_blank"`, `rel="noopener noreferrer"`
- 매입단가 포맷: 국내주식 `Math.floor()` 소수점 절사(정수), 해외주식 소수점 2자리 고정(`toFixed`)
- 주문 취소 가능 여부: `api_cancellable === false`이면 정정/취소 버튼 대신 "앱취소필요" 텍스트 표시 (마우스 오버 시 안내 tooltip)
- 잔고→주문 연계: HoldingsTable·OverseasHoldingsTable의 매도/매수 버튼 클릭 시 `/order?symbol=&market=&side=&quantity=` URL로 이동, OrderForm 기본값 + 호가창 자동 세팅
- **호가창 가격 포맷**: 국내 `Math.floor(price).toLocaleString()` (정수), 해외 `price.toFixed(2)` (소수점 2자리)
- **호가창 잔량 배경바**: 최대 잔량 대비 비율로 `width: N%` 동적 인라인 스타일. 매도=파란 계열, 매수=빨간 계열.
- **useQuote 재연결 패턴**: `mountedRef` 언마운트 가드 + `symbol` 변경 시 이전 WS `close(1000)` 후 즉시 재연결. 비정상 code 시 3초 후 retry. 언마운트 시 `clearTimeout` + `ws.close(1000)`.
