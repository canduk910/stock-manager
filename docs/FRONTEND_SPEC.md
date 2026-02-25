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
  vite.config.js             /api/* → localhost:8000 프록시 설정
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
| `/detail/:symbol` | DetailPage | 탭 UI: 재무분석 / 밸류에이션 / 종합 리포트 |

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

---

## 컴포넌트

### 공통 (`src/components/common/`)

| 컴포넌트 | 설명 |
|---------|------|
| `DataTable` | 범용 테이블. `columns` 배열과 `data` 배열을 받아 렌더링. 컬럼별 `render` 함수 지원. |
| `LoadingSpinner` | 로딩 스피너 |
| `ErrorAlert` | 에러 메시지 배너 |
| `EmptyState` | 데이터 없음 상태 메시지 |

### 레이아웃 (`src/components/layout/`)

| 컴포넌트 | 설명 |
|---------|------|
| `Header` | 상단 네비게이션 바. 로고 "DK STOCK". `NAV_ITEMS` 배열로 5개 메뉴 렌더링. `NavLink`의 `isActive`로 현재 페이지 강조. |

### 스크리너 (`src/components/screener/`)

| 컴포넌트 | 설명 |
|---------|------|
| `FilterPanel` | 시장/PER/PBR/ROE/정렬 등 필터 입력 폼. "조회하기" 버튼 클릭 시 API 호출 (onChange 즉시 호출 안 함). |
| `StockTable` | 스크리닝 결과 테이블. 시가총액 억/조 포맷팅. |

### 공시 (`src/components/earnings/`)

| 컴포넌트 | 설명 |
|---------|------|
| `FilingsTable` | 정기보고서 목록 테이블. `WatchlistButton`으로 인라인 관심종목 추가. 컬럼: 관심종목 버튼 / 종목코드 / 종목명 / 당일·3개월·6개월·1년 수익률(`ReturnCell`) / 매출액·영업이익(`FinCell`, YoY 포함) / 보고서 종류(색상 배지: 사업=보라, 반기=파랑, 분기=청록) / 보고서명(DART 링크) / 제출일 / 제출인. |

### 잔고 (`src/components/balance/`)

| 컴포넌트 | 설명 |
|---------|------|
| `PortfolioSummary` | 총평가금액/주식평가/예수금 카드. 해외주식·외화 보유 시 카드 하단에 국내/해외(원화환산) 세부 분류 표시. |
| `HoldingsTable` | 국내주식 보유종목 테이블. 매입단가 소수점 절사(`Math.floor`). |
| `OverseasHoldingsTable` | 해외주식 보유종목 테이블. 거래소·통화 컬럼 포함. 매입단가 소수점 2자리 고정. `평가손익(외화)` + `평가손익(원화)` 두 컬럼 표시. |
| `FuturesTable` | 국내선물옵션 포지션 테이블. 포지션 뱃지(매수=빨강, 매도=파랑). 미결제수량 표시. |

### 관심종목 (`src/components/watchlist/`)

| 컴포넌트 | 설명 |
|---------|------|
| `AddStockForm` | 종목 추가 폼 (코드/종목명 + 메모). 인라인 에러 표시. |
| `WatchlistDashboard` | 관심종목 시세/재무 테이블. 종목명 클릭 → `/detail/:symbol` 이동. CSV 다운로드. 인라인 메모 편집(`MemoCell`). 삭제 확인 팝업. |
| `StockInfoModal` | 단일 종목 상세 모달. 기본정보 10칸 그리드 + 최대 10년 재무 테이블(연도 클릭 → DART 링크) + 메모 편집. ESC로 닫기. |

### 종목 상세 (`src/components/detail/`)

| 컴포넌트 | 설명 |
|---------|------|
| `StockHeader` | 현재가/전일대비 + PER/PBR 배지 (평균 대비 저평가/고평가 색상 표시) + 시장/업종/시총 정보. |
| `FinancialTable` | 가로 스크롤 10년 재무 테이블. 연도 헤더는 DART 사업보고서 링크. 매출/영업이익/영업이익률/순이익 행. YoY 증감률 색상 표시. 첫 열(항목명) sticky. |
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
- 탭 UI: 재무분석(FinancialTable) / 밸류에이션(ValuationChart) / 종합 리포트(ReportSummary)
- "← 관심종목으로" 뒤로가기 링크

---

## UI 규칙

- 한국 관례: **상승 = 빨간색** (`text-red-600`), **하락 = 파란색** (`text-blue-600`)
- 시가총액: 억/조 포맷팅은 프론트에서 처리 (1조 이상은 `X.Y조`, 미만은 `X,XXX억`)
- 변동: 상승 시 `▲` + `+`, 하락 시 `▼`
- DART 링크: `target="_blank"`, `rel="noopener noreferrer"`
- 매입단가 포맷: 국내주식 `Math.floor()` 소수점 절사(정수), 해외주식 소수점 2자리 고정(`toFixed`)
