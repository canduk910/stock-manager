# 프론트엔드 감사 발견 사항 요약

**생성일**: 2026-04-17
**분석 범위**: `/frontend/src` (25,100줄)
**종합 평가**: 7.8/10

---

## 🔴 HIGH 우선순위 (즉시 실행 권장)

### #1: useOrder.js 분할
- **파일**: `hooks/useOrder.js` (115줄)
- **문제**: 7개 독립 함수를 1파일에 패킹 (useOrderPlace / useBuyable / useOpenOrders / useExecutions / useOrderHistory / useOrderSync / useReservations)
- **영향도**: ⭐⭐⭐ (HIGH) — 5개+ 컴포넌트에서 의존
- **예상 비용**: 2-3시간
- **효과**: 단일책임 원칙 복구, 유지보수성↑
- **상태**: 미시작

---

### #2: OrderPage 상태 복잡도 감소
- **파일**: `pages/OrderPage.jsx` (542줄)
- **문제**: 13개 상태 변수 + 5개 useEffect + eslint-disable 3곳
- **영향도**: ⭐⭐⭐ (HIGH) — 버그 위험, 유지보수성↓
- **예상 비용**: 2-3시간
- **효과**: useOrderPageState 훅으로 상태 번들링, 의존성 배열 정리
- **상태**: 미시작

---

### #3: OrderForm Props 정규화
- **파일**: `components/order/OrderForm.jsx` (313줄)
- **문제**: Props 8개 혼재 (symbol/market/externalPrice/externalSide/onPriceChange/onSideChange/onConfirm)
- **영향도**: ⭐⭐ (MEDIUM) — 호출처 1곳
- **예상 비용**: 1시간
- **효과**: Props 8개 → 3개 + external/handlers 객체로 명확화
- **상태**: 미시작

---

## 🟡 MEDIUM 우선순위 (다음 스프린트)

### #4: FundamentalPanel 분할
- **파일**: `components/advisory/FundamentalPanel.jsx` (540줄)
- **문제**: 5개 섹션 통합 (계량지표/손익계산서/대차대조표/현금흐름표/사업별매출)
- **영향도**: ⭐⭐ (MEDIUM)
- **예상 비용**: 3-4시간
- **효과**: 540줄 → 4개 파일 (각 ~140줄)
- **분할**: MetricsCard / FinancialStatements / BusinessSegments 컴포넌트 추출
- **상태**: 미시작

---

### #5: TechnicalPanel 분할
- **파일**: `components/advisory/TechnicalPanel.jsx` (462줄)
- **문제**: 7개 섹션 통합 (타임프레임/캔들/신호카드/MACD/RSI/Stochastic/밸류에이션)
- **영향도**: ⭐⭐ (MEDIUM)
- **예상 비용**: 3-4시간
- **효과**: 462줄 → 6개 파일 (각 ~80줄)
- **분할**: CandleWithIndicators / MacdChart / RsiChart / StochasticChart / ValuationSection
- **상태**: 미시작

---

### #6: API 쿼리파라미터 표준화
- **파일**: `api/order.js`, `api/advisory.js`
- **문제**: 쿼리 구성 방식 혼재 (문자열 연결 vs URLSearchParams)
- **영향도**: ⭐ (LOW) — 현재 동작함
- **예상 비용**: 1-2시간
- **효과**: `utils/queryString.js` 헬퍼 함수 중앙화, 일관성↑
- **상태**: 미시작

---

### #7: useBacktest / useMarketBoard / useAdvisory 분할
- **파일**:
  - `hooks/useBacktest.js` (143줄, 3개 export)
  - `hooks/useMarketBoard.js` (127줄, 2개 export)
  - `hooks/useAdvisory.js` (126줄, 4개 export)
- **문제**: 여러 독립 훅을 1파일에 패킹
- **영향도**: ⭐⭐ (MEDIUM)
- **예상 비용**: 2-3시간
- **효과**: 각 훅별 파일 분리, 호환성 유지 (index.js re-export)
- **상태**: 미시작

---

### #8: TabBar/SubTabBar 공통 컴포넌트 제작
- **파일**: `components/detail/` (DetailPage), `components/order/` (OrderPage)
- **문제**: TabBtn/SubTabBtn 유사 코드 3곳 중복 정의
- **영향도**: ⭐ (LOW)
- **예상 비용**: 1-2시간
- **효과**: `components/common/TabBar.jsx` 공통화, 3곳 중복 제거
- **상태**: 미시작

---

### #9: 탭 UI 상수 중앙화
- **파일**: `pages/DetailPage.jsx`, `pages/OrderPage.jsx`, `pages/ReportPage.jsx`
- **문제**: TABS, REPORT_SUB_TABS, MARKET_TABS 각각 정의됨
- **영향도**: ⭐ (LOW)
- **예상 비용**: 1시간
- **효과**: `src/constants/tabs.js` 중앙화, DRY 원칙
- **상태**: 미시작

---

## 🟢 LOW 우선순위 (개선하면 좋음)

### #10: WatchlistDashboard DnD 로직 추출
- **파일**: `components/watchlist/WatchlistDashboard.jsx` (376줄)
- **문제**: @dnd-kit 드래그앤드롭 로직이 컴포넌트 내 직접 구현
- **영향도**: ⭐ (LOW)
- **예상 비용**: 1-2시간
- **효과**: `useWatchlistDnD()` 커스텀훅으로 분리
- **상태**: 미시작

---

### #11: AsyncRender 보일러플레이트 패턴화
- **파일**: 전역 (많은 컴포넌트)
- **문제**: `{loading} ? <Spinner /> : {error} ? <Error /> : {data} && <Render />` 반복
- **영향도**: ⭐ (LOW)
- **예상 비용**: 2-3시간
- **효과**: `<AsyncBoundary>` 컴포넌트 또는 `useAsyncRender()` 훅으로 패턴화
- **상태**: 미시작

---

### #12: ReportPage 섹션별 분할
- **파일**: `pages/ReportPage.jsx` (472줄)
- **문제**: 일일보고서 / 추천이력 / 성과통계 3섹션 통합
- **영향도**: ⭐ (LOW)
- **예상 비용**: 2-3시간
- **효과**: 472줄 → 3개 파일 (각 ~150줄)
- **분할**: DailyReportSection / RecommendationSection / PerformanceSection
- **상태**: 미시작

---

## ✅ 잘하고 있는 것

| 항목 | 평가 | 코멘트 |
|------|------|--------|
| **apiFetch 중앙화** | ✅ | 모든 API 호출이 `/api/client.js` 통과 |
| **useAsyncState 활용** | ✅ | 11개 훅이 일관되게 사용 (보일러플레이트↓) |
| **미사용 코드 정리** | ✅ | 죽은 import/export 거의 없음 |
| **Tailwind 원칙** | ✅ | 인라인 스타일 24건 모두 동적값만 사용 |
| **컴포넌트 재사용** | ✅ | DataTable/LoadingSpinner/WatchlistButton 통일 |

---

## 📊 구현 로드맵

```
Phase 1 (High Priority) — 이번 주
├─ #1 useOrder.js 분할                    (2-3h)
├─ #2 OrderPage 상태 번들링               (2-3h)
└─ #3 OrderForm props 정규화              (1h)
└─ Subtotal: 5-7 시간

Phase 2 (Medium Priority) — 다음 스프린트
├─ #4 FundamentalPanel 분할               (3-4h)
├─ #5 TechnicalPanel 분할                 (3-4h)
├─ #6 API 쿼리파라미터 표준화             (1-2h)
├─ #7 useBacktest/useMarketBoard/useAdvisory 분할  (2-3h)
├─ #8 TabBar 공통화                       (1-2h)
└─ #9 탭 상수 중앙화                      (1h)
└─ Subtotal: 12-18 시간

Phase 3 (Low Priority) — 백로그
├─ #10 WatchlistDashboard DnD 추출        (1-2h)
├─ #11 AsyncRender 패턴화                 (2-3h)
├─ #12 ReportPage 섹션 분할               (2-3h)
└─ Subtotal: 5-8 시간

총 예상 비용: 22-33 시간
```

---

## 📈 점수 카드

| 카테고리 | 점수 | 등급 | 주요 이슈 |
|---------|------|------|---------|
| 파일 크기 관리 | 7/10 | B | FundamentalPanel(540) / TechnicalPanel(462) |
| 훅 설계 | 8/10 | B+ | useOrder 7개 export 패킹 |
| API 일관성 | 8.5/10 | A- | 쿼리파라미터 혼재 (경미) |
| 컴포넌트 구조 | 7.5/10 | B | TabBtn 반복 코드 2곳 |
| 공통 컴포넌트 | 8/10 | B+ | 탭 UI 정규화 기회 |
| 미사용 코드 | 9/10 | A | 거의 없음 ✅ |
| 인라인 스타일 | 9/10 | A | 원칙 준수 ✅ |
| **종합** | **7.8/10** | **B+** | **신규 기능 단계에서 리팩토링 시작 권장** |

---

## 🎯 핵심 3가지

1. **useOrder.js 분할** (즉시)
   - 7개 함수 → 7개 파일로 단일책임 원칙 복구
   - 의존 컴포넌트: OrderPage, OrderForm 등 5개+
   - 비용: 2-3시간

2. **OrderPage 상태 번들링** (즉시)
   - 13개 상태 → useOrderPageState 훅으로 번들링
   - eslint-disable 3곳 제거, 의존성 배열 정리
   - 비용: 2-3시간

3. **FundamentalPanel/TechnicalPanel 분할** (다음 스프린트)
   - 540줄 / 462줄 → 각 150줄 이하로 분할
   - 섹션별 컴포넌트 추출
   - 비용: 각 3-4시간

---

**문의**: 각 항목별 상세 개선안은 `FRONTEND_AUDIT_RESULTS.md` 참조
