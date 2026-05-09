# services/ — 서비스 레이어

`stock/` 패키지의 데이터 소스를 조합해 웹 API용 응답을 조립한다.

## 모듈 목록

| 파일 | 역할 |
|------|------|
| `exceptions.py` | 공용 예외 계층 |
| `_telemetry.py` | **계측(Telemetry) 모듈** (신규, 2026-05-03 Phase 3). 외부 의존성 0(stdlib only). `@timed(name)` 데코레이터, `record_event(name)` 카운터, `observe(name, value)` percentile(p50/p95/p99 deque 기반), `start_periodic_flush(interval_sec)` 5분 주기 stdout dump 후 reset. 7개 hot path 계측 — watchlist.dashboard / _fetch_dashboard_row / stock_info.get·is_stale / ai_gateway.call_openai / advisory 4 페이즈 / yf_client._ticker hit·miss / analyst_pdf 캐시. 메모리 < 300KB 상한. `TELEMETRY_ENABLED=0/1`, `TELEMETRY_FLUSH_SEC` 환경변수 제어. 1주 누적 측정 후 max_workers/RefreshContext/Single-flight 우선순위 재평가 자료. |
| `_dashboard_cache.py` | **워치리스트 dashboard 응답 캐시** (신규, 2026-05-03 Phase 2 QW-4). 사용자별 60s in-memory TTL (부분 실패 응답은 15s 단축). `(user_id, sorted_codes_hash)` 키. `add_item / remove_item / update_memo` 핸들러에서 invalidate. `threading.Lock`으로 동시성 보호. 멀티 인스턴스 확장 시 Redis로 재설계 필요 — F-4-A 코드 주석 명시. F5 연타 즉시 응답(<50ms), 동시 30 사용자 시 외부 API 호출 1/30. |
| `secure_store.py` | **AES-GCM 암호화 모듈** (신규, 2026-05-04 Phase 4). `encrypt(plaintext: str) -> str(b64)`, `decrypt(b64: str) -> str`. 32-byte 마스터 키(`KIS_ENCRYPTION_KEY` env, SSM SecureString). nonce 12-byte 랜덤 prepend + ciphertext + auth tag 16B. 키 미설정 시 `ConfigError(503)` fail-fast. 사용자 KIS 자격증명 저장에 사용. cryptography>=42 의존. |
| `kis_validator.py` | **KIS 자격증명 검증** (신규, 2026-05-04 Phase 4). `validate_kis(app_key, app_secret, base_url) -> True/Exception`. KIS `/oauth2/tokenP` 호출로 토큰 발급 시도 → 실패 시 `ExternalAPIError("KIS 인증 실패")`. `routers/me_kis.py`의 POST/validate에서 호출. |
| `watchlist_service.py` | 관심종목 대시보드(ThreadPoolExecutor 병렬, **max_workers=4** — 2026-05-02 t3.small OOM 방지로 10→4 축소) + 종목 상세 (국내=pykrx+DART, 해외=yfinance). **(2026-05-03 Phase 2 QW-1/QW-3)**: stock_info N+1 제거(`is_stale_from_dict()` 순수 함수 + `_fetch_dashboard_row` dict 기반 단축, 26종목 SELECT 104→26 -75%) + `partial_failure: list[str]` 메타필드(외부 API 실패 영역 기록, `logger.debug → warning` 승격). 응답 dict에 `partial_failure` 키. |
| `detail_service.py` | 재무 테이블 + PER/PBR 히스토리 + CAGR 종합 리포트. KR: metrics에서 PBR/PER/ROE fallback 보충 |
| `order_service.py` | 주문 오케스트레이션 + 대사 (시장별 실행은 order_kr/us/fno에 위임). **(2026-05-08 KRX+NXT+SOR)** `place_order(..., exchange="SOR")` 시그니처 확장 + KR 거래소 검증(`_VALID_EXCHANGES={SOR,KRX,NXT}`) + 모의투자 차단(`_is_simulation()` → SOR/NXT 시 ServiceError). PENDING insert 시 `exchange` 기록 → PLACED 갱신 시 KIS 응답 `excg_id_dvsn_cd`/`ORD_EXG_GB` 정밀 거래소(SOR-KRX/SOR-NXT)로 덮어쓰기. `modify_order`/`cancel_order` 진입부에서 DB orders.exchange 조회 → `EXCG_ID_DVSN_CD` 주입(원주문 거래소 유지, SOR-KRX/SOR-NXT 는 KRX/NXT 로 환원, 거래소 변경 불가). |
| `order_kr.py` | 국내주식 KIS API 주문 실행 (발주/조회/정정/취소). **(2026-05-08 신 TR_ID 일괄 전환)** `_KR_TR_IDS = {buy:TTTC0012U, sell:TTTC0011U, modify/cancel:TTTC0013U, open:TTTC0084R, executions:TTTC0081R, buyable:TTTC8908R}`. `place_domestic_order(..., *, exchange="SOR")` body 에 `EXCG_ID_DVSN_CD` 주입. `_validate_ord_dvsn(exchange, order_type)` — KRX 00~24 / NXT 00,03,04,11~16,21~24 / SOR 00,01,03,04,11~16. `_normalize_excg_code(item)` — 응답 정규화 헬퍼(KRX/NXT/SOR/SOR-KRX/SOR-NXT, ord_exg_gb 1/2/3/4 매핑). `get_domestic_open_orders` — TTTC0084R 로 KRX/NXT/SOR 3회 호출 + (주문번호, 거래소) dedup. `get_domestic_executions` — TTTC0081R + EXCG_ID_DVSN_CD="ALL" 1회 호출. |
| `order_us.py` | 해외주식 KIS API 주문 실행. **(2026-05-05 핫픽스)** `get_overseas_executions` + `get_overseas_open_orders` NASD 단일 → NASD/NYSE/AMEX 3개 거래소 순회. 체결조회는 KST 어제~오늘 명시(ET 경계 누락 방지). 중복 제거 키 `order_no::exchange`. **(2026-05-08 매수가능 환율/원화)** `get_overseas_buyable` 응답에 `usd_krw_rate`/`deposit_krw`/`buyable_amount_krw` 추가. `_fetch_usd_krw_rate()` 헬퍼 — `stock/macro_fetcher.fetch_currency_quotes` 재사용(USDKRW=X, 15분 캐시) lazy import. 환율 조회 실패 시 USD 필드만 정상 반환(graceful degrade). |
| `order_fno.py` | 선물옵션 KIS API 주문 실행 |
| `reservation_service.py` | 예약주문 실행 엔진 (asyncio 20초 폴링) |
| `quote_service.py` | 실시간 시세 공개 API 진입점 (get_manager/get_overseas_manager 싱글턴) |
| `quote_kis.py` | KIS WebSocket 단일 연결 + 심볼별 pub/sub (국내+FNO). KISQuoteManager 클래스. **(2026-05-08 KRX+NXT+SOR)** `_KR_TR_MATRIX = {UN:{H0UNCNT0,H0UNASP0,10}, KRX:{H0STCNT0,H0STASP0,10}, NXT:{H0NXCNT0,H0NXASP0,10}}`. `_KR_EXECUTION_TR_IDS`/`_KR_ORDERBOOK_TR_IDS`/`_KR_MARKET_STATUS_TR_IDS` set 멤버십으로 메시지 디스패치 추상화. `_resolve_exchange_by_clock(now_kst)` 4구간 분기(08:00~09:00 NXT / 09:00~15:30 UN / 15:30~15:40 KRX / 15:40~20:00 NXT / 그 외 CLOSED→UN 폴백). `subscribe(symbol, queue, *, is_fno=False, exchange="auto")` 시그니처 확장. `_resolve_kr_exchange(symbol)` 명시값(UN/KRX/NXT) 우선, `auto` 시 시계 기반. `subscribe_market_status(queue)` / `_send_subscribe_market_status` / `_broadcast_market_status` 신규 — H0UNMKO0+H0STMKO0+H0NXMKO0 멀티플렉스 broadcast. `_run_ws` 재연결 시 market-status 자동 재구독. NXT/통합 호가도 ASKP1~10/RSQN1~10 동일 구조 → 기존 `_parse_orderbook()`/`_parse_execution()` 재사용. |
| `quote_overseas.py` | 해외주식 시세. OverseasQuoteManager 클래스. **(2026-05-08 phase 1)** 가격 채널: KIS REST `get_kis_price()` 우선 + Finnhub WS / yfinance 2초 폴링 fallback. `_fetch_quote_message`/`_fetch_quote_message_yf` 추출 + `record_event("quote_overseas.fallback_to_yf")`. **(2026-05-08 phase 2 호가 채널 신규)** 호가 채널 통합 — `get_kis_orderbook()` 기반 종목별 REST 폴링 태스크(`_orderbook_pollers` dict + `_orderbook_poll_loop` 2초 주기) + broadcast `{type:"orderbook", symbol, asks, bids, total_ask_volume, total_bid_volume}`(국내 호가와 동일 shape, 프론트 useQuote 자동 호환). **(2026-05-09 phase 3 KIS WS 호가)** `KISOverseasOrderbookWS` 신규 내부 클래스 — KIS WS HDFSASP0 단일 연결 + 다종목 토픽 구독 + 메시지 파싱(`wrapper.parse_overseas_orderbook` 재사용) + 지수 백오프 재연결(1→2→4→8→16→30s 캡, KIS rate limit 안전 마진). WS 메시지 수신 시 해당 종목 REST 폴링 자동 중단(중복 broadcast 방지) / WS 끊김 시 자동 REST 폴링 재시작. KIS WS 키 부재(개발/CI) 환경 graceful → REST 폴링만. 텔레메트리 8종(`quote_overseas.kis_orderbook_ws.{start,stop,connect,disconnect,reconnect_attempt,topic_subscribe,topic_unsubscribe,message}`). |
| `advisory_service.py` | AI자문 **통합 v3**: 10년 재무 수집(ThreadPoolExecutor 7~8 workers) + 리서치 데이터 병렬 수집 + GPT 리포트 생성. **8대 비판적 분석** + 정량 프레임워크(3전략+7점등급). 단일 프롬프트, 단일 스키마(v3). Pydantic v3 검증 + 토큰 잘림 재시도. **(2026-05-02 보수성 완화)**: `_get_cycle_context()` 신규로 macro_cycle 통합 + `_CYCLE_REGIME_RULES` 16셀(체제×사이클) 매트릭스 + `_format_cycle_regime_rule()` + `_build_system_prompt(regime, regime_desc, cycle_ctx)` 시그니처 확장. **defensive "어떤 경우에도 매수 금지" 폐기** → "사이클 회복/확장 시 단계적 매수 허용". `_build_consensus_section` defensive 가드 폐지(50% 감산으로 완화). Graham 임계 cycle 보정(회복/확장 15% / 과열 25% / 수축 10%). 사전계산에 `growth_grade` 병기, JSON에 `성장주_보조판단` 필드. **12번 섹션 증권사 컨센서스**: defensive에서도 노출(50% 감산 경고). **누락데이터 6종 보강**(2026-05-01): 사업개요/사업부문, 52주 가격위치, 자본행위(CB/BW/유증/자사주/M&A), 10년 밸류에이션 사이클, 경쟁사 비교, 배당수익률·주당배당금. KR=중앙 목표가/dispersion/momentum/recent 3건 요약. US=등급 변경 이력. Value Trap 6번째 규칙(consensus_overheated). 사전 계산값(grade/score/진입가/손절가) 불변. **(2026-05-06 보고서 챗봇)** `chat_with_report(code, market, report_id, messages, user_id)` 추가 — stateless 챗봇 진입점. 보고서 본문(`advisory_reports.report` JSON)을 system prompt에 주입(가드: 보고서 외 추정/새 의견 금지) + 슬라이딩 윈도우(최근 20개) + `ai_gateway.call_openai_chat(service_name="advisory_chat", max_completion_tokens=1500)`. user_id/code/market 일치 검증. DB 저장 없음(메시지 히스토리는 클라이언트가 보관). **(2026-05-06 권한 검증 + 비즈니스 모델 통합)** 챗봇 권한 검증을 DB 레벨로 위임 — `advisory_store.get_report_by_id(report_id, user_id=user_id)` 호출로 user_id 비교 라인 제거(`AdvisoryReport.to_dict()`에 user_id 누락 → 항상 NotFoundError 버그 해소). `_collect_fundamental_kr/us` segments 호출 직후 `advisory_fetcher.fetch_business_model(code, name, market, segments_dict, financial_dict, user_id)` 통합 → fundamental dict에 `business_model: {revenue_model, cash_generation, rd_strategy}` Optional 추가(백워드 호환). `_collect_fundamental_us(code, name="", user_id=1)` 시그니처 확장. **(2026-05-07 사용자 코멘트 양면 평가)** `generate_ai_report(..., user_comment: Optional[str] = None)` 시그니처 확장. `_build_system_prompt(..., user_comment=None)` — 코멘트 존재 시 후미에 6개 규칙 가이드 블록 append(악마의 변호인 의무 / strength 1~10 임계값 / overall_stance 5단계 / summary 1~3문장 / 본문 정합성 / JSON `user_commentary_evaluation` 필드 + 형식 명세). `_build_prompt(..., user_comment=None)` user 메시지 후미에 코멘트 원문 echo. 등급/composite_score/action은 코멘트와 무관하게 데이터 기반 유지(stance만 가설 평가용). DB 마이그레이션 0건(JSON 컬럼 자연 저장). |
| `macro_regime.py` | **공용 체제 판단 모듈**. REGIME_MATRIX 20셀(버핏×공포탐욕) + REGIME_PARAMS(margin/stock_max/cash_min/single_cap) + VIX>35 오버라이드 + 하이스테리시스 ±5. **(2026-05-02)** `get_regime_params(regime, cycle_phase)` + `get_margin_requirement(regime, cycle_phase)` 신규 — 16셀 매트릭스로 cycle 의존 동적 single_cap/margin 반환. defensive+회복=single_cap 7%·margin 35%, +확장=5%·40%, +과열=2%·40%, +수축=0%·40%. accumulation/selective/cautious도 cycle 가중. **(2026-05-04 HY OAS 통합)** `determine_regime(sentiment, previous_regime, hy_oas_percentile=None, hy_oas_value=None)` 시그니처 확장(Optional, 후방호환). `_step_fg_level()` 신규. **Phase 1 F&G 보정**(`credit_adjustment`): hy_oas p≥90 → F&G 한 단계 fear / p≤10 → 한 단계 greed. **Phase 2 신용 오버라이드**(`credit_override`): `OAS>10% OR p>95` → `extreme_fear+accumulation` 강제(단 버핏 high/extreme이면 `selective` 완화). `p<5 + 버핏 high/extreme` → `defensive` 강제. VIX>35 우선순위 보존. 기존 `REGIME_PARAMS` dict는 fallback 호환. 4개 서비스(advisory/portfolio_advisor/pipeline/growth_grade) 공유. |
| `safety_grade.py` | **7점 등급/복합점수 공유 모듈**. `compute_grade_7point()`(7지표×4점=28점→A/B+/B/C/D), `compute_composite_score()`, `compute_regime_alignment()`, `compute_position_sizing()`. **(2026-05-02 C 등급 부분 진입 허용)**: `GRADE_FACTOR["C"]=0.0 → 0.25`, `GRADE_STOP_LOSS_PCT["C"]=-15%` 신규, `valid_entry`에 C 포함. D 등급은 0 유지(가치 평가). 7지표 임계값 변경 없음. |
| `growth_grade.py` | **성장주 보조 등급 모듈** (신규, 2026-05-02). `compute_growth_grade(metrics, cycle_ctx)` → G-A/G-B/G-C 등급 + 점수(0-20). 5지표(각 4점): 매출 CAGR / 영업이익 CAGR / FCF 추세 / R&D 비중 / 사이클 주도 섹터 정합성. `combine_grades(value_grade, growth_grade) → (factor, label)` — 가치 D + 성장 G-A → factor=0.30 진입 허용(분할매수, 손절 -20%), 가치 C + 성장 G-A → factor=0.5 등 6종 라벨. `safety_grade.py`(가치)와 분리, MarginAnalyst 도메인 규칙 보존. |
| `guru_formulas.py` | **구루 투자 공식 모듈**. 6개 공식: Greenblatt(`calc_greenblatt`: ROIC+EY), Neff(`calc_neff`: EPS CAGR+배당/PER), 서준식(`calc_seo_expected_return`: ROE/PBR), **Graham NCAV**(`calc_graham_ncav`: 순유동자산/시총), **Fisher PSR**(`calc_fisher_psr`: 시총/매출), **Piotroski F-Score**(`calc_piotroski_fscore`: 8항목 재무건전성). 통합 패널(`calc_guru_panel`: 24점=6공식×4점). Value Trap 경고(`check_value_trap`: 7규칙). 체제별 파라미터(`REGIME_GURU_PARAMS`). |
| `schemas/advisory_report_v2.py` | **Pydantic v2 응답 스키마** (하위호환 유지). `AdvisoryReportV2Schema`. `validate_v2_report()`/`extract_v2_fields()`. 기존 v2 리포트 조회용. |
| `schemas/advisory_report_v3.py` | **Pydantic v3 통합 응답 스키마**. v2 중복 필드 통합: 밸류에이션분석/매크로및산업분석/최종매매전략. `FutureGrowthDrivers`/`ContrarianView` 모델(2026-05-01). `GrowthAuxiliary` 모델(2026-05-02 신규, 성장주_보조판단 필드: growth_grade/growth_score/growth_thesis/cycle_alignment/combined_label, 모두 Optional, backward-compat). **(2026-05-07)** `AgreePoint`/`DisagreePoint` 모델(point: str, evidence: str, strength: int = Field(ge=1, le=10)) + `UserCommentaryEvaluation`(user_comment, overall_stance: Literal[strong_agree/agree/balanced/disagree/strong_disagree], agree_points: list[AgreePoint] max 5, disagree_points: list[DisagreePoint] max 5, summary). `AdvisoryReportV3Schema.user_commentary_evaluation: Optional[UserCommentaryEvaluation] = None` (백워드 호환 — 기존 보고서 누락 시 검증 통과). `validate_v3_report()`/`extract_v3_fields()`. |
| `macro_service.py` | 매크로 분석 오케스트레이션: 지수/뉴스/심리/투자자 + **금리차/신용스프레드/환율/원자재/섹터히트맵/경기국면**(6개 신규). 10개 섹션 독립 실패 허용. GPT 결과 `macro.db` 일일 캐싱. **`get_macro_cycle()` 경기국면+투자체제(determine_regime) 통합 반환**. **(2026-05-04)** `get_credit_spread()` MacroRepository 일일 영속 캐시(`get_macro_today/save_macro_today`). `get_macro_cycle()` credit_spread 입력 자동 주입(`oas_momentum_6m` → cycle / `hy_oas_percentile`+value → regime). **(2026-05-05 R2)** `_events_for_history()` 헬퍼 + `get_yield_curve()` / `get_credit_spread()` 응답에 `events: {recessions, bear_markets}` 임베드(NBER 침체 + S&P -20% 약세장, 캐시 hit 경로 포함). |
| `macro_events.py` | **매크로 음영 이벤트 모듈** (신규, 2026-05-05). `NBER_RECESSIONS` 3건(2001 닷컴 / 2007-2009 GFC / 2020 코로나) + `SP500_BEAR_MARKETS` 4건(2000-2002 / 2007-2009 / 2020.2-3 / 2022.1-10). `get_events_in_range(start, end)` 범위 클립 헬퍼(원본은 `original_start`/`original_end` 보존). 차트 ReferenceArea 음영용 정적 데이터. 출처: NBER Business Cycle Dating + Macrotrends/Yardeni 코드 주석. |
| `macro_cycle.py` | **경기 사이클 국면 판단** (신규). 4단계(회복/확장/과열/수축). 5지표 가중합산(수익률곡선30%+신용스프레드20%+VIX20%+섹터로테이션15%+달러15%). macro_regime.py와 독립. **(2026-05-04 Phase 3)** `_score_credit()`에 `oas_momentum_6m` 가중(+0.3) 입력 추가 — 16셀 cycle×regime 매트릭스 미터치, 입력만 정밀화. |
| `portfolio_advisor_service.py` | AI 포트폴리오 자문: 잔고 컨텍스트(52주 하락률+**개별 AI 리포트 연계**) + 매크로 체제 + **경기사이클 국면** + **매크로 뉴스 헤드라인** → OpenAI 호출(체제별 프롬프트 + **경기국면 주도섹터** + 역발상 + **가중 등급 집계 + 체제 정합성 + 신규 섹터 진입 추천(규칙 29-32)**) → 진단/리밸런싱/매매안/**섹터 추천**. `cache.db` 30분 TTL + `advisory.db` 영구 저장. 52주 고가 6h 캐시. **(2026-05-02 톤 균형화)**: "현금 확보를 위한 매도를 우선 검토" → "조합 권고에 따라 비중 조정", "가중 평균<B면 신규 편입 전면 보류" → "사이클 주도 섹터 + 가치 B 이상 또는 성장 G-A 한정 허용", 손실 -15% 초과 "손절 우선" → "손절/평균단가 분할매수/홀딩 3안 균형 제시". `_format_cycle_context`에 사이클×체제 액션 매트릭스 가이드 1줄 추가. **(2026-05-06 보고서 챗봇)** `chat_with_report(report_id, messages, user_id)` 추가 — `service_name="portfolio_chat"`, 진단/리밸런싱/매매안/시장코멘트 보고서 본문을 system prompt에 주입. require_admin 라우터에서만 노출. **(2026-05-07 사용자 코멘트 양면 평가)** `_compute_cache_key(balance_data, user_comment=None)` SHA256 payload에 코멘트 strip 후 포함 — 동일 잔고+다른 코멘트=다른 보고서, None/""/" "=같은 키. `analyze_portfolio(..., user_comment=None)` + `_build_system_prompt(..., user_comment=None)` 후미 가이드 블록 + `_build_prompt(..., user_comment=None)` user 메시지 echo. JSON 응답 스키마에 `user_commentary_evaluation: null|{...}` 형식 명시. |
| `sector_recommendation_service.py` | **GPT 섹터 추천 서비스** (신규). 매크로 현황(체제/VIX/버핏/공포탐욕/지수/뉴스) 기반 3컨셉(모멘텀/역발상/3개월선점) 탑픽 섹터+종목 추천. `macro_store` 일일 캐싱. `response_format=json_object`, `max_completion_tokens=5000→8000` 재시도. |
| `report_service.py` | 투자 보고서: 추천 이력 + 매크로 체제 이력 + 일일 보고서 + Markdown 생성(**섹터 추천 섹션 포함**) + 성과 통계. `stock/report_store.py` 래퍼 경유. |
| `pipeline_service.py` | 투자 파이프라인: **Step 0 중복방지**(날짜+market 기존 보고서 체크) → 체제 판단 → **Step 1.5 매크로 수집+GPT 섹터 추천** → 스크리닝 → 심층 분석 → 추천 생성 → 보고서 저장(**report_json version 2**: regime_data+macro_snapshot+sector_recommendations). `run_pipeline(market)` 단일 진입점. |
| `scheduler_service.py` | APScheduler: 08:00 KR / 16:00 US 파이프라인 + **(2026-05-09)** 00:05 매크로 GPT 캐시 cleanup BackgroundScheduler. `setup_scheduler()` / `shutdown_scheduler()` / `get_scheduler_status()`. main.py lifespan 통합. **`_run_macro_cleanup_job()`** 신규 — `macro_store.delete_before_today()` 호출, 자정 KST 기준 어제 이전 매크로 GPT 캐시 일괄 삭제(매크로 정보는 당일치만 유지 정책). cache.db `macro:*` TTL 캐시는 미터치(장기 시계열 보호). |
| `mcp_client.py` | KIS AI Extensions MCP Streamable HTTP 클라이언트. 세션 기반 프로토콜(initialize → session ID → tools/call). SSE 응답 파싱. Host 헤더 고정(Docker 내부 접근). `health_check()`/`call_tool()`. 싱글턴 `get_mcp_client()`. |
| `backtest_service.py` | 백테스트 오케스트레이션: **비동기 2단계**(run_tool→job_id→get_backtest_result_tool(wait=true)). MCP 파라미터: `strategy_id`/`symbols`(배열)/`initial_capital`/`commission_rate`/`tax_rate`/`slippage`. `_extract_metrics()` 중첩 메트릭(basic/risk/trading) 플래트닝. 실패 시 `update_job_status("failed")`. `get_strategy_signals()` — 대표 3전략 신호 + 합의. MCP 비활성화 시 None. **(2026-05-07 로컬 백테스트 진입점)** `run_local_backtest(preset, symbols, market, start_date, end_date, initial_capital, commission_rate, tax_rate, slippage, params, user_id)` + `list_local_presets()` 추가 — `services/local_backtest/` 자체 Python 일봉 엔진 호출, MCP 미경유, 동기 응답. KR market만 허용(MVP), `symbols` 1~10 검증, `BacktestJob.strategy_type="local"` + `symbols[0]` 자동 저장 + 신규 `symbols` JSON 컬럼에 전체 리스트 저장. 기존 MCP 함수(`run_preset_backtest`/`run_custom_backtest`/`run_batch_backtest`/`get_strategy_signals`) 100% 미터치. **(2026-05-09 백테스트 500 픽스 + 메시지 분류기)** `_classify_local_failure(exc)` — 로컬 실패 원인 분류(`db_error`/`serialize`/`timeout`/`data_load`/`unknown`)로 telemetry suffix 매핑. `_classify_backtester_error(error_msg)` — MCP 응답 error 분류(`vps_key_missing` / `data_prep` / None). `'vps'` 패턴 우선순위 > `데이터 준비 실패` 패턴: `vps_key_missing` 시 "백테스트 인증 설정 오류: backtester 서버의 ~/KIS/config/kis_devlp.yaml 에 KIS 모의투자(`vps:`) 섹션이 누락…" 가이드. `data_prep` 시 "백테스트 데이터 조회 실패: 종목 코드/날짜 범위" 가이드. 그 외는 기존 메시지. `run_local_backtest` save_backtest_job 호출에 `try/except (Exception)` + ServiceError 변환 + `_classify_local_failure` telemetry 추가. `_to_jsonable` 적용 직전 응답 직렬화 안전화. 진단(2026-05-09): backtester EC2 yaml에 `vts:` 키로 잘못 작성되어 `KeyError: 'vps'` 발생 → SSM `sed 's/^vts:/vps:/'`로 즉시 복구 + 메시지 분류기로 차후 재발 시 가이드 자동 노출. |
| `local_backtest/` | **자체 일봉 백테스트 엔진** (신규, 2026-05-07; 2026-05-09 안정화). KR yfinance 일봉 기반 포트폴리오(최대 10종목) 균등 배분 시뮬레이터. 외부 backtester(MCP/Lean) 미의존. 4개 KR 단기/추세 전략 프리셋 내장 — `momentum`(상한가 모멘텀: 전일종가+29%↑·익일 시가 매도·-7.5% 손절), `volatility_breakout`(VB: 시가+전일Range×K20 돌파·당일 종가 청산·-3% 손절. **K20=직전 20일 평균 노이즈비율(`1-|Close-Open|/(High-Low)`)** — 횡보장 K≈1 진입 장벽↑·추세장 K≈0 빠른 추격, Range=0 도지는 평균에서 제외), `donchian_swing`(20일 신고가+60EMA 우상향+거래대금 1.5배+갭<3% 매수·20일 저가 이탈 매도·-7% 손절), `long_tail_volatility`(VB 매수+전일대비 +3% 추가필터·당일 종가 매도, 단 +29% spike 시 익일 시가 매도·당일 -3%/익일 -5% 손절). 구성: `engine.py`(일봉 시뮬레이션 루프) + `portfolio.py`(균등 배분 자본 관리, `min(10, len(symbols))` 슬롯, 가득 차면 신규 신호 스킵) + `metrics.py`(8개 메트릭) + `data_loader.py`(yfinance KR 캐시) + `presets.py`(4개 프리셋 메타) + `strategies/_base.py`(`Strategy` ABC + `EntrySignal`/`ExitSignal`/`Position` 데이터클래스) + 4개 전략 모듈. 거래비용: commission_rate(매수+매도)·tax_rate(매도시)·slippage(양방향 단가 보정). 결과: `result_json={equity_curve, trades, per_symbol_contribution, metrics, failures}`. **(2026-05-09 백테스트 500 픽스)** `data_loader.py`: yfinance None 응답 영구 캐시 회피(조기 return + 1회 재시도 5s 대기 + TTL 10분). `engine.py`: 모든 종목 DataFrame index `normalize().tz_localize(None)` 통일로 timezone/precision 미스매치 해소 + `_idx_for()` None 시 `logger.debug` silent skip 가시화 + 결과 빌드 `_to_jsonable(obj)` 재귀 헬퍼(numpy float64/int64 → Python native, pd.Timestamp → ISO 문자열). |
| `strategy_builder_service.py` | 전략빌더 BuilderState→.kis.yaml 변환(`convert_builder_to_yaml`) + 검증(`validate_builder_state`) + YAML 요약 추출(`extract_strategy_summary`: 지표/조건/리스크 메타데이터). 프론트 5단계 빌더 UI의 JSON을 MCP가 이해하는 YAML로 변환. |
| `tax_service.py` | 해외주식 양도소득세: CTOS4001R+TTTS3035R 병합 동기화(연속조회 `tr_cont:N` 헤더) + 잔고 기반 적응적 소급(2015년까지) + 시간순 FIFO 재생(매도 시점 이전 매수만 소진) + `tax_fifo_lots` 매도→매수 매핑 + 잔고 `avg_price` fallback + 가상 매도 시뮬레이션 + 동기화 후 자동 재계산. `stock/tax_store.py` 래퍼 경유. 도메인 규칙: `docs/TAX_DOMAIN.md`. |
| `ai_gateway.py` | **모든 OpenAI API 호출의 단일 진입점** (신규). `call_openai_chat()` — 유저별 일일 쿼터 체크 + OpenAI 호출 + 사용량 기록. `user_id=None`이면 시스템 호출(한도 검사 건너뜀). `check_quota=False`로 재시도 시 중복 검사 방지. `AiQuotaExceededError`(429) 예외. **(2026-05-03 Phase 3)**: `@timed("ai_gateway.call_openai_chat")` + per-model token counter(`ai_gateway.model.{m}.tokens.prompt/completion`) 계측 추가. |

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
