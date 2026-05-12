# services/ — 서비스 레이어

`stock/` 패키지의 데이터 소스를 조합해 웹 API용 응답을 조립한다. 모든 OpenAI 호출은 `ai_gateway.py`를 통과해야 한다(쿼터/사용량). HTTPException 직접 raise 금지 — `services/exceptions.py`의 `ServiceError` 계층 사용.

> 변경 이력은 `docs/CHANGELOG.md`가 단일 출처. 본 문서는 모듈 책임과 영구 규칙만 기술.

## 모듈 목록

| 파일 | 역할 |
|------|------|
| `exceptions.py` | 공용 예외 계층 (ServiceError → NotFound/Conflict/ExternalAPI/Config/PaymentRequired/AiQuotaExceeded) |
| `ai_gateway.py` | 모든 OpenAI 호출 단일 진입점. `call_openai_chat()`, 유저별 일일 쿼터 + 사용량 기록. `user_id=None`은 시스템 호출(쿼터 미차감). `AiQuotaExceededError(429)`. |
| `_telemetry.py` | 계측 (stdlib only). `@timed` / `record_event` / `observe(p50/p95/p99)` / `start_periodic_flush`. `TELEMETRY_ENABLED`/`TELEMETRY_FLUSH_SEC` 제어. 메모리 < 300KB 상한. |
| `_dashboard_cache.py` | 워치리스트 dashboard 사용자별 60s in-memory TTL (부분 실패 15s). `(user_id, sorted_codes_hash)` 키. add/remove/update 핸들러에서 invalidate. 멀티 인스턴스 시 Redis로 재설계 필요. |
| `secure_store.py` | AES-GCM 암호화 (`KIS_ENCRYPTION_KEY` 32-byte b64). nonce 12B + ciphertext + tag 16B. 키 미설정 시 `ConfigError(503)`. 사용자 KIS 자격증명 저장. cryptography>=42. |
| `kis_validator.py` | KIS 자격증명 검증. `/oauth2/tokenP` 호출로 토큰 발급 시도. 실패 시 `ExternalAPIError`. |
| `auth_deps.py` | FastAPI Depends — `get_current_user`, `require_admin`, `require_kis` (사용자 KIS 자격증명 필수). |
| `watchlist_service.py` | 관심종목 대시보드(ThreadPool max_workers=4, t3.small OOM 방지) + 종목 상세 (KR=pykrx+DART, US=yfinance). `is_stale_from_dict()` 순수 함수로 stock_info N+1 제거. 응답에 `partial_failure: list[str]`. `_norm_sector(raw, code, market, industry=None)` idempotent wrapper로 응답 직전 sector 한글 14/11 보장 (구버전 영문 GICS 캐시도 변환). stock_info hit 분기에서도 sector 채움(누락 버그 fix). |
| `detail_service.py` | 재무 테이블 + PER/PBR 히스토리 + CAGR 종합 리포트. KR metrics에서 PBR/PER/ROE fallback 보충. |
| `supply_demand_service.py` | 투자자별 수급정보(개인/외국인/기관 11종). 시장(코스피/코스닥) `fetch_market_supply_demand(market, days)` + 종목 `fetch_stock_supply_demand(code, days)`. wrapper KIS TR(FHPTJ04040000/FHPTJ04160001) 위임 → 단위 변환(백만원→억원, ÷100) + 누적합 + 색상 표준(개인 #EF4444/외국인 #3B82F6/기관 #10B981) + advisory_note 안전 고지. `macro_store` 일자 영속 캐시 + **zero-row 가드**(`_is_all_zero_net`/`_fetch_or_cache`) — 전 행 net_amt=0 응답은 캐시 저장 거부 + ExternalAPIError 표면화, 영속 결함 데이터는 자동 폐기 후 1회 재호출(무한 루프 없음). 매매 액션 키 금지(`recommendation`/`action`/`buy_signal` 부재 — OrderAdvisor 안전 정책). |
| `order_service.py` | 주문 오케스트레이션 + 대사 (실행은 order_kr/us/fno에 위임). `place_order(..., exchange="SOR")` KR 거래소 검증(`_VALID_EXCHANGES={SOR,KRX,NXT}`) + 모의투자 차단. PENDING insert 시 `exchange` 기록 → PLACED 갱신 시 KIS 응답으로 정밀 거래소(SOR-KRX/SOR-NXT) 덮어쓰기. modify/cancel은 DB orders.exchange 조회 후 `EXCG_ID_DVSN_CD` 주입(거래소 변경 불가). |
| `order_kr.py` | 국내주식 KIS API 주문. 신 TR_ID `_KR_TR_IDS = {buy:TTTC0012U, sell:TTTC0011U, modify/cancel:TTTC0013U, open:TTTC0084R, executions:TTTC0081R, buyable:TTTC8908R}`. `_validate_ord_dvsn(exchange, order_type)` / `_normalize_excg_code()`. open orders 는 KRX/NXT/SOR 3회 호출 + (주문번호, 거래소) dedup. executions 는 `EXCG_ID_DVSN_CD="ALL"` 1회. |
| `order_us.py` | 해외주식 KIS API 주문. open/executions 는 NASD/NYSE/AMEX 3개 거래소 순회, KST 어제~오늘 명시(ET 경계 누락 방지). dedup 키 `order_no::exchange`. `get_overseas_buyable` 응답에 `usd_krw_rate`/`deposit_krw`/`buyable_amount_krw` 추가 (`_fetch_usd_krw_rate` lazy import). |
| `order_fno.py` | 선물옵션 KIS API 주문. `KIS_ACNT_PRDT_CD_FNO` 미설정 시 `ConfigError(503)`. 주간/야간 TR_ID 자동 분기. |
| `reservation_service.py` | 예약주문 실행 엔진 (asyncio 20초 폴링). 가격/시간 조건 충족 시 자동 발송. |
| `quote_service.py` | 실시간 시세 공개 진입점. `get_manager()` / `get_overseas_manager()` 싱글턴. |
| `quote_kis.py` | KIS WS 단일 연결 + 심볼별 pub/sub. `_KR_TR_MATRIX={UN:H0UN*, KRX:H0ST*, NXT:H0NX*}` (체결+호가 각 10단계). `_resolve_exchange_by_clock(now_kst)` 4구간(08~09 NXT / 09~15:30 UN / 15:30~15:40 KRX / 15:40~20 NXT). `subscribe(symbol, queue, *, is_fno, exchange="auto")`. FNO WS는 심볼 첫자리 기반 (1xxx/2xxx/3xxx) → IFASP/IOASP/ZFASP/ZOASP. 체결통보 H0STCNI0 + AES-CBC 복호화 (`pycryptodome`, `KIS_HTS_ID` 필요). **2026-05-12: 장운영정보(H0UN/ST/NXMKO0) 구독·broadcast·관련 헬퍼 6개 제거 — slot 3건 회수 (자동매매 동시구독 41건 충돌 해소)** |
| `quote_overseas.py` | 해외 시세. 가격: KIS REST `get_kis_price()` 우선 + Finnhub WS / yfinance 2초 폴링 fallback. 호가: KIS WS `KISOverseasOrderbookWS`(HDFSASP0, 지수 백오프 1→30s) 우선 + KIS REST `get_kis_orderbook()` 2초 폴링 fallback. broadcast `{type:"orderbook", asks, bids, total_*_volume}` (국내 동일 shape). KIS 키 부재 시 graceful → REST 폴링만. |
| `advisory_service.py` | AI자문 통합 v3 (10년 재무 + 리서치 6카테고리 + GPT 1프롬프트 1보고서). 8대 비판적 분석 + 정량 프레임워크(3전략+7점등급). `_get_cycle_context()` macro_cycle 통합 + `_CYCLE_REGIME_RULES` 16셀 매트릭스. defensive에서도 cycle 회복/확장 시 단계적 매수 허용. Graham 임계 cycle 보정(15%/25%/10%). `business_model` fundamental 통합. `chat_with_report(code, market, report_id, messages, user_id)` stateless 챗봇 (DB 레벨 user_id 검증). `generate_ai_report(..., user_comment)` 양면 평가(`UserCommentaryEvaluation`). |
| `macro_regime.py` | 공용 체제 판단. REGIME_MATRIX 20셀(버핏×F&G) + `get_regime_params(regime, cycle_phase)` 16셀 cycle 매트릭스 동적 single_cap/margin + VIX>35 오버라이드 + 하이스테리시스 ±5. `determine_regime(sentiment, prev, hy_oas_percentile, hy_oas_value)` 신용 보정 — Phase 1 F&G ±1 step (p≥90/≤10) / Phase 2 신용 오버라이드 (OAS>10% OR p>95 → extreme_fear+accumulation). 4개 서비스 공유. |
| `safety_grade.py` | 7점 등급/복합점수/체제정합성/포지션사이징 공유 모듈. 7지표×4점=28점 → A/B+/B/C/D. C 등급 부분 진입 허용(factor 0.25, 손절 -15%). D=0 (가치 평가). |
| `growth_grade.py` | 성장주 보조 등급 (G-A/G-B/G-C). 5지표 (매출/영업이익 CAGR / FCF / R&D / 사이클 정합성). `combine_grades(value, growth)` → factor + 라벨 (가치D+성장G-A → factor 0.30 우회 진입). `_LEADER_SECTOR_MAP`에 KR 14 한글 라벨(`반도체`/`2차전지`/`IT/인터넷`/`자동차`/`바이오/헬스케어`/`은행/금융`/`철강/소재`/`에너지/화학` 등) 추가 — sector_normalize 일관화 후 leader 매칭 누락 차단 (기존 키 보존, 추가만). |
| `guru_formulas.py` | 6 공식: Greenblatt, Neff, 서준식, Graham NCAV, Fisher PSR, Piotroski F-Score. 통합 패널(24점=6×4). Value Trap 7규칙. `REGIME_GURU_PARAMS`. |
| `schemas/advisory_report_v2.py` | Pydantic v2 응답 스키마 (하위호환). `validate_v2_report()`. |
| `schemas/advisory_report_v3.py` | Pydantic v3 통합 스키마. `FutureGrowthDrivers` / `ContrarianView` / `GrowthAuxiliary` / `AgreePoint` / `DisagreePoint` / `UserCommentaryEvaluation`. 모두 Optional (백워드 호환). |
| `macro_service.py` | 매크로 분석 오케스트레이션 (10개 섹션 독립 실패 허용). GPT 결과 일일 캐싱. `get_credit_spread()` MacroRepository 일일 영속 캐시. `get_macro_cycle()` credit_spread 입력 자동 주입(oas_momentum_6m → cycle / hy_oas_percentile+value → regime). `get_sector_heatmap()` 응답 `sectors_us`(11) + `sectors_kr`(14) 동시 반환(KRX는 KODEX/TIGER 14종 별도 분류, GICS와 1:1 매핑 X). `sectors` 키는 백워드 호환을 위해 US 데이터 유지. `_events_for_history()` 헬퍼로 yield_curve / credit_spread 응답에 NBER 침체 + S&P 약세장 events 임베드. |
| `macro_events.py` | 매크로 음영 이벤트. NBER 침체 + S&P -20% 약세장 정적 데이터 (1962~). `get_events_in_range(start, end)` 범위 클립. 차트 ReferenceArea 음영용. |
| `macro_cycle.py` | 경기 사이클 4단계 (회복/확장/과열/수축). 5지표 가중합산 (수익률곡선30+신용20+VIX20+섹터15+달러15). `_score_credit()`에 oas_momentum_6m 가중. macro_regime과 독립. |
| `portfolio_advisor_service.py` | AI 포트폴리오 자문. 잔고+개별 AI 리포트 연계 + 매크로 체제 + 경기사이클 + 뉴스 헤드라인 → GPT (체제별 프롬프트 + 가중 등급 집계 + 신규 섹터 진입 추천). 진단/리밸런싱/매매안/섹터 추천. `cache.db` 30분 TTL + `advisory.db` 영구. 톤 균형화(매도 우선 → 조합 권고). `chat_with_report(report_id, messages, user_id)` `service_name="portfolio_chat"`, require_admin. `_compute_cache_key(balance, user_comment)` SHA256 — 동일 잔고+다른 코멘트=다른 보고서. |
| `sector_recommendation_service.py` | GPT 섹터 추천 (3컨셉: 모멘텀/역발상/3개월선점). `macro_store` 일일 캐싱. `response_format=json_object`. |
| `report_service.py` | 투자 보고서 (추천 이력 + 체제 이력 + 일일 보고서 + Markdown 생성 + 성과 통계). |
| `pipeline_service.py` | 투자 파이프라인. Step 0 중복방지 → 체제 판단 → 매크로+섹터 추천 → 스크리닝 → 심층 분석 → 추천 생성 → 보고서 저장 (report_json v2). `run_pipeline(market)` 단일 진입점. |
| `scheduler_service.py` | APScheduler. 08:00 KR / 16:00 US 파이프라인 + 00:05 매크로 GPT 캐시 cleanup BackgroundScheduler. main.py lifespan 통합. `_run_macro_cleanup_job()` → `macro_store.delete_before_today()` (cache.db `macro:*` 미터치). |
| `mcp_client.py` | KIS AI Extensions MCP Streamable HTTP 클라이언트. 세션 기반(initialize → session ID → tools/call). SSE 응답. `health_check()` / `call_tool()`. 싱글턴. |
| `backtest_service.py` | 백테스트 오케스트레이션. **fire-and-poll**: `_submit_mcp_job()` 즉시 반환 + `_fetch_mcp_result_nowait()` lazy 폴링 + `poll_backtest_job()` (504 회복 + 결과 보존). `_classify_backtester_error()` MCP 응답 분류 (vps_key_missing / data_prep) → 친화 메시지. `_classify_local_failure()` telemetry suffix. `run_local_backtest()` / `list_local_presets()` 로컬 엔진 진입점. `get_strategy_signals()` 대표 3전략 합의. |
| `local_backtest/` | 자체 일봉 백테스트 엔진. KR yfinance 일봉 기반 포트폴리오(최대 10종목) 균등 배분. 외부 backtester(MCP/Lean) 미의존. 4 KR 단기/추세 프리셋: `momentum`(상한가) / `volatility_breakout`(VB, K20=20일 평균 노이즈비율) / `donchian_swing`(20일 신고가) / `long_tail_volatility`. 구성: `engine.py` + `portfolio.py`(min(10, len(symbols)) 슬롯) + `metrics.py`(8개) + `data_loader.py`(yfinance KR 캐시 TTL 10분, None 영구 캐시 회피) + `presets.py` + `strategies/`. `_to_jsonable()` 재귀 직렬화 (numpy/pd.Timestamp). 결과: `{equity_curve, trades, per_symbol_contribution, metrics, failures}`. |
| `strategy_builder_service.py` | 전략빌더 BuilderState→.kis.yaml 변환 + 검증 + 요약 추출. 프론트 5단계 빌더 UI의 JSON을 MCP YAML로 변환. |
| `tax_service.py` | 해외주식 양도소득세. CTOS4001R+TTTS3035R 병합 동기화 (연속조회 `tr_cont:N`) + 잔고 기반 적응적 소급(2015~) + 시간순 FIFO 재생 + `tax_fifo_lots` 매도→매수 매핑 + 가상 매도 시뮬레이션. 도메인 규칙: `docs/TAX_DOMAIN.md`. |

---

## 통화 규칙

- 국내: `currency="KRW"`, 금액 단위 **억원**
- 해외: `currency="USD"`, 금액 단위 **M USD** (백만달러)

---

## 서비스별 핵심 패턴

### order_service.py
- **`routers/order.py`의 유일한 의존 대상** — `order_store` 직접 import 금지
- 시장별 분할: 실제 KIS API는 `order_kr/us/fno`에 위임. `order_store`는 service에서만.
- **Write-Ahead 중앙화**: `place_order()` dispatcher가 PENDING→API→PLACED/REJECTED 전체 흐름 관리
- `cancel_order()` / `modify_order()` → 로컬 DB 즉시 반영 + `local_synced`. 동기화 실패 시 로깅
- `get_order_history()` / `get_executions()` → **30초 쿨다운** 대사 (`_maybe_reconcile()`). `sync_orders()`는 쿨다운 무시 강제 대사
- `_strip_leading_zeros()`: 10자리→8자리 주문번호 변환

### quote_kis.py (KISQuoteManager)
- 단일 KIS WS 연결 + 심볼별 `asyncio.Queue` pub/sub
- WS 끊김 → REST fallback(`FHKST01010100`) 3초 폴링, 재연결 시 자동 해제
- 재연결 지수 백오프 (1→30s)
- Approval key + REST token 12시간 TTL 자동 재발급
- 비개장일: `_push_initial_price()`로 yfinance 직전 종가 push
- Queue overflow: 100건마다 경고

### quote_overseas.py (OverseasQuoteManager)
- 가격: KIS REST 우선 / Finnhub WS / yfinance 2초 폴링 fallback. 비개장일 `last_price or previous_close`
- 호가: KIS WS HDFSASP0 우선 / KIS REST 2초 폴링 fallback. WS 메시지 수신 시 해당 종목 REST 폴링 자동 중단/끊김 시 재시작
- 구독자 0 → on-demand cancel
- 텔레메트리: `quote_overseas.{fallback_to_yf, kis_orderbook_ws.*}`

### reservation_service.py
- `asyncio` 20초 폴링. 가격(`price_below`/`price_above`) + 시간(`scheduled`) 조건 충족 시 자동 발송
- `_fetch_current_price(symbol, market)`: KR=`stock.market.fetch_price()`, US=`stock.yf_client.fetch_price_yf()`

### advisory_service.py
- 3전략 프레임워크: 변동성 돌파(K=0.3/0.5/0.7) + 안전마진(Graham) + 추세추종(MA+MACD+RSI)
- System Prompt 도메인 규칙 삽입: MarginAnalyst 7점 등급 + MacroSentinel 체제 매트릭스 + OrderAdvisor 손절폭(A=-8%/B+=-10%/B=-12%) + ValueScreener Value Trap 6규칙
- v3 JSON 정량 필드: `종목등급`(A~D)/`등급점수`(0-28)/`복합점수`(0-100)/`체제정합성점수`/`Value_Trap_경고`/`등급팩터`/`recommendation`(ENTER/HOLD/SKIP)
- 재시도: `max_completion_tokens=10000`→12000. 토큰 잘림/Pydantic 실패/일반 에러 각 1회. 토큰 2차 실패 시 저장 거부
- `response_format={"type":"json_object"}`. Pydantic v3 검증 + v2 폴백.

### watchlist_service.py
- `resolve_symbol(name_or_code, market)` 종목명/코드 해석
- `get_stock_detail()` basic에 roe, dividend_yield, dividend_per_share 포함
- financial rows에 `oi_margin`(영업이익률), `net_margin`(순이익률) 포함

### detail_service.py
- 해외 yfinance 최대 4년, 밸류에이션 차트 빈 데이터 반환
- `_get_report_kr()`/`_get_report_us()` 모두 `fetch_forward_estimates_yf()` 호출

> 메서드 시그니처 상세 → `docs/SERVICES.md`

---

## 에이전트 역할

도메인 에이전트(MacroSentinel/ValueScreener/MarginAnalyst/OrderAdvisor)는 **자문 전용** — API를 직접 호출하지 않는다. 도메인 규칙은 `advisory_service.py`의 System Prompt + `safety_grade.py`/`macro_regime.py` 공용 모듈에 코드화되어 있다.

**3중 일관성 필수**: System Prompt(문자) = safety_grade.py(코드) = Pydantic(타입) 동일 임계값 유지.
