# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

한국투자증권(KIS) OpenAPI를 연동한 주식 계좌 관리 FastAPI 서버 + 웹 기반 주식 스크리너/관심종목 대시보드 + AI자문 기능.

- **백엔드**: FastAPI. 종목 스크리닝 + 공시 조회 + 잔고 조회 + 관심종목 + 종목 상세 분석 + AI자문 API
- **프론트엔드**: React 19 + Vite + Tailwind CSS v4 + Recharts SPA
- **CLI**: `python -m screener` (종목 스크리너) + `python -m stock watch` (관심종목 관리)
- **해외주식 지원**: yfinance (미국 시세/재무) + SEC EDGAR (미국 공시)
- **AI자문**: 기본적 분석(재무제표 3종 + 계량지표) + 기술적 분석(15분봉 + MACD/RSI/Stochastic) + OpenAI GPT-4o 종합 투자 의견

> KIS API 키는 잔고 조회에만 필요하다. 스크리너, 공시, 관심종목 기능은 KIS 계정 없이 동작한다.
> AI자문 기능은 `OPENAI_API_KEY`가 필요하다 (데이터 수집은 키 없이 동작, AI 리포트 생성 시만 필요).

---

## 상세 스펙 (작업 전 반드시 참조)

| 문서 | 내용 |
|------|------|
| `docs/API_SPEC.md` | 전체 API 엔드포인트 설계 (screener, earnings, balance, watchlist, detail, advisory) |
| `docs/FRONTEND_SPEC.md` | 프론트엔드 아키텍처, 페이지, 컴포넌트, 라우팅 |
| `docs/KIS_API_REFERENCE.md` | wrapper.py 메서드 + KIS API 참조 |
| `docs/STOCK_PACKAGE.md` | `stock/` 패키지 (관심종목 CLI, 시장 데이터, DART 재무, advisory_store, advisory_fetcher) |
| `docs/SCREENER_PACKAGE.md` | `screener/` 패키지 (스크리너 CLI, KRX, DART 공시, 캐시) |
| `docs/SERVICES.md` | `services/` 서비스 레이어 (watchlist_service, detail_service, advisory_service) |
| `docs/CHANGELOG.md` | 시세 수신 Phase 1~4 개선 이력 + 버그 수정 이력 |

> 각 디렉토리(`routers/`, `services/`, `stock/`, `screener/`, `frontend/`)에 **디렉토리별 CLAUDE.md**가 있다. 해당 디렉토리 작업 시 자동 로드된다.

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
config.py           환경변수 중앙 관리 (os.getenv 단일 진입점)
wrapper.py          KIS API 완전 래퍼 (standalone)
main.py             FastAPI 서버 진입점 (라우터 등록 + SPA 정적 파일 서빙)
routers/            API 라우터 패키지 (10개, quote/market_board는 WebSocket 포함)
services/           서비스 레이어 (watchlist_service, detail_service, quote_service, advisory_service)
services/exceptions.py  서비스 레이어 공용 예외 계층 (ServiceError / NotFoundError / ExternalAPIError / ConfigError / PaymentRequiredError)
screener/           스크리너 패키지 (CLI + API 공용, pykrx + OpenDart)
stock/              관심종목 패키지 (CLI + API 공용, pykrx + OpenDart + yfinance + advisory_store/fetcher)
stock/db_base.py    SQLite 공용 유틸 (connect contextmanager + row_to_dict, 4개 store 공용)
frontend/           React SPA (Vite + Tailwind + Recharts)
```

### `wrapper.py` — KIS API 래퍼 (standalone)

`KoreaInvestment`(REST) + `KoreaInvestmentWS`(WebSocket 실시간 스트리밍). `main.py`/`routers/`와 독립적. 상세는 `docs/KIS_API_REFERENCE.md` 참조.

### 국내/해외/FNO 분기 기준

- `stock/utils.py`의 `is_domestic(code)` — 6자리 숫자이면 국내(KRX), 아니면 해외
- `is_fno(code)` — FNO 마스터 단축코드 형식(6자리 숫자가 아니고 알파벳+숫자 혼합) 여부 판별

### 예외 계층

`ServiceError`(400) → `NotFoundError`(404) / `ExternalAPIError`(502) / `ConfigError`(503) / `PaymentRequiredError`(402). `main.py`에서 일괄 HTTP 변환. 모든 서비스/라우터에서 `HTTPException` 직접 raise 금지.

---

## 환경변수

`.env` 파일에 설정. 항목별 필요 기능:

| 변수 | 필수 여부 | 용도 |
|------|----------|------|
| `KIS_APP_KEY` | 잔고 조회 시 필수 | KIS 실계좌 앱 키 |
| `KIS_APP_SECRET` | 잔고 조회 시 필수 | KIS 실계좌 앱 시크릿 |
| `KIS_ACNT_NO` | 잔고 조회 시 필수 | 계좌번호 앞 8자리 |
| `KIS_ACNT_PRDT_CD_STK` | 잔고 조회 시 필수 | 주식 계좌상품코드(뒤 2자리, 예: 01) |
| `KIS_ACNT_PRDT_CD_FNO` | 선택 | 선물옵션 계좌상품코드(뒤 2자리, 예: 03). 미설정 시 선물옵션 잔고·주문 기능 비활성화 |
| `KIS_BASE_URL` | 선택 | 기본값: `https://openapi.koreainvestment.com:9443` |
| `OPENDART_API_KEY` | 국내 공시/재무 조회 시 필수 | https://opendart.fss.or.kr 에서 발급 |
| `OPENAI_API_KEY` | AI자문 리포트 생성 시 필수 | https://platform.openai.com 에서 발급. 미설정 시 `/analyze` → 503. 크레딧 부족 시 402 반환. |
| `OPENAI_MODEL` | 선택 | AI자문 리포트 생성 모델. 기본값: `gpt-4o`. `max_completion_tokens` 사용 (신규 모델 호환). |
| `FINNHUB_API_KEY` | 선택 | 해외주식 실시간 시세 (Finnhub WS). 미설정 시 yfinance 2초 폴링(15분 지연). |
| `KIS_HTS_ID` | 선택 | KIS HTS ID. 체결통보(H0STCNI0) WS 실시간 수신용. 미설정 시 폴링만 동작. |
| `TEST_KIS_*` | 선택 | 모의계좌용 (`test.py`에서 사용) |

모의투자 BASE_URL: `https://openapivts.koreainvestment.com:29443`

---

## 데이터 소스

| 소스 | 용도 | 모듈 |
|------|------|------|
| **pykrx** | KRX 데이터 (PER/PBR/시가총액/시세) | `screener/krx.py`, `stock/market.py` |
| **OpenDart API** | 국내 정기보고서 + 재무제표. `OPENDART_API_KEY` 필요 | `screener/dart.py`, `stock/dart_fin.py` |
| **yfinance** | 미국 주식 시세/재무 (15분 지연, 최대 4년). 키 불필요 | `stock/yf_client.py` |
| **SEC EDGAR** | 미국 10-K/10-Q 공시. 키 불필요 | `stock/sec_filings.py` |
| **KIS OpenAPI** | 잔고, 현재가, 주문 등. `KIS_APP_KEY`/`KIS_APP_SECRET` 필요 | `wrapper.py`, `routers/balance.py` |
| **OpenAI API** | 종합 투자 의견 (3전략 프레임워크). `OPENAI_API_KEY` 필요 | `services/advisory_service.py` |

---

## 캐시 시스템

| 위치 | 용도 | TTL |
|------|------|-----|
| `screener_cache.db` (프로젝트 루트) | 스크리너 KRX/DART 캐시 | 만료 없음 (날짜키) |
| `~/stock-watchlist/cache.db` | 시세/재무/종목코드/수익률 캐시 | 키별 상이 |
| `~/stock-watchlist/watchlist.db` | 관심종목 목록 | 영구 |
| `~/stock-watchlist/orders.db` | 주문 이력 + 예약주문 | 영구 |
| `~/stock-watchlist/market_board.db` | 시세판 별도 등록 종목 | 영구 |
| `~/stock-watchlist/advisory.db` | AI자문 (자문종목/캐시/리포트) | 영구 |
| `~/stock-watchlist/macro.db` | 매크로 GPT 결과 일일 캐시 (KST 날짜 기반) | 영구 (30일 자동 정리) |

- **NaN 주의**: `cache.py`의 `_sanitize()`가 get/set 양쪽에서 NaN → None 변환 보장
- **시작 시 초기화**: `entrypoint.sh`에서 `cache.db` 삭제 (구버전 캐시 방지). 다른 DB는 영향 없음
- **WAL 모드**: `db_base.py`와 `cache.py`에서 `PRAGMA journal_mode=WAL` + timeout 10초

---

## Docker

```
Stage 1  node:22-slim    → npm ci + npm run build → /frontend/dist
Stage 2  python:3.11-slim → pip install + 앱 소스 + COPY --from Stage 1
```

- `docker-compose.yml`: `watchlist-data` 네임드 볼륨 → `/home/app/stock-watchlist` (DB 보존)
- `entrypoint.sh`: 환경변수 점검 + 경고 출력 (키 없어도 서버 시작). `cache.db` 초기화.
- 프로덕션: `docker-compose up --build` → `http://localhost:8000`
- 개발: `npm run dev` 별도 실행 (Vite 프록시로 백엔드 연결)

---

## 패키지 주의사항

`requirements.txt` 포함: `websockets` (KIS WS 연결용, `services/quote_service.py`)

미포함 (별도 설치): `pycryptodome` — `KoreaInvestmentWS` 체결통보 AES 복호화용
