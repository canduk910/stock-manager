# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

한국투자증권(KIS) OpenAPI를 연동한 주식 계좌 관리 FastAPI 서버 + 웹 기반 주식 스크리너/관심종목 대시보드.

- **백엔드**: FastAPI. 종목 스크리닝 + 공시 조회 + 잔고 조회 + 관심종목 + 종목 상세 분석 API
- **프론트엔드**: React 19 + Vite + Tailwind CSS v4 + Recharts SPA
- **CLI**: `python -m screener` (종목 스크리너) + `python -m stock watch` (관심종목 관리)
- **해외주식 지원**: yfinance (미국 시세/재무) + SEC EDGAR (미국 공시)

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
stock/              관심종목 패키지 (CLI + API 공용, pykrx + OpenDart + yfinance)
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
- `index.html` 응답에 `Cache-Control: no-cache, no-store, must-revalidate` 헤더 적용 — 도커 재빌드 후 브라우저가 반드시 최신 JS 번들을 로드하도록 강제
- KIS API를 직접 호출하지 않음. 모든 로직은 `routers/` → `services/` → `stock/`/`screener/`로 위임.

---

### `routers/` — API 라우터 패키지

| 파일 | 엔드포인트 | 설명 |
|------|-----------|------|
| `screener.py` | `GET /api/screener/stocks` | 멀티팩터 스크리닝 |
| `earnings.py` | `GET /api/earnings/filings` | 정기보고서 목록 (국내 DART / 미국 SEC EDGAR) |
| `balance.py` | `GET /api/balance` | KIS 실전계좌 잔고 (국내주식 + 해외주식 + 국내선물옵션) |
| `watchlist.py` | `/api/watchlist/*` | 관심종목 CRUD + 대시보드 + 종목정보 (국내/해외) |
| `detail.py` | `/api/detail/*` | 10년 재무 + PER/PBR 히스토리 + 종합 리포트 |

- 모든 핸들러는 `def`(sync) — pykrx/requests가 동기 라이브러리이므로 FastAPI가 threadpool에서 자동 실행
- KIS 키 미설정 시 `/api/balance`는 503 반환 (서버 시작은 정상)
- OPENDART 키 미설정 시 국내 `/api/earnings/filings`, `/api/detail/*`는 502 반환
- 해외 공시(`market=US`)는 OPENDART 키 불필요 (SEC EDGAR 무료 API)

> 각 엔드포인트 상세 파라미터는 `docs/API_SPEC.md` 참조.

#### `earnings.py` — 공시 조회

```
GET /api/earnings/filings?market=KR&start_date=...&end_date=...
GET /api/earnings/filings?market=US&start_date=...&end_date=...
```

- `market=KR` (기본값): 국내 DART 정기보고서 (사업/반기/분기). `OPENDART_API_KEY` 필요.
- `market=US`: 미국 SEC EDGAR 10-K/10-Q. 키 불필요. `stock/sec_filings.py` 사용.
- 수익률: 국내=pykrx, 미국=yfinance

#### `watchlist.py` — 관심종목 CRUD

```
POST /api/watchlist           body: { code, memo, market="KR"|"US" }
DELETE /api/watchlist/{code}  ?market=KR
PATCH /api/watchlist/{code}   ?market=KR
GET /api/watchlist/info/{code}?market=KR
```

- `market` 파라미터로 국내/해외 구분. 동일 코드가 여러 시장에 존재 가능 (복합 PK).
- 해외 추가: `market=US` + 티커 코드 (AAPL, NVDA, TSLA 등). 종목명은 yfinance로 자동 조회.
- 국내 추가: 기존과 동일 (6자리 코드 또는 종목명 허용).

#### `balance.py` — 잔고 조회 상세

`GET /api/balance` 는 3종류의 잔고를 순차 조회해 단일 응답으로 반환한다.

**사용 TR_ID**

| TR_ID | API | 용도 |
|-------|-----|------|
| `TTTC8434R` | `/uapi/domestic-stock/v1/trading/inquire-balance` | 국내주식 잔고 |
| `JTTT3010R` | `/uapi/overseas-stock/v1/trading/dayornight` | 해외주식 주야간원장 구분 |
| `TTTS3012R` / `JTTT3012R` | `/uapi/overseas-stock/v1/trading/inquire-balance` | 해외주식 잔고 (주간/야간) |
| `CTRP6504R` | `/uapi/overseas-stock/v1/trading/inquire-present-balance` | 기준환율 + KRW 합계 |
| `CTFO6118R` | `/uapi/domestic-futureoption/v1/trading/inquire-balance` | 국내선물옵션 잔고 |

**KIS API 구조 주의사항 (잔고 관련)**

- `bass_exrt`(기준환율)는 `TTTS3012R` output1/output2에 **없다**. `CTRP6504R` output2의 `frst_bltn_exrt` 필드에만 존재.
- 해외주식 KRW 환산 절차: ① `CTRP6504R` 먼저 호출 → 통화별 환율 dict 수집 → ② `TTTS3012R` 종목별 `frcr_evlu_pfls_amt × 환율` 계산
- `CTRP6504R` output3 주요 필드: `evlu_amt_smtl`(해외주식 평가금액 KRW 합계), `frcr_evlu_tota`(외화 예수금 KRW 환산 합계)
- `CTFO6118R` 미결제수량 필드: `thdt_nccs_qty` (당일 기준), 포지션 구분: `trad_dvsn_name`
- 해외주식/선물옵션 조회 실패 시 해당 목록만 `[]`로 반환하고 국내주식은 정상 응답

**`/api/balance` 응답 구조**

```json
{
  "total_evaluation": "...",          // 국내 전체 + 해외주식 + 외화예수금 KRW 합산
  "stock_eval": "...",                // 주식 평가금액 합산 (국내 + 해외 KRW환산)
  "stock_eval_domestic": "...",       // 국내주식 평가금액
  "stock_eval_overseas_krw": "...",   // 해외주식 평가금액 (원화환산)
  "deposit": "...",                   // 예수금 합산 (원화 + 외화 KRW환산)
  "deposit_domestic": "...",          // 원화 예수금
  "deposit_overseas_krw": "...",      // 외화 예수금 (원화환산)
  "stock_list": [...],                // 국내주식 보유 종목
  "overseas_list": [...],             // 해외주식 보유 종목 (profit_loss_krw 포함)
  "futures_list": [...]               // 국내선물옵션 포지션
}
```

`overseas_list` 항목: `name`, `code`, `exchange`, `currency`, `quantity`, `avg_price`, `current_price`, `profit_loss`(외화), `profit_loss_krw`(원화환산), `profit_rate`, `eval_amount`

`futures_list` 항목: `name`, `code`, `trade_type`(매수/매도 포지션), `quantity`, `avg_price`, `current_price`, `profit_loss`, `profit_rate`, `eval_amount`

---

### `services/` — 서비스 레이어

`stock/` 패키지의 데이터 소스를 조합해 웹 API용 응답을 조립한다.

| 파일 | 역할 |
|------|------|
| `watchlist_service.py` | 관심종목 대시보드 + 종목 상세. 국내=pykrx+DART, 해외=yfinance 분기. `resolve_symbol(name_or_code, market)` |
| `detail_service.py` | 재무 테이블 + PER/PBR 히스토리 + CAGR 종합 리포트. 해외는 yfinance(최대 4년), 밸류에이션 차트 빈 데이터 반환. |

**국내/해외 분기 기준**: `stock/utils.py`의 `is_domestic(code)` — 6자리 숫자이면 국내(KRX), 아니면 해외.

**서비스 반환 통화**
- 국내: `currency="KRW"`, 금액 단위 억원
- 해외: `currency="USD"`, 금액 단위 M USD (백만달러)

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
| `store.py` | 관심종목 CRUD. `~/stock-watchlist/watchlist.db` (SQLite). 복합 PK `(code, market)`. `market` 컬럼 자동 마이그레이션. |
| `utils.py` | `is_domestic(code)` — 6자리 숫자=국내, 아니면 해외. 모든 모듈에서 국내/해외 분기에 사용. |
| `symbol_map.py` | pykrx 기반 종목코드↔종목명 매핑 (7일 캐시). |
| `market.py` | pykrx 기반 시세/시가총액/52주 고저/PER/PBR + 월별 밸류에이션 히스토리 + `fetch_period_returns()`(당일/3M/6M/1Y 수익률, 1시간 캐시). |
| `dart_fin.py` | OpenDart `fnlttSinglAcntAll` API 기반 재무제표 조회. 3년 단위 배치 호출로 최대 10년치 수집. DART 사업보고서 링크(`dart_url`) 포함. `_ACCOUNT_KEYS`에 적자 기업 변형 계정명(`영업손실`, `당기순손실`, `매출` 등) 포함. |
| `yf_client.py` | yfinance 기반 해외주식 데이터. `validate_ticker`, `fetch_price_yf`, `fetch_detail_yf`, `fetch_period_returns_yf`, `fetch_financials_multi_year_yf`. NaN → None 자동 정제. |
| `sec_filings.py` | SEC EDGAR EFTS API 기반 미국 10-K/10-Q 공시 조회. 키 불필요. 국내 공시와 동일한 필드 구조 반환. |
| `display.py` | Rich 테이블 출력 + CSV 내보내기. |
| `cache.py` | SQLite TTL 캐시 (`~/stock-watchlist/cache.db`). `set_cached`/`get_cached` 모두 NaN/Inf → None 자동 sanitize. |
| `cli.py` | Click CLI. `stock watch add/remove/list/memo/dashboard/info` 명령. |

**`store.py` 마이그레이션**: 기존 `code TEXT PRIMARY KEY` 테이블에 `ALTER TABLE ... ADD COLUMN market TEXT NOT NULL DEFAULT 'KR'` 자동 실행. 기존 데이터는 모두 `KR`로 처리.

**`yf_client.py` 제약사항**
- 시세: 15분 지연 (실시간 아님)
- 재무: 최대 4년 (`t.financials` 기준)
- 종목 검색: 불가. 티커 직접 입력 필요 (AAPL, NVDA, TSLA 등)

**`cache.py` NaN 처리**: Python의 `json.loads`는 `NaN` 리터럴을 허용하므로, 구버전 캐시에 `NaN`이 저장된 경우 `float('nan')`으로 로드될 수 있다. `get_cached`에서 `_sanitize()`로 자동 정제.

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
      earnings.js         fetchFilings(startDate, endDate, market="KR")
      balance.js
      watchlist.js        addToWatchlist(code, memo, market) / removeFromWatchlist(code, market) 등
      detail.js           10년 재무 + 밸류에이션 + 종합 리포트
    hooks/
      useScreener.js      { data, loading, error, search }
      useEarnings.js      { data, loading, error, load(startDate, endDate, market) }
      useBalance.js       { data, loading, error, load }
      useWatchlist.js     useWatchlist (CRUD, market 파라미터) + useDashboard + useStockInfo
      useDetail.js        useDetailReport
    components/
      layout/Header.jsx   네비게이션 바 (5개 메뉴, 로고: "DK STOCK")
      common/             LoadingSpinner, ErrorAlert, EmptyState, DataTable
      screener/           FilterPanel, StockTable
      earnings/           FilingsTable  (국내/미국 컬럼 분기, market prop)
      balance/            PortfolioSummary, HoldingsTable, OverseasHoldingsTable, FuturesTable
      watchlist/          AddStockForm (시장 선택 드롭다운), WatchlistDashboard (통화 표시), StockInfoModal
      detail/             StockHeader, FinancialTable, ValuationChart, ReportSummary
    pages/
      DashboardPage.jsx   /         잔고 요약 + 오늘 공시 + 시총 상위
      ScreenerPage.jsx    /screener
      EarningsPage.jsx    /earnings  국내/미국 탭 선택 + 기간 조회
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
- StockInfoModal: 재무 테이블 연도 클릭 → DART 사업보고서 링크 (국내만)
- DetailPage: Recharts로 PER/PBR 시계열 차트 렌더링 (국내만, 해외는 빈 차트)
- EarningsPage: 국내/미국 탭 선택 → 조회 시 필터 초기화. 종목명/종목코드 클라이언트 사이드 필터.
- FilingsTable: `market` prop으로 국내/미국 분기. 미국은 10-K/10-Q 배지 + SEC 링크. `WatchlistButton`은 market 파라미터 포함.
- WatchlistDashboard: 통화 배지 (US 종목은 `[US]`), 금액 단위 (KRW=억, USD=M). 삭제/메모 편집 시 market 파라미터 포함.
- AddStockForm: 시장 드롭다운 (`국내 KRX` / `미국 NASDAQ·NYSE`). 미국 선택 시 티커 코드 입력 안내.
- BalancePage: 국내주식 / 해외주식 / 국내선물옵션 3개 섹션으로 분리. 해외·선물 보유분이 있을 때만 해당 섹션 표시
- PortfolioSummary: 해외주식·외화 예수금 보유 시 카드 하단에 세부 분류 표시 (국내/해외 원화환산 분리)
- OverseasHoldingsTable: 거래소·통화 컬럼 포함. `평가손익(외화)` + `평가손익(원화)` 두 컬럼 표시. 외화 소수점 포맷
- 매입단가 포맷: 국내주식 `Math.floor()` 소수점 절사(정수 표시), 해외주식 소수점 2자리 고정
- FuturesTable: 포지션 뱃지 (매수=빨강, 매도=파랑), 미결제수량 표시

> 상세 컴포넌트 설명은 `docs/FRONTEND_SPEC.md` 참조.

---

### Docker — 멀티스테이지 빌드

```
Stage 1  node:22-slim    → npm ci + npm run build → /frontend/dist
Stage 2  python:3.11-slim → pip install + 앱 소스 + COPY --from Stage 1
```

- **`Dockerfile`**: `useradd -m` 옵션으로 `/home/app` 홈 디렉토리 생성. `/home/app/stock-watchlist` 디렉토리를 `app:app` 소유로 사전 생성 (볼륨 마운트 시 권한 보장).
- **`.dockerignore`**: `frontend/node_modules/`, `frontend/dist/`, `.env`, `token.dat`, `screener_cache.db` 제외
- **`docker-compose.yml`**: `watchlist-data` 네임드 볼륨을 `/home/app/stock-watchlist`에 마운트 — 컨테이너 재시작 시 관심종목 DB 보존. `frontend/dist/`는 볼륨 없이 이미지에 포함.
- 프로덕션: `docker-compose up --build` → `http://localhost:8000` (프론트 + 백엔드 통합)
- 개발: 볼륨 마운트로 핫리로드 시 프론트엔드는 `npm run dev`로 분리 실행

---

### `entrypoint.sh` — 컨테이너 시작 스크립트

시작 시 환경변수 상태를 점검하고 경고를 출력한다. **키가 없어도 서버는 시작된다.**

| 조건 | 동작 |
|------|------|
| `KIS_APP_KEY` / `KIS_APP_SECRET` 미설정 | 경고 출력 (종료 안 함). `/api/balance` → 503 |
| `KIS_ACNT_NO` / `KIS_ACNT_PRDT_CD` 미설정 | 경고 출력 |
| `OPENDART_API_KEY` 미설정 | 경고 출력. 국내 `/api/earnings/filings`, `/api/detail/*` → 502 (해외 공시는 영향 없음) |
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
| `OPENDART_API_KEY` | 국내 공시/재무 조회 시 필수 | https://opendart.fss.or.kr 에서 발급 |
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
| **OpenDart API** | 국내 정기보고서 공시 + 재무제표(`fnlttSinglAcntAll`). `OPENDART_API_KEY` 필요 | `screener/dart.py`, `stock/dart_fin.py` |
| **yfinance** | 미국 주식 시세/재무 (15분 지연, 최대 4년 재무). 키 불필요 | `stock/yf_client.py` |
| **SEC EDGAR** | 미국 10-K/10-Q 공시. EFTS API 무료 사용. 키 불필요 | `stock/sec_filings.py` |
| **KIS OpenAPI** | 잔고 조회, 현재가, 주문 등. `KIS_APP_KEY`/`KIS_APP_SECRET` 필요 | `wrapper.py`, `routers/balance.py` |
| **KIS 마스터파일** | `fetch_symbols()`로 다운로드. 연간 정적 데이터 → 일별 스크리닝에 부적합 | `wrapper.py` |

---

## 캐시 시스템

| 위치 | 용도 | TTL |
|------|------|-----|
| `screener_cache.db` (프로젝트 루트) | 스크리너 KRX/DART 데이터 캐시 | 만료 없음 (날짜키 기반) |
| `~/stock-watchlist/cache.db` | 관심종목 시세/재무/종목코드/수익률 캐시 (국내+해외) | 키별 상이 |
| `~/stock-watchlist/watchlist.db` | 관심종목 목록 (SQLite CRUD, 국내+해외) | 영구 |

`stock/` 캐시 TTL: `corpCode.xml` 30일, `symbol_map` 7일, 시세/재무 24시간, `market:period_returns:` 1시간, `yf:*` 1~24시간.

**NaN 주의**: Python `json.loads`는 `NaN` 리터럴을 `float('nan')`으로 파싱한다. `cache.py`의 `_sanitize()`가 get/set 양쪽에서 NaN → None 변환을 보장한다.

---

## 해외주식 지원 범위 및 제약

| 기능 | 지원 여부 | 비고 |
|------|----------|------|
| 관심종목 추가/삭제 | ✅ | 티커 코드 직접 입력 (AAPL, NVDA 등) |
| 대시보드 시세 | ✅ | USD, 15분 지연 |
| 대시보드 재무 | ✅ | USD, M 단위, 최대 4년 |
| 종목 상세 재무 | ✅ | yfinance 최대 4년 |
| CAGR 종합 리포트 | ✅ | yfinance 재무 기반 |
| PER/PBR 히스토리 차트 | ❌ | 미지원 (빈 데이터 반환) |
| 공시 조회 (SEC) | ✅ | 10-K/10-Q, 수익률 포함 |
| 스크리너 | ❌ | 미지원 (국내 전용) |
| 종목명 검색 | ❌ | 티커 코드만 가능 |
| 지원 시장 | US | NASDAQ/NYSE/AMEX. 일본·홍콩 등 추후 확장 가능 구조 |
