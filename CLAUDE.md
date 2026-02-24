# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

한국투자증권(KIS) OpenAPI를 연동한 주식 계좌 관리 FastAPI 서버 + 웹 기반 주식 스크리너/관심종목 대시보드.

- **백엔드**: FastAPI. 종목 스크리닝 + 공시 조회 + 잔고 조회 + 관심종목 + 종목 상세 분석 API
- **프론트엔드**: React 19 + Vite + Tailwind CSS v4 + Recharts SPA
- **CLI**: `python -m screener` (종목 스크리너) + `python -m stock watch` (관심종목 관리)

> KIS API 키는 잔고 조회에만 필요하다. 스크리너, 공시, 관심종목 기능은 KIS 계정 없이 동작한다.

---

## 상세 스펙 (작업 전 반드시 참조)

| 문서 | 내용 |
|------|------|
| `docs/API_SPEC.md` | 전체 API 엔드포인트 설계 (screener, earnings, balance, watchlist, detail) |
| `docs/FRONTEND_SPEC.md` | 프론트엔드 아키텍처, 페이지, 컴포넌트, 라우팅 |
| `docs/KIS_API_REFERENCE.md` | wrapper.py 메서드 + KIS API 참조 |
| `docs/STOCK_PACKAGE.md` | `stock/` 패키지 (관심종목 CLI, 시장 데이터, DART 재무) |
| `docs/SCREENER_PACKAGE.md` | `screener/` 패키지 (스크리너 CLI, KRX, DART 공시, 캐시) |
| `docs/SERVICES.md` | `services/` 서비스 레이어 (watchlist_service, detail_service) |

---

## 개발 명령어

```bash
# ── 백엔드 ───────────────────────────────────────────────────
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# Swagger UI: http://localhost:8000/docs

# ── 프론트엔드 (개발) ─────────────────────────────────────────
cd frontend && npm install
cd frontend && npm run dev          # http://localhost:5173 (Vite 프록시로 백엔드 연결)

# ── 프론트엔드 (빌드) ─────────────────────────────────────────
cd frontend && npm run build        # dist/ 생성 → FastAPI가 정적 파일로 서빙

# ── Docker (프로덕션) ─────────────────────────────────────────
docker-compose up --build           # 멀티스테이지 빌드 후 http://localhost:8000

# ── 스크리너 CLI ──────────────────────────────────────────────
python -m screener screen --help
python -m screener screen --sort-by "ROE desc, PER asc" --market KOSPI --top 20
python -m screener screen --per-range 0 15 --roe-min 10 --export csv
python -m screener earnings --date 2025-02-20
python -m screener screen --earnings-today --sort-by PER

# ── 관심종목 CLI ──────────────────────────────────────────────
python -m stock watch add 삼성전자 --memo "반도체 대장"
python -m stock watch list
python -m stock watch dashboard --export csv
python -m stock watch info 005930
python -m stock watch remove 삼성전자

# ── wrapper.py 직접 테스트 ────────────────────────────────────
python test.py                      # 삼성전자 현재가 조회
```

---

## 아키텍처

### 레이어 구성

```
wrapper.py          KIS API 완전 래퍼 (standalone)
main.py             FastAPI 서버 진입점 (라우터 등록 + SPA 정적 파일 서빙)
routers/            API 라우터 패키지 (5개)
services/           서비스 레이어 (watchlist_service, detail_service)
screener/           스크리너 패키지 (CLI + API 공용, pykrx + OpenDart)
stock/              관심종목 패키지 (CLI + API 공용, pykrx + OpenDart)
frontend/           React SPA (Vite + Tailwind + Recharts)
```

---

### `wrapper.py` — KIS API 래퍼

standalone으로 사용 가능. `main.py`/`routers/`와는 독립적이다.

- **`KoreaInvestment`**: REST API 클래스. OAuth2 토큰을 `token.dat`(pickle)에 캐싱, 만료/키 불일치 시 자동 재발급.
  - 국내/해외 현재가, OHLCV(일/주/월), 분봉, 잔고, 주문(시장가/지정가), 주문정정/취소
  - `fetch_symbols()`: KIS 마스터파일에서 KOSPI/KOSDAQ 종목 코드 다운로드 및 파싱
- **`KoreaInvestmentWS`**: WebSocket 실시간 스트리밍. `multiprocessing.Process` + `Queue`로 체결가(`H0STCNT0`), 호가(`H0STASP0`), 체결통보(`H0STCNI0`) 수신. 체결통보는 AES-CBC 복호화 적용.

---

### `main.py` — FastAPI 서버

- CORS 미들웨어: `localhost:5173` 허용 (Vite 개발 서버)
- `routers/` 5개 라우터 등록 (screener, earnings, balance, watchlist, detail)
- SPA 라우팅: `/assets` StaticFiles 마운트 + `/{full_path:path}` 캐치올로 index.html 반환
- `frontend/dist/`가 존재하면 정적 파일 서빙 (라우터 등록 **이후** 마지막에 마운트)
- KIS API를 직접 호출하지 않음. 모든 로직은 `routers/` → `services/` → `stock/`/`screener/`로 위임.

---

### `routers/` — API 라우터 패키지

| 파일 | 엔드포인트 | 설명 |
|------|-----------|------|
| `screener.py` | `GET /api/screener/stocks` | 멀티팩터 스크리닝 |
| `earnings.py` | `GET /api/earnings/filings` | 정기보고서 목록 (기간 조회) |
| `balance.py` | `GET /api/balance` | KIS 실전계좌 잔고 |
| `watchlist.py` | `/api/watchlist/*` | 관심종목 CRUD + 대시보드 + 종목정보 |
| `detail.py` | `/api/detail/*` | 10년 재무 + PER/PBR 히스토리 + 종합 리포트 |

- 모든 핸들러는 `def`(sync) — pykrx/requests가 동기 라이브러리이므로 FastAPI가 threadpool에서 자동 실행
- KIS 키 미설정 시 `/api/balance`는 503 반환 (서버 시작은 정상)
- OPENDART 키 미설정 시 `/api/earnings/filings`, `/api/detail/*`는 502 반환

> 각 엔드포인트 상세 파라미터는 `docs/API_SPEC.md` 참조.

---

### `services/` — 서비스 레이어

`stock/` 패키지의 데이터 소스를 조합해 웹 API용 응답을 조립한다.

| 파일 | 역할 |
|------|------|
| `watchlist_service.py` | 관심종목 대시보드 데이터 + 단일 종목 상세 (기본정보 + 최대 10년 재무) |
| `detail_service.py` | 10년 재무 테이블 + 월별 PER/PBR 히스토리 + CAGR/밸류에이션 종합 리포트 |

> 상세 메서드 설명은 `docs/SERVICES.md` 참조.

---

### `screener/` — 스크리너 패키지

CLI와 API 라우터 양쪽에서 공용으로 사용한다.

| 파일 | 역할 |
|------|------|
| `service.py` | CLI 독립 비즈니스 로직. `normalize_date`, `parse_sort_spec`, `apply_filters`, `sort_stocks`. `ScreenerValidationError` 예외. |
| `cli.py` | Click CLI. `service.py`를 호출하는 얇은 래퍼. `ScreenerValidationError` → `click.BadParameter` 변환. |
| `krx.py` | pykrx로 전종목 PER/PBR/EPS/BPS/시가총액 수집. ROE = EPS/BPS × 100. |
| `dart.py` | OpenDart API. `pblntf_ty=A` 단일 쿼리로 정기보고서 조회. `rcept_no` 기준 중복 제거. 기간 조회 지원. |
| `display.py` | Rich 테이블 출력 + CSV 내보내기. 시가총액 억/조 포맷팅. |
| `cache.py` | SQLite 캐시 (`screener_cache.db`). 동일 날짜 재조회 시 API 호출 생략. |

> 상세 설명은 `docs/SCREENER_PACKAGE.md` 참조.

---

### `stock/` — 관심종목 패키지

CLI와 API 라우터 양쪽에서 공용으로 사용한다. 데이터는 `~/stock-watchlist/` 디렉토리에 저장.

| 파일 | 역할 |
|------|------|
| `store.py` | 관심종목 CRUD. `~/stock-watchlist/watchlist.json` 관리. |
| `symbol_map.py` | pykrx 기반 종목코드↔종목명 매핑 (7일 캐시). |
| `market.py` | pykrx 기반 시세/시가총액/52주 고저/PER/PBR + 월별 밸류에이션 히스토리 + `fetch_period_returns()`(당일/3M/6M/1Y 수익률, 1시간 캐시). |
| `dart_fin.py` | OpenDart `fnlttSinglAcntAll` API 기반 재무제표 조회. 3년 단위 배치 호출로 최대 10년치 수집. DART 사업보고서 링크(`dart_url`) 포함. `_ACCOUNT_KEYS`에 적자 기업 변형 계정명(`영업손실`, `당기순손실`, `매출` 등) 포함. |
| `display.py` | Rich 테이블 출력 + CSV 내보내기. |
| `cache.py` | SQLite TTL 캐시 (`~/stock-watchlist/cache.db`). 기본 24시간, 수익률은 1시간, 기업코드는 30일. |
| `cli.py` | Click CLI. `stock watch add/remove/list/memo/dashboard/info` 명령. |

> 상세 설명은 `docs/STOCK_PACKAGE.md` 참조.

---

### `frontend/` — React SPA

React 19 + Vite + Tailwind CSS v4 + Recharts. 네이티브 fetch 사용 (외부 HTTP 라이브러리 없음).

```
frontend/
  index.html
  package.json
  vite.config.js          /api/* → localhost:8000 프록시
  src/
    main.jsx
    App.jsx               BrowserRouter + Routes
    index.css             @import "tailwindcss"
    api/
      client.js           fetch 래퍼 (에러 처리)
      screener.js
      earnings.js
      balance.js
      watchlist.js        관심종목 CRUD + 대시보드 + 종목정보
      detail.js           10년 재무 + 밸류에이션 + 종합 리포트
    hooks/
      useScreener.js      { data, loading, error, search }
      useEarnings.js      { data, loading, error, load }
      useBalance.js       { data, loading, error, load }
      useWatchlist.js     useWatchlist (CRUD) + useDashboard + useStockInfo
      useDetail.js        useDetailReport
    components/
      layout/Header.jsx   네비게이션 바 (5개 메뉴, 로고: "DK STOCK")
      common/             LoadingSpinner, ErrorAlert, EmptyState, DataTable
      screener/           FilterPanel, StockTable
      earnings/           FilingsTable  (수익률·재무·관심종목 버튼 포함)
      balance/            PortfolioSummary, HoldingsTable
      watchlist/          AddStockForm, WatchlistDashboard, StockInfoModal
      detail/             StockHeader, FinancialTable, ValuationChart, ReportSummary
    pages/
      DashboardPage.jsx   /         잔고 요약 + 오늘 공시 + 시총 상위
      ScreenerPage.jsx    /screener
      EarningsPage.jsx    /earnings  기간 조회 지원 (시작/종료 날짜)
      BalancePage.jsx     /balance
      WatchlistPage.jsx   /watchlist
      DetailPage.jsx      /detail/:symbol  탭 UI (재무분석/밸류에이션/종합 리포트)
```

**프론트엔드 규칙**
- 시가총액: 억/조 포맷팅은 프론트에서 처리
- 한국 관례: 상승 = 빨간색, 하락 = 파란색
- KIS 키 없으면 BalancePage에 안내 메시지 표시 (에러 대신)
- ScreenerPage: "조회하기" 버튼 클릭 시 API 호출 (onChange 즉시 호출 안 함)
- WatchlistDashboard: 종목명 클릭 → `/detail/:symbol` 페이지로 이동
- StockInfoModal: 재무 테이블 연도 클릭 → DART 사업보고서 링크
- DetailPage: Recharts로 PER/PBR 시계열 차트 렌더링
- EarningsPage: 종목명/종목코드 클라이언트 사이드 필터 지원. "조회" 시 필터 초기화.
- FilingsTable: 관심종목 추가 버튼(`WatchlistButton`) + 당일/3M/6M/1Y 수익률 + 매출액/영업이익(YoY) 컬럼 포함

> 상세 컴포넌트 설명은 `docs/FRONTEND_SPEC.md` 참조.

---

### Docker — 멀티스테이지 빌드

```
Stage 1  node:22-slim    → npm ci + npm run build → /frontend/dist
Stage 2  python:3.11-slim → pip install + 앱 소스 + COPY --from Stage 1
```

- **`.dockerignore`**: `frontend/node_modules/`, `frontend/dist/`, `.env`, `token.dat`, `screener_cache.db` 제외
- **`docker-compose.yml`**: 볼륨 마운트 없음 (볼륨이 있으면 컨테이너 내부 `frontend/dist/`가 가려짐)
- 프로덕션: `docker-compose up --build` → `http://localhost:8000` (프론트 + 백엔드 통합)
- 개발: 볼륨 마운트로 핫리로드 시 프론트엔드는 `npm run dev`로 분리 실행

---

### `entrypoint.sh` — 컨테이너 시작 스크립트

시작 시 환경변수 상태를 점검하고 경고를 출력한다. **키가 없어도 서버는 시작된다.**

| 조건 | 동작 |
|------|------|
| `KIS_APP_KEY` / `KIS_APP_SECRET` 미설정 | 경고 출력 (종료 안 함). `/api/balance` → 503 |
| `KIS_ACNT_NO` / `KIS_ACNT_PRDT_CD` 미설정 | 경고 출력 |
| `OPENDART_API_KEY` 미설정 | 경고 출력. `/api/earnings/filings`, `/api/detail/*` → 502 |
| `frontend/dist/` 존재 | "정적 파일 서빙" 안내 |
| `/app` 쓰기 불가 | 경고 출력 (캐시 비활성화) |

---

## 환경변수

`.env` 파일에 설정. 항목별 필요 기능:

| 변수 | 필수 여부 | 용도 |
|------|----------|------|
| `KIS_APP_KEY` | 잔고 조회 시 필수 | KIS 실계좌 앱 키 |
| `KIS_APP_SECRET` | 잔고 조회 시 필수 | KIS 실계좌 앱 시크릿 |
| `KIS_ACNT_NO` | 잔고 조회 시 필수 | 계좌번호 앞 8자리 |
| `KIS_ACNT_PRDT_CD` | 잔고 조회 시 필수 | 계좌번호 뒤 2자리 |
| `KIS_BASE_URL` | 선택 | 기본값: `https://openapi.koreainvestment.com:9443` |
| `OPENDART_API_KEY` | 공시/재무 조회 시 필수 | https://opendart.fss.or.kr 에서 발급 |
| `TEST_KIS_*` | 선택 | 모의계좌용 (`test.py`에서 사용) |

모의투자 BASE_URL: `https://openapivts.koreainvestment.com:29443`

---

## 실전/모의투자 TR_ID 구분

KIS API는 실전/모의투자에 따라 TR_ID 접두사가 다르다.

- 실전: `T***`, `J***` (예: `TTTC8434R`)
- 모의: `V***` (예: `VTTC8434R`)

`wrapper.py`의 `KoreaInvestment`는 생성자 `mock` 파라미터로 제어. `routers/balance.py`는 실전 TR_ID 하드코딩.

---

## 패키지 주의사항

`requirements.txt`에 누락된 패키지 — `wrapper.py`의 일부 기능은 별도 설치 필요:
- WebSocket 기능: `pip install websockets`
- AES 복호화: `pip install pycryptodome`

---

## 데이터 소스

| 소스 | 용도 | 모듈 |
|------|------|------|
| **pykrx** | KRX 데이터 (PER/PBR/시가총액/시세). OTP 기반 인증 내부 처리 | `screener/krx.py`, `stock/market.py` |
| **OpenDart API** | 정기보고서 공시 목록 + 재무제표(`fnlttSinglAcntAll`). `OPENDART_API_KEY` 필요 | `screener/dart.py`, `stock/dart_fin.py` |
| **KIS OpenAPI** | 잔고 조회, 현재가, 주문 등. `KIS_APP_KEY`/`KIS_APP_SECRET` 필요 | `wrapper.py`, `routers/balance.py` |
| **KIS 마스터파일** | `fetch_symbols()`로 다운로드. 연간 정적 데이터 → 일별 스크리닝에 부적합 | `wrapper.py` |

---

## 캐시 시스템

| 위치 | 용도 | TTL |
|------|------|-----|
| `screener_cache.db` (프로젝트 루트) | 스크리너 KRX/DART 데이터 캐시 | 만료 없음 (날짜키 기반) |
| `~/stock-watchlist/cache.db` | 관심종목 시세/재무/종목코드/수익률 캐시 | 키별 상이 |
| `~/stock-watchlist/watchlist.json` | 관심종목 목록 (CRUD) | 영구 |

`stock/` 캐시 TTL: `corpCode.xml` 30일, `symbol_map` 7일, 시세/재무 24시간, `market:period_returns:` 1시간.
