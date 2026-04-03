# stock-manager 리팩토링 핫스팟 (2026-04-03 기준)

코드 감사에서 식별된 주요 리팩토링 후보. refactor-engineer가 실행 전 참조한다.

## 우선순위 TOP 10

### 1. [HIGH] order_service.py 분할 (1,338줄, 37함수)

**현재 구조**: 주문 발주 + 정정/취소 + 대사/동기화 + 검증 + KR/US/FNO 분기가 단일 파일에 혼재.

**제안**:
```
services/order_service.py          — 공개 API (place, modify, cancel, list) + 시장별 디스패치
services/order_sync_service.py     — _maybe_reconcile(), _sync_local_*, sync_orders()
services/order_validation.py       — _validate_market(), _strip_leading_zeros() 유틸
```

**도메인 주의**: Write-Ahead 패턴(`PENDING → PLACED/REJECTED`)은 order_service.py에 유지 필수. 분리 시 원자성 깨질 위험.

**자문 대상**: OrderAdvisor

---

### 2. [HIGH] 프론트 공통 훅 추출 (6개 동일 패턴)

**현재**: useBalance, useEarnings, useScreener, useDetail, useMarketBoard, useMacro가 동일한 `useState+useCallback+try/catch` 패턴 반복.

**제안**: `useAsyncData(fetcher, deps)` 공통 훅 추출.

**도메인 자문 불필요**: UI 패턴 변경, 비즈니스 로직 영향 없음.

---

### 3. [HIGH] API 래퍼 일관성 (search.js)

**현재**: `search.js`만 `apiFetch()`를 사용하지 않고 직접 `fetch()` 호출. 에러 시 빈 배열 반환 (다른 모듈은 에러 throw).

**제안**: `apiFetch()` 경유로 통일. 빈 배열 fallback은 훅 레벨에서 처리.

**도메인 자문 불필요**: 에러 처리 통일.

---

### 4. [MEDIUM] advisory 관심사 분리 (advisory_fetcher.py 693줄)

**현재**: OHLCV fetch + 8개 기술지표 계산 함수가 한 파일에 혼재.

**제안**:
```
stock/advisory_fetcher.py  — OHLCV fetch + ���이터 수집
stock/indicators.py        — 순수 함수: calc_macd, calc_rsi, calc_stochastic, calc_bb, calc_ma
```

**도메인 주의**: `calc_technical_indicators()`가 fetch 결과에 의존하는 부분 확인 필요.

**자문 대상**: MarginAnalyst

---

### 5. [MEDIUM] 프론트 OrderContext 추출

**현재**: OrderPage(531줄)에서 symbol/symbolName/market 상태를 12개 하위 컴포넌트에 props 전달.

**제안**: `OrderContext` + `useOrderContext()` 훅으로 prop drilling 제거.

**도메인 자문 불필요**: 상태 관리 패턴 변경.

---

### 6. [MEDIUM] yf_client.py 구조화 (772줄, 17함수)

**현재**: 데이터 검증(`_safe()`, `_safe_int()`), fetch, 변환이 한 파일에 혼재.

**제안**: 함수 그룹핑으로 영역 분리 (같은 파일 내 섹션화 또는 분할).

**도메인 주의**: `fetch_segments_yf()` 반환 타입이 `fetch_segments_kr()`와 최근 통일됨(dict). 분리 시 호환성 유지.

**자문 대상**: MarginAnalyst

---

### 7. [MEDIUM] KIS 토큰 캐시 통합

**현재**: `stock/advisory_fetcher.py`의 `_kis_token_cache`와 `services/quote_service.py`의 토큰 관리가 별도.

**제안**: `routers/_kis_auth.py`의 기존 토큰 관리로 통합, 또는 공통 토큰 캐시 모듈.

**도메인 자문 불필요**: 인프라 통합. 단, KIS 분당 1회 토큰 제한 고려.

---

### 8. [LOW] 캐시 TTL 상수화

**현재**: 각 모듈에 하드코딩된 TTL.
```python
# market.py: cache_ttl=21600 (6h)
# advisory_fetcher.py: cache_ttl=3600 (1h)
# yf_client.py: cache_ttl=86400 (24h)
```

**제안**: `config.py`에 `CACHE_TTL_*` 상수 추가 + 주석으로 도메인 이유 기록.

**도메인 자문 필요**: 각 TTL 값이 데이터 소스 갱신 주기와 맞는지 확인.

**자문 대상**: MacroSentinel (매크로 TTL), MarginAnalyst (advisory/기술지표 TTL)

---

### 9. [LOW] DB Store 베이스 클래스

**현재**: 6개 store가 각각 `connect()` + `CREATE TABLE` + CRUD 보일러플레이트 반복.

**제안**: `BaseStore` 클래스 + `_init_schema()` 템플릿 메서드.

**도메인 자문 불필요**: 인프라 추상화. 단, 각 store의 특수 로직(cache.py의 NaN 처리 등) 보존.

---

### 10. [LOW] 쿼리 파라미터 빌더

**현재**: 프론트에서 URL 구성 방식 3종 혼재.
```javascript
// 방식 1: URLSearchParams (earnings.js)
// 방식 2: 문자열 연결 (advisory.js)
// 방식 3: 템플릿 리터럴 (order.js)
```

**제안**: `buildUrl(base, params)` 유틸 함수 추가.

**도메인 자문 불필요**: UI 유틸리티.

---

## 변경 불가 항목 (도메인 이유)

| 항목 | 이유 |
|------|------|
| KR/US/FNO 주문 로직 분기 | 각각 다른 KIS TR_ID + 파라미터 규격. 통합 시 파라미터 꼬임 위험 |
| 잔고 조회 국내/해외/FNO 별도 처리 | KIS API가 별도 엔드포인트. 응답 shape도 다름 |
| pykrx/yfinance 이중 fallback | KRX 서버 불안정 대응. 제거 시 서비스 중단 위험 |
| advisory_store/cache 분리 | advisory는 영구 데이터, cache는 TTL 만료 데이터. 생명주기가 다름 |

---

## 모범 사례 파일 (리팩토링 시 참조)

| 파일 | 라인 | 특징 |
|------|------|------|
| `stock/db_base.py` | 41 | 단일 책임, 깔끔한 인터페이스 |
| `services/exceptions.py` | 42 | 명확한 계층 구조 |
| `frontend/src/api/client.js` | 23 | 최소한의 래퍼, 재사용 용이 |
