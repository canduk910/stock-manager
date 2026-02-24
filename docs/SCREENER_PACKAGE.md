# screener/ 패키지

KRX(pykrx) + DART 데이터 기반 전종목 멀티팩터 스크리너. CLI와 웹 API에서 공용.

---

## 모듈 구성

| 파일 | 역할 |
|------|------|
| `service.py` | CLI 독립 비즈니스 로직 (필터/정렬/날짜 정규화) |
| `cli.py` | Click CLI (`python -m screener screen/earnings`) |
| `krx.py` | pykrx 전종목 시세 + 펀더멘털 수집 |
| `dart.py` | DART 정기보고서 제출 목록 조회 |
| `display.py` | Rich 테이블 렌더링 + CSV 내보내기 |
| `cache.py` | SQLite 캐시 (영구, TTL 없음) |

---

## `service.py` — 비즈니스 로직

CLI(`cli.py`)와 API 라우터(`routers/screener.py`) 양쪽에서 공용으로 사용한다.
`ScreenerValidationError` 예외를 발생시키며, CLI는 `click.BadParameter`로, API는 `HTTPException(422)`로 변환한다.

### 함수

| 함수 | 설명 |
|------|------|
| `normalize_date(date_str)` | `YYYYMMDD`, `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD` → `YYYYMMDD`. None이면 오늘. |
| `parse_sort_spec(sort_str, order)` | `"ROE desc, PER asc"` → `[("roe", True), ("per", False)]`. 유효 필드: per, pbr, roe, mktcap |
| `apply_filters(stocks, ...)` | 시장/PER/PBR/ROE/적자기업 필터 적용 |
| `sort_stocks(stocks, sort_specs)` | 다중 기준 정렬. None 값은 항상 마지막으로 밀어냄 |

### `apply_filters()` 파라미터

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `market` | `str \| None` | `KOSPI` 또는 `KOSDAQ` |
| `per_min` | `float \| None` | PER 최소값 |
| `per_max` | `float \| None` | PER 최대값 |
| `pbr_max` | `float \| None` | PBR 최대값 |
| `roe_min` | `float \| None` | ROE 최소값 (%) |
| `include_negative` | `bool` | True면 PER < 0 종목 포함 |

---

## `krx.py` — KRX 데이터 수집

pykrx 라이브러리를 사용하여 전종목 시세/펀더멘털 데이터를 수집한다.

### 함수

| 함수 | 설명 |
|------|------|
| `get_all_stocks(date_str)` | YYYYMMDD → 전종목 통합 데이터 리스트 |

### `get_all_stocks()` 반환값

```python
[
    {
        "code": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "per": 12.5,      # 0이면 None
        "pbr": 1.2,       # 0이면 None
        "roe": 10.0,      # EPS/BPS*100, BPS=0이면 None
        "mktcap": 418000000000000,  # 시가총액 (원)
    },
    ...
]
```

### 내부 동작

1. `get_market_ticker_list(date, market)` — KOSPI/KOSDAQ 종목코드 집합
2. `get_market_fundamental(date, market="ALL")` — PER/PBR/EPS/BPS
3. `get_market_cap(date, market="ALL")` — 시가총액
4. `get_market_ticker_name(ticker)` — 종목명
5. ROE = EPS / BPS * 100 (BPS ≠ 0일 때)

결과는 `screener_cache.db`에 캐싱 (키: `stocks_merged:{date}`).

---

## `dart.py` — DART 정기보고서 조회

DART `list.json` API로 정기보고서(사업/반기/분기) 제출 목록을 조회한다.

### 함수

| 함수 | 설명 |
|------|------|
| `fetch_filings(start_date, end_date)` | 기간별 정기보고서 제출 목록 |

### `fetch_filings()` 동작

- `pblntf_ty=A` (정기공시) 단일 쿼리 — `pblntf_detail_ty` 미사용으로 중복 방지
- `report_nm` 텍스트 기반 분류: "사업보고서" / "반기보고서" / "분기보고서"
- `rcept_no` 기준 중복 제거
- 비상장 기업 제외 (`stock_code` 없는 항목)
- 페이지네이션 처리 (100건 단위)
- Rate limit: 0.3초 간격, 요청 제한(020) 시 1초 대기 후 재시도

### 반환값

```python
[
    {
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "report_type": "사업보고서",     # "사업보고서" | "반기보고서" | "분기보고서"
        "report_name": "사업보고서 (2024.12)",
        "rcept_no": "20250220001567",
        "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20250220001567",
        "rcept_dt": "20250220",
        "flr_nm": "삼성전자",
    },
    ...
]
```

---

## `display.py` — CLI 출력

Rich 라이브러리 기반 터미널 출력.

### 함수

| 함수 | 설명 |
|------|------|
| `print_earnings_table(filings, date_str)` | 정기보고서 테이블 |
| `print_screen_table(stocks, date_str, title)` | 스크리닝 결과 테이블 |
| `export_earnings_csv(filings, date_str)` | 공시 CSV 저장 → 파일경로 반환 |
| `export_screen_csv(stocks, date_str)` | 스크리닝 CSV 저장 → 파일경로 반환 |

- 시가총액 포맷: 1조 이상 `X.Y조`, 미만 `X,XXX억`
- CSV 인코딩: `utf-8-sig` (Excel 호환)
- 파일명: `earnings_{date}.csv`, `screen_{date}_{time}.csv`

---

## `cache.py` — SQLite 캐시

프로젝트 루트의 `screener_cache.db`에 데이터를 저장한다.

### 함수

| 함수 | 설명 |
|------|------|
| `get_cached(key)` | 캐시 조회 (없으면 None) |
| `set_cached(key, value)` | 캐시 저장 |
| `clear_cache()` | 전체 삭제 |

### `stock/cache.py`와의 차이

- TTL 없음 (영구 저장, 동일 키로 덮어쓰기만 가능)
- `delete_prefix()` 없음
- 위치: 프로젝트 루트 `screener_cache.db` (stock/cache.py는 `~/stock-watchlist/cache.db`)

### 캐시 키

| 키 패턴 | 용도 |
|---------|------|
| `stocks_merged:{date}` | KRX 전종목 통합 데이터 |
| `dart_filings:{start}:{end}` | DART 정기보고서 목록 |

---

## CLI 명령어

### `python -m screener screen`

전종목 멀티팩터 스크리닝.

| 옵션 | 설명 |
|------|------|
| `--date` | 조회 날짜 (기본: 오늘) |
| `--sort-by` | 정렬 기준. `"ROE desc, PER asc"` |
| `--order` | 단일 정렬 시 방향 (asc/desc) |
| `--top N` | 상위 N개만 출력 |
| `--per-range MIN MAX` | PER 범위 |
| `--pbr-max` | PBR 최대값 |
| `--roe-min` | ROE 최소값 (%) |
| `--market` | KOSPI 또는 KOSDAQ |
| `--include-negative` | 적자기업 포함 |
| `--earnings-today` | 당일 실적발표 종목만 |
| `--export csv` | CSV 내보내기 |

### `python -m screener earnings`

정기보고서 제출 종목 조회.

| 옵션 | 설명 |
|------|------|
| `--date` | 조회 날짜 (기본: 오늘) |
| `--export csv` | CSV 내보내기 |

### 사용 예시

```bash
# KOSPI 시장, ROE 10% 이상, PER 0~15, 상위 20개
python -m screener screen --market KOSPI --roe-min 10 --per-range 0 15 --top 20

# 다중 정렬: ROE 내림차순 → PER 오름차순
python -m screener screen --sort-by "ROE desc, PER asc"

# 당일 실적발표 종목만 PER 순 정렬
python -m screener screen --earnings-today --sort-by PER

# 오늘 공시 조회
python -m screener earnings

# 특정 날짜 공시 + CSV 내보내기
python -m screener earnings --date 2025-02-20 --export csv
```
