# services/ 레이어

`stock/` 패키지의 데이터 수집 함수들을 조합하여 웹 API용 데이터를 조립하는 서비스 레이어.

---

## 모듈 구성

| 파일 | 클래스/역할 |
|------|------------|
| `exceptions.py` | 서비스 레이어 공용 예외 계층 (FastAPI HTTPException 의존 제거) |
| `watchlist_service.py` | `WatchlistService` — 관심종목 대시보드 + 상세 조회 |
| `detail_service.py` | `DetailService` — 종목 상세 분석 (재무/밸류에이션/리포트) |
| `quote_service.py` | 실시간 시세 공개 API 진입점 (싱글턴 `get_manager`/`get_overseas_manager`) |
| `quote_kis.py` | KIS WebSocket 단일 연결 + 심볼별 pub/sub (국내+FNO) + 체결통보(H0STCNI0) |
| `quote_overseas.py` | 해외주식 시세 (Finnhub WS 또는 yfinance 2초 폴링) |
| `advisory_service.py` | 자문종목 데이터 수집 + OpenAI 리포트 생성 |
| `order_service.py` | 주문 오케스트레이션 + Write-Ahead 패턴 + 대사(Reconciliation). 시장별 실행은 order_kr/us/fno에 위임. |
| `order_kr.py` | 국내주식 KIS API 주문 실행 (발주/조회/정정/취소) |
| `order_us.py` | 해외주식 KIS API 주문 실행 |
| `order_fno.py` | 선물옵션 KIS API 주문 실행 |

---

## `exceptions.py` — 서비스 레이어 예외 계층

서비스 레이어가 FastAPI `HTTPException`을 직접 raise하지 않도록 분리한 예외 계층.
`main.py`에서 `@app.exception_handler(ServiceError)`로 일괄 HTTP 응답 변환.

```python
class ServiceError(Exception):
    """기본 서비스 예외. status_code + message."""
    def __init__(self, message: str, status_code: int = 400): ...

class NotFoundError(ServiceError): ...      # 404
class ExternalAPIError(ServiceError): ...   # 502
class ConfigError(ServiceError): ...        # 503
class PaymentRequiredError(ServiceError):... # 402
class ConflictError(ServiceError): ...      # 409
```

| 예외 | HTTP | 사용 예 |
|------|------|---------|
| `NotFoundError` | 404 | 캐시/리포트 없음 |
| `ExternalAPIError` | 502 | KIS·OpenAI API 오류 |
| `ConfigError` | 503 | API 키 미설정 |
| `PaymentRequiredError` | 402 | OpenAI 크레딧 부족(429) |
| `ConflictError` | 409 | 리소스 중복 (예: 관심종목/시세판 종목 중복 등록) |

---

## `watchlist_service.py` — WatchlistService

`routers/watchlist.py`에서 사용. `stock/` 패키지(pykrx + OpenDart)를 조합해 데이터를 조립한다.

### 생성자

```python
WatchlistService(broker=None)
```

- `broker`: `KoreaInvestment` 인스턴스 (선택). 현재 미사용, pykrx로 대체.

### 메서드

#### `resolve_symbol(name_or_code) → (code, name)`

종목명 또는 코드를 정규화한다. `symbol_map.resolve()`를 사용.

- 단일 매칭: `(code, name)` 반환
- 복수 매칭: `ValueError` (후보 목록 포함)
- 매칭 없음: `ValueError`

#### `get_dashboard_data(items) → list[dict]`

관심종목 목록을 받아 시세 + 재무 + 배당 데이터를 조합한 대시보드 행 리스트를 반환한다.

반환 필드:

| 필드 | 타입 | 단위 | 설명 |
|------|------|------|------|
| `code` | str | | 종목코드 |
| `name` | str | | 종목명 |
| `memo` | str | | 메모 |
| `currency` | str | | `"KRW"` 또는 `"USD"` |
| `price` | int \| None | 원/달러 | 현재가 |
| `change` | int \| None | 원/달러 | 전일대비 |
| `change_pct` | float \| None | % | 등락률 |
| `market_cap` | int \| None | 억원/M USD | 시가총액 |
| `revenue` | int \| None | 억원/M USD | 매출액 |
| `operating_profit` | int \| None | 억원/M USD | 영업이익 |
| `net_income` | int \| None | 억원/M USD | 당기순이익 |
| `oi_margin` | float \| None | % | 영업이익률 |
| `report_date` | str | | 보고서 기준 (예: "2024/12") |
| `dividend_yield` | float \| None | % | 배당수익률 (trailing 12개월, 무배당 시 None) |

- KR 배당수익률: `fetch_market_metrics(code)` → `dividendYield`(이미 % 형태) 우선, 없으면 `trailingAnnualDividendYield × 100` fallback
- US 배당수익률: `fetch_detail_yf(code)` → 동일 우선순위 로직
- 종목당 0.05초 sleep (rate limit)
- 개별 종목 오류는 무시하고 None 필드로 처리

#### `get_stock_detail(code) → dict`

단일 종목의 기본정보 + 최대 10개년 재무 통합 데이터.

반환 구조:

```python
{
    "basic": {
        "code": "005930",
        "price": 70000,          # 원
        "change": 1000,
        "change_pct": 1.45,
        "market_cap": 4200000,   # 억원
        "per": 12.5,
        "pbr": 1.2,
        "roe": 15.3,             # % (fetch_market_metrics, KR) / fetch_detail_yf (US)
        "dividend_yield": 2.5,   # % (무배당 시 null)
        "dividend_per_share": 1444,  # 주당배당금 원/달러 (yfinance dividendRate)
        "high_52": 80000,
        "low_52": 50000,
        "market": "KOSPI",
        "sector": "전기·전자",
        "shares": 5969782550,
    },
    "financials_3y": [           # 키 이름은 하위호환 유지 (실제 최대 10년)
        {
            "year": 2015,        # 정수
            "revenue": 2006535,  # 억원
            "operating_profit": 264134,
            "net_income": 190601,
            "oi_margin": 13.2,   # 영업이익률 % (null 가능)
            "net_margin": 9.5,   # 순이익률 % (null 가능)
            "yoy_revenue": null,
            "yoy_op": null,
            "dart_url": "https://dart.fss.or.kr/...",
        },
        ...  # 과거 → 최신 순
    ],
    "memo": "반도체 대장",
}
```

- `fetch_financials_multi_year(code, 10)` 사용 (KR), `fetch_financials_multi_year_yf(code, 4)` (US)
- KR `roe`/`dividend_yield`/`dividend_per_share`: `fetch_market_metrics(code)` 추가 호출
- US `roe`/`dividend_yield`/`dividend_per_share`: `fetch_detail_yf(code)` 에서 직접 포함
- YoY 증감률은 전년도 대비 계산 (첫 해는 null)
- `oi_margin` / `net_margin`: 서비스 레이어에서 원본값으로 계산 후 포함

---

## `detail_service.py` — DetailService

`routers/detail.py`에서 사용. 10년 재무, 밸류에이션 차트, 종합 리포트를 제공한다.

### 메서드

#### `get_financials(code, years=10) → dict`

최대 years개 사업연도 재무 데이터.

반환:
```python
{
    "code": "005930",
    "rows": [
        {
            "year": 2015,
            "revenue": 2006535,          # 억원
            "operating_profit": 264134,
            "net_income": 190601,
            "oi_margin": 13.2,           # % (None 가능)
            "yoy_revenue": null,         # 첫 해는 null
            "yoy_op": null,
            "dart_url": "https://dart.fss.or.kr/...",
        },
        ...  # 과거 → 최신 순
    ]
}
```

#### `get_valuation_chart(code, years=10) → dict`

월별 PER/PBR 히스토리 + 기간 평균.

- **국내**: `fetch_valuation_history()` (KRX 인증 필요, 미인증 시 빈 배열)
- **해외**: `yf_client.fetch_valuation_history_yf(code, min(years, 5))` — 분기 EPS/BPS + 일별 주가 조합으로 월별 PER/PBR 추정. PER > 500 이상치 제외.

반환:
```python
{
    "history": [
        {"date": "2016-02", "per": 7.69, "pbr": 1.24},
        ...
    ],
    "avg_per": 15.2,    # PER > 500 이상치 제외
    "avg_pbr": 1.62,
    "note": "분기 EPS/BPS + 일별 주가 추정",  # 해외주식만, 데이터 있을 때
}
```

#### `get_report(code, years=10) → dict`

재무 + 밸류에이션 + 기본 시세 + 종합 요약 통합.

반환:
```python
{
    "basic": { ... },        # 시세 + 종목 기본정보
    "financials": { ... },   # get_financials() 결과
    "valuation": { ... },    # get_valuation_chart() 결과
    "summary": {
        "rev_cagr": 4.6,     # 매출 연평균 성장률 (%)
        "op_cagr": 2.4,      # 영업이익 CAGR
        "net_cagr": 6.8,     # 순이익 CAGR
        "current_per": 12.5,
        "current_pbr": 1.2,
        "avg_per": 15.2,
        "avg_pbr": 1.62,
        "per_vs_avg": -17.8, # 평균 대비 % (음수 = 저평가)
        "pbr_vs_avg": -25.9,
        "years": 10,
        "year_start": 2015,
        "year_end": 2024,
    },
    "forward_estimates": {   # 애널리스트 컨센서스 추정치 (없으면 {})
        "eps_current_year": 6.5,
        "eps_forward": 7.2,
        "forward_pe": 22.1,
        "revenue_current": 2500000,     # 억원(KR) 또는 M USD(US)
        "revenue_forward": 2700000,
        "net_income_estimate": 150000,
        "net_income_forward": 170000,
        "target_mean_price": 85000,
        "target_high_price": 95000,
        "target_low_price": 70000,
        "num_analysts": 12,
        "recommendation": "buy",
        "current_fiscal_year_end": "2025-12",
    },
}
```

---

## 공통 헬퍼 함수

두 서비스 모듈 모두 동일한 유틸리티 함수를 내부에 정의한다:

| 함수 | 설명 |
|------|------|
| `_awk(won)` | 원 → 억원 변환 (반올림 int). None 안전. |
| `_growth(cur, prev)` | 전년대비 증감률 (%). prev=0이면 None. |
| `_cagr(start, end, n)` | CAGR 계산. 음수/0 시작값이면 None. (detail_service만) |

---

## 데이터 흐름

```
[pykrx]  ─── fetch_price() ────────┐
[pykrx]  ─── fetch_detail() ───────┤
[pykrx]  ─── fetch_valuation_history() ──┤
                                    ├──→ WatchlistService / DetailService
[DART]   ─── fetch_financials() ───┤
[DART]   ─── fetch_financials_multi_year() ──┤
                                    │
[store]  ─── get_item() ───────────┘
[symbol_map] ─── resolve() ────────┘
```

- 모든 데이터 수집 함수는 `stock/cache.py` 또는 `screener/cache.py`로 캐싱됨
- 서비스 레이어는 캐시를 직접 관리하지 않음 (하위 모듈에 위임)

---

## `order_service.py` — 주문 서비스

`routers/order.py`의 **유일한 의존 대상**. KIS REST API 직접 호출 + 로컬 `orders.db` 기록 + 대사 로직 + 예약주문 관리 + FNO 시세. 라우터에서 `order_store` 직접 접근은 금지됨 (계층 분리).

### 주요 함수

| 함수 | 설명 |
|------|------|
| `place_order(symbol, symbol_name, market, side, order_type, price, quantity, memo)` | 국내/해외/FNO 주문 발송. KIS API 호출 후 로컬 DB에 PLACED 상태로 기록. |
| `get_buyable(symbol, market, price, order_type, side)` | 매수가능 금액/수량 조회 (국내: `TTTC8908R`, 해외: `TTTS3007R`, FNO: `TTTO5105R`). |
| `get_open_orders(market)` | 미체결 주문 목록 (국내: `TTTC8036R`, 해외: `TTTS3018R`, FNO: `TTTO5201R`). `api_cancellable` 필드 포함. |
| `modify_order(order_no, org_no, market, ...)` | 주문 정정. **KIS 성공 후 로컬 DB 가격/수량 즉시 반영**. 응답에 `local_synced: true`. |
| `cancel_order(order_no, org_no, market, ...)` | 주문 취소. **KIS 성공 후 로컬 DB 즉시 CANCELLED 갱신**. 응답에 `local_synced: true`, `order_status: "CANCELLED"`. |
| `get_executions(market)` | 당일 체결 내역 (국내: `TTTC8001R`, 해외: `JTTT3001R`, FNO: `TTTO5201R`). |
| `sync_orders()` | 로컬 PLACED/PARTIAL 주문을 KIS **체결+미체결** 양쪽과 대사. 양쪽 다 없으면 CANCELLED 자동 감지. |
| `get_order_history(symbol, market, status, date_from, date_to, limit)` | 이력 조회. **반환 전 `_reconcile_active_orders()` 자동 대사(best-effort)**. 기간 필터 검증. |
| `get_fno_price(symbol, mrkt_div)` | 선물옵션 현재가 조회 (FHMIF10000000 REST). |
| `create_reservation(symbol, ..., condition_type, condition_value)` | 예약주문 등록. **도메인 규칙 검증**: condition_type 유효성, ISO datetime/양수 float, quantity>0, price>=0. |
| `get_reservations(status)` | 예약주문 목록 조회. |
| `delete_reservation(res_id)` | 예약주문 삭제 (WAITING만). |

### 내부 헬퍼

| 함수 | 설명 |
|------|------|
| `_reconcile_active_orders()` | 활성 주문(PLACED/PARTIAL)을 KIS 체결+미체결 양쪽 조회하여 대사. 양쪽 다 없으면 CANCELLED 자동 감지. |
| `_sync_local_order_status(order_no, market, status)` | 로컬 DB에서 주문 찾아 상태 갱신 (best-effort). |
| `_sync_local_order_details(order_no, market, price, quantity)` | 로컬 DB에서 주문 찾아 가격/수량 갱신 (best-effort). |

### 주요 설계 결정

**주문번호 포맷 (`_strip_leading_zeros`)**

`TTTC8036R` 미체결 조회는 `odno` 필드를 10자리 제로패딩(`0039822900`)으로 반환하지만,
`TTTC0803U` 정정/취소 API는 `ORGN_ODNO`에 8자리(`39822900`)를 요구한다.
`_strip_leading_zeros(order_no)` 함수로 자동 변환한다.

**채널 구분 (`api_cancellable`)**

KIS는 주문 채널(API/HTS/MTS)별로 접근을 분리한다:
- `TTTC8036R` (미체결 조회): 모든 채널 주문 반환
- `TTTC0803U` (취소/정정): **동일 채널(API)로 발주한 주문만** 처리 가능
- `excg_id_dvsn_cd: 'KRX'` → API 발주 → 취소 가능
- `excg_id_dvsn_cd: 'SOR'` → HTS/MTS(Smart Order Routing) 발주 → API 취소 불가 (APBK0344 오류)

`api_cancellable = (excg_id != "SOR")` 조건으로 프론트엔드에 전달.

---

---

## `quote_service.py` — KISQuoteManager + OverseasQuoteManager

`routers/quote.py`에서 사용. 국내/FNO는 KIS WebSocket 단일 연결, 해외는 Finnhub WS 또는 yfinance 폴링으로 심볼별 `asyncio.Queue` pub/sub 브로드캐스트.

### 싱글턴 접근

```python
from services.quote_service import get_manager, get_overseas_manager
manager = get_manager()                   # KISQuoteManager (국내)
overseas = get_overseas_manager()         # OverseasQuoteManager (해외)
```

### KISQuoteManager — 생명주기

```python
await manager.start()   # FastAPI lifespan startup
await manager.stop()    # FastAPI lifespan shutdown
```

- KIS 키(`KIS_APP_KEY`/`KIS_APP_SECRET`) 미설정 시 `start()`에서 경고 후 즉시 반환 (비활성화)
- WS 오류 시 지수 백오프 재연결 (1초 → 최대 30초). 재연결 성공 시 리셋.
- WS 끊김 시 `{"type": "disconnected"}` 브로드캐스트 → 클라이언트 즉시 인식
- WS 끊김 시 **REST fallback 자동 시작** (`FHKST01010100` 3초 폴링, 심볼 간 0.1초 throttle)
- WS 재연결 성공 시 REST fallback 자동 종료
- **Approval key 12시간 TTL**: 만료 시 자동 재발급. WS 재연결 시 TTL도 초기화.
- **REST token 12시간 TTL**: `_get_rest_token_sync()` — 동일 패턴.
- **Queue overflow 로깅**: `_broadcast()`에서 큐 만재 시 100건마다 경고 로그 (로그 폭발 방지).
- **FNO 타입 캐싱**: `_fno_types` dict에 `_resolve_fno_type()` 결과 저장 → 반복 SQLite 조회 방지.

### KISQuoteManager — pub/sub API

```python
await manager.subscribe(symbol, queue, is_fno=False)  # asyncio.Queue 등록 (최대 100 메시지 버퍼). is_fno=True 시 FNO WS TR_ID 사용.
manager.unsubscribe(symbol, queue)                    # Queue 제거. 마지막 구독자 해제 시 심볼도 제거.
```

- Queue Full 시 오래된 메시지 제거 후 새 메시지 삽입 (느린 클라이언트 대응). 100건마다 경고 로그.
- 동일 심볼에 여러 큐 등록 가능 (브라우저 탭 여러 개)
- `is_fno=True`: `_send_subscribe_fno(symbol)` 호출 → `_resolve_fno_type(symbol)`로 TR_ID 자동 결정

### KISQuoteManager — 비개장일 초기 가격 push (`_push_initial_price`)

`subscribe()` 호출 즉시 `asyncio.create_task`로 비동기 실행. 비개장일(주말/공휴일)에도 직전 거래일 가격이 즉시 표시됨.

- `stock.market.fetch_price(symbol)` (yfinance 기반) 호출 — 항상 마지막 알려진 가격 반환
- queue에 `{"type": "price", "price": ..., "sign": "3", "change_rate": ...}` push
- 이후 KIS WS 체결가가 도착하면 자동으로 overwrite됨 (개장일 정상 동작)

### KISQuoteManager — REST fallback (`_rest_fallback_loop`)

WS 연결 끊김 감지 시 자동으로 KIS REST API를 폴링합니다.

| 항목 | 내용 |
|------|------|
| TR_ID | `FHKST01010100` |
| 경로 | `GET /uapi/domestic-stock/v1/quotations/inquire-price` |
| 폴링 주기 | 5초 (심볼 간 0.2초 간격으로 throttle) |
| 응답 필드 | `stck_prpr`(현재가), `prdy_vrss_sign`(부호), `prdy_vrss`(전일대비), `prdy_ctrt`(대비율) |
| 비개장일 | KIS 반환 `price=0` 시 `stock.market.fetch_price(symbol)` yfinance fallback으로 직전 종가 반환 |
| 토큰 관리 | `_get_rest_token_sync()` 모듈 레벨 캐시. 401 응답 시 자동 갱신. |
| 종료 조건 | WS 재연결 성공 시 `_fallback_mode = False` → 루프 자연 종료 |

### KISQuoteManager — KIS 메시지 파싱

#### `_parse_execution(raw)` — H0STCNT0

| 필드 | 설명 |
|------|------|
| `symbol` | 종목코드 (items[0]) |
| `price` | 현재가 (items[2]) |
| `sign` | 전일대비부호 (items[3]) — '2'=상승, '3'=보합, '5'=하락 |
| `change` | 전일대비 (items[4]) |
| `change_rate` | 전일대비율(%) (items[5]) |
| `open` | 시가 (items[7]) — `len(t) > 9`일 때만 |
| `high` | 고가 (items[8]) — `len(t) > 9`일 때만 |
| `low` | 저가 (items[9]) — `len(t) > 9`일 때만 |

#### `_parse_orderbook(raw)` — H0STASP0 (plaintext, AES 복호화 불필요)

| 필드 | 설명 |
|------|------|
| `symbol` | 종목코드 (items[0]) |
| `asks[0~9]` | 매도호가 01~10 `{price, volume}`. [0]=최우선(최저가) |
| `bids[0~9]` | 매수호가 01~10 `{price, volume}`. [0]=최우선(최고가) |
| `total_ask_volume` | 총매도잔량 (items[43]) |
| `total_bid_volume` | 총매수잔량 (items[44]) |

### KISQuoteManager — FNO WS 지원

FNO 심볼은 `subscribe(symbol, queue, is_fno=True)` 호출 시 국내 주식과 동일한 KIS WS 연결을 공유하되, FNO 전용 TR_ID를 등록한다.

#### `_resolve_fno_type(symbol)` — FNO TR_ID 결정

단축코드 첫 자리로 상품 유형을 추론한다.

| 첫 자리 | 상품 유형 | 체결 TR_ID | 호가 TR_ID | 호가 레벨 |
|---------|----------|-----------|-----------|---------|
| `1` | 지수선물 | `H0IFCNT0` | `H0IFASP0` | 5 |
| `2` | 지수옵션 | `H0IOCNT0` | `H0IOASP0` | 5 |
| `3` (선물) | 주식선물 | `H0ZFCNT0` | `H0ZFASP0` | 10 |
| `3` (옵션) | 주식옵션 | `H0ZOCNT0` | `H0ZOASP0` | 10 |

`_FNO_TR_IDS`: `{tr_id: (product_type, data_type)}` 상수 딕셔너리.
`_FNO_EXECUTION_TR_IDS`: 체결 TR_ID set (price 메시지 발행).
`_FNO_ORDERBOOK_TR_IDS`: 호가 TR_ID set (orderbook 메시지 발행).
`_FNO_5LEVEL_TR_IDS`: 5레벨 호가 TR_ID set (H0IFASP0, H0IOASP0).

#### `_parse_fno_execution(raw)` — FNO 체결

체결가 파싱. `_parse_execution(raw)`와 유사 구조. `type: "price"` 메시지 발행.

#### `_parse_fno_orderbook(raw, levels)` — FNO 호가

`levels=5`(지수) 또는 `levels=10`(주식). `type: "orderbook"` 메시지 발행. `asks`/`bids` 배열 길이가 레벨에 따라 다름.

#### `_push_initial_price_fno(symbol, queue)`

FNO `subscribe()` 즉시 `asyncio.create_task`로 실행. `_fetch_fno_rest_price_sync(symbol)` 호출 → `FHMIF10000000` REST API로 직전 가격 push. 이후 WS 체결가가 도착하면 overwrite.

---

### OverseasQuoteManager — 생명주기

```python
await overseas.start()   # FastAPI lifespan startup
await overseas.stop()    # FastAPI lifespan shutdown
```

- `FINNHUB_API_KEY` 환경변수 설정 시 Finnhub WS 활성화 (최대 30 심볼 실시간)
- 미설정 시 yfinance 2초 폴링 모드 (15분 지연)

### OverseasQuoteManager — pub/sub API

```python
await overseas.subscribe(symbol, queue)   # Queue 등록. 즉시 최신 시세 전송 (있을 경우).
overseas.unsubscribe(symbol, queue)       # Queue 제거. 구독자 0이면 폴러/WS 구독 자동 cancel.
```

### OverseasQuoteManager — Finnhub WS 모드

`FINNHUB_API_KEY` 설정 시 `FinnhubWSClient`를 내부에서 관리합니다.

| 항목 | 내용 |
|------|------|
| WS URL | `wss://ws.finnhub.io?token=<API_KEY>` |
| 무료 플랜 한도 | 30 심볼 |
| 초과 심볼 | yfinance 2초 폴링으로 자동 fallback |
| 초기 시세 | `_prefetch_and_subscribe()`: `fi.last_price or fi.previous_close` 패턴 — 비개장일에도 직전 종가 broadcast |
| 재연결 | 지수 백오프 (1→30초) |
| PINGPONG | websockets 라이브러리 `ping_interval=20, ping_timeout=10`으로 자동 처리 |

### OverseasQuoteManager — yfinance 폴링 모드

- `run_in_executor`로 블로킹 yfinance 호출을 asyncio 이벤트 루프와 분리
- **비개장일 대응**: `_poll_loop()`에서 `fi.last_price or fi.previous_close` 패턴. 둘 다 None이면 broadcast skip.
- 구독자 0이면 태스크 자동 cancel (on-demand)
- `_latest[symbol]`: 새 구독자에게 즉시 최신 시세 전송

---

## `advisory_service.py` — AI자문 서비스

`routers/advisory.py`에서 사용. `stock/advisory_fetcher.py`와 `stock/dart_fin.py`/`stock/yf_client.py`를 조합해 분석 데이터를 수집하고, OpenAI GPT-4o로 종합 리포트를 생성한다.

### 주요 함수

#### `refresh_stock_data(code, market, name) → dict`

전체 데이터 수집 → `advisory_cache` 저장 → 저장된 캐시 반환.

| 항목 | KR (국내) | US (해외) |
|------|-----------|-----------|
| 손익계산서 | `dart_fin.fetch_income_detail_annual()` (5년) | `yf_client.fetch_income_detail_yf()` (4년) |
| 대차대조표 | `dart_fin.fetch_bs_cf_annual()` (5년) | `yf_client.fetch_balance_sheet_yf()` (4년) |
| 현금흐름표 | `dart_fin.fetch_bs_cf_annual()` (5년) | `yf_client.fetch_cashflow_yf()` (4년) |
| 계량지표 | `market.fetch_market_metrics()` | `yf_client.fetch_metrics_yf()` |
| 15분봉 OHLCV | `advisory_fetcher.fetch_15min_ohlcv_kr()` | `advisory_fetcher.fetch_15min_ohlcv_us()` |
| 사업별 매출비중 | `advisory_fetcher.fetch_segments_kr()` (OpenAI 추론) | `yf_client.fetch_segments_yf()` |
| 기술적지표 | `advisory_fetcher.calc_technical_indicators()` | 동일 |
| 포워드 가이던스 | `yf_client.fetch_forward_estimates_yf(code, is_kr=True)` | `yf_client.fetch_forward_estimates_yf(code)` |

#### `generate_ai_report(code, market, name) → dict`

저장된 캐시 데이터 → OpenAI 모델 호출 → `advisory_reports` 저장.

- `OPENAI_API_KEY` 미설정 → `ConfigError` (→ HTTP 503)
- 캐시 없음 → `NotFoundError` (→ HTTP 404)
- OpenAI 크레딧 부족(429) → `PaymentRequiredError` (→ HTTP 402)
- 기타 OpenAI 오류 → `ExternalAPIError` (→ HTTP 502)

**사용 모델**: `OPENAI_MODEL` 환경변수로 설정 (기본값: `gpt-4o`). `max_completion_tokens=2500` 사용 (신규 모델 호환).

**프롬프트 구성**: 최근 3년 손익/대차/현금흐름 요약 + 계량지표 + 기술적 시그널(`current_signals`) + 포워드 가이던스(추정 EPS/매출/목표가) + **12번 증권사 컨센서스 섹션** (`_build_consensus_section()`: defensive 체제 미표시 / cautious 50% 가중 감산 경고 / KR 중앙 목표가·dispersion·momentum_signal·consensus_overheated 경고·최근 3건 요약·6개월 추이 / US 등급 변경 이력). Value Trap 6번째 규칙(consensus_overheated). 사전 계산값(grade/score/진입가/손절가) 불변.

**3전략 프레임워크**: 시스템 프롬프트에 3가지 전략을 명시하여 GPT-4o가 각 관점에서 분석.
- **변동성 돌파** (Larry Williams): K=0.3/0.5/0.7 목표가, ATR 변동성, 당일 돌파 기회
- **안전마진** (Benjamin Graham): `Graham Number = √(22.5 × EPS × BPS)`, `_calc_graham_number()` 헬퍼
- **추세추종**: MA 정배열(MA5>MA20>MA60), MACD 골든크로스, RSI 모멘텀

**KR 계량지표 계산 방식** (`_build_metrics_kr`):
- `per`, `pbr`, `roe`, `mktcap`: `fetch_market_metrics()` yfinance 값
- `psr`: mktcap / revenue (revenue는 income_stmt 최신 연도)
- `roa`: net_income / total_assets × 100 (balance_sheet 최신 연도)
- `debt_to_equity` / `current_ratio`: balance_sheet의 `debt_ratio` / `current_ratio`
- `pbr` fallback: yfinance None이면 mktcap / total_equity로 계산

**반환 JSON 구조**:
```json
{
  "종합투자의견": {"등급": "매수|중립|매도|관망", "요약": "...", "근거": ["..."]},
  "전략별평가": {
    "변동성돌파": {"신호": "매수|대기|중립", "설명": "..."},
    "안전마진": {"graham_number": 숫자|null, "현재가대비": "할인|프리미엄", "설명": "..."},
    "추세추종": {"신호": "매수|중립|매도", "설명": "..."}
  },
  "기술적시그널": {"신호": "매수|관망|매도", "해석": "...", "지표별": {"macd":"...", "rsi":"...", "stoch":"..."}},
  "리스크요인": [{"요인": "...", "설명": "..."}],
  "투자포인트": [{"포인트": "...", "설명": "..."}]
}
```

OpenAI 응답 JSON 파싱 실패 시 `raw` 필드에 원문 저장 → 프론트엔드에서 원문 텍스트로 표시.

---

## `reservation_service.py` — 예약주문 스케줄러

`main.py` lifespan에서 `asyncio` 백그라운드 태스크로 실행. `orders.db`의 `WAITING` 예약주문을 20초마다 체크.

### 주요 함수

| 함수 | 설명 |
|------|------|
| `start_scheduler()` | `asyncio.create_task`로 폴링 루프 시작. `main.py` lifespan startup에서 호출. |
| `stop_scheduler()` | 폴링 루프 종료. `main.py` lifespan shutdown에서 호출. |
| `_check_reservations()` | WAITING 예약주문 전체 조회 → 조건 체크 → 충족 시 주문 발송. |

### 조건 유형

| `condition_type` | 발동 조건 | `condition_value` |
|-----------------|----------|-------------------|
| `price_below` | 현재가 ≤ 목표가 | 숫자 문자열 (원화 또는 외화) |
| `price_above` | 현재가 ≥ 목표가 | 숫자 문자열 |
| `scheduled` | 현재 시각 ≥ 지정 시각 | ISO 8601 datetime 문자열 |

- 발동 시 `order_service.place_order()`로 자동 주문 발송
- 발동 성공: `TRIGGERED` → `EXECUTED` 상태 갱신, `result_order_no` 기록
- 발동 실패: `FAILED` 상태 갱신

---

## 에이전트 서비스 매핑

AI 에이전트 팀(`.claude/agents/`)은 `routers/` 엔드포인트를 HTTP로 호출한다. 아래는 라우터가 위임하는 서비스와 에이전트의 매핑:

| 서비스 | 에이전트 | 호출 경로 |
|--------|---------|----------|
| `macro_service.py` | MacroSentinel | `/api/macro/*` → 체제 판단용 매크로 데이터 |
| `advisory_service.py` | MarginAnalyst | `/api/advisory/*/refresh\|data\|analyze` → 기본적+기술적 분석 |
| `detail_service.py` | MarginAnalyst, ValueScreener | `/api/detail/*/report\|valuation` → 재무/CAGR/밸류에이션 |
| `order_service.py` | OrderAdvisor | `/api/order/buyable\|open\|reserve`, `/api/balance` → 포지션 사이징+주문 |
| `watchlist_service.py` | ValueScreener (fallback) | `/api/watchlist` → KRX 스크리너 불가 시 관심종목 기반 분석 |
| `reservation_service.py` | OrderAdvisor (간접) | 예약주문 등록 후 스케줄러가 자동 발동 |

### 동시성 참고

- 에이전트가 병렬로 API를 호출해도 SQLite WAL 모드 + timeout 10초로 안전
- `advisory_service.py`의 `refresh_stock_data()`는 순차 호출 권장 (DART API rate limit)
- `order_service.py`의 KIS API 호출은 토큰 분당 1회 제한 주의 (캐시 활용)
