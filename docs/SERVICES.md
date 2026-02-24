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
