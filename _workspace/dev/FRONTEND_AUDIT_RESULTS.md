# 프론트엔드 코드 감사 결과 (2026-04-17)

**범위**: `/frontend/src` (25,100줄)
**종합 평가**: 7.8/10
**분석 대상**: 파일크기 / 훅 패턴 / API 일관성 / 컴포넌트 구조 / 공통컴포넌트 / 미사용코드 / 스타일

---

## 🔴 HIGH 우선순위 (즉시 실행 권장)

### 1. useOrder.js 분할 (7개 함수 → 7개 파일)

**파일**: `/frontend/src/hooks/useOrder.js`
**현황**: 115줄, 7개 export 함수 패킹
```javascript
export function useOrderPlace()        // 주문 발송
export function useBuyable()           // 매수가능 조회
export function useOpenOrders()        // 미체결 목록
export function useExecutions()        // 당일 체결
export function useOrderHistory()      // 주문 이력
export function useOrderSync()         // 대사/동기화
export function useReservations()      // 예약주문
```

**문제**: 단일책임 원칙 위반 + 7개 독립 기능 혼재
**영향도**: 높음 (useOrder 의존 컴포넌트: OrderPage, OrderForm 등 5개+)
**예상 비용**: 2-3시간

**개선안**:
```
hooks/useOrder/
├─ useOrderPlace.js       (현재 L18-25)
├─ useBuyable.js          (현재 L28-35)
├─ useOpenOrders.js       (현재 L38-58)
├─ useExecutions.js       (현재 L61-68)
├─ useOrderHistory.js     (현재 L71-83)
├─ useOrderSync.js        (현재 L86-102)
├─ useReservations.js     (현재 L105-115)
└─ index.js               (전체 re-export)
```

**단계별 마이그레이션**:
1. 각 함수를 별도 파일로 이동
2. `hooks/useOrder/index.js`에서 re-export
3. import 문 일괄 변경: `import { useOrderPlace } from '../hooks/useOrder'` (기존 코드 호환 유지)

---

### 2. OrderPage 상태 복잡도 감소

**파일**: `/frontend/src/pages/OrderPage.jsx` (542줄)
**현황**:
- 13개 상태 변수 (symbol/market/activeTab/orderSubTab/pendingOrder/selectedPrice/selectedSide/…)
- 5개 useEffect + `eslint-disable-line react-hooks/exhaustive-deps` **3곳**
- 의존성 배열 관리 어려움

```javascript
// 현재 상태 (L47-68)
const [activeTab, setActiveTab] = useState('order')
const [market, setMarket] = useState(searchParams.get('market') || 'KR')
const [pendingOrder, setPendingOrder] = useState(null)
const [symbol, setSymbol] = useState(searchParams.get('symbol') || '')
const [symbolName, setSymbolName] = useState(searchParams.get('symbol_name') || '')
const [selectedPrice, setSelectedPrice] = useState(null)
const [selectedSide, setSelectedSide] = useState(null)
const [orderSubTab, setOrderSubTab] = useState('new')
const [modifyTarget, setModifyTarget] = useState(null)
```

**문제**: 상태 분산으로 인한 관리 복잡도 증가
**영향도**: 높음 (버그 위험, 유지보수성↓)
**예상 비용**: 2-3시간

**개선안 - 커스텀훅 도입**:
```javascript
// hooks/useOrderPageState.js
export function useOrderPageState(initialSymbol, initialMarket) {
  const [symbol, setSymbol] = useState(initialSymbol)
  const [symbolName, setSymbolName] = useState('')
  const [market, setMarket] = useState(initialMarket)
  const [activeTab, setActiveTab] = useState('order')
  const [orderSubTab, setOrderSubTab] = useState('new')
  const [pendingOrder, setPendingOrder] = useState(null)
  const [selectedPrice, setSelectedPrice] = useState(null)
  const [selectedSide, setSelectedSide] = useState(null)
  const [modifyTarget, setModifyTarget] = useState(null)

  const handleSymbolSelect = useCallback(({ code, name, market: mkt }) => {
    setSymbol(code)
    setSymbolName(name)
    if (mkt) setMarket(mkt)
  }, [])

  const handleMarketChange = useCallback((newMarket) => {
    setMarket(newMarket)
    setSymbol('')
    setSymbolName('')
  }, [])

  return {
    symbol, setSymbol, symbolName, setSymbolName,
    market, setMarket, activeTab, setActiveTab,
    orderSubTab, setOrderSubTab, pendingOrder, setPendingOrder,
    selectedPrice, setSelectedPrice, selectedSide, setSelectedSide,
    modifyTarget, setModifyTarget,
    handleSymbolSelect, handleMarketChange,
  }
}

// OrderPage.jsx에서 사용
const pageState = useOrderPageState(
  searchParams.get('symbol') || '',
  searchParams.get('market') || 'KR'
)
```

**의존성 배열 정리**:
- L100: `[activeTab]` → useCallback로 감싸기
- L111: `market` 변경 감지 → usePrevious 훅으로 간소화
- L123: `[activeTab, market, loadOpen, loadExec]` → loadOpen/loadExec는 자체 useCallback이므로 안정적

---

### 3. OrderForm Props 정규화

**파일**: `/frontend/src/components/order/OrderForm.jsx` (313줄)
**현황**: Props 8개, 콜백과 값 혼재

```javascript
// 현재 (L49-56)
export default function OrderForm({
  symbol = '',
  symbolName = '',
  market = 'KR',
  externalPrice = null,
  externalSide = null,
  onPriceChange = null,
  onSideChange = null,
  onConfirm = () => {},
})
```

**문제**: Props 수 과다 + 핸들러 이름 불일치 (onPriceChange vs externalPrice)
**영향도**: 중간 (호출처 1곳: OrderPage)
**예상 비용**: 1시간

**개선안**:
```javascript
// 정규화된 Props 구조
export default function OrderForm({
  symbol = '',
  symbolName = '',
  market = 'KR',
  external = { price: null, side: null },
  handlers = { onPriceChange: null, onSideChange: null, onConfirm: () => {} },
}) {
  // 내부에서 external.price, handlers.onConfirm으로 접근
}

// 사용처 (OrderPage)
<OrderForm
  symbol={symbol}
  symbolName={symbolName}
  market={market}
  external={{ price: selectedPrice, side: selectedSide }}
  handlers={{ onPriceChange, onSideChange, onConfirm }}
/>
```

**효과**: Props 8개 → 3개 + external/handlers 객체로 명확한 의도 표현

---

## 🟡 MEDIUM 우선순위 (다음 스프린트)

### 1. FundamentalPanel 분할 (540줄 → 3개 컴포넌트)

**파일**: `/frontend/src/components/advisory/FundamentalPanel.jsx` (540줄)
**구성**:
- 계량지표 카드 (10개 지표)
- 손익계산서 (매출/영업이익/순이익)
- 대차대조표 (자산/부채/자본)
- 현금흐름표 (영업/투자/재무 캐시플로우)
- 사업별 매출비중 (파이차트)

**문제**: 단일 파일에 5개 섹션 통합 → 수정/유지보수 어려움
**영향도**: 중간
**예상 비용**: 3-4시간

**분할 구조**:
```
components/advisory/fundamental/
├─ FundamentalPanel.jsx        (메인, 전체 레이아웃)
├─ MetricsCard.js              (계량지표 10개 카드)
├─ FinancialStatements.jsx      (IS/BS/CF 테이블 3종류)
└─ BusinessSegments.jsx         (사업별 매출 파이차트)
```

**각 파일 예상 크기**: ~140-150줄

---

### 2. TechnicalPanel 분할 (462줄 → 5개 컴포넌트)

**파일**: `/frontend/src/components/advisory/TechnicalPanel.jsx` (462줄)
**구성**:
- 타임프레임 선택 UI (15m/60m/1d/1wk)
- 캔들스틱 차트 (CandlestickChart 재사용)
- 기술지표 신호 카드
- MACD 차트
- RSI 차트
- Stochastic 차트
- PER/PBR 밸류에이션 차트

**문제**: 7개 섹션이 1개 파일에 → 수정 영향도 높음
**영향도**: 중간
**예상 비용**: 3-4시간

**분할 구조**:
```
components/advisory/technical/
├─ TechnicalPanel.jsx           (메인, 타임프레임 선택)
├─ CandleWithIndicators.jsx     (캔들 + MA + BB)
├─ MacdChart.jsx                (MACD)
├─ RsiChart.jsx                 (RSI)
├─ StochasticChart.jsx          (Stochastic)
└─ ValuationSection.jsx         (PER/PBR 차트, 1d/1wk만)
```

**각 파일 예상 크기**: ~80-100줄

---

### 3. API 쿼리파라미터 표준화 (URLSearchParams)

**파일**: `/frontend/src/api/order.js`, `advisory.js`
**현황**: 쿼리 파라미터 구성 방식 혼재

```javascript
// order.js (L12): 문자열 연결 + encodeURIComponent
export const fetchBuyable = (symbol, market = 'KR', price = 0, orderType = '00', side = 'buy') =>
  apiFetch(`/api/order/buyable?symbol=${encodeURIComponent(symbol)}&market=${market}&...`)

// advisory.js (L22): 조건부 문자열 연결
export const refreshAdvisoryData = (code, market = 'KR', name = null) => {
  const q = name ? `&name=${encodeURIComponent(name)}` : ''
  return apiFetch(`/api/advisory/${encodeURIComponent(code)}/refresh?market=${market}${q}`, ...)
}

// screener.js: URLSearchParams 사용 ✅
export function fetchStocks(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') qs.set(k, v)
  })
  return apiFetch(`/api/screener/stocks?${qs}`)
}
```

**문제**: 혼재된 방식 → 유지보수 어려움, undefined 값 처리 비일관
**영향도**: 낮음 (현재 동작함)
**예상 비용**: 1-2시간

**표준화 방안**:
```javascript
// utils/queryString.js
export function buildQuery(params) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') {
      qs.set(k, v)
    }
  })
  return qs.toString()
}

// api/order.js 개선
export const fetchBuyable = (symbol, market = 'KR', price = 0, orderType = '00', side = 'buy') => {
  const qs = buildQuery({ symbol, market, price, order_type: orderType, side })
  return apiFetch(`/api/order/buyable?${qs}`)
}

// api/advisory.js 개선
export const refreshAdvisoryData = (code, market = 'KR', name = null) => {
  const qs = buildQuery({ market, name })
  return apiFetch(`/api/advisory/${encodeURIComponent(code)}/refresh?${qs}`, {
    method: 'POST',
  })
}
```

---

### 4. useBacktest / useMarketBoard / useAdvisory 분할

**파일**:
- `/frontend/src/hooks/useBacktest.js` (143줄, 3개 export)
- `/frontend/src/hooks/useMarketBoard.js` (127줄, 2개 export)
- `/frontend/src/hooks/useAdvisory.js` (126줄, 4개 export)

**문제**: 단일 파일에 여러 독립 훅 패킹
**영향도**: 낮음 (현재 동작)
**예상 비용**: 2-3시간

**개선안**:
```
hooks/useBacktest/
├─ useMcpStatus.js
├─ usePresets.js
├─ useBacktest.js
└─ index.js

hooks/useMarketBoard/
├─ useMarketBoard.js
├─ useDisplayStocks.js
└─ index.js

hooks/useAdvisory/
├─ useAdvisoryStocks.js
├─ useAdvisoryData.js
├─ useAdvisoryReport.js
├─ useAdvisoryOhlcv.js
└─ index.js
```

**호환성 유지**: 기존 import 경로 유지 (`hooks/useBacktest` → index.js re-export)

---

### 5. TabBar/SubTabBar 공통 컴포넌트 제작

**파일**: DetailPage.jsx (L24-52), OrderPage.jsx (L33-45)
**현황**: TabBtn/SubTabBtn 유사 코드 반복

```javascript
// DetailPage.jsx (L24-37)
function TabBtn({ id, active, onClick, children }) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
        active
          ? 'border-blue-600 text-blue-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
      }`}
    >
      {children}
    </button>
  )
}

// OrderPage.jsx (L다른 위치)에서도 유사하게 정의됨
```

**문제**: 동일한 UI 패턴이 3곳에서 중복 정의
**영향도**: 낮음
**예상 비용**: 1-2시간

**개선안**:
```javascript
// components/common/TabBar.jsx
export function TabBar({ tabs, activeTab, onChange, size = 'md' }) {
  const sizeClasses = {
    sm: 'px-3 py-2 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-3 text-base',
  }

  return (
    <div className="border-b border-gray-200">
      <div className="flex gap-2">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`font-medium border-b-2 transition-colors ${sizeClasses[size]} ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  )
}

// 사용처
<TabBar
  tabs={TABS}
  activeTab={activeTab}
  onChange={setActiveTab}
/>
```

---

### 6. 탭 UI 상수 중앙화

**파일**: DetailPage.jsx (L12-15), OrderPage.jsx (L33-45), ReportPage.jsx (추정)
**현황**: TABS, REPORT_SUB_TABS, MARKET_TABS 등이 컴포넌트 마다 정의됨

**개선안**:
```
src/constants/
├─ tabs.js
├─ markets.js
└─ orders.js

// src/constants/tabs.js
export const PAGE_TABS = {
  DETAIL: [
    { id: 'financials', label: '재무분석' },
    { id: 'report', label: '종합 리포트' },
  ],
  DETAIL_REPORT_SUB: [
    { id: 'cagr',        label: 'CAGR 요약' },
    { id: 'fundamental', label: '기본적 분석' },
    { id: 'technical',   label: '기술적 분석' },
    { id: 'ai',          label: 'AI 자문' },
  ],
  ORDER: [
    { key: 'order', label: '주문 발송' },
    { key: 'open', label: '미체결' },
    { key: 'executions', label: '체결 내역' },
    { key: 'history', label: '주문 이력' },
    { key: 'reservation', label: '예약주문' },
  ],
}

export const MARKET_OPTIONS = [
  { key: 'KR', label: '국내' },
  { key: 'US', label: '미국' },
  { key: 'FNO', label: '선물옵션' },
]
```

---

## 🟢 LOW 우선순위 (개선하면 좋음)

### 1. WatchlistDashboard DnD 로직 추출

**파일**: `/frontend/src/components/watchlist/WatchlistDashboard.jsx` (376줄)
**현황**: @dnd-kit 드래그앤드롭 로직이 컴포넌트 내 직접 구현

**개선안**: `useWatchlistDnD()` 커스텀훅으로 분리
```javascript
// hooks/useWatchlistDnD.js
export function useWatchlistDnD(watchlist) {
  const [items, setItems] = useState(watchlist)

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      // 순서 변경 로직
    }
  }

  return { items, setItems, handleDragEnd }
}
```

**영향도**: 낮음 (현재 동작)
**예상 비용**: 1-2시간

---

### 2. AsyncRender 보일러플레이트 패턴화

**현황**: 많은 컴포넌트에서 반복되는 패턴
```javascript
{loading && <LoadingSpinner />}
{error && <ErrorAlert error={error} />}
{data && <DataRender {...data} />}
```

**개선안**: `<AsyncBoundary>` 컴포넌트 또는 `useAsyncRender()` 훅

```javascript
// components/common/AsyncBoundary.jsx
export function AsyncBoundary({ loading, error, data, children }) {
  if (loading) return <LoadingSpinner />
  if (error) return <ErrorAlert error={error} />
  if (!data) return null
  return children(data)
}

// 사용처
<AsyncBoundary loading={loading} error={error} data={data}>
  {(data) => <DataRender {...data} />}
</AsyncBoundary>
```

**영향도**: 낮음 (리팩토링만)
**예상 비용**: 2-3시간

---

### 3. ReportPage 섹션별 분할

**파일**: `/frontend/src/pages/ReportPage.jsx` (472줄)
**구성**: 일일보고서 / 추천이력 / 성과통계 3섹션

**분할 구조**:
```
pages/report/
├─ ReportPage.jsx           (메인, 탭 라우팅)
├─ DailyReportSection.jsx   (~150줄)
├─ RecommendationSection.jsx (~150줄)
└─ PerformanceSection.jsx   (~150줄)
```

**영향도**: 낮음
**예상 비용**: 2-3시간

---

## 📊 평가별 상세 점수

| 항목 | 점수 | 코멘트 |
|------|------|--------|
| **파일 크기 관리** | 7/10 | FundamentalPanel(540) / TechnicalPanel(462) 초과 → 분할 필요 |
| **훅 설계** | 8/10 | useAsyncState 활용↑, 하지만 useOrder(7개) 패킹 문제 |
| **API 일관성** | 8.5/10 | apiFetch 중앙화↑, 쿼리파라미터 혼재 경미 |
| **컴포넌트 구조** | 7.5/10 | Props drilling 양호, TabBtn 반복 코드 2곳 |
| **공통 컴포넌트 활용** | 8/10 | 재사용도↑, 탭 UI 정규화 기회 |
| **미사용 코드 정리** | 9/10 | 매우 양호. 죽은 import/export 거의 없음 |
| **인라인 스타일** | 9/10 | 동적값만 인라인 사용. Tailwind 원칙 준수 |
| **종합** | **7.8/10** | 신규 기능 단계에서 리팩토링 시작 권장 |

---

## ✅ 잘하고 있는 것

1. **apiFetch 중앙화 설계** — 모든 API 호출이 `/api/client.js` 통과 ✅
2. **useAsyncState 활용** — 11개 훅이 일관되게 사용 (보일러플레이트 최소화) ✅
3. **미사용 코드 정리** — 전체 import 스캔 결과 죽은 코드 거의 없음 ✅
4. **Tailwind 원칙 준수** — 인라인 스타일 24건 모두 동적값만 사용 ✅
5. **컴포넌트 재사용** — DataTable, LoadingSpinner, WatchlistButton 통일 ✅

---

## 🎯 구현 우선순위 (총 비용 추정)

| 우선순위 | 항목 | 비용 | 영향도 |
|---------|------|------|--------|
| **1** | useOrder.js 분할 | 2-3h | 높음 |
| **2** | OrderPage 상태 번들링 | 2-3h | 높음 |
| **3** | OrderForm props 정규화 | 1h | 중간 |
| **4** | FundamentalPanel 분할 | 3-4h | 중간 |
| **5** | TechnicalPanel 분할 | 3-4h | 중간 |
| **6** | API 쿼리파라미터 표준화 | 1-2h | 낮음 |
| **7** | useBacktest/useMarketBoard/useAdvisory 분할 | 2-3h | 낮음 |
| **8** | TabBar/SubTabBar 공통화 | 1-2h | 낮음 |
| **9** | 탭 상수 중앙화 | 1h | 낮음 |
| **10** | ReportPage 섹션 분할 | 2-3h | 낮음 |
| | **총계** | **19-28시간** | |

**권장 스케줄**:
- **Phase 1 (고우선 3개)**: 5-7시간 → 즉시 (품질↑, 버그 감소)
- **Phase 2 (중우선 5개)**: 8-12시간 → 다음 스프린트
- **Phase 3 (저우선 2개)**: 4-6시간 → 여유 시간 활용

---

## 📝 최종 권장사항

1. **즉시 실행** (이번 주)
   - useOrder.js 분할 → 단일책임 원칙 복구
   - OrderPage 상태 번들링 → 복잡도 감소, 버그 방지

2. **다음 스프린트**
   - FundamentalPanel / TechnicalPanel 분할
   - API 쿼리파라미터 표준화
   - TabBar 공통 컴포넌트화

3. **백로그**
   - ReportPage 섹션 분할
   - useBacktest/useMarketBoard 분할 (선택사항)

---

**분석 완료**: 2026-04-17 15:00 KST
