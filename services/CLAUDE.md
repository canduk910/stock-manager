# services/ — 서비스 레이어

`stock/` 패키지의 데이터 소스를 조합해 웹 API용 응답을 조립한다.

## 모듈 목록

| 파일 | 역할 |
|------|------|
| `exceptions.py` | 공용 예외 계층 |
| `watchlist_service.py` | 관심종목 대시보드(ThreadPoolExecutor 병렬) + 종목 상세 (국내=pykrx+DART, 해외=yfinance) |
| `detail_service.py` | 재무 테이블 + PER/PBR 히스토리 + CAGR 종합 리포트. KR: metrics에서 PBR/PER/ROE fallback 보충 |
| `order_service.py` | 주문 오케스트레이션 + 대사 (시장별 실행은 order_kr/us/fno에 위임) |
| `order_kr.py` | 국내주식 KIS API 주문 실행 (발주/조회/정정/취소) |
| `order_us.py` | 해외주식 KIS API 주문 실행 |
| `order_fno.py` | 선물옵션 KIS API 주문 실행 |
| `reservation_service.py` | 예약주문 실행 엔진 (asyncio 20초 폴링) |
| `quote_service.py` | 실시간 시세 공개 API 진입점 (get_manager/get_overseas_manager 싱글턴) |
| `quote_kis.py` | KIS WebSocket 단일 연결 + 심볼별 pub/sub (국내+FNO). KISQuoteManager 클래스. |
| `quote_overseas.py` | 해외주식 시세 (Finnhub WS 또는 yfinance 2초 폴링). OverseasQuoteManager 클래스. |
| `advisory_service.py` | AI자문 **통합 v3**: 10년 재무 수집(ThreadPoolExecutor 7~8 workers) + 리서치 데이터 병렬 수집 + GPT 리포트 생성. **6대 비판적 분석**(재무건전성/밸류에이션/매크로산업/경영진/가치함정/최종매매전략) + 정량 프레임워크(3전략+7점등급). 단일 프롬프트, 단일 스키마(v3). Pydantic v3 검증 + 토큰 잘림 재시도(16000→20000). |
| `macro_regime.py` | **공용 체제 판단 모듈** (신규). REGIME_MATRIX 20셀(버핏×공포탐욕) + REGIME_PARAMS(margin/stock_max/cash_min/single_cap) + VIX>35 오버라이드 + 하이스테리시스 ±5. 3개 서비스(advisory/portfolio_advisor/pipeline) 공유. |
| `safety_grade.py` | **7점 등급/복합점수 공유 모듈** (신규). `compute_grade_7point()`(7지표×4점=28점→A/B+/B/C/D), `compute_composite_score()`(ValueScreener 공식), `compute_regime_alignment()`, `compute_position_sizing()`. advisory_service + pipeline_service 공유. |
| `guru_formulas.py` | **구루 투자 공식 모듈**. 6개 ���식: Greenblatt(`calc_greenblatt`: ROIC+EY), Neff(`calc_neff`: EPS CAGR+배당/PER), 서준식(`calc_seo_expected_return`: ROE/PBR), **Graham NCAV**(`calc_graham_ncav`: 순유동자산/시총), **Fisher PSR**(`calc_fisher_psr`: 시��/매출), **Piotroski F-Score**(`calc_piotroski_fscore`: 8항목 재무건전성). 통합 패널(`calc_guru_panel`: 24점=6공식×4점). Value Trap 경고(`check_value_trap`: 7규칙). 체제별 파라미터(`REGIME_GURU_PARAMS`). |
| `schemas/advisory_report_v2.py` | **Pydantic v2 응답 스키마** (하위호환 유지). `AdvisoryReportV2Schema`. `validate_v2_report()`/`extract_v2_fields()`. 기존 v2 리포트 조회용. |
| `schemas/advisory_report_v3.py` | **Pydantic v3 통합 응답 스키마** (신규). v2 중복 필드 통합: 밸류에이션분석(v2심화+v3밴드), 매크로및산업분석(v2환경+v3사이클), 최종매매전략(v2포지션가이드+v3전략). `validate_v3_report()`/`extract_v3_fields()`. |
| `macro_service.py` | 매크로 분석 오케스트레이션: 지수/뉴스/심리/투자자 + **금리차/신용스프레드/환율/원자재/섹터히트맵/경기국면**(6개 신규). 10개 섹션 독립 실패 허용. GPT 결과 `macro.db` 일일 캐싱 |
| `macro_cycle.py` | **경기 사이클 국면 판단** (신규). 4단계(회복/확장/과열/수축). 5지표 가중합산(수익률곡선30%+신용스프레드20%+VIX20%+섹터로테이션15%+달러15%). macro_regime.py와 독립 |
| `portfolio_advisor_service.py` | AI 포트폴리오 자문: 잔고 컨텍스트(52주 하락률+**개별 AI 리포트 연계**) + 매크로 체제 + **매크로 뉴스 헤드라인** → OpenAI 호출(체제별 프롬프트 + 역발상 + **가중 등급 집계 + 체제 정합성 + 신규 섹터 진입 추천(규칙 29-32)**) → 진단/리밸런싱/매매안/**섹터 추천**. `cache.db` 30분 TTL + `advisory.db` 영구 저장. 52주 고가 6h 캐시. |
| `sector_recommendation_service.py` | **GPT 섹터 추천 서비스** (신규). 매크로 현황(체제/VIX/버핏/공포탐욕/지수/뉴스) 기반 3컨셉(모멘텀/역발상/3개월선점) 탑픽 섹터+종목 추천. `macro_store` 일일 캐싱. `response_format=json_object`, `max_completion_tokens=5000→8000` 재시도. |
| `report_service.py` | 투자 보고서: 추천 이력 + 매크로 체제 이력 + 일일 보고서 + Markdown 생성(**섹터 추천 섹션 포함**) + 성과 통계. `stock/report_store.py` 래퍼 경유. |
| `pipeline_service.py` | 투자 파이프라인: **Step 0 중복방지**(날짜+market 기존 보고서 체크) → 체제 판단 → **Step 1.5 매크로 수집+GPT 섹터 추천** → 스크리닝 → 심층 분석 → 추천 생성 → 보고서 저장(**report_json version 2**: regime_data+macro_snapshot+sector_recommendations). `run_pipeline(market)` 단일 진입점. |
| `scheduler_service.py` | APScheduler: 08:00 KR / 16:00 US BackgroundScheduler. `setup_scheduler()` / `shutdown_scheduler()` / `get_scheduler_status()`. main.py lifespan 통합. |
| `mcp_client.py` | KIS AI Extensions MCP Streamable HTTP 클라이언트. 세션 기반 프로토콜(initialize → session ID → tools/call). SSE 응답 파싱. Host 헤더 고정(Docker 내부 접근). `health_check()`/`call_tool()`. 싱글턴 `get_mcp_client()`. |
| `backtest_service.py` | 백테스트 오케스트레이션: **비동기 2단계**(run_tool→job_id→get_backtest_result_tool(wait=true)). MCP 파라미터: `strategy_id`/`symbols`(배열)/`initial_capital`/`commission_rate`/`tax_rate`/`slippage`. `_extract_metrics()` 중첩 메트릭(basic/risk/trading) 플래트닝. 실패 시 `update_job_status("failed")`. `get_strategy_signals()` — 대표 3전략 신호 + 합의. MCP 비활성화 시 None. |
| `strategy_builder_service.py` | 전략빌더 BuilderState→.kis.yaml 변환(`convert_builder_to_yaml`) + 검증(`validate_builder_state`) + YAML 요약 추출(`extract_strategy_summary`: 지표/조건/리스크 메타데이터). 프론트 5단계 빌더 UI의 JSON을 MCP가 이해하는 YAML로 변환. |
| `tax_service.py` | 해외주식 양도소득세: CTOS4001R+TTTS3035R 병합 동기화(연속조회 `tr_cont:N` 헤더) + 잔고 기반 적응적 소급(2015년까지) + 시간순 FIFO 재생(매도 시점 이전 매수만 소진) + `tax_fifo_lots` 매도→매수 매핑 + 잔고 `avg_price` fallback + 가상 매도 시뮬레이션 + 동기화 후 자동 재계산. `stock/tax_store.py` 래퍼 경유. 도메인 규칙: `docs/TAX_DOMAIN.md`. |

---

## 예외 계층 (중요)

```
ServiceError (기본 400)
├── NotFoundError (404)
├── ConflictError (409)
├── ExternalAPIError (502)
├── ConfigError (503)
└── PaymentRequiredError (402)
```

- `main.py`에서 `@app.exception_handler(ServiceError)`로 일괄 HTTP 변환
- **모든 서비스/라우터에서 `HTTPException` 직접 raise 금지** — ServiceError 계층 사용

---

## 통화 규칙

- 국내: `currency="KRW"`, 금액 단위 **억원**
- 해외: `currency="USD"`, 금액 단위 **M USD** (백만달러)

---

## 서비스별 핵심 패턴

### order_service.py
- **`routers/order.py`의 유일한 의존 대상** — `order_store` 직접 import 금지
- **시장별 분할**: 실제 KIS API 호출은 `order_kr.py`/`order_us.py`/`order_fno.py`에 위임. `order_store`는 `order_service.py`에서만 접근.
- **Write-Ahead 중앙화**: `place_order()` dispatcher가 PENDING→API→PLACED/REJECTED 전체 흐름 관리
- `cancel_order()` → 로컬 DB 즉시 CANCELLED + `local_synced`/`order_status` 응답. 동기화 실패 시 로깅
- `modify_order()` → 로컬 DB 가격/수량 즉시 반영 + `local_synced`. 동기화 실패 시 로깅
- `get_order_history()` / `get_executions()` → **30초 쿨다운** 대사 (`_maybe_reconcile()`). F5 연타 시 KIS API 호출 0회
- `sync_orders()` → 쿨다운 무시, 강제 대사. 사용자 명시적 동기화 요청용
- `_validate_market()`: 디스패치 함수(get_buyable/get_open_orders/get_executions) 진입부 시장 코드 검증
- `_strip_leading_zeros()`: 10자리→8자리 주문번호 변환
- **FNO**: `_is_fno_night_session()`으로 주간/야간 TR_ID 자동 선택. `KIS_ACNT_PRDT_CD_FNO` 미설정 시 `ConfigError` → 503

### quote_service.py (공개 API 진입점)
- `get_manager()` → `KISQuoteManager` 싱글턴, `get_overseas_manager()` → `OverseasQuoteManager` 싱글턴
- **실제 구현은 분할 파일에 위임**:

### quote_kis.py (KISQuoteManager)
- KIS WS 단일 연결 + 심볼별 `asyncio.Queue` pub/sub
  - `_parse_execution()`: H0STCNT0 t[0~5] + t[7]=시가, t[8]=고가, t[9]=저가 파싱 (시세판 당일캔들용)
  - WS 끊김 → REST fallback(`FHKST01010100`) 3초 폴링, 재연결 시 자동 해제
  - 재연결 지수 백오프 (1→30초)
  - Approval key 12시간 TTL: `_get_approval_key()` 자동 재발급
  - REST token 12시간 TTL: `_get_rest_token_sync()` 동일
  - 비개장일: `_push_initial_price()`로 yfinance 직전 종가 push
  - Queue overflow: 100건마다 경고 로그
- **FNO WS**: `subscribe(is_fno=True)` + `_resolve_fno_type(symbol)` (심볼 첫자리 기반)
  - 지수선물(1xxx): H0IFASP0/H0IFCNT0
  - 지수옵션(2xxx): H0IOASP0/H0IOCNT0
  - 주식선물(3xxx): H0ZFASP0/H0ZFCNT0
  - 주식옵션(3xxx): H0ZOASP0/H0ZOCNT0
- **체결통보(H0STCNI0)**: `KIS_HTS_ID` 설정 시 WS로 본인 주문 체결/거부/접수 실시간 수신
  - AES-CBC 복호화 (`pycryptodome`). `_aes_key`/`_aes_iv`는 구독 응답에서 자동 캡처
  - `_parse_notice()`: 22개 필드 파싱 (주문번호, 체결수량, 체결단가, 체결여부 등)
  - `subscribe_notice()`/`unsubscribe_notice()`: 심볼 무관, 계정 단위 pub/sub
  - `_broadcast_notice()`: 모든 notice 구독자에게 전송. `/ws/execution-notice` WS 엔드포인트
  - 미설정 시 폴링만 동작 (에러 없음)

### quote_overseas.py (OverseasQuoteManager)
- Finnhub WS(30 심볼) 또는 yfinance 2초 폴링
  - `fast_info.last_price or previous_close` 패턴 (비개장일 직전 종가)
  - 구독자 0 → on-demand cancel

### reservation_service.py
- `asyncio` 20초 간격 폴링
- 가격 조건(`price_below`/`price_above`) + 시간 조건(`scheduled`) 체크 후 자동 주문 발송
- `_fetch_current_price(symbol, market)`: 국내=`stock.market.fetch_price()`, 해외=`stock.yf_client.fetch_price_yf()` (yfinance 통일)

### advisory_service.py
- **3전략 프레임워크**: 변동성 돌파(K=0.3/0.5/0.7) + 안전마진(Graham Number) + 추세추종(MA+MACD+RSI)
- **System Prompt 도메인 규칙 삽입** (Phase 1): MarginAnalyst 7점 등급표 + MacroSentinel 체제 매트릭스 + OrderAdvisor 등급별 손절폭(A=-8%/B+=-10%/B=-12%) + ValueScreener Value Trap 5규칙
- **User Prompt 추가 섹션** (Phase 2): Forward 추정치 + PER/PBR 5년 통계 + 분기 실적 + 거래량·BB 신호 + 7점 등급 사전 계산값
- **v2 JSON 정량 필드**: `schema_version`/`종목등급`(A~D)/`등급점수`(0-28)/`복합점수`(0-100)/`체제정합성점수`(0-100)/`Value_Trap_경고`/`등급팩터`/`recommendation`(ENTER/HOLD/SKIP)
- **재시도 로직**: `max_completion_tokens=10000`(기본)→12000(재시도). 토큰 잘림/Pydantic 실패/일반 에러 각 1회 재시도. 토큰 2차 실패 시 저장 거부(ExternalAPIError)
- `response_format={"type":"json_object"}`
- Pydantic v2 스키마 검증 (`schemas/advisory_report_v2.py`) + v1 폴백
- fundamental 응답에 `business_description`, `business_keywords`, `forward_estimates`, `valuation_stats`, `quarterly` 필드
- ServiceError 계층 사용 (HTTPException 직접 raise 없음)

### watchlist_service.py
- `resolve_symbol(name_or_code, market)`: 종목명/코드 해석
- `get_stock_detail()`: basic에 roe, dividend_yield, dividend_per_share 포함
- financial rows에 `oi_margin`(영업이익률), `net_margin`(순이익률) 포함

### detail_service.py
- 해외는 yfinance 최대 4년, 밸류에이션 차트 빈 데이터 반환
- `_get_report_kr()`/`_get_report_us()` 모두 `fetch_forward_estimates_yf()` 호출 — 응답에 `forward_estimates` 필드 포함

> 메서드 시그니처 상세 → `docs/SERVICES.md`

---

## 에이전트 역할

하네스의 도메인 에이전트(MacroSentinel/ValueScreener/MarginAnalyst/OrderAdvisor)는 **자문 전용** — API를 직접 호출하지 않는다. 도메인 규칙은 `advisory_service.py`의 System Prompt + `safety_grade.py`/`macro_regime.py` 공용 모듈에 코드화되어 있다.

**3중 일관성 필수**: System Prompt(문자) = safety_grade.py(코드) = Pydantic(타입) 동일 임계값 유지.
