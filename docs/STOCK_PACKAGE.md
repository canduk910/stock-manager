# stock/ 패키지

관심종목 관리 + 종목 데이터 수집 패키지. CLI와 웹 API 양쪽에서 사용한다.

데이터 저장: `~/stock-watchlist/` (watchlist.json + cache.db)

---

## 모듈 구성

| 파일 | 역할 |
|------|------|
| `store.py` | 관심종목 CRUD (JSON 파일) |
| `symbol_map.py` | 종목코드 ↔ 종목명 매핑 (pykrx 기반) |
| `market.py` | pykrx 시세/펀더멘털 수집 |
| `dart_fin.py` | OpenDart 재무데이터 수집 |
| `display.py` | Rich 테이블 렌더링 + CSV 내보내기 |
| `cache.py` | SQLite 캐시 (TTL 지원) |
| `cli.py` | Click CLI (`python -m stock watch ...`) |

---

## `store.py` — 관심종목 CRUD

`~/stock-watchlist/watchlist.json`에 관심종목 목록을 저장한다.

### 함수

| 함수 | 설명 |
|------|------|
| `all_items()` | 전체 목록 반환 |
| `get_item(code)` | 단일 종목 조회 (없으면 None) |
| `add_item(code, name, memo)` | 추가 (중복이면 False) |
| `remove_item(code)` | 삭제 (없으면 False) |
| `update_memo(code, memo)` | 메모 수정 |

### 데이터 구조

```json
[
  {
    "code": "005930",
    "name": "삼성전자",
    "added_date": "2025-02-20",
    "memo": "반도체 대장"
  }
]
```

---

## `symbol_map.py` — 종목코드 매핑

pykrx로 KOSPI + KOSDAQ 전 종목 코드/이름/시장을 수집하고 7일간 캐싱한다.

### 함수

| 함수 | 반환 | 설명 |
|------|------|------|
| `get_symbol_map(refresh)` | `dict[str, dict]` | 전체 종목 맵 (`{code: {name, market}}`) |
| `code_to_name(code)` | `str \| None` | 코드 → 종목명 |
| `code_to_market(code)` | `str \| None` | 코드 → 시장 (KOSPI/KOSDAQ) |
| `name_to_results(query)` | `list[tuple]` | 이름 부분일치 검색. `[(code, name, market)]` |
| `resolve(code_or_name)` | `tuple[str, str] \| None` | 6자리 코드 또는 정확한 이름 → `(code, name)`. 복수 매칭이면 None |

- 캐시 키: `symbol_map:v1`, TTL 7일
- `resolve()`은 웹 API(`routers/watchlist.py`)와 CLI 양쪽에서 사용

---

## `market.py` — 시세/펀더멘털

pykrx를 사용하여 종목별 시세, 상세 정보, 밸류에이션 히스토리를 수집한다.

### 함수

| 함수 | 설명 | 캐시 TTL |
|------|------|---------|
| `fetch_price(code, refresh)` | 현재가/등락/시가총액 | 1시간 |
| `fetch_detail(code, refresh)` | 시세 + 52주 고저 + PER/PBR + 업종/시장 | 1시간 |
| `fetch_valuation_history(code, years)` | 월말 PER/PBR 시계열 | 24시간 |
| `fetch_period_returns(code)` | 당일/3개월/6개월/1년 주가 수익률 (%) | 1시간 |

### `fetch_price()` 반환값

```python
{
    "close": 70000,       # 종가 (원)
    "change": 1000,       # 전일대비 (원)
    "change_pct": 1.45,   # 등락률 (%)
    "mktcap": 418000000000000,  # 시가총액 (원)
    "volume": 12345678,   # 거래량
}
```

### `fetch_detail()` 반환값

`fetch_price()` + 추가 필드:

```python
{
    ...fetch_price 필드,
    "market_type": "KOSPI",
    "sector": "전기·전자",
    "high_52": 80000,     # 52주 최고가
    "low_52": 50000,      # 52주 최저가
    "per": 12.5,
    "pbr": 1.2,
    "shares": 5969782550, # 상장주식수
}
```

### `fetch_valuation_history()` 반환값

pykrx `get_market_fundamental_by_date`로 일별 데이터를 가져온 후 `pandas.resample("ME")`로 월말 리샘플링.

```python
[
    {"date": "2016-02", "per": 7.69, "pbr": 1.24},
    {"date": "2016-03", "per": 8.12, "pbr": 1.30},
    ...
]
```

- PER/PBR이 모두 0 이하인 월은 제외
- PER > 0일 때만 포함, PBR > 0일 때만 포함

---

## `dart_fin.py` — OpenDart 재무데이터

DART `fnlttSinglAcntAll` API로 사업보고서(연간) 재무제표를 수집한다.

### 함수

| 함수 | 설명 | 캐시 TTL |
|------|------|---------|
| `fetch_financials(stock_code, refresh)` | 최근 1개 사업보고서 (당기/전기/전전기) | 24시간 |
| `fetch_financials_multi_year(stock_code, years)` | 최대 years개 사업연도 재무 | 24시간 |

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
