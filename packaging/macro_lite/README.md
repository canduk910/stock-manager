# macro_lite — 매크로 4섹션 이식 패키지

## 개요

stock-manager 매크로 메뉴의 4개 섹션을 **다른 FastAPI + React 프로젝트에 폴더 복사만으로 붙일 수 있는 자체 완결형 패키지**로 추출한 것이다.

| 섹션 | 백엔드 엔드포인트 | 프론트 컴포넌트 |
|------|------------------|-----------------|
| 경기사이클 + 투자 체제 | `GET /api/macro/macro-cycle` | `MacroCycleSection` |
| 장단기 금리차 (10Y-3M) | `GET /api/macro/yield-curve` | `YieldCurveSection` |
| 하이일드 스프레드 (FRED HY/IG OAS) | `GET /api/macro/credit-spread` | `CreditSpreadSection` |
| 환율 / 원자재 | `GET /api/macro/currencies`, `GET /api/macro/commodities` | `CurrencySection`, `CommoditySection` |

- 성격: **기존 코드 추출·재포장**. 투자 로직(체제 매트릭스, 사이클 가중치, OAS 백분위 분류, 캐시 TTL)은 원본과 동일하다. 바뀐 것은 import 경로, 캐시 저장소(DB → 파일 캐시), 인증 의존성뿐이다.
- 원 프로젝트의 `stock/`, `services/`, `db/`, `config.py` 를 일절 import 하지 않는다.
- 데이터 소스: yfinance (VIX/지수/금리/환율/원자재/섹터 ETF), FRED (`fredgraph.csv` 무키 → JSON API `FRED_API_KEY` 폴백).
- 응답 shape 는 원본과 100% 동일 — 프론트 컴포넌트는 무수정으로 동작한다.

## 파일 구조

```
packaging/macro_lite/
├── README.md
├── requirements.txt               # fastapi, requests, numpy<2, pandas, yfinance (+ 주석 처리된 dev 섹션)
├── backend/
│   ├── macro_lite/
│   │   ├── __init__.py            # 서브모듈만 노출 (부작용 import 없음). 라우터는 `from macro_lite.router import router`
│   │   ├── cache.py               # 파일 캐시(raw SQLite, WAL) + KST 헬퍼 + 당일 1회 캐시(get_today/save_today/delete_today)
│   │   ├── events.py              # NBER 침체 + S&P 약세장 정적 이벤트 (원본 services/macro_events.py 그대로)
│   │   ├── cycle.py               # 경기 사이클 4국면 판단 (원본 services/macro_cycle.py 그대로)
│   │   ├── regime.py              # 투자 체제 판단 (원본 services/macro_regime.py 그대로)
│   │   ├── oas_history_store.py   # FRED OAS 10년 FIFO 누적 store + load_seed()
│   │   ├── seed.py                # `python -m macro_lite.seed [--path]` seed 적재 엔트리
│   │   ├── fetcher.py             # yfinance/FRED 수집 (원본 stock/macro_fetcher.py 중 필요 함수만)
│   │   ├── service.py             # 5개 섹션 + get_sentiment 오케스트레이션
│   │   └── router.py              # APIRouter(prefix="/api/macro") 5개 GET, AUTH_DEPENDENCY 교체 지점
│   ├── tests/                     # 패키지 단독 pytest (conftest 가 캐시 경로를 tmp 로 격리)
│   ├── data/
│   │   ├── oas_history_seed.json  # OAS 누적 시계열 초기 적재 데이터 (비어 있으면 FRED 3년치부터 시작)
│   │   └── macro_regime_history_seed.json  # 체제 판정 일별 이력 (참고용 — macro_lite 는 소비하지 않음, 아래 "부가 데이터" 참조)
│   └── pytest.ini
├── frontend/
│   └── macro/
│       ├── MacroLitePage.jsx      # 경기사이클 → 금리차 → 하이일드 → 환율 → 원자재
│       ├── components/            # 5개 섹션 + EventLabelsOverlay + LoadingSpinner + ErrorAlert
│       ├── hooks/                 # useMacro.js (5개 훅), useAsyncState.js
│       └── api/                   # macro.js (apiFetch import 한 줄이 교체 지점), client.js (최소 fetch 래퍼)
└── scripts/
    ├── export_oas_history.py      # stock-manager cache.db → data/oas_history_seed.json (표준 라이브러리만 사용)
    └── export_regime_history.py   # stock-manager macro_regime_history 테이블 → data/macro_regime_history_seed.json (표준 라이브러리만)
```

## 백엔드 통합 5단계

### 1. 복사

`backend/macro_lite/` 디렉토리와 `backend/data/` 디렉토리를 통합 대상 프로젝트의 Python 경로 안에 복사한다.
`oas_history_store.SEED_PATH_DEFAULT` 가 `<macro_lite 상위>/data/oas_history_seed.json` 을 가리키므로 두 디렉토리는 **같은 상위 디렉토리** 아래 두어야 한다 (다른 위치에 두면 `python -m macro_lite.seed --path` 로 지정).

```
your-project/
├── macro_lite/
├── data/oas_history_seed.json
└── main.py
```

### 2. requirements

```bash
pip install -r requirements.txt
```

`fastapi`, `requests`, `numpy<2`, `pandas`, `yfinance` 만 런타임에 필요하다. 이미 설치된 프로젝트라면 `yfinance` 만 추가하면 되는 경우가 많다.

### 3. 라우터 등록

```python
from fastapi import FastAPI
from macro_lite.router import router as macro_router

app = FastAPI()
app.include_router(macro_router)   # prefix "/api/macro" 는 라우터에 내장
```

### 4. 인증 주입

`macro_lite/router.py` 상단의 `AUTH_DEPENDENCY` 한 곳만 바꾸면 5개 엔드포인트 전체에 적용된다.

```python
# macro_lite/router.py
from your_app.auth import get_current_user   # 통합 대상 프로젝트의 FastAPI Depends 함수
AUTH_DEPENDENCY = get_current_user
```

`None` 이면 인증 없이 공개된다. 패키지는 `HTTPException` 을 직접 raise 하지 않으며, 외부 API 부분 실패는 각 응답의 `errors: list[str]` 로 반환한다 (HTTP 200 유지).

### 5. 환경변수

아래 [환경변수](#환경변수) 표 참조. 둘 다 선택이지만 `FRED_API_KEY` 는 등록을 권장한다 (FRED CSV 가 운영 IP 에서 차단되는 경우 JSON API 폴백이 유일한 신선 데이터 경로).

## 부가 데이터: 체제 판정 일별 이력 (참고용)

`backend/data/macro_regime_history_seed.json` 은 원 프로젝트 `macro_regime_history` 테이블 추출본이다
(147행, 2026-04-25 ~ 2026-09-18, 컬럼: date/regime/buffett_ratio/vix/fear_greed_score/kospi/sp500/notes/created_at).
원 프로젝트가 매일 KST 01:00 에 그날의 체제 판정 결과와 입력값(VIX·공포탐욕·버핏지수)을 1행씩 기록한 것이다.

- **macro_lite 는 이 파일을 읽지 않는다.** 체제 판정(`regime.determine_regime`)은 무상태이며 `previous_regime` 을 전달하지 않는다.
  이 데이터를 판정 입력으로 연결하면 원 프로젝트와 결과가 갈리므로 하지 말 것.
- 용도는 통합 대상 프로젝트가 자체 스냅샷 테이블(예: 일별 체제 기록)을 백필하거나, 원 프로젝트 산출값과 로컬 산출값을 비교 검증할 때의 참고 자료다.
- 재추출: `python scripts/export_regime_history.py --container <postgres 컨테이너>` 또는 `--sqlite <app.db 경로>` / `--pg-url <url>`.
- 이 외에 원 프로젝트에 누적되는 매크로 장기 데이터는 없다. 금리차·환율·원자재·VIX·공포탐욕·버핏지수·경기사이클 입력값은
  모두 yfinance/FRED 에서 매번 재취득하는 TTL 캐시(10분~24h)라 이관 대상이 아니다.

## seed 적재 절차 (하이일드 누적 시계열 이관)

FRED 는 2026-04 부터 ICE BofA OAS 시리즈를 **최근 3년치만** 제공한다. 원 프로젝트는 매일 1일치를 자체 store 에 머지해 10년 시계열을 누적해 왔으며, 그 누적분을 seed 로 이관해야 새 프로젝트에서도 백분위 baseline 이 끊기지 않는다.

```bash
# 1) 원 프로젝트(stock-manager) 루트에서 실행 — ~/stock-watchlist/cache.db 의 누적 키를 읽어 seed JSON 생성
python scripts/export_oas_history.py
#    운영 데이터가 docker 컨테이너 안에 있으면 컨테이너에서 직접 꺼내기 (docker cp 사용):
python scripts/export_oas_history.py --container stock-manager
python scripts/export_oas_history.py --container prodclone-web --container-path /home/app/stock-watchlist/cache.db
#    이미 꺼낸 cache.db 파일을 대상으로 하려면:
python scripts/export_oas_history.py --db /path/to/prod/cache.db --out /path/to/oas_history_seed.json
#    (키가 없으면 빈 리스트 + stderr 경고. 표준 라이브러리만 사용 — 어느 환경에서든 실행 가능)

# 2) 생성된 packaging/macro_lite/backend/data/oas_history_seed.json 을 통합 대상의 data/ 로 복사

# 3) 통합 대상 프로젝트에서 명시적으로 적재 (앱 기동 시 자동 적재는 하지 않는다)
cd your-project
MACRO_LITE_CACHE_DIR=/var/lib/macro-lite python -m macro_lite.seed            # 기본 경로 data/oas_history_seed.json
MACRO_LITE_CACHE_DIR=/var/lib/macro-lite python -m macro_lite.seed --path /path/to/oas_history_seed.json
```

- **주의**: 로컬 호스트 `~/stock-watchlist/cache.db` 에는 누적 키가 없을 수 있다(운영 데이터는 docker 볼륨 — `stock-manager` / `prodclone-web` 컨테이너 내부 `/home/app/stock-watchlist/cache.db`). 그 경우 `--container <name>` 으로 추출하거나, `docker cp <name>:/home/app/stock-watchlist/cache.db ./cache.db` 로 꺼낸 파일에 `--db` 를 지정한다.
- **동봉 seed**: `backend/data/oas_history_seed.json` 은 운영 데이터 추출본이다 — BAMLH0A0HYM2(HY) 881행, BAMLC0A0CM(IG) 880행, 2023-05-09 ~ 2026-09-16 (2026-09-18 재추출). 이후 기간은 FRED 매일 머지로 이어진다.
- 적재는 **멱등**이다. 이미 있는 날짜는 덮어쓰지 않고(vintage 우선), 두 번 실행해도 `total` 이 변하지 않는다.
- 적재 시 `MACRO_LITE_CACHE_DIR` 는 **앱이 실제로 쓰는 값과 동일**해야 한다 (다른 디렉토리에 적재하면 앱이 못 본다).
- 출력 예: `BAMLH0A0HYM2: added=881 removed=0 total=881 range=2023-05-09 ~ 2026-09-16`

## 프론트 통합 4단계

### 1. 복사

`frontend/macro/` 를 통합 대상 React 프로젝트의 `src/` 아래로 복사한다 (예: `src/macro/`). 컴포넌트 간 상대경로 import 는 폴더 내부로 닫혀 있으므로 위치는 자유다.

의존성: React 19, Tailwind CSS v4, Recharts (원 프로젝트와 동일 스택 전제).

### 2. apiFetch 교체

**교체 지점은 `frontend/macro/api/macro.js` 상단의 한 줄**이다.

```js
// frontend/macro/api/macro.js
import { apiFetch } from './client'          // ← 이 한 줄을 호스트 프로젝트의 apiFetch 로 교체
// 예: import { apiFetch } from '../../api/client'
```

동봉된 `client.js` 는 토큰/refresh 없이 `fetch` + 에러 throw 만 하는 최소 래퍼로, 인증 없는 환경에서 패키지 단독 동작을 보장한다. 호스트 프로젝트에 JWT/refresh 래퍼가 있으면 그 import 로 바꾸면 된다 (`apiFetch(path) → Promise<json>`, 실패 시 throw 계약만 맞으면 됨).

### 3. Route + Nav 등록

```jsx
import MacroLitePage from './macro/MacroLitePage'
// react-router 예
<Route path="/macro" element={<MacroLitePage />} />
```

네비게이션 메뉴에 `/macro` 링크를 추가한다.

### 4. Vite proxy

개발 서버에서 `/api` 를 백엔드로 프록시한다.

```js
// vite.config.js
server: {
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true },
  },
},
```

## 환경변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `FRED_API_KEY` | 선택(권장) | `""` | FRED JSON API 폴백 키. `fredgraph.csv` 가 실패(HTML 차단/timeout)할 때만 사용. 없으면 7일 stale 캐시 → 그것도 없으면 `partial_failure: ["hy_oas"]`. 발급: https://fred.stlouisfed.org/docs/api/api_key.html |
| `MACRO_LITE_CACHE_DIR` | 선택 | `~/macro-lite/` | 파일 캐시(`cache.db`) 디렉토리. **호출 시점에 읽는다**. OAS 누적 store 도 여기에 저장되므로 영속 볼륨이어야 한다 (아래 도메인 제약 3). |
| `MACRO_LITE_FRED_TIMEOUT` | 선택 | `25` | FRED HTTP 요청 timeout(초). CSV 1회 재시도 × 시리즈 2종이라 CSV가 차단되면 최악 `timeout×4`초 대기 후 JSON 폴백. 정상 CSV는 1초 미만이므로 `8` 정도로 낮춰도 됨(I/O 정책, 투자 로직 무관). |

## 도메인 제약

리팩토링/통합 시 바꾸면 안 되는 항목. 각 근거는 원본(stock-manager) 파일:라인과 macro-sentinel 자문 결론이다.

### 1. VIX 스팟 캐시 TTL 10분(0.17h) 고정 — 상향 금지

`fetcher.get_vix_spot()` 의 `set_cached(key, value, ttl_hours=0.17)` (원본 `stock/macro_fetcher.py:141-170`). 체제 판단에는 **VIX > 35 → 공포탐욕 level 을 `extreme_fear` 로 강제 오버라이드** 규칙이 있고(`services/macro_regime.py:108-110`), 이 오버라이드는 하이스테리시스·신용 보정보다 우선한다(`:153-155`, `:207`). 즉 **TTL 0.17h 가 곧 VIX>35 감지 지연 시간**이다 — 상향하면 급락 국면에서 체제 전환이 그만큼 늦어진다. 실패 시 `None` 반환 + 캐시 미저장을 유지할 것: 폴백값(공포탐욕의 20)을 실측치로 저장하면 오버라이드가 오염되므로 폴백은 소비처 로컬(`calc_fear_greed`)에서만 적용한다.

### 2. credit_spread 의 partial_failure 폐기 로직 — 읽기측·쓰기측 2단 모두 보존

`service.get_credit_spread()` 는 원본과 동일하게 두 곳에서 방어한다.

- **읽기측** (원본 `services/macro_service.py:278-291`): 당일 캐시의 `partial_failure` 에 `hy_oas`/`ig_oas` 가 있으면 캐시를 폐기하고 재조회.
- **쓰기측** (`:313-321`): 새 응답도 핵심 데이터가 빠졌으면 저장하지 않는다.

둘 중 하나만 있으면 FRED 일시 장애 응답이 자정까지 캐시에 박혀 하루 종일 잘못된 스프레드가 표시된다(원본 2026-05-05 fix). 패키지에는 원본의 자정 스케줄러가 없으므로 **읽기 시 폐기가 유일한 자가 복구 경로**다. `hy_oas_stale_used`/`ig_oas_stale_used` 는 폐기 대상이 아니다(7일 stale fallback 은 정상 경로). HY OAS 백분위는 체제 Phase 1 보정(p≥90/≤10)과 Phase 2 오버라이드(OAS>10% 또는 p>95)의 **유일한 신용 입력**이라(`services/macro_regime.py:201-207`) 이 값이 잘못 캐시되면 체제 자체가 오판된다.

### 3. FRED 3년 제한 → 누적 store 영속성 필수 (tmpfs 금지)

원본 `stock/oas_history_store.py:1-20`: 2026-04 부터 ICE BofA 라이센스 정책으로 FRED 가 OAS 시리즈를 **최근 3년치만** 공개한다. 백분위 baseline(하워드 막스 5단계)은 누적 store `macro:oas_history_persist:{series_id}` (TTL 50년, 10년 FIFO) 에 매일 1일치씩 쌓이는 시계열에 의존한다. **파일이 유실되면 3년 초과분은 영구 재취득 불가**하다 — 이것이 `MACRO_LITE_CACHE_DIR` 를 tmpfs/컨테이너 임시 레이어에 두면 안 되는 이유이자, 위 seed 이관 절차가 필요한 이유다. 영속 볼륨 + 정기 백업을 권장한다.

### 4. yfinance 호출량과 TTL — 원본 값이 균형점

| 데이터 | 캐시 키 | TTL |
|--------|---------|-----|
| VIX 스팟 / VIX 표시 dict | `macro:vix_spot` / `macro:vix` | 0.17h |
| 환율 4쌍 / 원자재 6종 | `macro:currencies` / `macro:commodities` | 0.17h |
| 공포탐욕 / 수익률곡선 / 섹터 ETF / 사이클 입력 | `macro:fear_greed` / `macro:yield_curve` / `macro:sector_returns_v4` / `macro:cycle_inputs` | 1h |
| 버핏지수 | `macro:buffett` | 24h |
| credit_spread 통합 응답 | `macro:credit_spread_v8` | 24h (+ 당일 1회 캐시 `macro:daily:credit_spread:{날짜}`) |
| FRED stale 폴백 | `macro:credit_spread_fred_{hy,ig}_stale` | 7일 |

콜드 캐시에서 1회 전체 갱신은 yfinance 약 27건(환율 4 + 원자재 6 + 금리 4 + 섹터 ETF 11 + VIX 2 + 달러 1)이다. 0.17h 항목을 프론트가 계속 폴링하면 하루 약 1,400회 수준으로, yfinance 비공식 API 의 rate-limit(빈 응답/차단) 경계 근처다. TTL 을 줄이면 차단, 늘리면 체제 판단 입력이 stale — 원본 값을 유지한다. 수익률곡선은 4개 심볼 `period="max", interval="1wk"`, 섹터는 11개 ETF `period="5y"` 를 병렬 조회하므로 1h 미만으로 내리지 말 것.

### 5. 하이스테리시스 `previous_regime` 인자 — 무상태 판정 유지, 이력 저장소 추가 금지

`determine_regime()` 은 `previous_regime` 인자로 경계값 하이스테리시스(F&G ±5점 / 버핏지수 ±0.05, `services/macro_regime.py:195, 212, 277-281`)를 지원하지만, **원본 프로젝트를 포함해 이 패키지는 이를 전달하지 않는다** — 원본 프로덕션 호출처 0건(`services/macro_service.py:445`, `services/pipeline_service.py:428/433` 모두 미전달, `macro_regime_history` 테이블은 write-only). 매 호출이 독립적인 무상태 판정이며 경계값 근처에서는 체제가 날마다 토글될 수 있다. 하이스테리시스를 켜려면 직전 체제 저장소를 호스트 앱이 직접 제공해야 하고, 그 순간 판정 결과가 원본과 달라진다(이전 level 역추적이 근사값이라는 구현 한계 포함 — `:277-278`). 패키지 내부에 이력 저장소를 추가하지 않는다.

### 6. NBER 침체 / S&P 약세장 정적 데이터 출처 — 색/레이어 순서 변경 금지

`events.py` (원본 `services/macro_events.py:1-48`) 의 `NBER_RECESSIONS`(NBER Business Cycle Dating Committee 공식 peak/trough, 9건) 와 `SP500_BEAR_MARKETS`(Macrotrends/Yardeni 통계, 고점 대비 -20% 이상, 9건, 1962~) 는 정적 상수다. 차트 음영(`events` 키)에만 쓰이며 체제/사이클 판단 입력이 아니다.

- 갱신: NBER 는 연 1회 확인, 약세장은 새 -20% 확정 시 수기 추가. 기존 행은 수정하지 않는다.
- 표시 규약(MacroSentinel 합의, docstring): **침체 = 회색 alpha 0.15 상위 레이어, 약세장 = 붉은색 alpha 0.10**. 두 시계열은 의미가 다르다(실물경제 침체 vs 자산가격 패닉). 프론트 `EventLabelsOverlay` 가 이 색/레이어 순서에 의존하므로 변경 금지.
- 응답 shape 계약 `events.recessions[]` / `events.bear_markets[]` 유지.

### 7. 경기사이클 입력의 `credit_direction` — "버그"로 고치지 말 것

`fetcher.fetch_cycle_inputs()` 2번 블록(원본 `stock/macro_fetcher.py:1495-1509`)은 `fetch_credit_spread()` 응답에서 `oas_momentum_6m` 을 읽지만 **그 응답에는 이 키가 없어 항상 None → `credit_direction` 은 사실상 항상 `"stable"`** 이다. 신용 정보는 이 경로가 아니라 `service.get_macro_cycle()` 이 credit_spread 응답의 `oas_history_5y` 로 6개월 모멘텀을 계산해 `inputs["oas_momentum_6m"]` 로 주입하는 경로(원본 `services/macro_service.py:418-437`)로 사이클 판정(`cycle._score_credit`)에 반영된다. 이는 원본과 동일한 기존 특성이며, 2번 블록을 "고쳐" 두 경로가 이중 반영되면 사이클 가중치가 원본과 달라진다. 또한 KR 섹터·거시 팩터 모델은 `fetch_cycle_inputs`/`determine_cycle_phase` 에 영향이 0 이라 패키지에서 제외해도 결과가 같다(사이클 입력은 US 섹터 ETF 11개만 사용, factor model 은 write-only).

## 하이일드 첫 호출 지연과 prewarm (운영 주의)

`credit-spread` / `macro-cycle` 는 24h 캐시 miss 시 FRED 를 실호출한다. FRED `fredgraph.csv` 는 IP 에 따라 **간헐적으로 응답을 끊으며**, 그때 `_FRED_TIMEOUT × 2회 × 2시리즈`(기본 100초) 를 채운 뒤에야 JSON API(`FRED_API_KEY`) 로 폴백한다. 하루 한 번이지만 그 요청은 nginx `proxy_read_timeout`(보통 60s)에 걸려 504 가 될 수 있다.

- **시도 순서(CSV → JSON)는 바꾸지 말 것.** 백분위·z-score 의 baseline 은 누적 store 가 아니라 **그 호출에서 받은 신선 rows** 로 계산된다(`_compute_oas_stats(rows)`). CSV 는 현재 vintage(~3년), JSON 은 `realtime_start=1776`(전 vintage) 로 호출하므로 두 소스가 같은 date 집합을 돌려준다는 보장이 없고, 다르면 5단계 sentiment 가 갈린다. 순서 변경은 두 소스의 (첫 날짜, 끝 날짜, 행 수, 중복 date 없음) 동일성을 실측으로 확인한 뒤에만.
- 권장 대응: (1) `MACRO_LITE_FRED_TIMEOUT=8` 로 낮춰 최악 32초, (2) 원 프로젝트처럼 **매일 KST 00:05 경 prewarm**(컨테이너 cron/스케줄러가 `GET /api/macro/credit-spread` 와 `/macro-cycle` 을 미리 호출) 하여 사용자가 miss 경로를 밟지 않게 한다. FRED 는 전 영업일분을 KST 당일 밤(22~23시) 에 게시하므로 00:05 prewarm 이면 최신값이 잡힌다.
- 동봉 seed 는 차트 시계열(10y/5y 슬라이스)을 채우는 것이지 백분위 baseline 을 채우는 것이 아니다.

## 장애 복구

### FRED_API_KEY 등록/교체 후 즉시 반영

`credit_spread` 는 두 겹으로 캐시된다 — 당일 1회 캐시(`macro:daily:credit_spread:{날짜}`)와 fetcher 24h 캐시(`macro:credit_spread_v8`, 원본 `stock/macro_fetcher.py:1067`). partial_failure 폐기는 당일 캐시만 비우므로, 키 등록 직후 신선 데이터를 받으려면 **둘 다** 비운다.

```bash
cd your-project
MACRO_LITE_CACHE_DIR=/var/lib/macro-lite python - <<'PY'
from macro_lite import cache
cache.delete_prefix("macro:credit_spread")   # credit_spread_v8 + fred stale 캐시
cache.delete_prefix("macro:daily:credit_spread:")
PY
```

`macro:oas_history_persist:*` 는 **절대 지우지 말 것**(제약 3). `delete_prefix("macro:credit_spread")` 는 접두사가 달라 persist 키를 건드리지 않는다.

### 누적 store 유실 시

seed JSON 백업이 있으면 `python -m macro_lite.seed --path <backup>` 로 재적재한다(멱등). 백업이 없으면 FRED 가 제공하는 최근 3년치부터 다시 누적되며 baseline 이 3년으로 퇴행한다 — 복구 불가 항목이므로 영속 볼륨 백업을 운영 절차에 포함할 것.

## 운영 주의

- **`now_kst()` 는 tz-aware 다.** 당일 1회 캐시는 "키에 KST 날짜 포함"이 1차 경계, expires(다음날 KST 00:00)가 2차 가드로, 원본 `macro_gpt_cache` 의 "당일(KST) 1회" 와 동치다. 이 동치는 `cache.now_kst()` 가 `datetime.now(KST)` 인 것을 전제한다 — UTC 컨테이너에서 naive `datetime.now()` 로 바꾸면 경계가 KST 09:00 으로 밀린다.
- **자정 하우스키핑 스케줄러는 패키지에 없다.** 원본의 KST 00:05 `delete_before_today` 는 DB 정리 전용이라 이식하지 않았다. 만료 row 는 카테고리당 1행/일이라 누적량이 미미하며, 필요 시 `cache.delete_prefix("macro:daily:")` 를 수동/크론으로 호출하면 된다.
- **캐시 저장소는 로컬 파일이다.** 원본은 RDS(공유)였지만 패키지는 `MACRO_LITE_CACHE_DIR` 의 SQLite 다. 영속 볼륨이 아니면 재시작마다 FRED/yfinance 를 다시 호출한다(판단 결과는 동일, 호출량만 증가 — 단 제약 3 의 누적 store 는 유실되므로 영속 볼륨 필수). 멀티 인스턴스라면 인스턴스별로 캐시가 분리된다.
- **인증은 `router.AUTH_DEPENDENCY` 한 곳.** 서비스/fetcher 는 사용자 컨텍스트를 받지 않는다(원본도 user 무관 공유 캐시).

## 테스트 실행법

```bash
# 패키지 단독 (외부 API 는 전부 monkeypatch — 네트워크 불필요)
cd packaging/macro_lite/backend
pip install pytest pytest-timeout httpx
pytest -q
```

- `tests/conftest.py` 가 테스트마다 `MACRO_LITE_CACHE_DIR` 를 `tmp_path` 로 설정해 실제 `~/macro-lite/cache.db` 를 건드리지 않는다.
- `pytest.ini` 의 `pythonpath = .` 로 `import macro_lite` 가 `backend/` 기준으로 해석된다.
- 시간 조작 테스트는 `monkeypatch.setattr("macro_lite.cache.now_kst", lambda: fixed_dt)` 로 한다 (cache.py 의 모든 현재시각이 이 함수를 경유).

원 프로젝트 모듈 의존이 없음을 확인하려면:

```bash
grep -rn "from stock\|from services\|from config\|from db\|import stock\|import services\|import config\|import db" backend/macro_lite/   # 0건이어야 함
```
