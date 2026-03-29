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
- `routers/` 10개 라우터 등록 (screener, earnings, balance, watchlist, detail, order, quote, advisory, search, market_board)
- lifespan: ① `quote_manager.start()` (KIS WebSocket 관리자) ② 예약주문 스케줄러 시작 ③ `symbol_map` background pre-warm thread 시작 (Docker 재기동 후 cold-start 지연 방지) — 종료 시 역순 정리
- `services/quote_service.py`: `KISQuoteManager` + `OverseasQuoteManager` + `FinnhubWSClient`. WS 끊김 시 REST fallback 자동 전환
- SPA 라우팅: `/assets` StaticFiles 마운트 + `/{full_path:path}` 캐치올로 index.html 반환
- `frontend/dist/`가 존재하면 정적 파일 서빙 (라우터 등록 **이후** 마지막에 마운트)
- `index.html` 응답에 `Cache-Control: no-cache, no-store, must-revalidate` 헤더 적용 — 도커 재빌드 후 브라우저가 반드시 최신 JS 번들을 로드하도록 강제
- KIS API를 직접 호출하지 않음. 모든 로직은 `routers/` → `services/` → `stock/`/`screener/`로 위임.

---

### `routers/` — API 라우터 패키지

| 파일 | 엔드포인트 | 설명 |
|------|-----------|------|
| `screener.py` | `GET /api/screener/stocks` | 멀티팩터 스크리닝. 필터·정렬·top 슬라이싱 후 yfinance enrichment(ThreadPoolExecutor 병렬): `prev_close`, `current_price`, `change_pct`, `return_3m`, `return_6m`, `return_1y`, `dividend_yield` 추가. |
| `earnings.py` | `GET /api/earnings/filings` | 정기보고서 목록 (국내 DART / 미국 SEC EDGAR) |
| `balance.py` | `GET /api/balance` | KIS 실전계좌 잔고 (국내주식 + 해외주식 + 국내선물옵션) |
| `watchlist.py` | `/api/watchlist/*` | 관심종목 CRUD + 대시보드 + 종목정보 (국내/해외) |
| `detail.py` | `/api/detail/*` | 10년 재무 + PER/PBR 히스토리 + 종합 리포트 |
| `_kis_auth.py` | (내부 모듈) | KIS 인증 공통 모듈 (토큰 관리, hashkey 발급). `balance.py`와 `order.py` 공용. 예외는 `ConfigError`/`ExternalAPIError` 사용 (ServiceError 계층 통일) |
| `order.py` | `/api/order/*` | 주문 발송 / 정정 / 취소 / 미체결 / 체결 내역 / 이력 / 예약주문. **`order_service`만 import** (order_store 직접 접근 금지) |
| `quote.py` | `WS /ws/quote/{symbol}` | 실시간 호가 WebSocket. `?market=KR`(기본)=KIS WS 브릿지, `?market=FNO`=KIS FNO WS(H0IFASP0/H0IFCNT0 등), `?market=US`=yfinance 2초 polling |
| `advisory.py` | `/api/advisory/*` | AI자문 종목 관리 + 데이터 수집/조회 + GPT-4o AI 리포트 생성 |
| `search.py` | `GET /api/search` | 종목 검색. KR=이름/코드 자동완성(최대 10건), US=티커 유효성 검증, FNO=선물옵션 종목명/단축코드 자동완성(최대 10건, `fno_master` 연동) |
| `market_board.py` | `GET /api/market-board/new-highs-lows`, `POST /api/market-board/sparklines`, `GET/POST/DELETE /api/market-board/custom-stocks`, `WS /ws/market-board` | 당일 신고가/신저가 + sparkline 배치 + 시세판 별도 종목 CRUD + 다중심볼 실시간 시세 WS (200ms 배칭) |

- 모든 핸들러는 `def`(sync) — pykrx/requests가 동기 라이브러리이므로 FastAPI가 threadpool에서 자동 실행
- KIS 키 미설정 시 `/api/balance`는 503 반환 (서버 시작은 정상)
- OPENDART 키 미설정 시 국내 `/api/earnings/filings`, `/api/detail/*`는 502 반환
- 해외 공시(`market=US`)는 OPENDART 키 불필요 (SEC EDGAR 무료 API)
- `OPENAI_API_KEY` 미설정 시 `/api/advisory/{code}/analyze`는 503 반환 (데이터 수집·조회는 정상)

> 각 엔드포인트 상세 파라미터는 `docs/API_SPEC.md` 참조.

#### `order.py` — 주문 관리

```
POST /api/order/place          국내/해외/선물옵션 주문 발송 (매수/매도, 지정가/시장가)
GET  /api/order/buyable        매수가능 금액/수량 조회 (FNO: side 파라미터 필요)
GET  /api/order/open           미체결 주문 목록 (KIS 실시간, market=KR|US|FNO)
POST /api/order/{order_no}/modify   주문 정정 (FNO: nmpr_type_cd 등 선택)
POST /api/order/{order_no}/cancel   주문 취소
GET  /api/order/executions     당일 체결 내역 (KIS, market=KR|US|FNO)
GET  /api/order/history        로컬 DB 주문 이력 (날짜/종목/상태 필터)
POST /api/order/sync           KIS 체결 내역과 로컬 DB 대사(Reconciliation)
POST /api/order/reserve        예약주문 등록
GET  /api/order/reserves       예약주문 목록
DELETE /api/order/reserve/{id} 예약주문 삭제
GET  /api/order/fno-price      선물옵션 현재가 조회 (?symbol=101W09&mrkt_div=F)
```

- **계층 분리**: `routers/order.py`는 오직 `services.order_service`만 import. `order_store` 직접 접근 금지. 이력 조회·예약주문·FNO 시세 모두 서비스 계층 경유.
- KIS API 키 미설정 시 503 반환
- 주문 발송 시 로컬 `orders.db`에 자동 기록 (status: PLACED). 응답에 `balance_stale: true` 포함 → 프론트에서 잔고 재조회 트리거.
- **취소 즉시 동기화**: KIS 취소 성공 → 로컬 DB 즉시 CANCELLED 갱신. 응답에 `local_synced: true`, `order_status: "CANCELLED"`.
- **정정 즉시 동기화**: KIS 정정 성공 → 로컬 DB 가격/수량 즉시 반영. 응답에 `local_synced: true`.
- **대사(Reconciliation)**: `sync_orders()` → 체결 내역 + 미체결 내역 양쪽 조회. 양쪽 다 없는 주문 → CANCELLED 자동 감지. `get_order_history()` 호출 시 반환 전 자동 대사(best-effort).
- **예약주문 검증**: `create_reservation()` — condition_type/value/quantity/price 도메인 규칙 검증.
- `excg_id_dvsn_cd` 필드: `'KRX'`=API 주문(취소 가능), `'SOR'`=HTS/MTS 주문(API 취소 불가)
- 주문번호 포맷: `TTTC8036R`은 10자리 제로패딩(`0039822900`), 취소/정정 API는 8자리 필요 → `_strip_leading_zeros()`로 자동 변환

#### `advisory.py` — AI자문 관리

```
GET    /api/advisory                                  자문종목 목록 (캐시 업데이트 시각 포함)
POST   /api/advisory                                  종목 추가 {code, market, memo}
DELETE /api/advisory/{code}?market=KR                 종목 삭제
POST   /api/advisory/{code}/refresh?market&name=      전체 데이터 수집 → advisory_cache 저장 (30초+)
GET    /api/advisory/{code}/data?market               캐시된 분석 데이터 조회 (fundamental + technical)
GET    /api/advisory/{code}/ohlcv?market&interval&period  타임프레임별 OHLCV + 기술지표 조회
POST   /api/advisory/{code}/analyze?market            OpenAI GPT-4o 리포트 생성 (10-30초)
GET    /api/advisory/{code}/report?market             최신 AI 리포트 조회
GET    /api/advisory/{code}/reports?market&limit=20   AI 리포트 히스토리 목록 (본문 제외, 최신순)
GET    /api/advisory/{code}/reports/{id}?market       특정 ID의 AI 리포트 상세 조회
```

- `/refresh`: `name` 쿼리 파라미터 추가. advisory_stocks 미등록 종목도 허용 (name 없으면 code 사용)
- `/ohlcv`: interval(`15m`/`60m`/`1d`/`1wk`), period(`60d`/`6mo`/`1y` 등) 파라미터. 기술지표 자동 계산 포함. TTL 캐시 없음(매 호출 계산).
- `/refresh`, `/analyze`는 처리 시간이 길어 프론트에서 loading 처리 필수
- `OPENAI_API_KEY` 미설정 시 `/analyze` → 503 반환
- KIS 키 미설정 시 국내 15분봉 yfinance fallback 사용 (재무 데이터는 정상)
- OpenAI 크레딧 부족(429) 시 `/analyze` → 402 반환 (한국어 안내 메시지)
- `advisory_store.py` → `advisory_fetcher.py` → `advisory_service.py` 레이어 분리

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
| `TTTC0802U` | `/uapi/domestic-stock/v1/trading/order-cash` | 국내주식 매수 주문 |
| `TTTC0801U` | `/uapi/domestic-stock/v1/trading/order-cash` | 국내주식 매도 주문 |
| `TTTC0803U` | `/uapi/domestic-stock/v1/trading/order-rvsecncl` | 국내주식 정정/취소 |
| `TTTC8036R` | `/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl` | 국내주식 미체결 조회 |
| `TTTC8001R` | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` | 국내주식 당일 체결 내역 |
| `TTTC8908R` | `/uapi/domestic-stock/v1/trading/inquire-psbl-order` | 국내주식 매수가능 조회 |
| `JTTT1002U` | `/uapi/overseas-stock/v1/trading/order` | 해외주식 매수 주문 |
| `JTTT1006U` | `/uapi/overseas-stock/v1/trading/order` | 해외주식 매도 주문 |
| `TTTS3018R` | `/uapi/overseas-stock/v1/trading/inquire-nccs` | 해외주식 미체결 조회 |
| `JTTT3001R` | `/uapi/overseas-stock/v1/trading/inquire-ccnl` | 해외주식 당일 체결 내역 |
| `TTTS3007R` | `/uapi/overseas-stock/v1/trading/inquire-psamount` | 해외주식 매수가능 조회 |
| `TTTO1101U` | `/uapi/domestic-futureoption/v1/trading/order` | 선물옵션 주문 (주간, 매수·매도 동일) |
| `STTN1101U` | `/uapi/domestic-futureoption/v1/trading/order` | 선물옵션 주문 (야간) |
| `TTTO1103U` | `/uapi/domestic-futureoption/v1/trading/order-rvsecncl` | 선물옵션 정정/취소 (주간) |
| `TTTN1103U` | `/uapi/domestic-futureoption/v1/trading/order-rvsecncl` | 선물옵션 정정/취소 (야간) |
| `TTTO5201R` | `/uapi/domestic-futureoption/v1/trading/inquire-ccnl` | 선물옵션 체결/미체결 조회 |
| `TTTO5105R` | `/uapi/domestic-futureoption/v1/trading/inquire-psbl-order` | 선물옵션 주문가능 조회 |
| `FHMIF10000000` | `/uapi/domestic-futureoption/v1/quotations/inquire-price` | 선물옵션 현재가 조회 |

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

`stock_list` 항목: `name`, `code`, `exchange`(KOSPI/KOSDAQ), `quantity`, `avg_price`, `current_price`, `profit_loss`, `profit_rate`, `eval_amount`, `mktcap`(원), `per`, `pbr`, `roe`(%)

`overseas_list` 항목: `name`, `code`, `exchange`, `currency`, `quantity`, `avg_price`, `current_price`, `profit_loss`(외화), `profit_loss_krw`(원화환산), `profit_rate`, `eval_amount`, `eval_amount_krw`(원화환산), `mktcap`(USD), `per`, `pbr`, `roe`(%)

`futures_list` 항목: `name`, `code`, `trade_type`(매수/매도 포지션), `quantity`, `avg_price`, `current_price`, `profit_loss`, `profit_rate`, `eval_amount`

---

### `services/` — 서비스 레이어

`stock/` 패키지의 데이터 소스를 조합해 웹 API용 응답을 조립한다.

| 파일 | 역할 |
|------|------|
| `exceptions.py` | 서비스 레이어 공용 예외. `ServiceError`(기본 400) 상속: `NotFoundError`(404), `ExternalAPIError`(502), `ConfigError`(503), `PaymentRequiredError`(402). `main.py`에서 `@app.exception_handler(ServiceError)`로 일괄 HTTP 변환. |
| `watchlist_service.py` | 관심종목 대시보드 + 종목 상세. 국내=pykrx+DART, 해외=yfinance 분기. `resolve_symbol(name_or_code, market)`. `get_stock_detail()` basic에 `roe`, `dividend_yield`, `dividend_per_share` 포함. financial rows에 `oi_margin`(영업이익률), `net_margin`(순이익률) 포함. |
| `detail_service.py` | 재무 테이블 + PER/PBR 히스토리 + CAGR 종합 리포트. 해외는 yfinance(최대 4년), 밸류에이션 차트 빈 데이터 반환. `_get_report_kr()`/`_get_report_us()` 모두 `fetch_forward_estimates_yf()` 호출 — 응답에 `forward_estimates` 필드 포함. |
| `order_service.py` | KIS API 직접 호출로 국내/해외/선물옵션 주문 발송·정정·취소·미체결 조회·당일 체결 내역·이력 조회·예약주문 관리·FNO 시세·로컬 DB 대사. **계층 분리**: `routers/order.py`의 유일한 의존 대상. `cancel_order()` → 로컬 DB 즉시 CANCELLED 갱신 + `local_synced`/`order_status` 응답. `modify_order()` → 로컬 DB 가격/수량 즉시 반영. `get_order_history()` → 반환 전 `_reconcile_active_orders()` 자동 대사(체결+미체결 양쪽 조회, 양쪽 다 없으면 CANCELLED). `get_fno_price()` → FHMIF10000000 REST. `create_reservation()` → 도메인 규칙 검증 후 DB 삽입. `_strip_leading_zeros()`로 10자리→8자리 주문번호 변환. FNO: `_is_fno_night_session()`으로 주간/야간 TR_ID 자동 선택. `KIS_ACNT_PRDT_CD_FNO` 미설정 시 `ConfigError` → 503. |
| `reservation_service.py` | 예약주문 실행 엔진. `asyncio` 20초 간격 폴링. 가격 조건(`price_below`/`price_above`) + 시간 조건(`scheduled`) 체크 후 자동 주문 발송. |
| `quote_service.py` | **KISQuoteManager** + **OverseasQuoteManager** + **FinnhubWSClient**. 국내: KIS WS 단일 연결 + 심볼별 `asyncio.Queue` pub/sub. WS 끊김 시 REST fallback(`FHKST01010100`) 3초 폴링 자동 전환(심볼 간 0.1초 throttle), 재연결 시 자동 해제. 재연결 지수 백오프(1→30초). **approval key 12시간 TTL**: `_get_approval_key()` — 발급 후 12시간 경과 시 자동 재발급. **REST token 12시간 TTL**: `_get_rest_token_sync()` — 동일. **비개장일 대응**: 구독 즉시 `_push_initial_price()`로 yfinance 직전 거래일 가격 push. REST fallback `price=0` 시 yfinance fallback. **Queue overflow 로깅**: `_broadcast()`에서 큐 만재 시 100건마다 경고 로그. **FNO WS 지원**: `subscribe(is_fno=True)` + `_FNO_TR_IDS` 상수 딕셔너리 + `_resolve_fno_type(symbol)`로 심볼 첫 자리 기반 TR_ID 자동 선택(결과 `_fno_types` dict에 캐싱). FNO TR_ID: 지수선물(1xxx)=H0IFASP0/H0IFCNT0, 지수옵션(2xxx)=H0IOASP0/H0IOCNT0, 주식선물(3xxx 선물)=H0ZFASP0/H0ZFCNT0, 주식옵션(3xxx 옵션)=H0ZOASP0/H0ZOCNT0. 해외: `FINNHUB_API_KEY` 있으면 Finnhub WS(30 심볼), 없으면 yfinance 2초 폴링. `fast_info.last_price or previous_close` 패턴으로 비개장일에도 직전 종가 표시. 구독자 0이면 on-demand cancel. |
| `advisory_service.py` | AI자문 서비스. `refresh_stock_data()` — 기본적/기술적 분석 수집 후 `advisory_cache` 저장(포워드 가이던스 포함). `generate_ai_report()` — 캐시 데이터 기반 OpenAI GPT-4o 호출 후 리포트 저장. **3전략 프레임워크**: 변동성 돌파(Larry Williams, K=0.3/0.5/0.7), 안전마진(Graham Number=√(22.5×EPS×BPS)), 추세추종(MA정배열+MACD+RSI). `_calc_graham_number()` 헬퍼. 출력 JSON에 `전략별평가` 섹션 포함. `max_completion_tokens=2500`. ServiceError 계층 사용 (HTTPException 직접 raise 없음). |

**국내/해외/FNO 분기 기준**: `stock/utils.py`의 `is_domestic(code)` — 6자리 숫자이면 국내(KRX), 아니면 해외. `is_fno(code)` — FNO 마스터 단축코드 형식(6자리 숫자가 아니고 알파벳+숫자 혼합) 여부 판별.

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
| `db_base.py` | SQLite 공용 유틸. `connect(db_name, init_fn)` contextmanager — DB 생성/init 중복 방지(`_initialized` set). `row_to_dict()`. 4개 store(store/order_store/advisory_store/market_board_store)에서 공용 사용. |
| `store.py` | 관심종목 CRUD. `~/stock-watchlist/watchlist.db` (SQLite). 복합 PK `(code, market)`. `market` 컬럼 자동 마이그레이션. |
| `order_store.py` | 주문 이력 + 예약주문 CRUD. `~/stock-watchlist/orders.db` (SQLite). `orders` + `reservations` 테이블. `update_order_details(order_id, price, quantity, order_type)` — 정정 사항 로컬 반영. |
| `advisory_store.py` | AI자문 DB CRUD. `~/stock-watchlist/advisory.db` (SQLite). `advisory_stocks`(자문종목) + `advisory_cache`(분석데이터) + `advisory_reports`(AI리포트 히스토리) 3테이블. `get_report_history(code, market, limit=20)` — 히스토리 목록(본문 제외, 최신순). `get_report_by_id(id)` — 특정 리포트 조회. |
| `advisory_fetcher.py` | AI자문 데이터 수집. `fetch_15min_ohlcv_kr()` — KIS 1분봉 4회 호출(시간대별) → 15분 resample, 30봉 미만 시 yfinance fallback. `fetch_ohlcv_by_interval(code, market, interval, period)` — 타임프레임/기간 지정 OHLCV 수집 + 기술지표 자동 계산 반환 (`{ohlcv, indicators}`). yfinance interval/period 제한 자동 적용(`15m` max 60d, `60m` max 2y). `calc_technical_indicators()` — MACD/RSI(Wilder)/Stochastic/%K%D/볼린저밴드/MA5·20·60·**ATR(14, Wilder법)**/MA배열(`ma_alignment`: 정배열/역배열/혼합)/**K=0.3·0.5·0.7 변동성 돌파 목표가** 순수 pandas 구현, 최대 300봉. `current_signals`에 `ma5`, `ma60`, `ma_alignment`, `atr`, `volatility_target_k03/05/07` 추가. 모듈 레벨 KIS 토큰 캐시(`_kis_token_cache`)로 분당 1회 발급 제한 우회. `fetch_segments_kr()` — OpenAI 기반 사업부문 추론. |
| `utils.py` | `is_domestic(code)` — 6자리 숫자=국내, 아니면 해외. `is_fno(code)` — FNO 단축코드 여부 판별. 모든 모듈에서 국내/해외/FNO 분기에 사용. |
| `symbol_map.py` | pykrx 기반 종목코드↔종목명 매핑 (7일 캐시). `_find_latest_trading_day()`로 최근 거래일 자동 탐색. `code_to_name()` — 맵 빌드 실패 시 `get_market_ticker_name()` 직접 호출 fallback. |
| `market.py` | **yfinance 기반** 시세/시가총액/52주 고저/PER/PBR + 기간별 수익률 (2026-02 KRX 서버 변경으로 pykrx 전면 yfinance 전환). `_kr_yf_ticker_str(code)` — `.KS`/`.KQ` suffix 자동 선택 (7일 캐시). `fetch_market_metrics(code)` — 잔고·관심종목·AI자문용 시가총액·PER·PBR·ROE·**배당수익률·주당배당금** 조회 (6시간 캐시). 배당수익률: `dividendYield`(이미 % 형태, KR/US 공통) 우선 사용, 없으면 `trailingAnnualDividendYield × 100` fallback (ADR 환율 오류 방지). 주당배당금: `dividendRate`(연간, 원). |
| `market_board.py` | 시세판 데이터. `fetch_new_highs_lows()` — 시총 상위 200종목 yfinance 배치 스캔, 신고가/신저가 탐지(3개월 거래량 0·연간변동폭 3% 미만 제외, 중복 시 거리 기반 분류). `fetch_sparkline(code, market)` — 1년 주봉 종가(24시간 캐시). `fetch_sparklines_batch(items)` — ThreadPoolExecutor 병렬 배치. |
| `market_board_store.py` | 시세판 별도 등록 종목 CRUD (`~/stock-watchlist/market_board.db`). `all_items()` / `add_item(code, name, market)` / `remove_item(code, market)`. 복합 PK `(code, market)`. |
| `dart_fin.py` | OpenDart `fnlttSinglAcntAll` API 기반 재무제표 조회. 3년 단위 배치 호출로 최대 10년치 수집. DART 사업보고서 링크(`dart_url`) 포함. `_ACCOUNT_KEYS`에 적자 기업 변형 계정명(`영업손실`, `당기순손실`, `매출` 등) 포함. `fetch_income_detail_annual()` — 매출원가/SGA/이자비용/EPS 세부 손익. `fetch_bs_cf_annual()` — 대차대조표(자산/부채/자본) + 현금흐름표(영업/투자/재무 CF, CAPEX, FCF). **`latest_year = today.year - 1` (월 경계 제거)** — 3월에도 전년도(2025) 보고서 조회. **첫 배치 fallback**: 첫 배치 빈 결과 시 `anchor-1`로 재시도 (최신연도 미공시 기업 대응). |
| `yf_client.py` | yfinance 기반 해외주식 데이터. `validate_ticker`, `fetch_price_yf`, `fetch_detail_yf`(ROE+**배당수익률+주당배당금** 포함), `fetch_period_returns_yf`, `fetch_financials_multi_year_yf`. NaN → None 자동 정제. `fetch_financials_multi_year_yf`는 캐시에 전체 연도를 저장하고 반환 시점에 슬라이싱 (부분 캐시 버그 방지). `fetch_price_yf()`: `fast_info.last_price or previous_close` 패턴으로 비개장일(주말/공휴일)에도 직전 종가 반환. AI자문용 추가 함수: `fetch_income_detail_yf()` / `fetch_balance_sheet_yf()` / `fetch_cashflow_yf()` / `fetch_metrics_yf()`(PER·PBR·PSR·EV/EBITDA·ROE·ROA) / `fetch_segments_yf()`(사업부문, best-effort). `fetch_detail_yf()` 반환: `dividend_per_share` 필드 포함 (`dividendRate`, USD). **`fetch_forward_estimates_yf(code, is_kr=False)`** (신규): 애널리스트 컨센서스 추정치 반환. `is_kr=True` 시 `.KS`/`.KQ` suffix 자동 선택. 반환: `{eps_current_year, eps_forward, forward_pe, revenue_current, revenue_forward, net_income_estimate, net_income_forward, shares_outstanding, target_mean_price, target_high_price, target_low_price, num_analysts, recommendation, current_fiscal_year_end}`. `net_income_estimate = eps_current_year × shares_outstanding`. TTL 6시간 캐시 (`yf:forward:{code}`). |
| `fno_master.py` | KIS 선물옵션 마스터파일 다운로드/파싱/검색. 지수선물/옵션(`fo_idx_code_mts.mst.zip`) + 주식선물/옵션(`fo_stk_code_mts.mst.zip`). `get_fno_symbol_map()` — `{단축코드: {name, product_type, atm, strike, underlying_name, ...}}` (캐시 7일). `search_fno_symbols(query, limit=10)`. `validate_fno_symbol(code)`. 파이프(`\|`) 구분자, CP949 인코딩. SSL 검증 우회. |
| `sec_filings.py` | SEC EDGAR EFTS API 기반 미국 10-K/10-Q 공시 조회. 키 불필요. 국내 공시와 동일한 필드 구조 반환. |
| `display.py` | Rich 테이블 출력 + CSV 내보내기. |
| `cache.py` | SQLite TTL 캐시 (`~/stock-watchlist/cache.db`). `set_cached`/`get_cached` 모두 NaN/Inf → None 자동 sanitize. |
| `cli.py` | Click CLI. `stock watch add/remove/list/memo/dashboard/info` 명령. |

**`store.py` 마이그레이션**: 기존 `code TEXT PRIMARY KEY` 테이블에 `ALTER TABLE ... ADD COLUMN market TEXT NOT NULL DEFAULT 'KR'` 자동 실행. 기존 데이터는 모두 `KR`로 처리.

**`symbol_map.py` pykrx fallback**: `get_market_ticker_list(date)`가 KRX 서버 이슈로 빈 리스트를 반환하는 경우가 있다. `_find_latest_trading_day()`는 최근 10거래일을 역순으로 탐색해 유효한 날짜를 찾는다. 빌드 자체가 실패하면 `code_to_name()`이 `get_market_ticker_name(code)` 직접 호출로 fallback해 종목명을 반환한다. 종목명이 코드로 저장되는 현상이 발생하면 이 경로를 확인할 것.

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
  vite.config.js          /api/* → localhost:8000 프록시, /ws → ws://localhost:8000 (WebSocket)
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
      order.js            placeOrder / fetchOpenOrders / cancelOrder / modifyOrder / fetchExecutions /
                          fetchBuyable(symbol, market, price, orderType, side) /
                          fetchFnoPrice(symbol, mrktDiv) → GET /api/order/fno-price
      advisory.js         fetchAdvisoryStocks / addAdvisoryStock / removeAdvisoryStock /
                          refreshAdvisoryData(code, market, name) / fetchAdvisoryData / generateReport /
                          fetchReport / fetchReportHistory(code, market, limit) / fetchReportById(code, id, market) /
                          fetchAdvisoryOhlcv(code, market, interval, period)
      search.js           searchStocks(q, market) → GET /api/search
    hooks/
      useScreener.js      { data, loading, error, search }
      useEarnings.js      { data, loading, error, load(startDate, endDate, market) }
      useBalance.js       { data, loading, error, load }
      useWatchlist.js     useWatchlist (CRUD, market 파라미터) + useDashboard + useStockInfo
      useDetail.js        useDetailReport
      useOrder.js         useOrderPlace / useBuyable(load(symbol,market,price,orderType,side)) / useOpenOrders / useExecutions / useOrderHistory / useOrderSync / useReservations
      useNotification.js  토스트 상태 관리 + 브라우저 Notification API 래퍼
      useWebSocket.js     공용 WebSocket 훅. 연결 수명주기 + 지수 백오프 재연결(500ms→10초) + visibilitychange. { connected, sendMessage }. buildWsUrl(path) 헬퍼 export.
      useQuote.js         실시간 호가 WebSocket 훅 (useWebSocket 기반). `useQuote(symbol, market='KR')` — market 파라미터를 WS URL `?market=` 쿼리로 전달. { price, change, changeRate, sign, asks, bids, totalAskVolume, totalBidVolume, connected }. rAF throttle 자체 관리.
      useMarketBoard.js   `useMarketBoard` (신고가/신저가 + sparkline) + `useDisplayStocks` (관심종목+별도등록 종목 API 캡슐화). MarketBoardPage에서 api/ 직접 import 대신 이 훅 사용.
      useAdvisory.js      useAdvisoryStocks (CRUD) / useAdvisoryData (load + refresh) /
                          useAdvisoryReport (load + generate + loadById, history 상태 포함) /
                          useAdvisoryOhlcv (load(code, market, interval, period) → { ohlcv, indicators, interval, period })
    components/
      layout/Header.jsx   네비게이션 바 (7개 메뉴, 로고: "DK STOCK")
      common/             LoadingSpinner, ErrorAlert, EmptyState, DataTable, ToastNotification
                          WatchlistButton (code/market/alreadyAdded props, ★/+ 버튼, StockTable·FilingsTable 공용)
                          CandlestickChart (ohlcv/indicators props, 캔들+MA5/20/60+BB+거래량, PriceChartPanel·TechnicalPanel 공용)
      screener/           FilterPanel, StockTable (WatchlistButton import — common/WatchlistButton 사용)
      earnings/           FilingsTable  (국내/미국 컬럼 분기, market prop, WatchlistButton import — common/WatchlistButton 사용)
      balance/            PortfolioSummary, HoldingsTable, OverseasHoldingsTable, FuturesTable
      watchlist/          AddStockForm (시장 선택 드롭다운), WatchlistDashboard (통화 표시), StockInfoModal
      detail/             StockHeader, FinancialTable, ValuationChart, ReportSummary
      order/              OrderForm, OrderConfirmModal, OpenOrdersTable, ModifyOrderModal,
                          ExecutionsTable, OrderHistoryTable, ReservationForm, ReservationsTable, SyncButton,
                          OrderbookPanel (실시간 호가창)
      advisory/           FundamentalPanel (포워드추정치 + 재무제표 3종 + 계량지표 + 파이차트)
                          TechnicalPanel (타임프레임/기간 선택 + ATR/MA배열/K=0.3·0.5·0.7 시그널 + 캔들스틱+MA+BB / 거래량 / MACD / RSI / Stochastic)
                          AIReportPanel (GPT-4o 종합의견 + 전략별평가[변동성돌파/안전마진/추세추종] + 기술적시그널 + 리스크/투자포인트. 리포트 2개 이상 시 날짜 드롭다운으로 과거 리포트 선택 가능)
    pages/
      DashboardPage.jsx   /         잔고 요약 + 오늘 공시 + 시총 상위
      ScreenerPage.jsx    /screener
      EarningsPage.jsx    /earnings  국내/미국 탭 선택 + 기간 조회
      BalancePage.jsx     /balance
      WatchlistPage.jsx   /watchlist
      DetailPage.jsx      /detail/:symbol  탭 UI (재무분석/밸류에이션/종합 리포트[서브탭: CAGR요약/기본적분석/기술적분석/AI자문])
      OrderPage.jsx       /order     탭 UI (주문발송/미체결/체결내역/주문이력/예약주문)
      MarketBoardPage.jsx /market-board  시세판: 신고가/신저가 Top10 + 사용자 선택 종목(관심종목 자동 동기화). 실시간 WS.
```

**프론트엔드 규칙**
- 시가총액: 억/조 포맷팅은 프론트에서 처리
- 한국 관례: 상승 = 빨간색, 하락 = 파란색
- KIS 키 없으면 BalancePage에 안내 메시지 표시 (에러 대신)
- ScreenerPage: "조회하기" 버튼 클릭 시 API 호출 (onChange 즉시 호출 안 함)
- WatchlistDashboard: 종목명 클릭 → `/detail/:symbol` 페이지로 이동
- StockInfoModal: 재무 테이블 연도 클릭 → DART 사업보고서 링크 (국내만)
- DetailPage: Recharts로 PER/PBR 시계열 차트 렌더링. 국내=KRX 인증 기반(일반적으로 빈 배열), 해외=분기 EPS/BPS + 일별 주가 추정 (`fetch_valuation_history_yf`)
- EarningsPage: 국내/미국 탭 선택 → 조회 시 필터 초기화. 종목명/종목코드 클라이언트 사이드 필터.
- FilingsTable: `market` prop으로 국내/미국 분기. 미국은 10-K/10-Q 배지 + SEC 링크. `WatchlistButton`은 market 파라미터 포함.
- WatchlistDashboard: 통화 배지 (US 종목은 `[US]`), 금액 단위 (KRW=억, USD=M). 삭제/메모 편집 시 market 파라미터 포함.
- AddStockForm: 시장 드롭다운 (`국내 KRX` / `미국 NASDAQ·NYSE`). 미국 선택 시 티커 코드 입력 안내.
- BalancePage: 국내주식 / 해외주식 / 국내선물옵션 3개 섹션으로 분리. 해외·선물 보유분이 있을 때만 해당 섹션 표시
- PortfolioSummary: 해외주식·외화 예수금 보유 시 카드 하단에 세부 분류 표시 (국내/해외 원화환산 분리)
- OverseasHoldingsTable: 거래소·통화 컬럼 포함. `평가손익(외화)` + `평가손익(원화)` 두 컬럼 표시. 외화 소수점 포맷
- 매입단가 포맷: 국내주식 `Math.floor()` 소수점 절사(정수 표시), 해외주식 소수점 2자리 고정
- FuturesTable: 포지션 뱃지 (매수=빨강, 매도=파랑), 미결제수량 표시
- DataTable: 모든 컬럼 헤더 클릭 시 정렬 (⇅ 아이콘, 재클릭 시 asc/desc 토글, 숫자/문자 자동 구분). 모든 잔고 테이블에 공통 적용. `renderContext` prop으로 `navigate` 등 외부 의존성 전달 지원. `sortable: false` 컬럼 설정 지원.
- HoldingsTable(국내주식): 거래소(KOSPI/KOSDAQ) → 종목코드 → 종목명 → 투자비중(%) → 보유수량 → 평가금액 → 매입단가 → 현재가 → 평가손익 → 수익률 → 시가총액 → PER → ROE → PBR → **배당수익률** → 주문(매도/매수 버튼) 순서. 투자비중은 카테고리 내 eval_amount 기준.
- OverseasHoldingsTable(해외주식): 거래소 → 종목코드 → 종목명 → 투자비중(%) → 통화 → 보유수량 → 평가금액(외화) → 매입단가 → 현재가 → 평가손익(외화) → 평가손익(원화) → 수익률 → 시가총액 → PER → ROE → PBR → **배당수익률** → 주문(매도/매수 버튼). 투자비중은 eval_amount_krw 기준.
- FinancialTable: currency-aware 단위 표시. USD면 M USD 기준으로 1,000M 이상은 $B, 1,000,000M 이상은 $T. KRW는 억/조. `forward` prop: `ForwardSection` 컴포넌트(포워드 PER/EPS/매출/목표가/투자의견 카드, 데이터 없으면 숨김) + 재무요약 테이블에 `{fyYear}E`/`{fyYear+1}E` 추정 열 추가 (인디고 계열 스타일, 매출·순이익 추정값, 영업이익은 `-`).
- StockHeader: currency-aware 현재가/등락/시총 표시. PER·PBR은 `Math.floor()` 정수 표시.
- StockInfoModal: PER·PBR `Math.floor()` 정수 표시. ROE(%), 배당수익률(%), 주당배당금(DPS, 국내=원/해외=$) InfoCard 추가. 재무 테이블에 `MarginRow`(영업이익률·순이익률 %) 추가.
- OrderPage: 5탭 UI (주문발송 / 미체결 / 체결내역 / 주문이력 / 예약주문). URL 파라미터(`?symbol=&market=&side=&quantity=`)로 잔고 페이지 매도/매수 버튼과 연계. **공유 상태**(symbol/symbolName/market)를 최상단에서 관리. 주문발송 탭: 상단 `SymbolSearchBar` → [신규주문|정정취소] 서브탭 → 2컬럼(호가창/주문폼) → 하단 `PriceChartPanel`. `isMounted` ref로 mount 시 중복 API 호출 방지. **미체결/체결 탭 MARKET_TABS**: KR / US / FNO 3개.
- SymbolSearchBar: 주문 페이지 공용 종목 검색 컴포넌트. 시장 드롭다운: `KR`(국내 KRX) / `US`(미국 NASDAQ·NYSE) / `FNO`(선물옵션) 3개. KR·FNO=자동완성 드롭다운(`execAutoSearch`로 통합), US=티커 직접 입력 검증. FNO 드롭다운 항목에 `underlying_name` 표시. 시장 변경 시 debounce 취소+상태 초기화. `marketRef`로 async race condition 방지.
- OrderbookPanel: `symbol` + `market` prop. **KR/FNO 모두 `useQuote(symbol, market)` 훅 사용** (REST 폴링 제거). KR=KIS WS 10호가(실시간), FNO=KIS FNO WS 호가(H0IFASP0/H0ZFASP0 등, 실시간), US=현재가만(호가 미지원 안내). KR/FNO는 동일한 호가창 그리드 렌더링 공유. FNO 현재가 클릭 버튼("현재가 매수"/"현재가 매도") → `onPriceSelect(price, side)`. 국내/FNO 매도호가 클릭 → `side='sell'`, 매수호가 클릭 → `side='buy'`. `connected` 배지(초록/회색).
- OrderForm: `symbol`, `symbolName`, `market` props로 외부 제어. `externalPrice` prop → 지정가 자동 세팅. `externalSide` prop → 매매방향 자동 세팅(호가 클릭 연동). 종목/시장 선택 로직은 `SymbolSearchBar`로 이전. **FNO**: `FNO_ORDER_TYPE_OPTIONS`(지정가/시장가/조건부지정가/최유리지정가 4종) + `FNO_CONDITION_OPTIONS`(IOC/FOK). `mapFnoOrderCodes(orderType, condition)` → `{nmpr_type_cd, krx_nmpr_cndt_cd, ord_dvsn_cd}` 자동 매핑. 가격 step=0.01. 매수가능 조회에 `side` 파라미터 전달. FNO 주문코드: `NMPR_TYPE_CD` 01=지정가/02=시장가/03=조건부지정가/04=최유리지정가, `KRX_NMPR_CNDT_CD` 0=없음/3=IOC/4=FOK, `ORD_DVSN_CD` 01~04(기본) / 10=지정가IOC / 11=지정가FOK / 12=시장가IOC / 13=시장가FOK / 14=최유리IOC / 15=최유리FOK.
- PriceChartPanel: 가격 차트 패널(신규). `useAdvisoryOhlcv` 훅 재사용. 타임프레임(15m/60m/1d/1wk)+기간 선택. 캔들+MA5/20+볼린저밴드+거래량. 500ms debounce로 symbol 변경 감지.
- OpenOrdersTable: `api_cancellable` 필드로 API 취소 가능 여부 판별. `excg_id_dvsn_cd === 'SOR'`(HTS/MTS 주문)은 정정/취소 버튼 대신 "앱취소필요" 안내 표시.
- ToastNotification: 화면 우상단 고정 토스트 알림 컨테이너. `App.jsx`에서 `useNotification` 훅과 함께 마운트.
- DetailPage: 종합 리포트 탭에 4개 서브탭 (CAGR 요약 / 기본적 분석 / 기술적 분석 / AI 자문). cagr 외 서브탭에서만 [새로고침] 버튼 표시, AI자문 서브탭에서 [AI분석 생성] 버튼 추가. advisory 데이터는 최초 서브탭 진입 시 lazy load.
- FundamentalPanel: `data`, `market` props. ① 애널리스트 추정치 섹션(`ForwardEstimatesSection`): `forward_estimates` 있을 때만 표시, 포워드 EPS/매출/순이익 추정·목표가·투자의견 카드 ② 계량지표 카드(PER/PBR/PSR/EV·EBITDA/ROE/ROA) ③ 손익계산서 테이블+막대차트(`{fyYear}E`/`{fyYear+1}E` 추정 열 포함) ④ 대차대조표 테이블 ⑤ 현금흐름표 테이블+막대차트 ⑥ 사업별 매출비중 파이차트. KR 사업부문에는 "AI추정" 배지 표시.
- TechnicalPanel: `data`, `symbol`, `market` props. 타임프레임 선택 UI (15분/60분/1일/1주) + 기간 선택 (타임프레임별 허용 범위). interval 변경 시 `GET /api/advisory/{code}/ohlcv?interval=&period=` 자동 호출. 초기 데이터는 `data.technical.ohlcv` 캐시 사용. 시그널 요약 카드: MACD/RSI/Stochastic/MA20/변동성돌파 목표가(K=0.5) + **ATR(14)** + **MA배열**(정배열=빨강/역배열=파랑/혼합=회색) + **K=0.3·0.5·0.7 변동성 돌파 목표가**(보라 배지) 추가. 차트 순서: 캔들스틱+MA+볼린저밴드 → 거래량 → MACD → RSI(70/30) → Stochastic(80/20).
- AIReportPanel: [AI분석 생성] 버튼 → 종합투자의견(매수/중립/매도 배지) → **전략별평가 3컬럼 카드** (변동성돌파/안전마진/추세추종, 구 리포트에는 미표시) → 기술적시그널 → 리스크요인 목록 → 투자포인트 목록. OPENAI_API_KEY 미설정 시 503 안내, 크레딧 부족(402) 시 한국어 안내.

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
| `KIS_ACNT_NO` / `KIS_ACNT_PRDT_CD_STK` 미설정 | 경고 출력 |
| `KIS_ACNT_PRDT_CD_FNO` 미설정 | 정보 출력. 선물옵션 잔고 조회 비활성화 |
| `OPENDART_API_KEY` 미설정 | 경고 출력. 국내 `/api/earnings/filings`, `/api/detail/*` → 502 (해외 공시는 영향 없음) |
| `OPENAI_API_KEY` 미설정 | 경고 출력. `/api/advisory/{code}/analyze` → 503 (데이터 수집/조회는 정상) |
| `frontend/dist/` 존재 | "정적 파일 서빙" 안내 |
| `/app` 쓰기 불가 | 경고 출력 (캐시 비활성화) |
| 항상 실행 | `cache.db` 전체 초기화 — 배포 후 구버전 캐시(필드 누락 등) 방지 |

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
| `OPENAI_MODEL` | 선택 | AI자문 리포트 생성 모델. 기본값: `gpt-4o`. 예: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `o3-mini`. `max_completion_tokens` 사용 (신규 모델 호환). |
| `FINNHUB_API_KEY` | 선택 | 해외주식 실시간 시세 (Finnhub WS). 미설정 시 yfinance 2초 폴링(15분 지연). https://finnhub.io 무료 플랜, 30 심볼 한도. |
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

`requirements.txt`에 포함된 패키지: `websockets` (실시간 호가창 KIS WS 연결용, `services/quote_service.py`)

`requirements.txt`에 미포함 — `wrapper.py`의 일부 기능은 별도 설치 필요:
- AES 복호화 (`KoreaInvestmentWS` 체결통보): `pip install pycryptodome`

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
| **OpenAI API** | 종합 투자 의견 생성 (3전략 프레임워크 분석). `OPENAI_API_KEY` 필요. 모델은 `OPENAI_MODEL` env (기본 `gpt-4o`). `response_format={"type":"json_object"}` 사용. `max_completion_tokens=2500` (신규 모델 호환). | `services/advisory_service.py` |

---

## 캐시 시스템

| 위치 | 용도 | TTL |
|------|------|-----|
| `screener_cache.db` (프로젝트 루트) | 스크리너 KRX/DART 데이터 캐시 | 만료 없음 (날짜키 기반) |
| `~/stock-watchlist/cache.db` | 관심종목 시세/재무/종목코드/수익률 캐시 (국내+해외) | 키별 상이 |
| `~/stock-watchlist/watchlist.db` | 관심종목 목록 (SQLite CRUD, 국내+해외) | 영구 |
| `~/stock-watchlist/orders.db` | 주문 이력 + 예약주문 (SQLite). `orders` + `reservations` 테이블 | 영구 |
| `~/stock-watchlist/market_board.db` | 시세판 별도 등록 종목 (SQLite). `market_board_stocks` 테이블. 복합 PK `(code, market)` | 영구 |
| `~/stock-watchlist/advisory.db` | AI자문 (SQLite). `advisory_stocks` + `advisory_cache` + `advisory_reports` 3테이블 | 영구 |

`stock/` 캐시 TTL: `corpCode.xml` 30일, `symbol_map` 7일, 시세/재무 24시간, `market:period_returns:` 1시간, `yf:*` 1~24시간.

**NaN 주의**: Python `json.loads`는 `NaN` 리터럴을 `float('nan')`으로 파싱한다. `cache.py`의 `_sanitize()`가 get/set 양쪽에서 NaN → None 변환을 보장한다.

**시작 시 캐시 초기화**: `entrypoint.sh`에서 uvicorn 시작 직전 `cache.db` 전체를 삭제한다. 코드 배포 후 구버전 캐시(필드 구조 변경, NaN 등)로 인한 오류를 원천 차단. `watchlist.db`(관심종목 목록)는 별개 파일이므로 영향 없음.

**`market:metrics:` 캐시**: `fetch_market_metrics(code)` — `{market_type, mktcap, per, pbr, roe, dividend_yield, dividend_per_share}` 저장. TTL 6시간. 잔고·관심종목·AI자문에서 각 종목에 대해 호출.

**SQLite WAL 모드**: `stock/db_base.py`와 `stock/cache.py`에서 `PRAGMA journal_mode=WAL` 활성화 + timeout 10초. 읽기-쓰기 동시성 향상, `database is locked` 오류 사실상 제거. 예약주문 스케줄러와 사용자 API 요청이 동시에 DB에 접근해도 안전.

---

## 해외주식 지원 범위 및 제약

| 기능 | 지원 여부 | 비고 |
|------|----------|------|
| 관심종목 추가/삭제 | ✅ | 티커 코드 직접 입력 (AAPL, NVDA 등) |
| 대시보드 시세 | ✅ | USD, 15분 지연 |
| 대시보드 재무 | ✅ | USD, M 단위, 최대 4년 |
| 종목 상세 재무 | ✅ | yfinance 최대 4년 |
| CAGR 종합 리포트 | ✅ | yfinance 재무 기반 |
| PER/PBR 히스토리 차트 | ✅ | 분기 EPS/BPS + 일별 주가 기반 추정 (`fetch_valuation_history_yf`). 최대 5년. |
| 공시 조회 (SEC) | ✅ | 10-K/10-Q, 수익률 포함 |
| 스크리너 | ❌ | 미지원 (국내 전용) |
| 종목명 검색 | ❌ | 티커 코드만 가능 |
| AI자문 (국내 KR) | ✅ | DART 재무 3종 + pykrx 계량지표 + KIS 15분봉(yfinance fallback) + GPT-4o. DetailPage 종합리포트 탭에서 접근. |
| AI자문 (해외 US) | ✅ | yfinance 재무 3종 + yfinance 계량지표 + yfinance 15분봉 + GPT-4o. DetailPage 종합리포트 탭에서 접근. |
| 지원 시장 | US | NASDAQ/NYSE/AMEX. 일본·홍콩 등 추후 확장 가능 구조 |

---

## 시세 수신 개선 이력 (Phase 1 → Phase 4)

### Phase 1 (2026-03 완료)
- rAF throttle (`useQuote.js`): 고빈도 WS 메시지 → 최대 60fps 렌더링
- OrderbookPanel `useMemo` + `memo`: asks/bids/maxVolume 재계산 방지
- 지수 백오프 재연결 (클라이언트 500ms→10초, KIS WS 1→30초)
- `visibilitychange` 탭 복귀 즉시 재연결
- `OverseasQuoteManager`: 심볼당 단일 yfinance 폴링 태스크 (N 클라이언트 → 1 호출)
- 100ms 메시지 병합: 국내 WS 고빈도 메시지 → 최대 10건/초
- 장중/장외 TTL 분리 (`stock/market.py`): 국내 `fetch_price` 6분/6시간, `fetch_market_metrics` 1시간/12시간

### Phase 2 (2026-03 완료)
- `_is_us_trading_hours()` (`stock/market.py`): DST 자동 반영 (zoneinfo)
- `stock/yf_client.py` 장중 TTL 분리: `fetch_price_yf` 2분/30분, `fetch_detail_yf` 30분/6시간, `fetch_metrics_yf` 30분/6시간, `fetch_period_returns_yf` 15분/6시간
- **KIS REST fallback** (`KISQuoteManager`): WS 끊김 시 `FHKST01010100` 5초 폴링 자동 전환, WS 재연결 시 자동 해제. `_rest_fallback_loop()` + `_fetch_rest_price()`. 심볼 간 0.2초 throttle.
- **Finnhub WS** (`FinnhubWSClient` + `OverseasQuoteManager`): `FINNHUB_API_KEY` 설정 시 해외주식 실시간 체결가 수신 (무료 플랜 30 심볼). 한도 초과 심볼은 yfinance 폴링 fallback. 전일종가 prefetch로 change 계산.

### 환경변수 추가
- `FINNHUB_API_KEY`: 해외주식 실시간 시세 (선택). 미설정 시 yfinance 2초 폴링(15분 지연) 유지.

### Phase 3 (2026-03 완료)
- **신고가/신저가 그리드 밀도 개선** (`NewHighLowSection.jsx`): `md:grid-cols-4`, `lg:grid-cols-3` 추가. 외부 2컬럼 래퍼 안에서도 충분한 카드 밀도 확보.
- **비개장일 국내 시세 fallback** (`KISQuoteManager`): `subscribe()` 호출 즉시 `asyncio.create_task(_push_initial_price())` — yfinance `fetch_price(symbol)`로 직전 거래일 가격 queue push. `_fetch_rest_price()` KIS 반환 `price=0` 시 yfinance fallback.
- **비개장일 해외 시세 fallback** (`OverseasQuoteManager`): `_prefetch_and_subscribe()`에서 `fi.last_price or fi.previous_close` 패턴. `_poll_loop()`도 동일 패턴 적용, p=None이면 broadcast skip.
- **`fetch_price_yf()` fallback** (`stock/yf_client.py`): `close = _safe(fi.last_price) or _safe(fi.previous_close)` — 관심종목·잔고·AI자문용 해외 시세도 비개장일 직전 종가 반환.
- **FNO 실시간 WebSocket** (`KISQuoteManager` + `routers/quote.py`): FNO 심볼에 KIS WS 실시간 호가 지원 추가. `_FNO_TR_IDS` 상수 딕셔너리 + `_resolve_fno_type(symbol)` + `_send_subscribe_fno()`. `routers/quote.py`에 `?market=FNO` 쿼리 파라미터 추가 → `_stream_fno()` 핸들러로 분기. `useQuote(symbol, market='KR')` 시그니처 변경으로 프론트엔드 market 전달.
- **FNO 주문유형 확장** (`OrderForm.jsx`): 지정가만 지원하던 FNO 주문을 지정가/시장가/조건부지정가/최유리지정가 + IOC/FOK 조건으로 확장. `mapFnoOrderCodes()` 함수로 `ORD_DVSN_CD` 자동 계산. `OrderbookPanel`에서 FNO REST 폴링 제거 → `useQuote` 훅으로 통합.
- **`stock/utils.py` `is_fno(code)` 추가**: FNO 단축코드 식별 함수 추가.

### Phase 4 — 구조 개선 + WS 효율화 (2026-03 완료)
- **주문 도메인 계층 분리**: `routers/order.py`에서 `order_store` 직접 import 완전 제거. 이력 조회·예약주문·FNO 시세 모두 `order_service` 경유. 예약주문 `create_reservation()` 도메인 규칙 검증 추가.
- **주문 즉시 동기화**: `cancel_order()` → 로컬 DB 즉시 CANCELLED + `local_synced`/`order_status` 응답. `modify_order()` → 가격/수량 즉시 반영 + `local_synced`. `place_order()` → `balance_stale: true`.
- **대사 로직 강화**: `sync_orders()` → 체결+미체결 양쪽 조회, 양쪽 다 없으면 CANCELLED 자동 감지. `get_order_history()` 반환 전 자동 대사(best-effort).
- **SQLite WAL 모드**: `db_base.py`, `cache.py` — `PRAGMA journal_mode=WAL` + timeout 10초. 읽기-쓰기 동시성 향상.
- **예외 통일**: `_kis_auth.py`, `balance.py` — `HTTPException` → `ConfigError`/`ExternalAPIError` (ServiceError 계층 통일).
- **프론트엔드 계층 분리**: `MarketBoardPage.jsx` — api/ 직접 import 제거 → `useDisplayStocks()` 훅 사용.
- **Approval Key TTL**: `_get_approval_key()` — 12시간 TTL, 만료 시 자동 재발급.
- **REST Token TTL**: `_get_rest_token_sync()` — 12시간 TTL, 동일 패턴.
- **REST Fallback 최적화**: 폴링 주기 5초→3초, 심볼 간 throttle 0.2초→0.1초.
- **FNO 타입 캐싱**: `_fetch_fno_rest_price_sync()`에서 `_fno_types` dict 캐시 미스 시 결과 저장.
- **Queue Overflow 로깅**: `_broadcast()`에서 큐 만재 시 100건마다 경고 로그.
- **시세판 배칭 단축**: `market_board.py` — 500ms→200ms (호가 100ms와의 격차 축소).

### DART 공시 캐시 버그 수정 (2026-03)
- **원인**: `screener/cache.py`는 TTL 없는 영구 캐시. 당일 오전 조회 시 빈 결과가 캐시되면 이후 제출 공시가 보이지 않음 (골프존 3/19 사업보고서 미노출 사례)
- **수정**: `screener/dart.py`의 `fetch_filings()`에서 `end_date < today`인 경우만 캐시 사용. 오늘 이상 날짜 포함 범위는 항상 DART API 직접 호출.
