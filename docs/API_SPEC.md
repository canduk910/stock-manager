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
  "stock_list": [...],
  "overseas_list": [...],
  "futures_list": [...],
  "fno_enabled": true
}
```

- `stock_list`: name, code, exchange, quantity, avg_price, current_price, profit_loss, profit_rate, eval_amount, mktcap, per, pbr, roe, dividend_yield
- `overseas_list`: + currency, profit_loss_krw, eval_amount_krw
- `futures_list`: name, code, trade_type, quantity, avg_price, current_price, profit_loss, profit_rate, eval_amount
- `fno_enabled`: `KIS_ACNT_PRDT_CD_FNO` 환경변수 설정 여부 (프론트에서 FNO 섹션 표시 제어)

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

### `GET /api/watchlist/order`

관심종목 표시 순서 조회.

**응답**: `{"items": [{"code": "005930", "market": "KR", "position": 0}, ...]}`

### `PUT /api/watchlist/order`

관심종목 표시 순서 저장 (전체 교체). 배열 인덱스가 position.

**요청 바디**: `{"items": [{"code": "005930", "market": "KR"}, ...]}`
**응답**: `{"ok": true}`

### `GET /api/watchlist/batch-details`

N종목 metrics 병렬 일괄 조회 (2026-05-12 신규). `useWatchlist` N+1 호출 패턴 제거 + ThreadPoolExecutor(4) 병렬.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `codes` | str (CSV) | — | 종목 코드 콤마 구분 (최대 50개, 초과 시 400 ServiceError) |
| `market` | "auto"/"KR"/"US" | "auto" | "auto"는 `is_domestic(code)`로 자동 판별 |

**응답**: `{"details": {"005930": {price, change, change_pct, per, pbr, roe, dividend_yield, sector, ...}, ...}}`
**부분 실패**: 일부 종목 fetch 실패 시 해당 키만 누락(200 응답 유지). 빈 codes → 400.

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
  },
  "forward_estimates": {
    "eps_current_year": 6.5, "eps_forward": 7.2, "forward_pe": 22.1,
    "revenue_current": null, "revenue_forward": null,
    "net_income_estimate": 150000, "net_income_forward": null,
    "target_mean_price": 85000, "target_high_price": 95000, "target_low_price": 70000,
    "num_analysts": 12, "recommendation": "buy", "current_fiscal_year_end": "2025-12"
  }
}
```

- `per_vs_avg` / `pbr_vs_avg`: 평균 대비 현재 밸류에이션 비율(%). 음수면 저평가.
- CAGR: 첫 해와 마지막 해 기준 연평균 성장률(%).

### `GET /api/detail/{symbol}/bundle`

DetailPage 마운트 시 모든 섹션을 한 번에 반환 (2026-05-12 신규). `report/{symbol}`의 응답과 동일 shape이지만 내부적으로 ThreadPoolExecutor 병렬 수집 + 부분 실패 보존.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `market` | "auto"/"KR"/"US" | "auto" | 시장 자동 판별 |

**응답 추가 필드**: `partial_failure: list[str]` — 실패한 섹션 ID 목록 (예: `["valuation"]`). 정상 시 빈 배열.

**효과**: DetailPage 마운트 N+1 → 1회 호출 + 캐시 미스 시 3~8s → 2~3s.

---

## 주문 관리 — `routers/order.py`

KIS 실전계좌 주문 발송·정정·취소·미체결·체결 내역·이력·대사·예약주문. KIS API 키 필수.

**계층 분리**: `routers/order.py`는 오직 `services.order_service`만 import. `order_store` 직접 접근 금지. 이력 조회·예약주문·FNO 시세 모두 서비스 계층 경유.

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
  "memo": "",
  "exchange": "SOR"
}
```

- `market`: `KR` / `US` / `FNO`
- `side`: `buy` / `sell`
- `order_type`: `00`(지정가) / `01`(시장가)
- `price`: 시장가 주문 시 `0`
- `exchange` (KR 전용, 2026-05-08): `"SOR"`(기본, 자동 라우팅) / `"KRX"`(KOSPI/KOSDAQ) / `"NXT"`(넥스트레이드). 통합(UN)은 시세 전용 코드라 주문값 X. 모의투자(`openapivts`)에서는 KRX만 허용(SOR/NXT 시 400 ServiceError). 응답 항목에 `exchange` 키 포함(KIS 라우팅 결과로 `SOR-KRX`/`SOR-NXT` 정밀 거래소가 채워질 수 있음).

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
  },
  "balance_stale": true
}
```

- `balance_stale: true` — 프론트엔드에서 잔고 재조회 트리거 신호

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

**응답**: `{"success": true, "data": {...}, "local_synced": true, "order_status": "CANCELLED"}`

- `local_synced: true` — 로컬 DB의 주문 상태가 즉시 CANCELLED로 갱신됨
- `order_status` — 최종 상태 (`"CANCELLED"` 전량취소, `"PARTIAL"` 부분취소)

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

**응답**: `{"success": true, "data": {...}, "local_synced": true}`

- `local_synced: true` — 로컬 DB의 가격/수량이 즉시 반영됨

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

로컬 DB 주문 이력. **반환 전 활성 주문(PLACED/PARTIAL)을 KIS 체결+미체결 내역과 자동 대사(best-effort)**하여 최신 상태를 보장한다. `date_from > date_to`이면 400 에러.

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

### ~~`WS /ws/market-status`~~ (2026-05-12 폐지)

> **제거됨.** 장운영정보 멀티플렉스 WS(`H0UNMKO0`/`H0STMKO0`/`H0NXMKO0`)는 동일 KIS 계정을 공유하는 외부 자동매매 시스템과의 동시구독 41건 충돌 원인 중 하나로, slot 3건 회수를 위해 폐지. 프론트 `useMarketClock`은 KST 시계 기반 4구간 폴백(`resolvePhaseByClock(now)` + 1분 setInterval)을 단독 사용한다.

---

### `WS /ws/quote/{symbol}`

실시간 현재가 + 호가 WebSocket 스트림.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `symbol` | path | - | 종목코드 또는 FNO 단축코드 |
| `market` | query | `KR` | `KR` / `US` / `FNO` |
| `exchange` | query | `auto` | (KR 전용, 2026-05-08) `auto`(기본, KST 시계 기반 4구간 자동) / `UN`(통합) / `KRX` / `NXT`. FNO/US는 무시. |

- **국내(`market=KR`)**: KIS WebSocket(`ws://ops.koreainvestment.com:21000`) 브릿지. **(2026-05-08 KRX+NXT 통합)** 시간대 자동 분기 — 09:00~15:30 = `H0UNCNT0`(통합)+`H0UNASP0`, 15:30~15:40 = `H0STCNT0`(KRX)+`H0STASP0`, 08:00~09:00 / 15:40~20:00 = `H0NXCNT0`(NXT)+`H0NXASP0`. `exchange` 명시(`UN`/`KRX`/`NXT`) 시 시계와 무관하게 강제. `auto`(기본) 시 `KISQuoteManager._resolve_exchange_by_clock()` + `H0UNMKO0` WS override. NXT/통합 호가도 ASKP1~10/RSQN1~10 동일 10호가 구조.
- **선물옵션(`market=FNO`)**: KIS WebSocket FNO 채널 브릿지. `_resolve_fno_type(symbol)`으로 TR_ID 자동 선택. 지수선물(1xxx): `H0IFCNT0`(체결)+`H0IFASP0`(5레벨 호가), 지수옵션(2xxx): `H0IOCNT0`+`H0IOASP0`, 주식선물(3xxx): `H0ZFCNT0`+`H0ZFASP0`(10레벨), 주식옵션(3xxx): `H0ZOCNT0`+`H0ZOASP0`. `_stream_fno()` 핸들러로 분기.
- **해외(`market=US`)**: **(2026-05-08~09)** KIS REST `get_kis_price()` 우선 + Finnhub WS / yfinance 2초 폴링 fallback (가격 채널). **호가 채널 신규** — KIS WS HDFSASP0 우선(2026-05-09 통합) + REST `HHDFS76200100` 2초 폴링 폴백 자동 전환. broadcast `{type:"orderbook", asks, bids, total_*_volume}` 국내와 동일 shape. KIS WS 키 부재 환경 graceful → REST 폴링.
- KIS 키 미설정 시 연결은 수락되나 데이터 없음(ping만 수신).

**메시지 타입**

| `type` | 발생 조건 | 필드 |
|--------|----------|------|
| `price` | 체결 발생(KR/FNO) / 2초 주기(US) | `symbol`, `price`, `change`, `change_rate`, `sign` |
| `orderbook` | 호가 변동(KR=10호가 / FNO=5 또는 10레벨) | `symbol`, `asks[{price,volume}×N]`, `bids[{price,volume}×N]`, `total_ask_volume`, `total_bid_volume` |
| `ping` | 30초간 데이터 없음 | (연결 유지용) |
| `error` | 시세 조회 실패 | `message` |

**`sign` 값**: `'2'`=상승, `'3'`=보합, `'5'`=하락

**`asks` / `bids` 인덱스 규칙**
- `asks[0]` = 최우선(최저가) 매도호가. 프론트에서 `reverse()` 후 상단에 높은가격 표시.
- `bids[0]` = 최우선(최고가) 매수호가. 그대로 표시(높은가격 → 낮은가격).

**에러 처리**: 예외 발생 시 code=1011로 WS 종료. 클라이언트는 비정상 종료(code≠1000) 시 3초 후 재연결.

### `GET /api/quote/us/{symbol}/orderbook` (2026-05-08 신규)

미국주식 10단계 호가 REST 폴백. `Depends(get_current_user)`. KIS `HHDFS76200100`. WS 차단 환경 또는 디버깅용 — 일반 사용자 경로는 `/ws/quote/{symbol}` WS 사용.

**응답 (200)**:
```json
{
  "asks": [{"price": 150.52, "volume": 100, "total_volume": 250}, ...up to 10],
  "bids": [{"price": 150.50, "volume": 80, "total_volume": 200}, ...up to 10],
  "total_ask_volume": 1234,
  "total_bid_volume": 5678,
  "exchange": "NAS"
}
```

응답 단계가 10 미만일 수 있음(KIS Level 2 미제공 종목 → 응답 받은 단계만). 가격은 USD 소수 2자리.

**에러**: 503(KIS 키 부재 — ConfigError) / 504(KIS 응답 None — `get_kis_orderbook` 실패).

### `GET /api/quote/us/{symbol}/detail` (2026-05-08 신규)

미국주식 현재가 상세(시/고/저/거래량/52주). KIS `HHDFS76200200`.

**응답 (200)**:
```json
{
  "open": 150.20,
  "high": 151.80,
  "low": 149.50,
  "prev_close": 150.10,
  "volume": 12345678,
  "high_52w": 198.23,
  "low_52w": 124.17,
  "exchange": "NAS"
}
```

**에러**: 503 / 504.

---

## AI자문 — `routers/advisory.py`

자문종목 CRUD + 기본적/기술적 분석 데이터 수집 + OpenAI GPT-5.4 리포트 생성.

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

OpenAI GPT-5.4로 종합 투자 의견 리포트 생성. **10~30초 소요**.

캐시된 분석 데이터를 기반으로 프롬프트를 구성하여 GPT-5.4 호출.

**요청 바디** (Optional, 백워드 호환):
```json
{
  "user_comment": "이 종목은 AI 사이클 수혜로 향후 12개월 강세 예상"
}
```
- `user_comment`: 사용자 가설(1000자 상한, 초과 시 400). 전달 시 응답 `report`에 `user_commentary_evaluation` 섹션 추가:
  ```json
  {
    "user_commentary_evaluation": {
      "user_comment": "원문 echo",
      "overall_stance": "strong_agree|agree|balanced|disagree|strong_disagree",
      "agree_points": [{"point": "...", "evidence": "...", "strength": 1~10}],
      "disagree_points": [{"point": "...", "evidence": "...", "strength": 1~10}],
      "summary": "1~3문장 직접 답변"
    }
  }
  ```
- 코멘트 없으면 (또는 body 미전송) 기존 동작과 동일.

**응답**:
```json
{
  "id": 1,
  "code": "005930",
  "market": "KR",
  "generated_at": "2026-03-04T09:10:52",
  "model": "gpt-5.4",
  "report": {
    "종합투자의견": {
      "등급": "중립",
      "요약": "...",
      "근거": ["...", "..."]
    },
    "전략별평가": {
      "변동성돌파": {"신호": "매수|대기|중립", "설명": "..."},
      "안전마진": {"graham_number": 75000, "현재가대비": "할인", "설명": "..."},
      "추세추종": {"신호": "중립", "설명": "..."}
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

---

## 부록: 해외주식 지원 범위 및 제약

| 기능 | 지원 여부 | 비고 |
|------|----------|------|
| 관심종목 추가/삭제 | ✅ | 티커 코드 직접 입력 (AAPL, NVDA 등) |
| 대시보드 시세 | ✅ | USD, 15분 지연 |
| 대시보드 재무 | ✅ | USD, M 단위, 최대 4년 |
| 종목 상세 재무 | ✅ | yfinance 최대 4년 |
| CAGR 종합 리포트 | ✅ | yfinance 재무 기반 |
| PER/PBR 히스토리 차트 | ✅ | 분기 EPS/BPS + 일별 주가 기반 추정. 최대 5년. |
| 공시 조회 (SEC) | ✅ | 10-K/10-Q, 수익률 포함 |
| 스크리너 | ❌ | 미지원 (국내 전용) |
| 종목명 검색 | ❌ | 티커 코드만 가능 |
| AI자문 (국내 KR) | ✅ | DART 재무 3종 + pykrx 계량지표 + KIS 15분봉(yfinance fallback) + GPT-5.4 |
| AI자문 (해외 US) | ✅ | yfinance 재무 3종 + yfinance 계량지표 + yfinance 15분봉 + GPT-5.4 |
| 지원 시장 | US | NASDAQ/NYSE/AMEX. 일본·홍콩 등 추후 확장 가능 구조 |

---

## 시세판 — `routers/market_board.py`

### `GET /api/market-board/new-highs-lows`
당일 신고가/신저가 종목 조회 (시총 상위 기준). `?top=10`

### `POST /api/market-board/sparklines`
복수 종목 1년 주봉 종가 배치 조회. 바디: `{"items": [{"code": "005930", "market": "KR"}]}`

### `POST /api/market-board/intraday-ohlc`
복수 종목 당일 OHLC 배치 조회. 바디: `{"items": [{"code": "005930", "market": "KR"}]}`. 응답: `{"005930": {"open": 71000, "high": 72500, "low": 70500, "close": 72000, "prev_close": 71500}}`. 캐시: 장중 6분 / 장외 6시간. yfinance `history(period="5d")` 기반.

### `GET /api/market-board/custom-stocks`
시세판 별도 등록 종목 목록. 응답: `{"items": [...]}`

### `POST /api/market-board/custom-stocks`
별도 종목 추가. 바디: `{"code": "005930", "name": "삼성전자", "market": "KR"}`. 에러: 409(중복)

### `DELETE /api/market-board/custom-stocks/{code}?market=KR`
별도 종목 삭제. 에러: 404(미등록)

### `GET /api/market-board/order`
시세판 종목 표시 순서 조회. 응답: `{"items": [{"code": "005930", "market": "KR", "position": 0}, ...]}`

### `PUT /api/market-board/order`
시세판 종목 표시 순서 저장 (전체 교체). 바디: `{"items": [{"code": "005930", "market": "KR"}, ...]}`. 응답: `{"ok": true}`

### `GET /api/market-board/prices?codes=&market=KR` (2026-05-12 신규)
다중심볼 가격 일괄 폴링 — `WS /ws/market-board` 대체. 쿼리: `codes`(콤마 구분, 최대 50개) + `market='KR'|'US'`(기본 `KR`). 응답: `{"prices": {"005930": {"price", "change", "change_pct", "prev_close", "volume", "sign"}, ...}}`. yfinance `yf.Tickers(...)` fast_info 일괄 1차 → 빈응답·예외 시 KIS REST `FHKST01010100` 폴백(분당 한도 보호 N≤20 가드). 부분 실패 시에도 200 + 성공 종목만 반환. in-memory TTL 캐시 장중 10s / 장외 60s. 에러: 400(`codes` 빈 값/50개 초과), 422(missing).

### ~~`WS /ws/market-board`~~ (2026-05-12 폐지)

> **제거됨.** 다중심볼 실시간 시세 WebSocket은 동일 KIS 계정을 공유하는 외부 자동매매 시스템과 동시구독 41건 한도를 잠식해 충돌 원인이 되었음. `GET /api/market-board/prices` REST 일괄 폴링으로 대체. 호가창(`/ws/quote/{symbol}`)·체결통보(`/ws/execution-notice`)는 유지.

---

## 에이전트 API 활용 맵

AI 에이전트 팀(`.claude/agents/`)이 호출하는 엔드포인트 매핑. 에이전트는 HTTP API를 통해서만 접근하며, 서비스/DB에 직접 접근하지 않는다.

| 에이전트 | 엔드포인트 | 용도 |
|---------|-----------|------|
| MacroSentinel | `GET /api/macro/sentiment` | VIX + 버핏지수 + 공포탐욕 → 체제 판단 |
| MacroSentinel | `GET /api/macro/indices` | 4대 지수 동향 |
| MacroSentinel | `GET /api/macro/investor-quotes` | 투자대가 발언 |
| MacroSentinel | `GET /api/macro/news` | 시장 뉴스 |
| ValueScreener | `GET /api/screener/stocks` | PER/PBR/ROE 멀티팩터 스크리닝 |
| ValueScreener | `GET /api/detail/{code}/report` | 상위 후보 CAGR 확인 |
| MarginAnalyst | `POST /api/advisory/{code}/refresh` | 기본적+기술적 데이터 수집 |
| MarginAnalyst | `GET /api/advisory/{code}/data` | 캐시된 분석 데이터 |
| MarginAnalyst | `POST /api/advisory/{code}/analyze` | GPT 3전략 리포트 |
| MarginAnalyst | `GET /api/advisory/{code}/ohlcv` | 기간별 OHLCV + 기술지표 |
| MarginAnalyst | `GET /api/detail/{code}/report` | 10년 재무 + CAGR |
| MarginAnalyst | `GET /api/detail/{code}/valuation` | PER/PBR 히스토리 |
| OrderAdvisor | `GET /api/balance` | 현재 포트폴리오 + 예수금 |
| OrderAdvisor | `GET /api/order/buyable` | 매수 가능 금액 |
| OrderAdvisor | `GET /api/order/open` | 미체결 주문 (중복 방지) |
| OrderAdvisor | `POST /api/order/reserve` | 예약주문 등록 (사용자 승인 후) |

> 에이전트 정의: `.claude/agents/`, 오케스트레이터: `.claude/skills/value-invest/skill.md`

---

## 사용자 KIS 자격증명 — `routers/me_kis.py` (2026-05-04 Phase 4)

### `POST /api/me/kis`
사용자 본인의 KIS 자격증명 등록/갱신 + 즉시 검증.

Request body:
```json
{
  "app_key": "PSxxxxxxxxxxxxx",
  "app_secret": "xxxxxxxxxxxxxxx",
  "acnt_no": "12345678",
  "acnt_prdt_cd_stk": "01",
  "acnt_prdt_cd_fno": "03",
  "hts_id": "MYHTSID",
  "base_url": "https://openapi.koreainvestment.com:9443"
}
```

검증: KIS `/oauth2/tokenP` 호출 → 성공 시 AES-GCM 암호화 후 `UserKisCredentials` 저장 + `validated_at` 기록. 실패 시 `ExternalAPIError(502, "KIS 인증 실패: ...")`.

Response 200:
```json
{
  "validated_at": "2026-05-04T10:30:00+09:00",
  "is_active": true
}
```

### `GET /api/me/kis`
현재 등록 상태 조회. 마스킹된 값만 반환.

Response:
```json
{
  "is_registered": true,
  "is_active": true,
  "app_key_masked": "PS••••••••XXXX",
  "validated_at": "2026-05-04T10:30:00+09:00",
  "acnt_no_masked": "••••5678",
  "acnt_prdt_cd_stk": "01",
  "acnt_prdt_cd_fno": "03"
}
```

`app_secret`은 응답에서 영구히 노출되지 않음.

### `DELETE /api/me/kis`
자격증명 삭제 + 토큰 캐시 invalidate.

### `POST /api/me/kis/validate`
저장된 자격증명을 다시 KIS에 검증. `validated_at` 갱신.

---

## 관리자 사용자 관리 — `routers/admin_users.py` (2026-05-04 Phase 4)

모두 `require_admin` 의존성. audit_log에 변경 기록.

### `GET /api/admin/users?q=&limit=20&offset=0`
사용자 목록 검색/페이지네이션.

Response:
```json
{
  "items": [
    {
      "id": 1,
      "username": "admin",
      "name": "관리자",
      "role": "admin",
      "has_kis": true,
      "created_at": "2026-04-25T00:00:00+09:00"
    }
  ],
  "total": 12
}
```

### `GET /api/admin/users/{user_id}`
사용자 상세.

### `PATCH /api/admin/users/{user_id}`
Request body:
```json
{
  "role": "admin",
  "reset_password": true
}
```
`reset_password=true`면 임시 비밀번호 발급. 응답에 평문 임시 비밀번호 1회 노출.

### `DELETE /api/admin/users/{user_id}`
사용자 삭제(또는 soft delete). 자기 자신 삭제 불가.

---

## 페이지별 이용 통계 — `routers/admin_stats.py` (2026-05-04 Phase 4)

### `GET /api/admin/page-stats?from=YYYY-MM-DD&to=YYYY-MM-DD&top=20`
관리자 전용. 경로별 호출 횟수 + 평균/p95 latency + 유저 수 + 일별 시계열.

Response:
```json
{
  "period": {"from": "2026-05-01", "to": "2026-05-04"},
  "top_paths": [
    {
      "path": "/api/watchlist/dashboard",
      "calls": 1234,
      "avg_latency_ms": 145,
      "p95_latency_ms": 620,
      "unique_users": 8
    }
  ],
  "timeseries": [
    {"date": "2026-05-01", "path": "/api/watchlist/dashboard", "calls": 320}
  ]
}
```

데이터 소스: `PageView` 모델(FastAPI 미들웨어가 매 요청 비동기 INSERT, 제외 path: /api/health, /assets/*, /static/*, /ws/*, /api/admin/page-stats).

---

## 로컬 백테스트 — `routers/backtest.py` (2026-05-07)

stock-manager 자체 Python 일봉 엔진. 외부 MCP backtester(Lean) 미의존. KR 종목만 지원(MVP). 1~10종목 균등 배분 포트폴리오 시뮬레이션. 4개 KR 단기/추세 전략 프리셋 내장.

### `GET /api/backtest/local/presets`
인증 필요. MCP 무관, 즉시 응답. 4개 KR 전략 메타데이터(`id`, `name`, `description`, `default_params`, `param_schema`) 반환.

```json
{
  "presets": [
    {"id": "momentum", "name": "상한가 모멘텀", ...},
    {"id": "volatility_breakout", "name": "변동성 돌파", ...},
    {"id": "donchian_swing", "name": "20일 신고가 스윙", ...},
    {"id": "long_tail_volatility", "name": "롱테일 변동성", ...}
  ]
}
```

### `POST /api/backtest/run/local`
인증 필요. 동기 응답(MCP 비동기 2단계와 다름).

Request Body (`LocalBacktestBody`):
```json
{
  "preset": "momentum",
  "symbols": ["005930", "000660", "035720"],
  "market": "KR",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 10000000,
  "commission_rate": 0.0015,
  "tax_rate": 0.0023,
  "slippage": 0.001,
  "params": null
}
```
- `symbols`: `Field(min_length=1, max_length=10)` — 1~10개 KR 종목코드
- `market`: "KR"만 허용. 그 외 → ServiceError(400)
- `params`: 전략별 default_params 오버라이드(생략 가능)

Response:
```json
{
  "job_id": "local-{uuid}",
  "status": "completed",
  "result": {
    "preset": "momentum",
    "symbols": ["005930", "000660", "035720"],
    "market": "KR",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "params": {...},
    "equity_curve": [{"date": "2024-01-02", "value": 10000000}, ...],
    "trades": [{"symbol": "005930", "entry_date": "...", "entry_price": ..., "exit_date": "...", "exit_price": ..., "qty": ..., "pnl_pct": ..., "reason": "next_open|stop_loss|..."}, ...],
    "per_symbol_contribution": {
      "005930": {"return_pct": 12.5, "trades": 8, "contribution_pct": 4.2},
      ...
    },
    "metrics": {
      "total_return_pct": 8.7,
      "cagr": 8.7,
      "sharpe_ratio": 1.2,
      "sortino_ratio": 1.8,
      "max_drawdown": -12.4,
      "win_rate": 56.3,
      "profit_factor": 1.45,
      "total_trades": 24
    },
    "failures": []
  }
}
```

검증/에러:
- `symbols` 0개 또는 11개↑ → 422 (Pydantic)
- 알 수 없는 `preset` → 400 (`ServiceError`)
- `market != "KR"` → 400 (`ServiceError("로컬 백테스트는 KR만 지원합니다")`)
- 모든 종목 데이터 fetch 실패 → 400 (`ServiceError`)
- 부분 실패(일부 종목 실패) → 200 + `failures` 배열에 기록 후 나머지로 시뮬레이션 진행

저장: `BacktestJob`(strategy_type=`"local"`, `symbol`=`symbols[0]`, 신규 `symbols` JSON 컬럼에 전체 리스트). 기존 MCP 백테스트 흐름(`run/preset`/`run/custom`/`run/batch`) 100% 미터치.
