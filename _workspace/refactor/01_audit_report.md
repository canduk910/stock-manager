# 코드 감사 보고서

## 요약
- **감사 범위**: 전체 시스템 (백엔드 13,638줄 + 프론트엔드 9,688줄)
- **감사 일시**: 2026-04-03
- **발견 사항**: HIGH 5건, MEDIUM 6건, LOW 4건

---

## 발견 사항 (우선순위순)

### [HIGH-1] 프론트 API 래퍼 불일치 — `search.js`, `marketBoard.js`

- **문제**: `api/client.js`에 `apiFetch()` 공용 래퍼가 존재하나, `search.js`(1개)와 `marketBoard.js`(9개) 총 **10개 함수**가 `fetch()`를 직접 사용. 에러 처리 로직이 각각 다름.
  - `search.js`: 실패 시 `[]` 반환 (silent)
  - `marketBoard.js`: `throw new Error(...)` (각 함수마다 다른 메시지)
  - `apiFetch()`: 응답 body에서 `detail` 추출 후 throw
- **영향**: 에러 핸들링 불일치 → UI 에러 표시 비일관
- **도메인 자문 필요**: NO
- **리팩토링 제안**: `apiFetch()` 경유로 통일. `search.js`의 "실패 시 빈 배열" 동작은 호출측에서 처리.

### [HIGH-2] 프론트 훅 동일 패턴 대량 반복 — 전체 hooks/

- **문제**: `useState(data/loading/error)` + `try/setLoading/catch/finally` 패턴이 **최소 15개 함수**에서 동일하게 반복됨.
  - `useBalance`, `useScreener`, `useDetailReport`, `useMacroIndices/News/Sentiment/InvestorQuotes` (4개), `useBuyable`, `useOpenOrders`, `useExecutions`, `useOrderHistory`, `useOrderSync`, `useReservations`, `useAdvisoryStocks` 등
  - 각 함수는 fetcher만 다르고 구조 100% 동일 (15~25줄)
- **영향**: 코드 중복 ~350줄. 새 API 추가 시마다 보일러플레이트 복사.
- **도메인 자문 필요**: NO (동작 변경 없음)
- **리팩토링 제안**: `useAsyncAction(fetcher)` 공통 훅 추출. 개별 훅은 1~3줄 래퍼로 축소.

### [HIGH-3] `order_service.py` 비대 — 1,338줄, 37개 함수

- **문제**: 단일 파일에 주문 발주/정정/취소, 미체결/체결 조회, 대사(reconciliation), FNO 주문, 주문 이력, 예약주문 관리가 모두 혼재.
- **영향**: 유지보수 어려움, 관심사 미분리
- **도메인 자문 필요**: **YES** — OrderAdvisor에게 "Write-Ahead 패턴 원자성이 분할로 깨지는가?" 확인 필요
- **리팩토링 제안**:
  - `order_service.py` — 공개 인터페이스 (place/modify/cancel/get_*)
  - `order_reconcile.py` — 대사/동기화 로직 (_reconcile_active_orders, _maybe_reconcile, sync_orders)
  - `order_helpers.py` — 내부 헬퍼 (_validate_market, _strip_leading_zeros, _sync_local_*)

### [HIGH-4] `quote_service.py` 비대 — 995줄, 51개 함수

- **문제**: KISQuoteManager(국내 WS) + OverseasQuoteManager(해외 WS/폴링) + 체결통보(H0STCNI0) + FNO WS + REST fallback이 단일 파일.
- **영향**: 하나의 변경이 전체에 영향, 테스트 불가능
- **도메인 자문 필요**: NO (네트워크 인프라 분리, 도메인 로직 변경 없음)
- **리팩토링 제안**:
  - `quote_service.py` — 공개 API (get_manager, get_overseas_manager, subscribe/unsubscribe)
  - `quote_kis_ws.py` — KISQuoteManager 클래스
  - `quote_overseas.py` — OverseasQuoteManager 클래스

### [HIGH-5] KIS 토큰 캐시 중복 구현

- **문제**: KIS API 토큰 발급/캐싱이 **2곳**에 독립 구현됨.
  - `routers/_kis_auth.py`: `_access_token` 글로벌 변수 (만료 시각 관리 없음)
  - `stock/advisory_fetcher.py`: `_kis_token_cache` dict (expires_at으로 TTL 관리)
- **영향**: 토큰 발급 2회 발생 가능, 캐시 전략 불일치
- **도메인 자문 필요**: NO
- **리팩토링 제안**: `advisory_fetcher.py`가 `routers/_kis_auth.py`의 `get_access_token()` 사용하도록 통합. `_kis_auth.py`에 TTL 추가.

---

### [MEDIUM-1] 라우터에서 `stock/` 패키지 직접 import (서비스 레이어 우회)

- **문제**: 7개 라우터가 서비스 레이어 없이 `stock/` 패키지를 직접 import (총 18개 import).
  - `earnings.py`: dart_fin, market, sec_filings, yf_client (4개)
  - `screener.py`: market (3개)
  - `advisory.py`: symbol_map, advisory_fetcher, yf_client (4개)
  - `search.py`: yf_client, fno_master (2개)
  - `market_board.py`: market_board, market_board_store (5개)
  - `balance.py`: market, yf_client (2개)
- **영향**: 레이어 아키텍처 위반. 비즈니스 로직이 라우터에 분산.
- **도메인 자문 필요**: NO
- **리팩토링 제안**: 단계적 서비스 레이어 추출. 우선순위: `market_board.py`(5건) → `earnings.py`(4건) → `balance.py`(2건). 단, 현재 잘 동작하는 코드이므로 급하지 않음.

### [MEDIUM-2] `watchlist_service.py` silent except pass — 7건

- **문제**: 시세/재무 조회 시 `except Exception: pass`가 7개소. 에러 발생 시 원인 추적 불가.
  - 116, 122, 138, 150, 157, 173, 216행
- **영향**: 디버깅 난이도 상승, 데이터 누락 원인 파악 불가
- **도메인 자문 필요**: NO
- **리팩토링 제안**: `except Exception as e: logger.debug(...)` 또는 최소 `logger.warning`으로 전환. 기존 동작(예외 무시) 유지.

### [MEDIUM-3] `order_service.py` silent except pass — 3건

- **문제**: `_maybe_reconcile()`, `_reconcile_active_orders()` 내에서 `except Exception: pass` 3건 (1100, 1150, 1154행).
- **영향**: 대사 실패 시 원인 파악 불가
- **도메인 자문 필요**: **YES** — 대사 실패를 로깅하면 로그 과다 발생하는가?
- **리팩토링 제안**: `logger.warning` 전환 (대사 실패는 비치명적이나 추적 필요)

### [MEDIUM-4] 프론트 비대 컴포넌트 — 6개

- **문제**: 300줄 이상 컴포넌트 6개.
  - `OrderPage.jsx` (531줄) — 5개 탭 + 공유 상태 + 폴링 + WS
  - `FundamentalPanel.jsx` (509줄) — 사업개요 + 추정치 + 계량지표 + 재무 3종
  - `WatchlistDashboard.jsx` (374줄) — DnD + 테이블 + 모달
  - `FinancialTable.jsx` (365줄) — 10년 재무 + 통화 분기
  - `TechnicalPanel.jsx` (359줄) — 차트 5종 + 시그널 카드
  - `OrderForm.jsx` (313줄) — KR/US/FNO 분기 + 유효성 검증
- **영향**: 단일 컴포넌트 책임 과다
- **도메인 자문 필요**: NO
- **리팩토링 제안**: 우선순위 기준 — `FundamentalPanel`(섹션별 하위 컴포넌트 추출) → `OrderPage`(탭별 로직 추출)

### [MEDIUM-5] 라우터 예외 처리 불일치

- **문제**: 서비스 레이어는 `ServiceError` 계층을 완벽히 준수(0건 HTTPException). 그러나 라우터에서는 **34건**의 `raise HTTPException`이 직접 사용됨.
  - `earnings.py` 7건, `screener.py` 5건, `advisory.py` 6건, `watchlist.py` 6건, `detail.py` 6건, `market_board.py` 2건, `order.py` 1건
  - `main.py`의 ServiceError 핸들러와 중복 처리 가능성
- **영향**: 예외 계층 일관성 미흡
- **도메인 자문 필요**: NO
- **리팩토링 제안**: 라우터의 HTTPException 중 서비스로 이동 가능한 것을 점진적으로 ServiceError로 교체. 422(유효성)은 라우터에 유지 가능.

### [MEDIUM-6] `advisory_fetcher.py` — 데이터 수집 + 기술지표 계산 혼합 (693줄)

- **문제**: OHLCV fetch(KIS/yfinance) + 기술지표 순수 계산(_ema, _sma, _rsi, _stoch, _bollinger, _atr, calc_technical_indicators) + 사업 매출비중(fetch_segments_kr) 이 단일 파일에 혼합.
- **영향**: 기술지표 함수는 순수 계산이므로 단위 테스트 가능하나, fetch와 결합되어 테스트 어려움.
- **도메인 자문 필요**: **YES** — MarginAnalyst에게 "기술지표 계산이 fetch context에 의존하는 부분이 있는가?" 확인
- **리팩토링 제안**: `stock/indicators.py` 분리 (순수 함수만)

---

### [LOW-1] `wrapper.py` 비대 (1,588줄, 47함수)

- **문제**: KIS API 전체 래퍼가 단일 파일. REST + WS 클래스 혼합.
- **영향**: 탐색 어려움. 단, standalone 모듈이라 의존성 적음.
- **도메인 자문 필요**: NO
- **리팩토링 제안**: 현행 유지. standalone 설계 의도 존중. 필요 시 REST/WS 분리.

### [LOW-2] `market_board.py` 라우터에서 store 직접 접근

- **문제**: `routers/market_board.py`가 `stock/market_board_store.py`를 직접 import (서비스 레이어 없음).
- **영향**: 레이어 위반이나, CRUD만 수행하므로 서비스 레이어 추가는 과도.
- **도메인 자문 필요**: NO
- **리팩토링 제안**: 현행 유지. 단순 CRUD에 서비스 레이어는 불필요한 추상화.

### [LOW-3] `useMarketBoardWS.js` — 미사용 가능성

- **파일**: `frontend/src/hooks/useMarketBoardWS.js` (2,387줄)
- **문제**: `useMarketBoard.js`에 WS 기능 통합 여부 확인 필요
- **도메인 자문 필요**: NO
- **리팩토링 제안**: 사용처 확인 후 중복이면 제거

### [LOW-4] import 정리 / 미사용 import

- **문제**: 일부 파일에 미사용 import 잔존 가능 (상세 스캔 미실시)
- **도메인 자문 필요**: NO
- **리팩토링 제안**: 자동 도구(autoflake) 적용

---

## 도메인 자문 필요 항목 정리

| # | 대상 | 자문 대상 | 질문 |
|---|------|----------|------|
| 1 | order_service.py 분할 | OrderAdvisor | Write-Ahead 패턴 원자성이 파일 분할로 깨지는가? _reconcile → 별도 모듈 이동 시 _last_reconcile_ts 공유 문제는? |
| 2 | order_service.py silent pass | OrderAdvisor | 대사 실패 로깅이 운영 환경에서 로그 과다를 유발하는가? |
| 3 | advisory_fetcher.py 지표 분리 | MarginAnalyst | 기술지표 계산이 OHLCV fetch context에 의존하는 부분이 있는가? calc_technical_indicators()를 독립 모듈로 분리해도 안전한가? |

---

## 정량 요약

| 구분 | 항목 | 수치 |
|------|------|------|
| 백엔드 | 전체 Python LOC | 13,638 |
| 백엔드 | 500줄+ 파일 | 5개 (wrapper 1,588 / order_service 1,338 / quote_service 995 / yf_client 772 / advisory_fetcher 693) |
| 백엔드 | HTTPException in 라우터 | 34건 (서비스: 0건 ✓) |
| 백엔드 | silent except pass | 10건 (watchlist 7 + order 3) |
| 백엔드 | 라우터→stock 직접 import | 18건 (7개 라우터) |
| 백엔드 | 토큰 캐시 중복 | 2개소 |
| 프론트 | 전체 JS/JSX LOC | 9,688 |
| 프론트 | 300줄+ 컴포넌트 | 6개 |
| 프론트 | 직접 fetch (apiFetch 미경유) | 10개 함수 |
| 프론트 | 동일 훅 패턴 반복 | 15개+ 함수 |
