# 변경 이력

## 2026-06-02 — CI 차단 hotfix (통합 테스트 누락 보완)

### 버그 수정 — 어제 변경에서 누락된 integration 테스트

- **CI 실패 원인**: `tests/integration/test_stock_info_repo.py::TestStockInfoStale::test_is_stale_fresh`가 여전히 `price` field로 fresh→`is_stale=False`를 기대했으나, 2026-06-01 "현재가 캐시 금지" 강화로 price는 timestamp 무관 항상 stale.
- **수정**: 동일 도메인 원칙을 integration에도 정렬. `upsert_metrics` 후 `metrics` 필드 not stale + `price` 필드는 stale 양쪽 모두 검증.
- 영향 파일: `tests/integration/test_stock_info_repo.py` 1개. 운영 코드 무변경.

## 2026-06-01 — 관심종목 현재가 stale 결함 제거 (현재가 캐시 금지 강화)

### 버그 수정 — 관심종목 목록/상세 현재가가 과거 시점 데이터 표시

**증상**: 관심종목 목록과 상세 페이지의 "현재가" 컬럼이 장중에도 수 분~수 시간 묵은 가격을 보여줌. F5 새로고침해도 즉시 갱신되지 않음.

**진단** (read-only 코드 추적, 6개 캐시 레이어 발견):
1. **`stock/market.py:fetch_detail()` 6시간 캐시** — 가장 큰 주범. `market:detail:` 캐시키에 `**price` 통째 묶어 6h 보관 → DetailPage 첫 진입 후 6시간 동안 같은 가격 노출. `fetch_price` 자체는 짧은 TTL이지만 우회됨.
2. **`db/repositories/stock_info_repo.py:is_stale_from_dict()`** `_is_kr_trading_hours()`만 사용 — 미국 종목도 한국 거래시간 기준 판정. 미국 정규장(KST 22:30~05:00) 중에는 항상 `off` 분기 → price TTL=30분 적용으로 stale 노출.
3. `stock/market.py:fetch_price()` — `market:price:` 캐시 (장중 5s / 장외 30m). 장외 30분이 길게 느껴짐.
4. `stock/yf_client.py:fetch_price_yf()` — `yf:price:` 동일 TTL 정책.
5. `stock/market.py:fetch_prices_batch()` — `_prices_batch_cache` in-memory TTL (장중 10s / 장외 60s).
6. `services/_dashboard_cache.py` — dashboard 응답 전체 사용자별 5s TTL.

**사용자 결정**: "현재가에는 캐시 적용예외. 무조건 api호출하도록 적용" — 모든 가격 캐시 레이어 무력화.

#### 변경 — 6개 캐시 레이어 우회

| 파일 | 변경 |
|---|---|
| `stock/market.py:fetch_price()` | `market:price:` 캐시 read/write 제거. 매 호출 yfinance fast_info 호출. refresh=True는 `kr_yf_ticker` 보조 캐시만 무효화. |
| `stock/market.py:fetch_detail()` | 가격은 매 호출 `fetch_price()`로 신선 값. 메타(market_type/sector/high_52/low_52/per/pbr)만 `market:detail_meta:` 별도 캐시키로 6h 유지. 응답 dict는 `{**meta, **price}` 병합. |
| `stock/market.py:fetch_prices_batch()` | `_prices_batch_cache` in-memory dict read/write 제거. 매 호출 yfinance Tickers + KIS 폴백. |
| `stock/yf_client.py:fetch_price_yf()` | `yf:price:` 캐시 read/write 제거. KIS 우선 / yfinance 폴백 양 경로 모두. |
| `db/repositories/stock_info_repo.py:is_stale_from_dict()` | `field=="price"` 분기 추가 — timestamp 무관 무조건 True 반환. 영속 캐시 우회. metrics/financials/returns는 기존 TTL 유지. |
| `services/_dashboard_cache.py` | `get()`→항상 None, `set()`→no-op. 모듈 시그니처 보존하여 호출 측 무변경. |

#### 회귀 가드 (4개 단위 테스트 재작성)

- `tests/unit/test_dashboard_cache.py` — `TestDashboardCacheDisabled`로 전면 재편. `get_always_none` / `set_is_noop` / `each_call_hits_service` (라우터가 매 호출 service 호출 확인).
- `tests/unit/test_watchlist_partial_failure.py::test_price_always_calls_external_api` — stock_info에 1초 전 fresh price가 있어도 `fetch_price` 호출되어야 함 (metrics/financials는 stock_info hit 유지).
- `tests/unit/test_market_prices_batch.py::test_cache_disabled_external_called_each_call` — 동일 코드 연속 호출 시 외부 호출 2회 확인.
- `tests/unit/test_stock_info_freshness.py` — `test_price_always_stale_regardless_of_timestamp` 추가. 기존 `test_recent_price_is_fresh_during_trading`/`test_explicit_now_parameter`/`test_off_hours_uses_off_ttl`는 의미 상실 → metrics 영역 검증으로 재편.

**테스트 결과**: 영향 32건 PASS / 전체 단위 테스트 1508 PASS (사전 결함 `pdfplumber` 미설치 2건만 잔존, 변경 무관).

#### 흐름 변경 영향

- **관심종목 목록**: 매 새로고침 시 `fetch_price`/`fetch_price_yf` → 즉시 yfinance/KIS 호출. 미국 종목도 한국 거래시간 무관 매번 새 값.
- **DetailPage**: 기존 6시간 묵은 detail 캐시 → price는 매 호출, 메타(sector/52w)는 6h 유지.
- **시세판**: 다중심볼 batch도 매 호출 외부 API. KIS 폴백 N≤20 가드는 유지.
- **swap thrashing 보호**: dashboard cache 제거 후 `watchlist_service.py` ThreadPool max_workers=4로만 보호.

#### 도메인 자문 부재 (사용자 직접 결정)

부서장 라우팅으로 진단(유형 C/D 후보)을 수행했으나, 사용자가 "현재가 캐시 적용예외" 명시적 결정으로 도메인 전문가 호출 생략. `현재가 캐시 금지 도메인 원칙`은 이미 기존 주석에 명시되어 있었으나 5s/30m TTL로 우회되고 있던 것을 강화.

---

## 2026-05-18 — 호가 미수신 결정적 원인 규명 (시계 + WS URL)

### 버그 수정 — 호가창 빈 화면 본진 결함 2건 동시 발견·수정

**배경**: 어제 추가한 silent failure 차단(`ffef462`)을 로컬 docker로 검증하던 중, 사용자 보고가 시간 무관 지속 → **시간 무관**의 진짜 의미는 "휴장 시간대"였음. 시계 결함이 풀린 후에야 WS 결함이 표면화. 두 결함은 별개 원인이고 누적 효과로 사용자에게 같은 증상으로 보였다.

#### Phase 1 — 시계 결함 (`frontend/src/hooks/useMarketClock.js`)

**진단** (사용자 화면 캡처 "통합 (휴장)" 라벨 + 한국 14:50 시각 정보로 모순 발견):
```js
// 결함 코드
const KST_OFFSET_MIN = 9 * 60
function toKstDate(now) {
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60000  // KST 브라우저: offset=-540 → 9h 뒤로 돌림
  return new Date(utcMs + KST_OFFSET_MIN * 60000)
}
// KST 브라우저 14:50 → minutes=350 → CLOSED 분기 → "통합(휴장)" 표시
```

`getTimezoneOffset()` MDN 정의는 `UTC = local + offset`인데, epoch ms에 그대로 더하면 의미 없는 시간 연산. KST 브라우저(`offset=-540`)에서 시간을 9시간 뒤로 돌려, 평일 14:50을 새벽 05:50(=350분)으로 잘못 판정 → `CLOSED` 분기로 떨어져 `isClosed=true` + `exchange='UN'` → 화면에 "🟦 통합 (휴장)" 잘못 표시.

**부수 영향**: `useMarketBoard.js`의 `usePricePolling`이 `clock.phase === 'UN'` 분기로 장중 15s / 장외 60s를 결정 → 평일 장중에도 60s 잘못 폴링하여 시세판 갱신 4배 느림.

**수정**: `Intl.DateTimeFormat({timeZone: 'Asia/Seoul'})` `formatToParts`로 KST wall clock 추출 (`useUsMarketClock`이 이미 사용 중인 패턴과 일관). 브라우저 timezone과 무관하게 동일 결과 보장.

**검증** (8개 경계 케이스 node 직접 실행):
```
월 14:50 (장중)    → UN ✓ (이전: CLOSED)
월 09:00 (정각)    → UN
월 15:30 (마감)    → KRX_CLOSE
월 15:40 (NXT)     → NXT_AFTER
월 20:00 (장 마감) → CLOSED
월 07:59 (장외)    → CLOSED
토/일 14:00 (주말) → CLOSED(주말)
```

#### Phase 2 — WS URL `?` 중복 결함 (`frontend/src/hooks/useQuote.js`)

**진단** (Phase 1 fix 후에도 "● 연결 중..." 무한 지속. `/api/admin/quote-status`로 백엔드 정상 확인 → `subscriber_count: 0` → 클라이언트 WS 연결 자체 실패. `routers/quote.py`에 임시 print 진단 삽입 후 사용자 새로고침 → 로그에서 결정적 단서):

```
[DIAG] verify_token JWTError: JWTError: Signature verification failed.
       (expected_type=access, token_head=eyJhbGciOiJIUzI1NiIs...
        token_tail=...MjpKoE?exchange=auto)  ← 토큰 끝에 ?exchange=auto가 흡수됨
```

`useQuote.js`의 buildUrl 결함:
```js
// 결함 코드
const base = buildWsUrl(`/ws/quote/${symbol}`)  // → ws://.../ws/quote/005930?token=eyJ...
const params = []
if (exchange === 'auto') params.push('exchange=auto')
return `${base}?${params.join('&')}`  // → ws://.../ws/quote/005930?token=eyJ...?exchange=auto
                                       //                                  ↑      ↑
                                       //                       buildWsUrl이 ?    useQuote가 또 ?
```

백엔드 query parser는 첫 `?`만 separator로 인식하고 나머지는 한 줄로 파싱 → `token = "eyJ...MjpKoE?exchange=auto"` (토큰 값에 `?exchange=auto` 흡수) → JWT 서명 검증 실패 → 1008 close 반복.

**HTTP API는 무영향** — Authorization 헤더로 토큰 전달하므로 URL 결함과 무관. 잔고 등 API가 정상 동작하면서 WS만 거부되어 결함 위치를 잘못 추적하기 쉬웠음. 표면화 시점은 시계 결함이 풀려 "통합(휴장)" 라벨이 정상화된 직후 — 이전엔 휴장 라벨 때문에 사용자가 WS를 진지하게 기대하지 않았음.

**수정**: query 파라미터를 path 안에서 먼저 합친 후 `buildWsUrl` 한 번만 호출. buildWsUrl이 `path.includes('?')` 체크로 자동으로 `&token=...` 부착 → URL `?` 1회만 등장.

```js
// 수정 코드
const params = []
if (market === 'FNO') params.push('market=FNO')
if (exchange === 'auto') params.push('exchange=auto')
const path = params.length
  ? `/ws/quote/${symbol}?${params.join('&')}`
  : `/ws/quote/${symbol}`
return buildWsUrl(path)  // path?exchange=auto&token=eyJ...
```

**검증**: 로컬 docker 재빌드(`docker compose up --build -d`) → 사용자 hard reload → "🟢 NXT" 라벨 + "● 실시간" 초록색 + 005930 호가 실시간 수신 확인.

**도메인 원칙 회복**: silent failure → loud failure(어제 ffef462). 어제 추가한 1008 자동 logout 가드 + manager `getattr` 방어 + `/api/admin/quote-status` 진단 엔드포인트가 본진 결함 좁히기에 결정적 기여.

---

## 2026-05-18 — 호가 silent failure 차단 + 1008 자동 logout

### 버그 수정 — 호가창 빈 화면 결함의 단일 점 진단 보강

**배경**: 사용자 보고 — 주문 페이지 호가창에서 KR/US/FNO 모든 시장, 시간 무관 지속, 호가·현재가 둘 다 미수신. 모든 시장 동시 결함이라 시장별 파이프라인이 아니라 공통 진입점(WS 인증/KISQuoteManager/운영자 KIS 키) 단일 점 결함이 후보. 코드 검증 결과:
- `services/quote_kis.py:144-146` — `start()`에서 KIS 키 미설정 시 `logger.warning` 1줄 후 silent return → `_running=False` → subscribe 호출돼도 무한 침묵 (사용자에게 빈 호가창만 보임).
- `frontend/src/hooks/useWebSocket.js:77-87` — 1008(Policy Violation, JWT 만료) close 후 무한 백오프 재시도. refresh/logout 분기 부재 → JWT 만료 후에도 stale token으로 재시도 누적.
- `routers/quote.py:32-41` — WS 핸들러에 ContextVar `set_current_user_id` 호출 부재 → `_stream_overseas`가 user_id=None으로만 운영자 키 사용 (멀티계좌 사용자 키 미적용).

**수정** (silent failure → loud failure 원칙, 어느 가설이 확정되든 안전한 개선):

1. **`services/quote_kis.py`** — `KISQuoteManager` 진단 보강:
   - `start()` KIS 키 미설정 시 `logger.warning` → `logger.error` 승격 + `_start_failed_reason` 인스턴스 변수에 사유 보관 (SSM Parameter Store 점검 안내 로그 포함).
   - `_connect_loop` 연속 실패 카운터(`_consecutive_connect_failures`) + 5회 연속 시 `logger.critical` 1회(스팸 방지) → KIS 키 만료/quota 초과/네트워크 차단 알람. backoff 상한 30s → 60s.
   - `_get_approval_key` HTTP non-200 / JSON 파싱 실패 / approval_key 필드 부재 3분류 `RuntimeError`(상세 메시지) → `_connect_loop` 사유 식별 가능.

2. **`routers/quote.py`** — WS 핸들러 ContextVar + manager 상태 검증:
   - JWT verify 성공 시 `payload["sub"]`로 `set_current_user_id(user_id)` 호출 → quote_overseas가 사용자별 KIS REST 키 사용.
   - KR/FNO 진입 전 `manager._running=False`이면 `{"type":"error","message":...}` 송신 후 `close(1011)` → 프론트가 빨간 배너로 사유 표시(빈 호가창 차단).

3. **`routers/admin.py`** — `GET /api/admin/quote-status` 진단 엔드포인트 신규 (`require_admin`):
   - `kis_manager.{running, ws_connected, fallback_mode, subscriber_count, subscribed_symbols, approval_key_age_sec, consecutive_connect_failures, start_failed_reason}` + `overseas_manager.{running, subscriber_count}` 반환.
   - 원인 식별 + 향후 회귀 모니터링 양쪽 효용.

4. **`frontend/src/hooks/useWebSocket.js`** — 1008 자동 logout 회귀 가드:
   - `_tryRefreshForWs()` 모듈 내부 helper — `_refreshing` race 방지 싱글톤 promise.
   - `onclose` 분기: `event.code === 1008` → refresh 시도 → 성공 시 backoff 리셋 + 즉시 재연결(lazy URL 새 토큰 박힘) / 실패 시 localStorage 클리어 + `/login` 리다이렉트 (client.js와 동일 정책).
   - 기타 비정상 종료(1006/1011 등)는 기존 지수 백오프 유지.

5. **`frontend/src/hooks/useQuote.js`** — `type:"error"` 메시지 핸들:
   - `EMPTY_STATE.errorMessage` 추가 → `setState({errorMessage: msg.message})`.

6. **`frontend/src/components/order/OrderbookPanel.jsx`** — silent 빈 호가창 차단:
   - `errorMessage` 수신 시 헤더 위 빨간 ⚠ 배너 (`bg-red-50 border-red-200`) → 사용자가 즉시 사유 인지.

**검증**:
- 신규 단위 테스트 `tests/unit/test_quote_start_failure.py` 6/6 PASS — start() 사유 노출 + ERROR 로그 + approval_key 응답 분류 3종 + 카운터 초기값.
- `tests/unit/test_quote_kis_exchange.py` 21/21 PASS (기존 회귀 가드).
- 전체 `pytest tests/unit/` baseline 사전 결함(pytest-asyncio + pdfplumber 미설치 25건)을 제외하면 신규 결함 0.

**후속 hotfix — CI 회귀 2건 (`tests/api/test_quote_ws_exchange.py`)**:
- 원인: `routers/quote.py:57` 매니저 상태 검증이 `manager._running` / `manager._start_failed_reason` 속성을 직접 접근. 테스트 `FakeManager`(이 두 속성 미정의)에서 AttributeError → outer except로 빠져 subscribe 호출 누락 → 빈 dict 응답으로 assertion 실패.
- 수정: `getattr(manager, "_running", True)` / `getattr(manager, "_start_failed_reason", None)` 방어 fallback. 실제 KISQuoteManager는 두 속성을 명시 정의하므로 운영 동작 동일, mock manager만 호환.
- 검증: `tests/api/test_quote_ws_exchange.py` 3/3 + `tests/unit/test_quote_start_failure.py` 6/6 PASS.

**운영 진단 가이드** (사용자 후속):
- `aws sso login` 후 `aws ssm send-command ... docker logs ... grep "QuoteService|approval_key|WS 오류|tokenP"` → 가설 2/3 결정적 신호 식별.
- 또는 배포 후 `GET /api/admin/quote-status` 1회 호출 → 즉시 manager 상태 확인.
- JWT 만료(가설 1) 시 1008 자동 logout으로 사용자 추가 액션 불필요.

---

## 2026-05-18 — CI flaky test 수정 (price freshness 시간 의존)

### 버그 수정 — CI 백엔드 테스트 2건 실패 hotfix

**배경**: GitHub Actions `54b04de` Deploy/CI 모두 failure. pytest 결과 2/2026 fail.
- `test_stock_info_freshness.py::test_recent_price_is_fresh_during_trading` — `is_stale_from_dict` True 반환 (기대: False)
- `test_watchlist_partial_failure.py::test_all_fresh_skips_external_api` — price=None, "should not be called" 외부 API 호출 발생

**원인**: 2430c0a 커밋 "관심종목 현재가 캐시 제거 (도메인 원칙 정합)"에서 `_TTL["price"]["trading"] = 0.0014h = 5초` (현재가 캐시 금지 도메인 원칙)로 줄였으나, 두 테스트가 여전히 **5분 전 timestamp를 fresh로 가정**. CI 실행 시각이 평일 KST 10:13(trading hours)이라 발현된 flaky test — 이전 4개 커밋(8089c87/aab3762/c28177f/899ec4a)은 off-hours에 실행되어 30분 TTL로 우연히 통과.

**수정**:
- `tests/unit/test_stock_info_freshness.py::test_recent_price_is_fresh_during_trading` — `datetime(2026, 5, 4, 14, 0, 0)` 평일 trading 14:00 고정 + `now=now` 명시 주입 + timestamp 2초 전(5초 TTL 내). 시간 의존성 제거로 결정적 통과.
- `tests/unit/test_watchlist_partial_failure.py::test_all_fresh_skips_external_api` — `_fetch_dashboard_row` 내부는 `now` 주입 불가하여 timestamp를 1초 전으로 변경 (trading 5초 / off 30분 둘 다 fresh 보장). 주석에 회귀 가드 명시.

**검증**: `pytest tests/unit/test_stock_info_freshness.py tests/unit/test_watchlist_partial_failure.py` → 17/17 PASS.

---

## 2026-05-18 — 매크로 장단기 금리차 차트에 10Y 금리 추이 오버레이

### UI 개선 — YieldCurveSection 스프레드 + 10Y 듀얼 축

**배경**: 사용자 요청. 장단기 금리차(10Y-3M 스프레드) 추이 그래프에 10Y 금리 추이를 겹쳐 표시하여 "스프레드 좁아짐이 10Y 하락 때문인지 3M 상승 때문인지" 직관적 판단 가능하게.

**변경** (`frontend/src/components/macro/YieldCurveSection.jsx` 단일 파일):
- 백엔드 변경 0 — 응답 history에 이미 `y10y` 포함됨 (`stock/macro_fetcher.py:490`)
- `SpreadHistoryChart`: `AreaChart` → `ComposedChart` 전환
- 이중 Y축:
  - 좌축 (`yAxisId="spread"`): 기존 스프레드 Area + 0% ReferenceLine 유지
  - 우축 (`yAxisId="y10y"`, `orientation="right"`): 10Y 금리 Line (#6366f1 indigo, strokeWidth 1.5)
- `<Legend>` 추가 — "10Y-3M 스프레드" / "10Y 금리" 자동 구분
- NBER 침체 / S&P 약세장 ReferenceArea에 `yAxisId="spread"` 명시 — 음영 좌축에 고정 (충돌 회피)
- 헤더: "10Y-3M 스프레드 추이" → "10Y-3M 스프레드 + 10Y 금리 추이"

**검증**: 프론트 빌드 PASS, 도커 재빌드 + 사용자 확인 대기. 별도 스케일이라 스프레드 음수 구간과 10Y 절대 수준이 시각적으로 충돌 없음.

---

## 2026-05-17 — 사용자별 일별 접속현황 admin 기능 + 섹터 진단 범례 개선

### 신규 기능 — 사용자별 일별 접속현황

**배경**: 관리자가 사용자별 활동 패턴(어느 날 몇 회 접속, 어느 페이지 주로 이용)을 파악할 수 있어야 함. 기존 `/admin/users`는 누적 visit_count만, `/admin/page-stats`는 전체 통합 통계만 제공.

**도메인 자문**: minimal — admin 통계라 권고안 100% 채택(투자 도메인 4명 자문 생략).

**신규 API** (`routers/admin_users.py`):
- `GET /api/admin/users/{user_id}/access-history?days=7|30|90|180&top_paths=5`
- 응답: `{user_id, username, last_seen_at, total_views, daily: [{date, views, unique_paths}], top_paths: [{path, views}]}`
- 권한: `require_admin`. `user_id IS NOT NULL` 필터로 익명 제외. 연속 시계열 padding(데이터 없는 날도 `{views: 0, unique_paths: 0}`).

**PageViewRepository 신규 메서드 3개** (`db/repositories/page_view_repo.py`):
- `user_daily_timeseries(user_id, days)` — 사용자별 일자별 PV + 고유 path 수
- `user_top_paths(user_id, days, limit)` — 상위 N path
- `user_last_seen_at(user_id)` — 마지막 접속 시각 (days 무관 전체 누계)
- 기존 `(user_id, created_at)` 인덱스 활용 (별도 인덱스 추가 불필요)

**프론트엔드**:
- `frontend/src/components/admin/UserAccessHistoryModal.jsx` (신규) — Recharts ComposedChart(PV 막대 + 고유 path 라인 보조축) + 7/30/90/180일 토글 + 상위 path 리스트
- `frontend/src/pages/AdminUsersPage.jsx` — 방문수 셀 클릭(underline + cursor-pointer) 또는 별도 "이력" 작업 버튼 → 모달
- `frontend/src/api/admin.js` — `fetchUserAccessHistory(user_id, days, top_paths)` 추가

**TDD 사이클 R1~R6, 44/44 PASS**:
- `tests/unit/test_page_view_repo_user_access.py` (신규, 16): 3 메서드 + 익명 제외 + 인덱스 + padding 보장
- `tests/api/test_admin_users_access_history.py` (신규, 16): 권한 403 / 404 / 422 / 200 응답 shape / days 4값 4건 / top_paths 정합
- 기존 admin 영역 회귀 0건 (`test_page_view_repo_count_by_user.py` 4/4, `test_admin_users_visit_count.py` 2/2, `test_admin_page_stats_api.py` 2/2)

**QA Inspector 체크리스트 11/11 PASS**: shape snake_case 정합 / `daily.length == days` / 익명 제외 / 권한 403 / 404 ServiceError 핸들러 / 인덱스 성능 / 모달 ESC+백드롭 / padding 연속성 / AbortController stale 차단 / KST 일자 경계 일관성 / 방문수 셀 시각적 underline + 별도 "이력" 버튼.

### UI 개선 — DiagnosisCard 섹터 진단 우측 범례 재구성

**배경**: 사용자 보고. "파이차트 옆 오른쪽 범례가 좀 더 직관적이었으면 좋겠어. 편중/적정/부족을 확실히 구분하고 포트폴리오에 없는 섹터도 함께 명시, 그 중 신규 편입 추천이 어디인지까지 반영."

**변경** (`frontend/src/components/advisor/DiagnosisCard.jsx`, `AdvisorPanel.jsx`):
- 우측 영역을 두 그룹으로 재구성:
  1. **보유 섹터** — `classifyAssessment(assessment)`로 텍스트 키워드 매칭:
     - "편중"/"과잉"/"과다" → 🟧 ⚠ 편중 (orange)
     - "부족"/"미흡"/"낮음" → 🟨 ↓ 부족 (yellow)
     - "적정"/기본 → 🟩 ✓ 적정 (green)
  2. **⭐ 신규 편입 추천** — `recommendations` prop(`analysis.sector_recommendations`)에서 보유 섹터에 없는 섹터만 필터. 점선 emerald 테두리 + 목표 비중 배지 + 진입 타이밍(immediate/this_week/this_month 색상) + 추천 근거 line-clamp-2.
- AdvisorPanel: `<DiagnosisCard diagnosis={...} recommendations={analysis.sector_recommendations} />` (1줄 prop 전달).
- 파이차트는 보유 섹터만 (변경 없음, 14색 cycle 유지).

**검증**: 프론트 빌드 PASS, 도커 재빌드 + 사용자 화면 확인 대기.

---

## 2026-05-17 — 매크로 미국 뉴스 번역 캐시 mismatch 버그 수정

### 버그 수정 — NYT/Google News 제목과 링크 불일치

**배경**: 사용자 보고. 매크로 페이지 미국 뉴스 섹션에서 표시된 제목과 클릭 시 열리는 링크 내용이 다름. "원문보기" 했을 때도 화면 제목과 본문이 일치하지 않음.

**원인 사슬**:
1. `_translate_headlines()` 캐시 키가 `nyt_translation` 단일 문자열로, 인덱스 0~9에 번역만 매핑 (헤드라인 텍스트와 무관)
2. 3개 캐시 계층의 TTL 불일치:
   - `fetch_nyt_news` 자체 캐시: **30분** (`macro:news:nyt_raw`)
   - `get_news` 전체 결과 캐시: **4시간** (`macro:news:full_result_v1`)
   - `_translate_headlines` 번역 캐시: **일일 KST** (`macro_store nyt_translation`)
3. 시나리오: 09:00 첫 호출 → 인덱스 0~9에 번역 캐시. 13:01 두 번째 호출(4h cache 만료) → `fetch_nyt_news` 30분 cache도 만료 → **새 기사 fetch** (다른 순서/내용) → `_translate_headlines` 일일 cache HIT → **옛 인덱스 0~9 번역 반환** → 새 기사 + 옛 번역 매핑 → 제목/링크 mismatch.

**수정** (`services/macro_service.py`):
- **번역 캐시 키 헤드라인 셋 해시화**: `nyt_translation` 단일 → `macro:nyt_translation:<sha256(headlines)[:16]>` 24h TTL. 헤드라인 셋이 1글자라도 변경 시 자동 캐시 미스 → 재번역. 순서 변경도 다른 해시 (인덱스 매핑 안전성).
- **저장소 전환**: `save_macro_today/get_macro_today` (카테고리 단일 키) → `set_cached/get_cached` (해시별 격리).
- **`_NEWS_CACHE_KEY` v1 → v2 bump**: 기존 4시간 캐시에 이미 저장된 mismatch 결과를 자동 invalidate. 운영 배포 직후 옛 캐시 자연 폐기.

**검증**:
- 가설 검증: 같은 헤드라인 셋 → 같은 해시 / 1글자 변경 → 다른 해시 / 순서 변경 → 다른 해시 (3건 모두 OK)
- 로컬 도커 재빌드 + 사용자 화면 검증 — 제목과 링크 일치 확인 PASS

---

## 2026-05-17 — 포트폴리오 UI 가독성 개선 (전체 종목 표시 + 섹터 파이차트)

### UI 개선 — ProfitChart 전체 종목 + 동적 사이즈

**배경**: 사용자 보고. 포트폴리오 화면(`/portfolio`)에서 종목이 많을 때 손실 종목이 아예 보이지 않음. 원인은 `ProfitChart.jsx:21`의 `.slice(0, 15)` — 수익률 내림차순 정렬 후 상위 15개만 표시하여 16번째 이후 손실 종목 잘림.

**변경** (`frontend/src/components/portfolio/ProfitChart.jsx`):
- `.slice(0, 15)` 제거 → 전체 보유 종목 표시
- 동적 height — `Math.max(260, data.length * 26 + 20)` (종목당 26px + 여백, 최소 260px)
- Y축 너비 동적 — `Math.min(200, Math.max(80, maxNameLen * 11 + 12))` (가장 긴 종목명에 맞춰 자동, 한글 1자 ≈ 11px)
- 종목명 잘림 제거 — `name.slice(0, 6) + '..'` 제거, 전체 표시
- `YAxis interval={0}` — Recharts 자동 라벨 생략 차단, 모든 종목 라벨 강제
- 헤더에 `(N종목)` 카운트 표시 — UX 보강
- 정렬은 수익률 내림차순 유지(위쪽 이익 빨강 / 아래쪽 손실 파랑 시각 구분)

### UI 개선 — DiagnosisCard 섹터 분석 도넛 파이차트 전환

**배경**: 사용자 보고. 포트폴리오 진단의 섹터 분석에서 섹터명 잘림(이전: `w-28 truncate` = 112px 고정 + ellipsis). 후속 요청으로 시각화도 가로 진행바 → 파이차트로 전환.

**변경** (`frontend/src/components/advisor/DiagnosisCard.jsx`):
- 가로 진행바 → **도넛 파이차트 (innerRadius=50, outerRadius=85) + 우측 평가 리스트 좌우 분할** (`md:flex-row`, 모바일 `flex-col`)
- 파이 슬라이스 외부 라벨 `${sector} ${weight_pct}%` (truncate 없음, 자동 배치)
- 14색 `SECTOR_COLORS` cycle 팔레트 — KR 14 + US 11 GICS 카테고리 모두 시각 구분
- 우측 리스트: 색상 점(슬라이스와 매칭) + 섹터명(`whitespace-nowrap`) + 비중 + assessment 평가 텍스트 동시 표시
- `SectorTooltip` — Hover 시 섹터/비중/assessment 한 번에 표시 (정보 손실 없음)

### 검증
- 프론트 빌드 PASS (`✓ built in 1.42s`)
- 회귀 가드: AllocationChart 패턴 일관, 다른 컴포넌트 변경 없음

---

## 2026-05-16 — 금융지주/금융업 데이터 보강 + PostgreSQL SEQUENCE hotfix

### 신규 기능 — 금융지주/금융업 종목 기본적 분석 정상화

**배경**: 사용자 보고. 하나금융지주(086790) 관심종목 상세에서 매출 5,525억(자산 591조 / 순이익 3.5조 대비 비정상)·영업이익률 +849%·매출원가/매출총이익/유동자산·부채 "-"·사업개요 누락. 진단 결과 `_ACCOUNT_REGEX["revenue"]`의 `보험(영업)?수익` 절(보험사 보강용)이 금융지주에서 자회사 보험사만 매칭하여 발생.

**도메인 자문 합의** (4명 전원, 9건):
- D-1: 금융지주 매출 = `이자수익 + 수수료수익 + 보험수익` 합산 (`_sum_bank_holding_revenue`)
- D-2: 업종 4-tier 자동 감지 — `detect_sector_tier(items)` (insurance → bank_holding → securities → general, 회계과목 패턴 기반, `is_insurance_company()`와 동일 위치)
- D-3: 매출원가/매출총이익/유동자산·부채 5+2행은 `sector_tier`에 따라 프론트 행 자체 숨김
- D-4: 7점 등급 산정은 본 작업 범위 외 (등급 산정 무변경, 매출 정상화로 자동 보정. PBR 임계값 분기는 후속 phase 권고)
- D-5: 사업보고서 키워드 정규식 보강 (`_REVENUE_TABLE_PATTERNS` 8개 + `_REVENUE_SECTION_PATTERNS` 3개: `부문별\s*영업이익`/`영업\s*부문`/`그룹의\s*사업영역`/`주요\s*자회사` — 086790/105560/055550 실제 헤더 검증)
- D-6: 부문 라벨 GPT hint 7카테고리 통일 (은행/카드/증권/보험/자산운용/기타금융/비금융) + `_attach_metric_field()` `revenue_share`/`operating_income_share` 분기
- D-7: `detect_sector_tier()` 헬퍼 위치 — `stock/dart_fin.py` 내부 (보험사 분기와 동일 모듈)
- D-8: MacroSentinel 본 작업 범위 외 (체제별 금융업 영향은 후속)
- D-9: OrderAdvisor 본 작업 범위 외 (위험 가드 미발동)

**변경 파일**:
- 백엔드 (5): `stock/dart_fin.py` (업종 4-tier 감지 + 금융지주 매출 합산 + BS 신규 필드 5개), `stock/dart_segments.py` (키워드 8+3 패턴 + GPT hint 7카테고리), `stock/advisory_fetcher.py` (sector_tier 응답), `services/advisory_service.py` (`_extract_sector_tier_from_fundamental`), `services/detail_service.py` (sector_tier 응답)
- 프론트 (2): `frontend/src/components/advisory/FundamentalPanel.jsx` (5+2행 조건부 미렌더), `frontend/src/components/detail/FinancialTable.jsx` (동일 prop 분기)
- 신규 테스트 (3): `test_dart_fin_sector_tier.py` (22), `test_dart_segments_bank_holding.py` (19), `test_advisory_detail_sector_tier.py` (8) — **49/49 PASS**
- 본 작업 영역 회귀 가드: 331/331 PASS / 0 FAIL (dart_fin/dart_segments/advisory/detail/safety_grade)
- 캐시 키 v3 bump: `advisor:segments_history_kr/dart:{}:{years}:v3` + `dart:segments:{}:{}:v3`

**검증 결과 (도메인팀 OPENDART 실측)**:
- 086790 하나금융지주: 28.33조원 매출, 영업이익률 17.1% (이전 5,525억 → 정상)
- 105560 KB금융: 47.43조원
- 316140 우리금융: 24.88조원
- 회귀: 보험사(032830) 11+13+6/30 PASS, 일반 제조업 변경 없음, 카카오(035720) securities 미발동 → general 분류 (의도된 폴백)

---

### 버그 수정 — 운영 PostgreSQL `user_kis_credentials.id` SEQUENCE 누락 hotfix

**배경**: 사용자가 운영(dkstock.cloud)에서 `/settings/kis` 계좌 추가 시도 시 모두 500 (21 bytes `Internal Server Error` 평문) → 502 응답. 운영 로그에 traceback 부재. AWS SSM Run Command + nginx access log 추적으로 원인 진단.

**원인 사슬**:
1. `e7f8a9b0c1d2` 마이그레이션에서 `id` 컬럼을 `add_column(autoincrement=True)`로 추가 — PostgreSQL은 **컬럼 추가 시점에 SEQUENCE 자동 생성 안 함** (CREATE TABLE 시점에만 작동)
2. 결과: PostgreSQL `user_kis_credentials.id`가 `is_identity=NO`, `column_default=NULL`, `is_nullable=NO` 상태
3. INSERT 시 id 명시 누락 → NULL → **NotNullViolation (psycopg2 IntegrityError)**
4. SQLAlchemy IntegrityError는 `ServiceError` 계층 아님 → `main.py:149` ServiceError 핸들러 미통과
5. starlette `ServerErrorMiddleware` 기본 응답 = `Internal Server Error` 21 bytes 평문 ← 운영 nginx access log에서 본 응답
6. SQLite는 `INTEGER PRIMARY KEY`로 ROWID 자동 매핑 → 로컬 정상 (운영-로컬 차이의 원인)

**수정**:
- **신규 마이그레이션 `alembic/versions/f1a2b3c4d5e6_user_kis_id_sequence.py`**:
  - PostgreSQL: `CREATE SEQUENCE IF NOT EXISTS user_kis_credentials_id_seq OWNED BY user_kis_credentials.id` + `ALTER TABLE ... ALTER COLUMN id SET DEFAULT nextval(...)` + 기존 max(id)+1 setval
  - SQLite: no-op (dialect 분기)
  - dialect 분기로 다른 DB도 안전 통과
- **`main.py` generic Exception 핸들러 추가** (`@app.exception_handler(Exception)`):
  - 미처리 예외 응답: 21 bytes 평문 → JSON `{"detail":"내부 오류가 발생했습니다.","error_id":"..."}`
  - traceback 자동 logger.error (exc_info=True)로 운영 로그에 출력 — 미래 동일 결함 즉시 진단
  - ServiceError 핸들러가 먼저 매칭되므로 ServiceError 계층 영향 없음

**검증**:
- 테스트 PostgreSQL(stock-manager-test-db, 포트 5433)에 마이그레이션 적용 → `id` 컬럼 `column_default: nextval('user_kis_credentials_id_seq'::regclass)` 정상
- 실제 INSERT 시 id 자동 부여 검증 (1, 2 순차 발급)
- 로컬 SQLite docker 재빌드 → `alembic head 일치: f1a2b3c4d5e6` (no-op 정상 통과)

**호가 문제 동반 해결 가능성**: 계좌 등록 실패로 `user_kis_credentials` 비어 있으면 `get_kis_credentials(user_id)` ConfigError(503) → WS/REST 호가 둘 다 실패 → "해외 호가 데이터 수신 중..." 무한 대기. 본 hotfix로 계좌 등록 정상화되면 호가도 자동 복구 가능성 높음.

---

## 2026-05-15 — KIS 멀티 계좌 지원 (1→N 확장, 전체 자산 합산 평가)

### 신규 기능 — 사용자 1명 N개 KIS 계좌 등록 + 합산 평가 + 계좌별 주문

**배경**: 사용자가 여러 KIS 계좌(주식/연금/IRP/ISA/CMA 등)를 보유하지만 시스템은 1사용자=1계좌로 하드코딩(`user_kis_credentials.user_id` 단독 PK). 전체 자산을 합산 평가하지 못하고 한 계좌만 사용 가능했음.

**사용자 확정 결정사항**:
1. 잔고 페이지: 전체 합산 + 계좌별 토글 (탭 UI)
2. 주문 페이지: 주문 폼 상단 계좌 선택 드롭다운
3. 계좌 식별: 사용자 지정 라벨 + 계좌번호 마스킹
4. 마이그레이션: 기존 1계좌 사용자 → 라벨 '기본', is_default=true 자동 변환

**도메인 자문 합의** (도메인 전문가 4명 전원 합의, 6건):

| ID | 결정 | 채택안 |
|----|------|--------|
| REQ-DOMAIN-01 | 포지션 사이징 자산 기준 | **합산 평가액 + 단독 예수금 이중 가드** — `total_portfolio`는 모든 계좌 합산(자산 분산 원칙), `cash_available`는 주문 계좌 단독(KIS reject 방지). 응답에 `binding_constraint: portfolio\|cash` 메타 노출 |
| REQ-DOMAIN-02 | 예약주문 동시 트리거 | **FIFO(created_at ASC) + 계좌별 독립 try/except** — `Reservation.id.desc()` → `asc()` 변경. KIS 거래소 FIFO 원칙 정합 |
| REQ-DOMAIN-03 | 잔고 갱신 범위 | 해당 계좌 + 합산 캐시 동시 invalidate (합산은 단독의 함수) |
| REQ-DOMAIN-04 | 7점 등급 계좌 영향 | **종목 단위, 계좌 무관** — `compute_grade_7point()` 변경 0줄 (확인용 invariant 테스트) |
| REQ-DOMAIN-05 | 체제별 현금 버퍼 | **사용자 합산 현금 비율** — portfolio_advisor `_build_context` 변경 0줄 |
| REQ-DOMAIN-06 | AI 자문 자산 기준 | 합산 (현재 동작 보존) + 계좌별 옵션은 후속 작업 |

### DB 스키마 변경 + Alembic 마이그레이션

**`db/models/user_kis.py` — UserKisCredentials**:
- PK `user_id` 단독 → `id` (AUTO_INCREMENT) 신규 PK
- 신규 컬럼: `label VARCHAR(50) NOT NULL` / `is_default BOOLEAN NOT NULL DEFAULT false`
- 신규 제약: `UNIQUE(user_id, label)` + 사용자당 is_default=true 최대 1개 (Repository 트랜잭션 가드)
- 기존 컬럼(app_key_enc, app_secret_enc, acnt_no_enc, acnt_prdt_cd_stk/fno, validated_at) 100% 보존

**`db/models/order.py` — Order / Reservation**:
- 신규 컬럼: `account_label VARCHAR(50) NULL` (기존 row는 NULL, 라우터 조회 시 default 폴백)
- `(user_id, account_label)` 복합 인덱스 (쿼리 성능)

**`alembic/versions/e7f8a9b0c1d2_multi_account_kis_credentials.py`**:
- 기존 1계좌 사용자 → 라벨 '기본' + is_default=true 자동 변환
- SQLite 호환 위해 `op.batch_alter_table` 사용
- entrypoint.sh `alembic upgrade head` 자동 실행 (lifespan 통합)

### Repository / Auth / Router 멀티 계좌화

**`db/repositories/user_kis_repo.py`**: 신규 9 API (`get_default`/`get_by_label`/`list_accounts_masked`/`create_account`/`update_account`/`delete_account`/`set_default_account`/`mark_validated_label`/`get_masked_by_label`) + 백워드 호환 5 (`upsert`/`get`/`mark_validated`/etc).

**`db/repositories/order_repo.py`**: `insert_order(..., account_label)` + `list_orders(user_id, account_label=None)` 인자 확장 + `list_reservations()` 정렬 `id.asc()` (REQ-DOMAIN-02 FIFO).

**`routers/_kis_auth.py`** (R2):
- `get_kis_credentials(user_id, account_label)` — None=default, str=특정 라벨
- `_token_cache` 키 `(user_id, account_label)` 튜플 격리
- `get_access_token(user_id, account_label)` 시그니처 확장
- ContextVar `_current_account_label` 추가 (요청 단위 라벨 전파, FastAPI Depends에서 set)

**`routers/me_kis.py`** — 8 라우트 재설계:
- `POST /api/me/kis` body=`{label, is_default?, app_key, app_secret, acnt_no, acnt_prdt_cd_stk, acnt_prdt_cd_fno?, ...}` — 첫 계좌 자동 is_default=true, 라벨 중복 409
- `GET /api/me/kis` → `{accounts:[{label, is_default, app_key_masked, acnt_no_masked, ...}], default_label, ...백워드 호환}`
- `GET /api/me/kis/{label}` 단일 마스킹
- `PUT /api/me/kis/{label}` 부분 갱신 (라벨 변경 + 자격증명 변경 동시 가능, sensitive 변경 시 자동 재검증)
- `DELETE /api/me/kis/{label}` 삭제 (기본 계좌 삭제 시 다른 계좌 자동 default 승격)
- `POST /api/me/kis/{label}/default` 기본 지정
- `POST /api/me/kis/{label}/validate` 재검증 (24h TTL)

**`services/balance_service.py` (신규)** — 멀티 계좌 잔고 진입점:
- `fetch_single_account_balance(user_id, account_label)` 한 계좌 KIS 호출(KR/US/FNO 분기) + 메트릭 보강 + partial_failure
- `aggregate_balance_accounts(list[per_account])` 종목 단위 합산 (key=`(symbol, market)`, qty=sum, avg_price=weighted_avg, eval/pl=sum, accounts 메타)
- `fetch_aggregated_balance(user_id, account_label=None)` — None 시 모든 계좌 `asyncio.gather(Semaphore=6)` 병렬, 라벨 지정 시 단독. 등록 0개 시 빈 응답 (예외 raise 금지)
- 환율은 1회 조회 (계좌 무관 동일)
- FNO는 합산 안 함 (만기/사이즈 차이로 무의미) + `account_label` 부착

**`services/account_label_matcher.py` (신규)** — 체결통보 라벨 매칭:
- H0STCNI0 ACNT_NO 파싱 → `(user_id, decrypted_acnt_no) → label` LRU 100 인메모리 캐시
- me_kis 라우터 create/update/delete 시 invalidate
- 매칭 실패 시 label=None + 경고 로그 (타 사용자 계좌 등)

**`services/order_service.py`**: `place_order(..., user_id, account_label)` 시그니처 확장 + `orders.account_label` 기록. modify/cancel은 원주문 라벨 자동 사용(계좌 간 정정 금지).

**`services/safety_grade.py`** (REQ-DOMAIN-01): `compute_position_size()` 응답에 `position_meta: {total_portfolio_limit_qty, account_cash_limit_qty, binding_constraint, reason?}` 추가.

**`services/reservation_service.py`**: 예약 등록 시 `account_label` 저장 + 발동 시 동일 계좌로 발송.

**`services/quote_kis.py`**: 체결통보 핸들러 `_parse_notice` ACNT_NO 8자 토큰 파싱 → account_label_matcher 위임.

### 프론트엔드 UI

**`pages/SettingsKisPage.jsx`** (R8): 단일 폼 → **카드 그리드 + 모달**
- 계좌 카드: 라벨 / 마스킹 계좌번호 / 검증 상태 / "기본" 배지 / 수정/삭제/재검증/기본설정 버튼
- "+ 계좌 추가" 모달 (label + 6필드)
- **계좌상품코드 default '01' 제거** (사용자가 의식적으로 입력 — 일반 01 / 연금·IRP·ISA 02·22 등 KIS 발급값)
- 안내문 강화

**`pages/BalancePage.jsx`** (R9): 상단 탭 [전체|라벨1|라벨2|...] + 합산/단독 토글
- 탭 라벨은 `listAccounts()`로 마운트 시 1회 별도 fetch (`data.accounts` 의존 X — 단독 탭 응답 메타 1개로 탭 사라짐 방지)
- `useBalance(activeTab)` 분기, partial_failure 노란 배너 표시

**`pages/OrderPage.jsx`** (R10): 주문 폼 상단 계좌 선택 드롭다운 + localStorage 마지막 사용 계좌 + 토스트 라벨 prefix

**`api/me.js`**: 멀티 6 (`listAccounts/createAccount/updateAccount/deleteAccount/setDefaultAccount/validateAccount`) + 백워드 호환 4
**`api/balance.js`**: `fetchBalance(accountLabel?)` null=합산
**`api/order.js`**: 전 함수 `accountLabel` 쿼리/body 옵션
**`hooks/useBalance.js`**: `load(accountLabel = null)` 인자 추가 (백워드 호환)

### TDD 사이클 R1~R11 (도메인팀장 요건 → 개발팀장 RED→GREEN→VERIFY)

- 본 작업 신규/관련 147/147 PASS
- 전체 `pytest tests/unit/ tests/integration/`: 1676 PASS / 26 사전 환경 결함(pdfplumber/pytest-asyncio 누락, 본 작업 무관) / 18 skip
- 프론트 `npm run build` PASS

신규 테스트 9개 파일: `test_user_kis_repo.py`(24), `test_user_kis_migration_compat.py`(4), `test_order_repo_account_label.py`(6), `test_kis_auth_multi_account.py`(10), `test_me_kis_multi_account_api.py`(19), `test_balance_aggregate.py`(10), `test_safety_grade_multiaccount.py`(4), `test_order_account_label.py`(4), `test_execution_notice_label.py`(3), `test_domain_invariants_multiaccount.py`(4).

### 백워드 호환 가드 (REQ-MIGRATION-01)

- 기존 1계좌 사용자 → 자동 'label=기본' 변환, 기존 동작 100% 유지
- `POST /api/order` body `account_label` 누락 → default 계좌 폴백 (기존 클라이언트 호환)
- `GET /api/balance` 쿼리 미지정 → 합산 모드 (등록 0개 시 빈 응답)
- `/ws/execution-notice` 메시지 기존 필드 보존 + `account_label`만 추가
- 기존 orders/reservations row (account_label NULL) → default 계좌로 처리

### 사용자 보고 후속 수정 (재기동 후 발견)

**버그**: 연금 계좌의 `acnt_prdt_cd_stk=22`로 등록했음에도 DB에 `01`로 저장됨.
- **원인 추정**: SettingsKisPage 폼 default `'01'`이 사용자 입력으로 오인되어 그대로 제출됨
- **수정**: `initialForm.acnt_prdt_cd_stk: '01'` → `''` (빈 값, 사용자 의식적 입력 강제) + 수정 모드 폴백 `|| '01'` → `|| ''` + 필드 라벨 안내문 강화 "일반 01, 연금/IRP/ISA 등은 02·22 등 KIS 발급값 확인"

**버그**: 잔고 페이지에서 특정 계좌 탭 선택 시 다른 계좌 탭이 사라짐.
- **원인**: `accountTabs`를 `data.accounts`(현재 응답)에서 그렸는데, 단독 모드 응답은 해당 계좌 1개만 메타에 포함
- **수정**: 마운트 시 `listAccounts()`로 탭 라벨 1회 별도 fetch + state로 보존. `data.accounts` 의존성 제거

---

## 2026-05-15 — 관심종목 현재가 캐시 제거 (도메인 원칙 정합)

### 버그 수정 — 관심종목 대시보드 현재가 갱신 지연

**진단**: 사용자 보고 "관심종목 현재가가 제대로 안 갱신된다". 코드 감사 결과 현재가에 **4중 캐시**가 운영 중이었음.

| 계층 | 위치 | 기존 장중 TTL | 기존 장외 TTL |
|------|------|---------------|---------------|
| L1 응답 | `services/_dashboard_cache.py` | 60s | 60s |
| L2 영속 | `db/repositories/stock_info_repo.py:_TTL["price"]` | **10분** | **12시간** |
| L3 raw (KR) | `stock/market.py:fetch_price` cache.db | 6분 | 6시간 |
| L4 raw (US) | `stock/yf_client.py:fetch_price_yf` cache.db | 2분 | 30분 |

가장 큰 stale 원인: L2. `_fetch_dashboard_row`(`services/watchlist_service.py:107`)가 `price_fresh`이면 외부 API 호출 자체를 스킵 → 장중 최대 10분, 장외 최대 12시간 stale. 시세판(인메모리 10s/60s)과 비교 시 장중 60배, 장외 720배 stale.

**도메인 원칙 (사용자 결정)**: 현재가는 캐시 적용 금지 영역. F5 연타 시 t3.small swap thrashing 방지를 위한 **dedup 5초만 허용** (시세판 정책과 일관). 장외(폐장)는 호가 변동이 없으므로 30분 유지.

**변경**:
- `services/_dashboard_cache.py:33-34` — `DEFAULT_TTL_SEC` 60s → **5s**, `PARTIAL_FAILURE_TTL_SEC` 15s → **3s** + 모듈 docstring 업데이트
- `db/repositories/stock_info_repo.py:17` — `_TTL["price"]` `{trading:0.167h, off:12.0h}` → `{trading:0.0014h, off:0.5h}` (5s/30m). 다른 영역(metrics/financials/returns)은 유지 (분 단위 변동 없음, 도메인 원칙 미해당)
- `stock/market.py:158` — `fetch_price()` cache.db ttl `0.1h / 6h` → `0.0014h / 0.5h` (5s/30m)
- `stock/yf_client.py` (KIS 경로 + yfinance 폴백 2곳) — `fetch_price_yf()` cache.db ttl `2/60h / 0.5h` → `5/3600h / 0.5h` (5s/30m)
- `tests/unit/test_stock_info_freshness.py` — 회귀 가드 갱신 (5s/30m 경계 검증으로 변경)

**효과**:
- 장중 관심종목 현재가 stale 상한: 10분 → 5초 (**120배 감소**)
- 장외 관심종목 현재가 stale 상한: 12시간 → 30분 (**24배 감소**)
- 시세판(인메모리 10s)과 일관된 "현재가 캐시 금지 + F5 dedup 한정" 정책 확립

**회귀 가드**: `pytest tests/unit/test_stock_info_freshness.py tests/unit/test_dashboard_cache.py tests/unit/test_watchlist_partial_failure.py -v` → **26 passed**.

---

## 2026-05-15 — 종목별 외국인 보유율 차트 + 반년 누적 추이 (V1.5 + V1.6)

### 신규 — 외국인 보유율 + 추가 매수여력 직관적 차트 (V1.5)

**배경**: 종목별 수급정보(`SupplyDemandPanel`)는 V1에서 개인/외국인/기관 일별 매매동향만 제공. 사용자가 외국인 보유수량 / 총상장주식수 비율과 추가 매수여력(외국인한도종목은 한도소진 상한)을 표가 아닌 **직관적 차트**로 보고 싶다고 요청.

**KIS TR 사실관계 (도메인팀 검증)**: 사용자/V1 요건서가 언급한 `FHKST01010800`은 KIS 공식 LLM 카탈로그에 미존재. 대신 이미 노출된 두 TR 조합으로 우회:
- `FHKST01010100`(주식현재가) — `frgn_hldn_qty`/`hts_frgn_ehrt`(소진율)/`lstn_stcn`(상장주수) 스냅샷
- `FHKST01010400`(주식현재가 일자별) — 일별 `hts_frgn_ehrt`/`frgn_ntby_qty` 시계열 (**최대 30거래일**)

한도수량 = `보유수량 / (소진율/100)` 역산 (소진율 ≥ 0.01%일 때). 한도 미설정 종목은 `None` 폴백.

**도메인 합의 (3인 만장일치)**:
- 외국인 보유율은 **가치 지표 아님 → SafetyGrade 7점 등급 편입 금지** (MarginAnalyst/MacroSentinel/OrderAdvisor)
- 잔여 매수여력 = 외국인 합산 한도 → **개인 매수 적합성과 무관 명시** (OrderAdvisor)
- V1 `_ADVISORY_NOTE` 강화 통일: "한도소진율과 개인 투자자 매수 적합성은 무관(외국인 합산 한도). 매매 신호로 단독 사용 금지(Graham 원칙)"
- 한도 미설정/한도 초과 폴백: `None` + `unlimited`/`exceeded` 분기 배지(0 채우면 잘못된 시각화)
- 임계값 4단계: safe(<50%, 회색)/caution(50~80%, 노랑)/warning(80~95%, 주황)/saturated(≥95%, 빨강)

**변경**:
- `wrapper.py` — `_opt_int`/`_opt_float` 헬퍼 + `get_foreign_holding_snapshot(code)` (`FHKST01010100`) + `get_foreign_holding_daily(code, days=30)` (`FHKST01010400`, days 1~30 검증). 6자리 숫자 검증, 빈 응답/빈 필드 None 정규화, KIS rt_cd≠0 시 `ExternalAPIError(502)`
- `services/supply_demand_service.py` — `_FH_COLOR_MAP`/`_FH_DAYS_*`/`_FH_EHRT_UNLIMITED_THRESHOLD` 상수 + `_classify_limit_status`(safe/caution/warning/saturated/unlimited/exceeded) + `_is_defective_fh_snapshot`/`_is_defective_fh_daily` 가드 + `_fetch_or_cache_fh` + `_build_fh_snapshot` + `_build_fh_daily` + `fetch_foreign_holding(code, days=30)` 공개 API. 단위: 보유수량 = **만주**(÷10000 반올림), 소진율 = % 소수점 2자리. `_ADVISORY_NOTE` 통일 (V1 응답도 강화 문구)
- `routers/advisory.py` — `GET /api/advisory/{code}/foreign-holding?days={5..30}` 엔드포인트. ServiceError(400)/NotFoundError(404)/ConfigError(503)/ExternalAPIError(502) 매핑
- `frontend/src/api/advisory.js` — `fetchForeignHolding(code, days)` 추가
- `frontend/src/hooks/useAdvisory.js` — `useForeignHolding(code, days)` 훅 (독립 로딩/에러)
- `frontend/src/components/advisory/ForeignHoldingCard.jsx` 신규 — 좌(Recharts `PieChart` 도넛 게이지 + 중앙 큰 글씨 + 4지표 그리드 + 상태 배지) + 우(`LineChart` 추이 + 임계값 ReferenceLine + 변동 보조 텍스트). 해외 종목 진입 시 `return null`. 부분 실패 격리(KIS 키 503/404/502 안내, V1 차트 무영향)
- `frontend/src/components/advisory/SupplyDemandPanel.jsx` — 하단에 `<ForeignHoldingCard code={code} market={market} />` 통합

**테스트 (RED→GREEN→VERIFY)**:
- `tests/unit/test_kis_wrapper_foreign_holding.py` (18 PASS) — TR_ID/파라미터 일치, 6자리/days 범위 검증, 빈 응답/빈 필드 정규화, KIS rt_cd 에러
- `tests/unit/test_foreign_holding_service.py` (25 PASS) — 단위 변환, 임계값 6 경계(49.99/50/79.99/80/94.99/95), unlimited/exceeded 분기, 잔여여력 음수 보호(max 0), KIS 키 503/ServiceError 400/매매 액션 키 부재
- `tests/api/test_advisory_foreign_holding.py` (10 PASS) — 200/400/404/503/502, advisory_note 존재, 매매 액션 키 부재
- 신규 53 PASS / V1 supply_demand 회귀 27 PASS

### 신규 — 외국인 보유율 반년(180일) 누적 추세 + 일별 백필 cron (V1.6)

**배경**: V1.5는 KIS `FHKST01010400` 30거래일 한도로 30일 추이만 가능. 사용자가 **반년(약 120거래일)** 추세를 요청.

**KIS TR 재검증 (도메인팀 2차)**: LLM 카탈로그 6회 검색 + 후보 TR 4개 본문 직접 확인:
- `inquire_daily_itemchartprice`(FHKST03010100): 기간 지정 + 100건/회 가능, 그러나 output2 array에 `hts_frgn_ehrt` 부재 (OHLCV만)
- `investor_trade_by_stock_daily`(FHPTJ04160001): `frgn_ntby_qty`만, `hts_frgn_ehrt` 부재
- `frgnmem_pchs_trend`(FHKST644400C0): 외국계 회원사 단위, 보유율 없음
- → **외국인 소진율을 30거래일 초과로 array 제공하는 KIS TR은 존재하지 않음** 확정

**우회 채택**: `macro_store` 일자별 list append 패턴 + 일별 cron 자연 누적. N일 후 자연스럽게 반년 차트 완성.

**도메인 합의 (3인 만장일치 9건)**:
- 캐시 모델 (가): `macro_store` list append, 키 `foreign_holding:daily_history:{code}`, **FIFO 250거래일**. DB 마이그레이션 0건
- 백필 전략 (a): Lazy + 일별 cron (advisory_stocks ∪ watchlist 국내, **50개 cap**)
- 슬라이더: 5단계 stepper (30/60/90/120/180, **기본 120**)
- `change_alert`: 첫일자↔마지막일자 소진율 차이 **±3.0%p** 초과 시 강조
- 매매 액션 키 금지 유지 / advisory_note 유지 (V1.5 통일 문구)
- cron 시각: KST 평일 18:00 (장 마감 후), 휴장일 자동 skip

**변경**:
- `services/supply_demand_service.py` — `_FH_HISTORY_MAX_KEEP=250` + `_FH_CHANGE_ALERT_THRESHOLD=3.0` 상수 + `_merge_fh_daily(existing, new, max_keep=250)` 헬퍼 (오래된 일자 → 최신, 중복 dedup last-wins, None ehrt 새 행 필터 + 기존 행 보존) + `_build_change_alert(daily)` (signed/abs delta + breached + first/last + color). `fetch_foreign_holding(code, days=120)` 시그니처 확장 (days 5~180, 기본 120), 누적 캐시 조회 + KIS 30일 머지 → 최근 `days` 슬라이스 반환. 응답에 `change_alert`/`daily_history_total_days` 키 추가
- `services/scheduler_service.py` — `_FH_BACKFILL_CAP=50` + `_run_foreign_holding_backfill_job()` + `_all_advisory_users_codes()`/`_all_watchlist_codes()` 헬퍼 + `setup_scheduler()`에 `foreign_holding_backfill` 잡 등록 (KST 18:00, Mon-Fri). 휴장일(weekday≥5) 즉시 return. 종목별 예외는 logger.error로만, raise 금지(잡 중단 방지)
- `routers/advisory.py` — foreign-holding `days` 범위 5~180 + 기본 120
- `frontend/src/api/advisory.js` — `fetchForeignHolding(code, days=120)` 기본값 변경
- `frontend/src/hooks/useAdvisory.js` — `useForeignHolding(code, days=120)` 기본값 변경
- `frontend/src/components/advisory/ForeignHoldingCard.jsx` — 슬라이더 → 5단계 stepper 버튼(30/60/90/120/180), x축 자동 포맷 (≤60일 MM-DD / ≥90일 YYYY-MM 격주/월말), 변동 보조 텍스트 동적 days, **`change_alert.breached` 시 라인 강조(#F97316) + 배지** "급증 +3.5%p"/"급감 -4.1%p", **콜드스타트 안내** (`daily_history_total_days < days` 시 "데이터 누적 중 (현재 N일, 매일 자동 채워짐)" 노란 배너)

**테스트 (RED→GREEN→VERIFY)**:
- `tests/unit/test_foreign_holding_history_merge.py` (9 PASS) — 빈/오버랩/dedup last-wins/FIFO cap 250/None ehrt 필터·보존/중복 dedup
- `tests/unit/test_foreign_holding_extended.py` (20 PASS) — days 기본 120/5미만 raise/180초과 raise/180 허용/V1.5 회귀(30 동작)/누적 첫 저장+이후 append/change_alert 4 경계(3.0/2.99/+/-)/single row 시 omit/history_total_days/daily 슬라이싱·None 제외/매매 액션 키 부재/advisory_note 존재
- `tests/unit/test_foreign_holding_backfill_scheduler.py` (7 PASS + 1 skip) — 토/일 skip/평일 활성 종목 fetch/advisory+watchlist dedup/50 cap/종목별 예외 무중단/활성 0건 early return
- `tests/api/test_advisory_foreign_holding_extended.py` (7 PASS) — days 기본 120/180 허용/180+/5미 400/V1.5 회귀 30/응답 신규 키 포함/매매 액션 키 부재

**회귀 영향 분석**: 본 변경 직접 import 영향권 157 PASS + 2 skip (외국인 96 PASS + V1 supply_demand 59 PASS + macro_prewarm 2 PASS / apscheduler 환경 의존 skip). wrapper.py 변경 0건 + DB 마이그레이션 0건 회귀 가드.

**효과**: 첫 진입 시 30일 노출 + 매일 18:00 cron 자연 누적 → N일 후 사용자 가시 범위 30→60→90→120→180일 자동 확장. 한도소진/매수여력 직관적 시각화 + 단방향 가격 충격 위험 양면성 명시 (MarginAnalyst).

## 2026-05-12 (후속) — advisory_service stampede 우회 버그 수정

### 버그 수정 — refresh_stock_data 동시 호출 시 fetcher 중복 호출

**증상**: CI에서 `tests/api/test_advisory_refresh_dedup.py::test_concurrent_refresh_deduplicates` 실패. 5 thread 동시 호출 시 fetcher가 1회가 아니라 5회 호출됨 (`fundamental called 5x`).

**Root cause**: `services/advisory_service.py:refresh_stock_data()` 내 variable shadowing.
- 함수 진입 시 `key = (code.upper(), market.upper())`를 stampede 캐시 키로 정의
- 그러나 `as_completed(futures)` 루프에서 `key, val, dur, err = fut.result()`가 같은 `key` 변수를 phase 문자열("fundamental" 등)로 덮어씀
- 결과적으로 `_REFRESH_LAST_DONE[key] = perf_counter()`가 잘못된 문자열 키에 저장 → 후속 thread의 tuple 키 조회는 항상 miss → stampede 우회 무효화

**보조 발견**: stampede 윈도우 비교가 `datetime.now().replace(tzinfo=None)` vs KST tz-aware ISO `updated_at`을 naive로 비교 → CI(UTC) 환경에서 ±9h 오차로 5s 윈도우가 무조건 초과되던 잠재 버그도 동시 존재.

**변경**:
- `services/advisory_service.py` — `as_completed` 루프 변수 `key` → `phase`로 rename (shadowing 제거)
- timezone-naive `updated_at` 비교를 in-memory `_REFRESH_LAST_DONE[(code, market)] = perf_counter()` 단조 시계 비교로 교체. 호스트 timezone 무관, datetime/timedelta import 제거

**검증**:
- `tests/api/test_advisory_refresh_dedup.py` GREEN (fundamental/technical/research/strategy 각 1회)
- `tests/unit/test_advisory_parallel.py` + `tests/unit/test_advisory_cache_shared.py` 회귀 PASS

## 2026-05-12 — 중복 데이터 최소화 (공유 캐시 전환) + 핫 병목 비동기화 + 멀티유저 격리 보강 + 매크로 뉴스/투자자 공유 캐싱

### 리팩토링 — 트랙 1: `advisory_cache` 공유 캐시 전환

**배경**: 멀티유저 환경에서 `advisory_cache` PK가 `(user_id, code, market)`로 격리되어 동일 종목의 fundamental/technical 분석을 사용자 N명이 각자 외부 API(DART/yfinance/KIS) 수집 → AI 자문 첫 응답 30~60초, 외부 호출 N배. `cache.db`(시세/재무/공시/매크로 지표) 영역은 이미 user_id 무관 공유이지만 `app.db.advisory_cache`만 격리되어 가장 큰 중복 누수 지점.

**변경**:
- `db/models/advisory.py` — `AdvisoryCache` PK `(user_id, code, market)` → **`(code, market)`** 변경. `user_id` 컬럼은 1차 안정화 기간 nullable=True 유지(2차 마이그레이션에서 drop 예정, 롤백 안전)
- `db/repositories/advisory_repo.py` — `save_cache/load_cache/save_research_data/get_cache` 4함수 user_id 인자 호환 유지, 내부에서 무시(공유 저장/조회)
- `stock/advisory_store.py` — adapter 시그니처 100% 유지 (백워드 호환)
- `services/advisory_service.py` — `_REFRESH_LOCKS: dict[(code,market), Lock]` 추가 → **stampede 방지**: 동일 종목 동시 N명 호출 시 1명만 실제 수집, 나머지는 대기 후 동일 결과 공유
- `alembic/versions/c1d2e3f4a5b6_share_advisory_cache_drop_user_id_pk.py` 신규 — 동일 (code, market) 중복 row 중 `updated_at` 최신만 보존 후 PK 재정의. **SQLite 호환 dialect 분기**: PostgreSQL은 `drop_constraint("advisory_cache_pkey")`, SQLite는 PK constraint 자동 명명 없으므로 `batch_alter_table(recreate="always") + create_primary_key`만 사용. 멱등 가드(`_current_pk_cols`)로 부분 적용 상태에서 재실행 안전

**효과**: 동일 종목 첫 사용자 수집 → 다른 사용자 즉시 캐시 응답. 외부 API 호출 50~70%↓.

**도메인 자문 — MarginAnalyst**: TTL 30분 유지 GO. 분기 결산 직후 사용자 격리 모드와 안전성 동등 (오히려 캐시 일관성 우위).

### 리팩토링 — 트랙 2: AI 자문 4단계 병렬화

**변경**:
- `services/advisory_service.py:refresh_stock_data()` — fundamental/technical/strategy_signals/research 4단계를 `ThreadPoolExecutor(max_workers=4)`로 동시 실행. 부분 실패 시 다른 단계 결과 보존(실패 필드만 null)

**효과**: 30~60초 → 7~20초 (외부 I/O 블로킹이라 GIL 영향 미미).

### 리팩토링 — 트랙 3: 매크로 pre-warm + 일일 cron

**배경**: `macro_gpt_cache` KST 일자별 캐시 자정 후 첫 사용자가 GPT(10s) + FRED(2s) + yfinance(3s) 누적 15~30s 대기.

**변경**:
- `services/macro_service.py:prewarm_macro_summary()` 신규 — 모든 카테고리(`indices`, `sentiment`, `summary`) `user_id=None` 시스템 호출(쿼터 미차감)로 사전 적재
- `services/scheduler_service.py:_run_macro_prewarm_job()` 신규 + APScheduler **KST 00:05** cron 등록 (cleanup 직후 실행)

**효과**: 자정 후 첫 매크로 페이지 진입 15~30s → 즉시.

**도메인 자문 — MacroSentinel**: 단일 cron(00:05) GO. 한국 새벽 거주자 즉시 응답 우선. 미국 마감 후 정확도 향상은 06:30 보조 cron(후속 작업).

### 신규 기능 — 트랙 4: `/api/watchlist/batch-details` 신규 엔드포인트

**배경**: 관심종목 대시보드가 N종목에 대해 N번 `/api/stock/{code}/detail` 호출 → 캐시 미스 누적 10~20s.

**변경**:
- `routers/watchlist.py` — `GET /api/watchlist/batch-details?codes=...&market=auto` 신규. codes ≤ 50 가드 (ServiceError(400))
- `services/watchlist_service.py:fetch_batch_details(codes, market='auto')` 신규 — ThreadPoolExecutor(4)로 종목별 metrics 병렬 수집. 시장 자동 판별 + 부분 실패 부분 반환
- `frontend/src/api/watchlist.js:fetchWatchlistBatchDetails(codes, market)` 신규

**효과**: 10~20s → 2~5s.

### 신규 — `portfolio_reports.user_id` 격리

**배경**: `portfolio_reports` 테이블 `user_id` 컬럼 없음 — 현재 admin 1명 가정 운영 중이지만 멀티유저 시 충돌 위험.

**변경**:
- `alembic/versions/d4e5f6a7b8c9_add_user_id_to_portfolio_reports.py` 신규 — `user_id INTEGER NULL` 컬럼 추가 + 기존 행 백필(`user_id=1`) + 인덱스 `(user_id, generated_at DESC)` + FK `users(id) ondelete=SET NULL`. 멱등 가드(`_has_column`/`_has_index`) + downgrade 가능
- `db/models/advisory.py` — `PortfolioReport.user_id` 컬럼 + FK + 인덱스
- `db/repositories/advisory_repo.py` — `save_portfolio_report/get_portfolio_report_by_id/get_portfolio_report_history/get_latest_portfolio_report` 4함수에 user_id 인자
- `stock/advisory_store.py` — adapter 4함수 백워드 호환
- `services/portfolio_advisor_service.py` — `analyze_portfolio/get_report_by_id/get_report_history/chat_with_report` 사용자별 격리 + 권한 검증(`NotFoundError`)
- `routers/portfolio_advisor.py` — `Depends(require_admin)` user_id 명시 전달

**도메인 자문 — OrderAdvisor**: DB 저장은 사용자별 분리 필수(보유 종목 = 사적 정보), 캐시(잔고 해시 키)는 공유 유지 OK(분석 결과 = 잔고의 함수). 캐시 키 정밀화(평가손익 반영)는 후속 PR로 분리.

### 신규 기능 — `/api/detail/{symbol}/bundle` 신규 엔드포인트

**배경**: DetailPage 마운트 시 stock-detail / DART financials / yfinance metrics 등을 N회 fetch — 캐시 미스 시 3~8s 누적.

**변경**:
- `services/detail_service.py:get_bundle(symbol, market='auto')` 신규 — basic/financials/valuation/forward_estimates/summary 5섹션을 `ThreadPoolExecutor(max_workers=4)`로 병렬 수집. 부분 실패 시 `partial_failure: list[str]`로 보존
- `routers/detail.py` — `GET /api/detail/{symbol}/bundle?market=auto` 신규
- `frontend/src/api/detail.js:fetchDetailBundle(code, market)` 신규
- `frontend/src/hooks/useDetail.js:useDetailBundle(symbol, market)` 신규
- `frontend/src/pages/DetailPage.jsx` — `useDetailReport` → `useDetailBundle` 전환 + 부분 실패 안내 카드. 기존 컴포넌트(`FundamentalPanel`/`TechnicalPanel` 등) shape 100% 호환

### 신규 — 매크로 뉴스/투자자 코멘트 공유 캐싱

**배경**: 매크로 페이지의 뉴스(`get_news`)와 투자대가 코멘트(`get_investor_quotes`)는 RSS fetch + GPT 번역/추출을 매 호출마다 일부 반복. RSS는 부분 캐시(0.5h/6h)였으나 **전체 결과 캐싱이 없어** 사용자별 호출 시 함수 진입부터 재실행. 사용자 요청: 뉴스 4시간 단위 / 투자대가 일일 단위로 공유 캐싱.

**변경**:
- `services/macro_service.py:get_news()` — 전체 결과 `cache.db` `macro:news:full_result_v1` 키 **4시간 공유 캐싱** (빈 응답 가드: korean/international 모두 빈 경우 캐싱 거부)
- `services/macro_service.py:get_investor_quotes()` — 전체 결과 `macro_store` `investor_quotes_full` 카테고리 **KST 일별 공유 캐싱** (최소 1명 quotes 확보 시에만 저장)

**공유 메커니즘**: cache.db / macro_store 둘 다 user_id 없는 공유 인프라 → 별도 작업 없이 즉시 모든 사용자 공유 적용.

**효과**:
- 4시간 슬롯 내 뉴스 호출: RSS fetch 0회 + GPT 번역 0회 → 즉시 응답
- KST 일자 내 투자대가 호출: RSS 6×0회 + GPT 6×0회 → 즉시 응답
- AI 사용량(`macro_translate`/`macro_investor`) 일일 1회로 축소

### 테스트
- 신규 23건 (advisory_cache_shared 4 / refresh_dedup 1 / advisory_parallel 2 / macro_prewarm 3 / watchlist_batch_service 3 / watchlist_batch_details 6 / portfolio_user_id 9 / migration_portfolio_user_id 4 / detail_bundle_service 3 / detail_bundle 2)
- 회귀: `pytest tests/ -v` baseline +18 PASS, 회귀 0건. 사전 결함(pdfplumber 미설치 + quote_overseas_kis_ws_orderbook) 본 PR 무관

---

## 2026-05-12 — 시세판/장운영정보 KIS WS → REST 폴링 전환 (자동매매 동시구독 41건 충돌 해소) + 수급 차트 부호 중복 버그 수정

### 리팩토링 — 시세판 다중심볼 WS 제거, REST 일괄 폴링 전환

**배경**: 동일 KIS 계정으로 외부 자동매매 시스템이 실시간 시세를 구독하는데, 본 프로젝트 시세판의 다중심볼 WS(`/ws/market-board`, 종목당 체결+호가 2 slot) + 장운영정보 WS(`/ws/market-status`, 3 slot 고정)가 KIS WS **계정당 41건 동시구독 한도**를 잠식해 자동매매 측 종목 수신이 중단됨. 시세판은 정보 표시(브라우징)용으로 실시간성보다 충돌 회피가 우선이라 판단해 REST 폴링으로 전환. 호가창(`/ws/quote/{symbol}`)과 체결통보(`/ws/execution-notice`)는 매매 결정 직접 영향(슬리피지/IOC)이라 KIS WS 유지.

**KIS WS slot 회수 효과**: 시세판 N종목 × 2건(체결+호가) + 장운영정보 3건 = `N×2+3`건 회수 (N=20 가정 시 43건 → 자동매매 41건 한도 해소).

**백엔드 (`stock/market.py`)**
- 신규 `fetch_prices_batch(codes: list[str], market='KR'|'US')` — 시세판 다중심볼 일괄 폴링. 반환 `{code: {price, change, change_pct, prev_close, volume, sign}}`(`sign='2'`/`'5'`/`'3'`은 기존 WS shape 호환)
- 1차 yfinance `yf.Tickers(...)` fast_info 일괄 호출(`_kr_yf_ticker_str()` 캐시로 `.KS`/`.KQ` suffix 자동 부착) → 2차 폴백 (빈응답·예외·모든 종목 None 시) KIS REST `FHKST01010100` 종목별 호출(분당 한도 보호 N≤20 가드). **부분 실패 시에도 성공 종목만 반환** (시세판은 부분 표시가 전체 실패보다 나음)
- in-memory TTL 캐시: 장중 10초 / 장외 60초 (yfinance rate limit 방지)

**라우터 (`routers/market_board.py`, `routers/quote.py`)**
- 신규 `GET /api/market-board/prices?codes=&market=KR` — codes 콤마 구분, 최대 50개 가드, 빈 codes 400 + ServiceError(400) 사용
- 제거 `WS /ws/market-board` (다중심볼 시세 WS) + 헬퍼 5종 일괄 삭제
- 제거 `WS /ws/market-status` (장운영정보 멀티플렉스 WS)

**서비스 (`services/quote_kis.py`)**
- `subscribe_market_status` / `unsubscribe_market_status` / `_send_subscribe_market_status` / `_broadcast_market_status` / `_KR_MARKET_STATUS_TR_IDS` / `_market_status_subscribers` 6개 헬퍼 + `_handle_message`/`_run_ws`의 market-status 분기 제거. KISQuoteManager는 호가/체결/체결통보 단일 책임으로 단순화

**프론트엔드**
- 신규 `api/marketBoard.js:fetchPricesBatch(codes, market)` — GET 호출 + codes 콤마 직렬화
- 신규 `hooks/useMarketBoard.js:usePricePolling(codes, market)` — `useMarketClock` phase 기반 장중 15s/장외 60s 자동 조정. cleanup·재마운트·codes 변경 시 setInterval 안전 재구성. 기존 `useMarketBoardWS` prices shape 100% 호환
- 삭제 `hooks/useMarketBoardWS.js` (단일 책임 종료)
- `hooks/useMarketClock.js` — `useWebSocket`/`buildMarketStatusUrl`/`onMessage` WS 분기 제거. `resolvePhaseByClock(now)` 시계 폴백 + 1분 setInterval 단독 사용
- `pages/MarketBoardPage.jsx` — `useMarketBoardWS` import 제거, `usePricePolling(polledCodes, 'KR')` 연결, `polledCodes = useMemo(...)` 변경 시 자동 재구독

**테스트**
- `tests/unit/test_market_prices_batch.py` (신규 8건) — yfinance 정상 / 빈응답 폴백 / KIS REST 폴백 / 모든 종목 None 시 폴백 / 부분 실패 부분반환 / N>20 KIS REST 가드 / TTL 캐시 적중 / sign 부호 매핑
- `tests/api/test_market_board_prices.py` (신규 6건) — 응답 shape / 부분 실패에도 200 / codes>50 400 / 빈 codes 400 / market missing 422 / market 기본값 'KR'
- `tests/api/test_quote_ws_exchange.py` — `test_market_status_ws_*` 2건 제거(엔드포인트 폐지)
- 전체 회귀 1,710 PASS (baseline 동일)

**경계면 QA**: API 응답 shape ↔ `usePricePolling` 기대값 일치 / 제거된 WS 라우트가 프론트 코드에 잔존 0건 / 호가창·체결통보 WS 무변경 / 예외 계층 준수(`ServiceError` 사용, `HTTPException` 0건) / 프론트 빌드 862 modules (baseline 863 − useMarketBoardWS 1건 삭제, 예상치 부합).

**도메인 자문 (OrderAdvisor)**: 시세판 폴링 주기 15s/60s는 주문 의사결정/안전마진에 **영향 없음** — 시세판은 정보 표시용, 매매는 OrderPage의 `useQuote` 실시간 WS로 진행. 호가창 즉시성 보존으로 슬리피지/IOC 정확도 유지. 안전마진가격은 일봉 기준 계산(밀리세컨드 정밀도 불필요).

### 버그 수정 — 수급 차트 당일 요약 양수 부호 중복 (`++100억`)

매크로 `SupplyDemandSection`(`SummaryChip`)과 종목 상세 `SupplyDemandPanel`이 `formatAmount(v)`로 이미 부호(`+`/`-`)를 포함해 반환하는 값에 외부 분기 `v > 0 ? '+' : ''`로 한 번 더 양수 부호를 추가해 `++100억`이 표시되었음. 음수는 외부 분기가 빈 문자열이라 `-100억` 정상 표시되어 비대칭 발생. 외부 부호 분기 4곳 제거(파일당 2곳 × 2파일) + `SummaryChip`의 `sign` 함수 제거. `formatAmount`만 호출하도록 단순화. 빌드 863 modules 변동 없음.

---

## 2026-05-12 — 투자자별 수급정보(매크로+종목) + 백테스트 UI/UX 개선 (단위 토글·포트폴리오 모달)

### 신규 기능 1 — 투자자별 수급정보 V1 (개인/외국인/기관 11종)

매크로 페이지(시장 단위 KOSPI/KOSDAQ)와 종목 상세 종합 리포트(개별 종목)에 KIS OpenAPI 기반 일별 투자자 매매동향 가시화. KIS TR `FHPTJ04040000`(시장 일별) + `FHPTJ04160001`(종목 일별) 신규 wrapping. 외부 무료 소스(yfinance/FRED/RSS)는 한국 투자자별 수급 미제공, KIS가 유일 진입점.

**KIS wrapper (`wrapper.py`)**
- `get_market_investor_daily(market_code, days)` / `get_stock_investor_daily(code, days)` 신규 메서드 + 헬퍼 5종 (`_format_date_yyyymmdd`, `_to_float`, `_to_int` 등)
- 응답 표준화 키: 합계 3종(personal/foreign/institution_net_amt) + 기관 11종 분해(securities/inv_trust/private_fund/bank/insurance/mrbn/pension/etc_finance/etc_corp/etc_org). 단위 백만원 그대로(서비스 레이어 변환)
- **결함 후 hotfix(같은 날 12:00 KST)**: 시장 TR `FID_INPUT_ISCD_2`를 `KSP`/`KSQ`(소속시장) → `0001`/`1001`(업종분류코드) 정정. KIS 명세상 ISCD_2는 "하위 분류코드(업종분류코드)"이며, 잘못된 KSP/KSQ 송신 시 KIS가 전 행 `*_ntby_tr_pbmn=0`과 엉뚱한 지수값을 반환. 검증: 코스피 호출 직후 개인 +1.43조원/외국인 -1.95조원/기관 +4,884억원 정상 수신
- **종목 TR `FID_INPUT_DATE_1` KST cutoff 후퇴 로직**: KIS 명세에 "해당일 조회는 장 종료 후 정상 조회 가능" 명시되어 있어 평일 15:40 이전엔 오늘 날짜로 TIME LIMIT 반환. KST 평일 15:40 이전 또는 주말이면 직전 영업일(월요일은 직전 금요일, 토·일은 직전 금요일)로 자동 후퇴 → 장중에도 어제까지 데이터 정상 조회. 표준라이브러리 `datetime.timezone(timedelta(hours=9))`만 사용(pytz 미의존)

**서비스 (`services/supply_demand_service.py` 신규)**
- `fetch_market_supply_demand(market, days)` / `fetch_stock_supply_demand(code, days)` — wrapper 위임 + 단위 변환(백만원 → 억원, ÷100 반올림) + 누적합 + 색상 표준(개인 #EF4444 / 외국인 #3B82F6 / 기관 #10B981 — 한국 차트 컨벤션) + advisory_note 안전 고지(Graham 원칙)
- 매매 액션 키 금지(`recommendation`/`action`/`buy_signal` 부재) — OrderAdvisor 자문 결과. 자동 트리거 미래 방지 테스트(`test_advisory_note_no_trade_signal_keys`) 포함
- 영속 캐시: `stock/macro_store.py`(KST 일자 기반) 재사용. 카테고리 키 `supply_demand:market:{kospi|kosdaq}` / `supply_demand:stock:{code}`. DB 마이그레이션 0건
- **zero-row 가드** (`_is_all_zero_net` + `_fetch_or_cache`) — 결함 응답 영속 캐시 차단. 정책: (1) 캐시 hit + 정상 → 그대로 / (2) 캐시 hit + 전 행 zero-row → 자동 폐기 + wrapper 재호출(영속 결함 자동 복구) / (3) wrapper 결과 zero-row → 캐시 저장 거부 + `ExternalAPIError(502)` 표면화 / (4) wrapper 재호출 1회만(무한 루프 방지). 일부 행만 0(휴장일 등)은 정상 통과(false positive 방지). 이 가드는 2026-05-12 오전 코스피 결함 60행 영속 사례에서 도출
- 예외 계층: `ConfigError(503)` KIS 키 미설정 / `ExternalAPIError(502)` KIS 5xx 또는 zero-row / `ServiceError(400)` days 10~60 외 / `NotFoundError(404)` 빈 응답. `HTTPException` 직접 raise 0건

**라우터**
- `GET /api/macro/supply-demand?market=kospi|kosdaq&days=10..60` (기본 20) — 시장별, `Literal["kospi","kosdaq"]` 422 가드
- `GET /api/advisory/{code}/supply-demand?days=10..60` (기본 30) — 종목별, 국내 6자리 전용. 해외종목 400, 빈 응답 404, KIS 키 미설정 503

**프론트엔드**
- `frontend/src/components/macro/SupplyDemandSection.jsx` (신규) — 코스피/코스닥 토글 + 10~60일 슬라이더 + Recharts ComposedChart(일별 막대 + 누적 라인) + 당일 요약 칩(외국인 +X억 / 기관 -Y억 / 개인 +Z억)
- `frontend/src/components/advisory/SupplyDemandPanel.jsx` (신규) — 동일 차트 패턴 + advisory_note 노란 배너 + 매수/매도 분리 토글 + 해외종목 "국내 전용" 안내
- `frontend/src/pages/DetailPage.jsx` — 종합 리포트 5번째 서브탭 `{id:'supply-demand', label:'수급/투자자'}` 신설, lazy-mount(KIS 호출 절약)
- `frontend/src/pages/MacroPage.jsx` — `<IndexSection />` 직후 `<SupplyDemandSection />` 마운트(체감상 지수와 묶이는 자연 위치)
- `frontend/src/api/{macro,advisory}.js`에 `fetchSupplyDemand(market, days)` / `fetchStockSupplyDemand(code, days)` 추가, `hooks/{useMacro,useAdvisory}.js`에 `useSupplyDemand()` / `useStockSupplyDemand(code)` 부분 실패 격리 훅

**도메인 자문 (요건서 `_workspace/dev_20260511/01_requirements.md`)**
- **MacroSentinel**: 단위 억원 통일, 20일 기본, REGIME_MATRIX 결합은 V2 분리 — 매크로 페이지 독립 카드. Graham "미스터 마켓" 보조지표
- **OrderAdvisor**: V1 표시 한정. AI 자문 입력 통합·시그널 임계값(외국인·기관 동반 매수 5거래일, 등급 가중치 ≤ 0.1)은 V2. V1엔 `advisory_note` 안전 고지 + 매매 액션 키 금지로 충분
- MarginAnalyst / ValueScreener는 미관여(본 작업과 무관). V2 분리: 섹터별 수급(KRX TR 미존재) / 외국인 보유비율 추이(`FHKST01010800`) / AI 자문 입력 통합 / 체제 가중치

**테스트**
- `tests/unit/test_kis_wrapper_supply_demand.py` (신규, 20건) — TR_ID + ISCD_2 매핑(KOSPI/KOSDAQ) + KST cutoff 후퇴 6 케이스(장중/장후/cutoff 정각/토/일/월 직전 금요일). `wrapper.datetime.datetime.now`만 patch하는 `_freeze_kst()` 헬퍼(`timezone`/`timedelta` 원본 유지)
- `tests/unit/test_supply_demand_service.py` (신규, 26건) — 단위 변환 / 누적 / 부분 응답 / 캐시 hit/miss / advisory_note / 매매 액션 키 부재 + **zero-row 가드 6건** (헬퍼 단독 / wrapper zero-row → ExternalAPIError / 캐시 폐기 후 재호출 회복 / 재호출도 zero-row → 502 + 무한 루프 방지 / partial zero / 종목 TR)
- `tests/api/test_macro_supply_demand.py` (신규, 6건) — 응답 shape / 422 / 400 / 503 / 502
- `tests/api/test_advisory_supply_demand.py` (신규, 7건) — `advisory_note` 존재 + 매매 액션 키 부재 + 해외 400 + 빈 응답 404 + 503/502 + days 파라미터 전달

**회귀 결과**
- supply-demand 회귀 스위트: **59 PASS / 0 FAIL** (wrapper 20 + service 26 + macro API 6 + advisory API 7). 이 중 신규/갱신: KST cutoff 6 + ISCD_2 매핑 갱신 2 + zero-row 가드 6 = **14건**
- KOSPI 캐시 결함 핫픽스: `macro_store.delete_today('supply_demand:market:kospi')` 1회 호출로 60행 zero-row 영속 데이터 폐기 → 새 wrapper로 재호출 → 정상 응답(개인 +16,690억 / 외국인 -21,582억 / 기관 +4,531억)

### 신규 기능 2 — 백테스트 UI/UX (단위 토글 + 포트폴리오 모달)

기존 "로컬프리셋" 탭이 다종목 포트폴리오 백테스트 진입점이지만 명시적이지 않았고, 이력 테이블이 다종목 백테스트도 `symbol`(첫 종목)만 표시해 정보 손실. `BacktestJob.symbols` JSON 컬럼은 이미 존재(2026-05-07 추가). 프론트 표면화 + 백엔드 응답 보강만으로 해결.

**프론트엔드**
- `frontend/src/pages/BacktestPage.jsx` — 상단 segment control "단위: 종목 / 포트폴리오" 토글(`unitMode` state, 기본 `'single'`). 토글이 전략 탭 자동 제한: `'single'` → `allowedModes=['builder','preset','custom']` + SymbolSearchBar(단일), `'portfolio'` → `allowedModes=['local-preset']` + SymbolMultiInput + `strategyMode='local-preset'` 자동. 전환 시 `multiSymbols`/`symbol` state 보존(재전환 시 복원)
- `frontend/src/components/backtest/StrategySelector.jsx` — `allowedModes` prop 추가, 4탭 화이트리스트 필터링(`visibleModes`). prop 미전달 시 기존 4탭 모두 노출(백워드 호환)
- `frontend/src/components/backtest/BacktestHistoryTable.jsx` — `Array.isArray(job.symbols) && job.symbols.length > 1` 분기로 종목 컬럼에 "포트폴리오 (N종목)" + 앞 3개 칩 미리보기 + "보기" → 모달. 단일 종목 행은 기존 동작(symbol_name 표시 + onSelect 콜백) 100% 유지
- `frontend/src/components/backtest/BacktestPortfolioModal.jsx` (신규) — 헤더(일시·전략명·기간·최종 수익률·샤프·MDD 4메트릭 카드) + 종목 칩 리스트(`symbols_names` 매핑) + per_symbol_contribution 테이블(종목·거래수·수익률·기여도) + 파라미터 JSON pretty 출력. ESC 키 + 백드롭 클릭 닫기

**백엔드**
- `routers/backtest.py` — `GET /api/backtest/history` 응답에 `symbols_names: [{code, name}] | null` 필드 추가. `_resolve_name()` 헬퍼로 `symbol_map.code_to_name()` 위임. 기존 `symbol_name` 단일 필드는 유지(백워드 호환)

**테스트**
- `tests/unit/test_backtest_history_response.py` (신규, 4건) — 단일 종목 / 다종목 KR / 혼합 / 빈 배열 케이스로 `symbols_names` 변환 검증

**회귀 결과**
- 백테스트 전용 스위트: 54/54 PASS (50 baseline + 4 신규)
- 프론트 빌드: 863 modules OK (baseline 856 → +7)

### KIS 명세 동기화 — `docs/kis/` 23개 마크다운 + MCP 보조

수급 작업 중 KIS API 명세 검증을 위해 `mcp__kis-code-assistant__search_domestic_stock_api`로 FHPTJ04040000 응답 필드를 사전 확인. `docs/kis/07_KR_MARKET_ANALYSIS.md`에 정리된 시장/종목 매매동향 TR이 1차 검증 출처로 활용됨. 결함 진단 시 컨테이너 내 직접 wrapper 호출 + 캐시 dump + 로그로 root cause 격리하는 패턴 정립.

### 운영 hotfix 패턴 — docker-compose 빌드 캐시 + 결함 캐시 영속

- 컨테이너 dist 파일이 옛 빌드 시점에 박혀 있어 `docker-compose up --build` 필수(단순 `restart`로는 갱신 안 됨). Vite 컨텐츠 해시 기반 파일명이라 번들 내용 변경 없으면 같은 해시 → mtime만 변하지 않을 수 있음을 검증
- wrapper.py 같은 백엔드 코드는 `docker cp` + `docker-compose restart`로 hot-fix 가능. 단 이미지 자체는 다음 정규 빌드에서 호스트 코드로 재빌드됨(상태 일관성)
- 결함 응답이 일자 영속 캐시에 굳어버리는 시나리오는 zero-row 가드(`_fetch_or_cache`)로 항구 차단. 운영 중 동일 패턴 재발 시 다음 호출에서 자동 복구

---

## 2026-05-11 — 섹터명 한글 정규화 SSoT + 스크리너 헤더 sticky + watchlist sector 누락 fix

### 섹터 정규화 모듈 신규 (`stock/sector_normalize.py`)

관심종목/스크리너의 섹터명 컬럼이 영문/한자 혼재 또는 KRX 업종(전기·전자/서비스업/운수장비)과 매크로 섹터히트맵 분류(반도체/IT/인터넷/2차전지 등)가 일치하지 않아 사용자 혼란. 매크로 섹터히트맵 분류를 단일 정답(SSoT)으로 삼아 모든 노출 영역에서 동일한 한글 라벨로 표시.

- **단일 출처 동기**: `KR_SECTOR_LABELS`는 `stock/macro_fetcher.py:_KR_SECTOR_ETFS`의 `name_ko`를 import-time 자동 추출(14개). 매크로 SSoT 변경 시 본 모듈 자동 추종, 별도 수정 불필요.
- **70 KR 종목 코드 화이트리스트**: 프론트 `KR_SECTOR_REPS`와 동일(매크로 대표종목). 코드 매핑이 정규식보다 우선.
- **정규식 다대일 매핑**: 한글 KRX 업종(`전기·전자` → 반도체) + 영문 GICS sector/industry 14 패턴(`Auto Manufacturers` → 자동차, `Banks - Regional` → 은행/금융 등). yfinance가 KR 종목에 영문 GICS 라벨 반환하는 케이스 다수 커버 — `industry`(세부) → `sector`(광역) 순으로 매칭.
- **`\bMedia\b` 단어경계** — `Multimedia`(IT/인터넷)와 미디어/엔터 패턴 충돌 차단 (`Communication Services + Electronic Gaming & Multimedia` → IT/인터넷 정상 매핑).
- **US 11 GICS 한글**: 정보기술/헬스케어/금융/커뮤니케이션 서비스/임의소비재/필수소비재/산업재/에너지/유틸리티/부동산/소재(KB·미래에셋 리서치 표기 관행).
- **폴백**: 매핑 모호 시 "기타" (Graham 보수 원칙 — false 매핑 회피).
- **캐시**: `normalize_sector_cached()` wrapper로 `sector_norm:{market}:{code}` 30일 TTL.

### 데이터 수집부 정규화 단일 진입점

- **`stock/yf_client.py:_normalize_sector_for_code(raw, code, industry=None)`** — KR(6자리 숫자)/US 자동 추론 헬퍼. `fetch_detail_yf` / `fetch_sector_peers` 호출에 `info.get("industry")` 함께 전달.
- **`stock/market.py:fetch_detail/fetch_market_metrics`** — KR yfinance 응답에서 `info.get("sector")` + `info.get("industry")` 둘 다 `normalize_sector()`에 전달.
- **`services/watchlist_service.py:_norm_sector(raw, code, market, industry=None)`** — 응답 직전 idempotent wrapper(데이터 수집부에서 이미 정규화되어도 None/빈 값/구버전 영문 GICS 캐시 방어).

### `services/watchlist_service.py` stock_info hit 분기 sector 누락 fix

기존 코드는 `_build_row()`에서 stock_info 영속 캐시 hit(metrics_fresh=True)인 경우 외부 API 호출을 건너뛰어 `row["sector"]`가 line 85의 초기값 `None` 그대로 응답에 들어감. 상세 페이지(`detail_service`)는 별도 경로라 정상 표시되었으나 관심종목 대시보드 sector 컬럼만 빈 칸. `_build_row()` line 113 근처에 `if metrics_fresh and info.get("sector"): row["sector"] = _norm_sector(...)` 추가.

### `services/growth_grade.py:_LEADER_SECTOR_MAP` 키워드 확장

sector_normalize 일관화로 응답 sector 라벨이 KR 14 한글로 통일됨에 따라 leader 매칭 누락 위험. `반도체`/`2차전지`/`IT/인터넷`/`자동차`/`바이오/헬스케어`/`은행/금융`/`철강/소재`/`에너지/화학`/`미디어/엔터`/`운송/물류` 등 14 한글 라벨 전 phase(회복/확장/과열/수축) 매트릭스에 추가. 기존 키 100% 보존, 추가만. 14×4=56 케이스 회귀 테스트(`test_growth_grade_sector.py`).

### 스크리너 결과 테이블 헤더 sticky (`frontend/src/components/common/DataTable.jsx`)

스크리너 결과를 스크롤할 때 컬럼 헤더가 화면 밖으로 나가 컬럼 의미 파악 어려움. `DataTable`에 `stickyHeader` prop 추가(default false) — 활성화 시 부모 `overflow-x-auto` 제거 + `<thead>` `sticky top-14 z-20 shadow-sm` (페이지 헤더 56px 아래 고정). `<th>`에 `bg-gray-50` 명시(투명 sticky 시 본문 비침 방지). `frontend/src/components/screener/StockTable.jsx`에서 활성화. 다른 테이블(잔고/관심종목/공시 등)은 prop 미사용 → 기존 동작 유지.

### 회귀 가드

- 단위 테스트: 1257 passed (사이클 신규 27 케이스 — 영문 GICS industry 14 매핑 + sector-only 폴백 + 우선순위)
- 17 errors는 PostgreSQL 5433 미가동 baseline (본 변경 무관)
- frontend `npm run build` 0 error (vite v6.4.1, 4.26s)
- `growth_grade._LEADER_SECTOR_MAP` 기존 키 100% 보존 가드 (4 phase × frozen set 비교)
- `composite_score` sector 독립성 5케이스 가드
- 매크로 SSoT(`_KR_SECTOR_ETFS` / `KR_SECTOR_REPS`) 무변경

### 도메인 합의 (요건서 `_workspace/dev_sector_normalize/01_requirements.md`)

- KR 14 + US 11 + "기타" 폴백 (보수 원칙)
- "임의소비재"(US) vs "경기소비재"(KR) 시장별 분리 채택
- DART KSIC 도입은 후속 phase
- "Specialty Industrial Machinery"(두산에너빌리티 등) 14 KR 분류에 직매핑 없어 "기타" 폴백 — 향후 코드 화이트리스트 종목별 보강 옵션

---

## 2026-05-10 — 매크로 섹터 히트맵 KR/US 분리 + 산점도 직관화 + OAS FIFO 누적

### 매크로 섹터 히트맵 KR/US 토글 신규

KRX 자체 섹터 분류는 GICS와 1:1 매핑 안 돼 단일 표(US 11종)에 KR을 카테고리 매핑으로 끼워 넣으면 대표종목이 엉망으로 노출됨(KODEX 자동차에 이마트, KODEX 미디어에 통신사 등). 시장별 별개 화면으로 분리.

- **`services/macro_service.py:get_sector_heatmap()`** 응답 확장 — `sectors_us`(11) + `sectors_kr`(14) 동시 반환. `sectors` 키는 백워드 호환을 위해 US 데이터 유지.
- **`stock/macro_fetcher.py:_KR_SECTOR_ETFS`** — KODEX IT(157490) 추가로 13→14종. 네이버/카카오/삼성SDS/엔씨/넷마블 등 인터넷·SI 섹터 추적 가능. KRX 산업분류상 "서비스업"이라 기존 13개 섹터에 미포함이었음.
- **`frontend/src/components/macro/SectorHeatmapSection.jsx`** — ReportPage 패턴의 KR/US 토글(회색 배경 + 선택 시 흰색 shadow). 부제로 분류 기준 명시("KRX 자체 분류 13섹터" / "GICS 11섹터"). 시장 전환 시 펼친 섹터 자동 닫힘.
- **레이아웃 좌우 분할** — `lg:grid-cols-2`로 데스크탑은 산점도(좌) + 히트맵 테이블(우) 한 화면. 모바일은 세로 스택(반응형).
- **`frontend/src/components/macro/sectorRepresentatives.js` 신규** — KR_SECTOR_REPS에 KODEX/TIGER ETF 14개 각각의 실제 비중 상위 5종목 직접 정의(ETF symbol 키). GICS 카테고리 폴백은 안전망. US는 GICS 카테고리 매핑 그대로(표준이라 정확).

### 섹터 산점도 직관화 (옛 기준 유지 + 한국식 용어)

새 기준(1M × 1Y 수익률)은 직관적이나 점이 위쪽에 몰려 분산도 떨어짐. 옛 기준(`trend_days × intensity_z`) 복귀 + 한국 투자자 친숙 용어로 라벨만 직관화.

- **`frontend/src/components/macro/SectorRelativeChart.jsx`** — x축 `trend_days`를 `🟢 골든크로스 N일째 / 🔴 데드크로스 N일째`로 표기. y축 `intensity_z`를 `평균 대비 ±σ`로 표기. 4분면 한국식 라벨: ↗ 추세 가속 / ↖ 전환 직전 / ↘ 추세 약화 / ↙ 약세 가속. 각 분면 안쪽에 큰 컨셉 라벨 + 우상단 2x2 범례 + 하단 회색 박스에 정의 설명(20일 이동평균선 돌파 후 유지된 일수 / z-score 의미).
- 툴팁 — 4분면 컨셉 배지 + `🟢 골든크로스 N일째` + 강도(σ) + 1Y 수익률.

### HY OAS 시계열 자체 누적 인프라 (FRED 라이센스 변경 대응)

ICE BofA 라이센스 정책 변경(2026-04~)으로 FRED `BAMLH0A0HYM2`가 최근 ~3년치만 반환. 매일 +1일치 누적해 시간이 지날수록 시계열 확장.

- **`stock/oas_history_store.py` 신규** — cache.db 영속(50년 TTL = 사실상 무한) FIFO 누적 store. `merge_and_persist(series_id, new_rows)` / `slice_history(series_id, years)` / `cleanup(series_id)`. 10년 보존 후 가장 오래된 항목 자동 제거. 키 스키마 `macro:oas_history_persist:{series_id}`.
- **`stock/macro_fetcher.py:_fetch_fred_oas()`/`_fetch_fred_ig_oas()`** — FRED 신규 데이터(rows)를 누적 store에 머지 후 store에서 10년/5년 슬라이스 사용(FRED 직접 슬라이스 fallback 보존). 신규 1일치 자연 머지 + FIFO retention.
- **`tests/unit/test_oas_history_store.py` 신규** — FIFO 누적/머지 vintage 보존/slice years 분기/series_id isolation 7개 테스트.

### HYG ETF 프록시 시도 → 제거 (사용자 검토 결과 신뢰도 부족)

HYG 분배수익률은 6~12개월 전 매수 채권의 쿠폰 lag 반영이라 OAS의 실시간 YTM·옵션 조정과 본질적으로 다름. 평균 캘리브레이션은 절대 레벨만 맞출 뿐 변곡점 시점 자체가 어긋나 신용 사이클 전환점에서 정확히 반대 방향이 나올 수 있음. 사용자 결정으로 방향 A(FRED만 정직 표시 + 자체 FIFO 누적)로 정리.

- `_fetch_hyg_proxy_oas()` 함수(96줄) + `fetch_credit_spread()` 내 hyg_proxy 호출/캘리브레이션 로직/응답 필드 3개(`hy_proxy_current`/`hy_proxy_history_10y`/`hy_proxy_offset`) 모두 제거.
- `frontend/src/components/macro/CreditSpreadSection.jsx` — ComposedChart→AreaChart 복귀, Line/Legend/proxy 머지 로직 모두 제거. 면책 텍스트 갱신("FRED 라이센스 변경으로 ~3년만 표시. 매일 +1일치 자체 누적되어 시간이 지날수록 시계열 확장"). 캐시 키 v7→v8.

### 회귀 가드

- 백워드 호환: `get_sector_heatmap` 응답 `sectors` 키 유지(US 데이터). 옛 호출자(예: macro-cycle 섹터 로테이션 입력) 영향 0.
- `oas_history_store`는 별도 시리즈(`BAMLH0A0HYM2`/`BAMLC0A0CM`)별 격리 — 한 시리즈 손상이 다른 시리즈 미파급.
- `_compute_sma20_trend_days` / `_compute_intensity_zscore` 응답 필드(`trend_days`/`intensity_z`) 그대로 보존 — 산점도 외 다른 곳에서 참조 가능성 보호.
- 프론트 빌드 ✓ / 백엔드 fetch_credit_spread/get_sector_heatmap 응답 검증 ✓.

---

## 2026-05-09 — 배포 실패 5건 누적 원인 해소 (pycryptodome 누락)

### 진단 (사용자 후속 보고 "DB손해보험 재무내역 여전히 안 됨, 캐시 문제인지?" 추적)

사용자 의문은 캐시였으나, 운영 진단 결과 **새 코드 자체가 5건 연속 배포 실패로 운영에 미반영**된 상태. 실제 캐시 무관:

- 운영 컨테이너 이미지 태그 `02d76aab...` (5건 전 커밋)
- 컨테이너 내부 `_resolve_yf_code` 0회 매칭, `corp_code` 0회 매칭 — 새 코드 모두 미반영
- GitHub Actions Deploy 워크플로우 직전 5건(`b71ddf1`/`010c8b7`/`4970ce3`/`2f0a414`/`0c96fb5`) 모두 `failure`
- 각 워크플로우 `CI / Backend Tests` step의 "Run tests"에서 동일 실패: `tests/unit/test_wrapper_overseas_*.py` 4 모듈 collection error → `wrapper.py:16: from Crypto.Cipher import AES` → `ModuleNotFoundError: No module named 'Crypto'`
- 운영 컨테이너에서도 `python -c "import Crypto"` → `ModuleNotFoundError`. wrapper.py 자체가 import 실패. routers/services는 lazy import(`stock/kis_overseas_client.py:71`, `services/quote_overseas.py:419`)로 우회 — KIS 미국 시세 KIS-우선 경로가 항상 None → yfinance fallback로만 동작 중(graceful 흡수돼 표면화 안 됨)

### 변경

- **`requirements.txt`**: `pycryptodome>=3.20` 추가. CLAUDE.md에 "미포함, 별도 설치"로 명시되어 있던 항목이 실제로는 `wrapper.py` 모듈 레벨 import이라 누락 시 (1) CI test collection error → 배포 차단, (2) 운영 wrapper.py import 실패로 KIS 체결통보(H0STCNI0)·KIS 미국 시세 정상 경로 무력화. 운영 이미지에 누락된 상태로 5건 누적된 것이 본질적 회귀 미감지의 원인.
- **`CLAUDE.md`**: "미포함" 표현 제거 → `requirements.txt` 포함 항목으로 갱신 + "누락 시 wrapper.py import 자체가 ModuleNotFoundError로 실패해 CI/배포 차단" 명시.

### 영향 (배포 성공 후)

- 5건 누적 변경(KR 자문 데이터 수집 결함 2건 / 한글화 / CLAUDE.md 압축 / 모델 라우팅 정책 / 백테스트 fire-and-poll / 백테스트 504 nginx fix / 매크로 GPT 캐시 cleanup)이 한 번에 운영 반영됨
- DB손해보험 005830 재무내역·자문 데이터 정상 회복 (별도 캐시 작업 불필요 — 새 코드 캐시 키가 자동 분리되어 raw 코드 빈 응답 캐시는 자연 우회)
- KIS 체결통보 AES 복호화 + KIS 미국 시세 KIS-우선 경로도 동시 회복 (사이드 이득)

### 회귀 가드

- `pycryptodome` 의존성 추가 외 코드 변경 0건
- `wrapper.py:16` import 패턴은 기존 그대로 유지 (의존성 충족만 확보)
- 향후 동일 회귀 차단: CLAUDE.md에 명시적 경고 추가 — "pycryptodome 누락 시 wrapper import 자체 실패"

---

## 2026-05-09 — KR 자문 데이터 수집 인프라 결함 2건 근본 수정 + 로그인/회원가입 한글화 + CLAUDE.md 6개 압축

### 진단 (DB손해보험 005830 재무 수집 실패 — 운영 SSM 라이브 분석)

사용자 보고는 단일 종목 이슈처럼 보였으나, 운영 EC2 SSM Send-Command 로그 분석 결과 **두 가지 별개의 인프라 결함이 005830에서 동시 노출**된 것으로 확인:

1. `WARNI [stock.research_collector] DART 공시 수집 실패 005830: DART API 오류 (100): corp_code가 없는 경우 검색기간은 3개월만 가능합니다.`
2. `ERROR [yfinance] HTTP Error 404: Quote not found for symbol: 005830` / `possibly delisted; no price data found  (period=10y)` / `No earnings dates found`

**확인된 근본 원인** (운영 라이브 검증):
- **결함 #1 (yfinance)**: KR 6자리 raw 코드(`005830`)가 yfinance에 그대로 전달되어 404. 라이브 검증 — `yf.Ticker("005830")` → `last_price: None`, 404 "Quote not found"; `yf.Ticker("005830.KS")` → `last_price: 164,600원`, `market_cap: 9.98조원` 정상. `_collect_management`처럼 `_kr_yf_ticker_str()` 거치는 경로는 보호됐으나, `_collect_valuation_band`(`fetch_earnings_dates(code, limit=12)`)는 raw code 직접 전달로 노출.
- **결함 #2 (DART)**: `screener/dart.py:fetch_filings()`이 `corp_code` 인자 없이 365일 호출 → DART 정책 강화로 거부. 라이브 검증 — `corp_code=None + 365일` → `status=100`; `corp_code='00159102' + 365일` → `status=000`, **6건 정상 응답**. `_load_corp_map()` 매핑 크기 3,963개 정상 — 005830 corp_code(`'00159102'`)는 항상 존재했고, 이전 코드가 lookup 자체를 안 한 것이 본질. 모든 KR 종목이 동일 영향(005830만의 문제 아님).

### 변경 (백엔드 — 결함 #1, KR raw 코드 가드)

- **`stock/yf_client.py`**: `_resolve_yf_code(code)` 헬퍼 신규 — 6자리 숫자 KR 코드면 `_kr_yf_ticker_str()`로 `.KS`/`.KQ` 자동 부착. 이미 변환된 ticker(`005830.KS`)/매크로 심볼(`^TNX`)/US 알파벳(`AAPL`)/빈 입력은 그대로 통과(무한 재귀 방지). `_ticker()` 진입부에서 자동 적용 → 모든 yfinance 호출이 일괄 보호됨.
- **`stock/yf_client.py`**: `validate_ticker`/`fetch_company_officers`/`fetch_major_holders`/`fetch_earnings_dates`/`fetch_sector_peers` 5개 함수 진입부에 `code = _resolve_yf_code(code)` 명시적 가드 추가 — 캐시 키 일관성(이전 raw 코드 빈 응답 캐시 24h~7일 락-인 방지). 변환 실패 시 raw 반환(yfinance 404 graceful, 호출자 try/except 흡수).

### 변경 (백엔드 — 결함 #2, DART corp_code 활용)

- **`screener/dart.py`**: `fetch_filings(start_date, end_date, *, corp_code=None)` 시그니처 키워드 인자 확장(백워드 호환 100%). `corp_code` 있으면 DART API params에 포함되어 단일 회사 + 무제한 기간 조회. 캐시 키도 `corp_code` 별 분리(`dart_filings:{start}:{end}:{corp_code}`).
- **`stock/research_collector.py`**: `_collect_capital_actions`에서 `_fetch_corp_code(code)` lookup 후 365일 호출. 매핑 실패 시(corpCode.xml 다운로드 실패/신규 상장 직후 미반영 등 매우 예외적) 90일로 자동 단축 + 클라이언트 필터(DART 정책 준수). 일반 상장 종목엔 절대 발동 안 함.

### 변경 (프론트엔드 — 로그인/회원가입 한글화)

- **`frontend/src/pages/LoginPage.jsx`**: 부제목 "Investment Management System" → "투자 관리 시스템", 라벨/placeholder/버튼/링크/에러 한글화. 회원가입 직후 진입 시 success 안내 추가("회원가입이 완료되었습니다. 로그인해 주세요." — `useLocation` state.registered 활용).
- **`frontend/src/pages/RegisterPage.jsx`**: 부제목 "Create Account" → "계정 만들기", 4개 입력 필드(아이디/이름/비밀번호/비밀번호 확인) 라벨/placeholder/검증 에러("비밀번호가 일치하지 않습니다", "비밀번호는 4자 이상이어야 합니다")/버튼/링크 한글화.
- **백엔드 `services/auth_service.py`**: 모든 사용자 노출 메시지가 이미 한글이므로 변경 없음("아이디 또는 비밀번호가 올바르지 않습니다" 등).

### 변경 (문서 — CLAUDE.md 6개 일괄 압축)

전체 CLAUDE.md 6개 파일에 누적된 phase 단위 변경 이력(셀에 내장된 dated 주석)이 docs/CHANGELOG.md와 100% 중복되어 메인 CLAUDE.md 36,981 토큰까지 비대해진 상태. 모듈/컴포넌트 책임 기반 기술로 환원하고 변경 이력은 CHANGELOG로 위임:

- **루트 `CLAUDE.md`**: 402행 → 246행 (-39%), **토큰 ~37K → ~5K (-87%)**. 변경 이력 표(50여 행, 각 행이 phase 단위 수천 토큰) 통째 제거 → CHANGELOG 포인터 1줄. 환경변수 표 24행 → 기능 그룹별 9줄 요약. 하네스 섹션 에이전트 12명 상세 → 한 줄 요약(`.claude/agents/<name>.md` 단일 출처). DB 시스템 16행 표 → 그룹별 항목.
- **`stock/CLAUDE.md`**: 16178 → 11270 bytes (-30%)
- **`services/CLAUDE.md`**: 31105 → 14167 bytes (-54%)
- **`routers/CLAUDE.md`**: 13251 → 11554 bytes (-13%)
- **`frontend/CLAUDE.md`**: 31862 → 15587 bytes (-51%)
- **`screener/CLAUDE.md`**: 1962 bytes (이미 간결, 변경 없음)
- 전체 약 **-50% bytes / -65% 토큰** 절감. 영구 규칙(TR_ID 매핑/캐시 TTL/UI 색상/컬럼 순서/도메인 자문 3중 일관성 등)은 100% 보존.

### 도메인 자문 (MarginAnalyst)

- 등급/Value Trap/Graham Number 산출은 `safety_grade.py`에 이미 graceful 처리 보유 → **데이터 인프라 수정만으로 충분, 등급 코드 변경 불필요**.
- 평가 가능 항목 < 4개면 "등급 평가 불가" 표시(현행 정책 유지). best-effort + 누락 표시. Value Trap 2개 이상 "판정 불가"면 종합 판정 보류. Graham EPS·BPS 둘 다 양수 필수 정책 유지.

### 라이브 검증 (운영 EC2 SSM Send-Command)

| 항목 | 결과 |
|------|------|
| `_load_corp_map()` 매핑 크기 | 3,963개 정상 |
| `_fetch_corp_code("005830")` | `'00159102'` ✅ |
| `_kr_yf_ticker_str("005830")` | `'005830.KS'` ✅ |
| corp_code 전달 + 365일 DART 호출 | `status=000`, 6건 ✅ |
| corp_code 없이 + 365일 DART 호출 | `status=100`, "검색기간은 3개월만" ❌ (이전 코드 실패 재현) |
| `005830.KS` yfinance 호출 | `last_price=164600`, `market_cap=9.98조` ✅ |
| `005830` raw yfinance 호출 | `last_price=None`, 404 ❌ (이전 코드 실패 재현) |

### 회귀 가드

- 단위 테스트 신규 14건 PASS (`test_yf_client_resolve_yf_code.py` 10건 + `test_dart_filings_corp_code.py` 4건)
- 단위 전체 908 PASS / 0 신규 fail (17 ERROR는 PostgreSQL CI 의존, 변경 무관 베이스라인)
- yf_client KIS-first 회귀 10건 전체 PASS
- DB/도메인/주문/스크리너 알고리즘 무영향
- 기존 `fetch_filings(start, end)` 호출자 4곳(routers/earnings, routers/screener, screener/cli ×2) 모두 키워드 인자 미사용 → 백워드 호환
- 005830 외에도 동일 패턴(suffix 미부착 호출 / corp_code 없는 365일 DART 호출)을 가진 모든 KR 종목 자동 회복
- frontend 빌드 OK (vite 6.4.1 / 857 modules / 4.86s / 0 error)
- CLAUDE.md 압축은 코드 변경 0건 — 문서 컨텍스트 비대화 해소만

---

## 2026-05-09 — 작업 유형별 모델 라우팅 + 부서장 기본 진입 명시

### 운영 정책 신규
- **모델 라우팅 정책** — Claude Code의 작업 유형 기반 자동 모델 라우팅은 표준 기능 부재(공식 문서 확인). 유일한 실용 방법인 **서브에이전트 frontmatter `model:` 필드** 분기로 정책 적용:
  - **Opus 4.7** (계획·검증·자문·감사) — `department-head`/`dev-lead`/`domain-lead`/`qa-inspector`/`refactor-engineer` + 도메인 전문가 4명(`macro-sentinel`/`value-screener`/`margin-analyst`/`order-advisor`).
  - **Sonnet** (일반 구현) — `backend-dev`/`frontend-dev`/`test-engineer`.
  - **Haiku** (명령어 작성) — 사용자 정의 에이전트에 해당 없음. 빌트인 `statusline-setup`이 자연 매핑되나 frontmatter 수정 불가 → `/model haiku` 수동 전환.

### 기본 라우팅 (필수, CLAUDE.md 하네스 섹션 신규)
- **모든 비-사소 요청은 `department-head` 에이전트를 단일 진입점으로 사용**:
  1. `asset-dev` 스킬 호출 (표준 진입점, 유형 A/B/C/D 자동 분류)
  2. 또는 `Agent(subagent_type="department-head", ...)` 직접 호출
- **메인 직접 처리 가능 예외** — 정보 질문, 코드 설명, 환경변수·로컬 설정 조회, 운영 진단 read-only, 사용자 명시적 우회 지시.
- **금지** — 메인 에이전트가 12명 하위 에이전트(backend-dev/frontend-dev/도메인 전문가 등)를 부서장 우회로 직접 호출. 라우팅 책임자는 부서장.

### 변경
- **`.claude/agents/backend-dev.md`** / **`.claude/agents/frontend-dev.md`** / **`.claude/agents/test-engineer.md`**: frontmatter `model: opus` → `model: sonnet`.
- 나머지 9개 에이전트(department-head/dev-lead/domain-lead/qa-inspector/refactor-engineer + 도메인 전문가 4명) `model: opus` 유지.
- **`CLAUDE.md`**: 하네스 섹션에 「기본 라우팅 (필수)」 항목 신규 — 부서장 단일 진입점 + 직접 처리 예외 4종 + 금지 사항 + 모델 라우팅 정책 명시.
- **`README.md`**: 「모델 라우팅 정책」 섹션 신규 — 외부 독자용 카테고리 매핑 표.

### 회귀 가드
- 코드 변경 0건(에이전트 정의 frontmatter + 문서만).
- 도메인/DB/테스트 영향 0.
- 기존 `asset-dev` 스킬의 유형 A/B/C/D 자동 라우팅 100% 보존.

---

## 2026-05-09 — 백테스트 fire-and-poll 패턴 도입 (504 + "이력에 결과 보존" 동시 해소)

### 진단
- backtester EC2(`i-05c673384e1093d61`) MCP 로그 분석(SSM Send-Command):
  - MCP 정상 가동(PID 1411983, port 3846), yaml 5개 키 모두 OK → 사용자 의문(yaml `vts:`→`vps:` fix가 모드를 잘못 바꿨는지) 해소: `vps`는 KIS 공식 용어 Virtual Paper Session(모의), 원래 의도대로의 설정.
  - 단일 005930 sma_crossover 1년 백테스트 정상 완료(Lean 27.5초). backtester 자체는 작동.
  - 실패 케이스는 KIS 모의투자 인증 서버(`openapivts.koreainvestment.com:29443/oauth2/tokenP`) 응답 빈 JSON / SSL EOF / Connection refused 또는 EGW00201 rate limit. 캐시 없는 종목은 RuntimeError로 실패.
- 504와 별개로 "504 후 이력에서도 실패 처리"가 진짜 문제 — backtester가 백그라운드로 작업 진행해도 stock-manager가 동기 대기에서 끊겨 결과 회수 안 됨.

### 변경 (백엔드, fire-and-poll)
- **`db/models/backtest.py`**: `BacktestJob.mcp_job_id: String nullable` 추가 + `to_dict()` 노출.
- **`alembic/versions/a9b8c7d6e5f4_add_mcp_job_id_to_backtest_jobs.py`**: 신규 마이그레이션 — 다중 head(`e4f5a6b7c8d9` stock_info.exchange + `f5a6b7c8d9e0` orders.exchange) merge.
- **`db/repositories/backtest_repo.py`**: `set_mcp_job_id(job_id, mcp_job_id)`, `update_job_failed(job_id, error_message)` 신규. alembic 미적용 환경 graceful(`_is_mcp_job_id_column_missing`) — 컬럼 부재 시 silent skip(폴링 비활성화 + 동기 폴백).
- **`stock/strategy_store.py`**: `set_mcp_job_id` / `update_job_failed` 위임 래퍼 추가.
- **`services/backtest_service.py`**:
  - `_submit_mcp_job(client, tool_name, params)` 신규 — MCP 1단계만 호출 후 mcp_job_id 즉시 반환(wait 없음).
  - `_fetch_mcp_result_nowait(client, mcp_job_id)` 신규 — `get_backtest_result_tool(wait=False, timeout=0)` 1회 조회. 진행 중 → None / 완료 → dict / 실패 → ExternalAPIError.
  - `run_preset_backtest` / `run_custom_backtest`: 동기 `_run_and_wait` → fire-and-poll. status="running" Write-Ahead 후 `_submit_mcp_job` → `set_mcp_job_id` → 즉시 `{job_id, status:"running", mcp_job_id}` 반환.
  - `poll_backtest_job(job_id, _user_id=None)` 신규 — fire-and-poll 진입점. completed/failed면 DB 행 반환, running이면 mcp_job_id로 lazy MCP 폴링 → 완료 시 `_save_completed`, 실패 시 `update_job_failed`(친화 메시지). 일시 네트워크 오류는 status 유지(다음 폴링 재시도).
  - `_surface_error(job)` 신규 — 프론트 `useBacktest.js`가 `res.error` 직접 사용하므로 `result_json.error_message` 를 top-level `error` 로 expose.
  - `get_backtest_result(job_id)` → `poll_backtest_job` 위임.
  - `run_batch_backtest`: `run_preset_backtest`가 fire-and-poll로 바뀌어 동기 결과를 못 받게 되므로 batch 내부에서 `_run_and_wait` 직접 호출(동기 흐름 유지). `user_id` 시그니처 추가.
- **`routers/backtest.py`**:
  - `POST /run/preset`/`/run/custom`/`/run/batch`: 코드 변경 없이 응답이 자동으로 `{job_id, status:"running"}`로 변경(서비스 계층 변경의 자연 효과).
  - `GET /result/{job_id}`: `backtest_service.get_backtest_result(job_id)` → `backtest_service.poll_backtest_job(job_id, user_id=user["id"])`. 프론트 3초 폴링이 자연스럽게 진행 상태 트리거.

### 프론트 변경 (0건 — 이미 인프라 갖춰짐)
- `frontend/src/hooks/useBacktest.js`: 3초 × 200회(10분) 폴링 인프라 이미 구현. `runPreset`/`runCustom` 응답 받으면 `startPolling(job_id)` 자동. status `running` 받으면 그대로 폴링 지속.
- `frontend/src/components/backtest/BacktestResultPanel.jsx`: `result.metrics` / `result.result?.metrics` / `result.result_json?.result?.metrics` 3 fallback 체인이 이미 들어있어 동기/비동기 응답 shape 모두 호환.

### 검증
- 신규 단위 18 케이스(`tests/unit/test_backtest_fire_and_poll.py`):
  - `_submit_mcp_job`: get_backtest_result_tool 호출되지 않음 / job_id 부재 시 ExternalAPIError
  - `_fetch_mcp_result_nowait`: running/in_progress → None, completed → dict, failed → ExternalAPIError
  - `run_preset_backtest`: 즉시 `{status:"running", mcp_job_id}` 반환 + Write-Ahead + `set_mcp_job_id` / 제출 실패 시 `update_job_failed` + raise
  - `poll_backtest_job`: completed → MCP 호출 없이 DB 반환 / running + 진행중 → DB 그대로 / running + 완료 → `save_backtest_result` / running + 실패 → `update_job_failed` 친화 메시지 / mcp_job_id 부재 → graceful / KIS_MCP_ENABLED=false → graceful / 일시 네트워크 오류 → running 유지(failed 마킹 안 함) / not found → NotFoundError
  - `_surface_error`: failed 행의 `result_json.error_message` 를 top-level `error` 로 expose
- 단위 회귀: **894 PASS / 0 FAIL** (베이스라인 877 + 신규 18 - merge 1 = 894). 17 ERROR는 PostgreSQL 로컬 미가동 의존(CI에서 통과).

### 회귀 가드
- `get_strategy_signals` 미터치 (단기 신호 도출은 `_run_and_wait` 동기 흐름 유지).
- 로컬 백테스트(`run_local_backtest`) 미터치 (in-process 동기, 빠름).
- DB 마이그레이션 후방호환: `mcp_job_id` 부재 환경(alembic 미적용) graceful — 폴링 비활성화되지만 에러 없음.
- 프론트 0건 변경, 백엔드 응답 shape `result_json.result.metrics` 호환 체인이 이미 존재.
- 이전 commit(`0c96fb5` nginx /api/backtest/run/ 310s)도 그대로 유지 — 로컬 백테스트 + 배치 + 안전 가드.

### 배포 후 동작
- 사용자가 백테스트 실행 → POST 즉시 200 OK + `{job_id, status:"running"}` 반환 → 프론트가 자동 폴링 시작 → 30초~5분 사이 결과 또는 실패 메시지 표시.
- 504 자체 소멸 (POST는 즉시 응답, GET 폴링은 90s 내 끝남).
- backtester 측 KIS 인증 실패 / rate limit / vps yaml 누락 등 어떤 실패도 BacktestJob row의 `result_json.error_message`에 보존 → 이력 페이지에서 사유 확인 가능.

---

## 2026-05-09 — 백테스트 504 픽스 (nginx `/api/backtest/run/` location 분리)

### 버그 수정
- **운영 dkstock.cloud 백테스트 HTTP 504 지속 발생** — 사용자 의문(외부 backtester yaml fix `vts:`→`vps:`가 모드를 잘못 바꿨는지)은 해소: `vps`는 KIS 공식 용어 Virtual Paper Session(모의)로 원래 의도대로의 설정. stock-manager → MCP 호출엔 paper/prod 플래그가 없고 backtester EC2 yaml에서 자동 판정.
- **진짜 원인 — 타임아웃 매트릭스 불일치**: `infra/nginx/app.conf:79` 의 `location /api/` 가 `proxy_read_timeout 90s` 인데, `services/mcp_client.py:52` httpx read=300s + `services/backtest_service.py:175-196` MCP wait=280s. 백테스트 실행이 90초 넘는 순간 nginx가 504로 잘라버림(stock-manager는 still-waiting). 2026-05-03 Phase 1 nginx 분리 시 백테스트 long-running 케이스 누락.

### 변경
- **`infra/nginx/app.conf`**: `^~ /api/backtest/run/` location 신규 추가(`/api/` 위), `proxy_read_timeout 310s` (MCP 280s + httpx 300s 보다 길게). `^~` prefix로 우선 매칭. 다른 `/api/*` 90s 그대로 유지(다른 백엔드 hang이 nginx 워커 무한 점유 방지).

### 매트릭스 정합화 (변경 후)
| 레이어 | 타임아웃 |
|--------|---------|
| nginx `/api/backtest/run/` | **310s** |
| stock-manager httpx read | 300s |
| MCP wait | 280s |

→ 280s 안에 응답 → 정상 200 / 280s 초과 → stock-manager가 `MCP 서버 응답 시간 초과` ExternalAPIError(502) 반환. 어느 경로든 504 없음.

### 회귀 가드
- 다른 `/api/*` 엔드포인트 90s 보존(백엔드 hang 방어 효과 유지)
- 백테스트 4개 흐름(`/run/preset`/`/run/custom`/`/run/batch`/`/run/local`) 모두 새 location 매칭
- 코드 변경 0건(서비스/라우터/DB/프론트 미터치)
- 도메인 알고리즘 무영향
- KIS_MCP_ENABLED=false 환경 무영향(로컬 백테스트도 동일 prefix)

### 검증 (배포 후)
```bash
sudo docker exec nginx nginx -t                           # syntax ok
sudo docker exec nginx cat /etc/nginx/conf.d/app.conf | grep -A2 "/api/backtest/run/"  # 310s 확인
# Long-running 다종목 10년 백테스트 → 200 (이전 504)
```

### 후속 (선택, 별도 phase)
- 비동기 fire-and-poll 패턴 도입 — POST 즉시 job_id 반환 + 프론트 폴링. nginx 90s 그대로 가능. 변경 6+파일 범위로 별도 phase 권고.

---

## 2026-05-09 — 매크로 GPT 캐시 일일 자정 cleanup + 헤더 sticky

### 운영 정책 신규
- **매크로 GPT 캐시 일일 자정 정리** — `macro_gpt_cache` 테이블에 무한 누적되던 데이터를 매일 KST 00:05 cleanup. 매크로 정보는 당일치만 유지(어제 이전 row 자동 삭제).
  - 사용자 보고: `cleanup_old(days=30)` 함수는 있었으나 어디서도 호출되지 않는 상태 발견.
  - 사용자 결정: ① 대상 = `macro_gpt_cache` 테이블만 (cache.db `macro:*` TTL 캐시 미터치 — 1년 스파크라인/5년 OAS 등 장기 시계열 보호), ② 트리거 = APScheduler 자정 KST 00:05 cron(자정 정각 race 회피로 5분 여유).

### 변경
- **`db/repositories/macro_repo.py`**: `delete_before_today()` 신규 — `DELETE FROM macro_gpt_cache WHERE date_kst < today_kst`, 삭제 건수 반환. 기존 `cleanup_old(days=30)`/`delete_today(category)`와 별개.
- **`stock/macro_store.py`**: 위임 래퍼 `delete_before_today()` 추가.
- **`services/scheduler_service.py`**: `_run_macro_cleanup_job()` 잡 + APScheduler `CronTrigger(hour=0, minute=5)` 등록(replace_existing=True). `setup_scheduler()` 시작 로그에 `00:05 매크로 cleanup` 추가. main.py lifespan 통합으로 EC2 재기동 시 다음 KST 00:05에 자동 실행.
- **`tests/integration/test_macro_repo.py`**: `TestMacroDeleteBeforeToday` 3 케이스 — (a) yesterday+older 일괄 삭제 / (b) 빈 테이블 0 반환 / (c) today 보존.

### UI 개선
- **`frontend/src/components/layout/Header.jsx`**: `<header>` 루트 className 에 `sticky top-0 z-40` 추가. 스크롤 시 메뉴바가 viewport 상단에 고정 유지(`position: sticky`, fixed와 달리 페이지 흐름 유지). 모달/드롭다운(z-50+)이 헤더 위에 표시되어 가림 없음.

### 회귀 가드
- 도메인 알고리즘(macro_regime/macro_cycle) 무영향
- 기존 `save_today` / `get_today` / `cleanup_old(days=30)` / `delete_today(category)` 100% 보존
- cache.db `macro:*` TTL 캐시 미터치(장기 시계열 보호)
- 일반 페이지 콘텐츠 레이아웃 변경 0 (sticky는 fixed와 달리 콘텐츠 점프 없음)
- 백엔드/DB/프론트 모달·드롭다운 스택 무영향
- 단위 회귀: **877 PASS / 0 FAIL** (베이스라인 874 + 신규 통합 3건). 17 ERROR는 PostgreSQL CI 의존 환경(변경 무관).

### 검증 (사용자 측)
- 운영 배포 후: `curl -sf https://dkstock.cloud/api/pipeline/status | jq '.jobs[] | select(.id=="macro_cleanup")'` → 다음 실행 시각 확인
- 다음 KST 00:05 직후 docker logs 에서 `[스케줄러] 매크로 캐시 cleanup 완료: N건 삭제` 확인
- 브라우저: 페이지 스크롤 시 헤더 고정 유지

---

## 2026-05-09 — 백테스트 500 두 갈래 픽스 + 운영 가시성(CloudWatch + error_id) + KIS yaml SSM 영속화

### 배경
운영(dkstock.cloud)에서 두 종류 백테스트 오류 보고:
1. **MCP 단일 종목**: `오류: MCP 백테스트 실패: 백테스트 실패: 데이터 준비 실패: 'vps'`
2. **로컬 포트폴리오 (2종목 이상)**: 본문 메시지 없이 raw HTTP 500, 종목 무관 100% 재현

### 진단 (SSM Send-Command, 자격증명 본문 미노출)
**Bug A — MCP 'vps' KeyError**: backtester EC2 (`i-05c673384e1093d61`)의 `~/KIS/config/kis_devlp.yaml`에서 KIS 모의투자 모드 식별자 키가 누락. 필수 5개 키(`my_agent`/`prod`/`vps`/`ops`/`vops`) 중 `vps:`만 `vts:`로 잘못 작성됨. KIS MCP 코드 `kis_backtest/providers/kis/auth.py:158`의 `svr = "vps" if is_paper else "prod"`가 dict 접근 시 KeyError → `RuntimeError: 데이터 준비 실패: 'vps'` 전파. **stock-manager 호출 양식 회귀 아님** — backtester EC2 yaml 휴먼 에러.

**Bug B — 로컬 포트폴리오 raw 500**: 종목 무관 100% 재현 = 입력 독립 = 인프라 레이어 패턴. 4 후보 식별:
1. alembic `BacktestJob.symbols` 컬럼 부재 SQL 에러 → ServiceError 변환 회피 → raw 500
2. `data_loader.py` yfinance None 응답 영구 캐시
3. `engine.py` datetime 미스매치 (`pd.Timestamp(date_obj)` vs DataFrame index)
4. `result_json` numpy/Timestamp JSON 직렬화 실패

### 즉시 복구 (SSM Send-Command)
```bash
# yaml rename + MCP 재기동
sudo -u ec2-user sed -i 's/^vts:/vps:/' /home/ec2-user/KIS/config/kis_devlp.yaml
# 결과: OK_my_agent / OK_prod / OK_vps ← 핵심 / OK_ops / OK_vops, VTS_REMOVED
# MCP 재기동 → PID 1411983 health {"status":"ok","version":"0.1.0"}
```

### 변경 (코드 6 + 인프라 4 + 테스트 6 + 문서 2)

#### Backend (코드 6)
- **`services/backtest_service.py`**: `_classify_local_failure(exc)` 분류 헬퍼(db_error/serialize/timeout/data_load/unknown) + `_classify_backtester_error(error_msg)` MCP 응답 분류(`vps_key_missing`/`data_prep`/None). `'vps'` 패턴 우선순위 > `데이터 준비 실패`. `_VPS_KEY_FRIENDLY_MESSAGE`(yaml 가이드) + `_DATA_PREP_FRIENDLY_MESSAGE`(종목/날짜 가이드). save_backtest_job try/except → ServiceError 변환. `_to_jsonable` 응답 직렬화 안전화. 원본 error는 logger.warning 보존.
- **`services/local_backtest/data_loader.py`**: yfinance None 영구 캐시 회피(조기 return) + 1회 재시도(5초 대기) + `_cache` TTL 10분.
- **`services/local_backtest/engine.py`**: 모든 종목 DataFrame `df.index = df.index.normalize().tz_localize(None) if df.index.tz else df.index.normalize()` 통일. `_idx_for()` None 시 `logger.debug` silent skip 가시화. `_to_jsonable(obj)` 재귀 헬퍼 — numpy float64/int64 → Python native, pd.Timestamp → ISO 문자열.
- **`db/repositories/backtest_repo.py`**: `create_job(..., symbols=...)` `OperationalError` 자동 감지 → INSERT 페이로드에서 `symbols` 자동 누락 후 재시도(graceful, 마이그레이션 미적용 환경에서도 동작).
- **`routers/backtest.py`**: `run_local`/`run_preset`/`run_custom`/`run_batch` 4 핸들러 entry/exit 로그 — entry: preset/symbols 길이/market/dates/user_id, exit: job_id/duration_ms/status. telemetry `backtest.local.{success,fail.cause}` 카운터.
- **`main.py`**: ServiceError handler에 `error_id = uuid.uuid4().hex[:8]` 추가 + 응답 본문 `error_id` 필드 + `logger.error(f"[{error_id}] {e}", exc_info=True)`로 매칭. lifespan에 `alembic_command.current()` vs `head` 비교 + 불일치 시 `logger.error("alembic 미적용: current={}, head={}")` 부팅 알림.

#### Infra (4)
- **`infra/modules/backtester/main.tf`**: `aws_iam_role_policy.backtester_ssm_params`에 `ssm:PutParameter` 권한 추가(`kis_devlp_yaml` 한정) — 자격증명 회전 시 EC2가 자기 yaml을 SSM에 갱신.
- **`infra/modules/backtester/user_data.sh`**: KIS 설정 디렉토리 준비 직후 `aws ssm get-parameter --name /stock-manager/prod/kis_devlp_yaml --with-decryption`로 yaml 자동 다운로드 + chmod 600 + chown ec2-user + 필수 5개 키 검증(자격증명 본문 미노출, 키 라벨만 출력) + 미등록 시 WARNING + 수동 작성 fallback.
- **`infra/modules/compute/main.tf`**: `aws_cloudwatch_log_group.main` (`/stock-manager/prod` retention 14일) + `aws_iam_role_policy.cloudwatch_logs`(CreateLogStream/PutLogEvents/DescribeLogStreams) + `log_retention_days` 변수(기본 14) + outputs 2건(log_group_name/log_group_arn).
- **`docker-compose.cloudwatch.yml` (신규)**: docker-compose.prod.yml override — app/nginx 서비스에 `awslogs` 드라이버. `awslogs-group: /stock-manager/prod`, region 환경변수, stream-prefix 분리(app/nginx), `awslogs-create-group: false`(Terraform 생성 가정).
- **`.github/workflows/deploy.yml`**: `CLOUDWATCH_LOGS: ${{ vars.CLOUDWATCH_LOGS || 'false' }}` env 토글 + SCP source에 cloudwatch override 포함 + staging 복사 + 배포 분기(`if CLOUDWATCH_LOGS=true → -f docker-compose.cloudwatch.yml 추가`).

#### 신규 테스트 (6 모듈, 25 케이스 + 9 케이스 갱신)
- `test_backtest_local_alembic_safe.py` (4) — symbols 컬럼 부재 mock graceful
- `test_local_backtest_data_loader_cache.py` (4) — None 미저장/재시도/TTL
- `test_local_backtest_engine_datetime.py` (3) — tz-aware/naive normalize
- `test_local_backtest_jsonable.py` (5) — numpy/Timestamp 재귀 변환
- `test_backtest_mcp_vps_error.py` (9, 갱신) — `_classify_backtester_error` 단위 3 + 메시지 매핑 + caplog
- `test_backtest_router_logging.py` (3) — entry/exit 로그 + telemetry + error_id

### 운영 영속화: KIS yaml SSM Parameter Store

Console에서 SecureString 등록 완료:
```
Name      = /stock-manager/prod/kis_devlp_yaml
Type      = SecureString
Version   = 1
LastModifiedDate = 2026-05-09T10:30:31+09:00
SSM bytes = 1110, EC2 yaml bytes = 1110, diff = MATCHED
```

EC2 재생성 시 user_data.sh가 자동 다운로드 → 휴먼 에러(`vts:` 같은 오타) 차단. 자격증명 본문은 KMS `alias/aws/ssm` 암호화 저장. 비용 무료(Standard tier 4KB 미만).

### 사용자 친화 메시지 분리

| 패턴 | 메시지 |
|------|--------|
| `'vps'` 단독 또는 혼합 | "백테스트 인증 설정 오류: backtester 서버의 ~/KIS/config/kis_devlp.yaml 에 KIS 모의투자(`vps:`) 섹션이 누락되었습니다. 운영자 조치 필요. (임시: 로컬 백테스트 사용 권고)" |
| `'vps'` 없는 `데이터 준비 실패`/`data preparation failed` | "백테스트 데이터 조회 실패: 종목 코드를 확인하거나 다른 날짜 범위로 재시도하세요. (외부 backtester 데이터 준비 실패)" |
| 그 외 | 기존 `f"MCP 백테스트 실패: {error_msg}"` 유지 |

### 회귀 가드
- 기존 MCP 백테스트(preset/custom/batch) 4종 흐름 미터치 — 메시지 변환 한 줄만 추가
- DB 스키마 변경 0건 (alembic 마이그레이션 적용 자동화만)
- 도메인 알고리즘(safety_grade/macro_regime) 무영향
- 프론트 변경 0건 (BacktestPage 응답 dict shape 보존)
- KIS_MCP_ENABLED=false 환경 무영향 (로컬 백테스트 단독 동작)
- alembic 적용 환경 후방 호환 100%
- `CLOUDWATCH_LOGS` 미설정 시 기존 json-file 그대로 (운영 영향 0)
- 단위 회귀: **874 PASS / 0 FAIL** (베이스라인 849 + 신규 25, 회귀 0). 17 ERROR는 PostgreSQL 의존 통합 테스트 환경 제약(변경 무관).

### 도메인 자문 (OrderAdvisor)
- symbols 컬럼 NULL graceful → 데이터 무결성 영향 없음 (BacktestJob 후속 조회/이력 표시 모두 NULL 허용)
- 'vps' 친화 메시지 → 사용자 의사결정 충분 (yaml 가이드 + 로컬 백테스트 권고)

### 잔여 (별도 phase 권고)
- backtester 레포(`open-trading-api/backtester`) 측 `'vps'` 키 누락 fix — 외부 레포, stock-manager 권한 영역 외
- terraform apply (admin 자격증명 + tfvars 필요) — 다음 인프라 변경 사이클에 동기화 (`stock_manager_remote`는 `iam:PutRolePolicy` 부재로 자동 실행 불가)
- GitHub Actions Variables `CLOUDWATCH_LOGS=true` 설정 + Terraform apply 후 awslogs 활성화

---

## 2026-05-09 — 해외매매화면 후속: KIS WS 호가 채널 실제 통합 + 미국 공휴일 휴장 + 실 키 통합 테스트

### 배경
이전 phase에서 해외매매화면(`/order`, `market='US'`)에 호가창/현재가상세/환율/거래시간이 도입됐으나 호가 채널은 KIS REST(`HHDFS76200100`) 2초 폴링이 1차 운영. WS 인터페이스(`KoreaInvestmentWS.subscribe_overseas_orderbook` HDFSASP0)와 메시지 파서(`wrapper.parse_overseas_orderbook`)만 마련된 상태로 실제 WS 채널은 미연결. `useUsMarketClock`도 주말 휴장만 판정. KIS HHDFS76200100/76200200 응답 필드명도 가이드 추정값으로 실 키 검증 미실시.

### 사용자 결정 (3개)
1. **WS 우선 + REST 폴백 동시 구현** — WS 정상 시 WS, 끊김 시 자동 REST 폴링 재시작
2. **모의투자 미지원 정책 무관** — 사용자가 해외거래 모의투자 미사용
3. **공휴일 10일 / 부분 휴장은 v3** — Black Friday 13:00 ET 조기마감 등 단축 거래일은 보류

### 변경
- **`services/quote_overseas.py`** (+220): `KISOverseasOrderbookWS` 신규 내부 클래스 — KIS WS HDFSASP0 단일 연결 + 다종목 토픽(`f"D{exchange3}{symbol}"`) + `wrapper.parse_overseas_orderbook` 재사용 + 지수 백오프 재연결(1→2→4→8→16→30s 캡, KIS rate limit 안전 마진) + WS 메시지 수신 시 해당 종목 REST 폴링 자동 중단/끊김 시 자동 재시작. KIS 키 부재 환경 graceful → REST 폴링.
- **`frontend/src/hooks/useUsMarketClock.js`** (+90): `US_HOLIDAYS_ET` 2026~2028 30일 명단 + `isUsHoliday(dateString)` 헬퍼 + `resolveUsPhaseByClock` 휴장 분기 강화. 공휴일: New Year/MLK/Presidents/Good Friday/Memorial/Juneteenth/Independence/Labor/Thanksgiving/Christmas. 단축 거래일은 v3 주석으로 표시.
- **`tests/integration/test_kis_overseas_live.py`** (신규, 3 케이스): `pytest.mark.live` + `KIS_LIVE_TEST` 환경변수 가드. HHDFS76200100/76200200/HDFSASP0 응답 필드명 확정용. CI 자동 SKIP, 사용자 로컬 실 키 환경에서 1회 실행.
- **`pytest.ini`**: `live` 마커 등록.
- **`_workspace/dev/05_live_test_runbook.md`** (신규): 사용자 실 키 검증 절차 + 응답 필드 보정 가이드 (`_normalize_orderbook_response` 키 매핑 한 줄 패치 위치 명시).

### 신규 텔레메트리 (8종)
`quote_overseas.kis_orderbook_ws.{start, stop, connect, disconnect, reconnect_attempt, topic_subscribe, topic_unsubscribe, message}`

### 도메인 자문 (OrderAdvisor)
- WS 재연결 백오프 1→30s 캡 — KIS 분당 connect 한도와 안전 마진 확보
- 메시지 파서는 `wrapper.parse_overseas_orderbook` 재사용 — offset 가정은 실 키 통합 테스트로 검증, 런북에 보정 위치 명시

### 회귀 가드
- 가격 채널(Finnhub/yfinance/KIS price) 무영향 — 호가 채널만 신규
- KIS WS 키 부재 환경 graceful → REST 폴링 자동 사용
- 평일 거래시간 동작 무영향 — 휴장 분기만 강화
- 통합 테스트 스크립트 CI skip — 회귀 0
- broadcast shape 5키 100% 보존 → 프론트 useQuote 변경 0건
- 도메인 알고리즘(safety_grade/macro_regime) 무영향
- DB 변경 0건
- 단위 **849 PASS / 0 FAIL** (baseline 838 + 신규 10 + 회귀 0)
- 통합 3 SKIP (KIS_LIVE_TEST 미설정 의도)
- frontend 빌드: vite v6.4.1 / 4.64s / 0 error

---

## 2026-05-08 — 해외매매화면 호가창 + 현재가 상세 + USD/KRW 환율 + 미국 거래시간

### 배경
이전 phase에서 미국 시세는 KIS로 전환됐지만 `/order` 페이지의 해외 매매화면(`market='US'`)은 `OrderbookPanel.jsx:230-234`에서 "해외주식 호가는 지원되지 않습니다" 안내만 표시. 국내(KR)는 10단계 호가창 + 호가 클릭→가격 자동입력 완성. KIS 미구현 API 4종(HHDFS76200100 호가/HHDFS76200200 상세/HDFSASP0 WS 호가/USDKRW 매수가능 환산)을 통합해 국내매매화면 수준으로 정보 밀도 향상.

### 사용자 결정 (4개)
1. **개선 범위**: 호가창 + 현재가 상세 + USD/KRW 환율 + 미국 거래시간(KST/ET) 4종
2. **호가 데이터 소스**: WS(HDFSASP0) + REST(HHDFS76200100) 동시 구현 — WS 우선/끊김 시 REST 폴백
3. **모의투자 정책**: 해외거래 미사용 → 정책 분기 생략
4. **호가 단계**: 10단계 시도, 응답 부족 시 실제 받은 단계만 표시

### 변경 (Backend 5 + Frontend 3 + 테스트 7)

#### Backend
- **`wrapper.py`** (+138): `fetch_oversea_asking_price(symbol, exchange)` 신규(HHDFS76200100, `/uapi/overseas-price/v1/quotations/inquire-asking-price`) + `fetch_oversea_price_detail(symbol, exchange)` 신규(HHDFS76200200, `/uapi/overseas-price/v1/quotations/price-detail`) + `KoreaInvestmentWS.subscribe/unsubscribe_overseas_orderbook(rsym)` 신규(HDFSASP0) + 모듈 함수 `parse_overseas_orderbook(t)` 신규(rsym 파싱 D/R + EXCD3 + SYMB, 빈 단계 동적 제외, `len(t) < 49` 안전 가드).
- **`stock/kis_overseas_client.py`** (+150): `get_kis_orderbook(symbol)` — `{asks: up to 10, bids: up to 10, total_ask_volume, total_bid_volume, exchange}`. `get_kis_price_detail(symbol)` — `{open, high, low, prev_close, volume, high_52w, low_52w, exchange}`. `_normalize_orderbook_response(raw)` 헬퍼 — None/0/누락 키 안전 처리(graceful, 실 응답 필드명 보정 시 한 줄 매핑 패치). `_resolve_exchange` 재사용. ConfigError(KIS 키 부재) raise, 기타 외부 호출 실패 None.
- **`services/quote_overseas.py`** (+45): `_orderbook_pollers: dict[symbol, Task]` + `_orderbook_poll_loop` 2초 주기 — `get_kis_orderbook` 호출 → broadcast `{type:"orderbook", asks, bids, total_*_volume}` 국내 호가와 100% 동일 shape. 종목 구독 시 폴링 시작/구독자 0 시 폴링 중단.
- **`routers/quote.py`** (+50): `GET /api/quote/us/{symbol}/orderbook` 200/503/504 + `GET /api/quote/us/{symbol}/detail` 신규 — `Depends(get_current_user)` + `kis_overseas_client` 위임. `_stream_overseas` WS 분기는 dict 메시지 그대로 forward.
- **`services/order_us.py`** (+50): `_fetch_usd_krw_rate()` 헬퍼 — `stock/macro_fetcher.fetch_currency_quotes` 재사용(USDKRW=X, 15분 캐시) lazy import. `get_overseas_buyable` 응답에 `usd_krw_rate`/`deposit_krw`/`buyable_amount_krw` 추가. 환율 조회 실패 시 USD만 정상 반환(graceful degrade).

#### Frontend
- **`OrderbookPanel.jsx`** (~30): `market !== 'US'` 가드 제거 → `showOrderbook` 항상 true. 동적 단계 표시(`displayAsks = asks.slice(0, asks.length || 10)`). USD `toFixed(2)` 포맷. 매도/매수 호가 클릭 → 기존 `onPriceSelect(price, side)`. KR/FNO 동작 0 변경(가드 제거만, 그리드 코드 100% 공유). useUsMarketClock 결합 헤더 거래시간 라벨.
- **`useUsMarketClock.js`** (신규, +110): ET 시계 4구간(`pre`/`regular`/`after`/`closed`). DST 자동 — `Intl.DateTimeFormat('en-US', {timeZone:'America/New_York'})`. 1분 setInterval. 순수 함수 `resolveUsPhaseByClock(now)` export. 반환: `{phase, label, etTime, kstTime}`.
- **`OrderForm.jsx`** (~20): US 매수가능 표시 `$X (₩X) · 환율 ₩1,XXX/USD`. 신규 필드 누락 시 USD만 표시(graceful).

### 신규 테스트 (단위 39 + API 8 = 47 케이스)
- `test_wrapper_overseas_orderbook.py` (7) / `test_wrapper_overseas_detail.py` (6) / `test_wrapper_overseas_orderbook_ws.py` (9, parse_overseas_orderbook + WS 토픽 dedupe) / `test_kis_overseas_orderbook.py` (10) / `test_quote_overseas_kis_orderbook.py` (3, _orderbook_poll_loop) / `test_order_us_buyable_krw.py` (4) / `test_quote_us_orderbook_detail.py` (8 API)

### 신규 API
- `GET /api/quote/us/{symbol}/orderbook` — 10단계 호가 REST 폴백
- `GET /api/quote/us/{symbol}/detail` — 현재가 상세

### 신규 WS 메시지 타입
- `{type: "orderbook", symbol, asks, bids, total_ask_volume, total_bid_volume}` — 2초 주기 broadcast (국내와 동일 shape)

### 회귀 가드
- 국내(KR)/FNO 호가창 무영향 — 분기 가드 제거만, 그리드 코드 100% 공유
- DB 변경 0건 (호가/상세는 실시간이라 영속 불필요)
- 도메인 알고리즘 무영향
- KIS_APP_KEY 미설정 환경 graceful — 빈 호가 + 안내
- 단위 **838 PASS / 0 FAIL** (baseline 817 + 신규 39 + 회귀 0)
- frontend 빌드: 857 modules / 5.27s / 0 error

### 후속 (별도 phase)
- KIS WS HDFSASP0 실제 통합 → 다음 phase에서 처리(2026-05-09)
- 응답 필드명 실 키 보정 → `_normalize_orderbook_response` graceful, 통합 테스트 후 한 줄 패치
- 미국 공휴일 휴장 → 다음 phase에서 처리(2026-05-09)

---

## 2026-05-08 — 미국주식 시세 KIS API 1차 대체 (현재가/일봉/15분봉)

### 배경
미국주식 시세를 yfinance에서 가져오고 있어 (1) 15분 지연, (2) 비공식 API 의존, (3) 간헐 차단 위험이 누적. KIS OpenAPI 정식 메서드로 대체 가능한 항목을 식별하여 1차 SoT를 KIS로 전환. KIS 미제공 항목(PER/PBR/52주/배당/재무/매크로 ETF)은 yfinance 유지.

### 사용자 결정 (4개)
1. **대체 범위**: 현재가(`HHDFS00000300`) + 일봉(`HHDFS76240000`) + 15분봉(`HHDFS76950200`) 3종
2. **거래소 매핑**: `stock_info.exchange` 영속 캐시 + 미스 시 NAS→NYS→AMS 순회 후 영속
3. **Fallback 정책**: KIS 우선 + 실패 시 yfinance 자동 fallback (서비스 무중단)
4. **인증**: 사용자 키 우선 + 운영자 키 폴백 (`get_kis_credentials(user_id)` 재사용)

### 변경 (Backend 6 + 테스트 6 + DB 1)

#### Backend
- **`wrapper.py`** (+75): `fetch_minute_bar_overesea(symbol, exchange, time_period, end_day)` 신규 — TR_ID `HHDFS76950200`. EXCD/SYMB/NMIN/PINC/NEXT/NREC/FILL/KEYB 페이로드. KEYB 페이지네이션 인자.
- **`stock/kis_overseas_client.py`** (신규, +291): KIS 해외 시세 단일 게이트웨이. `get_kis_price`/`get_kis_ohlcv_daily`/`get_kis_ohlcv_15min` 3종. `_resolve_exchange(symbol)` — `stock_info.exchange` 캐시 우선 → 미스 시 NAS→NYS→AMS 순회 후 영속. `_get_kis_client(user_id)` — `get_kis_credentials(user_id)` 재사용. 외부 호출 실패 시 None(fallback hook), ConfigError(키 부재) raise.
- **`services/quote_overseas.py`** (+45): `_fetch_quote_message(symbol)` — KIS 우선 + yfinance fallback. 텔레메트리 `quote_overseas.fallback_to_yf`. WS 메시지 shape 보존.
- **`stock/yf_client.py`** (+108): `fetch_price_yf`/`fetch_detail_yf`/`fetch_period_returns_yf` 미국 종목에서 KIS 우선. `fetch_detail_yf`는 가격 필드만 KIS 덮어쓰기, PER/PBR/52주/배당/sector 등은 yfinance 유지(KIS 미제공). 함수 시그니처/반환 dict 키 100% 보존. 부수 해소: logger 정의 누락 잠재 NameError.
- **`stock/advisory_fetcher.py`** (+50): `fetch_15min_ohlcv_us` KIS 우선 + yfinance fallback. `_normalize_kis_15min_to_advisory` — OHLCV 형식 통일, 정렬 과거→최신, max 300봉.
- **`db/models/stock_info.py`** (+3): `exchange: String(8) NULL` 컬럼.
- **`db/repositories/stock_info_repo.py`** (+27): `get_exchange(code, market="US")` / `set_exchange(code, market, exchange)`.
- **alembic** `e4f5a6b7c8d9_add_exchange_to_stock_info.py` 신규: NULLABLE 무손실.

### 신규 테스트 (단위 6 / 51 케이스)
test_wrapper_overseas_minute (10) / test_stock_info_repo_exchange (7) / test_kis_overseas_client (15) / test_quote_overseas_kis_first (4) / test_yf_client_kis_first (10) / test_advisory_fetcher_kis_first (5)

### 신규 텔레메트리
- `kis_overseas.{resolve_exchange,get_kis_price,get_kis_ohlcv_daily,get_kis_ohlcv_15min}.{success,fail}`
- `quote_overseas.fallback_to_yf`

### 회귀 가드
- 함수 시그니처/반환 dict 키 100% 보존(후방호환)
- DB 무손실(NULLABLE 컬럼만)
- 도메인 알고리즘(safety_grade/macro_regime) 무영향
- 매크로 ETF/지수/원자재/환율 — yfinance 그대로(macro_fetcher 미터치)
- yfinance fallback 100% 보존 — KIS 장애 시 서비스 무중단
- 단위 **817 PASS / 0 FAIL** (baseline 766 + 신규 51 + 회귀 0)

---

## 2026-05-08 — 매매화면 KRX+NXT 통합시세 + SOR 활용 + KIS API 신 TR_ID 일괄 전환

### 배경
KIS 차세대시스템 출범으로 (1) 신 TR_ID 체계 일괄 도입(구 TR_ID는 사전고지 없이 차단 가능), (2) NXT(넥스트레이드) 대체거래소 정식 가동(08:00~09:00 / 15:40~20:00 시간외), (3) 09:00~15:30 KRX+NXT 통합시세, (4) SOR(Smart Order Routing) 시세·주문 양면 노출. 기존 구현은 KRX 단일 + 구 TR_ID(`TTTC0801U`/`TTTC0802U`/`TTTC0803U`/`TTTC8036R`/`TTTC8001R`) + 호가 WS `H0STCNT0`/`H0STASP0` 고정으로 NXT 시간대(8~9시/15:40~20시) 호가 표시 불가, SOR 가격개선 효과 0, 신 TR_ID 차단 시 매매 중단 위험.

### 사용자 결정 (4개)
1. 주문 셀렉터: **SOR/KRX/NXT** 3개 (SOR 기본). 통합(UN)은 시세 전용 코드 → 주문값 X.
2. KIS 신 TR_ID 일괄 전환: 매수 `TTTC0012U` / 매도 `TTTC0011U` / 정정·취소 `TTTC0013U` / 미체결 `TTTC0084R` / 당일체결 `TTTC0081R`(EXCG_ID_DVSN_CD 필수).
3. 자동 전환: 프론트 KST 시계 4구간 + 백엔드 H0UNMKO0 장운영정보 WS 둘 다 사용. 휴장 자동.
4. DB·노출: `orders.exchange` 컬럼(alembic 1건) + 미체결/체결 테이블 거래소 배지(■KRX/◆NXT/⚡SOR) + 체결 토스트 거래소 표기.

### 거래소 매트릭스 (시세 WS)
| 시간대 | exchange | execution | orderbook | levels |
|---|---|---|---|---|
| 09:00~15:30 (정규장 통합) | UN | H0UNCNT0 | H0UNASP0 | 10 |
| 15:30~15:40 (KRX 동시호가/마감) | KRX | H0STCNT0 | H0STASP0 | 10 |
| 08:00~09:00, 15:40~20:00 (NXT) | NXT | H0NXCNT0 | H0NXASP0 | 10 |

KIS 명세 검증 완료(`docs/kis/09_KR_REALTIME.md`): NXT/통합 호가도 ASKP1~10+RSQN1~10 동일 10호가 구조 → 기존 `_parse_orderbook()`/`_parse_execution()` 재사용 가능.

### 백엔드 변경
- `services/order_kr.py`: `_KR_TR_IDS` 신 TR_ID 일괄 교체. `place_domestic_order(..., *, exchange="SOR")` body 에 `EXCG_ID_DVSN_CD` 주입. `_validate_ord_dvsn(exchange, order_type)` 검증(KRX 00~24 / NXT 00,03,04,11~16,21~24 / SOR 00,01,03,04,11~16). `_normalize_excg_code(item)` 응답 정규화 헬퍼(KRX/NXT/SOR/SOR-KRX/SOR-NXT, 누락 시 KRX 폴백). `get_domestic_open_orders` TTTC0084R로 KRX/NXT/SOR 3회 호출 + (주문번호, 거래소) dedup. `get_domestic_executions` TTTC0081R + EXCG_ID_DVSN_CD="ALL" 1회 호출. `modify/cancel_domestic_order(..., *, exchange)` 원주문 거래소 유지.
- `services/order_service.py`: `place_order(..., exchange="SOR")` 시그니처 확장 + `_VALID_EXCHANGES={SOR,KRX,NXT}` 검증 + `_is_simulation()` 모의투자 차단(SOR/NXT 시 ServiceError). PENDING insert 시 exchange 기록 → PLACED 갱신 시 KIS 응답 정밀 거래소(SOR-KRX/SOR-NXT)로 덮어쓰기. `modify_order`/`cancel_order` 진입부에서 DB orders.exchange 조회 → `EXCG_ID_DVSN_CD` 주입(SOR-KRX/SOR-NXT 는 KRX/NXT 로 환원, 거래소 변경 불가).
- `services/quote_kis.py`: `_KR_TR_MATRIX = {UN/KRX/NXT × execution/orderbook/levels}` 정의. set 멤버십 디스패치 (`_KR_EXECUTION_TR_IDS`/`_KR_ORDERBOOK_TR_IDS`/`_KR_MARKET_STATUS_TR_IDS`). `_resolve_exchange_by_clock(now_kst)` 4구간 분기. `subscribe(..., exchange="auto")` 시그니처 확장. `subscribe_market_status(queue)` 신규 — H0UNMKO0+H0STMKO0+H0NXMKO0 멀티플렉스. `_run_ws` 재연결 시 market-status 자동 재구독.
- `routers/order.py`: `PlaceOrderBody.exchange: Literal["SOR","KRX","NXT"] = "SOR"` 추가. body.exchange 흐름.
- `routers/quote.py`: `WS /ws/quote/{symbol}?exchange=auto|UN|KRX|NXT` 쿼리. 신규 `WS /ws/market-status` 엔드포인트.
- `db/models/order.py`: `Order.exchange = Column(String(16), nullable=True)`. `to_dict()` `exchange or "KRX"` legacy 폴백.
- `db/repositories/order_repo.py` + `stock/order_store.py`: `insert_order` / `update_order_status` 에 `exchange` 키워드 인자.
- alembic `f5a6b7c8d9e0_add_orders_exchange.py`: `orders.exchange varchar(16) nullable` 추가(NULL → 'KRX' 폴백, 기존 데이터 unaffected).

### 프론트 변경
- `frontend/src/hooks/useMarketClock.js` 신규: KST 시계 기반 4구간 + 휴장 판정. 1분 setInterval + `/ws/market-status` 메시지 override. 반환 `{exchange, label, isHoliday, isClosed, phase}`.
- `frontend/src/hooks/useQuote.js`: `useQuote(symbol, market='KR', exchange='auto')` 3번째 파라미터. buildUrl 에 `&exchange=` 자동 부착.
- `frontend/src/hooks/useExecutionNotice.js`: `mapOrdExgGb(code)` 헬퍼 + 응답 dict에 `exchange` 필드 자동 enrich(1=KRX/2=NXT/3=SOR-KRX/4=SOR-NXT).
- `frontend/src/components/order/ExchangeBadge.jsx` 신규: 거래소 5종 배지 공용 컴포넌트(■KRX/◆NXT/⚡SOR/⚡SOR→KRX/⚡SOR→NXT) + size('xs'/'sm').
- `frontend/src/components/order/OrderForm.jsx`: `KR_EXCHANGE_OPTIONS = [SOR(추천)/KRX/NXT]` 셀렉터(market==='KR'만 노출). `isSimulation` prop 시 SOR/NXT 비활성+안내. body.exchange 자동 포함.
- `frontend/src/components/order/OrderbookPanel.jsx`: `useMarketClock()` 결합 헤더 거래소 라벨(🟦 통합 / 🟢 NXT / 🟧 KRX / 휴장). `useQuote(symbol, market, 'auto')` — KR 종목은 시간대 자동 분기.
- `frontend/src/components/order/OpenOrdersTable.jsx` + `ExecutionsTable.jsx`: "거래소" 컬럼 + `ExchangeBadge` 사용. KR 행에서만 렌더.
- `frontend/src/pages/OrderPage.jsx`: 체결통보 토스트 거래소 prefix 표기(`[⚡SOR-KRX] 체결: 삼성전자 매수 10주 @ 71,500원`).

### KIS API 통합 문서 (docs/kis/)
- KIS OpenAPI 전체 문서(338개 시트, 1.3MB 엑셀) → 카테고리별 마크다운 23개 파일로 변환.
- `docs/kis/00_INDEX.md` 인덱스 + 22개 카테고리 파일(OAuth/주문/시세/순위/실시간/선물옵션/해외/채권). 총 337개 API 명세 포함(기본정보+개요+Layout 표+Example).
- 변환 스크립트: `scripts/kis_excel_to_md.py`. 향후 엑셀 갱신 시 동일 스크립트로 재변환 가능.

### 백워드 호환·실전/모의
- 모의투자(`openapivts.koreainvestment.com:29443`): SOR/NXT 차단(백엔드 ServiceError + UI 비활성화 이중 방어). KRX 만 허용.
- 기존 `orders.exchange=NULL` → `to_dict()` 변환 시 `'KRX'` 폴백. 기존 주문 데이터 영향 0.
- 신용/예약/통합증거금/KRX 시간외(H0STOAA0/H0STOUP0)는 v1 범위 외, v2.

### 검증
- 회귀: `pytest tests/unit tests/api -q` → **919 passed / 0 failed / 6 skipped** (baseline 680 → +239 신규 PASS).
- 단위 신규 5: `test_order_repo_exchange.py` (7) + `test_order_kr_exchange.py` (16) + `test_quote_kis_exchange.py` (17) + `test_order_service_exchange.py` (11) + `test_order_place_exchange.py` (4) + `test_quote_ws_exchange.py` (5).
- frontend build: 856 modules transformed OK (이전 854 → +useMarketClock + ExchangeBadge).

---

## 2026-05-08 — 시세판/호가창/체결통보 가격 갱신 안 되는 버그 수정 (WS URL stale token)

### 배경
사용자 보고: "시세판 메뉴가 제대로 작동하지 않고 있어. 가격 갱신이 안됨." 운영 환경(dkstock.cloud)에서 시세판 진입 시 헤더의 연결 표시가 회색("연결 중") 상태로 머물고 카드 가격이 갱신되지 않음. F5 전체 새로고침 후에도 회복 불가.

### 근본 원인
WS URL의 stale access_token + 인증 처리 비대칭. 사용자가 공유한 WS handshake URL의 JWT를 디코드한 결과 `exp = 2026-05-07 17:20:04 KST`로 이미 만료. 시퀀스:
1. `useMarketBoardWS.js:9`의 `const WS_URL = buildWsUrl(...)`가 **모듈 로드 시점에 1회만** 평가되어 `localStorage.access_token`을 즉시 URL에 박음.
2. 동시에 React 마운트 → REST API 호출 → 401 → `api/client.js:35~46`이 자동 refresh → 새 토큰 저장.
3. 하지만 WS는 **이미 stale URL로 시도** → 백엔드(`routers/market_board.py:128~137`)가 `verify_token` 실패 → `code=1008` close.
4. `useWebSocket.js:71~80`이 **동일 stale URL**로 무한 백오프(500ms→10s) 재시도 → 회복 불가.

REST는 401 인터셉터로 자동 갱신되지만 WS 경로엔 동등한 인터셉터가 없는 것이 본질. F5 해도 모듈 const 평가가 401 refresh보다 빨라 같은 시퀀스 반복.

동일 패턴이 `useExecutionNotice.js:18`(체결통보), `useQuote.js:73~77`(호가창)에도 존재하여 토큰 만료 후 호가창·체결통보도 회복 불가했던 잠재 버그.

### 변경 (4개 파일, 백엔드 0)

#### A안: `useWebSocket` lazy URL 평가 (사용자 승인)
- **`frontend/src/hooks/useWebSocket.js`**: `url` 인자 타입 확장 — `string | null | (() => string|null)`. `connect()` 안에서 `const currentUrl = typeof url === 'function' ? url() : url`로 lazy 평가. 1008 close 후 다음 백오프 재시도 시 자동으로 갱신된 access_token을 읽어 자기치유. jsdoc 갱신.
- **`frontend/src/hooks/useMarketBoardWS.js`**: 모듈 const `WS_URL = buildWsUrl(...)` 폐기 → 모듈 함수 `buildMarketBoardUrl = () => buildWsUrl('/ws/market-board')` (안정 reference). `useWebSocket(buildMarketBoardUrl, ...)`.
- **`frontend/src/hooks/useExecutionNotice.js`**: 동일 패턴 — 모듈 함수 `buildExecutionNoticeUrl` 정의 후 전달.
- **`frontend/src/hooks/useQuote.js`**: `useMemo` string url → `useCallback([symbol, market])` url 빌더 함수. symbol/market 변경 시 함수 인스턴스 갱신 → useWebSocket 재연결 트리거 유지.

### 백엔드/DB/도메인 영향
백엔드(`routers/market_board.py`, `services/quote_kis.py`), nginx(`infra/nginx/app.conf`), 인증 흐름은 모두 정상 — 클라이언트 측 단일 버그. **DB 마이그레이션 0건**.

### 자기치유 흐름
stale token으로 첫 시도 → 1008 close → 백오프(최대 10초) → connect 재진입 시 url 함수 다시 호출 → REST가 그동안 refresh한 새 토큰이 박힌 URL로 정상 연결.

### 검증
- frontend 빌드 OK (854 modules transformed).
- 회귀: 백엔드 변경 0건이므로 기존 테스트 회귀 0.
- 수동: 운영 배포 후 시세판/호가창/체결통보 모두 토큰 만료 사이클 후에도 자동 회복 확인 필요.

---

## 2026-05-07 — AI 자문 입력데이터 패널 사업 개요/부문 크래시 버그 수정 + 객체 통째 렌더 방어망

### 배경
사용자 보고: AI 자문 보고서의 "AI분석 입력 데이터" 패널에서 "사업 개요/부문" 카드를 펼치면 페이지가 터지는 버그. 다른 카테고리도 동일 위험이 있는지 점검 요청.

### 근본 원인
`frontend/src/components/advisory/ResearchDataPanel.jsx`의 `renderSegments`가 백엔드 응답 shape와 키 mismatch — 백엔드(`stock/advisory_fetcher.py:fetch_segments_kr/yf`)는 `{segment, revenue_pct, note}` 형태로 반환하지만 프론트는 `s.name`/`s.ratio`를 봄. `s.name`이 undefined면 `s.name || s` 폴백이 **객체 자체**를 React child로 넘겨 `"Objects are not valid as a React child"` 에러로 페이지 크래시.

### 버그 수정
- `renderSegments`: `segName = typeof s === 'string' ? s : (s?.segment || s?.name || s?.product || '-')` + `segPct = s.revenue_pct ?? s.ratio ?? s.percentage ?? s.pct` 순으로 키 매핑. `s.note`(예: "AI추정")는 작은 회색 라벨로 표시. keywords 배열 항목이 객체일 경우도 안전 처리.
- `hasData` 조건에 `keywords-only` 케이스 추가(키워드만 있는 종목도 카드 펼침 가능).

### 회귀 방지 — 공용 안전망
- `MiniStat` / `Tr` 공용 컴포넌트에 `_safeText()` 헬퍼 적용 — value가 객체이면 `JSON.stringify`로 변환 후 렌더. 향후 16개 카테고리 중 어떤 백엔드 응답이 객체로 오더라도 페이지 크래시 없이 `[object]` 또는 JSON 문자열로 폴백 표시.

### 다른 15개 카테고리 점검 결과 (백엔드 ↔ 프론트 키 일치 검증)
- 재무 3종(손익/BS/CF) / 분기 / 계량지표 / 밸류에이션 5Y / 10년 밸류에이션 밴드 / 포워드 추정 / 증권사 컨센서스 / 기술 시그널 / KIS 퀀트 / 경영진 / 자본행위 / 업황 / 거시지표 — 모두 키 mismatch **없음**.
- `renderTechnical`은 `JSON.stringify` 가드 기존, `renderManagement`/`renderForward`는 yfinance string 응답이라 안전.
- 명백한 크래시 버그는 `renderSegments` 1건만 발견.

### 영향
- 변경 파일 1개: `frontend/src/components/advisory/ResearchDataPanel.jsx` (+40 -11).
- 빌드 OK (854 modules).
- DB/백엔드 변경 0건.

---

## 2026-05-07 — 백테스트 강화: 4개 KR 전략 프리셋 + 포트폴리오 다중 종목(최대 10) 균등 배분

### 배경
사용자 요청: 라이브 트레이딩 시스템에서 운용 중인 4개 KR 전략(상한가 모멘텀 / 변동성 돌파 / 20일 신고가 스윙 / 롱테일 변동성)을 stock-manager 백테스트에 추가하고, 동시에 최대 10종목 포트폴리오 백테스트 지원. 라이브 코드는 KIS 거래량순위 API·1분봉·15:20 강제청산 등 intraday 의존이 강해 그대로 외부 backtester(Lean)로 이식하기 어려움 → 사용자 협의로 룰을 일봉 단위로 단순화(트레일링·15:20 청산 생략) → stock-manager 자체 Python 일봉 엔진 신설.

### 백엔드 — `services/local_backtest/` 패키지 신설
- `engine.py` — 일봉 시뮬레이터 메인 루프(매일 보유 청산→신규 매수 후보 수집→슬롯 가용분 균등 배분→MTM 평가→equity_curve 갱신).
- `portfolio.py` — `PortfolioState` 균등 배분 자본 관리. `max_slots = min(10, len(symbols))`. 슬롯 가득 차면 신규 신호 스킵(라이브 자본 부족 거동 일치). 청산 시 자본 회수 → 다음 매수에 재사용.
- `metrics.py` — 8개 메트릭(`total_return_pct`/`cagr`/`sharpe_ratio`/`sortino_ratio`/`max_drawdown`/`win_rate`/`profit_factor`/`total_trades`).
- `data_loader.py` — KR yfinance 일봉 fetch + 캐시. `stock.market._kr_yf_ticker_str` + `stock.yf_client._ticker` 재사용.
- `presets.py` — 4개 KR 전략 정적 메타데이터(`id`/`name`/`description`/`default_params`/`param_schema`).
- `strategies/_base.py` — `Strategy` ABC + `EntrySignal`/`ExitSignal`/`Position` 데이터클래스. `check_entry()`/`check_exit()` 인터페이스.
- `strategies/momentum.py` — 전일종가 +29%↑ AND 종가<전일×1.30 → 당일 종가 매수 → 익일 시가 매도 → 손절 -7.5%.
- `strategies/volatility_breakout.py` — 시가+전일Range×K20 돌파 → 타겟가 매수 → 당일 종가 청산 → 손절 -3%. **K20 = 직전 20일 평균 노이즈 비율(`1 - |Close-Open|/(High-Low)`)** — 횡보장 K≈1 진입 장벽↑·추세장 K≈0 빠른 추격, Range=0 도지는 평균 제외. 라이브 표준 K=0.5 스케일과 동일 의미.
- `strategies/donchian_swing.py` — 20일 신고가 + 60EMA 5일 변화율≥0 + 거래대금≥20일 평균×1.5 + 갭<+3% → 당일 종가 매수 → 20일 저가 이탈 매도 → 손절 -7%.
- `strategies/long_tail_volatility.py` — VB 매수 + 전일대비 +3% 추가필터 → 타겟가 매수 → (a) 당일 +29% spike 시 익일 시가 매도 / (b) 그 외 당일 종가 매도 → 당일 -3%/익일 -5% 손절.

### 백엔드 — 서비스/라우터/DB 통합
- `services/backtest_service.py` — `run_local_backtest(preset, symbols, market, start_date, end_date, initial_capital, commission_rate, tax_rate, slippage, params, user_id)` + `list_local_presets()` 추가. 기존 MCP 함수(`run_preset_backtest`/`run_custom_backtest`/`run_batch_backtest`/`get_strategy_signals`) 100% 미터치.
- `routers/backtest.py` — `LocalBacktestBody` Pydantic(`symbols: list[str] = Field(min_length=1, max_length=10)`, `market="KR"` 검증, ServiceError 사용) + `POST /run/local` + `GET /local/presets` 신규 2건. MCP 라우터/엔드포인트 미터치.
- `db/models/backtest.py` — `BacktestJob.symbols = Column(JSON, nullable=True)` 추가. 기존 `symbol` 컬럼은 첫 종목 캐싱용으로 유지(인덱스/조회 호환). `to_dict()` 응답에 `symbols` 노출.
- `db/repositories/backtest_repo.py` — `create_job(symbols=...)` 키워드 인자 확장(후방호환).
- `stock/strategy_store.py` — `save_backtest_job(symbols=...)` Repository 위임.
- `alembic/versions/e1f2a3b4c5d6_add_backtest_symbols.py` — `BacktestJob.symbols` JSON 컬럼 add.

### 프론트엔드
- `frontend/src/components/backtest/SymbolMultiInput.jsx` — 1~10개 종목 칩(chip) 선택. SymbolSearchBar 재사용 + ✕ 제거 + 카운터(N/10).
- `frontend/src/components/backtest/StrategySelector.jsx` — 4탭 확장(빌더/MCP 프리셋/**로컬 프리셋(신규)**/커스텀). 로컬 프리셋 카드: 4개 KR 전략 메타.
- `frontend/src/components/backtest/BacktestResultPanel.jsx` — `result.per_symbol_contribution` 존재 시 종목별 기여도 카드 그리드, 거래내역 symbol 컬럼 추가, 로컬 거래(entry+exit 한 행)는 매수/매도 2행 펼침.
- `frontend/src/pages/BacktestPage.jsx` — `strategyMode === 'local-preset'` 분기 + `multiSymbols` state. MCP 미연결 시 페이지 차단 → 노란색 안내 배너로 완화(빌더/MCP/커스텀 탭만 차단, 로컬은 MCP 불필요).
- `frontend/src/api/backtest.js` — `runLocalBacktest()` + `fetchLocalPresets()` 추가.
- `frontend/src/hooks/useBacktest.js` — `useLocalPresets()` + `runLocal()` 훅 추가.

### 도메인 정합성
- 4 전략 모두 단기/추세 전용 → 가치주 등급(A~D)·Value Trap 6규칙·체제 매트릭스와 직교(별도 트랙). `safety_grade.py`/`macro_regime.py` 미터치.
- 균등 배분 + 슬롯 가득 시 스킵 = 라이브 자본 부족 거동.
- 일봉 단순화 한계: intraday 정밀도 ±수% 오차 가능. 손절은 일봉 저가 ≤ 손절가일 때 손절가 체결 가정.

### 백워드 호환
- 기존 MCP 백테스트(`run/preset`/`run/custom`/`run/batch`/`get_strategy_signals`) 100% 미터치.
- `BacktestJob.symbol` 그대로 유지(`symbols[0]` 자동 저장, SQL 인덱스 호환).
- `BacktestJob.symbols` JSON 컬럼은 nullable — 기존 row NULL 허용.
- `BacktestJob.strategy_type` 기존 "preset"/"custom" + 신규 "local" 추가.
- 프론트 단일 종목 모드 기본값 유지 — 로컬 프리셋 탭에서만 다중 종목 활성.

### 테스트
- `tests/unit/test_local_backtest_momentum.py` (6 케이스) — 정상 매수/상한가 제외/29% 미달/익일 시가 매도/손절 우선/필요 history.
- `tests/unit/test_local_backtest_vb.py` (6 케이스) — **횡보장 K20≈1 진입 장벽↑** + **추세장 K20≈0 빠른 추격** 양면 검증, 타겟 미달, 동일 일봉 종가 청산, 손절 우선, 최소 history 20일.
- `tests/unit/test_local_backtest_donchian.py` (6 케이스) — 20일 신고가+필터 진입/거래량 미달/갭 초과/20일 저가 이탈 매도/손절/최소 60일.
- `tests/unit/test_local_backtest_portfolio.py` (6 케이스) — 5종목 균등 배분/슬롯 가득 시 스킵/청산 후 자본 재배분/max_slots=10 캡/정확 자본 분할.
- `tests/unit/test_local_backtest_metrics.py` (6 케이스) — total_return/MDD/win_rate+PF/CAGR 1년/Sharpe 양수/empty trades 안전.
- `tests/api/test_backtest_local_endpoint.py` (4 케이스) + `tests/api/test_backtest_local_validation.py` (4 케이스) — POST /run/local 200 + per_symbol_contribution / symbols 0개·11개 → 422 / unknown preset → 400 / market != KR → 400.
- 단위 30 PASS / 회귀 baseline 648 → 680 (+32). API 8 케이스 PostgreSQL 의존 → CI 위탁.

### DB 마이그레이션
- 1건: `BacktestJob.symbols` JSON 컬럼 add (nullable).

### K20 정의 보정 (2026-05-07 후속)
- 초기 구현은 plan 표 그대로 `K20 = (H-L)/시가` 노이즈 비율을 사용 → 실무 표준 변동성돌파 K=0.5 스케일과 의미·스케일 차이(0.02 수준의 미세 가산)로 의도와 어긋남.
- 사용자 도메인 자문 반영: **K20 = `1 - |Close-Open|/(High-Low)`**(노이즈 비율) 평균. Range=0 도지 캔들은 평균에서 제외.
- 의미: 횡보장(시가↔종가 본체 작음) → noise≈1 → 진입 장벽↑(가짜 돌파 차단) / 추세장(시가↔종가 본체 큼) → noise≈0 → 빠른 추격.
- VB의 `_compute_target` 함수 1곳만 수정 → long_tail은 동일 함수 import로 자동 반영.
- 단위 테스트 헬퍼 `_build_choppy_history`(K≈1) + `_build_trend_history`(K≈0) 양면 검증 추가.

---

## 2026-05-07 — 자문보고서·포트폴리오 자문 사용자 코멘트 양면 평가 (동의/반박 + strength 1~10)

### 배경
사용자 요청: AI자문보고서·포트폴리오 자문의 분석시작 버튼 주변에 사용자 코멘트 입력박스를 추가. 코멘트를 기반으로 보고서 방향이 의견에 동의하며 논리를 강화하거나 반박하는 형태로 진행되도록 하고, 동의·반박 양쪽 의견의 강도를 10점 만점 점수로 표시.

### 백엔드 — Pydantic 스키마 + 시스템 프롬프트
- `services/schemas/advisory_report_v3.py` — `AgreePoint`/`DisagreePoint` 모델(`point: str`, `evidence: str`, `strength: int = Field(ge=1, le=10)`) + `UserCommentaryEvaluation` 모델(`user_comment`, `overall_stance: Literal["strong_agree","agree","balanced","disagree","strong_disagree"]`, `agree_points: list max 5`, `disagree_points: list max 5`, `summary`). `AdvisoryReportV3Schema.user_commentary_evaluation: Optional[UserCommentaryEvaluation] = None`(백워드 호환 — 기존 보고서 누락 시 검증 통과).
- `services/advisory_service.py` — `generate_ai_report(..., user_comment: Optional[str] = None)` 시그니처 확장. `_build_system_prompt(..., user_comment=None)` 후미 가이드 블록 6개 규칙 append:
  ① 동의/반박 양면 의무(악마의 변호인 — 한쪽 압도여도 반대측 1건 이상)
  ② strength 1~10 임계값(1~3 약한 단서 / 4~6 통상 / 7~8 강한 정량 / 9~10 결정적) + evidence 출처 명시
  ③ overall_stance 5단계(strong_agree=동의 평균≥7&반박<5 / agree=동의>반박 / balanced=±1 이내 / disagree / strong_disagree)
  ④ summary 1~3문장 직접 답변
  ⑤ 본문 8대 분석과 stance 정합성(본문 우선, stance 보정) — 등급/composite_score/action은 코멘트와 무관하게 데이터 기반
  ⑥ JSON `user_commentary_evaluation` 필드 필수 + 형식 명세
  `_build_prompt(..., user_comment=None)` user 메시지 후미에 코멘트 원문 echo.
- `services/portfolio_advisor_service.py` — `_compute_cache_key(balance_data, user_comment=None)` SHA256 payload에 코멘트 strip 후 포함(동일 잔고+다른 코멘트=다른 보고서, None/""/" "=같은 키). `analyze_portfolio(..., user_comment=None)` + `_build_system_prompt(..., user_comment=None)` 동일 가이드 블록 + `_build_prompt(..., user_comment=None)` user 메시지 echo. JSON 응답 스키마에 `user_commentary_evaluation: null|{...}` 형식 명시.

### 백엔드 — 라우터 (백워드 호환)
- `routers/advisory.py` — `AnalyzeBody(BaseModel)` 신규(`user_comment: Optional[str] = None`). `POST /{code}/analyze` body는 `Body(None)`으로 백워드 호환(기존 body 미전송 200 유지). 1000자 초과 시 `ServiceError(400)`. 정상화된 코멘트(빈 문자열/공백→None)를 `advisory_service.generate_ai_report`에 전달.
- `routers/portfolio_advisor.py` — `AnalyzeBody.user_comment: Optional[str] = None` 추가, 1000자 검증 후 서비스에 전달.

### 프론트엔드 — 입력 컴포넌트 + 결과 카드
- `frontend/src/components/common/UserCommentInput.jsx` (신규) — textarea + 글자수 카운터(0/1000) + 80% amber/100% red 임계 색상. props: `value`/`onChange`/`disabled`/`maxLength=1000`.
- `frontend/src/components/advisory/UserCommentaryCard.jsx` (신규) — 보고서 본문 최상단 카드. `evaluation` prop. 헤더(코멘트 원문 인용 + stance 5단계 배지: strong_agree=green/agree=lime/balanced=gray/disagree=amber/strong_disagree=red) → 좌(👍 녹색)/우(👎 빨강) 2컬럼 + 항목별 strength 1~10 게이지 막대 → 하단 summary. 모바일 1컬럼 스택. `evaluation` null 시 미렌더.
- `frontend/src/api/{advisory,advisor}.js` — `generateReport(code, market, userComment=null)` / `analyzePortfolio(balance_data, force_refresh, userComment=null)`. body에 `{user_comment}` 포함, null/공백 시 미전송(`Content-Type` 헤더도 조건부).
- `frontend/src/hooks/{useAdvisory,usePortfolioAdvisor}.js` — `generate(code, market, userComment=null)` / `analyze(balanceData, forceRefresh, userComment=null)` 시그니처 확장.
- `frontend/src/components/advisory/AIReportPanel.jsx` — 액션바 위 `<UserCommentInput>`(onUserCommentChange prop 있을 때만), 보고서 본문 최상단 `<UserCommentaryCard>`(reportData.user_commentary_evaluation 있을 때만).
- `frontend/src/components/advisor/AdvisorPanel.jsx` — "분석 받기" 버튼 위 `<UserCommentInput>`, 분석 결과 본문 상단 `<UserCommentaryCard>`.
- `frontend/src/pages/DetailPage.jsx` — `userComment` state(페이지 이동 시 초기화), `handleGenerate`에서 `generate(symbol, market, userComment || null)` 전파, AIReportPanel에 props 전달.

### 도메인 정합성
- **MarginAnalyst**: strength 1~10은 가설 검증용. 본문 등급(A~D)·composite_score는 데이터 기반 산출, 코멘트 무관(시스템 프롬프트 ⑤번 규칙).
- **OrderAdvisor**: 사용자 코멘트가 매수 권고를 만들지 않음. `action`(적극매수~전량매도)은 cycle×regime 매트릭스 + grade_factor 유지. stance는 내러티브 보강용.
- **ValueScreener**: Value Trap 6규칙 불변. 사용자가 "가치주야"라고 주장해도 trap 경고가 우선.
- **악마의 변호인 의무**: 한쪽 strength 평균이 8 이상이어도 반대측 1건 이상 제시(편향 방지).

### 캐시 전략
- 개별 종목: `advisory_reports`는 매 호출 GPT 재생성(보고서 캐시 없음) → 코멘트 재생성 자연스러움.
- 포트폴리오: `_compute_cache_key`에 코멘트 해시 포함 — 동일 잔고+다른 코멘트=새 보고서. None/""/" "=같은 키(strip 정규화).

### 백워드 호환 (4/4 PASS)
- `POST /api/advisory/{code}/analyze` body 없이 호출 → 200 (`Body(None)`)
- `POST /api/portfolio-advisor/analyze` `user_comment` 없이 호출 → 200 (`Optional`)
- 기존 보고서 조회 시 `user_commentary_evaluation` 누락 → Pydantic 통과 (`Optional[UserCommentaryEvaluation] = None`)
- DB 마이그레이션 0건 (`alembic/versions/` 18개 그대로) — JSON 컬럼 안에 자연 저장

### 테스트
**단위 4건 신규 (35 케이스)**:
- `tests/unit/test_advisory_schema_v3_user_commentary.py` (14) — strength 0/11=ValidationError, 1/10=통과, overall_stance 5단계, 누락=Optional 통과.
- `tests/unit/test_advisory_user_comment.py` (6) — `_build_system_prompt` 코멘트 유무 분기, "악마의 변호인"/"1~10" 키워드 포함.
- `tests/unit/test_portfolio_advisor_cache_key.py` (7) — 동일 잔고+다른 코멘트=다른 키, None/""/" "=같은 키.
- `tests/unit/test_advisory_router_user_comment.py` (8) — 라우터 `Body(None)` + 1000자 검증 + None 정규화.

**API 1건 신규 (8 케이스, PostgreSQL 의존 CI 위탁)**:
- `tests/api/test_advisory_analyze_with_comment.py` — body 있음/없음/1001자 체이닝, OpenAI mock.

**결과**: 단위 648 PASS / 0 FAIL / 6 skip. 회귀 0건. frontend 빌드 OK(853 modules).

### 도메인 자문 호출
**0건** — plan 사전 합의(strength 1~10/stance 5단계/악마의 변호인/등급 불변)를 그대로 코드화. MarginAnalyst/ValueScreener 추가 자문 불필요.

---

## 2026-05-07 — 자문보고서 챗봇 권한 검증 버그 수정 + 기본적분석 비즈니스 모델 섹션

### 배경
사용자 요청 2건:
1. **챗봇 버그**: 자문보고서 챗봇이 본인 보고서임에도 항상 "자문보고서를 찾을 수 없습니다"라고 응답하는 문제 — 원인 파악 + 수정.
2. **기능 추가**: 관심종목 → DetailPage → AI자문 → 기본적분석 패널에 "비즈니스 모델" 섹션 추가. "무엇을 만들어 누구에게 어떻게 팔아 이익/현금을 내는지, R&D는 어떤 분야에 투자하는지"를 한눈에 파악.

### 챗봇 권한 검증 버그 수정

**근본 원인**: `db/models/advisory.py:74-88`의 `AdvisoryReport.to_dict()`에 `user_id` 키가 빠져 있어 `services/advisory_service.py:1586`의 `report_row.get("user_id") != user_id` 검증이 항상 `None != user_id`로 실패. 결과: 어떤 사용자든 자기 보고서임에도 항상 `NotFoundError("자문보고서를 찾을 수 없습니다.")` 반환.

**부수 버그**: `routers/advisory.py:237`이 `advisory_store.get_report_by_id(user["id"], report_id)`로 인자 2개를 전달하지만 `stock/advisory_store.py:92` / `db/repositories/advisory_repo.py:155`는 `(report_id)` 1개만 받음 → `GET /api/advisory/{code}/reports/{id}` 호출 시 TypeError.

**수정 (B안 — DB 레벨 user_id 필터링 통일)**:
- `db/repositories/advisory_repo.py:155` — `get_report_by_id(report_id, user_id=None)`로 시그니처 확장. `user_id` 주어지면 `filter_by(id=report_id, user_id=user_id)` 추가.
- `stock/advisory_store.py:92` — 동일 시그니처 위임.
- `services/advisory_service.py:1583` — `advisory_store.get_report_by_id(int(report_id), user_id=user_id)`로 호출. `report_row.get("user_id") != user_id` 비교 라인 삭제(이미 Repo에서 필터링됨). code/market 일치 검증은 유지.
- `routers/advisory.py:237` — `get_report_by_id(report_id, user_id=user["id"])`로 정상화.
- `db/models/advisory.py` to_dict는 그대로(응답 보안 — user_id 노출 차단).

**검증**:
- 자문 보고서 생성 후 챗봇 질문 → 정상 답변
- 다른 사용자의 report_id로 호출 → Repo가 None 반환 → 404
- `GET /api/advisory/{code}/reports/{id}` — 본인 200, 타인 404 (이전 TypeError → 정상)

### 기본적분석 비즈니스 모델 narrative

**도메인 자문 합의** (MarginAnalyst + ValueScreener):
- **MarginAnalyst — 현금 창출 가이드** (시스템 프롬프트 내장):
  - OCF/NI 비율 — 1.0 이상이면 현금 전환력 양호, 지속 0.7 미만이면 이익의 질 의심.
  - FCF 마진(FCF/매출) + 3년 부호 일관성 — 양수 지속 + 5% 이상이면 안전마진 우호.
  - Capex 강도(capex/OCF) 분류 — <30% 자산경량, 30~70% 정상, >70% 자본집약·FCF 압박.
  - 잉여현금 사용처(배당/자사주/M&A/부채상환) 환원율 지속가능성.
  - 운전자본·일회성 항목으로 OCF 부풀려졌을 가능성 의심 시 "현금흐름 품질 주의" 명시.
- **ValueScreener — R&D 전략 가이드** (시스템 프롬프트 내장):
  - 기존 moat 강화(방어형) vs 신사업 발굴(공격형) 구분 — keywords·segments에서 단서 추출.
  - 산업 평균 R&D 비중 대비 — 반도체 8~15% / 제약 15~20% / 소비재 1~3%.
  - R&D 누적 → 매출 성장·신제품 전환(자본배분 효율) vs 비용만 증가·매출 정체.
  - Value trap 경계 — R&D 증액에도 매출 CAGR 0% 이하 / R&D 축소+배당 확대.
  - 공시 정보로 확인 불가 항목은 추측 금지, "공시 한정으로 단정 어려움" 명시.

**구현**:
- `stock/advisory_fetcher.py` — `fetch_business_model(code, name, market, segments_dict, financial_dict, user_id) -> dict`. KR/US 공통. GPT 1회(`response_format=json_object`, `max_completion_tokens=1500`, `service_name="advisory_business_model"` user_id 쿼터 차감) → `{revenue_model, cash_generation, rd_strategy}` 각 한국어 narrative. 시스템 프롬프트에 두 도메인 가이드 내장. 캐시 키 `advisor:business_model:{market}:{code}` TTL 7일(168h). 모든 필드 None이면 캐시 안 함(다음 재시도). `_format_cf_context()` 헬퍼로 매출/순이익/CF/CAPEX/FCF 최근 3년을 GPT 프롬프트 한 줄에 요약.
- `services/advisory_service.py` — `_collect_fundamental_kr/us`에서 segments 호출 직후 `fetch_business_model` 호출. fundamental dict에 `business_model: {revenue_model, cash_generation, rd_strategy}` Optional 필드 추가(백워드 호환). `_collect_fundamental_us(code, name="", user_id=1)` 시그니처 확장. `_collect_fundamental` dispatch도 `(code, market, name, user_id)` 전체 전달.
- `frontend/src/components/advisory/FundamentalPanel.jsx` — `BusinessModelSection` 컴포넌트 신규. 3카드 그리드(💰 매출 흐름 / 💵 현금 창출 / 🔬 R&D 투자), 각 카드 = 이모지 + 제목 + narrative whitespace-pre-wrap. `business_model`이 null이거나 모든 필드 빈 값이면 미렌더. `<SectionTitle>비즈니스 모델</SectionTitle>` BusinessOverview 직후 마운트.

**호출 시점**: `refresh_stock_data` 페이즈에서만(매 GET 호출 금지, research_collector 패턴). 캐시 hit 시 GPT 미호출.

### 테스트

| 카테고리 | 결과 | 비고 |
|----------|------|------|
| `tests/unit/test_advisory_business_model.py` | 8/8 PASS (신규) | 캐시 hit GPT 미호출 / TTL 7일 / 도메인 가이드 키워드 포함 / 시그니처 / 부분 응답 / 빈 응답 미캐시 / 재무 컨텍스트 키 포함 |
| `tests/unit/test_advisory_service_chat.py` | 11/11 PASS (보강) | user_id 인자 전달 검증 + 본인/타 유저 권한 케이스 신규 추가, 기존 mock 시그니처 정합 |
| `tests/integration/test_advisory_repo.py` | +2 케이스 | `get_report_by_id` user_id 필터, `to_dict` user_id 미노출 |
| 프론트 build | OK | 851 modules transformed, 1.41s |
| 회귀 영향 | 0건 | `pdfplumber` 미설치 / Docker PostgreSQL 미실행으로 인한 기존 환경 의존성 실패와 무관 |

### 변경 파일

**백엔드 (5)**: `db/repositories/advisory_repo.py`, `stock/advisory_store.py`, `services/advisory_service.py`, `routers/advisory.py`, `stock/advisory_fetcher.py`

**프론트엔드 (1)**: `frontend/src/components/advisory/FundamentalPanel.jsx`

**테스트 (3)**: `tests/unit/test_advisory_business_model.py`(신규), `tests/unit/test_advisory_service_chat.py`(보강), `tests/integration/test_advisory_repo.py`(보강)

**DB 마이그레이션 0건** / **도메인 변경 0건**(챗봇 권한 검증은 동일 정책의 위치 이동, 비즈니스 모델은 새 narrative만).

---

## 2026-05-06 — 자문보고서·포트폴리오 보고서 챗봇 + 상단 AI 사용량 게이지

### 배경
사용자 요청 2건:
1. 종목 자문보고서 / 포트폴리오 자문보고서 페이지에서 보고서 컨텍스트를 가지고 사용자가 궁금한 점을 대화로 확인할 수 있는 작은 챗봇 기능
2. 각 사용자가 자신의 일간 AI 호출 한도를 인지할 수 있도록 상단 메뉴바에 게이지바 + 수치 표시

### 보고서 챗봇 신규

**백엔드 (2 서비스 함수 + 2 라우터 엔드포인트)**

- `services/advisory_service.py` — `chat_with_report(code, market, report_id, messages, user_id)` 추가.
  - `advisory_store.get_report_by_id(report_id)` → `user_id` + `code` + `market` 일치 검증, 미일치 시 `NotFoundError`(404).
  - System prompt 빌드: 보고서 본문(JSON) 첨부 + 답변 가이드라인(보고서에 없는 사실 추정 금지 / 새 의견 생성 금지 / 한국어 간결 답변 / "보고서에 따르면 ~로 평가됩니다" 형식).
  - 슬라이딩 윈도우(최근 20개 메시지). 입력 검증(`role` user/assistant 한정 / `content` 4000자·50개 상한 / 마지막 user 강제) → `ServiceError`(400).
  - `ai_gateway.call_openai_chat(service_name="advisory_chat", max_completion_tokens=1500)`.
  - 반환: `{reply, model, report_id}`.

- `services/portfolio_advisor_service.py` — `chat_with_report(report_id, messages, user_id)` 추가.
  - `advisory_store.get_portfolio_report_by_id(report_id)`, 라우터에서 `require_admin`로 권한 차단(`PortfolioReport`는 user_id 컬럼 부재).
  - System prompt에 진단/리밸런싱/매매안/시장코멘트 첨부.
  - 동일 슬라이딩 윈도우 + `service_name="portfolio_chat"`.

- `routers/advisory.py` — `POST /api/advisory/{code}/chat` 추가. Pydantic `ChatBody { market, report_id, messages: ChatMessage[] }`.
- `routers/portfolio_advisor.py` — `POST /api/portfolio-advisor/chat` 추가(`require_admin`).

**프론트엔드 (1 API 모듈 + 1 공용 컴포넌트 + 2 페이지 통합)**

- `frontend/src/api/chatbot.js`(신규) — `chatAboutAdvisory(code, market, reportId, messages)` / `chatAboutPortfolio(reportId, messages)`.
- `frontend/src/components/common/ReportChatBubble.jsx`(신규) — 우하단 플로팅 챗봇.
  - Props: `kind('advisory'|'portfolio')` / `contextId(reportId)` / `contextLabel` / `market` / `code` / `disabled`.
  - 닫힘=원형 💬 버튼(`fixed bottom-6 right-6 z-40`, indigo-600). disabled 시 회색+tooltip "보고서 생성 후 이용 가능".
  - 열림=`w-96 max-h-[70vh]` 카드(헤더 indigo-600 + 메시지 스크롤 + 예시 질문 칩 3개 + textarea + 전송).
  - 상태: `useState`로 messages/input/pending/error 관리. `contextId`/`kind` 변경 시 messages 초기화. `AbortController`로 unmount 시 cancel.
  - Enter 전송 / Shift+Enter 줄바꿈. 응답 후 `window.dispatchEvent(new Event('ai-usage-changed'))` (성공/실패 모두).
  - 모바일: `right-6 left-4` 풀폭.
- `frontend/src/pages/DetailPage.jsx` — AI 자문 서브탭 활성 시점에 `<ReportChatBubble kind="advisory" code={symbol} market={market} contextId={report?.id} disabled={!report?.id} />` 마운트(다른 탭 미렌더링).
- `frontend/src/pages/PortfolioPage.jsx` — `<ReportChatBubble kind="portfolio" contextId={advisor.result?.report_id} disabled={!advisor.result?.report_id} />` 상시 마운트.

**도메인 정합성**: 신규 투자 로직 0건. 보고서 본문 재설명 한정. System prompt 가드("보고서 외 추정 금지", "새 의견 생성 금지", "예측·확정 표현 금지")로 환각 차단.

**영속성**: DB 마이그레이션 0건. 메시지 히스토리는 클라이언트 useState만 보관 → 페이지 이동·새로고침 시 초기화. 서버 stateless.

### 상단 AI 사용량 게이지 신규

**백엔드 신규 0** — 기존 `GET /api/admin/ai-usage/me` (`routers/admin.py:50-53`) 그대로 재사용. `services/ai_gateway.py:get_ai_usage_status(user_id) → {used, limit, remaining}`.

**프론트엔드 (1 훅 + 1 컴포넌트 + Header/App 통합)**

- `frontend/src/hooks/useAiUsage.jsx`(신규) — Context Provider.
  - `fetchMyAiUsage()` 호출, `usage`/`loading`/`refresh` 노출.
  - 마운트·`useAuth.user` 변화 시 1회 fetch. 로그아웃 시 `usage=null`.
  - `window.addEventListener('ai-usage-changed', refresh)` 등록 → 챗봇/Analyze 응답 후 자동 갱신. **폴링 X**(이벤트 기반).
- `frontend/src/components/common/AiUsageGauge.jsx`(신규) — 가로 24px 게이지바 + `used/limit` 수치.
  - 임계 색상: <50% emerald-400 / 50~80% indigo-400 / 80~95% amber-400 / ≥95% red-500.
  - hover tooltip: "오늘 AI 호출 사용량 {used}/{limit} · 남은 횟수 {remaining}".
  - `usage=null` 또는 `limit≤0` 시 미렌더(데스크톱 전용 `hidden sm:flex`).
- `frontend/src/components/layout/Header.jsx` — 우측 너비 토글 좌측에 `<AiUsageGauge />` 마운트.
- `frontend/src/App.jsx` — 최상단을 `<AiUsageProvider>`로 래핑.
- `frontend/src/hooks/useAdvisory.js` — `generate()` 응답 후(성공/실패 모두) `dispatchEvent('ai-usage-changed')`.
- `frontend/src/hooks/usePortfolioAdvisor.js` — `analyze()` 동일.

### 테스트
- `tests/unit/test_advisory_service_chat.py`(신규, 10 케이스) — 검증(빈/role/길이/마지막 user) / 권한(미존재/타인/code 불일치) / 정상 호출 / 슬라이딩 윈도우(30→20).
- `tests/unit/test_portfolio_advisor_service_chat.py`(신규, 3 케이스) — 빈 messages / 미존재 / system prompt 보고서 섹션 포함 검증.
- `tests/api/test_advisory_chat.py`(신규, 5 케이스) — 404/400/422/모킹 정상.
- `tests/api/test_portfolio_chat.py`(신규, 3 케이스) — 404/400/모킹 정상.
- 단위 13 PASS / 회귀 0 (629 PASS 유지).

### 결과
- 도메인 변경 0건. 신규 백엔드 엔드포인트 2 + 프론트 컴포넌트 2 + 통합 5 + 테스트 21 케이스. DB 마이그레이션 0건.

### 후속 — 챗봇 검증 순서 수정 (CI 실패 해소)
- `services/advisory_service.chat_with_report` / `services/portfolio_advisor_service.chat_with_report` 검증 순서를 **(1) messages 입력 검증 → (2) 보고서 조회·권한 검증 → (3) `OPENAI_API_KEY` 체크** 순으로 재배치.
- 이전: 키 체크가 가장 앞에 있어 `OPENAI_API_KEY` 미설정 CI 환경에서 입력/권한 케이스가 모두 503 반환 → API 테스트 5건 FAIL.
- 수정 후: 입력 400 / 미존재 404 / 환경 503의 의미가 외부 사용자 관점에서도 일관. 단위 13 PASS / 회귀 0.

---

## 2026-05-05 — 매크로 음영/섹터 산점도/방문수/미국체결 + FRED 안정화

### 배경
사용자 신고 4건 (협업 사이클):
1. 장단기 금리차 / 하이일드 스프레드 그래프에 NBER 침체 + S&P -20% 약세장 음영 표시
2. 섹터 히트맵 상단에 상대평가 산점도 추가 (x: 추세 지속기간, y: 강도, 색상+아이콘)
3. 사용자 관리에 사이트 방문횟수 카운트 추가
4. HY/IG OAS partial_failure 핫픽스 (운영 EC2 IP에서 FRED CSV 차단)
+ 미국 주식 체결됐는데 체결내역/미체결 미반영 (NASD 단일 거래소 한정)

### 백엔드 신규 (1)
- `services/macro_events.py` — NBER 침체 3건(2001 닷컴 / 2007-2009 GFC / 2020 코로나) + S&P500 -20% 약세장 4건(2000-2002 / 2007-2009 / 2020.2-3 / 2022.1-10) 정적 상수 + `get_events_in_range(start, end)` 범위 클립 헬퍼. 출처 NBER + Macrotrends/Yardeni 코드 주석.

### 백엔드 수정 (5)
- `stock/macro_fetcher.py` — `_http_get_fred_csv()` Mozilla UA + timeout 25s + Content-Type 검증 + 1회 재시도(2초). `_fetch_fred_via_api(series_id)` 신규(FRED 공식 JSON API 폴백, `FRED_API_KEY` 필요). `_fetch_fred_oas` / `_fetch_fred_ig_oas` 우선순위: CSV → JSON API → 7일 stale 캐시 → 빈 dict. `_compute_sma20_trend_days(closes)` + `_compute_intensity_zscore(returns_1y)` 헬퍼 신규. `fetch_sector_returns` / `fetch_sector_returns_kr` 응답에 `trend_days` + `intensity_z` 추가, 캐시 키 v2→v3.
- `services/macro_service.py` — `_events_for_history()` 헬퍼 + `get_yield_curve()` / `get_credit_spread()` 응답에 `events: {recessions, bear_markets}` 임베드(캐시 hit 경로 포함).
- `services/order_us.py` — `get_overseas_executions` + `get_overseas_open_orders`가 NASD 단일 → NASD/NYSE/AMEX 3개 거래소 순회. 체결조회는 KST 어제~오늘 명시(ET 경계 누락 방지). 중복 제거 키 `order_no::exchange`.
- `db/repositories/page_view_repo.py` — `count_by_user(user_ids: list[int]) -> dict[int, int]` 신규(1쿼리, anonymous 제외, N+1 방지).
- `routers/admin_users.py` — `GET /api/admin/users` + `GET /{user_id}` 응답에 `visit_count` 추가.

### 프론트엔드 신규 (1)
- `frontend/src/components/macro/SectorRelativeChart.jsx` — Recharts ScatterChart, 4분면 배경 음영(↗ 모멘텀강세 / ↘ 약세지속 / ↖ 반등초기 / ↙ 약세초기), 14개 섹터 키워드 매칭 색상+아이콘(💻🏦⚕️⚡🏭🛍️🛒💡🏠⛏️📡🔋🚗🚚), x축 ±365일 / y축 ±3 z-score, 범례.

### 프론트엔드 수정 (5)
- `frontend/src/components/macro/YieldCurveSection.jsx` / `CreditSpreadSection.jsx` — 침체/약세장 ReferenceArea 음영(회색 0.18 / 붉은색 0.10). 음영 좌표를 차트 데이터셋의 실제 date에 snap + `ifOverflow="hidden"`(extendDomain 부작용 회피). 인접 이벤트 라벨 dy stagger(2년 이내 클러스터 12px 계단). 좁은 음영(<365일) 라벨 단축("코로나 약세장" → "코로나"). 백분위 ReferenceLine 보존.
- `frontend/src/components/macro/SectorHeatmapSection.jsx` — 히트맵 상단에 SectorRelativeChart 마운트.
- `frontend/src/pages/AdminUsersPage.jsx` — 방문수 컬럼 추가(우측 정렬, locale toLocaleString).
- `frontend/src/pages/BacktestPage.jsx` — 시작/종료일 input `min`/`max` 속성 + 시장별 한계(US ≥ 1998-01-02 / KR ≥ 2000-01-04). 상단 가이드 박스(파란색)에 출처(QC Lean / KIS API)와 권장 기간(1년~10년) 명시.

### 환경변수 신규
- `FRED_API_KEY` (선택) — FRED 공식 JSON API 폴백용. 무료 발급(https://fred.stlouisfed.org/docs/api/api_key.html). SSM `/stock-manager/prod/FRED_API_KEY` 등록 시 운영 IP에서 CSV 차단당해도 JSON API로 자동 폴백.

### 신규 테스트 (5 + 보강 1)
- `tests/unit/test_macro_events.py` (6 케이스) — NBER/S&P 데이터 정합성, 범위 클립, 빈 범위, 인플레 약세장 포함
- `tests/unit/test_sector_trend.py` (9 케이스) — SMA20 cross 부호/cap, z-score 표준화/None/zero std
- `tests/unit/test_macro_fetcher_fred_fallback.py` (6 케이스) — 브라우저 UA, Content-Type 차단, 재시도, stale fallback, CSV 파서
- `tests/unit/test_page_view_repo_count_by_user.py` (4 케이스) — 기본/미존재/anonymous 제외/빈 입력
- `tests/api/test_admin_users_visit_count.py` (2 케이스) — 목록 + 단건 응답에 visit_count
- `tests/integration/test_credit_spread_api.py` 보강 — events 임베드(GFC 침체/약세장) 검증 1 케이스 추가
- 결과: 신규 27 PASS / 0 FAIL (회귀 0)

### 도메인 자문 합의 (사전 확보)
- MacroSentinel: NBER 3건 + Yardeni S&P 4건 데이터 확정, 음영 색상/투명도 합의(침체=회색 alpha 0.18 위 레이어, 약세장=붉은색 alpha 0.10 아래 레이어)
- ValueScreener: SMA20 cross + 1Y z-score 축 정의 합의, ±365일/±3 cap

### API 응답 shape 변경
- `GET /api/macro/yield-curve` 응답 `yield_curve` 필드에 `events: {recessions, bear_markets}` 추가
- `GET /api/macro/credit-spread` 응답 `credit_spread` 필드에 `events` + `partial_failure` 신규 토큰(`hy_oas_stale_used`, `ig_oas_stale_used`) 추가
- `GET /api/macro/sector-heatmap` 응답 `sectors[]`에 `trend_days: int` + `intensity_z: float` 추가
- `GET /api/admin/users` items / `GET /api/admin/users/{user_id}` 응답에 `visit_count: int` 추가

### 배포
- SSM `/stock-manager/prod/FRED_API_KEY` SecureString 등록 (Version 1, ap-northeast-2)
- GitHub Actions 자동 배포 → EC2 .env 자동 갱신 → 컨테이너 재기동 시 적용

### UI 후속 개선 (라벨 충돌 / HYG-LQD 폐기 / 섹터 3Y / 레이아웃)

#### 신규
- `frontend/src/components/macro/EventLabelsOverlay.jsx` — 시간 도메인 글로벌 row 계산 + ReferenceArea label 콜백 헬퍼. `computeEventRows(events, chartPxWidth=600)`: 라벨 픽셀 폭을 시간 폭으로 환산하여 같은 kind(rec/bear) 내 그리디 row 배정(rowEnds 트래킹). `makeLabelRenderer({kind, displayLabel, row, fill})`: viewBox 받아 row × 13px dy 적용된 SVG `<text>` 반환. 음영-라벨 분리하여 좁은 음영 위 긴 라벨이 인접 영역 침범하던 문제 원천 차단.

#### 수정
- `frontend/src/components/macro/YieldCurveSection.jsx` / `CreditSpreadSection.jsx` — 라벨 충돌 회피 로직을 EventLabelsOverlay로 이관. ReferenceArea 자체 `label` 콜백 패턴 사용(viewBox 100% 보장으로 글자 사라짐 없음). Customized 시도 폐기(일부 환경에서 chart internals props 미주입). 인접 라벨이 같은 픽셀 영역에 떨어지면 row × 13px 자동 적층.
- `frontend/src/components/macro/YieldCurveSection.jsx` — **3단 레이아웃** 도입: 1행 4금리 카드(grid-cols-4) → 2행 좌(SpreadCard: 10Y-3M 큰 숫자 + 역전 경고/정상 안내) | 우(수익률 곡선 반쪽) → 3행 10Y-3M 스프레드 추이 풀폭(차트 높이 h-56 → h-80). 60년 시계열 + 음영 라벨 가독성 개선.
- `frontend/src/components/macro/SectorRelativeChart.jsx` — 고정 도메인 [-365, 365] × [-3, 3] → 데이터 분포 기반 동적 도메인(`max(|값|) × 1.18`, 최소 ±30일/±0.5σ 보장). 4분면 음영 ReferenceArea도 동일 도메인으로 자동 확장. dot 크기 60→110으로 가시성 개선. 부제에 현재 스케일 표기.
- `stock/macro_fetcher.py` `fetch_credit_spread()` — **HYG/LQD ETF 수익률/비율 차트 폐기**(의미 약화). yfinance HYG/LQD 호출 블록 + `hyg_yield/lqd_yield/spread/spread_direction/history` 응답 필드 제거. 캐시 키 v4→v5. FRED 양쪽 실패 시 캐시 미저장 가드. 매크로 사이클 입력의 `credit_direction`은 `oas_momentum_6m` 부호 기반(>0.5 widening / <-0.5 narrowing / else stable)으로 대체.
- `stock/macro_fetcher.py` `fetch_sector_returns` / `fetch_sector_returns_kr` — **섹터 히트맵 3Y 항상 미표시 버그 수정**. yfinance `period="3y"`는 거래일 ~755개 반환 → `_calc_return(closes, 756)`은 `len ≥ 757` 요구로 항상 None 반환했음. `period="3y" → "5y"`로 확장(거래일 ~1260, 3Y/SMA20 둘 다 안전). 캐시 키 v3→v4.
- `services/macro_service.py` / `routers/macro.py` — `get_credit_spread()` docstring "HYG/LQD" 표기 제거.
- `frontend/src/components/macro/CreditSpreadSection.jsx` — ETF 수익률 3카드 + HYG/LQD 비율 추이 차트 + `DIRECTION_STYLE` 상수 + `spread_direction` 분기 모두 삭제.
- `main.py` — **방문수 카운트 항상 0이던 버그 수정**. BaseHTTPMiddleware는 새 task에서 라우터 호출 → 라우터의 ContextVar가 미들웨어로 propagate 안 돼 모든 PageView가 anonymous(NULL) 저장 → `count_by_user`가 anonymous 제외하므로 visit_count=0. `_extract_user_id_from_jwt(request)` 신규로 미들웨어 단계에서 Authorization Bearer JWT를 직접 `verify_token()` 파싱하여 user_id 추출.

#### 신규 테스트 (8 케이스 — 침체/약세장 시계열 확장 반영)
- `tests/unit/test_macro_events.py` — 6 → 8 케이스: 1962~2022 전 시계열 침체 6건/약세장 5건 포함 검증 + GFC → 서브프라임 라벨 변경

---

## 2026-05-04 — HY OAS 하워드 막스 시계추 전면 개편 (P0~P3)

### 배경
사용자 신고: "매크로 하이일드 스프레드가 제대로 동작하지 않는다." MacroSentinel 도메인 자문 결과:
- 임계값 3.5%/7%는 막스 원전 비정합 (3.5%는 역사적 5%ile에 해당해 거의 도달 불가)
- 5년 baseline은 코로나 이후 저금리 구간만 잡혀 분포 왜곡
- macro_regime에 신용 사이클 입력 누락 (주식 선행 지표인데 매트릭스에서 빠짐)
- 캐시 1시간은 FRED 일일 갱신 대비 과도

사용자 결정: P0~P3 풀스택 + 전 기간(1996-12 ~ 현재) baseline.

plan: `/Users/kimdukki/.claude/plans/shiny-herding-catmull.md`

### 백엔드 수정 (4)
- `stock/macro_fetcher.py` — `_fetch_fred_oas()` 5년 → **전 기간(1996-12-31~)** baseline. `_compute_oas_stats()` / `_classify_oas_sentiment()` / `_percentile_from_sorted()` 신규. 응답에 `oas_stats{p10,p25,p50,p75,p90,p95,max,max_date,mean,median,std}` / `oas_percentile` / `oas_zscore` / `oas_history_5y` 추가. **5단계 sentiment** (`extreme_greed/greed/normal/fear/extreme_fear`) — 백분위 + OAS>10% 절대 안전장치. `_fetch_fred_ig_oas()` 신규 (FRED `BAMLC0A0CM` Investment Grade OAS). `fetch_credit_spread()` 응답에 `ig_current` / `ig_history_5y` / `hy_ig_spread` / `hy_ig_spread_history_5y` / `partial_failure` 추가. 캐시 1h → **24h**. 후방호환 alias: `oas_history`(=5y), `percentile`(=oas_percentile).
- `services/macro_service.py` — `get_credit_spread()` MacroRepository 일일 영속 캐시(`get_macro_today/save_macro_today`). `get_macro_cycle()` credit_spread 입력 자동 주입(`oas_momentum_6m` → cycle / `hy_oas_percentile`+value → regime).
- `services/macro_regime.py` — `_step_fg_level()` 신규. `determine_regime(sentiment, previous_regime, hy_oas_percentile=None, hy_oas_value=None)` 시그니처 확장(Optional, 후방호환). **Phase 1 F&G 보정** (`credit_adjustment`): hy_oas p≥90 → F&G 한 단계 fear / p≤10 → 한 단계 greed. **Phase 2 신용 오버라이드** (`credit_override`): `OAS>10% OR p>95` → `extreme_fear+accumulation` 강제 (단 버핏 high/extreme이면 `selective` 완화). `p<5 + 버핏 high/extreme` → `defensive` 강제. VIX>35 우선순위 보존.
- `services/macro_cycle.py` — **Phase 3** `_score_credit()`에 `oas_momentum_6m` 가중(+0.3) 입력 추가. 16셀 cycle×regime 매트릭스 미터치(입력만 정밀화).

### 프론트엔드 수정 (1)
- `frontend/src/components/macro/CreditSpreadSection.jsx` — `SENTIMENT_CONFIG` 5단계 확장(extreme_greed/greed/normal/fear/extreme_fear). 메인 게이지 0~12% 선형 → **백분위 축(0~100)** + 절댓값 부제(역사 평균/p95/정점·날짜) 병기. ReferenceLine을 백분위 임계(p10/p25/p75/p90)에 매핑된 **동적 OAS 값**으로 표시. **IG OAS / HY-IG 스프레드 보조 카드** 추가(>5%p이면 "정크 영역 패닉" 강조). `data.credit_spread || data` 모호 fallback 제거 → `data?.credit_spread` 명시. `partial_failure` 안내 배너.

### 신규 테스트 (5)
- `tests/unit/test_macro_fetcher_oas.py` — 11 케이스 (5단계 경계, OAS>10% 안전장치, stats 정확성, 빈 응답/ZeroDivision 가드)
- `tests/unit/test_macro_regime_credit_integration.py` — 7 케이스 (F&G 보정, 신용 오버라이드 4종, dual extreme selective)
- `tests/unit/test_safety_grade_credit_propagation.py` — 1 케이스 (16셀 cycle 매트릭스 자동 정합)
- `tests/unit/test_macro_cycle_oas_momentum.py` — 6 케이스 (oas_momentum_6m cycle 입력 반영)
- `tests/integration/test_credit_spread_api.py` — 3 케이스 (응답 shape + 일일 캐시 동작)
- 결과: **495 PASS / 0 FAIL / 6 skip** (기존 478 → +17 신규).

### 도메인 자문 합의
- **MacroSentinel**: ✅ 백분위 5단계 + 전 기간 baseline + OAS>10% 안전장치 + IG OAS 보조 + 체제 통합 3 Phase 권고대로 반영.
- **MarginAnalyst**: ✅ `safety_grade.compute_grade_7point`은 macro_regime/cycle 독립. cycle 입력 변경 시 `get_margin_requirement(regime, cycle_phase)`의 16셀 매트릭스에서 자동 보정 — 회귀 테스트로 검증.
- **OrderAdvisor**: ✅ `extreme_fear+accumulation` 강제 시 `REGIME_PARAMS["accumulation"]`(margin=20, single_cap=5%, cash_min=25%) 적용. dual extreme(OAS>10% + 버핏 high)은 `selective`로 완화하여 4% 한도 유지. 적정.

### API 응답 shape 변경 (`GET /api/macro/credit-spread`)
- 신규: `oas_stats` / `oas_percentile` / `oas_zscore` / `oas_history_5y` / `ig_current` / `ig_history_5y` / `hy_ig_spread` / `hy_ig_spread_history_5y` / `partial_failure`
- 변경: `oas_sentiment` 3단계 → 5단계
- 호환: `oas_history`(=oas_history_5y), `percentile`(=oas_percentile) alias 유지

---

## 2026-05-04 — Phase 4: 관리 영역 확장 + 사용자별 KIS 자격증명

### 배경
멀티유저 운영을 위한 4건 일괄 처리 (옵션 B 권장 default). plan: `/Users/kimdukki/.claude/plans/shiny-herding-catmull.md`.
1. AI관리 user_id 입력 점검 → UI 정상, 사용자 목록 API 부재가 진짜 원인
2. 사용자관리 페이지 신설 (관리자 CRUD)
3. 페이지별 이용현황 통계 페이지 신설
4. 사용자별 KIS 자격증명 (AES-GCM) → 잔고/매매/양도세/포트폴리오 메뉴 활성화

### 신규 모듈 (백엔드 10)
- `services/secure_store.py` — AES-GCM 암호화. `encrypt/decrypt`. 32-byte 마스터 키 `KIS_ENCRYPTION_KEY`(SSM SecureString). nonce 12B + tag 16B. 키 미설정 시 ConfigError(503).
- `services/kis_validator.py` — `validate_kis()` KIS `/oauth2/tokenP` 호출로 즉시 검증.
- `db/models/user_kis.py` — `UserKisCredentials` 분리 테이블 (`user_id PK FK, app_key_enc, app_secret_enc, base_url, acnt_no_enc, acnt_prdt_cd_stk/fno?, hts_id?, validated_at?`).
- `db/models/page_view.py` — `PageView(id, user_id?, path, method, status_code, duration_ms, created_at)`.
- `db/repositories/user_kis_repo.py` — get/upsert/delete/mark_validated/is_valid(TTL 24h).
- `db/repositories/page_view_repo.py` — record/aggregate_by_path/top_paths/daily_count.
- `routers/me_kis.py` — POST/GET/DELETE `/api/me/kis` + `POST /api/me/kis/validate`. GET 응답은 마스킹(끝 4자리만).
- `routers/admin_users.py` — GET 목록/상세, PATCH role·password reset, DELETE. 모두 `require_admin` + audit_log 기록.
- `routers/admin_stats.py` — `GET /api/admin/page-stats?from=&to=&top=` 경로별 호출+latency+시계열.
- alembic 3건: `add_user_kis_credentials`, `add_page_view`, `add_user_id_to_orders_reservations_tax` (모두 up/down).

### 수정 (백엔드 13)
- `routers/_kis_auth.py` — `_token_cache: dict[int|None, (token, expires_at)]`. `get_kis_credentials(user_id=None)`/`get_access_token(user_id=None)`. user_id=None은 시스템(시세 등) 운영자 .env fallback. 사용자 라우터에서 user_id 무조건 전파.
- `routers/auth.py` — `/api/auth/me` 응답에 `has_kis: bool` 추가.
- `routers/balance.py`, `routers/order.py`, `routers/tax.py`, `routers/portfolio_advisor.py` — `Depends(get_current_user)` + user_id 전파.
- `services/order_service.py`, `services/tax_service.py` — 시그니처에 user_id 추가.
- `services/auth_deps.py` — `require_kis` 의존성 추가.
- `db/repositories/order_repo.py`, `tax_repo.py` — user_id 필터.
- `db/repositories/user_repo.py` — `list_users(q, limit, offset)`, `count_users(q)`, `update_role`, `reset_password` 추가.
- `main.py` — page_view 미들웨어(`asyncio.create_task` 비동기 INSERT, 제외 path: /api/health, /assets/*, /static/*, /ws/*, /api/admin/page-stats).
- `config.py` — `KIS_ENCRYPTION_KEY`, `KIS_VALIDATION_TTL_HOURS=24`.
- `requirements.txt` — `cryptography>=42`.
- `db/models/__init__.py`, `db/models/order.py`, `db/models/tax.py` — user_id 컬럼.

### 신규 (프론트 7)
- `pages/AdminAIPage.jsx` — 기존 AdminPage 3탭 이전(route `/admin/ai`).
- `pages/AdminUsersPage.jsx` — 사용자 검색/CRUD(route `/admin/users`).
- `pages/AdminPageStatsPage.jsx` — Recharts 차트, 기간 필터(route `/admin/page-stats`).
- `pages/SettingsKisPage.jsx` — KIS 등록 폼 + 검증 결과 표시(route `/settings/kis`).
- `components/KisRequiredNotice.jsx` — 미등록 안내 + 등록 버튼.
- `components/admin/*` — 사용자 콤보박스 등 보조 컴포넌트.
- `api/me.js` — `getMyKis/saveMyKis/deleteMyKis/validateMyKis`.

### 수정 (프론트 6)
- `pages/AdminPage.jsx` — `/admin` → `/admin/ai` redirect 진입점.
- `components/layout/Header.jsx` — "AI관리" → "관리" 드롭다운(3개 하위). 자산관리 그룹 메뉴 항목별 `requireKis: true` + 회색+🔒 + 클릭 시 `/settings/kis`.
- `components/common/ProtectedRoute.jsx` — `requireKis` prop. 미등록 시 `KisRequiredNotice` 렌더.
- `hooks/useAuth.jsx` — `hasKis` 추가 (`user?.has_kis`).
- `App.jsx` — 신규 라우트 + `/portfolio·/order/*·/balance·/tax/*`에 requireKis.
- `api/admin.js` — `fetchUsers/fetchUserById/patchUser/deleteUser`.

### 환경변수 추가
- `KIS_ENCRYPTION_KEY` — AES-GCM 마스터 키(b64 32-byte). **사용자별 KIS 사용 시 필수**. SSM `/stock-manager/prod/KIS_ENCRYPTION_KEY`(SecureString). 키 분실 시 모든 사용자 KIS 자격증명 영구 복구 불가.
- `KIS_VALIDATION_TTL_HOURS` — 검증 만료 TTL. 기본 `24` (시간).

### 신규 API (9개)
- `POST /api/me/kis` — 등록 + 즉시 검증
- `GET /api/me/kis` — 마스킹된 상태(끝 4자리)
- `DELETE /api/me/kis` — 삭제 + 토큰 캐시 invalidate
- `POST /api/me/kis/validate` — 재검증
- `GET /api/admin/users?q=&limit=&offset=` — 검색/페이지네이션
- `GET /api/admin/users/{user_id}` — 상세
- `PATCH /api/admin/users/{user_id}` — role/password 변경
- `DELETE /api/admin/users/{user_id}` — 삭제
- `GET /api/admin/page-stats?from=&to=&top=` — 통계

### 도메인 영향
**0건**. 체제/Graham/등급/Value Trap/주문 안전 규칙/portfolio_advisor 자문 로직 모두 미터치. 시세(quote_kis/quote_overseas/market_board) 운영자 키 통합 유지(rate limit 회피).

### 보안
- KIS_APP_SECRET 평문 저장 0건 — AES-GCM nonce 12B + tag 16B
- 응답 마스킹: `app_key`는 끝 4자리만, `app_secret`/`acnt_no`는 미노출
- 마스터 키 미설정 시 ConfigError(503) fail-fast
- 마스터 키 분실 → 영구 복구 불가 (별도 안전 백업 필수)

### 테스트
- 신규 단위 14 PASS: `tests/unit/test_secure_store.py` (9) + `tests/unit/test_kis_validator.py` (5)
- 신규 통합/API 24: `tests/integration/test_user_kis_repo.py`, `test_page_view_repo.py`, `tests/api/test_admin_users_api.py`, `test_me_kis_api.py`, `test_admin_page_stats_api.py` (PostgreSQL 의존, CI 검증 위탁)
- 회귀: 기존 단위 453 PASS 유지

### 마이그레이션 영향
신규 alembic 3건. 기존 운영 데이터:
- `orders.user_id` NULL 허용 — 기존 row는 NULL 유지(자동 매핑 안 함, 데이터 정합성 보호)
- `tax_transactions.user_id` 동일

### 멀티 인스턴스 영향 (현재 단일 EC2라 영향 0)
in-memory 토큰 캐시는 노드별 격리. 확장 시 F-4 메모(perf_audit_report.md 섹션 10.4) 참조 — Redis 전환 필요.

---

## 2026-05-03 — 성능/가용성 4단계 사이클 (Phase 1~3 + 부수 정리)

워치리스트/AI 자문 로딩 속도 이슈 분석 → 4 phase 점진 개선. RefactorEngineer + QA Inspector 합동 감사 산출물(`_workspace/dev/perf_audit_report.md` 1132줄, 5축 + AWS 인프라 5축) 기반.

### Phase 1 — 인프라 P0 (nginx 보안 헤더 drift + proxy_read_timeout)
- `infra/nginx/app.conf`: location 1→3 분리. `^~ /ws/` 3600s + `/api/` 90s + `/` 60s. 공통 프록시 헤더 server 블록 상위 이동.
- `.github/workflows/deploy.yml`: heredoc 70줄 제거 → SCP staging(`/opt/stock-manager/_staging`) + `nginx -t` 자동 검증 + `nginx -s reload` 명시 호출.
- `scripts/ec2-deploy.sh`: 비상용 명시(운영은 GitHub Actions 단일 경로).
- 핫픽스 2건: `--add-host=app:127.0.0.1`(검증 컨테이너 dummy DNS), `nginx -s reload`(volume mount 설정 반영).

### Phase 2 — Week 1 Quick Win 5건 (워치리스트/macro 성능)
- **QW-1 stock_info N+1 제거**: `db/repositories/stock_info_repo.py`에 `is_stale_from_dict()` 순수 함수 추출. `services/watchlist_service.py:_fetch_dashboard_row`가 dict 기반 fresh 판정으로 단축. 26종목 SELECT 104→26 (-75%).
- **QW-2 macro 7심볼 병렬**: `stock/yf_client.py:fetch_macro_indicators`가 `^TNX/GC=F/CL=F/USDKRW=X/...` 7심볼을 `ThreadPoolExecutor(max_workers=7)`로 병렬 조회. 첫 채움 7~14초 → 1~2초.
- **QW-3 partial_failure + logger.warning**: 워치리스트 try/except 6개 `debug→warning` 승격. row dict에 `partial_failure: list[str]` 메타필드. `frontend/src/components/watchlist/WatchlistDashboard.jsx`에 ⚠ 미수집 tooltip UI.
- **QW-4 워치리스트 dashboard 응답 캐시**: `services/_dashboard_cache.py` 신설. 사용자별 60s in-memory TTL(부분 실패 15s). `add/remove_item / update_memo` 핸들러에서 invalidate. 멀티 인스턴스 확장 시 Redis 재설계 필요(F-4-A 코드 주석).
- **INF-3 nginx gzip + 정적 캐시**: `infra/nginx/app.conf`에 gzip 8 MIME + `/assets/*` `Cache-Control: public, max-age=31536000, immutable`. 운영 검증 결과 `/assets/*.js` 1.4MB→386KB(-72.5%).

### Phase 2b — 부수 메모 정리 (보안 헤더 SSoT + SPA HEAD)
- `main.py`: `add_security_headers` 미들웨어 제거. nginx(`infra/nginx/app.conf`)를 single source of truth로 채택. 응답 헤더 중복 노출 해소(backend 5종 + nginx 6종 → nginx 단일 6종).
- `main.py`: SPA catchall `@app.get("/{full_path:path}")` → `@app.api_route("/{full_path:path}", methods=["GET","HEAD"])`. uptime 모니터/`curl -I`에서 405→200.
- `.github/workflows/deploy.yml`: 사전 `docker image prune -af` + `docker builder prune -af` 추가(EBS 가득 참으로 인한 image pull 실패 회피).

### Phase 3 — 계측(Telemetry) 도입
- `services/_telemetry.py` 신규(외부 의존성 0, stdlib only): `@timed(name)` 데코레이터, `record_event(name)` 카운터, `observe(name, value)` percentile(p50/p95/p99 deque), `start_periodic_flush(interval_sec)`.
- 7개 hot path 계측: T-1 `watchlist.dashboard` 응답+캐시 hit/miss, T-2 `_fetch_dashboard_row` per-stock+영역별 fresh 비율, T-3 `stock_info.get_stock_info`/`is_stale` 호출 횟수, T-4 `ai_gateway.call_openai_chat` latency+per-model token, T-5 `advisory` 4페이즈 timing, T-6 `yf_client._ticker` hit/miss, T-7 `analyst_pdf` 캐시 hit/miss + 다운로드 latency.
- `main.py` lifespan에서 5분 주기 stdout dump 후 reset. 메모리 < 300KB 상한.
- `TELEMETRY_ENABLED=0/1`, `TELEMETRY_FLUSH_SEC=300` 환경변수 제어.
- 1주 누적 측정 후 의사결정 트리거: 워치리스트 캐시 hit ≥ 90% → max_workers 4→8 복원, advisory refresh p95 > 30s → Phase 4 Mid 사이클 P0, yfinance 단일 종목 5+회 → RefreshContext 우선순위 P0.

### 도메인 영향
- 도메인 로직(체제 판단/Graham/등급 임계값) 변경 0건. 본 PR은 캐싱/중복제거/병렬화/계층 재배치/계측만 다룸.
- 후방 호환 100%: `is_stale(code, market, field)` 등 모든 기존 시그니처 보존.

### 테스트
- 단위 신규 5: `tests/unit/test_stock_info_freshness.py`, `test_macro_indicators_parallel.py`, `test_watchlist_partial_failure.py`, `test_dashboard_cache.py`, `test_telemetry.py`.
- API 신규 1: `tests/api/test_main_misc.py` (SPA GET 회귀 / SPA HEAD 200 / 루트 HEAD / 보안 헤더 부재).
- 단위 **453 PASS / 0 FAIL / 6 SKIP**(skip은 로컬 Python 3.9 의존성, CI 3.11 정상). 신규 30+ 케이스 모두 통과.

### 환경변수 추가
- `TELEMETRY_ENABLED` (기본 `1`): 계측 활성/비활성
- `TELEMETRY_FLUSH_SEC` (기본 `300`): 카운터 flush 간격

### 운영 측정 효과 (이론치)
| 영역 | Before | After |
|------|--------|-------|
| 워치리스트 26종목 SELECT | 104회 | 26회 (-75%) |
| F5 연타 응답 | 풀 작업 반복 | 즉시 (<50ms) |
| macro 7심볼 첫 채움 | 7~14초 | 1~2초 |
| `/assets/*.js` 전송 | 1.4MB | 386KB (-72.5%) |
| nginx HTTP timeout | 24시간 | 90s (957× 단축) |
| 보안 헤더 drift | 매 배포 누락 | 6종 안정 적용 (SSoT) |
| SPA HEAD 응답 | 405 | 200 |

---

## 2026-05-02 — AI 자문 보수성 완화 + 경기사이클×체제 조합 + 성장주 보조 트랙

### 신규 모듈
- `services/growth_grade.py` — 성장주 보조 등급(G-A/G-B/G-C). 5지표(매출CAGR/영업CAGR/FCF/R&D/사이클정합) 각 4점 → 20점. `combine_grades(value, growth)` 함수가 6종 라벨 + factor 반환 (가치D+성장A → factor 0.30 분할매수, 손절 -20%)

### 프롬프트 개선
- `services/advisory_service.py`: `_get_cycle_context()` 신규로 macro_cycle 통합. `_CYCLE_REGIME_RULES` 16셀(체제×사이클) 매트릭스 + `_format_cycle_regime_rule()` 신규. `_build_system_prompt()` 시그니처에 `cycle_ctx` 추가. **defensive "어떤 경우에도 매수 금지" 폐기** → "사이클 회복/확장 시 단계적 매수 허용"
- `_build_consensus_section()` defensive 가드 폐지 → 50% 감산 경고로 완화 (cautious와 동일)
- Graham 임계 cycle 보정: 회복/확장 15% / 과열 25% / 수축 10% (기존 30% 일괄)
- 사전 계산에 `growth_grade.compute_growth_grade()` 결과 병기 (가치 D + 성장 G-A 라벨 표시)
- JSON 응답 스키마에 `성장주_보조판단` 필드 추가
- `services/portfolio_advisor_service.py`: 톤 균형화 — "현금 확보를 위한 매도 우선 검토" → "조합 권고에 따라 비중 조정", "가중 평균<B면 신규 편입 전면 보류" → "사이클 주도 섹터 + 가치 B 이상 또는 성장 G-A 한정 허용", 손실 -15% "손절 우선" → "손절/평균단가 분할매수/홀딩 3안 균형 제시". `_format_cycle_context`에 사이클×체제 액션 매트릭스 가이드 1줄 추가

### 도메인 규칙
- `services/macro_regime.py`: `get_regime_params(regime, cycle_phase)` + `get_margin_requirement(regime, cycle_phase)` 신규 — 16셀 매트릭스 동적 single_cap/margin. defensive+회복=7%·35%, +확장=5%·40%, +과열=2%·40%, +수축=0%·40%. 기존 `REGIME_PARAMS` dict는 fallback 호환
- `services/safety_grade.py`: `GRADE_FACTOR["C"]=0 → 0.25` (C 등급 부분 진입 허용), `GRADE_STOP_LOSS_PCT["C"]=-15%` 신규, `valid_entry`에 C 포함. D는 0 유지(가치). 7지표 임계값 변경 없음

### 스키마
- `services/schemas/advisory_report_v3.py`: `GrowthAuxiliary` Pydantic 모델 신규(growth_grade/growth_score/growth_thesis/cycle_alignment/combined_label, 모두 Optional, backward-compat)

### 테스트
- 신규 5: `tests/unit/test_growth_grade.py`(11) / `test_macro_regime_cycle.py`(25) / `test_advisory_prompt_cycle.py`(6 환경 의존 skip) / `tests/integration/test_advisory_growth_track.py`(5) / `test_portfolio_advisor_tone.py`(7 환경 의존 skip)
- 수정 1: `tests/unit/test_safety_grade.py` C 등급 정책 변경 반영(grade_factor/position_size/stop_loss 3건)
- **414 PASS / 0 FAIL / 6 SKIP** (skip은 로컬 Python 3.9의 stock/* import 실패만, CI 3.11에서 정상)

### 도메인 자문 합의안 (4명)
- MacroSentinel: cycle×regime 16셀 single_cap 매트릭스
- MarginAnalyst: Graham 임계 cycle 보정 15%/25%/10%
- OrderAdvisor: 분할 진입 30→30→40, D+A 우회 진입 시 1차 25%만+손절 -20%
- ValueScreener: 성장 5지표 임계값 G-A=16-20, G-B=12-15, G-C<12

## 2026-05-02 — 워치리스트 t3.small OOM 핫픽스

### 버그 수정
- `services/watchlist_service.py:226`: `ThreadPoolExecutor(max_workers=min(10, len(items)))` → `min(4, len(items))` — 워치리스트 26종목 × 3종 외부 API(price/metrics/financials) 호출이 10병렬로 진행되어 t3.small(1.9GB)에서 메모리 폭증 + swap thrashing → 모든 API hang(`/api/watchlist/dashboard nginx 499 timeout`). 동시성 축소로 OOM 방지

## 2026-05-02 — 워치리스트 안정화 추가 개선 4종

### 인프라
- `entrypoint.sh`: 컨테이너 시작 시 `cache.db` 무조건 초기화 → `CACHE_PURGE_ON_START=1` 환경변수일 때만 초기화. 기본 보존으로 t3.small cold cache 첫 진입 폭주 방지
- `entrypoint.sh`: uvicorn 실행에 `--limit-concurrency 20 --timeout-keep-alive 5` 추가. `UVICORN_CONCURRENCY`/`UVICORN_KEEPALIVE` 환경변수로 조정 가능. worker가 동시 21번째 요청은 즉시 503 반환하여 전체 hang 방지
- `db/repositories/stock_info_repo.py`: TTL 연장 — price off 6h→12h, metrics trading 2h→6h·off 12h→24h, returns off 6h→12h. 외부 API 호출 빈도 감소로 메모리/네트워크 부하 완화
- `infra/modules/compute/user_data.sh`: Swap 2GB→4GB 확장 + `vm.swappiness=10` 추가. 메모리 압박 시 swap thrashing 빈도 감소(다음 EC2 재생성 시 적용, 기존 인스턴스는 수동 적용 필요)

## 2026-05-01 — AI 입력 데이터 패널 통합 + 증권사 컨센서스 노출

### UI 개선
- `frontend/src/components/advisory/ResearchDataPanel.jsx` 전면 리팩토링 — 기본/리서치 2섹션 구분 제거, **16개 카테고리 단일 목록**으로 통합
- 신규 카테고리 **증권사 컨센서스(`analyst_consensus`)** 표시:
  - 통계 6종(목표가 중앙값/평균/std/dispersion/상승여력 중앙값/컨센수)
  - 의견 분포(매수/보유/매도) + 강력매수/강력매도 보조 표시
  - 모멘텀 5단계 배지(strong_up/up/flat/down/strong_down) + 과열 경고
  - 6개월 목표가 추이 + 최근 5건 리포트 카드(증권사·날짜·의견·TP·요약·PDF 링크)
- 계량지표 카드 보강: ROA / 주당배당금 / 시가총액 신규 표시
- 거시 경제 카테고리에 52주 가격 위치 통합 (52주 고가/저가/위치%/고점 대비%)

## 2026-05-01 — AI자문 프롬프트 누락 데이터 보강 + 미래지향/역발상 강화

### 프롬프트 개선
- 누락 데이터 6종을 `_build_prompt()`에 신규 섹션으로 추가:
  - `## 사업 개요`: `business_description` + `business_keywords` + `segments` 매출 비중 (역발상·미래지향 분석의 출발점)
  - `## 가격 위치`: 52주 고가/저가 대비 현재가 위치 (%)
  - `## 자본행위 분류`: 1년 공시에서 유증/CB/BW/감자/자사주매입·소각/배당/M&A 자동 분류
  - `## 장기(10년) 밸류에이션 사이클`: `valuation_history`로 PER/PBR 10년 범위·평균
  - `## 경쟁사 비교`: `peers` PER/PBR/시총 표
  - `## 계량지표`에 **배당수익률·주당배당금** 추가 (KR 골프존 등 배당 종목 미인지 버그 수정)
- 시스템 프롬프트 미래지향/역발상 강화 (`_build_system_prompt`):
  - "결정은 과거가 아닌 미래에 베팅" 원칙 명시
  - 역발상 4대 시그널 가이드 (과매도+펀더멘털 강건 / 사이클 턴어라운드 / 컨센서스 합의도 반박 / 자사주·내부자 매수)
  - catalyst 8종 식별 의무 (3개 이상 권장: 신규시장/제품/규제/M&A/자사주/배당정책/구조조정/사이클회복)
  - peak-out 선행지표 검증 지침
  - 6대 → **8대 분석 항목** 확장 (미래성장동력, 역발상관점 추가)

### JSON 스키마 확장
- `미래성장동력`: catalysts / turning_points / industry_tailwinds / peak_out_signals / growth_horizon / confidence
- `역발상관점`: contrarian_thesis / market_misperception / edge / rebut_consensus / asymmetric_payoff
- `services/schemas/advisory_report_v3.py`: `FutureGrowthDrivers`, `ContrarianView` Pydantic 모델 신규. 모두 Optional → 기존 응답 backward-compat

### 버그 수정
- `stock/yf_client.py:fetch_metrics_yf()`: `dividend_yield`/`dividend_per_share` 3단계 fallback 추가 (US 종목 배당 누락 보완)
- `services/advisory_service.py:_build_metrics_kr()`: `dividend_yield`/`dividend_per_share` pass-through 추가 (KR 종목 배당 누락 수정)
- `stock/research_collector.py:_compute_momentum()`: 컨센서스 과열 임계값 0.30 → 0.20 (strong_up 경계와 정합, CI 테스트 통과)

---

## 2026-05-01 — 애널리스트 보고서 본문 → 종목 AI 자문 통합

### 애널리스트 컨센서스 신규
- `stock/analyst_pdf.py`: 증권사 PDF 본문 추출+요약 신규. `pdfplumber` 첫 5페이지 → `gpt-5.4` JSON 응답으로 6항목 강제 추출(catalyst 2 / risk 2 / TP 산정 근거 1 / EPS 추정 변경 1) → 300자 결합 텍스트
- 환각 방지: 시스템 프롬프트에 "본문에 명시된 숫자만 인용. 추정·외삽·외부 지식 금지" 명시
- PDF 다운로드 보안: 10MB 한도, Content-Type 검증, 모든 예외 흡수, 짧은 본문(100자 미만) 시 요약 생략
- 영구 캐시: `cache.db`에 `analyst:summary:{md5(pdf_url)}` 키. 동일 PDF 재요청 시 OpenAI 호출 0회
- `services/ai_gateway`: `service_name="analyst_summary"`, `user_id=None`(시스템 호출, 유저 일일 쿼터 미차감, `ai_usage_log`엔 기록)

### research_collector 6번째 카테고리
- `stock/research_collector.py`: `analyst_consensus` 카테고리 추가 (5→6 카테고리). `ThreadPoolExecutor` 병렬 슬롯에 합류
- KR/US 의견 매핑 31개 (`Strong Buy`/`강력매수`/`Buy`/`매수`/`Outperform`/`Overweight`/`Hold`/`Neutral`/`보유`/`Sector Perform`/`Sell`/`Underperform`/`매도`/`Strong Sell`/`강력매도` 등) → 5단계 정규화 → 3단계 재집계
- 컨센서스 통계: 중앙값(평균 대비 극단치 강건) + 평균 + 표준편차 + dispersion(stdev/median) + upside_pct_median. `target_price=None` 행은 분모 제외, count는 전체
- 시간축 추이: 동일 broker 6개월 변화율 평균 → 5단계 라벨(`strong_up`/`up`/`flat`/`down`/`strong_down`). 30%+ 동시 상향 broker 50% 초과 → `consensus_overheated=True`
- 영속: `AnalystRepository.upsert_report` 호출로 `analyst_reports` 테이블에 저장 → `get_target_price_history(180일)` 조회

### 신규 DB 테이블
- `db/models/analyst.py` `AnalystReport`: `id, code, market, broker, target_price(BigInteger), opinion, title, pdf_url, summary(Text), published_at, fetched_at`. 유니크 `(code, market, broker, published_at, title)` + 인덱스 `(code, market, published_at)`
- `db/repositories/analyst_repo.py` `AnalystRepository`: `upsert_report` (UPSERT — 동일 키 시 summary/target_price/opinion/fetched_at만 갱신) / `list_reports(since=, limit=)` / `get_target_price_history(days=180)`. 미래 날짜·`YY.MM.DD` 형식 자동 보정
- `alembic/versions/b3d4e5f6a7c8_add_analyst_reports_table.py`: 단일 head 유지 (parent: `9cda1c3787e5`)

### advisory_service 12번 섹션
- `services/advisory_service.py`: `_build_consensus_section()` 헬퍼 추가 + `_build_prompt()` 끝에 합류
- 체제별 차등 표시: defensive → 빈 문자열(섹션 자체 미표시) / cautious → 정상 표시 + "50% 가중 감산" 경고 라인 / accumulation·selective → 정상
- KR 출력: 중앙 목표가 + 현재가 대비 upside% + 표준편차 + dispersion + 매수/보유/매도 분포 + momentum_signal + 과열 시 경고 + 최근 3건(증권사·날짜·의견·TP·요약 100자) + 6개월 추이
- US 출력: 등급 변경 이력 형식 (Goldman: Buy → Sell 등)
- 시스템 프롬프트 강화: "증권사 컨센서스를 무비판적으로 수용하지 말 것 — 합의도(dispersion)/과열(consensus_overheated)/체제 신뢰도를 종합 판단"
- Value Trap 5규칙 → 6규칙: 6) 증권사 컨센서스 과열(consensus_overheated=True 시 가산 1점)
- 사전 계산값(grade/score/진입가/손절가) 불변 — 컨센서스는 GPT reasoning input일 뿐 (`compute_grade_7point`/`compute_position_size` 시그니처 변경 없음)

### 테스트
- `tests/unit/test_analyst_imports.py` (17 LOC), `test_analyst_pdf.py` (299 LOC)
- `tests/integration/test_analyst_repo.py` (173 LOC), `test_research_collector_analyst.py` (343 LOC), `test_advisory_prompt_analyst.py` (317 LOC)
- 부서장 직접 검증: 의견 정규화 / 컨센서스 산출 / momentum 계산 / `_build_consensus_section` 6/6 시나리오 / SQLite 마이그레이션 + Repository CRUD 모두 PASS

### 의존성
- `requirements.txt`: `pdfplumber>=0.11` 추가

## 2026-04-30 — 스크리너 안정화 + 관심종목 UX + 섹터히트맵 3Y + Advisory 버그수정 + PER/DART 개선

### 버그 수정
- `screener/krx.py`: KRX 종목 목록 빈 응답 시 `force_relogin()` 후 1회 재시도 (세션 만료 자동 복구)
- `screener/krx_auth.py`: `force_relogin()` 함수 추가 — 세션 강제 만료 + 재로그인
- `services/advisory_service.py`: 기본적 분석 새로고침 HTTP 500 수정 — `_collect_fundamental_kr()`에 `user_id` 파라미터 미전달 `NameError` 해결
- `stock/dart_fin.py`: DART 재무 연도 클릭 시 잘못된 보고서 열리는 버그 수정 — 3년 배치 호출(rcept_no 공유)에서 연도별 API 호출(고유 rcept_no)로 변경
- `stock/market.py`: PER 산출 개선 — `forwardPE` 제거(한국 주식 비정상 값) + fallback을 `income_stmt` 연간 순이익 기반으로 변경 + `trailingPE` 존재 시 덮어쓰기 방지

### 증권사 목표가 팝업 신규
- `stock/naver_research.py`: 네이버 증권 리서치 스크래핑 — 증권사별 최신 목표가+투자의견+리포트 제목+PDF 링크. ThreadPoolExecutor 병렬 수집. 캐시 6시간
- `stock/yf_client.py`: `fetch_upgrades_downgrades()` 추가 — 해외 종목 증권사 등급 변경 이력 (yfinance)
- `routers/advisory.py`: `GET /{code}/analyst-reports` 엔드포인트 추가 (KR=네이버/US=yfinance)
- `AnalystReportsModal.jsx`: 목표주가 클릭 시 증권사별 목표가 팝업 (KR: 증권사+목표가+의견+리포트+PDF / US: 등급이력)
- `FundamentalPanel.jsx`: 목표주가 값을 클릭 가능한 링크로 변경 → 모달 연결

### 하이일드 스프레드 하워드 막스 프레임워크
- `stock/macro_fetcher.py`: FRED HY OAS(BAMLH0A0HYM2) 5년 시계열 무료 CSV 수집. 하워드 막스 시계추: OAS<3.5%=탐욕(수비), 3.5~7%=정상, >7%=공포(공격)
- `CreditSpreadSection.jsx`: 시계추 카드(해석+전략) + 게이지 바(3구간) + OAS 5년 차트(3.5%/7% 기준선) + 기존 HYG/LQD 차트 유지

### 코드 품질 개선
- `DetailPage.jsx`: `useState(false)` → `useRef(false)` 버그 수정 (`advLoadedRef`)
- `OrderPage.jsx`: setTimeout ref 관리 + 언마운트 시 clearTimeout (메모리 누수 방지)
- `stock/cache.py`: 4곳 `except: pass` → `logger.warning()` 추가 (디버깅 가능)
- `services/order_fno.py`: 3곳 hashkey 발급 실패 시 `logger.warning()` 추가

### UI 개선
- `SectorConceptTabs.jsx`: 데일리 추천 페이지에서 관심종목 기등록 종목 `★ 관심종목` 표시 (watchlist 로드 + `alreadyAdded` prop)
- `WatchlistButton.jsx`: 추가 완료 후 `✓ 추가됨` → `★ 관심종목`으로 통일
- `Header.jsx` + `ReportPage.jsx`: 메뉴명 "보고서" → "데일리 추천", 페이지 제목도 동일 변경
- `SectorHeatmapSection.jsx`: "현재가" 컬럼 제거 + "3Y" 컬럼 추가 (5기간: 1M/3M/6M/1Y/3Y)
- `stock/macro_fetcher.py`: 섹터 ETF 조회 기간 `1y` → `3y` 확장, `return_3y`(756거래일) 추가, `price` 필드 제거

---

## 2026-04-29 — AI 게이트웨이 + 섹터 추천 개선 + PER 수정 + 보고서 접근 수정

### AI 게이트웨이 + 사용량 관리 신규
- `services/ai_gateway.py`: 모든 OpenAI API 호출의 단일 진입점 (`call_openai_chat()`). 유저별 일일 쿼터 체크 + 사용량 기록. `AiQuotaExceededError`(429)
- 기존 6개 서비스의 OpenAI 직접 호출을 게이트웨이로 전환 (advisory_service, sector_recommendation_service, portfolio_advisor_service, macro_service×2, advisory_fetcher)
- `db/models/admin.py`: 3개 테이블 (ai_usage_log, ai_limits, audit_log)
- `db/repositories/admin_repo.py`: 사용량/한도/감사로그 CRUD
- `routers/admin.py`: Admin API 6개 엔드포인트 (사용량 조회, 한도 설정, 감사 로그)
- `AdminPage.jsx`: Admin 관리 페이지 3탭 (사용량/한도/감사로그)

### 섹터 추천 데이터 기반 개선
- `stock/macro_fetcher.py`: 한국 섹터 ETF 13종 수익률 수집 (`fetch_sector_returns_kr()`) — KODEX 반도체/2차전지/건설/바이오 등
- `services/sector_recommendation_service.py`: GPT 프롬프트에 실제 섹터 ETF 수익률 테이블 전달. defensive 하드코딩 규칙 제거 → 실제 가격 추세 기반 모멘텀/역발상 분류
- `services/pipeline_service.py`: 파이프라인에서 시장별 섹터 수익률 수집 후 전달

### 버그 수정
- `stock/market.py`: PER fallback — yfinance forwardPE 부정확(골프존 4.61→12.06) → 시총/TTM순이익 직접 계산 (PBR/ROE fallback과 동일 패턴)
- `ReportPage.jsx`: 비admin 유저 접근 시 "보고서 생성 실패" 에러 → fetchReportByDate로 기존 보고서 조회. 보고서 없을 때 안내 메시지 분기

---

## 2026-04-29 — DART 계정명 정규식 전환 + 밸류에이션 차트 이동 + UI 개선

### 리팩토링
- `dart_fin.py`: DART 계정명 매칭 전면 정규식 전환 — `_ACCOUNT_KEYS`/`_BS_KEYS`/`_IS_DETAIL_KEYS` tuple → `_ACCOUNT_REGEX`/`_BS_REGEX`/`_IS_DETAIL_REGEX` re.Pattern
- `dart_fin.py`: 공용 `_match_account()` 함수 (공백 제거 + 정규식 매칭) — 5개 추출 함수 통합
- `dart_fin.py`: EPS 계정명 `"기본주당손익"` 변형 정규식 대응 (한국가스공사 EPS=None 해결)

### UI 개선
- DetailPage: "CAGR 요약" → "요약" 서브탭 이름 변경 + 하단에 PER/PBR/시총/주식수 밸류에이션 차트 배치
- TechnicalPanel: 밸류에이션 차트 제거 (요약 탭으로 이동)
- WatchlistButton: code/market 변경 시 상태 리셋 (탭 전환 후 "추가됨" 고착 버그 수정)
- App.jsx: 사이트 하단 투자 면책 문구 footer 추가

## 2026-04-29 — 웹 보안 헤더 추가 (securityheaders.com F→A)

### 보안 강화
- nginx(HTTPS): 보안 헤더 6개 추가 (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, HSTS)
- nginx: `server_tokens off` + `proxy_hide_header Server` (서버 정보 숨김)
- FastAPI 미들웨어: 보안 헤더 5개 추가 (IP 직접 접근 시에도 적용, HSTS 제외)

## 2026-04-29 — 경기국면+투자체제 통합 + 스크리너 한글화 + 전략빌더 UX 개선

### UI 개선
- 매크로 경기사이클: 경기 국면(5지표)과 투자 체제(심리/밸류에이션)를 2컬럼으로 나란히 표시
- 매크로 경기사이클: 경기 국면·투자 체제 hover 시 판단 기준 상세 툴팁 표시
- 매크로 경기사이클: 국면과 체제 괴리 시 설명 메시지 자동 표시
- 매크로 경기사이클: 하단 지표 게이지바 제거 → 소형 카드(신호값만) 간결화
- 스크리너: 투자전략 드롭다운 6종 한글화 (마법공식/저PER총수익/기대수익률/순유동자산/저PSR턴어라운드/재무건전성)
- 스크리너: 구루/GB/NF/주의 컬럼 헤더에 hover 툴팁 추가
- 스크리너: DART 프리셋 선택 시 구루 컬럼 항상 표시 (데이터 미수집 시에도)
- 스크리너: 구루점수 분모 6 고정 (기존 formulas_available/formulas_available 버그 수정)
- 백테스트: 전략빌더 탭을 기본 탭으로 변경 (탭 순서: 전략빌더→프리셋→커스텀)
- 백테스트: 전략빌더에서 YAML 변환 후 바로 백테스트 실행 가능 (커스텀 탭 전환 불필요)
- 전략빌더: 리스크관리 최소 1개 필수 검증 + 에러 메시지
- 전략빌더: StepPreview에서 중복 버튼(YAML변환/검증하기/전략저장) 제거 → 하단 네비에 "전략 완성"+"전략 저장" 통합

### 백엔드 개선
- `macro_service.get_macro_cycle()`: 투자 체제(determine_regime) 데이터 동시 반환
- `portfolio_advisor_service`: 경기사이클 국면(phase/leader_sectors/confidence) GPT 입력에 추가 → 섹터 추천 품질 향상

## 2026-04-29 — 매크로 분석 버그수정 + 개선

### 버그 수정
- YieldCurveSection/CreditSpreadSection/MacroCycleSection: API 응답 래핑(`{yield_curve:{...}}`) 언래핑 누락 → `data.yield_curve || data` 패턴 추가
- 경기사이클 `scores` 응답: 영문 국면명 점수 → 지표별 한국어 신호(스프레드 +0.76%, 축소 중, VIX 16.5 보통 등)

### 매크로 분석 개선
- 장단기 금리차/하이일드 스프레드 시계열: `period="6mo"` → `period="max", interval="1wk"` (금리 60년+, HYG/LQD 18년)
- 원자재에 **우라늄 ETF(URA)** 추가 (WTI-금 사이, 총 6종)
- 주요 지수에 **유로스톡스 50/닛케이 225/상하이종합/인도 SENSEX** 추가 (총 8개)
- 경기사이클: "현재 경기 국면" 라벨+크기 강조
- `frontend-dev.md` 에이전트에 모바일 호환성 규칙 테이블(9패턴) + 자가 점검 체크리스트 추가

---

## 2026-04-29 — 매크로 분석 대규모 개선 (6개 섹션 신규)

### 매크로 분석 신규
- **경기 사이클 국면** (`MacroCycleSection`): 4단계(회복/확장/과열/수축) 순환 다이어그램 + confidence + 5지표 breakdown + 주도 섹터 태그
- **장단기 금리차** (`YieldCurveSection`): ^IRX/^FVX/^TNX/^TYX 수익률곡선 LineChart + 10Y-3M 스프레드 시계열 AreaChart + 역전 경고
- **하이일드 스프레드** (`CreditSpreadSection`): HYG/LQD yield 카드 + 가격 비율 시계열 + widening/narrowing 배지
- **환율** (`CurrencySection`): USD/KRW, USD/JPY, EUR/USD, DXY 4개 카드 + 1개월 스파크라인
- **원자재** (`CommoditySection`): WTI, 금, 옥수수, 밀, 대두 5개 카드 + 1개월 스파크라인
- **섹터 히트맵** (`SectorHeatmapSection`): 11개 S&P 섹터 ETF × 4기간(1M/3M/6M/1Y) 수익률 히트맵 (초록~빨강 그라데이션)
- `services/macro_cycle.py` 신규: 5지표 가중합산 경기 국면 판단 (macro_regime.py와 독립)
- `stock/macro_fetcher.py`: 6개 yfinance 수집 함수 추가 (금리, 신용, 환율, 원자재, 섹터, 국면입력)
- `routers/macro.py`: 6개 GET 엔드포인트 추가 (총 11개)
- MacroPage 10개 섹션 통합 (기존 4 + 신규 6)

---

## 2026-04-28 — 모바일 호환성 전면 점검

### UI 개선
- Header: 모바일 햄버거 메뉴 추가 (`md:hidden`), 세로 네비게이션 패널, 드롭다운 클릭 지원
- ToastNotification: `w-80` → `w-[calc(100vw-1rem)] sm:w-80` (모바일 뷰포트 초과 방지)
- ScreenerPage: 300px 고정 사이드바 → `grid-cols-1 md:grid-cols-[300px_1fr]` 반응형
- ScreenerPage: 체제 배너 `flex-col sm:flex-row` 세로 스택
- FilterPanel/ReservationForm/OrderForm: `grid-cols-2` → `grid-cols-1 sm:grid-cols-2` 반응형 (총 7곳)
- PortfolioSummary: `grid-cols-3` → `grid-cols-1 sm:grid-cols-3`
- BacktestResultPanel: 메트릭 카드 `grid-cols-1 sm:grid-cols-2 md:grid-cols-4`
- BacktestPage: 설정 그리드 `grid-cols-1 sm:grid-cols-2 md:grid-cols-3`
- FinancialTable: 추정치 그리드 반응형 추가
- ReportDetailView: 체제/지수 그리드 반응형 추가
- StockHeader: `gap-6` → `gap-3 md:gap-6` (모바일 간격 축소)
- CustomStockSection: 삭제 버튼 터치 영역 확대 + 모바일 항상 표시

---

## 2026-04-28 — 도메인 + HTTPS 설정 (dkstock.cloud)

### 인프라
- `dkstock.cloud` 도메인 연결 (가비아 DNS → EC2 Elastic IP `3.39.188.29`)
- nginx 리버스 프록시 컨테이너 추가: SSL 종료 + HTTP→HTTPS 리다이렉트 + WebSocket 프록시
- Let's Encrypt certbot 컨테이너: 12시간마다 자동 인증서 갱신
- `infra/nginx/app.conf` 신규: nginx 설정 (dkstock.cloud + www, TLS 1.2/1.3)
- `scripts/init-ssl.sh` 신규: EC2 초기 SSL 인증서 발급 스크립트
- `docker-compose.prod.yml`: app `ports: 80:8000` → `expose: 8000` (내부 전용) + nginx/certbot 추가
- `deploy.yml`: nginx 설정 인라인 배포 + 3컨테이너(app+nginx+certbot) 구성

---

## 2026-04-28 — 테스트 환경 PostgreSQL 전환

### 테스트 인프라
- 테스트 DB를 인메모리 SQLite → **PostgreSQL 16**으로 전환 (프로덕션 동일 DBMS)
- `docker-compose.test.yml` 신규: 테스트용 PostgreSQL 컨테이너 (tmpfs 메모리 기반, 포트 5433)
- `tests/conftest.py`: session scope 엔진 + 함수별 TRUNCATE 격리 패턴
- CI(`ci.yml`): PostgreSQL service container 추가, `TEST_DATABASE_URL` 환경변수

### 버그 수정 (PostgreSQL 전환으로 발견)
- `stock_info` 모델 `shares`/`revenue`/`operating_income`/`net_income` 컬럼: `Integer` → `BigInteger` (삼성전자 발행주식수 59.7억 등 32bit 오버플로우)
- Alembic 마이그레이션 추가 (`de1f3d32fb96`)

---

## 2026-04-28 — AI자문 v3 전면 통합 (프롬프트+입력데이터+보고서 일원화)

### 프롬프트 통합
- v2/v3 이중 프롬프트 구조를 **단일 통합 프롬프트**로 전면 재작성
- 시스템 프롬프트: "20년 경력 수석 애널리스트 비판적 검증 모드" + 6대 분석 항목 + 정량 프레임워크
- 유저 프롬프트: 10년 재무(이자보상배율 포함) + 기술지표 + 리서치 데이터를 하나의 맥락으로 구성
- 중복 제거: 포지션가이드+최종매매전략→최종매매전략, 밸류에이션심화+밴드→밸류에이션분석, 매크로환경+사이클→매크로및산업분석

### 입력 데이터 통합
- `refresh_stock_data()` 1회 호출로 기본분석+리서치 데이터 전체 수집 ("입력정보 획득" 버튼 제거)
- 재무 데이터 수집 범위 5년→10년 확장 (dart_fin/yf_client years=10), 분기 실적 4분기→8분기
- `stock/research_collector.py` 신규: 거시지표/밸류에이션밴드/경영진/공시/뉴스 5카테고리 병렬 수집 (LLM 비용 0)
- `advisory_cache` 테이블에 `research_data` JSON 컬럼 추가 (Alembic 마이그레이션)

### v3 통합 스키마
- `advisory_report_v3.py` 전면 재작성: v2 상속 제거, 독립 통합 스키마
- 6대 분석 섹션: 재무건전성분석/밸류에이션분석/매크로및산업분석/경영진트랙레코드/가치함정분석/최종매매전략
- `generate_ai_report()` v2/v3 분기 완전 제거, 항상 v3 검증

### 프론트엔드
- `ResearchDataPanel.jsx` 신규: 프롬프트 전체 입력 데이터 미리보기 (기본분석 10항목 + 리서치 5항목)
- `AIReportPanel.jsx` 중복 섹션 제거: 포지션가이드/밸류에이션심화/매크로환경분석 카드 삭제
- 통합 보고서 구조: 등급→의견→6대분석→전략→시그널→시나리오→리스크/포인트

### 백엔드 확장
- `yf_client.py`: `fetch_company_officers()`/`fetch_major_holders()`/`fetch_earnings_dates()`/`fetch_macro_indicators()`/`fetch_sector_peers()` 5개 함수 추가
- `dart_fin.py`: `calc_interest_coverage()` 이자보상배율 계산 헬퍼
- `advisory_repo.py`: `save_research_data()` 리서치 전용 저장 함수
- `routers/advisory.py`: `POST /{code}/research` 수동 리서치 수집 엔드포인트

## 2026-04-27 — CI segfault 수정 + 섹터 컬럼 + 계층형 하네스

### 버그 수정
- CI pytest segfault 해결: `main.py` lifespan 백그라운드 서비스(prewarm/WS/스케줄러)를 `TESTING` 환경변수로 테스트 시 스킵
- conftest `engine.dispose()` 제거: daemon 스레드(pipeline 등)가 DB 접근 중 dispose되면 segfault 발생하는 문제 해소

### 섹터 컬럼 추가
- `fetch_market_metrics()` 반환값에 `sector` 필드 추가 (yfinance `info.get("sector")`)
- 관심종목 대시보드: 종목명 우측에 섹터 컬럼 추가
- 스크리너 테이블: 종목명 우측에 섹터 컬럼 + 52주 고점 대비 하락률(`drop_from_high`) 컬럼 추가

### 계층형 하네스 재구성
- 부서장(`department-head.md`) 신규: 모든 개발 요청의 단일 진입점, 유형 A/B/C/D 자동 라우팅
- 도메인팀장(`domain-lead.md`) 신규: 도메인 전문가 4명 팀 관리
- 개발팀장(`dev-lead.md`) 신규: 개발/QA/리팩토링 5명 팀 관리
- `asset-dev` 스킬을 부서장 오케스트레이터로 재작성 (코드 변경 수반 모든 요청의 단일 트리거)

## 2026-04-26 — 스크리너 구루 프리셋 확장 + UI 개선

### 구루 프리셋 3종 추가
- Graham NCAV(`calc_graham_ncav`): 순유동자산가치/시총 비율. 적자기업 포함. 청산가치 기반 절대 안전마진
- Fisher PSR(`calc_fisher_psr`): 시총/매출액. 적자기업 포함. 매출 기반 턴어라운드 발굴
- Piotroski F-Score(`calc_piotroski_fscore`): 8항목 재무건전성(신주발행 제외). 수익성(4)+재무구조(2)+영업효율(2). 추가 API 호출 0회
- 구루 패널 12점→24점 확장 (6공식×4점). Value Trap 7규칙 (F-Score극저, 극저PSR+매출급감 추가)
- 체제별 파라미터(`REGIME_GURU_PARAMS`) ncav/psr/fscore 임계값 추가

### UI 개선
- 필터 패널 접기/펼치기 버튼 (테이블 전체 폭 활용)
- 서준식 프리셋 per_min=0 버그 수정 (PER=None 종목 필터링 문제)
- defensive 체제 센티넬값(999) roe_min 유입 버그 수정
- guru_top 별도 입력 제거 (top과 통일)
- 구루 프리셋별 전략 소개 패널 추가 (6개 전략 상세 설명)
- 프리셋 선택 시 정렬 필드 자동 전환

## 2026-04-26 — 스크리너 구루 공식 + 체제 연계

### 스크리너 구루 공식 신규
- `services/guru_formulas.py` 신규: Greenblatt Magic Formula(ROIC+Earnings Yield), Neff Total Return Ratio(EPS CAGR+배당/PER), 서준식 기대수익률(ROE/PBR)
- 통합 구루 패널 (12점=3공식×4점), Value Trap 경고 5규칙, 체제별 파라미터(`REGIME_GURU_PARAMS`)
- `screener/service.py` 확장: `enrich_seo_scores`(서준식 일괄 계산), `sort_by_greenblatt_rank`(Combined Rank), `get_preset_filters`(프리셋별 기본 필터)
- `routers/screener.py` 확장: DART guru enrichment(`_enrich_guru`), 신규 파라미터(`preset`/`regime_aware`/`include_guru`/`guru_top`), 체제 응답 포함
- 4단계 파이프라인: KRX 기본 필터 → yfinance enrichment → DART guru enrichment → 체제 연계
- 단위 테스트 32개 (`tests/unit/test_guru_formulas.py`)

### 스크리너 UI 재설계
- FilterPanel: 구루 프리셋 드롭다운(Greenblatt/Neff/서준식), 체제 연계 토글, DART 분석 대상 수, 필터 설명 보강
- StockTable: 서준식 기대수익률 컬럼(항상), 구루 점수 배지/개별 점수/Value Trap 경고(DART enrichment 시)
- ScreenerPage: 체제 배너(regime+VIX/버핏/F&G+한줄메시지), 프리셋 배지, DART 로딩 메시지

## 2026-04-26 — 투자보고서 전면 개선 + AI자문 리포트 강화

### 투자보고서 페이지 전면 개선
- GPT 섹터 추천 서비스 신규 (`sector_recommendation_service.py`): 매크로 현황 기반 3컨셉(모멘텀/역발상/3개월선점) 탑픽 섹터+종목 추천. `macro_store` 일일 캐싱
- 파이프라인 확장: Step 0 중복방지(날짜+market) + Step 1.5 매크로 수집+GPT 섹터 추천 + report_json version 2 구조
- 보고서 페이지 UI 전면 재설계: 3탭 제거 → 페이지 진입 시 KR/US 자동 실행, 매크로 체제 카드(공유) + KR/US 토글 + 섹터 추천 + 종목+관심종목 버튼, 하단 이력 카드
- 신규 컴포넌트: `ReportDetailView`, `SectorConceptTabs`, `ReportHistoryList`
- `DailyReport.to_summary_dict()`에 `sector_summary` 필드 추가 (이력 목록에 전략별 섹터 요약)
- `GET /api/reports/by-date` 엔드포인트 추가

### AI자문 리포트 강화
- System/User Prompt에 4개 신규 분석 가이드라인 추가 (매크로환경분석/밸류에이션심화/시나리오분석/관련투자대안)
- Pydantic v2 스키마 확장: `MacroAnalysis`, `ValuationDeepDive`, `ScenarioAnalysis`, `InvestmentAlternative` 모델
- AIReportPanel에 4개 신규 섹션 UI: 매크로 카드, 밸류에이션 심화, 시나리오 3컬럼(낙관/기본/비관), 관련 투자 대안
- `max_completion_tokens` 10000→14000 (재시도 12000→18000)

## 2026-04-26 — KLineChart 차트 추가 + ROE/PBR 버그 수정

### KLineChart 캔들차트 신규
- 관심종목 상세(`DetailPage`)에 KLineChart(Canvas 기반) 캔들차트 추가
- StockHeader와 탭(재무분석/종합리포트) 사이에 배치
- 타임프레임 선택(15분/60분/1일/1주), 기간 선택, 기술지표 토글(MA/BB/VOL/MACD/RSI)
- 한국식 색상 테마(상승=빨강, 하락=파랑), 기존 OHLCV API 재사용
- `klinecharts@9.8.12` 의존성 추가

### 버그 수정
- ROE 미표기: `fetch_market_metrics()` — yfinance `returnOnEquity` None 시 분기 TTM순이익/자기자본 fallback 추가
- PBR 미표기: `_get_report_kr()` 및 `fetch_detail()` PBR/PER None 시 `fetch_market_metrics()` 값으로 보충

---

## 2026-04-26 — 하네스 TDD 애자일 재구성 + 개발자 분리

### 하네스 재구성
- 도메인 전문가 4명: 수동적 자문 → **능동적 요건 정의 참여** + 팀 통신 프로토콜 추가
- TestEngineer: 구현 후 테스트 → **TDD RED phase** (테스트 선행 작성)
- DevArchitect → **BackendDev + FrontendDev 분리** (백엔드/프론트 전담)
- QA Inspector: 파이프라인 끝 검증 → **각 GREEN 직후 즉시 경계면 검증**
- asset-dev 오케스트레이터: Phase 1(도메인 전문가 팀 토론→요건서) + Phase 2(TDD RED-GREEN-VERIFY 사이클)
- CLAUDE.md 하네스 포인터 + 변경 이력 테이블 추가

---

## 2026-04-25 — 인프라 개선 + CI/CD 백테스터 연동

### 인프라 개선
- EC2 인스턴스 타입 `t3.micro`(1GB) → `t3.small`(2GB) 업그레이드 (Docker pull 시 OOM hang 방지)
- Swap 1GB → 2GB 증설 (`user_data.sh`)
- SSM `KIS_MCP_ENABLED` `false` → `true` 활성화

### CI/CD 개선
- `deploy.yml`: **Ensure Backtester MCP** 단계 추가 — 배포 전 백테스터 MCP 서버 생존 확인 + 자동 기동
- `deploy.yml`: Deploy to EC2에 `command_timeout: 5m` 추가 (무한 hang 방지)
- GitHub Secret `BACKTESTER_HOST` 추가

---

## 2026-04-25 — 전략빌더(Strategy Builder) 신규

### 전략빌더 백엔드 신규
- `services/strategy_builder_service.py`: BuilderState JSON → .kis.yaml 변환(`convert_builder_to_yaml`) + 검증(`validate_builder_state`) + YAML 요약 추출(`extract_strategy_summary`)
- `routers/backtest.py`: 6개 엔드포인트 추가 (8→15개) — `POST /strategy/convert`, `POST /strategy/validate`, `GET/POST /strategies`, `GET/DELETE /strategies/{name}`
- `db/models/backtest.py`: Strategy 모델에 `builder_state_json` 컬럼 추가
- `db/repositories/backtest_repo.py`: `get_strategy()`, `delete_strategy()` 추가, `save_strategy()`에 `builder_state_json` 파라미터
- `stock/strategy_store.py`: Strategy CRUD 래퍼 4개 추가 (`save_strategy`/`list_strategies`/`get_strategy`/`delete_strategy`)
- `services/backtest_service.py`: `run_custom_backtest`에 `strategy_display_name`, `builder_state` 파라미터 추가, `extract_strategy_summary` 연동
- `stock/symbol_map.py`: `_build_map()`에 DART corpCode fallback 추가 (pykrx 실패 시), 빈 결과 캐시 방지
- Alembic 마이그레이션: `f3a8b1c7d9e2_add_builder_state_json_to_strategies.py`
- `requirements.txt`: `pyyaml` 추가

### 전략빌더 프론트엔드 신규 (14개 파일)
- `frontend/src/components/strategy-builder/` 디렉토리 전체:
  - `strategyBuilderConstants.js` — 83개 기술지표 + 66종 캔들패턴 카탈로그, 연산자, 프리셋 6개
  - `useStrategyBuilder.js` — 빌더 상태 관리 훅
  - `StrategyBuilder.jsx` — 5단계 스테퍼 메인 컨테이너
  - `StepMetadata.jsx`/`StepIndicators.jsx`/`StepConditions.jsx`/`StepRisk.jsx`/`StepPreview.jsx` — 각 단계 UI
  - `IndicatorCard.jsx`/`IndicatorPickerModal.jsx` — 지표 카드 + 모달
  - `ConditionCard.jsx`/`ConditionGroupCard.jsx`/`OperandSelector.jsx` — 조건 빌더
  - `StrategyListPanel.jsx` — 저장된 전략 목록 + 프리셋
- `frontend/src/api/strategyBuilder.js` — 변환/검증/저장/로드/삭제 API 6개

### 프론트엔드 수정
- `StrategySelector.jsx`: "전략 빌더" 세 번째 탭 추가 (프리셋/커스텀 YAML/빌더)
- `BacktestPage.jsx`: 빌더 YAML → `runCustom` 연결, 저장 전략 직접 실행
- `BacktestHistoryTable.jsx`: builder/custom 전략은 지표+파라미터 형식으로 표시 (YAML 대신)
- `api/backtest.js`: `runCustomBacktest`에 `strategyDisplayName`, `builderState` 추가
- `hooks/useBacktest.js`: `runCustom`에 추가 파라미터 전달

### 테스트
- `tests/unit/test_strategy_builder.py` — 114개 단위 테스트 (변환/검증/연산자/리스크/프리셋/null방어/요약추출)
- `tests/api/test_backtest_api.py` — 전략빌더 API 10개 테스트 추가

## 2026-04-25 — Lean 백테스터 EC2 + 백테스트 UI 개선

### Lean 백테스터 EC2 신규
- **Terraform 모듈**: `infra/modules/backtester/` (EC2 t3.micro + EIP + IAM + 보안그룹)
- QuantConnect Lean Docker 이미지 (27.5GB) + FastAPI(8002) + Next.js(3001) + MCP(3846) 배포
- 50GB EBS + 2GB swap, `open-trading-api/backtester` 레포 clone
- stock-manager EC2 → `KIS_MCP_URL=http://<private-ip>:3846/mcp` VPC 내부 연결
- SSM Parameter Store에 `KIS_MCP_URL`, `KIS_MCP_ENABLED` 추가

### 백테스트 UI 개선
- **파라미터 슬라이더**: `StrategySelector` number input → range slider 변환 (min/max 있는 파라미터)
- **거래비용 입력**: 수수료(0.015%), 세금(0.23%), 슬리피지(0.05%) 3개 필드 추가
- **API 전체 레이어**: `commission_rate`/`tax_rate`/`slippage` 파라미터 전달 (프론트→API→서비스→MCP)
- **원화 절사**: `BacktestResultPanel` 모든 금액 `Math.floor()` 적용 (거래가격/순자산/Y축/툴팁)

## 2026-04-24 — AWS 배포 + CI/CD 구축

### AWS 인프라 신규
- **Terraform IaC**: `infra/` 디렉토리에 6개 모듈 (network, security, compute, database, ecr, secrets)
- **EC2 t3.micro** (프리티어): Amazon Linux 2023, Docker + docker-compose, 1GB swap, Elastic IP
- **RDS PostgreSQL 16**: db.t3.micro (프리티어), 프라이빗 서브넷, 자동 백업
- **ECR**: Docker 이미지 리포지토리, 최근 5개 유지 + 미태그 1일 삭제
- **SSM Parameter Store**: 15개 환경변수 SecureString 저장, 배포 시 .env 자동 생성
- **VPC**: 퍼블릭 서브넷 1개(EC2) + 프라이빗 서브넷 2개(RDS)

### CI/CD 신규
- **GitHub Actions**: `ci.yml` (모든 push: pytest + frontend build) + `deploy.yml` (main push: ECR → EC2)
- **자동 배포**: main push → Docker 빌드 → ECR 푸시 → SSH EC2 → SSM .env 생성 → docker-compose up
- **GitHub Secrets**: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, EC2_HOST, EC2_SSH_KEY

### 코드 변경
- `requirements.txt`: `psycopg2-binary` 추가 (PostgreSQL 드라이버)
- `main.py`: `/api/health` 엔드포인트 추가 (ALB/모니터링용)
- `docker-compose.prod.yml` 신규: ECR 이미지, 포트 80, 로그 로테이션
- `scripts/ec2-deploy.sh` 신규: EC2 수동 배포 스크립트
- `.gitignore`: Terraform 상태 파일 제외
- `.dockerignore`: `infra/`, `.github/` 제외

## 2026-04-20 — 시세판 카드 개선 (당일 OHLC + 전일대비 + 미니캔들)

### UI 개선
- **시세판 카드**: 현재가 + 전일대비 가격등락(+500) + 등락률% 표시
- **미니캔들**: 당일 OHLC 캔들 (양봉=빨강, 음봉=파랑) 카드 우측 배치
- **스파크라인 축소**: 카드 폭 80%, 미니캔들 20% 배분
- **당일 고가/저가**: 카드 하단에 H/L 표시
- `MiniCandleBar.jsx` 신규 컴포넌트 (CSS 기반, Recharts 불필요)

### 백엔드
- `POST /api/market-board/intraday-ohlc`: 복수 종목 당일 OHLC 배치 조회 (yfinance history, 캐시 6분/6시간)
- `_parse_execution()` 확장: H0STCNT0 t[7]=시가, t[8]=고가, t[9]=저가 추가 파싱
- WS `/ws/market-board` 전송 데이터에 change/open/high/low 필드 추가

## 2026-04-19 — 백테스트 결과 상세내역 + 파라미터 표시 수정

### 백테스트 결과 상세내역 신규
- **포지션 요약** 6카드: 평균보유기간/평균수익거래/평균손실거래/최대연승/최대연패/승패분포
- **연간 수익률** 테이블: 연도별 수익률+시작자산+종료자산
- **월별 수익률 히트맵**: 연×월 매트릭스, 6단계 색상 그라데이션(빨강=수익/파랑=손실) + 범례 + 연간 합계
- `backtestUtils.js` 순수 계산 유틸 신규 (computeAnnualReturns/computeMonthlyReturns/computePositionSummary)

### 버그 수정
- **입력 파라미터 미표시**: `params_json` lookup 누락 + 프리셋 기본값 미저장 → 기본값+사용자수정값 병합 저장
- **StrategySelector `mode` not defined**: props 구조분해에 `mode`/`onModeChange`/`yamlContent`/`onYamlChange` 누락
- **커스텀 YAML 템플릿 오류**: 잘못된 YAML 포맷 템플릿 제거, 안내 텍스트만 표시

### 백엔드 개선
- `params_json`, `strategy_display_name` 컬럼 추가 (Alembic 마이그레이션)
- MCP `param_overrides` 파라미터명 수정, YAML 검증 에러 전파 개선
- `preset_name` API 파라미터 추가 (MCP display name 저장)

### 이력 테이블 개선
- 전략명: MCP display name 우선 → STRATEGY_KR fallback
- 파라미터 펼침/접기 토글 버튼 (한글 라벨+설명 포함)
- STRATEGY_KR 매핑을 실제 MCP 10개 프리셋에 맞게 갱신

## 2026-04-19 — 백테스트 UI 추가 개선 (캔들차트 통합, 파라미터 한글화)

### UI 개선
- 수익률 곡선에 주가 캔들차트 + 거래량 바차트 오버레이 (이중 Y축: 좌=주가, 우=순자산)
- OHLCV 데이터 advisory API 별도 조회 + equity_curve 날짜 범위 자동 매칭
- 캔들차트 위 MA5/MA20 이동평균선 표시
- OHLCV 미조회 시 기존 수익률 곡선 전용 차트 fallback
- 매매 시그널: ReferenceDot → ReferenceArea 보유 구간 범위 표시 (수익=빨강/손실=파랑/보유중=회색)
- 전략 파라미터 한글명 + 비유적 설명 매핑 (PARAM_KR, 80+개)
- 파라미터 UI: 카드형 레이아웃 (한글명 + 영문키 서브텍스트 + 설명)
- 백테스트 종목 검색에서 US/FNO 제거 (SymbolSearchBar `markets` prop, 국내 KRX만 지원)
- 거래내역 날짜 KST 변환 (UTC 타임스탬프 → +9h, 날짜만이면 그대로)
- 메트릭 한글화: CAGR→연평균 수익률, Sortino→소르티노 비율, Profit Factor→손익비
- MetricsCard/추가 메트릭 각 항목 아래 간단 설명 텍스트 추가

### 개발 도구 신규
- `scripts/run-related-tests.sh` — 변경 파일에 대응하는 테스트만 자동 실행
- Claude Code postToolUse hook (Edit/Write 후 관련 pytest/npm build 자동 실행)

## 2026-04-19 — 백테스트 UI 6가지 개선

### UI 개선
- 거래 내역 Buy/Sell 색상 수정 (대소문자 무시 비교 → Buy=빨강, Sell=파랑)
- 거래 내역 날짜 표시 (date/entry_date/timestamp/time 폴백 체인)
- 매도 거래 수익률 자동 계산 (직전 매수가 대비)
- 이력 테이블 종목명 표시 (코드+이름, 백엔드 code_to_name 부착)
- 이력 테이블 한글 전략명 + 카테고리 배지 (STRATEGY_KR/STRATEGY_CATEGORY 매핑)
- 이력 삭제 기능 (DELETE /api/backtest/history/{job_id} + 프론트 삭제 버튼)
- 전략 파라미터 편집 UI (StrategySelector input + BacktestPage customParams state)
- 수익률 곡선 매매 시그널 마커 (Recharts ReferenceDot, 매수=빨간점/매도=파란점 + 범례)
- 백테스트 결과에 사용된 파라미터 표시 섹션

### 신규 API
- `DELETE /api/backtest/history/{job_id}` — 이력 삭제
- `PresetBacktestBody.params` — 전략 파라미터 오버라이드

## 2026-04-19 — 전체 기능 테스트 536개 구현

### 테스트 신규
- 단위 테스트 306개: indicators, safety_grade, macro_regime, exceptions, schemas, cache, utils
- 통합 테스트 138개: 9개 DB Repository 전체 CRUD + 엣지케이스
- API 테스트 91개: 16개 라우터 전체 엔드포인트 + WebSocket

## 2026-04-19 — 백테스트 MCP 파라미터 수정 + 비동기 2단계 + 이력 조회

### 버그 수정
- MCP 서버 `kis_devlp.yaml`에 `my_agent`/`prod`/`vps`/`ops`/`vops` 누락 → KeyError 해결
- `backtest_service.py` 파라미터 불일치 수정: `symbol`→`symbols`(배열), `preset`→`strategy_id`, `initial_cash`→`initial_capital`
- MCP 비동기 2단계 구조 적용: `run_preset_backtest_tool` → job_id → `get_backtest_result_tool(wait=true)`
- 실패 시 job 상태를 `"failed"`로 갱신 (기존: `"submitted"` 영구 잔류)
- `BacktestResultPanel` MCP 중첩 메트릭(basic/risk/trading) 자동 플래트닝 + equity_curve 오브젝트→배열 변환

### 이력 조회 신규
- `BacktestHistoryTable` 컴포넌트 신규 (일시/종목/전략/수익률/상태/보기)
- `useBacktestHistory` 훅 + `fetchBacktestHistory` API 함수 추가
- `BacktestPage`에 이력 섹션 통합 (마운트 시 로드, 완료 시 새로고침, 과거 결과 보기)
- 폴링 타임아웃 3분→10분 확장

## 2026-04-18 — MCP 백테스트 연동 + 백테스트 UX 개선

### MCP 연동
- `mcp_client.py` Streamable HTTP 세션 프로토콜 전환 (initialize → session ID → tools/call + SSE 파싱)
- Docker 내부에서 호스트 MCP 접근: `host.docker.internal` + `Host: 127.0.0.1` 헤더 고정
- `docker-compose.yml` `extra_hosts: host.docker.internal:host-gateway` 추가
- `backtest_service.py` `_extract_mcp_content()` — MCP content 구조에서 실제 데이터 추출

### 백테스트 UI 개선
- `StrategySelector`: 프리셋 선택 시 상세 설명 카드 표시 (description, category 배지, tags, params 기본값/범위)
- `BacktestPage`: 진행 현황 강화 — 단계별 메시지(전략 제출/시뮬레이션 중) + 경과 시간 카운터 + 프로그레스 바(배치)
- "다른 페이지로 이동해도 괜찮습니다" 백그라운드 실행 안내 배너 추가

## 2026-04-18 — 양도세 FIFO 엔진 전면 재설계 + 시뮬레이션

### 버그 수정 (근본)
- KIS API 연속조회(페이지네이션) 무한루프 — 요청 헤더 `tr_cont: "N"` 누락으로 동일 50건 반복. CTOS4001R+TTTS3035R 모두 수정
- FIFO 시간역행 — 매수 큐를 한꺼번에 구축하여 2025-09 매도가 2025-11 매수를 소진. **시간순 재생 방식**으로 전면 재작성 (매도 시점 이전 매수만 소진)
- FIFO lots 삭제 순서 — `delete_calculations` 후 `delete_fifo_lots` 호출 시 calc_ids가 이미 삭제됨. 순서 교정

### 양도세 엔진 개선
- 잔고 기반 적응적 동기화: 현재 보유 + 매도 역산 → 매수 충족될 때까지 과거 소급 (최대 2015년)
- CTOS4001R + TTTS3035R 병합 동기화 (fallback이 아닌 양쪽 모두 시도, 중복 자동 스킵)
- `tax_fifo_lots` 테이블 신규: 매도→매수 FIFO 매핑을 정규 테이블로 관리
- 잔고 `avg_price` fallback: 매수 내역 없지만 잔고에 있는 종목은 KIS 매입단가로 취득가 추정
- 동기화 후 자동 재계산 (stale 계산 방지)
- 환율 조회 실패 캐시 (yfinance 반복 조회 방지)

### 시뮬레이션 신규
- `POST /api/tax/simulate`: 현재 잔고 가상 매도 → 예상 양도세 (DB 저장 없음, 인메모리 FIFO)
- `GET /api/tax/simulate/holdings`: 시뮬레이션용 보유종목 목록
- TaxSimulationPanel 컴포넌트: 보유종목 선택 + 매도가/수량 입력 + 실제 vs 합산 세액 비교

### 도메인 문서
- `docs/TAX_DOMAIN.md` 신규: 양도세 규칙, FIFO 알고리즘, 잔고 역산, 환율/수수료 규칙

## 2026-04-18 — 양도세 FIFO 전용 전환 + 과거 매수 자동 탐색

### 버그 수정
- 양도세 동기화 시 과세 연도만 조회하여 과거 매수 내역 부족 발생 → 과거 5년(~2020) 자동 탐색으로 FIFO 매수풀 확보
- `sync_transactions(year)` → `_sync_single_year()` 추출, 다년도 순회 구조

### 리팩토링
- 이동평균법(AVG) 제거, FIFO 전용으로 단순화
- 백엔드 `method` 파라미터 제거 (tax_service / routers/tax.py)
- 프론트엔드 FIFO/AVG 토글 UI 제거 (TaxPage / api/tax.js / useTax.js)

## 2026-04-18 — 해외주식 양도소득세 계산 서비스 신규 + KIS API 문서

### 해외주식 양도소득세 신규
- 백엔드: `db/models/tax.py` (TaxTransaction/TaxCalculation 2 테이블) + `db/repositories/tax_repo.py` + `stock/tax_store.py` + `services/tax_service.py` + `routers/tax.py` (7개 엔드포인트)
- 환율 조회: yfinance `USDKRW=X` 연간 일괄 fetch → cache.db 영구 캐시. 주말/공휴일 직전 영업일 자동 fallback
- 데이터 수집: 3단계 KIS API 동기화 — `CTOS4001R`(일별거래내역, 환율+수수료 내장) → `TTTS3035R`(주문체결내역, 기간별) → 로컬 DB orders fallback → 수동 입력
- 양도세 계산: 선입선출법(FIFO) 기본 + 이동평균법 토글. 기본공제 250만원, 세율 22%
- 프론트엔드: `/tax` 페이지 (3탭: 요약/매매내역/계산상세), 4카드(양도차익/공제/과세표준/세액), 종목별 BarChart, 수동 추가 폼
- Header "매매" 드롭다운에 "양도세" 메뉴 추가

### KIS OpenAPI 전체 문서 기록
- `docs/KIS_API_REFERENCE.md` 전면 재작성: xlsx 338개 API → 22개 카테고리별 Markdown 테이블 (REST 278개 + WebSocket 60개)

## 2026-04-18 — 포트폴리오 자문 섹터 추천 + 뉴스 수집 품질 개선

### 포트폴리오 자문 — 신규 섹터 진입 추천
- GPT 프롬프트에 `sector_recommendations[]` JSON 스키마 + 규칙 29-32 추가
- 체제별 신규 섹터 한도: accumulation=3-5개, selective=2-3개, cautious=1개, defensive=금지
- `_get_macro_news_context()`: 한국 5개 + 해외 3개 뉴스 헤드라인을 GPT 컨텍스트에 주입
- `_REGIME_VALUATION_LIMITS`: 체제별 PER/PBR 한도 매핑 (규칙 31에서 참조)
- `SectorRecommendationCard.jsx` 신규: 섹터명+목표비중+타이밍 배지+대표종목→DetailPage 링크
- `AdvisorPanel.jsx`: DiagnosisCard와 RebalanceCard 사이에 SectorRecommendationCard 배치

### 뉴스 수집 품질 개선
- 한국 뉴스: 단일 검색어 → Google News **비즈니스 토픽 RSS**(편집 큐레이션) + `증시+금리+환율` 2개 소스 병합
- 해외 뉴스: NYT만 → NYT + Google News US 비즈니스 토픽 2개 소스 병합
- `_dedup_and_sort()` 신규: 제목 앞 30자 기반 중복 제거 + `published_ts` 최신순 정렬
- `_parse_published_ts()` 신규: RFC 2822 날짜 → Unix timestamp 파싱
- `_parse_rss()`: `published_ts` 필드 추가 (정렬 기준)
- `fetch_investor_news()`: 여유있게 수집 후 `_dedup_and_sort()` 적용
- `macro_service.py`: `source` 필드 NYT 하드코딩 → 동적 반영

### UI 개선
- `DiagnosisCard.jsx`: 섹터명 잘림 수정 (`w-20` → `w-28 shrink-0` + `title` 속성)

## 2026-04-17 — KIS AI Extensions 백테스트 연동 + 267260 가격 버그 수정

### 버그 수정
- `_kr_yf_ticker_str()` score 기준 강화: `best_score = -1` → `0` (score ≥ 1 필수, mktcap 또는 shares 존재해야 유효 suffix)
- 267260(HD현대일렉트릭) `.KQ` 잘못 캐시되어 307,000원 표시 → `.KS` 정상 선택으로 1,087,000원 복구
- `market_cap > 0`, `shares > 0` 양수 검증 추가
- `best_score >= 2` 시 조기 중단 (불필요한 suffix 추가 시도 방지)

## 2026-04-17 — KIS AI Extensions 백테스트 연동

### 백테스트 기능 신규
- KIS AI Extensions MCP 서버 연동 (`services/mcp_client.py` — httpx JSON-RPC 클라이언트)
- 백테스트 서비스 (`services/backtest_service.py` — 프리셋/커스텀/배치 실행, 전략 신호 생성)
- 백테스트 API (`routers/backtest.py` — 7개 엔드포인트: status/presets/indicators/run/result/history)
- DB 모델 (`db/models/backtest.py` — BacktestJob, Strategy) + Alembic 마이그레이션
- Store 래퍼 (`stock/strategy_store.py` — db/repositories/backtest_repo.py 위임)
- 환경변수 `KIS_MCP_URL`, `KIS_MCP_ENABLED` 추가 (기본 비활성화)
- httpx 의존성 추가

### AI 자문 전략 신호 통합
- `advisory_service.py`: `_collect_strategy_signals()` — MCP 대표 3전략 신호 병렬 수집
- `_build_strategy_signal_section()` — GPT 프롬프트에 전략 신호/백테스트 메트릭 섹션 추가
- System Prompt에 "전략 4: KIS 퀀트 전략 신호 (보조 지표)" 규칙 추가
- `advisory_store.save_cache()` + `advisory_cache` 테이블에 `strategy_signals` JSON 컬럼
- MCP 비활성화 시 기존 자문 시스템 100% 동작 (zero degradation)

### 포트폴리오 자문 연동
- `portfolio_advisor_service.py`: 각 holding에 `backtest_metrics` 필드 추가

### 프론트엔드 신규
- BacktestPage (`/backtest`) — 종목 선택 + 전략 선택(프리셋/YAML) + 기간/금액 + 실행 + 결과 차트
- components/backtest/ (StrategySelector, MetricsCard, BacktestResultPanel, BatchCompareTable)
- api/backtest.js + hooks/useBacktest.js (3초 폴링, 타임아웃 3분)
- Header 분석 드롭다운에 "백테스트" 메뉴 추가
- TechnicalPanel에 KIS 전략 신호 카드 (MCP 활성화 시만 표시)

---

## 2026-04-17 — AI자문 개선 (입력/프롬프트/출력 3축 개편)

### Phase 1: 프롬프트 보강 + 개별↔포트폴리오 연계
- `services/macro_regime.py` 신규: 공용 체제 판단 모듈 (REGIME_MATRIX 20셀 + VIX>35 오버라이드 + 하이스테리시스 ±5). 3개 서비스(advisory/portfolio_advisor/pipeline) 통합
- System Prompt에 도메인 에이전트 규칙 삽입: MarginAnalyst 7점 등급표, MacroSentinel 매트릭스, OrderAdvisor 등급별 손절폭(A=-8%/B+=-10%/B=-12%), ValueScreener Value Trap 5규칙
- User Prompt에 Forward 추정치 섹션 추가 (기존 수집 데이터 활용)
- 포트폴리오 자문에 개별 AI 리포트 연계 (각 보유 종목의 등급/요약/할인율/리스크 주입)
- 52주 고가 6시간 캐시 도입 (`advisor:52w:{market}:{code}`)

### Phase 2: 데이터 보강 + 정량 필드
- `services/safety_grade.py` 신규: 7점 등급(`compute_grade_7point`) + 복합점수(`compute_composite_score`) + 체제정합성(`compute_regime_alignment`) + 포지션사이징(`compute_position_sizing`)
- `stock/indicators.py`: `volume_signal`(거래량/5일평균 비율), `bb_position`(BB밴드 내 위치 0~100) 추가
- `stock/advisory_fetcher.py`: `fetch_valuation_stats()` 신규 (PER/PBR 5년 평균/최대/최소/편차%)
- `stock/dart_fin.py`: `fetch_quarterly_financials()` 신규 (DART 누계→분기 환산, 최근 4분기)
- `stock/yf_client.py`: `fetch_quarterly_financials_yf()` 신규 (yfinance 분기 실적)
- User Prompt +4섹션: PER/PBR 5년 비교, 분기 실적, 거래량·BB 신호, 7점 등급 사전 계산값
- v2 JSON 스키마: `schema_version`/`종목등급`(A~D)/`등급점수`(0-28)/`복합점수`(0-100)/`체제정합성점수`(0-100)/`Value_Trap_경고`/`등급팩터`/`recommendation`(ENTER/HOLD/SKIP)
- 포트폴리오 가중 등급 집계(`portfolio_grade_weighted_avg`) + 등급 분포 + 체제 정합성 점수

### Phase 3: DB 스키마 + Pydantic + UI
- `db/models/advisory.py`: AdvisoryReport +6컬럼(grade/grade_score/composite_score/regime_alignment/schema_version/value_trap_warning), PortfolioReport +3컬럼(weighted_grade_avg/regime/schema_version). 모두 nullable=True
- Alembic 마이그레이션 `2e051b80939e_add_advisory_grade_fields.py`
- `services/schemas/advisory_report_v2.py` 신규: Pydantic v2 스키마 검증 (11개 모델, validate/extract)
- 재시도 로직: max_tokens 10000→12000, 토큰 잘림/Pydantic 실패/일반 에러 각 1회 재시도. 2차 실패 시 저장 거부
- `AIReportPanel.jsx`: v2 등급 카드 (SafetyGradeBadge + ScoreBar + Value Trap 배너 + recommendation). v1 리포트 시 카드 숨김
- `AdvisorPanel.jsx`: 개별 종목 리포트 연계 요약 카드 (가중 등급 + 분포 바 + B미만 경고). weighted_grade_avg 부재 시 숨김
- npm run build 성공 (779 modules)

### QA 결과
- 45 PASS / 0 MAJOR / 4 MINOR
- 3중 일관성 확인: System Prompt(문자) = safety_grade.py(코드) = Pydantic(타입)
- E2E API 호출 성공: 삼성전자 v2 등급=B+, 등급점수=20, recommendation=SKIP (defensive 체제)

## 2026-04-15 — db/ 패키지 구조 리팩토링

### 리팩토링
- `db/utils.py` 신규: KST 타임존 헬퍼(`KST`, `now_kst`, `now_kst_iso`) 정의 원본. db/repositories/에서 직접 import하여 db/→stock/ 역방향 의존 해소
- `stock/db_base.py`: 자체 정의 제거 → `db/utils.py`에서 re-export (기존 caller 호환)
- `stock/report_store.py` 신규: 보고서 CRUD 래퍼 (다른 6개 store와 동일 패턴 통일)
- `services/report_service.py`: `db: Session` 파라미터 제거 → `stock/report_store.py` 경유
- `routers/report.py`: `Depends(get_db)` 제거 → 서비스 직접 호출
- `services/pipeline_service.py`: `get_session()` 직접 사용 제거 → 서비스 경유
- `db/repositories/stock_info_repo.py`: `batch_get()` N+1 → `or_(and_(...))` 단일 쿼리
- `db/repositories/stock_info_repo.py`: upsert 에러 로깅 `debug` → `warning`
- `db/repositories/macro_repo.py`: `get_today()` 내 5% 확률 cleanup → `cleanup_old()` 별도 메서드 분리
- Alembic 마이그레이션: orders/reservations 테이블 `server_default` 추가
- Reservation 모델: `status`, `market`, `memo`에 `server_default` 추가

## 2026-04-13 — 투자 파이프라인 서비스 + 스케줄러

### 투자 파이프라인 신규
- `services/pipeline_service.py`: 매크로 체제 판단(REGIME_MATRIX) → 체제별 스크리닝 → 심층 분석(7점 등급) → 추천 생성 → 보고서 저장
- 체제 판단: 버핏지수×공포탐욕 교차표, VIX>35 오버라이드, 버핏지수 백분율→소수 자동 변환
- 7점 등급: Graham 할인율/PER평균비교/PBR절대/부채비율/유동비율/FCF추세/매출CAGR (28점 만점 A~D)
- 추천 생성: B+ 이상 + 안전마진 임계값 초과 + R:R≥2.0 필터
- `services/scheduler_service.py`: APScheduler BackgroundScheduler (08:00 KR / 16:00 US KST)
- `routers/pipeline.py`: POST /run (비동기), POST /run-sync (동기), GET /status
- ReportPage에 KR/US 분석 실행 버튼 + 스케줄러 상태 + 실행 결과 표시 추가
- `apscheduler` 의존성 추가

## 2026-04-13 — 하네스 재구성 + 보고서 시스템 + 테스트 인프라

### 하네스 재구성
- 대화형 투자 스킬 6개 삭제 (macro-analysis, value-screening, graham-analysis, portfolio-check, order-recommend, value-invest)
- 도메인 에이전트 4명(MacroSentinel/ValueScreener/MarginAnalyst/OrderAdvisor) → **자문 전용**으로 전환 (API 호출 제거)
- DevArchitect 역할 확대: 투자 자동화 시스템 전체 개발 (파이프라인/스케줄러/Telegram)
- TestEngineer 에이전트 신규 추가 (pytest 기반 자동화 테스트 전담)
- asset-dev 스킬 범위 확장 (파이프라인/스케줄러/Telegram 개발 포함)
- qa-verify 스킬에 파이프라인 로직 검증 항목 추가

### 보고서 시스템 신규
- DB 모델 3개: RecommendationHistory, MacroRegimeHistory, DailyReport + ReportRepository
- Alembic 마이그레이션 (테이블 3개 + 인덱스 5개)
- `services/report_service.py`: 추천 이력/체제 이력/보고서 CRUD + 통합 Markdown 생성 + 성과 통계
- `routers/report.py`: 7개 GET 엔드포인트 (`/api/reports/*`)
- `frontend/src/pages/ReportPage.jsx`: 3탭 UI (일일 보고서/추천 이력/성과 통계)
- Header 분석 드롭다운에 "보고서" 메뉴 추가

### 테스트 인프라 신규
- `tests/` 디렉토리: conftest.py(인메모리 DB + TestClient) + unit/integration/api 3계층
- 27개 테스트: 단위 7개(Markdown 생성, is_domestic) + 통합 11개(Repository CRUD) + API 9개(엔드포인트)
- pytest + pytest-asyncio 의존성 추가

## 2026-04-04 — 역발상 매수 전략 + 밸류에이션 차트 확장 + UI 개선

### 프롬프트 개선
- 포트폴리오 AI자문: cautious/selective 체제에서 역발상 매수 규칙 10개 추가 (규칙 19~28)
- 역발상 매수 5대 적격 조건 (52주 -30%+, PBR<1.0, 부채비율<100%, 영업이익 흑자, FCF 양수)
- 보유종목 vs 신규종목 판단 분리, 포지션 한도 (cautious 1.5%/7.5%)
- 포트폴리오 자문 컨텍스트에 종목별 52주 고가·하락률 추가

### 신규 기능
- 스크리너 API: `drop_from_high` 쿼리 파라미터 추가 (52주 고점 대비 하락률 필터)
- 스크리너 enrichment: `high_52`, `low_52`, `drop_from_high` 필드 추가
- FilterPanel: "52주 고점 대비 (%)" 입력 필드 추가

### UI 개선
- 메뉴바 순서 변경: 시세판→관심종목→분석▼→포트폴리오→매매▼, 그룹 구분선 3개
- ValuationChart: 시가총액 추이(보라) + 발행주식수 추이(주황) 차트 추가
- 발행주식수: 분기별 시계열 반영 (자사주 소각 등 변동 추적)

### 버그 수정
- EPS fallback: DART EPS 미제공 종목(SK하이닉스 등)에서 net_income/shares로 직접 계산
- PBR fallback: yfinance priceToBook None 시 대차대조표 자본총계/주식수로 계산 (골프존 등)
- yf_client: tz-aware/tz-naive 비교 버그 수정 (밸류에이션 히스토리 빈 배열 반환)
- KRX 경로: pykrx 빈 결과 시 yfinance fallback 전환
- fetch_market_metrics: high_52/low_52 필드 추가

### UI 개선 (자동완성)
- AddStockForm에 자동완성 검색 추가 (KR: 400ms debounce + 드롭다운, US: 티커 직접 입력)
- 기존 searchStocks API 재사용, 외부 클릭 닫기, 시장 변경 시 상태 초기화

## 2026-04-04 — SQLAlchemy ORM 마이그레이션

### 리팩토링
- SQLite 직접 접근 → SQLAlchemy ORM 전환 (6개 비즈니스 DB → 단일 `app.db` 통합)
- `db/` 패키지 신규: `base.py`(DeclarativeBase) + `session.py`(Engine/Session) + `models/`(12개 모델) + `repositories/`(6개 Repository)
- 기존 6개 store 모듈(`store.py`, `order_store.py` 등)은 Repository 위임 래퍼로 전환 (함수 시그니처 100% 유지)
- Alembic 마이그레이션 도입 (`alembic/`): 스키마 버전 관리, `render_as_batch=True` (SQLite 호환)
- `config.py`에 `DATABASE_URL` 환경변수 추가 (기본값: SQLite, PostgreSQL/Oracle 전환 가능)
- `main.py` lifespan + `entrypoint.sh`에서 `alembic upgrade head` 자동 실행
- `scripts/migrate_sqlite_data.py` 신규: 기존 6개 DB → app.db 데이터 이관 스크립트
- cache.db, screener_cache.db는 raw SQLite 유지 (ORM 이점 없는 TTL 캐시)
- services/, routers/, frontend/ 변경 없음

## 2026-04-04 — 계량지표 확장 + 포워드차트 + 매출추정 개선

### 기본적분석 개선
- 계량지표 8개→10개 확장: EPS + 안전마진가격(Graham Number) 추가 (MarginAnalyst 자문)
- MetricCard integer prop: 부채/자본, 유동비율, EPS, 안전마진가격 소수점 제거
- 프론트엔드 "Graham" 표기 → "안전마진/안전마진가격"으로 통일 (백엔드 키명 유지)
- ForwardEstimatesSection: 매출/순이익 현재E+차기E sub 텍스트 추가
- IncomeChart: 추정치 연도(xxE) 반투명 바 추가 (매출E+순이익E, opacity 0.35)

### 버그 수정
- fetch_market_metrics()에 shares 필드 누락 → Graham Number 계산 불가 수정
- 매출 추정치 수집 3단계 fallback: revenue_estimate(신API) → analysis(레거시) → totalRevenue×growth

## 2026-04-04 — 성능 최적화 리팩토링 (DB 캐시 + 병렬화)

### 성능 최적화
- `stock/stock_info_store.py` 신규: 종목 정보 영속 캐시 DB (`stock_info.db`). Docker 재시작에도 유지
- `watchlist_service.py`: stock_info DB 우선 조회 → stale 영역만 외부 API 호출 (대시보드 응답 속도 개선)
- `advisory_service.py`: `_collect_fundamental_kr/us` 5~6개 데이터 소스 ThreadPoolExecutor 병렬 수집
- `advisory_fetcher.py`: KIS 1분봉 4시간대 순차→병렬 수집 (최악 80초→20초)
- `macro_service.py`: sparkline 병렬 결과 미사용 버그 수정 (결과 버려지고 순차 재호출되던 문제)
- `dart_fin.py`: 재무 캐시 TTL 24시간→7일(168시간) 확장 (사업보고서 분기 변동 주기에 맞춤)
- `market.py`/`yf_client.py`: write-through 패턴으로 stock_info DB에 시세/지표/재무 자동 저장

### DB 인덱스 추가
- `order_store.py`: orders 테이블에 status, order_no+market, symbol+market 인덱스 3개 추가
- `advisory_store.py`: advisory_reports 테이블에 code+market+generated_at 인덱스 추가

### 프론트엔드 최적화
- `OrderPage.jsx`: 탭/마켓 전환 useEffect 분리 — market 변경 시 현재 활성 탭만 리로드

## 2026-04-04 — 메뉴바 드롭다운 + 대시보드 재설계 + doc-commit 스킬

### UI 개선
- Header.jsx: 9개 평면 메뉴 → 5개 드롭다운 (포트폴리오|분석▼(매크로/스크리너/공시)|관심종목|매매▼(주문/잔고)|시세판)
- 드롭다운 hover 영역: `mt-1` gap → `pt-1` 투명 패딩으로 마우스 이탈 방지
- DashboardPage.jsx: 포트폴리오 요약(체제배너+자산현황+배분차트) + 오늘 공시로 재설계

### 스킬 신규
- `.claude/skills/doc-commit/`: 문서 반영 + 커밋 + compact 자동화 스킬

---

## 2026-04-04 — AI자문 프롬프트 고도화 + 포트폴리오 통합 + 버그 수정

### AI자문 프롬프트 고도화 (도메인 전문가 3명 자문)
- `advisory_service.py` 시스템 프롬프트: 재무 건전성 체크리스트, 적자 기업 규칙, PBR 역산 한계, 업종 상대평가, 체제별 투자 원칙 동적 삽입
- `advisory_service.py` 유저 프롬프트: `## 매크로 환경` 섹션 추가 (VIX/버핏/공포탐욕/체제/요구 안전마진)
- `advisory_service.py` 출력: `포지션가이드` 섹션 추가 (진입가/손절가/익절가/R:R/분할매수)
- `portfolio_advisor_service.py`: `_SYSTEM_PROMPT` → `_build_system_prompt(regime, cash_pct)` 함수화
  - 포지션 사이징 규칙 (단일 5%, 1회 30%, 현금 체제별), 손실 종목 3단계, urgency 3단계
  - 체제별 현금 비중 동적 삽입 (accumulation 25%/selective 35%/cautious 50%/defensive 75%)
  - trades JSON 확장: stop_loss, position_pct, urgency_reason
- `AIReportPanel.jsx`: 포지션가이드 4카드 섹션 (PosGuideCard 컴포넌트)
- `TradeTable.jsx`: 손절가/비중/긴급도 근거 컬럼 추가 (하위 호환)

### "AI자문" + "포트폴리오" 메뉴 통합
- `PortfolioPage.jsx` 재작성: 매크로 배너 + 자산 요약 + 차트 + AdvisorPanel(진단+리밸런싱+매매안) 통합
- `AdvisorPage.jsx` 라우트 제거 (App.jsx, Header.jsx)
- `BalancePage.jsx`: AdvisorPanel 제거 → "포트폴리오에서 AI 자문 보기 →" 링크
- Header: "AI자문" 메뉴 제거 (9개 메뉴)

### usePortfolioAdvisor 훅 재설계 (stale closure 버그 수정)
- `loadHistory()`: `[result]` 의존성 제거 → 이력 목록만 가져옴 (자동 리포트 로드 제거)
- `loadLatest()`: 마운트 시 최신 리포트 자동 로드 (신규)
- `analyze()`: `setResult(res)` 후 `loadHistory()` fire-and-forget (await 제거, 덮어쓰기 방지)

### max_completion_tokens 부족 버그 수정
- `advisory_service.py` + `portfolio_advisor_service.py`: 3500 → 8000
- 토큰 제한 잘림 감지 (`finish_reason == "length"` 로깅)
- JSON 파싱 실패 시 `ExternalAPIError` 반환 (빈 화면 대신 에러 메시지)
- `AdvisorPanel.jsx`: `analysis.raw` 존재 시 "다시 시도" 안내 표시

### 기타 버그 수정
- `cache.py`: aware/naive datetime 비교 TypeError → `.replace(tzinfo=None)` 통일
- `RegimeBanner.jsx`: `sentiment.buffett` → `sentiment.buffett_indicator` 필드명 수정
- `RegimeBanner.jsx`: `fg?.value` → `fg?.score` 우선 (실제 백엔드 필드)
- `TradeTable.jsx`: 매매근거 `truncate` 제거 → `whitespace-pre-line` 전체 표시
- `AdvisorPanel.jsx`: 링크 `/advisor` → `/portfolio`

---

## 2026-04-03 — 포트폴리오 대시보드

### 포트폴리오 대시보드 (`/portfolio`) 신규
- `PortfolioPage.jsx` — 5개 섹션 대시보드 (매크로 배너 + 자산 요약 + 배분 차트 + 수익률 바 + 보유종목)
- `usePortfolio.js` — balance + macro sentiment 병렬 로드 + Graham 안전마진 등급 프론트 계산
- `RegimeBanner.jsx` — 공포탐욕지수 기반 매크로 체제 배너 (공포/신중/중립/탐욕 4단계)
- `AllocationChart.jsx` — Recharts PieChart 자산 배분 (국내/해외/현금)
- `ProfitChart.jsx` — Recharts BarChart 종목별 수익률 비교
- `HoldingsOverview.jsx` — 보유 종목 테이블 + 안전마진 등급(A~D) + PER/PBR/ROE
- 신규 백엔드 없음 — 기존 `/api/balance` + `/api/macro/sentiment` API 100% 재활용
- Header 메뉴 추가 (10개)

---

## 2026-04-03 — AI 포트폴리오 자문 + 인프라 개선

### AI 포트폴리오 자문 기능 신규
- `services/portfolio_advisor_service.py` — 잔고 데이터 기반 GPT 포트폴리오 분석 (진단/리밸런싱/매매안)
- `routers/portfolio_advisor.py` — `POST /analyze`, `GET /history`, `GET /history/{id}` 3개 엔드포인트
- `stock/advisory_store.py` — `portfolio_reports` 테이블 추가 (자문 이력 영구 저장)
- `config.py` — `ADVISOR_CACHE_TTL_HOURS` 환경변수 (기본 0.5=30분)
- `stock/cache.py` — `ttl_hours` 타입 `int → float` (30분 TTL 지원)
- 프론트엔드: `AdvisorPage`(/advisor) + `AdvisorPanel`/`DiagnosisCard`/`RebalanceCard`/`TradeTable`/`TradeConfirmModal` 5개 컴포넌트
- `BalancePage` 하단에 AdvisorPanel 통합 + "AI자문 페이지에서 이력 보기" 링크
- 페이지 진입 시 최신 리포트 자동 로드 (이력 있으면 버튼 클릭 불필요)
- Header에 "AI자문" 메뉴 추가 (9개 메뉴)

### KST 타임존 통일
- `stock/db_base.py` — `KST`, `now_kst()`, `now_kst_iso()` 공용 헬퍼 신규
- `stock/cache.py` — `datetime.utcnow()` → `now_kst()` (캐시 만료 비교/저장)
- `stock/order_store.py` — `_now()` → `now_kst_iso()`
- `stock/advisory_store.py` — `datetime.now()` 4곳 → `now_kst_iso()`
- `stock/macro_store.py` — 자체 `_KST` 상수 제거, `db_base.KST` 공용 사용
- `services/macro_service.py` — `datetime.now(timezone.utc)` → `now_kst_iso()`
- `services/portfolio_advisor_service.py` — `datetime.now()` → `now_kst_iso()`
- 프론트: `EarningsPage`/`WatchlistDashboard` — `.toISOString()` → 로컬 날짜 헬퍼

### 관심종목 대시보드 속도 개선
- `services/watchlist_service.py` — 순차 for 루프 → `ThreadPoolExecutor` 병렬 (max 10 workers)
- `_fetch_dashboard_row()` 함수 추출, `time.sleep(0.05)` 제거
- 10종목 기준 12-30초 → 2-4초로 단축

### 기타
- `TradeTable` 매매근거 텍스트 잘림 수정 (`truncate` → `whitespace-pre-line`)
- `AdvisorPage` 불필요한 "잔고 새로고침" 버튼 제거

---

## 2026-04-03 — 시스템 리팩토링

### 시스템 리팩토링 (2026-04-03)

**HIGH (5건)**
- H1: `search.js`/`marketBoard.js` → `apiFetch()` 경유로 에러 처리 통일
- H2: `useAsyncState` 공통 훅 추출, 15개 훅 보일러플레이트 제거
- H3: `order_service.py`(1,338줄) → 4파일 분할 (order_service + order_kr/us/fno). Write-Ahead 패턴 dispatcher 중앙화
- H4: `quote_service.py`(964줄) → 3파일 분할 (quote_service + quote_kis + quote_overseas)
- H5: KIS 토큰 캐시 3곳 → `_kis_auth.py` 단일화 + TTL 관리

**MEDIUM (3건)**
- M2: `watchlist_service.py` silent `except: pass` 7건 → `logger.debug` 전환
- M5: 라우터 HTTPException 22건 → ServiceError 계층 통일. `ConflictError(409)` 신규
- M6: `advisory_fetcher.py` 기술지표 8개 순수 함수 → `stock/indicators.py` 분리

**LOW (1건)**
- L4: 미사용 import 정리 (Optional, math 등)

---

## 2026-04-03 — AI 에이전트 팀 (하네스) 구성

### 에이전트 7명 (`.claude/agents/`)

**도메인 전문가 4명:**
- `macro-sentinel.md` — 매크로 환경 분석 (버핏지수/VIX/공포탐욕 → 시장 체제 판단)
- `value-screener.md` — Graham 기준 PER/PBR/ROE 동적 필터 스크리닝
- `margin-analyst.md` — Graham Number + 재무 건전성 + 기술적 타이밍 심층 분석
- `order-advisor.md` — 포지션 사이징 + 지정가/손절/익절 주문 추천 (자동 주문 금지)

**빌더 3명:**
- `dev-architect.md` — 통합자산관리 풀스택 개발 (도메인 전문가 자문 기반)
- `qa-inspector.md` — 경계면 교차 비교 통합 정합성 검증
- `refactor-engineer.md` — 도메인 인지 리팩토링 (도메인 전문가 확인 후 변경)

### 스킬 9개 (`.claude/skills/`)
- `macro-analysis/` — MacroSentinel 전용: 매크로 데이터 수집 + 체제 판단
- `value-screening/` — ValueScreener 전용: Graham 멀티팩터 스크리닝
- `graham-analysis/` — MarginAnalyst 전용: 내재가치 + 재무 건전성 + 기술적 분석
- `portfolio-check/` — OrderAdvisor 전용: 포트폴리오 상태 + 포지션 사이징
- `order-recommend/` — OrderAdvisor 전용: 주문 추천 생성 + 예약주문 보조
- `value-invest/` — 오케스트레이터: 분석 파이프라인 (Macro→Screener→Analyst→Advisor)
- `asset-dev/` — 오케스트레이터: 개발 파이프라인 (자문→설계→구현→QA→보고)
- `qa-verify/` — QA Inspector 전용: 교차 비교 검증 체크리스트
- `refactor-audit/` — 오케스트레이터: 리팩토링 파이프라인 (감사→자문→실행→QA)

### 특징
- 기존 서비스 코드 변경 없음 — 에이전트는 기존 API 엔드포인트를 HTTP로 호출
- 도메인 전문가 4명이 분석/개발/리팩토링 3개 파이프라인 모두에서 자문 역할
- 워크스페이스 산출물: `_workspace/` 디렉토리에 단계별 JSON 파일 저장

---

## 2026-04-01 — 매크로 분석 페이지 신규

### 매크로 분석 (Macro Analysis) 메뉴 추가
- `stock/macro_fetcher.py`: yfinance 지수(KOSPI/KOSDAQ/S&P500/NASDAQ), RSS 뉴스, VIX/버핏지수/공포탐욕 심리지표, Google News 투자자 코멘트
- `services/macro_service.py`: 병렬 수집(ThreadPoolExecutor) + GPT 번역/추출 + 캐싱 오케스트레이션
- `routers/macro.py`: 5개 GET 엔드포인트 (`/api/macro/indices|news|sentiment|investor-quotes|summary`)
- `main.py`: macro 라우터 등록
- `requirements.txt`: `feedparser` 추가 (RSS 파싱)
- 프론트엔드: MacroPage + IndexSection(1년 스파크라인+툴팁) + SentimentSection + NewsSection + InvestorSection
- 데이터 소스: yfinance(지수/VIX/버핏), Google News RSS(한국 뉴스), NYT RSS + GPT 번역, Google News + GPT 추출(투자자 코멘트)
- 새 API 키 불필요 (기존 OPENAI_API_KEY만 활용, 없으면 영문 표시 graceful degradation)

---

## 2026-03-30 — FNO 캐싱 + 예약주문 수정 + DnD 순서변경

### FNO 마스터 인메모리 캐싱
- `stock/fno_master.py`: 인메모리 캐시(24h TTL) → cache.db(7일) → ZIP 다운로드 3단계 캐싱
- `main.py` lifespan: FNO pre-warm 추가 (기존 symbol_map 스레드에 병합)

### 예약주문 국내 시세 버그 수정
- `services/reservation_service.py`: `_fetch_current_price()` pykrx → `stock.market.fetch_price()` 교체
- pykrx KRX 서버 변경(2026-02-27) 이후 국내 가격조건 예약주문이 실패하던 문제 해결

### 시세판 드래그앤드롭 순서 변경
- `stock/market_board_store.py`: `market_board_order` 테이블 + `get_order()`/`save_order()`
- `routers/market_board.py`: `GET/PUT /api/market-board/order`
- 프론트엔드: `@dnd-kit/core` + `@dnd-kit/sortable` — 카드 그리드 DnD (`rectSortingStrategy`)
- `useDisplayStocks()`: orderMap 기반 정렬 + `reorder()` 낙관적 업데이트

### 관심종목 드래그앤드롭 순서 변경
- `stock/store.py`: `watchlist_order` 테이블 + `get_order()`/`save_order()`
- `routers/watchlist.py`: `GET/PUT /api/watchlist/order`
- 프론트엔드: 테이블 행 DnD (`verticalListSortingStrategy`) + 드래그 핸들(⠿)
- `useDashboard()`: orderMap 기반 정렬 + `reorder()` 낙관적 업데이트

---

## 시세 수신 개선 이력 (Phase 1 → Phase 4)

### Phase 1 (2026-03 완료)
- rAF throttle (`useQuote.js`): 고빈도 WS 메시지 → 최대 60fps 렌더링
- OrderbookPanel `useMemo` + `memo`: asks/bids/maxVolume 재계산 방지
- 지수 백오프 재연결 (클라이언트 500ms→10초, KIS WS 1→30초)
- `visibilitychange` 탭 복귀 즉시 재연결
- `OverseasQuoteManager`: 심볼당 단일 yfinance 폴링 태스크 (N 클라이언트 → 1 호출)
- 100ms 메시지 병합: 국내 WS 고빈도 메시지 → 최대 10건/초
- 장중/장외 TTL 분리 (`stock/market.py`): 국내 `fetch_price` 6분/6시간, `fetch_market_metrics` 1시간/12시간

### Phase 2 (2026-03 완료)
- `_is_us_trading_hours()` (`stock/market.py`): DST 자동 반영 (zoneinfo)
- `stock/yf_client.py` 장중 TTL 분리: `fetch_price_yf` 2분/30분, `fetch_detail_yf` 30분/6시간, `fetch_metrics_yf` 30분/6시간, `fetch_period_returns_yf` 15분/6시간
- **KIS REST fallback** (`KISQuoteManager`): WS 끊김 시 `FHKST01010100` 5초 폴링 자동 전환, WS 재연결 시 자동 해제. `_rest_fallback_loop()` + `_fetch_rest_price()`. 심볼 간 0.2초 throttle.
- **Finnhub WS** (`FinnhubWSClient` + `OverseasQuoteManager`): `FINNHUB_API_KEY` 설정 시 해외주식 실시간 체결가 수신 (무료 플랜 30 심볼). 한도 초과 심볼은 yfinance 폴링 fallback. 전일종가 prefetch로 change 계산.

### 환경변수 추가
- `FINNHUB_API_KEY`: 해외주식 실시간 시세 (선택). 미설정 시 yfinance 2초 폴링(15분 지연) 유지.

### Phase 3 (2026-03 완료)
- **신고가/신저가 그리드 밀도 개선** (`NewHighLowSection.jsx`): `md:grid-cols-4`, `lg:grid-cols-3` 추가. 외부 2컬럼 래퍼 안에서도 충분한 카드 밀도 확보.
- **비개장일 국내 시세 fallback** (`KISQuoteManager`): `subscribe()` 호출 즉시 `asyncio.create_task(_push_initial_price())` — yfinance `fetch_price(symbol)`로 직전 거래일 가격 queue push. `_fetch_rest_price()` KIS 반환 `price=0` 시 yfinance fallback.
- **비개장일 해외 시세 fallback** (`OverseasQuoteManager`): `_prefetch_and_subscribe()`에서 `fi.last_price or fi.previous_close` 패턴. `_poll_loop()`도 동일 패턴 적용, p=None이면 broadcast skip.
- **`fetch_price_yf()` fallback** (`stock/yf_client.py`): `close = _safe(fi.last_price) or _safe(fi.previous_close)` — 관심종목·잔고·AI자문용 해외 시세도 비개장일 직전 종가 반환.
- **FNO 실시간 WebSocket** (`KISQuoteManager` + `routers/quote.py`): FNO 심볼에 KIS WS 실시간 호가 지원 추가. `_FNO_TR_IDS` 상수 딕셔너리 + `_resolve_fno_type(symbol)` + `_send_subscribe_fno()`. `routers/quote.py`에 `?market=FNO` 쿼리 파라미터 추가 → `_stream_fno()` 핸들러로 분기. `useQuote(symbol, market='KR')` 시그니처 변경으로 프론트엔드 market 전달.
- **FNO 주문유형 확장** (`OrderForm.jsx`): 지정가만 지원하던 FNO 주문을 지정가/시장가/조건부지정가/최유리지정가 + IOC/FOK 조건으로 확장. `mapFnoOrderCodes()` 함수로 `ORD_DVSN_CD` 자동 계산. `OrderbookPanel`에서 FNO REST 폴링 제거 → `useQuote` 훅으로 통합.
- **`stock/utils.py` `is_fno(code)` 추가**: FNO 단축코드 식별 함수 추가.

### Phase 4 — 구조 개선 + WS 효율화 (2026-03 완료)
- **주문 도메인 계층 분리**: `routers/order.py`에서 `order_store` 직접 import 완전 제거. 이력 조회·예약주문·FNO 시세 모두 `order_service` 경유. 예약주문 `create_reservation()` 도메인 규칙 검증 추가.
- **주문 즉시 동기화**: `cancel_order()` → 로컬 DB 즉시 CANCELLED + `local_synced`/`order_status` 응답. `modify_order()` → 가격/수량 즉시 반영 + `local_synced`. `place_order()` → `balance_stale: true`.
- **대사 로직 강화**: `sync_orders()` → 체결+미체결 양쪽 조회, 양쪽 다 없으면 CANCELLED 자동 감지. `get_order_history()` 반환 전 자동 대사(best-effort).
- **SQLite WAL 모드**: `db_base.py`, `cache.py` — `PRAGMA journal_mode=WAL` + timeout 10초. 읽기-쓰기 동시성 향상.
- **예외 통일**: `_kis_auth.py`, `balance.py` — `HTTPException` → `ConfigError`/`ExternalAPIError` (ServiceError 계층 통일).
- **프론트엔드 계층 분리**: `MarketBoardPage.jsx` — api/ 직접 import 제거 → `useDisplayStocks()` 훅 사용.
- **Approval Key TTL**: `_get_approval_key()` — 12시간 TTL, 만료 시 자동 재발급.
- **REST Token TTL**: `_get_rest_token_sync()` — 12시간 TTL, 동일 패턴.
- **REST Fallback 최적화**: 폴링 주기 5초→3초, 심볼 간 throttle 0.2초→0.1초.
- **FNO 타입 캐싱**: `_fetch_fno_rest_price_sync()`에서 `_fno_types` dict 캐시 미스 시 결과 저장.
- **Queue Overflow 로깅**: `_broadcast()`에서 큐 만재 시 100건마다 경고 로그.
- **시세판 배칭 단축**: `market_board.py` — 500ms→200ms (호가 100ms와의 격차 축소).

---

## 버그 수정

### DART 공시 캐시 버그 수정 (2026-03)
- **원인**: `screener/cache.py`는 TTL 없는 영구 캐시. 당일 오전 조회 시 빈 결과가 캐시되면 이후 제출 공시가 보이지 않음 (골프존 3/19 사업보고서 미노출 사례)
- **수정**: `screener/dart.py`의 `fetch_filings()`에서 `end_date < today`인 경우만 캐시 사용. 오늘 이상 날짜 포함 범위는 항상 DART API 직접 호출.
