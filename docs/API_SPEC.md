# API 엔드포인트 설계

모든 API는 `/api` 접두사를 사용한다. 모든 핸들러는 `def`(sync) — pykrx/requests가 동기 라이브러리이므로 FastAPI가 threadpool에서 자동 실행한다.

Swagger UI: `http://localhost:8000/docs`

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
      "per": 12.5, "pbr": 1.2, "eps": 5000, "bps": 50000,
      "roe": 10.0, "mktcap": 3000000000000, "close": 70000,
      "change_pct": 1.5
    }
  ]
}
```

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
