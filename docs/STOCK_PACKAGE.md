# stock/ 패키지

관심종목 관리 + 종목 데이터 수집 패키지. CLI와 웹 API 양쪽에서 사용한다.

데이터 저장: `~/stock-watchlist/` (watchlist.db + cache.db)

---

## 모듈 구성

| 파일 | 역할 |
|------|------|
| `db_base.py` | SQLite 공용 유틸. `connect(db_name, init_fn)` contextmanager (DB 생성/init 중복 방지), `row_to_dict()`. 모든 store 모듈의 공통 기반. |
| `store.py` | 관심종목 CRUD (SQLite) |
| `order_store.py` | 주문 이력 + 예약주문 CRUD (SQLite, `orders.db`) |
| `advisory_store.py` | AI자문 종목/캐시/리포트 CRUD (SQLite, `advisory.db`). 리포트 히스토리 조회 지원. |
| `advisory_fetcher.py` | 15분봉 OHLCV 수집 + 기술적 지표 계산 + 사업부문 추론 |
| `symbol_map.py` | 종목코드 ↔ 종목명 매핑 (pykrx 기반, fallback 포함). 서버 시작 시 background thread로 pre-warm. |
| `market.py` | yfinance 기반 국내 시세/펀더멘털 수집. `_is_kr_trading_hours()` / `_is_us_trading_hours()` 장중판별 헬퍼 포함. TTL 장중/장외 자동 분리. |
| `dart_fin.py` | OpenDart 재무데이터 수집 (IS + BS + CF) |
| `yf_client.py` | yfinance 해외주식 데이터 수집 + 밸류에이션 히스토리 추정 |
| `sec_filings.py` | SEC EDGAR 미국 공시 조회 |
| `utils.py` | `is_domestic(code)` 국내/해외 구분. `is_fno(code)` FNO 단축코드 여부 판별. |
| `display.py` | Rich 테이블 렌더링 + CSV 내보내기 |
| `cache.py` | SQLite 캐시 (TTL 지원) |
| `cli.py` | Click CLI (`python -m stock watch ...`) |

---

## `order_store.py` — 주문 이력 + 예약주문

`~/stock-watchlist/orders.db` (SQLite). `orders`와 `reservations` 두 테이블 관리. DB 파일이 없으면 최초 접속 시 자동 생성.

### 주문 이력 함수 (`orders` 테이블)

| 함수 | 설명 |
|------|------|
| `insert_order(symbol, symbol_name, market, side, order_type, price, quantity, currency, memo, order_no, org_no, kis_response)` | 신규 주문 기록 (status=PLACED) |
| `update_order_status(id, status, filled_quantity, filled_price)` | 주문 상태 갱신 |
| `list_orders(symbol, market, status, date_from, date_to, limit)` | 주문 이력 조회 (필터 지원) |
| `list_active_orders()` | PLACED/PARTIAL 상태 주문만 반환 (대사 용도) |

주문 상태값: `PLACED` / `PARTIAL` / `FILLED` / `CANCELLED` / `CANCEL_REQUESTED` / `MODIFY_REQUESTED` / `REJECTED` / `UNKNOWN`

### 예약주문 함수 (`reservations` 테이블)

| 함수 | 설명 |
|------|------|
| `insert_reservation(symbol, symbol_name, market, side, order_type, price, quantity, condition_type, condition_value, memo)` | 예약주문 등록 (status=WAITING) |
| `update_reservation_status(id, status, result_order_no, triggered_at)` | 예약주문 상태 갱신 |
| `list_reservations(status)` | 예약주문 목록 (status 필터 선택) |
| `delete_reservation(id)` | 예약주문 삭제 (WAITING 상태만 가능) |

예약주문 상태값: `WAITING` / `TRIGGERED` / `EXECUTED` / `FAILED` / `CANCELLED`

---

## `store.py` — 관심종목 CRUD

`~/stock-watchlist/watchlist.db` (SQLite)에 관심종목 목록을 저장한다.

- 최초 접속 시 `watchlist` 테이블 자동 생성 (`CREATE TABLE IF NOT EXISTS`)
- 기존 `watchlist.json` 파일이 있으면 자동 마이그레이션 후 `watchlist.json.bak`으로 백업
- Docker 환경: `watchlist-data` 네임드 볼륨 마운트로 컨테이너 재시작 시 데이터 보존

### 함수

| 함수 | 설명 |
|------|------|
| `all_items()` | 전체 목록 반환 (added_date, code 순 정렬) |
| `get_item(code)` | 단일 종목 조회 (없으면 None) |
| `add_item(code, name, memo)` | 추가 (중복이면 False) |
| `remove_item(code)` | 삭제 (없으면 False) |
| `update_memo(code, memo)` | 메모 수정 |

### 테이블 스키마

```sql
CREATE TABLE watchlist (
    code       TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    added_date TEXT NOT NULL,
    memo       TEXT NOT NULL DEFAULT ''
)
```

### 반환 dict 구조

```python
{
    "code": "005930",
    "name": "삼성전자",
    "added_date": "2025-02-20",
    "memo": "반도체 대장"
}
```

---

## `advisory_store.py` — AI자문 CRUD

`~/stock-watchlist/advisory.db` (SQLite). 3개 테이블 관리.

### 테이블 구조

```sql
advisory_stocks   -- 자문종목 목록 (code, market 복합 PK)
advisory_cache    -- 기본적/기술적 분석 데이터 JSON (code, market 복합 PK, upsert)
advisory_reports  -- AI 리포트 이력 (autoincrement id)
```

### 함수

| 함수 | 설명 |
|------|------|
| `add_stock(code, market, name, memo)` | 자문종목 추가. 이미 존재하면 False 반환 |
| `remove_stock(code, market)` | 자문종목 삭제. 없으면 False 반환 |
| `all_stocks()` | 전체 목록 (added_date 역순) |
| `get_stock(code, market)` | 단일 종목 조회. 없으면 None |
| `save_cache(code, market, fundamental, technical)` | 분석 데이터 upsert |
| `get_cache(code, market)` | 캐시 조회. 없으면 None |
| `save_report(code, market, model, report)` | AI 리포트 저장. report_id 반환 |
| `get_latest_report(code, market)` | 최신 리포트 조회. 없으면 None |
| `get_report_history(code, market, limit=20)` | 히스토리 목록 (본문 제외, 최신순). id/generated_at/model 포함. |
| `get_report_by_id(report_id)` | 특정 ID 리포트 상세 조회 (본문 포함). |

---

## `advisory_fetcher.py` — 기술적 분석 데이터 수집

15분봉 OHLCV 수집 + 순수 Python 기술적 지표 계산 + 사업부문 추론.

### 토큰 캐싱 (`_get_kis_token`)

KIS API의 토큰 발급 분당 1회 제한에 대응하기 위해 모듈 수준에서 토큰을 캐싱한다.
만료 60초 전에 자동 재발급.

### 함수

| 함수 | 설명 |
|------|------|
| `fetch_15min_ohlcv_kr(code)` | KIS 1분봉 4회 호출 → 15분 resample. 30봉 미만 시 yfinance fallback. 최대 300봉 반환. |
| `fetch_15min_ohlcv_us(code)` | yfinance `.history(period='5d', interval='15m')`. 최대 300봉 반환. |
| `fetch_ohlcv_by_interval(code, market, interval, period)` | 타임프레임/기간 지정 OHLCV 수집 후 `calc_technical_indicators()` 자동 호출. `{"ohlcv": [...], "indicators": {...}}` 반환. interval=`15m`/`60m`/`1d`/`1wk`. yfinance 최대 기간 자동 조정. |
| `calc_technical_indicators(ohlcv)` | 기술적 지표 계산. 데이터 부족 시 None 처리. 최대 300봉 입력 지원. **ATR(14, Wilder법)**, **MA배열** (`ma_alignment`: 정배열/역배열/혼합), **K=0.3·0.5·0.7 변동성 돌파 목표가** 추가. |
| `fetch_segments_kr(code, name)` | OpenAI로 국내 기업 사업부문 추론 (AI추정 표시) |

#### `fetch_15min_ohlcv_kr` 동작 방식

KIS `FHKST03010200` (1분봉) API를 시간대별로 4회 호출하여 하루 전체 데이터를 수집한다.
수집 후 pandas `resample("15min")`으로 15분봉으로 변환. 최대 300봉 반환.

| 호출 순서 | `fid_input_hour_1` | 설명 |
|----------|---------------------|------|
| 1 | `"153000"` | 장 마감 기준 (장중 + 오후 데이터) |
| 2 | `"143000"` | 오후 2시 이전 |
| 3 | `"133000"` | 오후 1시 이전 |
| 4 | `"123000"` | 오후 12시 이전 |

결과 30봉 미만이면 yfinance fallback (`_fetch_ohlcv_kr_yf`):
- `yfinance Ticker(code.KS/.KQ).history(period="5d", interval="15m")` 사용

#### `fetch_ohlcv_by_interval` 동작 방식

interval/period를 지정하여 yfinance로 OHLCV를 수집하고, 기술적 지표를 즉시 계산하여 반환한다.
`/api/advisory/{code}/ohlcv` 엔드포인트에서 직접 사용.

**interval → yfinance 매핑 및 최대 기간**:

| interval | yfinance interval | 최대 period |
|---------|------------------|------------|
| `15m` | `15m` | `60d` |
| `60m` | `60m` | `2y` |
| `1d` | `1d` | `10y` |
| `1wk` | `1wk` | `10y` |

period가 최대치를 초과하면 자동으로 최대값으로 조정.
국내(KR): `_kr_yf_ticker_str(code)`로 `.KS`/`.KQ` suffix 자동 선택.

필수 파라미터:

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| `fid_etc_cls_code` | `""` | KIS 필수 파라미터 (누락 시 EGW00131 오류) |
| `fid_pw_data_incu_yn` | `"Y"` | 이전 데이터 포함 |

KIS 키 미설정 시 즉시 yfinance fallback 시도. yfinance도 실패 시 `[]` 반환.

#### `calc_technical_indicators` 반환 구조

```python
{
    "macd": {"macd": [...], "signal": [...], "histogram": [...], "times": [...]},
    "rsi": {"values": [...], "times": [...]},      # Wilder's RSI 14기간
    "stoch": {"k": [...], "d": [...], "times": []}, # %K 14기간, %D SMA(3)
    "bb": {"upper": [...], "mid": [...], "lower": [...], "times": []},  # SMA(20), ±2σ
    "ma": {"ma5": [...], "ma20": [...], "ma60": [...], "times": []},
    "volatility_target": float | None,  # (전일고가-전일저가)×0.5 + 당일시가 (K=0.5)
    "current_signals": {
        "macd_cross": "golden" | "dead" | "none",
        "rsi_signal": "overbought" | "oversold" | "neutral",
        "rsi_value": float | None,
        "stoch_signal": "overbought" | "oversold" | "neutral",
        "stoch_k": float | None,
        "above_ma20": bool,
        "ma20": float | None,
        "ma5": float | None,          # 추가
        "ma60": float | None,         # 추가
        "ma_alignment": "정배열" | "역배열" | "혼합" | None,  # 추가
        "atr": float | None,          # ATR(14, Wilder법) 추가
        "volatility_target_k03": float | None,  # K=0.3 목표가 추가
        "volatility_target_k05": float | None,  # K=0.5 목표가 추가
        "volatility_target_k07": float | None,  # K=0.7 목표가 추가
        "current_price": float | None,
    }
}
```

기술지표 구현 방식 (외부 TA 라이브러리 미사용):
- MACD: EMA(12) - EMA(26), Signal = EMA(9)
- RSI: Wilder's RSI (14기간)
- Stochastic: %K 14기간, %D = SMA(%K, 3)
- 볼린저밴드: SMA(20), ±2σ
- ATR: `max(H-L, |H-PC|, |L-PC|)`, Wilder 평균법 (14기간)
- 변동성 돌파 목표가: `당일시가 + (전일H-전일L) × K` (K=0.3/0.5/0.7)

---

## `symbol_map.py` — 종목코드 매핑

pykrx로 KOSPI + KOSDAQ 전 종목 코드/이름/시장을 수집하고 7일간 캐싱한다.

### 함수

| 함수 | 반환 | 설명 |
|------|------|------|
| `get_symbol_map(refresh)` | `dict[str, dict]` | 전체 종목 맵 (`{code: {name, market}}`) |
| `code_to_name(code)` | `str \| None` | 코드 → 종목명. 맵 실패 시 `get_market_ticker_name()` fallback |
| `code_to_market(code)` | `str \| None` | 코드 → 시장 (KOSPI/KOSDAQ) |
| `name_to_results(query)` | `list[tuple]` | 이름 부분일치 검색. `[(code, name, market)]` |
| `resolve(code_or_name)` | `tuple[str, str] \| None` | 6자리 코드 또는 정확한 이름 → `(code, name)`. 복수 매칭이면 None |

- 캐시 키: `symbol_map:v1`, TTL 7일
- `resolve()`은 웹 API(`routers/watchlist.py`)와 CLI 양쪽에서 사용
- **pykrx fallback**: `get_market_ticker_list()`가 빈 결과 반환 시(KRX 서버 이슈/주말), `code_to_name()`은 `get_market_ticker_name(code)`를 직접 호출하여 종목명 조회
- `_find_latest_trading_day()`: 최대 10일 소급하여 실제 거래일 탐색 (주말/공휴일 대응)

---

## `market.py` — 시세/펀더멘털

> **2026-02 변경**: KRX 서버가 로그인 필수로 변경됨에 따라 pykrx 스크래핑 전면 중단.
> yfinance `.KS`(KOSPI) / `.KQ`(KOSDAQ) suffix 기반으로 완전 전환.

### 함수

| 함수 | 설명 | 캐시 TTL |
|------|------|---------|
| `fetch_price(code, refresh)` | 현재가/등락/시가총액 | 1시간 |
| `fetch_detail(code, refresh)` | 시세 + 52주 고저 + PER/PBR + 업종/시장 | 6시간 |
| `fetch_valuation_history(code, years)` | 월말 PER/PBR 시계열 (KRX 인증 필요, 미인증 시 빈 배열) | 24시간 |
| `fetch_period_returns(code)` | 당일/3개월/6개월/1년 주가 수익률 (%) | 1시간 |
| `fetch_market_metrics(code)` | 잔고/AI자문용 계량지표 (시가총액·PER·PBR·ROE·배당수익률) | 6시간 |

#### yfinance ticker 선택 (`_kr_yf_ticker_str`)

국내 종목코드로 `.KS`와 `.KQ` 양쪽을 시도해 market_cap + shares 점수가 높은 suffix를 선택. 결과 7일 캐시.

### `fetch_price()` 반환값

```python
{
    "close": 70000,       # 종가 (원)
    "change": 1000,       # 전일대비 (원)
    "change_pct": 1.45,   # 등락률 (%)
    "mktcap": 418000000000000,  # 시가총액 (원)
    "shares": 5969782550, # 상장주식수
    "trading_date": "20260307",
}
```

### `fetch_detail()` 반환값

`fetch_price()` + 추가 필드:

```python
{
    ...fetch_price 필드,
    "market_type": "KOSPI",  # or "KOSDAQ"
    "sector": "Technology",  # yfinance 영문 반환
    "high_52": 80000,        # 52주 최고가
    "low_52": 50000,         # 52주 최저가
    "per": 12.5,             # yfinance 국내 주식 미지원 → None 가능
    "pbr": 1.2,              # 동일
}
```

### `fetch_market_metrics()` 반환값

잔고 페이지 + AI자문 계량지표 + 관심종목 상세용. `t.info` 기반 (6시간 캐시).

```python
{
    "market_type": "KOSPI",
    "mktcap": 418000000000000,  # 원
    "per": 12.5,
    "pbr": 1.2,
    "roe": 8.5,              # returnOnEquity × 100 (%)
    "dividend_yield": 2.14,  # 우선순위: dividendYield(이미 %) → trailingAnnualDividendYield×100 → dividendRate/price×100. 무배당 시 None
    "dividend_per_share": 1444,  # dividendRate (연간 주당배당금, 원). 무배당 시 None
}
```

**배당수익률 fallback 우선순위** (NVO 등 ADR 오류 방지):
1. `dividendYield` — 이미 % 형태 (0.4 → 0.4%)
2. `trailingAnnualDividendYield × 100` — 소수점 형태 (0.004 → 0.4%)
3. `dividendRate / last_price × 100` — 연간 주당배당금으로 직접 계산 (0 < computed < 50% sanity check)

### `fetch_valuation_history()` 반환값

KRX 인증(KRX_ID/KRX_PASSWORD) 필요. 미인증 시 빈 배열 반환.

```python
[
    {"date": "2016-02", "per": 7.69, "pbr": 1.24},
    ...
]
```

### 제약사항

| 항목 | 상태 |
|------|------|
| PER/PBR | yfinance 국내 주식 미지원 → None 반환 가능 |
| 섹터명 | 영문 반환 (한국어 변환 미지원) |
| 밸류에이션 히스토리 | KRX 로그인 필수 → 일반적으로 빈 배열 |

### 장중/장외 TTL 분리

`_is_kr_trading_hours()` (KST 09:00~15:30) / `_is_us_trading_hours()` (ET 09:30~16:00, DST 자동 반영) 두 헬퍼로 캐시 TTL을 자동 조정합니다.

| 함수 | 장중 TTL | 장외 TTL |
|------|---------|---------|
| `fetch_price` (국내) | 6분 | 6시간 |
| `fetch_period_returns` (국내) | 15분 | 6시간 |
| `fetch_market_metrics` (국내) | 1시간 | 12시간 |
| `fetch_price_yf` (해외) | 2분 | 30분 |
| `fetch_period_returns_yf` (해외) | 15분 | 6시간 |
| `fetch_detail_yf` (해외) | 30분 | 6시간 |
| `fetch_metrics_yf` (해외) | 30분 | 6시간 |

- `_is_us_trading_hours()`: `zoneinfo.ZoneInfo("America/New_York")` 사용 (Python 3.9+ 기본 내장). DST(서머타임) 자동 반영. ImportError 시 UTC-5 고정 fallback.
- 미국 공휴일은 판별 불가이나 yfinance가 빈 데이터를 반환하므로 기능 오류 없음.

---

## `yf_client.py` — 해외주식 데이터 수집

yfinance 기반 해외주식 데이터 수집. 일부 함수는 국내주식(`.KS`/`.KQ` suffix)에도 사용.

### 주요 함수

| 함수 | 설명 |
|------|------|
| `validate_ticker(code)` | ticker 유효성 확인 (price > 0 체크) |
| `fetch_price_yf(code)` | 현재가/등락/시가총액 조회 |
| `fetch_detail_yf(code)` | 시세 + 52주 고저 + PER/PBR/ROE + 배당수익률/주당배당금 |
| `fetch_period_returns_yf(code)` | 당일/3개월/6개월/1년 수익률 (%) |
| `fetch_financials_multi_year_yf(code, years)` | 최대 years개 연간 재무 (최대 4년) |
| `fetch_valuation_history_yf(code, years=5)` | 월별 PER/PBR 히스토리 추정 (신규) |
| `fetch_income_detail_yf(code, years)` | 손익계산서 세부 (AI자문용) |
| `fetch_balance_sheet_yf(code, years)` | 대차대조표 (AI자문용) |
| `fetch_cashflow_yf(code, years)` | 현금흐름표 (AI자문용) |
| `fetch_metrics_yf(code)` | PER/PBR/PSR/EV·EBITDA/ROE/ROA (AI자문 계량지표) |
| `fetch_segments_yf(code)` | 사업부문 매출비중 (best-effort) |
| `fetch_forward_estimates_yf(code, is_kr=False)` | 애널리스트 컨센서스 추정치. `is_kr=True` 시 `.KS`/`.KQ` suffix 자동. TTL 6시간. |

#### `fetch_forward_estimates_yf(code, is_kr=False)` — 애널리스트 컨센서스 추정치

yfinance `t.info`와 `t.analysis` DataFrame을 조합하여 포워드 가이던스를 반환한다.

```python
{
    "eps_current_year": 6.5,          # 현재 회계연도 EPS 추정
    "eps_forward": 7.2,               # 차기 연도 EPS 추정
    "forward_pe": 22.1,               # 포워드 PER (info['forwardPE'])
    "revenue_current": 2500.0,        # 현재 회계연도 매출 추정 (M USD 또는 억원)
    "revenue_forward": 2700.0,        # 차기 연도 매출 추정
    "net_income_estimate": 150.0,     # 현재 연도 순이익 추정 (eps × shares)
    "net_income_forward": 170.0,      # 차기 연도 순이익 추정
    "shares_outstanding": 100.0,      # 주식수 (M주)
    "target_mean_price": 85000,       # 목표주가 평균
    "target_high_price": 95000,       # 목표주가 최고
    "target_low_price": 70000,        # 목표주가 최저
    "num_analysts": 12,               # 분석가 수
    "recommendation": "buy",          # 투자의견 (buy/hold/sell 등)
    "current_fiscal_year_end": "2025-12",  # 현재 회계연도 종료월
}
```

- `net_income_estimate = eps_current_year × shares_outstanding` 계산
- `revenue_current/forward`: `t.analysis` DataFrame "+0y"/"+1y" 행 사용 (yfinance 버전에 따라 None 가능)
- 국내 주식은 애널리스트 커버리지 제한으로 일부 필드 None 허용
- KR/US 공통 함수. `is_kr=True` 시 `_kr_yf_ticker_str(code)`로 suffix 선택.

---

#### `fetch_valuation_history_yf(code, years=5)` — 해외주식 PER/PBR 추정

분기 재무 데이터와 일별 주가를 조합하여 월별 PER/PBR을 추정한다.

**알고리즘**:
1. `t.quarterly_financials` → 분기 EPS (Net Income / Diluted Shares 또는 Basic EPS 행)
2. `t.quarterly_balance_sheet` → 분기 BPS (Stockholders Equity / shares_outstanding)
3. `t.history(period)` → 일별 종가
4. 각 날짜의 TTM EPS: 직전 4분기 EPS 합산
5. 월말 기준 리샘플 → `PER = price / ttm_eps`, `PBR = price / bps`
6. 이상치 제거: PER > 500 또는 PER < 0, PBR < 0 제외

반환:
```python
[{"date": "2021-03", "per": 35.2, "pbr": 8.7}, ...]  # 과거 → 최신 순
```

#### `fetch_detail_yf()` — 배당수익률 fallback

```python
div_yield_pct  = info.get("dividendYield")        # 이미 % 형태 우선
trailing_yield = info.get("trailingAnnualDividendYield")
div_rate       = info.get("dividendRate")          # 연간 주당배당금(USD)
# 1순위: dividendYield
# 2순위: trailingAnnualDividendYield × 100
# 3순위: dividendRate / close × 100 (0 < computed < 50% sanity check)
```

---

## `dart_fin.py` — OpenDart 재무데이터

DART `fnlttSinglAcntAll` API로 사업보고서(연간) 재무제표를 수집한다.

**연도 계산 수정 (2026-03)**: `latest_year = today.year - 1` 고정 (월 경계 제거). 3월에도 전년도(2025) 사업보고서를 조회. 기존 4월 경계 로직 제거.

**첫 배치 fallback (2026-03)**: 첫 배치(최신 연도 묶음)가 빈 결과일 경우 `anchor-1` 연도로 재시도. 최신 사업보고서 미공시 기업도 이전 연도부터 정상 반환.

### 함수

| 함수 | 설명 | 캐시 TTL |
|------|------|---------|
| `fetch_financials(stock_code, refresh)` | 최근 1개 사업보고서 (당기/전기/전전기) | 24시간 |
| `fetch_financials_multi_year(stock_code, years)` | 최대 years개 사업연도 재무 | 24시간 |
| `fetch_income_detail_annual(stock_code, years)` | 손익계산서 세부 항목 (매출원가/SGA/EPS 포함) | 24시간 |
| `fetch_bs_cf_annual(stock_code, years)` | 대차대조표 + 현금흐름표 연간 데이터 | 24시간 |

#### `fetch_income_detail_annual` 반환값

```python
[
    {
        "year": 2024,
        "revenue": ...,           # 매출액 (원)
        "cogs": ...,              # 매출원가
        "gross_profit": ...,      # 매출총이익
        "sga": ...,               # 판매비와관리비
        "operating_income": ...,  # 영업이익
        "interest_income": ...,   # 이자수익
        "interest_expense": ...,  # 이자비용
        "pretax_income": ...,     # 법인세비용차감전순이익
        "tax_expense": ...,       # 법인세비용
        "net_income": ...,        # 당기순이익
        "eps": ...,               # 기본주당이익
        "oi_margin": ...,         # 영업이익률 (%)
        "net_margin": ...,        # 순이익률 (%)
        "dart_url": "https://..."
    }
]
```

#### `fetch_bs_cf_annual` 반환값

```python
{
    "balance_sheet": [
        {
            "year": 2024,
            "total_assets": ..., "current_assets": ..., "non_current_assets": ...,
            "cash_and_equiv": ..., "receivables": ..., "inventories": ...,
            "ppe": ..., "intangibles": ...,
            "total_liabilities": ..., "current_liabilities": ..., "non_current_liabilities": ...,
            "short_term_debt": ..., "long_term_debt": ...,
            "total_equity": ..., "retained_earnings": ...,
            "debt_ratio": ...,    # 부채비율 (%)
            "current_ratio": ...  # 유동비율 (%)
        }
    ],
    "cashflow": [
        {
            "year": 2024,
            "operating_cf": ..., "investing_cf": ..., "financing_cf": ...,
            "capex": ..., "depreciation": ..., "cash_change": ...,
            "free_cf": ...,       # operating_cf - capex
            "fcf_margin": ...     # FCF / revenue (%)
        }
    ]
}
```

#### `sj_div` 필터 규칙

| 구분 | sj_div 우선순위 |
|------|----------------|
| 손익계산서 (IS) | `"CIS"` → `"IS"` (연결 우선) |
| 대차대조표 (BS) | `"CBS"` → `"BS"` |
| 현금흐름표 (CF) | `"CCF"` → `"CF"` |

### `fetch_period_returns()` — 기간별 주가 수익률

pykrx로 최근 370일 OHLCV를 가져와 기간별 등락률을 계산한다.

```python
{
    "change_pct": 1.23,    # 당일 등락률 (최근 2 거래일 비교, %)
    "return_3m":  5.4,     # 90일 전 대비 수익률 (%)
    "return_6m":  -2.1,    # 180일 전 대비 수익률 (%)
    "return_1y":  12.7,    # 365일 전 대비 수익률 (%)
}
```

- 데이터 없으면 각 필드 `None`
- `routers/earnings.py`에서 공시 목록 각 종목에 병합하여 반환

---

### `fetch_financials()` — 최근 보고서

- 사업연도 후보 자동 결정: 4월 이후면 `[y-1, y-2, y-3]`, 이전이면 `[y-2, y-1, y-3]`
- 연결(CFS) 우선, 없으면 개별(OFS) 시도
- 추출 항목: 매출액, 영업이익, 당기순이익 (당기/전기/전전기)

### `fetch_financials_multi_year()` — 다연도 배치 수집

3년 단위 배치 전략:
- `fnlttSinglAcntAll`은 1회 호출로 당기(`thstrm`)/전기(`frmtrm`)/전전기(`bfefrmtrm`) 3개년을 반환
- 10년 데이터는 4회 API 호출로 수집 가능 (앵커 연도: latest, latest-3, latest-6, latest-9)
- 한번 연결(CFS)로 성공하면 이후 배치도 CFS로 고정

반환값:
```python
[
    {
        "year": 2015,                    # 정수
        "revenue": 2006535_0000_0000,    # 원
        "operating_income": 264134_0000_0000,
        "net_income": 190601_0000_0000,
        "rcept_no": "20160331000123",
        "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=...",
    },
    ...  # 과거 → 최신 순
]
```

### 내부 헬퍼

| 함수 | 설명 |
|------|------|
| `_load_corp_map()` | DART corpCode.xml에서 전체 상장법인 코드 맵 수집 (30일 캐싱) |
| `_fetch_corp_code(stock_code)` | 종목코드 → DART 기업고유번호 |
| `_call_fin_api(corp_code, bsns_year, fs_div)` | fnlttSinglAcntAll 원시 호출 |
| `_extract_accounts(items)` | 당기/전기/전전기 금액 동시 추출 (fetch_financials용) |
| `_extract_period_accounts(items, period_key)` | 특정 기간의 금액만 추출 (multi_year용) |

### `_ACCOUNT_KEYS` — 계정과목명 매핑

기업마다 DART 보고서에 기재하는 계정과목명이 다르다. 여러 변형을 튜플로 열거하여 순서대로 매칭한다.

```python
_ACCOUNT_KEYS = {
    "revenue":          ("매출액", "수익(매출액)", "영업수익", "매출"),
    "operating_income": ("영업이익", "영업이익(손실)", "영업손실"),
    "net_income":       ("당기순이익", "당기순이익(손실)", "당기순손익", "당기순손실"),
}
```

- 적자 기업은 `"영업손실"`, `"당기순손실"` 계정명 사용 (롯데케미칼 등)
- 새로운 계정명 변형이 필요하면 튜플에 추가

---

## `display.py` — CLI 출력

Rich 라이브러리를 사용한 터미널 테이블 렌더링과 CSV 내보내기를 담당한다.

### 출력 함수

| 함수 | 설명 |
|------|------|
| `print_watchlist(items)` | 관심종목 목록 테이블 |
| `print_dashboard(rows, export)` | 대시보드 테이블 (시세 + 재무) |
| `print_stock_info(item, detail, fin, export)` | 단일 종목 상세 (기본정보 패널 + 3개년 재무 테이블) |

### 내보내기

- `--export csv` 옵션으로 CSV 파일 생성
- 파일명: `dashboard_YYYYMMDD_HHMMSS.csv`, `info_{code}_YYYYMMDD_HHMMSS.csv`
- 인코딩: `utf-8-sig` (Excel 호환)

### 포맷팅 규칙

- 시가총액: 원 → 억원 (천단위 콤마)
- 등락률: 양수 = 초록, 음수 = 빨강 (CLI 색상, 웹과 상이)
- 영업이익률: 매출액/영업이익으로 계산
- 기간 레이블: `thstrm_dt`에서 파싱 → `YYYY/MM` 형식

---

## `cache.py` — SQLite 캐시

`~/stock-watchlist/cache.db`에 데이터를 캐싱한다. TTL(Time-To-Live) 기반 만료.

### 함수

| 함수 | 설명 |
|------|------|
| `get_cached(key)` | 캐시 조회 (만료/없으면 None) |
| `set_cached(key, value, ttl_hours)` | 캐시 저장 (기본 24시간) |
| `delete_cached(key)` | 단일 키 삭제 |
| `delete_prefix(prefix)` | 접두사 일괄 삭제 (`LIKE prefix%`) |

### 캐시 키 규칙

| 접두사 | 용도 | TTL |
|--------|------|-----|
| `symbol_map:` | 전 종목 코드/이름 맵 | 7일 |
| `market:price:` | 현재가/시가총액 | 1시간 |
| `market:detail:` | 상세 시세 | 1시간 |
| `market:valuation_hist:` | 월별 PER/PBR | 24시간 |
| `market:period_returns:` | 당일/3M/6M/1Y 수익률 | 1시간 |
| `dart:corp_map:` | 기업코드 맵 | 30일 |
| `dart:corp_code:` | 개별 기업코드 | 30일 |
| `dart:fin:` | 최근 재무 | 24시간 |
| `dart:fin_multi:` | 다연도 재무 | 24시간 |

### screener/cache.py와의 차이

| 항목 | `stock/cache.py` | `screener/cache.py` |
|------|-------------------|---------------------|
| 위치 | `~/stock-watchlist/cache.db` | 프로젝트 루트 `screener_cache.db` |
| TTL | 지원 (만료 시각 기반) | 미지원 (영구 저장) |
| `delete_prefix()` | 지원 | 미지원 |

---

## `cli.py` — Click CLI

`python -m stock watch` 명령어 그룹.

### 명령어

| 명령 | 설명 | 옵션 |
|------|------|------|
| `watch add <종목>` | 관심종목 추가 | `--memo`, `--refresh` |
| `watch remove <종목>` | 관심종목 삭제 | |
| `watch list` | 목록 출력 | |
| `watch memo <종목> <텍스트>` | 메모 수정 | |
| `watch dashboard` | 대시보드 | `--refresh`, `--export csv` |
| `watch info <종목>` | 단일 종목 상세 | `--refresh`, `--export csv` |

- `<종목>`: 6자리 코드 또는 종목명 허용
- 종목명이 복수 매칭이면 후보 목록 출력 후 종료
- `--refresh`: 캐시 무시하고 최신 데이터 조회
