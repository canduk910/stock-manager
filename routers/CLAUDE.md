# routers/ — API 라우터 패키지

> 변경 이력은 `docs/CHANGELOG.md`가 단일 출처. 본 문서는 라우터 책임과 영구 규칙만 기술.

## 라우터 목록

| 파일 | 엔드포인트 | 설명 |
|------|-----------|------|
| `screener.py` | `GET /api/screener/stocks` | 멀티팩터 스크리닝 + yfinance enrichment(섹터 포함) + 구루 공식(preset=greenblatt/neff/seo, DART guru enrichment) + 체제 연계(regime_aware) + 52주 하락률 필터 + Value Trap 경고 |
| `earnings.py` | `GET /api/earnings/filings` | 정기보고서 (KR DART / US SEC EDGAR) |
| `balance.py` | `GET /api/balance` | KIS 실전계좌 잔고 (국내+해외+선물옵션). user_id Depends |
| `watchlist.py` | `/api/watchlist/*` | 관심종목 CRUD + 대시보드 + 종목정보 + 순서 관리. `GET/PUT /order`는 `/{code}` 라우트보다 앞에 등록 |
| `detail.py` | `/api/detail/*` | 10년 재무 + PER/PBR 히스토리 + 종합 리포트 |
| `_kis_auth.py` | (내부) | KIS 인증 공통 (토큰 관리, hashkey, **사용자별 토큰 캐시 dict**). `get_kis_credentials(user_id)` 사용자 키 우선 + 운영자 키 폴백 |
| `order.py` | `/api/order/*` | 주문 발송/정정/취소/미체결/체결/이력/예약주문/FNO 시세 |
| `quote.py` | `WS /ws/quote/{symbol}`, `WS /ws/execution-notice`, `WS /ws/market-status`, `GET /api/quote/us/{symbol}/orderbook`, `GET /api/quote/us/{symbol}/detail` | 실시간 호가 WS (KR/FNO/US) + 체결통보 WS + 장운영정보 멀티플렉스 WS (H0UNMKO0/H0STMKO0/H0NXMKO0). `/ws/quote/{symbol}?exchange=auto\|UN\|KRX\|NXT` (기본 auto, KST 시계 4구간 자동 분기). US REST 폴백 — orderbook(HHDFS76200100, 10단계) + detail(HHDFS76200200, 시/고/저/거래량/52주). 응답 200/503(키 부재)/504(KIS None) |
| `advisory.py` | `/api/advisory/*` | AI자문 종목 관리 + 데이터 수집(+리서치) + AI 리포트 v3 통합. `POST /research` 수동 리서치 수집. `GET /{code}/analyst-reports` (KR=네이버/US=yfinance). `POST /{code}/chat` 보고서 컨텍스트 stateless 챗봇. `POST /{code}/analyze` body `AnalyzeBody(user_comment: Optional[str])` (1000자) — 양면 평가 트리거 |
| `search.py` | `GET /api/search` | 종목 검색 (KR=자동완성, US=티커 검증, FNO=마스터) |
| `market_board.py` | `/api/market-board/*`, `WS /ws/market-board` | 신고가/신저가 + sparkline + 당일 OHLC + 시세판 종목 CRUD + 순서 관리 + 실시간 WS |
| `macro.py` | `/api/macro/*` | 매크로 분석: 지수/뉴스/심리/투자자/금리차/신용스프레드/환율/원자재/섹터히트맵/국면. 11개 GET |
| `portfolio_advisor.py` | `/api/portfolio-advisor/*` | AI 포트폴리오 자문: `POST /analyze`, `POST /chat` (require_admin, `service_name="portfolio_chat"`), `GET /history`, `GET /history/{id}`. `AnalyzeBody.user_comment: Optional[str]` (1000자) — 캐시 키 SHA256에 코멘트 strip 포함 |
| `report.py` | `/api/reports/*` | 일일 보고서 + 추천 이력 + 성과 통계 + 매크로 체제 이력. 8개 GET. `GET /by-date` 날짜+시장 조회. `/{report_id}` 패스 파라미터는 마지막 등록 |
| `pipeline.py` | `/api/pipeline/*` | 투자 파이프라인: `POST /run` (비동기), `POST /run-sync` (동기), `GET /status` (스케줄러+실행 상태) |
| `backtest.py` | `/api/backtest/*` | KIS AI Extensions MCP 백테스트 + 전략빌더 CRUD. fire-and-poll 패턴 (504 + 결과 보존 동시 해소). 17개 엔드포인트 + 로컬 백테스트 2종 (`GET /local/presets`, `POST /run/local`). `commission_rate`/`tax_rate`/`slippage` 거래비용. 4 핸들러에 entry/exit 로그 + ServiceError 본문 `error_id`(8자리 hex) — 동일 id로 stack trace 매칭. telemetry `backtest.local.{success,fail.cause}` (cause: db_error/serialize/timeout/data_load/unknown) |
| `tax.py` | `/api/tax/*` | 해외주식 양도소득세: 연간 요약/매매내역 CRUD/KIS 적응적 동기화/FIFO 재계산/계산 상세(lots)/시뮬레이션. 9개 엔드포인트 |
| `admin.py` | `/api/admin/*` | AI 사용량 관리: 유저별 일별 사용량 / 한도 CRUD / 감사 로그. `require_admin` (내 사용량 조회만 `get_current_user`) |
| `me_kis.py` | `/api/me/kis/*` | 사용자 본인 KIS 자격증명 등록/조회(마스킹)/검증/삭제. `POST` 즉시 검증(`/oauth2/tokenP`). `KIS_ENCRYPTION_KEY` 미설정 시 503 |
| `admin_users.py` | `/api/admin/users/*` | 관리자 전용 사용자 CRUD. 검색(`?q=`)/페이지네이션, role 변경, 비밀번호 reset, 삭제. 응답에 `visit_count`(누적 PageView) |
| `admin_stats.py` | `/api/admin/page-stats/*` | 페이지별 이용현황: 경로별 호출/평균·p95 latency/유저 수/일별 시계열 |

---

## 핸들러 규칙

- **모든 핸들러는 `def`(sync)** — pykrx/requests가 동기 라이브러리이므로 FastAPI가 threadpool에서 자동 실행
- **예외는 ServiceError 계층 사용** — `HTTPException` 직접 raise 금지. earnings.py/screener.py만 입력 검증(422)에 HTTPException 유지. `main.py`에서 `@app.exception_handler(ServiceError)` 일괄 HTTP 변환
- `_kis_auth.py` 예외도 `ConfigError`/`ExternalAPIError` 사용

## 환경변수 미설정 동작

| 조건 | 결과 |
|------|------|
| KIS 키 미설정 | `/api/balance`, `/api/order/*` → 503 (서버 시작은 정상) |
| `KIS_ENCRYPTION_KEY` 미설정 | `/api/me/kis` POST/PUT → 503 |
| OPENDART 키 미설정 | `/api/earnings/filings`(KR), `/api/detail/*` → 502 |
| OPENAI_API_KEY 미설정 | `/api/advisory/{code}/analyze` → 503 |
| OpenAI 크레딧 부족(429) | `/api/advisory/{code}/analyze` → 402 |
| AI 일일 한도 초과 | `AiQuotaExceededError` → 429 |
| 해외 공시(`market=US`) | OPENDART 키 불필요 (SEC EDGAR 무료) |

---

## `main.py` — FastAPI 서버 진입점

- CORS: `localhost:5173` 허용 (Vite 개발)
- 20+ 라우터 등록
- **lifespan**: ① `quote_manager.start()` ② 예약주문 스케줄러 ③ `symbol_map` background pre-warm ④ telemetry periodic flush ⑤ APScheduler (파이프라인 + 매크로 cleanup) ⑥ alembic head 비교 부팅 알림 — 종료 시 역순 정리
- **SPA 라우팅**: `/assets` StaticFiles + 캐치올 `@app.api_route("/{path:path}", methods=["GET","HEAD"])` (uptime 모니터/curl -I 호환)
- `index.html` 응답 `Cache-Control: no-cache, no-store, must-revalidate`
- **PageView 미들웨어** (BaseHTTPMiddleware): `asyncio.create_task` 비동기 INSERT. JWT 직접 파싱(`_extract_user_id_from_jwt`)으로 ContextVar propagation 우회
- **보안 헤더는 nginx SSoT** — FastAPI 미들웨어로 추가하지 말 것
- **ServiceError handler**: 응답 본문 `error_id=uuid4().hex[:8]` + `logger.error(f"[{error_id}] ...", exc_info=True)`
- KIS API 직접 호출 금지. 모든 로직은 `routers/` → `services/` → `stock/`/`screener/` 위임

---

## `order.py` — 주문 관리

**계층 분리**: `order_service`만 import. **`order_store` 직접 접근 금지**.

```
POST /api/order/place                주문 발송 (KR/US/FNO, 매수/매도, 지정가/시장가)
GET  /api/order/buyable              매수가능 (FNO: side 필요)
GET  /api/order/open                 미체결 (market=KR|US|FNO)
POST /api/order/{order_no}/modify    정정 (FNO: nmpr_type_cd 등)
POST /api/order/{order_no}/cancel    취소
GET  /api/order/executions           당일 체결
GET  /api/order/history              로컬 DB 주문 이력
POST /api/order/sync                 KIS 대사
POST /api/order/reserve              예약주문 등록
GET  /api/order/reserves             예약주문 목록
DELETE /api/order/reserve/{id}       예약주문 삭제
GET  /api/order/fno-price            선물옵션 현재가
```

- 주문 발송 → 로컬 `orders.db` 자동 기록 (PLACED). 응답 `balance_stale: true`
- 취소/정정 → 로컬 DB 즉시 반영 + `local_synced: true`. 동기화 실패 시 로깅
- KR 거래소: `PlaceOrderBody.exchange: Literal["SOR","KRX","NXT"] = "SOR"`. 통합(UN)은 시세 전용 → 주문값 X. 모의투자(`openapivts`)는 KRX 강제(`ServiceError`)
- 응답에 `exchange` 키 (orders.exchange → KRX/NXT/SOR/SOR-KRX/SOR-NXT, NULL→KRX 폴백)
- 정정/취소는 원주문 거래소 유지 (DB 조회 후 `EXCG_ID_DVSN_CD` 주입, SOR-KRX/SOR-NXT는 KRX/NXT 환원)
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
| `TTTC0012U` / `TTTC0011U` | 국내 매수/매도 (신 TR_ID, EXCG_ID_DVSN_CD 지원) |
| `TTTC0013U` | 국내 정정/취소 (신 TR_ID) |
| `TTTC0084R` | 국내 미체결 (KRX/NXT/SOR 3회 호출 + dedup) |
| `TTTC0081R` | 국내 당일 체결 (`EXCG_ID_DVSN_CD="ALL"` 필수) |
| `TTTC8908R` | 국내 매수가능 |
| `H0UNCNT0` / `H0UNASP0` | 통합(KRX+NXT) 실시간 체결가/호가 WS (09:00~15:30) |
| `H0STCNT0` / `H0STASP0` | KRX 단독 WS (15:30~15:40 마감) |
| `H0NXCNT0` / `H0NXASP0` | NXT 단독 WS (08:00~09:00, 15:40~20:00) |
| `H0UNMKO0` / `H0STMKO0` / `H0NXMKO0` | 장운영정보 — `/ws/market-status` 멀티플렉스 |
| `H0STCNI0` | 체결통보 WS (AES-CBC, `KIS_HTS_ID` 필요) |
| `JTTT1002U` / `JTTT1006U` | 해외 매수/매도 |
| `TTTS3018R` | 해외 미체결 |
| `JTTT3001R` | 해외 당일 체결 |
| `TTTS3007R` | 해외 매수가능 |
| `HHDFS00000300` / `HHDFS76240000` / `HHDFS76950200` | 해외 현재가 / 일봉 / 15분봉 |
| `HHDFS76200100` / `HHDFS76200200` | 해외 호가(10단계) / 현재가 상세 |
| `HDFSASP0` | 해외 호가 WS |
| `TTTO1101U` / `STTN1101U` | 선물옵션 주문 (주간/야간) |
| `TTTO1103U` / `TTTN1103U` | 선물옵션 정정/취소 (주간/야간) |
| `TTTO5201R` | 선물옵션 체결/미체결 |
| `TTTO5105R` | 선물옵션 주문가능 |
| `FHMIF10000000` | 선물옵션 현재가 |

### 실전/모의투자 TR_ID 구분
- 실전: `T***`, `J***` (예: `TTTC8434R`)
- 모의: `V***` (예: `VTTC8434R`)
- `wrapper.py`의 `mock` 파라미터로 제어. `routers/balance.py`는 실전 하드코딩

---

## KIS API 주의사항 (잔고)

- `bass_exrt`(기준환율)는 `CTRP6504R` output2 `frst_bltn_exrt`에만 존재 (`TTTS3012R` 없음)
- 해외 KRW 환산: ① `CTRP6504R` 환율 dict → ② `TTTS3012R` 종목별 계산
- `CTFO6118R` 파라미터: `MGNA_DVSN="01"`, `EXCC_STAT_CD="1"`
- `CTFO6118R` 응답: `cblc_qty`, `sll_buy_dvsn_name`, `ccld_avg_unpr1`, `idx_clpr`, `evlu_pfls_amt`, `evlu_amt`
- 해외/선물 조회 실패 → 해당 목록만 `[]`, 국내는 정상

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
- `fno_enabled`: `KIS_ACNT_PRDT_CD_FNO` 설정 여부 (프론트 FNO 섹션 표시 제어)

> API 파라미터/응답 스키마 상세 → `docs/API_SPEC.md`
