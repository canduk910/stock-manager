# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

한국투자증권(KIS) OpenAPI를 연동한 주식 계좌 관리 FastAPI 서버 + 웹 기반 주식 스크리너 대시보드.

- **백엔드**: FastAPI. KIS 잔고 조회 API + 종목 스크리닝 API + 공시 조회 API
- **프론트엔드**: React 19 + Vite + Tailwind CSS v4 SPA. 스크리너/공시/잔고 통합 대시보드
- **CLI**: `python -m screener` — KIS 계정 없이 독립 실행 가능한 종목 스크리너

> KIS API 키는 잔고 조회에만 필요하다. 스크리너와 공시 기능은 KIS 계정 없이 동작한다.

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

# ── wrapper.py 직접 테스트 ────────────────────────────────────
python test.py                      # 삼성전자 현재가 조회
```

---

## 아키텍처

### 레이어 구성

```
wrapper.py          KIS API 완전 래퍼 (standalone)
main.py             FastAPI 서버 진입점 (라우터 등록 + 정적 파일 서빙)
routers/            API 라우터 패키지
screener/           스크리너 패키지 (CLI + API 공용)
frontend/           React SPA
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
- `routers/` 3개 라우터 등록
- `frontend/dist/`가 존재하면 `StaticFiles`로 서빙 (라우터 등록 **이후** 마지막에 마운트)
- KIS API를 직접 호출하지 않음. 모든 로직은 `routers/`로 위임.

---

### `routers/` — API 라우터 패키지

| 파일 | 엔드포인트 | 설명 |
|------|-----------|------|
| `screener.py` | `GET /api/screener/stocks` | 멀티팩터 스크리닝 |
| `earnings.py` | `GET /api/earnings/filings` | 정기보고서 목록 |
| `balance.py` | `GET /api/balance` | KIS 실전계좌 잔고 |

**`GET /api/screener/stocks` 파라미터**

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `date` | string | YYYYMMDD 또는 YYYY-MM-DD (기본: 오늘) |
| `sort_by` | string | `"ROE desc, PER asc"` 형태 |
| `top` | int | 상위 N개 |
| `per_min` / `per_max` | float | PER 범위 |
| `pbr_max` | float | PBR 최대값 |
| `roe_min` | float | ROE 최소값 (%) |
| `market` | string | `KOSPI` 또는 `KOSDAQ` |
| `include_negative` | bool | 적자기업(PER < 0) 포함 |
| `earnings_only` | bool | 당일 실적발표 종목만 |

- 모든 핸들러는 `def`(sync) — pykrx/requests가 동기 라이브러리이므로 FastAPI가 threadpool에서 자동 실행
- KIS 키 미설정 시 `/api/balance`는 503 반환 (서버 시작은 정상)
- OPENDART 키 미설정 시 `/api/earnings/filings`는 502 반환

---

### `screener/` — 스크리너 패키지

CLI와 API 라우터 양쪽에서 공용으로 사용한다.

| 파일 | 역할 |
|------|------|
| `service.py` | CLI 독립 비즈니스 로직. `normalize_date`, `parse_sort_spec`, `apply_filters`, `sort_stocks`. `ScreenerValidationError` 예외. |
| `cli.py` | Click CLI. `service.py`를 호출하는 얇은 래퍼. `ScreenerValidationError` → `click.BadParameter` 변환. |
| `krx.py` | pykrx로 전종목 PER/PBR/EPS/BPS/시가총액 수집. ROE = EPS/BPS × 100. |
| `dart.py` | OpenDart API. 정기보고서(A001 사업 / A002 반기 / A003 분기) 제출 목록 조회. |
| `display.py` | Rich 테이블 출력 + CSV 내보내기. 시가총액 억/조 포맷팅. |
| `cache.py` | SQLite 캐시 (`screener_cache.db`). 동일 날짜 재조회 시 API 호출 생략. |

**CLI 주요 옵션**
- `--sort-by "ROE desc, PER asc"` — 다중 정렬, None 값은 항상 마지막
- `--per-range 0 15` — PER 범위
- `--market KOSPI|KOSDAQ` — 시장 필터
- `--include-negative` — 적자기업 포함
- `--earnings-today` — 당일 실적발표 종목만 대상
- `--export csv` — CSV 내보내기
- **날짜 형식**: YYYYMMDD, YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD 모두 지원

---

### `frontend/` — React SPA

React 19 + Vite + Tailwind CSS v4. 네이티브 fetch 사용 (외부 HTTP 라이브러리 없음).

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
    hooks/
      useScreener.js      { data, loading, error, search }
      useEarnings.js      { data, loading, error, load }
      useBalance.js       { data, loading, error, load }
    components/
      layout/Header.jsx   네비게이션 바
      common/             LoadingSpinner, ErrorAlert, EmptyState, DataTable
      screener/           FilterPanel, StockTable
      earnings/           FilingsTable
      balance/            PortfolioSummary, HoldingsTable
    pages/
      DashboardPage.jsx   /  — 잔고 요약 + 오늘 공시 5건 + 시총 상위 10종목
      ScreenerPage.jsx    /screener
      EarningsPage.jsx    /earnings
      BalancePage.jsx     /balance
```

**프론트엔드 규칙**
- 시가총액: 억/조 포맷팅은 프론트에서 처리
- 한국 관례: 수익 = 빨간색, 손실 = 파란색
- KIS 키 없으면 BalancePage에 안내 메시지 표시 (에러 대신)
- ScreenerPage: "조회하기" 버튼 클릭 시 API 호출 (onChange 즉시 호출 안 함)

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
| `OPENDART_API_KEY` 미설정 | 경고 출력. `/api/earnings/filings` → 502 |
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
| `OPENDART_API_KEY` | 공시 조회 시 필수 | https://opendart.fss.or.kr 에서 발급 |
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

- **pykrx**: KRX 데이터(PER/PBR/시가총액) 수집. OTP 기반 인증을 내부적으로 처리.
- **OpenDart API**: 정기보고서 공시 목록. `OPENDART_API_KEY` 필요.
- **KIS 마스터파일**: `wrapper.py`의 `fetch_symbols()`가 다운로드. ROE/시가총액 포함이나 연간 정적 데이터 → 일별 스크리닝에 부적합.
- **KRX 직접 API** (`data.krx.co.kr`): OTP + 세션 쿠키 필요 → `pykrx`가 대신 처리.
