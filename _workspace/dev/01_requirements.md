# 요건서: macro_lite 이식 패키지 (packaging/macro_lite/)

> 작성: 부서장 (2026-09-17). 사용자 결정: regime 포함, 파일 캐시 단순화, 하이일드 누적 데이터 seed 이관.
> 성격: **기존 코드 추출·재포장** (유형 B). 투자 로직은 한 줄도 바꾸지 않는다. 변경은 import 경로·캐시 저장소·인증 의존성뿐.

## 목적

이 프로젝트 매크로 메뉴의 4개 섹션(경기사이클+체제, 장단기금리차, 하이일드 스프레드, 환율/원자재)을
**다른 FastAPI + React 프로젝트에 폴더 복사만으로 붙일 수 있는 자체 완결형 패키지**로 만든다.
패키지는 이 프로젝트의 `stock/`, `services/`, `db/`, `config.py`를 일절 import하지 않는다.

## 산출 구조 (고정)

```
packaging/macro_lite/
├── README.md                      # 통합 절차 + 환경변수 + 도메인 제약 + seed 적재 절차
├── requirements.txt               # yfinance, pandas, requests (버전은 루트 requirements.txt와 동일 핀)
├── backend/
│   ├── macro_lite/
│   │   ├── __init__.py
│   │   ├── cache.py               # 파일 캐시 (raw SQLite) + KST 헬퍼
│   │   ├── events.py              # services/macro_events.py 그대로
│   │   ├── cycle.py               # services/macro_cycle.py 그대로
│   │   ├── regime.py              # services/macro_regime.py 그대로 (determine_regime + get_regime_params + get_margin_requirement)
│   │   ├── oas_history_store.py   # stock/oas_history_store.py + seed 적재 함수
│   │   ├── fetcher.py             # stock/macro_fetcher.py 중 필요한 함수만
│   │   ├── service.py             # macro_service 중 5개 + get_sentiment + _events_for_history
│   │   └── router.py              # /api/macro/{currencies,commodities,yield-curve,credit-spread,macro-cycle}
│   ├── tests/                     # 패키지 단독 pytest (conftest로 캐시 경로를 tmp로 격리)
│   ├── data/
│   │   └── oas_history_seed.json  # 부서장이 운영에서 추출해 채움 (초기엔 빈 {"BAMLH0A0HYM2": [], "BAMLC0A0CM": []} 자리표시)
│   └── pytest.ini
├── frontend/
│   └── macro/
│       ├── MacroLitePage.jsx      # 4개 섹션만 배치 (경기사이클 → 금리차 → 하이일드 → 환율 → 원자재 순)
│       ├── components/            # MacroCycleSection, YieldCurveSection, CreditSpreadSection, CurrencySection, CommoditySection, EventLabelsOverlay, LoadingSpinner, ErrorAlert
│       ├── hooks/useMacro.js, useAsyncState.js
│       └── api/macro.js           # apiFetch import 한 줄이 교체 지점 (README에 명시)
└── scripts/
    └── export_oas_history.py      # 이 프로젝트 cache.db → data/oas_history_seed.json (실행은 이 프로젝트 루트에서)
```

## 요건

### [REQ-PKG-01] 백엔드 순수 모듈 이관
- `events.py`, `cycle.py`, `regime.py`는 원본을 **바이트 단위로 동일하게** 복사 (docstring 포함). 원본은 외부 import가 없다.
- 수용 기준: `diff` 결과가 비어 있다.
- 테스트: 원본 `tests/unit/test_macro_events.py`, `test_macro_regime.py`, `test_macro_regime_cycle.py`, `test_macro_cycle_oas_momentum.py`를 import 경로만 바꿔 `backend/tests/`로 복사, 전부 PASS.

### [REQ-PKG-02] 파일 캐시 (`cache.py`)
- `stock/cache.py`의 `get_cached / set_cached / delete_cached / delete_prefix` + `_sanitize`(NaN→None, get/set 양쪽) 이관.
- `stock/db_base.py`의 `KST / now_kst / now_kst_iso` 헬퍼를 이 파일에 포함 (패키지 밖 KST 정의 금지 원칙은 패키지 내부에서 단일 출처 유지).
- 캐시 DB 경로: 환경변수 `MACRO_LITE_CACHE_DIR` (기본 `~/macro-lite/`), 파일명 `cache.db`. WAL + timeout 10s 유지.
- **하이일드 "당일 1회" DB 캐시 대체**: `macro_store.get_today/save_today/delete_today`를 같은 파일 캐시로 구현. 키 `macro:daily:{category}:{YYYY-MM-DD KST}`, TTL은 다음날 KST 00:00까지(계산해서 넣는다, 고정 24h 아님).
- 수용 기준: 자정 경계 테스트 (KST 23:59 저장 → 00:01 조회 시 miss).

### [REQ-PKG-03] fetcher 추출
- `stock/macro_fetcher.py`에서 다음만 복사: `_safe`, `get_vix_spot`, `fetch_vix`, `calc_buffett_indicator`, `calc_fear_greed`, `_YIELD_SYMBOLS`, `fetch_yield_curve_data`, `_percentile_from_sorted`, `_compute_oas_stats`, `_classify_oas_sentiment`, FRED 블록 전체(`_FRED_*` 상수, `_http_get_fred_csv`, `_fetch_fred_via_api`, `_parse_fred_csv`, `_fetch_fred_oas`, `_fetch_fred_ig_oas`, `fetch_credit_spread`), `_CURRENCY_SYMBOLS`, `fetch_currency_quotes`, `_COMMODITY_SYMBOLS`, `fetch_commodity_quotes`, `_SECTOR_ETFS`, `_calc_return`, `_compute_sma20_trend_days`, `_compute_intensity_zscore`, `fetch_sector_returns`, `fetch_cycle_inputs`.
- 제외: INDICES/뉴스/RSS/투자자/KR 섹터(`fetch_sector_returns_kr`)/factor model.
- `calc_buffett_indicator`/`calc_fear_greed`가 다른 fetcher 함수(예: 지수 조회)에 의존하면 그 의존 함수도 함께 가져온다 (실제 본문을 읽고 판단).
- `from config import FRED_API_KEY` → `os.getenv("FRED_API_KEY", "")`. `from stock.cache` → 패키지 내부 `.cache`. `from stock.oas_history_store` → `.oas_history_store`.
- **캐시 TTL은 원본 값 그대로** (VIX 스팟 0.17h 고정 상향 금지, 환율/원자재 0.17h, 금리차/사이클 입력 1h, credit_spread 24h, FRED stale 7일).
- 테스트: `test_macro_fetcher_oas.py`, `test_macro_fetcher_fred_fallback.py`, `test_macro_vix_spot.py` 이관 PASS.

### [REQ-PKG-04] oas_history_store + seed 이관
- `stock/oas_history_store.py` 그대로 + 다음 추가:
  - `load_seed(path: str | Path = <package>/data/oas_history_seed.json) -> dict`: 파일의 `{series_id: [{date, value}]}`를 각 시리즈에 `merge_and_persist`. 이미 있는 date는 덮어쓰지 않는다(기존 merge 규칙 따름). 반환 `{series_id: merge_stats}`.
  - `router.py`의 lifespan 또는 `service.py` 모듈 import 시점이 아닌, **명시적 호출**로만 적재 (`python -m macro_lite.seed` 엔트리 + README 절차). 앱 기동 자동 적재는 하지 않는다.
- `scripts/export_oas_history.py` (이 프로젝트용): `~/stock-watchlist/cache.db`의 `macro:oas_history_persist:BAMLH0A0HYM2` / `...:BAMLC0A0CM` 키를 읽어 `packaging/macro_lite/backend/data/oas_history_seed.json`으로 기록. `--db` 옵션으로 다른 cache.db 경로 지정 가능(운영 볼륨에서 꺼낸 파일 대상). 키 없으면 빈 리스트 + 경고 출력.
- 수용 기준: seed JSON 2개 시리즈 각 N행 → `load_seed` 후 `slice_history(series, 10)` 길이가 N(10년 이내분)과 같다. 두 번 호출해도 total 불변(멱등).

### [REQ-PKG-05] service + router
- `service.py`: `get_currencies`, `get_commodities`, `get_yield_curve`, `get_credit_spread`, `get_macro_cycle`, `get_sentiment`, `_events_for_history`를 원본 로직 그대로. `get_macro_today/save_macro_today/delete_macro_today`는 `.cache`의 daily 함수로 교체. **credit_spread의 partial_failure(hy_oas/ig_oas) 캐시 폐기 로직 보존.**
- `router.py`: `APIRouter(prefix="/api/macro", tags=["macro"])`, 5개 GET. 인증은 `router.py` 상단의 `AUTH_DEPENDENCY = None` 한 곳으로 모아 README에서 교체 지점으로 안내 (`Depends(...)` 주입 시 모든 엔드포인트에 적용).
- 예외: 패키지는 `HTTPException`을 직접 raise하지 않는다. 원본과 같이 부분 실패는 `errors` 배열로 반환.
- 응답 shape는 원본과 100% 동일 (프론트 컴포넌트 무수정 전제).
- 테스트: FastAPI TestClient로 5개 엔드포인트 200 + 최상위 키 shape 검증 (외부 API는 monkeypatch).

### [REQ-PKG-06] 프론트 이관
- 컴포넌트 5개 + `EventLabelsOverlay.jsx` + `common/LoadingSpinner.jsx` + `common/ErrorAlert.jsx` 원본 그대로 복사. import 상대경로만 조정.
- `useAsyncState.js` 그대로. `useMacro.js`는 5개 훅(useMacroCycle, useYieldCurve, useCreditSpread, useCurrencies, useCommodities)만.
- `api/macro.js`: 상단 `import { apiFetch } from './client'` 한 줄이 교체 지점. 패키지에는 최소 `client.js`(토큰 없이 fetch + 에러 throw, 원본의 refresh 로직 제외)를 동봉해 단독 동작 보장.
- `MacroLitePage.jsx`: 원본 `MacroPage.jsx` 구조 축약 (`space-y-8`, h1 "매크로 분석").
- 검증: 프론트 파일은 이 프로젝트 `frontend/`에서 임시로 import해 `npm run build`가 통과하는지 확인 후 임시 파일 제거 (또는 `npx vite build`로 패키지 폴더만 대상 빌드). 최소한 ESLint/문법 오류 없음을 확인.

### [REQ-PKG-07] README
- 섹션: 개요 / 파일 구조 / 백엔드 통합 5단계(복사, requirements, 라우터 등록, 인증 주입, 환경변수) / seed 적재 절차(`export_oas_history.py` → 복사 → `python -m macro_lite.seed`) / 프론트 통합 4단계(복사, apiFetch 교체, Route+Nav 등록, Vite proxy) / 환경변수 표(`FRED_API_KEY` 선택, `MACRO_LITE_CACHE_DIR`) / **도메인 제약 6개** (VIX TTL 10분 고정 이유, credit_spread partial_failure 폐기, FRED 3년 제한 → 누적 store 영속성 필수(tmpfs 금지), yfinance 호출량과 TTL, 하이스테리시스 previous_regime 인자, NBER/약세장 정적 데이터 출처) / 테스트 실행법.

## 완료 기준 (DoD)

1. `cd packaging/macro_lite/backend && pytest -q` 단독 PASS (이 프로젝트 모듈 import 0건: `grep -rn "from stock\|from services\|from config\|from db" macro_lite/` 결과 없음).
2. 루트 `pytest tests/unit -q` 회귀 없음 (이 프로젝트 코드는 `scripts/export_oas_history.py` 추가 외 변경 없음).
3. 프론트 문법/빌드 검증 통과.
4. README 완성.
5. **commit/push 금지** (`/doc-commit`에서만).

## 도메인 자문 포인트 (macro-sentinel 확인 필요)

- 파일 캐시 daily 키의 "다음날 KST 00:00 만료"가 원본 `macro_gpt_cache` "당일(KST) 1회" 의미와 동치인지.
- `get_macro_cycle`의 regime 계산에 `previous_regime`이 원본에서도 전달되지 않는지(원본 확인: 전달 안 함 → 동일 유지). 패키지에 하이스테리시스 이력 저장소를 추가하지 않는다.
- 제외한 KR 섹터/factor model이 `fetch_cycle_inputs` 결과에 영향을 주지 않는지 (원본 확인: US 섹터만 사용).
