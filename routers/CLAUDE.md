# routers/ — API 라우터 패키지

## 라우터 목록

| 파일 | 엔드포인트 | 설명 |
|------|-----------|------|
| `screener.py` | `GET /api/screener/stocks` | 멀티팩터 스크리닝 + yfinance enrichment(**섹터** 포함) + **구루 공식**(preset=greenblatt/neff/seo, DART guru enrichment) + **체제 연계**(regime_aware, 응답에 regime 포함) + 52주 하락률 필터 + Value Trap 경고 |
| `earnings.py` | `GET /api/earnings/filings` | 정기보고서 (국내 DART / 미국 SEC EDGAR) |
| `balance.py` | `GET /api/balance` | KIS 실전계좌 잔고 (국내+해외+선물옵션) |
| `watchlist.py` | `/api/watchlist/*` | 관심종목 CRUD + 대시보드 + 종목정보 + 순서 관리 (국내/해외). `GET/PUT /api/watchlist/order` (/{code} 라우트보다 앞에 등록) |
| `detail.py` | `/api/detail/*` | 10년 재무 + PER/PBR 히스토리 + 종합 리포트 |
| `_kis_auth.py` | (내부 모듈) | KIS 인증 공통 (토큰 관리, hashkey 발급). `balance.py`·`order.py` 공용 |
| `order.py` | `/api/order/*` | 주문 발송/정정/취소/미체결/체결/이력/예약주문 |
| `quote.py` | `WS /ws/quote/{symbol}`, `WS /ws/execution-notice` | 실시간 호가 WebSocket (KR/FNO/US) + 체결통보 WS |
| `advisory.py` | `/api/advisory/*` | AI자문 종목 관리 + 데이터 수집(+리서치)/조회 + AI 리포트 생성(v3 통합). `POST /research` 수동 리서치 수집 |
| `search.py` | `GET /api/search` | 종목 검색 (KR=자동완성, US=티커 검증, FNO=마스터 검색) |
| `market_board.py` | `/api/market-board/*`, `WS /ws/market-board` | 신고가/신저가 + sparkline + 당일 OHLC + 시세판 종목 CRUD + 순서 관리(`GET/PUT /api/market-board/order`) + 실시간 WS(시가/고가/저가 포함) |
| `macro.py` | `/api/macro/*` | 매크로 분석: 지수/뉴스/심리/투자자 + 금리차/신용스프레드/환율/원자재/섹터히트맵/국면. 11개 GET 엔드포인트 |
| `portfolio_advisor.py` | `/api/portfolio-advisor/*` | AI 포트폴리오 자문: `POST /analyze` (GPT 분석), `GET /history` (이력 목록), `GET /history/{id}` (리포트 상세) |
| `report.py` | `/api/reports/*` | 일일 보고서 + 추천 이력 + 성과 통계 + 매크로 체제 이력. 8개 GET 엔드포인트. `GET /by-date` 날짜+시장 조회(신규). `/{report_id}` 패스 파라미터는 마지막에 등록 |
| `pipeline.py` | `/api/pipeline/*` | 투자 파이프라인: `POST /run` (비동기), `POST /run-sync` (동기), `GET /status` (스케줄러+실행 상태) |
| `backtest.py` | `/api/backtest/*` | KIS AI Extensions MCP 연동 백테스트: 프리셋/커스텀/배치 실행, 결과 조회, 이력 삭제 + **전략빌더 CRUD**(변환/검증/저장/로드/삭제). `KIS_MCP_ENABLED=true` 필요. 15개 엔드포인트. 이력에 종목명(`symbol_name`) 부착. 프리셋 params 오버라이드. `commission_rate`/`tax_rate`/`slippage` 거래비용 파라미터 지원. 전략빌더: `POST /strategy/convert`, `POST /strategy/validate`, `GET/POST /strategies`, `GET/DELETE /strategies/{name}` |
| `tax.py` | `/api/tax/*` | 해외주식 양도소득세: 연간 요약/매매내역 CRUD/KIS 적응적 동기화/FIFO 재계산/계산 상세(lots)/시뮬레이션(가상매도). 9개 엔드포인트 |

---

## 핸들러 규칙

- **모든 핸들러는 `def`(sync)** — pykrx/requests가 동기 라이브러리이므로 FastAPI가 threadpool에서 자동 실행
- **예외는 ServiceError 계층 사용** — `HTTPException` 직접 raise 금지. earnings.py/screener.py만 입력 검증(422)에 HTTPException 유지. `main.py`에서 `@app.exception_handler(ServiceError)`로 일괄 HTTP 변환
- `_kis_auth.py` 예외도 `ConfigError`/`ExternalAPIError` 사용 (ServiceError 계층 통일)

## 환경변수 미설정 동작

| 조건 | 결과 |
|------|------|
| KIS 키 미설정 | `/api/balance`, `/api/order/*` → 503 (서버 시작은 정상) |
| OPENDART 키 미설정 | `/api/earnings/filings`(KR), `/api/detail/*` → 502 |
| OPENAI_API_KEY 미설정 | `/api/advisory/{code}/analyze` → 503 (데이터 수집·조회는 정상) |
| OpenAI 크레딧 부족(429) | `/api/advisory/{code}/analyze` → 402 |
| 해외 공시(`market=US`) | OPENDART 키 불필요 (SEC EDGAR 무료) |

---

## `main.py` — FastAPI 서버 진입점

- CORS 미들웨어: `localhost:5173` 허용 (Vite 개발 서버)
- 14개 라우터 등록 (screener, earnings, balance, watchlist, detail, order, quote, advisory, search, market_board, macro, portfolio_advisor, report, pipeline)
- **lifespan**: ① `quote_manager.start()` ② 예약주문 스케줄러 시작 ③ `symbol_map` background pre-warm — 종료 시 역순 정리
- **SPA 라우팅**: `/assets` StaticFiles 마운트 + `/{full_path:path}` 캐치올로 index.html 반환 (라우터 등록 **이후** 마지막)
- `index.html` 응답에 `Cache-Control: no-cache, no-store, must-revalidate` 헤더
- KIS API를 직접 호출하지 않음. 모든 로직은 `routers/` → `services/` → `stock/`/`screener/`로 위임

---

## `order.py` — 주문 관리

**계층 분리**: `order_service`만 import. **`order_store` 직접 접근 금지**. 이력·예약주문·FNO 시세 모두 서비스 계층 경유.

```
POST /api/order/place          주문 발송 (국내/해외/FNO, 매수/매도, 지정가/시장가)
GET  /api/order/buyable        매수가능 금액/수량 (FNO: side 파라미터 필요)
GET  /api/order/open           미체결 목록 (market=KR|US|FNO)
POST /api/order/{order_no}/modify   정정 (FNO: nmpr_type_cd 등)
POST /api/order/{order_no}/cancel   취소
GET  /api/order/executions     당일 체결 내역 (market=KR|US|FNO)
GET  /api/order/history        로컬 DB 주문 이력
POST /api/order/sync           KIS 대사(Reconciliation)
POST /api/order/reserve        예약주문 등록
GET  /api/order/reserves       예약주문 목록
DELETE /api/order/reserve/{id} 예약주문 삭제
GET  /api/order/fno-price      선물옵션 현재가
```

- 주문 발송 → 로컬 `orders.db` 자동 기록 (status: PLACED). 응답에 `balance_stale: true`
- 취소 → 로컬 DB 즉시 CANCELLED + `local_synced: true`
- 정정 → 로컬 DB 가격/수량 즉시 반영 + `local_synced: true`
- `excg_id_dvsn_cd`: `'KRX'`=API 주문(취소 가능), `'SOR'`=HTS/MTS(API 취소 불가)
- 주문번호: 10자리 제로패딩 → `_strip_leading_zeros()`로 8자리 변환

---

## TR_ID 테이블

| TR_ID | 용도 |
|-------|------|
| `TTTC8434R` | 국내주식 잔고 |
| `JTTT3010R` | 해외주식 주야간원장 구분 |
| `TTTS3012R` / `JTTT3012R` | 해외주식 잔고 (주간/야간) |
| `CTRP6504R` | 기준환율 + KRW 합계 |
| `CTFO6118R` | 국내선물옵션 잔고 |
| `TTTC0802U` / `TTTC0801U` | 국내 매수/매도 |
| `TTTC0803U` | 국내 정정/취소 |
| `TTTC8036R` | 국내 미체결 조회 |
| `TTTC8001R` | 국내 당일 체결 |
| `TTTC8908R` | 국내 매수가능 |
| `JTTT1002U` / `JTTT1006U` | 해외 매수/매도 |
| `TTTS3018R` | 해외 미체결 |
| `JTTT3001R` | 해외 당일 체결 |
| `TTTS3007R` | 해외 매수가능 |
| `TTTO1101U` / `STTN1101U` | 선물옵션 주문 (주간/야간) |
| `TTTO1103U` / `TTTN1103U` | 선물옵션 정정/취소 (주간/야간) |
| `TTTO5201R` | 선물옵션 체결/미체결 |
| `TTTO5105R` | 선물옵션 주문가능 |
| `FHMIF10000000` | 선물옵션 현재가 |

### 실전/모의투자 TR_ID 구분

- 실전: `T***`, `J***` (예: `TTTC8434R`)
- 모의: `V***` (예: `VTTC8434R`)
- `wrapper.py`의 `mock` 파라미터로 제어. `routers/balance.py`는 실전 TR_ID 하드코딩.

---

## 에이전트 역할

도메인 에이전트(MacroSentinel/ValueScreener/MarginAnalyst/OrderAdvisor)는 **자문 전용** — HTTP API를 직접 호출하지 않는다. 투자 파이프라인은 `pipeline_service.py`(미구현)에서 서비스 함수를 직접 호출할 예정.

---

## KIS API 주의사항 (잔고)

- `bass_exrt`(기준환율)는 `CTRP6504R` output2 `frst_bltn_exrt`에만 존재 (`TTTS3012R`에 없음)
- 해외 KRW 환산: ① `CTRP6504R` 환율 dict → ② `TTTS3012R` 종목별 계산
- `CTFO6118R` 파라미터: `MGNA_DVSN`(증거금구분, `"01"`), `EXCC_STAT_CD`(정산상태, `"1"`)
- `CTFO6118R` 응답 필드: `cblc_qty`(잔고수량), `sll_buy_dvsn_name`(포지션), `ccld_avg_unpr1`(평균단가), `idx_clpr`(현재가), `evlu_pfls_amt`(평가손익), `evlu_amt`(평가금액)
- 해외/선물 조회 실패 → 해당 목록만 `[]`, 국내주식은 정상

## `/api/balance` 응답 구조

```json
{
  "total_evaluation": "...",
  "stock_eval": "...", "stock_eval_domestic": "...", "stock_eval_overseas_krw": "...",
  "deposit": "...", "deposit_domestic": "...", "deposit_overseas_krw": "...",
  "stock_list": [...], "overseas_list": [...], "futures_list": [...],
  "fno_enabled": true
}
```

- `stock_list`: name, code, exchange, quantity, avg_price, current_price, profit_loss, profit_rate, eval_amount, mktcap, per, pbr, roe
- `overseas_list`: + currency, profit_loss_krw, eval_amount_krw
- `futures_list`: name, code, trade_type, quantity, avg_price, current_price, profit_loss, profit_rate, eval_amount
- `fno_enabled`: `KIS_ACNT_PRDT_CD_FNO` 설정 여부 (프론트엔드에서 FNO 섹션 표시 제어)

> API 파라미터/응답 스키마 상세 → `docs/API_SPEC.md`
