# services/ 레이어

`stock/` 패키지의 데이터 수집 함수들을 조합하여 웹 API용 데이터를 조립하는 서비스 레이어.

---

## 모듈 구성

| 파일 | 클래스/역할 |
|------|------------|
| `watchlist_service.py` | `WatchlistService` — 관심종목 대시보드 + 상세 조회 |
| `detail_service.py` | `DetailService` — 종목 상세 분석 (재무/밸류에이션/리포트) |

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

관심종목 목록을 받아 시세 + 재무 데이터를 조합한 대시보드 행 리스트를 반환한다.

반환 필드:

| 필드 | 타입 | 단위 | 설명 |
|------|------|------|------|
| `code` | str | | 종목코드 |
| `name` | str | | 종목명 |
| `memo` | str | | 메모 |
| `price` | int \| None | 원 | 현재가 |
| `change` | int \| None | 원 | 전일대비 |
| `change_pct` | float \| None | % | 등락률 |
| `market_cap` | int \| None | 억원 | 시가총액 |
| `revenue` | int \| None | 억원 | 매출액 |
| `operating_profit` | int \| None | 억원 | 영업이익 |
| `net_income` | int \| None | 억원 | 당기순이익 |
| `oi_margin` | float \| None | % | 영업이익률 |
| `report_date` | str | | 보고서 기준 (예: "2024/12") |

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
            "yoy_revenue": null,
            "yoy_op": null,
            "dart_url": "https://dart.fss.or.kr/...",
        },
        ...  # 과거 → 최신 순
    ],
    "memo": "반도체 대장",
}
```

- `fetch_financials_multi_year(code, 10)` 사용
- YoY 증감률은 전년도 대비 계산 (첫 해는 null)

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

반환:
```python
{
    "history": [
        {"date": "2016-02", "per": 7.69, "pbr": 1.24},
        ...
    ],
    "avg_per": 15.2,    # PER > 500 이상치 제외
    "avg_pbr": 1.62,
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

`routers/order.py`에서 사용. KIS REST API 직접 호출 + 로컬 `orders.db` 기록 + 대사 로직.

### 주요 함수

| 함수 | 설명 |
|------|------|
| `place_order(symbol, symbol_name, market, side, order_type, price, quantity, memo)` | 국내/해외 주문 발송. KIS API 호출 후 로컬 DB에 PLACED 상태로 기록. |
| `get_buyable(symbol, market, price, order_type)` | 매수가능 금액/수량 조회 (국내: `TTTC8908R`, 해외: `TTTS3007R`). |
| `get_open_orders(market)` | 미체결 주문 목록 (국내: `TTTC8036R`, 해외: `TTTS3018R`). `api_cancellable` 필드 포함. |
| `modify_order(order_no, org_no, market, order_type, price, quantity, total)` | 주문 정정 (국내: `TTTC0803U`). |
| `cancel_order(order_no, org_no, market, order_type, quantity, total)` | 주문 취소 (국내: `TTTC0803U`). |
| `get_executions(market)` | 당일 체결 내역 (국내: `TTTC8001R`, 해외: `JTTT3001R`). |
| `sync_orders()` | 로컬 PLACED/PARTIAL 주문을 KIS 체결 내역과 대사. FILLED/PARTIAL/CANCELLED로 상태 갱신. |

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
