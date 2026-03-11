# API 엔드포인트 설계

모든 API는 `/api` 접두사를 사용한다. 모든 핸들러는 `def`(sync) — pykrx/requests가 동기 라이브러리이므로 FastAPI가 threadpool에서 자동 실행한다.

Swagger UI: `http://localhost:8000/docs`

---

## 종목 검색 — `routers/search.py`

### `GET /api/search`

종목 검색 자동완성 (KR) 및 티커 검증 (US).

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `q` | string | `""` | 검색어 (종목명, 코드, 티커) |
| `market` | string | `KR` | `KR` / `US` |

**KR 응답** (최대 10건):
```json
[
  { "code": "005930", "name": "삼성전자", "market": "KOSPI" },
  { "code": "018260", "name": "삼성에스디에스", "market": "KOSPI" }
]
```

**KR 검색 로직**:
- 6자리 숫자 입력 → `symbol_map.resolve()` 로 코드→이름 변환
- 2글자 미만 → 빈 배열 반환
- 2글자 이상 → `symbol_map.name_to_results()` 부분일치 검색 (정확일치 우선), 최대 10건

**US 응답**:
```json
[{ "code": "AAPL", "name": "Apple Inc.", "market": "NMS" }]
```
- 유효 티커: 단일 항목 배열
- 무효 티커 또는 빈 쿼리: `[]`

**US 검색 로직**: `yf_client.validate_ticker()` 호출 (1시간 캐시). 무효 티커는 1시간 캐시 후 `[]` 반환.

**에러**: 없음 (검색 실패 시 빈 배열 반환)

---

## 스크리너 — `routers/screener.py`

### `GET /api/screener/stocks`

전종목 멀티팩터 스크리닝.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `date` | string | 오늘 | YYYYMMDD 또는 YYYY-MM-DD |
| `sort_by` | string | 시가총액 내림차순 | `"ROE desc, PER asc"` 형태 |
| `top` | int | 전체 | 상위 N개 |
| `per_min` | float | - | PER 최소값 |
| `per_max` | float | - | PER 최대값 |
| `pbr_max` | float | - | PBR 최대값 |
| `roe_min` | float | - | ROE 최소값 (%) |
| `market` | string | 전체 | `KOSPI` 또는 `KOSDAQ` |
| `include_negative` | bool | false | 적자기업(PER < 0) 포함 |
| `earnings_only` | bool | false | 당일 실적발표 종목만 |

**응답**:
```json
{
  "date": "20250220",
  "total": 150,
  "stocks": [
    {
      "code": "005930", "name": "삼성전자", "market": "KOSPI",
      "per": 12.5, "pbr": 1.2, "roe": 10.0, "mktcap": 3000000000000,
      "prev_close": 75000, "current_price": 76000, "change_pct": 1.33,
      "return_3m": 5.2, "return_6m": -2.1, "return_1y": 12.4,
      "dividend_yield": 2.5
    }
  ]
}
```

- `prev_close`, `current_price`, `change_pct`, `return_3m`, `return_6m`, `return_1y`, `dividend_yield`: yfinance enrichment (ThreadPoolExecutor 병렬). 조회 실패 시 `null`.
- enrichment는 필터·정렬·top 슬라이싱 **이후** 적용 (불필요한 API 호출 최소화).

**에러**: 422 (파라미터 오류), 502 (KRX/DART 호출 실패)

---

## 공시 조회 — `routers/earnings.py`

### `GET /api/earnings/filings`

기간별 정기보고서(사업/반기/분기) 제출 목록 조회.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `date` | string | 오늘 | 단일 날짜 조회 (start_date/end_date와 함께 쓰면 무시) |
| `start_date` | string | - | 시작 날짜 (YYYYMMDD 또는 YYYY-MM-DD) |
| `end_date` | string | - | 종료 날짜 (YYYYMMDD 또는 YYYY-MM-DD) |

- `start_date` + `end_date`: 기간 조회
- `date`만 지정: 단일 날짜 조회 (start = end = date)
- 모두 생략: 오늘 날짜
- 최대 조회 기간: 90일

DART `pblntf_ty=A`(정기공시) 단일 쿼리로 조회. `report_nm` 기반 분류, `rcept_no` 기준 중복 제거.

**응답**:
```json
{
  "start_date": "20250217",
  "end_date": "20250220",
  "total": 9,
  "filings": [
    {
      "corp_name": "삼성전자", "stock_code": "005930",
      "report_type": "사업보고서",
      "report_name": "사업보고서 (2024.12)",
      "rcept_no": "20250220001567",
      "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20250220001567",
      "rcept_dt": "20250220", "flr_nm": "삼성전자",
      "change_pct": 1.23,
      "return_3m": 5.4,
      "return_6m": -2.1,
      "return_1y": 12.7,
      "fin_year": 2024,
      "revenue": 3008709000000000,
      "revenue_prev": 2589336000000000,
      "operating_income": 327260000000000,
      "operating_income_prev": 64822000000000
    }
  ]
}
```

- `change_pct`: 당일 등락률(%). pykrx 1년치 OHLCV에서 최근 2 거래일 비교. 1시간 캐싱.
- `return_3m` / `return_6m` / `return_1y`: 90일/180일/365일 전 대비 수익률(%).
- `fin_year`: 재무 데이터 사업연도 (정수). `revenue` ~ `operating_income_prev`: 원(元) 단위.
- 데이터 없으면 각 필드 `null`.

**에러**: 422 (날짜 오류, 기간 초과), 502 (DART 호출 실패)

---

## 잔고 조회 — `routers/balance.py`

### `GET /api/balance`

KIS 실전계좌 잔고 조회. KIS API 키 필수.

파라미터 없음. 환경변수에서 계좌 정보를 읽는다.

**응답**:
```json
{
  "total_evaluation": "100000000",
  "deposit": "5000000",
  "stock_eval": "95000000",
  "stock_list": [
    {
      "name": "삼성전자", "code": "005930",
      "quantity": "100", "current_price": "70000",
      "profit_loss": "500000", "profit_rate": "5.00",
      "eval_amount": "7000000", "avg_price": "65000.00"
    }
  ]
}
```

**에러**: 503 (KIS 키 미설정), 502 (KIS API 호출 실패), 400 (API 오류/토큰 만료)

---

## 관심종목 — `routers/watchlist.py`

데이터 저장: `~/stock-watchlist/watchlist.json`

### `GET /api/watchlist`

관심종목 목록 반환.

**응답**: `{"items": [{"code": "005930", "name": "삼성전자", "added_date": "2025-02-20", "memo": "..."}]}`

### `POST /api/watchlist`

관심종목 추가. 종목코드 또는 종목명 허용.

**요청 바디**: `{"code": "삼성전자", "memo": "반도체 대장"}`

**응답**: `201 {"item": {...}}`
**에러**: 404 (종목 없음), 409 (이미 등록됨)

### `DELETE /api/watchlist/{code}`

관심종목 삭제. 6자리 종목코드 사용.

**응답**: `{"deleted": true}`
**에러**: 404 (미등록 종목)

### `PATCH /api/watchlist/{code}`

메모 수정.

**요청 바디**: `{"memo": "새 메모"}`

**응답**: `{"item": {...}}`
**에러**: 404 (미등록 종목)

### `GET /api/watchlist/dashboard`

전체 관심종목의 시세 + 재무 대시보드.

**응답**:
```json
{
  "stocks": [
    {
      "code": "005930", "name": "삼성전자", "memo": "...",
      "price": 70000, "change": 1000, "change_pct": 1.45,
      "market_cap": 4200000,
      "revenue": 3008709, "operating_profit": 327260,
      "net_income": 344514, "oi_margin": 10.9,
      "report_date": "2024/12"
    }
  ]
}
```

금액 단위: `market_cap`, `revenue`, `operating_profit`, `net_income`은 **억원**. `price`, `change`는 **원**.

### `GET /api/watchlist/info/{code}`

단일 종목 상세 (기본정보 + 최대 10년 재무).

**응답**:
```json
{
  "basic": {
    "code": "005930", "price": 70000, "change": 1000, "change_pct": 1.45,
    "market_cap": 4200000, "per": 12.5, "pbr": 1.2,
    "high_52": 80000, "low_52": 50000,
    "market": "KOSPI", "sector": "전기·전자", "shares": 5969782550
  },
  "financials_3y": [
    {
      "year": 2015, "revenue": 2006535, "operating_profit": 264134,
      "net_income": 190601, "yoy_revenue": null, "yoy_op": null,
      "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=..."
    }
  ],
  "memo": "반도체 대장"
}
```

`financials_3y` 키 이름은 하위호환 유지 (실제 최대 10년). 금액 단위: **억원**.
`year`는 정수(2024 등), `dart_url` 클릭 시 DART 사업보고서 열림.

---

## 종목 상세 분석 — `routers/detail.py`

### `GET /api/detail/financials/{symbol}`

최대 N년 사업연도 재무 데이터. DART `fnlttSinglAcntAll` 3년 단위 배치 호출.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `years` | int (1~20) | 10 | 조회 연도 수 |

**응답**:
```json
{
  "code": "005930",
  "rows": [
    {
      "year": 2015, "revenue": 2006535, "operating_profit": 264134,
      "net_income": 190601, "oi_margin": 13.2,
      "yoy_revenue": null, "yoy_op": null,
      "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=..."
    }
  ]
}
```

금액 단위: **억원**. 과거 → 최신 순 정렬.

### `GET /api/detail/valuation/{symbol}`

월별 PER/PBR 히스토리 + 기간 평균. pykrx `get_market_fundamental_by_date` 사용, 월말 리샘플링.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `years` | int (1~20) | 10 | 조회 연도 수 |

**응답**:
```json
{
  "history": [{"date": "2016-02", "per": 7.69, "pbr": 1.24}, ...],
  "avg_per": 15.2,
  "avg_pbr": 1.62
}
```

PER > 500 이상치는 평균 계산에서 제외.

### `GET /api/detail/report/{symbol}`

재무 + 밸류에이션 + 기본 시세 + 종합 요약 통합 반환.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `years` | int (1~20) | 10 | 조회 연도 수 |

**응답**:
```json
{
  "basic": {
    "code": "005930", "name": "삼성전자",
    "price": 70000, "change": 1000, "change_pct": 1.45,
    "market_cap": 4200000, "per": 12.5, "pbr": 1.2,
    "high_52": 80000, "low_52": 50000,
    "market": "KOSPI", "sector": "전기·전자"
  },
  "financials": { "code": "005930", "rows": ["..."] },
  "valuation": { "history": ["..."], "avg_per": 15.2, "avg_pbr": 1.62 },
  "summary": {
    "rev_cagr": 4.6, "op_cagr": 2.4, "net_cagr": 6.8,
    "current_per": 12.5, "current_pbr": 1.2,
    "avg_per": 15.2, "avg_pbr": 1.62,
    "per_vs_avg": -17.8, "pbr_vs_avg": -25.9,
    "years": 10, "year_start": 2015, "year_end": 2024
  }
}
```

- `per_vs_avg` / `pbr_vs_avg`: 평균 대비 현재 밸류에이션 비율(%). 음수면 저평가.
- CAGR: 첫 해와 마지막 해 기준 연평균 성장률(%).

---

## 주문 관리 — `routers/order.py`

KIS 실전계좌 주문 발송·정정·취소·미체결·체결 내역·이력·대사·예약주문. KIS API 키 필수.

로컬 DB: `~/stock-watchlist/orders.db`

### `POST /api/order/place`

주문 발송 (국내/해외 매수/매도).

**요청 바디**:
```json
{
  "symbol": "005930",
  "symbol_name": "삼성전자",
  "market": "KR",
  "side": "buy",
  "order_type": "00",
  "price": 70000,
  "quantity": 1,
  "memo": ""
}
```

- `market`: `KR` / `US`
- `side`: `buy` / `sell`
- `order_type`: `00`(지정가) / `01`(시장가)
- `price`: 시장가 주문 시 `0`

**응답** `201`:
```json
{
  "order": {
    "id": 1,
    "order_no": "39822900",
    "org_no": "91258",
    "symbol": "005930",
    "symbol_name": "삼성전자",
    "market": "KR",
    "side": "buy",
    "order_type": "00",
    "price": 70000.0,
    "quantity": 1,
    "filled_quantity": 0,
    "status": "PLACED",
    "currency": "KRW",
    "placed_at": "2026-02-26T15:10:49",
    "updated_at": "2026-02-26T15:10:49"
  }
}
```

**에러**: 503 (KIS 키 미설정), 400 (KIS 주문 오류 - 잔고 부족, 호가단위 오류 등)

---

### `GET /api/order/buyable`

매수가능 금액/수량 조회.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `symbol` | string | 필수 | 종목코드 |
| `market` | string | `KR` | `KR` / `US` |
| `price` | float | `0` | 주문 예정 가격 |
| `order_type` | string | `00` | `00`(지정가) / `01`(시장가) |

**응답**:
```json
{
  "buyable_amount": "1500000",
  "buyable_quantity": "21",
  "deposit": "2000000",
  "currency": "KRW"
}
```

---

### `GET /api/order/open`

미체결 주문 목록 (KIS 실시간 조회).

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `market` | string | `KR` | `KR` / `US` |

**응답**:
```json
{
  "orders": [
    {
      "order_no": "0039822900",
      "org_no": "91258",
      "symbol": "215000",
      "symbol_name": "골프존",
      "market": "KR",
      "side": "buy",
      "side_label": "매수",
      "order_type": "00",
      "order_type_label": "지정가",
      "price": "42700",
      "quantity": "1",
      "remaining_qty": "1",
      "filled_qty": "0",
      "ordered_at": "151049",
      "currency": "KRW",
      "excg_id_dvsn_cd": "KRX",
      "api_cancellable": true
    }
  ]
}
```

- `api_cancellable`: `true`=API 취소 가능(KRX 직접접수), `false`=HTS/MTS 주문(증권사 앱에서 취소 필요)
- `excg_id_dvsn_cd`: `'KRX'`=API 주문, `'SOR'`=HTS/MTS(Smart Order Routing) 주문

---

### `POST /api/order/{order_no}/cancel`

주문 취소.

**요청 바디**:
```json
{
  "org_no": "91258",
  "market": "KR",
  "order_type": "00",
  "quantity": 1,
  "total": true
}
```

- `total: true`: 잔량 전부 취소 (`QTY_ALL_ORD_YN: Y`)

**응답**: `{"success": true, "data": {...}}`

**에러**: 400 (KIS 취소 오류. HTS 주문이면 "원주문정보가 존재하지않습니다" 오류 발생)

---

### `POST /api/order/{order_no}/modify`

주문 정정 (가격/수량 변경).

**요청 바디**:
```json
{
  "org_no": "91258",
  "market": "KR",
  "order_type": "00",
  "price": 45000,
  "quantity": 1,
  "total": true
}
```

**응답**: `{"success": true, "data": {...}}`

---

### `GET /api/order/executions`

당일 체결 내역 (KIS 조회).

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `market` | string | `KR` | `KR` / `US` |

**응답**:
```json
{
  "executions": [
    {
      "order_no": "39822900",
      "symbol": "215000",
      "symbol_name": "골프존",
      "market": "KR",
      "side": "buy",
      "side_label": "매수",
      "order_type_label": "지정가",
      "price": "42700",
      "quantity": "1",
      "filled_qty": "1",
      "filled_price": "42700",
      "filled_amount": "42700",
      "ordered_at": "2026-02-26 151049",
      "status": "Y",
      "currency": "KRW"
    }
  ]
}
```

---

### `GET /api/order/history`

로컬 DB 주문 이력.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `symbol` | string | - | 종목코드 필터 |
| `market` | string | - | `KR` / `US` 필터 |
| `status` | string | - | `PLACED`/`FILLED`/`PARTIAL`/`CANCELLED`/`REJECTED` |
| `date_from` | string | - | 시작일 (YYYY-MM-DD) |
| `date_to` | string | - | 종료일 (YYYY-MM-DD) |
| `limit` | int | `100` | 최대 반환 건수 (1~500) |

**응답**: `{"orders": [...]}`

주문 상태:
- `PLACED`: 접수
- `PARTIAL`: 부분 체결
- `FILLED`: 전량 체결
- `CANCELLED`: 취소 완료
- `CANCEL_REQUESTED`: 취소 요청
- `REJECTED`: 거부

---

### `POST /api/order/sync`

KIS 당일 체결 내역과 로컬 DB 대사(Reconciliation). 로컬 `PLACED`/`PARTIAL` 주문을 KIS에서 조회해 상태를 갱신한다.

**응답**:
```json
{
  "synced": 1,
  "details": [
    {"id": 1, "order_no": "39822900", "action": "updated", "new_status": "FILLED"}
  ]
}
```

---

### `POST /api/order/reserve`

예약주문 등록.

**요청 바디**:
```json
{
  "symbol": "005930",
  "symbol_name": "삼성전자",
  "market": "KR",
  "side": "buy",
  "order_type": "00",
  "price": 65000,
  "quantity": 1,
  "condition_type": "price_below",
  "condition_value": "66000",
  "memo": ""
}
```

- `condition_type`: `price_below`(목표가 이하 시 발동) / `price_above`(목표가 이상 시 발동) / `scheduled`(지정 시각에 발동)
- `condition_value`: 가격 조건이면 숫자 문자열, 시간 조건이면 ISO 8601 datetime

**응답** `201`: `{"reservation": {...}}`

---

### `GET /api/order/reserves`

예약주문 목록.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `status` | string | - | `WAITING`/`TRIGGERED`/`EXECUTED`/`FAILED`/`CANCELLED` 필터 |

**응답**: `{"reservations": [...]}`

---

### `DELETE /api/order/reserve/{id}`

예약주문 삭제 (WAITING 상태만 가능).

**응답**: `{"deleted": true}`
**에러**: 404 (없거나 WAITING 아님)

---

---

## 실시간 호가 — `routers/quote.py`

### `WS /ws/quote/{symbol}`

실시간 현재가 + 10호가 WebSocket 스트림.

- **국내(KR)**: KIS WebSocket(`ws://ops.koreainvestment.com:21000`) 브릿지. `H0STCNT0`(체결가) + `H0STASP0`(호가) 실시간 수신. KIS Approval Key 자동 발급 및 캐시.
- **해외(US)**: yfinance `Ticker.fast_info` 2초 주기 polling.
- KIS 키 미설정 시 연결은 수락되나 데이터 없음(ping만 수신).

**메시지 타입**

| `type` | 발생 조건 | 필드 |
|--------|----------|------|
| `price` | 체결 발생(국내) / 2초 주기(해외) | `symbol`, `price`, `change`, `change_rate`, `sign` |
| `orderbook` | 호가 변동(국내만) | `symbol`, `asks[{price,volume}×10]`, `bids[{price,volume}×10]`, `total_ask_volume`, `total_bid_volume` |
| `ping` | 30초간 데이터 없음 | (연결 유지용) |
| `error` | 해외 시세 조회 실패 | `message` |

**`sign` 값**: `'2'`=상승, `'3'`=보합, `'5'`=하락

**`asks` / `bids` 인덱스 규칙**
- `asks[0]` = 최우선(최저가) 매도호가. 프론트에서 `reverse()` 후 상단에 높은가격 표시.
- `bids[0]` = 최우선(최고가) 매수호가. 그대로 표시(높은가격 → 낮은가격).

**에러 처리**: 예외 발생 시 code=1011로 WS 종료. 클라이언트는 비정상 종료(code≠1000) 시 3초 후 재연결.

---

## AI자문 — `routers/advisory.py`

자문종목 CRUD + 기본적/기술적 분석 데이터 수집 + OpenAI GPT-4o 리포트 생성.

로컬 DB: `~/stock-watchlist/advisory.db`

### `GET /api/advisory`

자문종목 목록 (캐시 업데이트 시각 + AI리포트 존재 여부 포함).

**응답**:
```json
[
  {
    "code": "005930",
    "market": "KR",
    "name": "삼성전자",
    "added_date": "2026-03-04T01:29:14",
    "memo": "반도체 대장",
    "updated_at": "2026-03-04T07:12:20",
    "has_report": true
  }
]
```

---

### `POST /api/advisory`

자문종목 추가. 종목명 자동 조회 (KR: pykrx, US: yfinance).

**요청 바디**:
```json
{
  "code": "005930",
  "market": "KR",
  "memo": ""
}
```

- `market`: `KR` / `US`

**에러**: 409 (이미 등록됨)

---

### `DELETE /api/advisory/{code}?market=KR`

자문종목 삭제.

**응답**: `{"ok": true}`

**에러**: 404 (미등록 종목)

---

### `POST /api/advisory/{code}/refresh?market=KR&name=`

기본적/기술적 분석 데이터 전체 수집 후 캐시 저장. **30초 이상 소요**.

**쿼리 파라미터**:
- `market`: `KR` (기본값) / `US`
- `name`: 종목명 (선택). advisory_stocks 미등록 종목에서 사용. 없으면 `code` 값으로 대체.

advisory_stocks에 등록되지 않은 종목도 호출 가능 (DetailPage에서 직접 호출 지원).

수집 데이터:
- **KR**: DART 손익계산서(5년) + 대차대조표(5년) + 현금흐름표(5년) + pykrx 계량지표 + KIS 15분봉(yfinance fallback 포함) + OpenAI 사업부문 추론
- **US**: yfinance 손익계산서(4년) + 대차대조표(4년) + 현금흐름표(4년) + yfinance 계량지표 + yfinance 15분봉

**응답**: 수집된 분석 데이터 전체 (아래 `/data` 응답과 동일)

**에러**: 502 (데이터 수집 실패)

---

### `GET /api/advisory/{code}/data?market=KR`

캐시된 분석 데이터 조회.

**응답**:
```json
{
  "code": "005930",
  "market": "KR",
  "updated_at": "2026-03-04T07:12:20",
  "fundamental": {
    "income_stmt": [
      {
        "year": 2024,
        "revenue": null,
        "cogs": null,
        "gross_profit": null,
        "operating_income": 327260000000000,
        "net_income": 344514000000000,
        "eps": null,
        "oi_margin": 10.9,
        "net_margin": 11.5,
        "dart_url": "https://dart.fss.or.kr/..."
      }
    ],
    "balance_sheet": [
      {
        "year": 2024,
        "total_assets": null,
        "total_liabilities": null,
        "total_equity": null,
        "debt_ratio": null,
        "current_ratio": null
      }
    ],
    "cashflow": [
      {
        "year": 2024,
        "operating_cf": null,
        "investing_cf": null,
        "financing_cf": null,
        "capex": null,
        "free_cf": null,
        "fcf_margin": null
      }
    ],
    "metrics": {
      "per": 12.5, "pbr": 1.2, "roe": 8.5, "roa": 5.2,
      "market_cap": 102000000000000,
      "market_type": "KOSPI",
      "psr": null, "ev_ebitda": null,
      "debt_to_equity": null, "current_ratio": null
    },
    "segments": [
      {"segment": "반도체", "revenue_pct": 45.0, "note": "AI추정"}
    ]
  },
  "technical": {
    "ohlcv": [
      {"time": "2026-03-04T15:00:00", "open": 175300, "high": 176300, "low": 172500, "close": 172800, "volume": 2962588}
    ],
    "indicators": {
      "macd": {"macd": [...], "signal": [...], "histogram": [...], "times": [...]},
      "rsi": {"values": [...], "times": [...]},
      "stoch": {"k": [...], "d": [...], "times": [...]},
      "bb": {"upper": [...], "mid": [...], "lower": [...], "times": [...]},
      "ma": {"ma5": [...], "ma20": [...], "ma60": [...], "times": [...]},
      "volatility_target": 173200,
      "current_signals": {
        "macd_cross": "golden",
        "rsi_signal": "neutral",
        "rsi_value": 54.7,
        "stoch_signal": "oversold",
        "stoch_k": 18.2,
        "above_ma20": true,
        "ma20": 170500,
        "current_price": 172800
      }
    }
  }
}
```

**에러**: 404 (데이터 없음. 먼저 `/refresh` 호출 필요)

---

### `GET /api/advisory/{code}/ohlcv?market=KR&interval=15m&period=60d`

타임프레임/기간을 지정하여 OHLCV 데이터 + 기술적 지표를 조회. 기술지표는 매 호출마다 재계산 (캐시 없음).

**쿼리 파라미터**:

| 파라미터 | 기본값 | 허용값 | 설명 |
|---------|--------|--------|------|
| `market` | `KR` | `KR` / `US` | 시장 구분 |
| `interval` | `15m` | `15m` / `60m` / `1d` / `1wk` | 봉 단위 |
| `period` | `60d` | `5d`, `1mo`, `60d`, `3mo`, `6mo`, `1y`, `2y`, `3y`, `5y`, `10y` | 조회 기간 |

**yfinance interval 제한**:
- `15m`: 최대 `60d`
- `60m`: 최대 `2y`
- `1d` / `1wk`: 최대 `10y`

period가 interval 허용 최대치를 초과하면 자동으로 최대값으로 조정.

**응답**:
```json
{
  "ohlcv": [
    {"time": "2026-03-04T15:00:00", "open": 175300, "high": 176300, "low": 172500, "close": 172800, "volume": 2962588}
  ],
  "indicators": {
    "macd": {"macd": [...], "signal": [...], "histogram": [...], "times": [...]},
    "rsi": {"values": [...], "times": [...]},
    "stoch": {"k": [...], "d": [...], "times": [...]},
    "bb": {"upper": [...], "mid": [...], "lower": [...], "times": [...]},
    "ma": {"ma5": [...], "ma20": [...], "ma60": [...], "times": [...]},
    "volatility_target": 173200,
    "current_signals": {
      "macd_cross": "golden",
      "rsi_signal": "neutral",
      "rsi_value": 54.7,
      "stoch_signal": "oversold",
      "stoch_k": 18.2,
      "above_ma20": true,
      "ma20": 170500,
      "current_price": 172800
    }
  },
  "interval": "15m",
  "period": "60d"
}
```

**에러**: 500 (데이터 수집 실패)

---

### `POST /api/advisory/{code}/analyze?market=KR`

OpenAI GPT-4o로 종합 투자 의견 리포트 생성. **10~30초 소요**.

캐시된 분석 데이터를 기반으로 프롬프트를 구성하여 GPT-4o 호출.

**응답**:
```json
{
  "id": 1,
  "code": "005930",
  "market": "KR",
  "generated_at": "2026-03-04T09:10:52",
  "model": "gpt-4o",
  "report": {
    "종합투자의견": {
      "등급": "중립",
      "요약": "...",
      "근거": ["...", "..."]
    },
    "기술적시그널": {
      "신호": "관망",
      "해석": "...",
      "지표별": {"macd": "...", "rsi": "...", "stoch": "..."}
    },
    "리스크요인": [
      {"요인": "글로벌 경제 불확실성", "설명": "..."}
    ],
    "투자포인트": [
      {"포인트": "재무성장성", "설명": "..."}
    ]
  }
}
```

**에러**:
- 402: OpenAI 크레딧 부족
- 404: 분석 데이터 없음 (먼저 `/refresh` 필요)
- 503: `OPENAI_API_KEY` 미설정
- 502: OpenAI API 오류

---

### `GET /api/advisory/{code}/report?market=KR`

최신 AI 리포트 조회.

**응답**: `/analyze`와 동일 구조

**에러**: 404 (생성된 리포트 없음)

---

### 로컬 DB 스키마 (`~/stock-watchlist/advisory.db`)

```sql
-- 자문종목 목록
CREATE TABLE advisory_stocks (
    code       TEXT NOT NULL,
    market     TEXT NOT NULL DEFAULT 'KR',
    name       TEXT NOT NULL,
    added_date TEXT NOT NULL,
    memo       TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (code, market)
);

-- 기본적/기술적 분석 캐시
CREATE TABLE advisory_cache (
    code       TEXT NOT NULL,
    market     TEXT NOT NULL DEFAULT 'KR',
    updated_at TEXT NOT NULL,
    fundamental TEXT,   -- JSON
    technical   TEXT,   -- JSON
    PRIMARY KEY (code, market)
);

-- AI 리포트 이력
CREATE TABLE advisory_reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT NOT NULL,
    market       TEXT NOT NULL DEFAULT 'KR',
    generated_at TEXT NOT NULL,
    model        TEXT NOT NULL,
    report       TEXT NOT NULL   -- JSON
);
```

---

### 로컬 DB 스키마 (`~/stock-watchlist/orders.db`)

```sql
-- 주문 이력
CREATE TABLE orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no        TEXT,
    org_no          TEXT,
    symbol          TEXT NOT NULL,
    symbol_name     TEXT,
    market          TEXT NOT NULL DEFAULT 'KR',
    side            TEXT NOT NULL,
    order_type      TEXT NOT NULL,
    price           REAL NOT NULL,
    quantity        INTEGER NOT NULL,
    filled_price    REAL,
    filled_quantity INTEGER DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'PLACED',
    currency        TEXT DEFAULT 'KRW',
    memo            TEXT DEFAULT '',
    placed_at       TEXT NOT NULL,
    filled_at       TEXT,
    updated_at      TEXT NOT NULL,
    kis_response    TEXT
);

-- 예약주문
CREATE TABLE reservations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    symbol_name     TEXT,
    market          TEXT NOT NULL DEFAULT 'KR',
    side            TEXT NOT NULL,
    order_type      TEXT NOT NULL,
    price           REAL NOT NULL,
    quantity        INTEGER NOT NULL,
    condition_type  TEXT NOT NULL,
    condition_value TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'WAITING',
    result_order_no TEXT,
    memo            TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    triggered_at    TEXT,
    updated_at      TEXT NOT NULL
);
```
