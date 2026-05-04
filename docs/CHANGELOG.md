# 변경 이력

## 2026-05-04 — HY OAS 하워드 막스 시계추 전면 개편 (P0~P3)

### 배경
사용자 신고: "매크로 하이일드 스프레드가 제대로 동작하지 않는다." MacroSentinel 도메인 자문 결과:
- 임계값 3.5%/7%는 막스 원전 비정합 (3.5%는 역사적 5%ile에 해당해 거의 도달 불가)
- 5년 baseline은 코로나 이후 저금리 구간만 잡혀 분포 왜곡
- macro_regime에 신용 사이클 입력 누락 (주식 선행 지표인데 매트릭스에서 빠짐)
- 캐시 1시간은 FRED 일일 갱신 대비 과도

사용자 결정: P0~P3 풀스택 + 전 기간(1996-12 ~ 현재) baseline.

plan: `/Users/kimdukki/.claude/plans/shiny-herding-catmull.md`

### 백엔드 수정 (4)
- `stock/macro_fetcher.py` — `_fetch_fred_oas()` 5년 → **전 기간(1996-12-31~)** baseline. `_compute_oas_stats()` / `_classify_oas_sentiment()` / `_percentile_from_sorted()` 신규. 응답에 `oas_stats{p10,p25,p50,p75,p90,p95,max,max_date,mean,median,std}` / `oas_percentile` / `oas_zscore` / `oas_history_5y` 추가. **5단계 sentiment** (`extreme_greed/greed/normal/fear/extreme_fear`) — 백분위 + OAS>10% 절대 안전장치. `_fetch_fred_ig_oas()` 신규 (FRED `BAMLC0A0CM` Investment Grade OAS). `fetch_credit_spread()` 응답에 `ig_current` / `ig_history_5y` / `hy_ig_spread` / `hy_ig_spread_history_5y` / `partial_failure` 추가. 캐시 1h → **24h**. 후방호환 alias: `oas_history`(=5y), `percentile`(=oas_percentile).
- `services/macro_service.py` — `get_credit_spread()` MacroRepository 일일 영속 캐시(`get_macro_today/save_macro_today`). `get_macro_cycle()` credit_spread 입력 자동 주입(`oas_momentum_6m` → cycle / `hy_oas_percentile`+value → regime).
- `services/macro_regime.py` — `_step_fg_level()` 신규. `determine_regime(sentiment, previous_regime, hy_oas_percentile=None, hy_oas_value=None)` 시그니처 확장(Optional, 후방호환). **Phase 1 F&G 보정** (`credit_adjustment`): hy_oas p≥90 → F&G 한 단계 fear / p≤10 → 한 단계 greed. **Phase 2 신용 오버라이드** (`credit_override`): `OAS>10% OR p>95` → `extreme_fear+accumulation` 강제 (단 버핏 high/extreme이면 `selective` 완화). `p<5 + 버핏 high/extreme` → `defensive` 강제. VIX>35 우선순위 보존.
- `services/macro_cycle.py` — **Phase 3** `_score_credit()`에 `oas_momentum_6m` 가중(+0.3) 입력 추가. 16셀 cycle×regime 매트릭스 미터치(입력만 정밀화).

### 프론트엔드 수정 (1)
- `frontend/src/components/macro/CreditSpreadSection.jsx` — `SENTIMENT_CONFIG` 5단계 확장(extreme_greed/greed/normal/fear/extreme_fear). 메인 게이지 0~12% 선형 → **백분위 축(0~100)** + 절댓값 부제(역사 평균/p95/정점·날짜) 병기. ReferenceLine을 백분위 임계(p10/p25/p75/p90)에 매핑된 **동적 OAS 값**으로 표시. **IG OAS / HY-IG 스프레드 보조 카드** 추가(>5%p이면 "정크 영역 패닉" 강조). `data.credit_spread || data` 모호 fallback 제거 → `data?.credit_spread` 명시. `partial_failure` 안내 배너.

### 신규 테스트 (5)
- `tests/unit/test_macro_fetcher_oas.py` — 11 케이스 (5단계 경계, OAS>10% 안전장치, stats 정확성, 빈 응답/ZeroDivision 가드)
- `tests/unit/test_macro_regime_credit_integration.py` — 7 케이스 (F&G 보정, 신용 오버라이드 4종, dual extreme selective)
- `tests/unit/test_safety_grade_credit_propagation.py` — 1 케이스 (16셀 cycle 매트릭스 자동 정합)
- `tests/unit/test_macro_cycle_oas_momentum.py` — 6 케이스 (oas_momentum_6m cycle 입력 반영)
- `tests/integration/test_credit_spread_api.py` — 3 케이스 (응답 shape + 일일 캐시 동작)
- 결과: **495 PASS / 0 FAIL / 6 skip** (기존 478 → +17 신규).

### 도메인 자문 합의
- **MacroSentinel**: ✅ 백분위 5단계 + 전 기간 baseline + OAS>10% 안전장치 + IG OAS 보조 + 체제 통합 3 Phase 권고대로 반영.
- **MarginAnalyst**: ✅ `safety_grade.compute_grade_7point`은 macro_regime/cycle 독립. cycle 입력 변경 시 `get_margin_requirement(regime, cycle_phase)`의 16셀 매트릭스에서 자동 보정 — 회귀 테스트로 검증.
- **OrderAdvisor**: ✅ `extreme_fear+accumulation` 강제 시 `REGIME_PARAMS["accumulation"]`(margin=20, single_cap=5%, cash_min=25%) 적용. dual extreme(OAS>10% + 버핏 high)은 `selective`로 완화하여 4% 한도 유지. 적정.

### API 응답 shape 변경 (`GET /api/macro/credit-spread`)
- 신규: `oas_stats` / `oas_percentile` / `oas_zscore` / `oas_history_5y` / `ig_current` / `ig_history_5y` / `hy_ig_spread` / `hy_ig_spread_history_5y` / `partial_failure`
- 변경: `oas_sentiment` 3단계 → 5단계
- 호환: `oas_history`(=oas_history_5y), `percentile`(=oas_percentile) alias 유지

---

## 2026-05-04 — Phase 4: 관리 영역 확장 + 사용자별 KIS 자격증명

### 배경
멀티유저 운영을 위한 4건 일괄 처리 (옵션 B 권장 default). plan: `/Users/kimdukki/.claude/plans/shiny-herding-catmull.md`.
1. AI관리 user_id 입력 점검 → UI 정상, 사용자 목록 API 부재가 진짜 원인
2. 사용자관리 페이지 신설 (관리자 CRUD)
3. 페이지별 이용현황 통계 페이지 신설
4. 사용자별 KIS 자격증명 (AES-GCM) → 잔고/매매/양도세/포트폴리오 메뉴 활성화

### 신규 모듈 (백엔드 10)
- `services/secure_store.py` — AES-GCM 암호화. `encrypt/decrypt`. 32-byte 마스터 키 `KIS_ENCRYPTION_KEY`(SSM SecureString). nonce 12B + tag 16B. 키 미설정 시 ConfigError(503).
- `services/kis_validator.py` — `validate_kis()` KIS `/oauth2/tokenP` 호출로 즉시 검증.
- `db/models/user_kis.py` — `UserKisCredentials` 분리 테이블 (`user_id PK FK, app_key_enc, app_secret_enc, base_url, acnt_no_enc, acnt_prdt_cd_stk/fno?, hts_id?, validated_at?`).
- `db/models/page_view.py` — `PageView(id, user_id?, path, method, status_code, duration_ms, created_at)`.
- `db/repositories/user_kis_repo.py` — get/upsert/delete/mark_validated/is_valid(TTL 24h).
- `db/repositories/page_view_repo.py` — record/aggregate_by_path/top_paths/daily_count.
- `routers/me_kis.py` — POST/GET/DELETE `/api/me/kis` + `POST /api/me/kis/validate`. GET 응답은 마스킹(끝 4자리만).
- `routers/admin_users.py` — GET 목록/상세, PATCH role·password reset, DELETE. 모두 `require_admin` + audit_log 기록.
- `routers/admin_stats.py` — `GET /api/admin/page-stats?from=&to=&top=` 경로별 호출+latency+시계열.
- alembic 3건: `add_user_kis_credentials`, `add_page_view`, `add_user_id_to_orders_reservations_tax` (모두 up/down).

### 수정 (백엔드 13)
- `routers/_kis_auth.py` — `_token_cache: dict[int|None, (token, expires_at)]`. `get_kis_credentials(user_id=None)`/`get_access_token(user_id=None)`. user_id=None은 시스템(시세 등) 운영자 .env fallback. 사용자 라우터에서 user_id 무조건 전파.
- `routers/auth.py` — `/api/auth/me` 응답에 `has_kis: bool` 추가.
- `routers/balance.py`, `routers/order.py`, `routers/tax.py`, `routers/portfolio_advisor.py` — `Depends(get_current_user)` + user_id 전파.
- `services/order_service.py`, `services/tax_service.py` — 시그니처에 user_id 추가.
- `services/auth_deps.py` — `require_kis` 의존성 추가.
- `db/repositories/order_repo.py`, `tax_repo.py` — user_id 필터.
- `db/repositories/user_repo.py` — `list_users(q, limit, offset)`, `count_users(q)`, `update_role`, `reset_password` 추가.
- `main.py` — page_view 미들웨어(`asyncio.create_task` 비동기 INSERT, 제외 path: /api/health, /assets/*, /static/*, /ws/*, /api/admin/page-stats).
- `config.py` — `KIS_ENCRYPTION_KEY`, `KIS_VALIDATION_TTL_HOURS=24`.
- `requirements.txt` — `cryptography>=42`.
- `db/models/__init__.py`, `db/models/order.py`, `db/models/tax.py` — user_id 컬럼.

### 신규 (프론트 7)
- `pages/AdminAIPage.jsx` — 기존 AdminPage 3탭 이전(route `/admin/ai`).
- `pages/AdminUsersPage.jsx` — 사용자 검색/CRUD(route `/admin/users`).
- `pages/AdminPageStatsPage.jsx` — Recharts 차트, 기간 필터(route `/admin/page-stats`).
- `pages/SettingsKisPage.jsx` — KIS 등록 폼 + 검증 결과 표시(route `/settings/kis`).
- `components/KisRequiredNotice.jsx` — 미등록 안내 + 등록 버튼.
- `components/admin/*` — 사용자 콤보박스 등 보조 컴포넌트.
- `api/me.js` — `getMyKis/saveMyKis/deleteMyKis/validateMyKis`.

### 수정 (프론트 6)
- `pages/AdminPage.jsx` — `/admin` → `/admin/ai` redirect 진입점.
- `components/layout/Header.jsx` — "AI관리" → "관리" 드롭다운(3개 하위). 자산관리 그룹 메뉴 항목별 `requireKis: true` + 회색+🔒 + 클릭 시 `/settings/kis`.
- `components/common/ProtectedRoute.jsx` — `requireKis` prop. 미등록 시 `KisRequiredNotice` 렌더.
- `hooks/useAuth.jsx` — `hasKis` 추가 (`user?.has_kis`).
- `App.jsx` — 신규 라우트 + `/portfolio·/order/*·/balance·/tax/*`에 requireKis.
- `api/admin.js` — `fetchUsers/fetchUserById/patchUser/deleteUser`.

### 환경변수 추가
- `KIS_ENCRYPTION_KEY` — AES-GCM 마스터 키(b64 32-byte). **사용자별 KIS 사용 시 필수**. SSM `/stock-manager/prod/KIS_ENCRYPTION_KEY`(SecureString). 키 분실 시 모든 사용자 KIS 자격증명 영구 복구 불가.
- `KIS_VALIDATION_TTL_HOURS` — 검증 만료 TTL. 기본 `24` (시간).

### 신규 API (9개)
- `POST /api/me/kis` — 등록 + 즉시 검증
- `GET /api/me/kis` — 마스킹된 상태(끝 4자리)
- `DELETE /api/me/kis` — 삭제 + 토큰 캐시 invalidate
- `POST /api/me/kis/validate` — 재검증
- `GET /api/admin/users?q=&limit=&offset=` — 검색/페이지네이션
- `GET /api/admin/users/{user_id}` — 상세
- `PATCH /api/admin/users/{user_id}` — role/password 변경
- `DELETE /api/admin/users/{user_id}` — 삭제
- `GET /api/admin/page-stats?from=&to=&top=` — 통계

### 도메인 영향
**0건**. 체제/Graham/등급/Value Trap/주문 안전 규칙/portfolio_advisor 자문 로직 모두 미터치. 시세(quote_kis/quote_overseas/market_board) 운영자 키 통합 유지(rate limit 회피).

### 보안
- KIS_APP_SECRET 평문 저장 0건 — AES-GCM nonce 12B + tag 16B
- 응답 마스킹: `app_key`는 끝 4자리만, `app_secret`/`acnt_no`는 미노출
- 마스터 키 미설정 시 ConfigError(503) fail-fast
- 마스터 키 분실 → 영구 복구 불가 (별도 안전 백업 필수)

### 테스트
- 신규 단위 14 PASS: `tests/unit/test_secure_store.py` (9) + `tests/unit/test_kis_validator.py` (5)
- 신규 통합/API 24: `tests/integration/test_user_kis_repo.py`, `test_page_view_repo.py`, `tests/api/test_admin_users_api.py`, `test_me_kis_api.py`, `test_admin_page_stats_api.py` (PostgreSQL 의존, CI 검증 위탁)
- 회귀: 기존 단위 453 PASS 유지

### 마이그레이션 영향
신규 alembic 3건. 기존 운영 데이터:
- `orders.user_id` NULL 허용 — 기존 row는 NULL 유지(자동 매핑 안 함, 데이터 정합성 보호)
- `tax_transactions.user_id` 동일

### 멀티 인스턴스 영향 (현재 단일 EC2라 영향 0)
in-memory 토큰 캐시는 노드별 격리. 확장 시 F-4 메모(perf_audit_report.md 섹션 10.4) 참조 — Redis 전환 필요.

---

## 2026-05-03 — 성능/가용성 4단계 사이클 (Phase 1~3 + 부수 정리)

워치리스트/AI 자문 로딩 속도 이슈 분석 → 4 phase 점진 개선. RefactorEngineer + QA Inspector 합동 감사 산출물(`_workspace/dev/perf_audit_report.md` 1132줄, 5축 + AWS 인프라 5축) 기반.

### Phase 1 — 인프라 P0 (nginx 보안 헤더 drift + proxy_read_timeout)
- `infra/nginx/app.conf`: location 1→3 분리. `^~ /ws/` 3600s + `/api/` 90s + `/` 60s. 공통 프록시 헤더 server 블록 상위 이동.
- `.github/workflows/deploy.yml`: heredoc 70줄 제거 → SCP staging(`/opt/stock-manager/_staging`) + `nginx -t` 자동 검증 + `nginx -s reload` 명시 호출.
- `scripts/ec2-deploy.sh`: 비상용 명시(운영은 GitHub Actions 단일 경로).
- 핫픽스 2건: `--add-host=app:127.0.0.1`(검증 컨테이너 dummy DNS), `nginx -s reload`(volume mount 설정 반영).

### Phase 2 — Week 1 Quick Win 5건 (워치리스트/macro 성능)
- **QW-1 stock_info N+1 제거**: `db/repositories/stock_info_repo.py`에 `is_stale_from_dict()` 순수 함수 추출. `services/watchlist_service.py:_fetch_dashboard_row`가 dict 기반 fresh 판정으로 단축. 26종목 SELECT 104→26 (-75%).
- **QW-2 macro 7심볼 병렬**: `stock/yf_client.py:fetch_macro_indicators`가 `^TNX/GC=F/CL=F/USDKRW=X/...` 7심볼을 `ThreadPoolExecutor(max_workers=7)`로 병렬 조회. 첫 채움 7~14초 → 1~2초.
- **QW-3 partial_failure + logger.warning**: 워치리스트 try/except 6개 `debug→warning` 승격. row dict에 `partial_failure: list[str]` 메타필드. `frontend/src/components/watchlist/WatchlistDashboard.jsx`에 ⚠ 미수집 tooltip UI.
- **QW-4 워치리스트 dashboard 응답 캐시**: `services/_dashboard_cache.py` 신설. 사용자별 60s in-memory TTL(부분 실패 15s). `add/remove_item / update_memo` 핸들러에서 invalidate. 멀티 인스턴스 확장 시 Redis 재설계 필요(F-4-A 코드 주석).
- **INF-3 nginx gzip + 정적 캐시**: `infra/nginx/app.conf`에 gzip 8 MIME + `/assets/*` `Cache-Control: public, max-age=31536000, immutable`. 운영 검증 결과 `/assets/*.js` 1.4MB→386KB(-72.5%).

### Phase 2b — 부수 메모 정리 (보안 헤더 SSoT + SPA HEAD)
- `main.py`: `add_security_headers` 미들웨어 제거. nginx(`infra/nginx/app.conf`)를 single source of truth로 채택. 응답 헤더 중복 노출 해소(backend 5종 + nginx 6종 → nginx 단일 6종).
- `main.py`: SPA catchall `@app.get("/{full_path:path}")` → `@app.api_route("/{full_path:path}", methods=["GET","HEAD"])`. uptime 모니터/`curl -I`에서 405→200.
- `.github/workflows/deploy.yml`: 사전 `docker image prune -af` + `docker builder prune -af` 추가(EBS 가득 참으로 인한 image pull 실패 회피).

### Phase 3 — 계측(Telemetry) 도입
- `services/_telemetry.py` 신규(외부 의존성 0, stdlib only): `@timed(name)` 데코레이터, `record_event(name)` 카운터, `observe(name, value)` percentile(p50/p95/p99 deque), `start_periodic_flush(interval_sec)`.
- 7개 hot path 계측: T-1 `watchlist.dashboard` 응답+캐시 hit/miss, T-2 `_fetch_dashboard_row` per-stock+영역별 fresh 비율, T-3 `stock_info.get_stock_info`/`is_stale` 호출 횟수, T-4 `ai_gateway.call_openai_chat` latency+per-model token, T-5 `advisory` 4페이즈 timing, T-6 `yf_client._ticker` hit/miss, T-7 `analyst_pdf` 캐시 hit/miss + 다운로드 latency.
- `main.py` lifespan에서 5분 주기 stdout dump 후 reset. 메모리 < 300KB 상한.
- `TELEMETRY_ENABLED=0/1`, `TELEMETRY_FLUSH_SEC=300` 환경변수 제어.
- 1주 누적 측정 후 의사결정 트리거: 워치리스트 캐시 hit ≥ 90% → max_workers 4→8 복원, advisory refresh p95 > 30s → Phase 4 Mid 사이클 P0, yfinance 단일 종목 5+회 → RefreshContext 우선순위 P0.

### 도메인 영향
- 도메인 로직(체제 판단/Graham/등급 임계값) 변경 0건. 본 PR은 캐싱/중복제거/병렬화/계층 재배치/계측만 다룸.
- 후방 호환 100%: `is_stale(code, market, field)` 등 모든 기존 시그니처 보존.

### 테스트
- 단위 신규 5: `tests/unit/test_stock_info_freshness.py`, `test_macro_indicators_parallel.py`, `test_watchlist_partial_failure.py`, `test_dashboard_cache.py`, `test_telemetry.py`.
- API 신규 1: `tests/api/test_main_misc.py` (SPA GET 회귀 / SPA HEAD 200 / 루트 HEAD / 보안 헤더 부재).
- 단위 **453 PASS / 0 FAIL / 6 SKIP**(skip은 로컬 Python 3.9 의존성, CI 3.11 정상). 신규 30+ 케이스 모두 통과.

### 환경변수 추가
- `TELEMETRY_ENABLED` (기본 `1`): 계측 활성/비활성
- `TELEMETRY_FLUSH_SEC` (기본 `300`): 카운터 flush 간격

### 운영 측정 효과 (이론치)
| 영역 | Before | After |
|------|--------|-------|
| 워치리스트 26종목 SELECT | 104회 | 26회 (-75%) |
| F5 연타 응답 | 풀 작업 반복 | 즉시 (<50ms) |
| macro 7심볼 첫 채움 | 7~14초 | 1~2초 |
| `/assets/*.js` 전송 | 1.4MB | 386KB (-72.5%) |
| nginx HTTP timeout | 24시간 | 90s (957× 단축) |
| 보안 헤더 drift | 매 배포 누락 | 6종 안정 적용 (SSoT) |
| SPA HEAD 응답 | 405 | 200 |

---

## 2026-05-02 — AI 자문 보수성 완화 + 경기사이클×체제 조합 + 성장주 보조 트랙

### 신규 모듈
- `services/growth_grade.py` — 성장주 보조 등급(G-A/G-B/G-C). 5지표(매출CAGR/영업CAGR/FCF/R&D/사이클정합) 각 4점 → 20점. `combine_grades(value, growth)` 함수가 6종 라벨 + factor 반환 (가치D+성장A → factor 0.30 분할매수, 손절 -20%)

### 프롬프트 개선
- `services/advisory_service.py`: `_get_cycle_context()` 신규로 macro_cycle 통합. `_CYCLE_REGIME_RULES` 16셀(체제×사이클) 매트릭스 + `_format_cycle_regime_rule()` 신규. `_build_system_prompt()` 시그니처에 `cycle_ctx` 추가. **defensive "어떤 경우에도 매수 금지" 폐기** → "사이클 회복/확장 시 단계적 매수 허용"
- `_build_consensus_section()` defensive 가드 폐지 → 50% 감산 경고로 완화 (cautious와 동일)
- Graham 임계 cycle 보정: 회복/확장 15% / 과열 25% / 수축 10% (기존 30% 일괄)
- 사전 계산에 `growth_grade.compute_growth_grade()` 결과 병기 (가치 D + 성장 G-A 라벨 표시)
- JSON 응답 스키마에 `성장주_보조판단` 필드 추가
- `services/portfolio_advisor_service.py`: 톤 균형화 — "현금 확보를 위한 매도 우선 검토" → "조합 권고에 따라 비중 조정", "가중 평균<B면 신규 편입 전면 보류" → "사이클 주도 섹터 + 가치 B 이상 또는 성장 G-A 한정 허용", 손실 -15% "손절 우선" → "손절/평균단가 분할매수/홀딩 3안 균형 제시". `_format_cycle_context`에 사이클×체제 액션 매트릭스 가이드 1줄 추가

### 도메인 규칙
- `services/macro_regime.py`: `get_regime_params(regime, cycle_phase)` + `get_margin_requirement(regime, cycle_phase)` 신규 — 16셀 매트릭스 동적 single_cap/margin. defensive+회복=7%·35%, +확장=5%·40%, +과열=2%·40%, +수축=0%·40%. 기존 `REGIME_PARAMS` dict는 fallback 호환
- `services/safety_grade.py`: `GRADE_FACTOR["C"]=0 → 0.25` (C 등급 부분 진입 허용), `GRADE_STOP_LOSS_PCT["C"]=-15%` 신규, `valid_entry`에 C 포함. D는 0 유지(가치). 7지표 임계값 변경 없음

### 스키마
- `services/schemas/advisory_report_v3.py`: `GrowthAuxiliary` Pydantic 모델 신규(growth_grade/growth_score/growth_thesis/cycle_alignment/combined_label, 모두 Optional, backward-compat)

### 테스트
- 신규 5: `tests/unit/test_growth_grade.py`(11) / `test_macro_regime_cycle.py`(25) / `test_advisory_prompt_cycle.py`(6 환경 의존 skip) / `tests/integration/test_advisory_growth_track.py`(5) / `test_portfolio_advisor_tone.py`(7 환경 의존 skip)
- 수정 1: `tests/unit/test_safety_grade.py` C 등급 정책 변경 반영(grade_factor/position_size/stop_loss 3건)
- **414 PASS / 0 FAIL / 6 SKIP** (skip은 로컬 Python 3.9의 stock/* import 실패만, CI 3.11에서 정상)

### 도메인 자문 합의안 (4명)
- MacroSentinel: cycle×regime 16셀 single_cap 매트릭스
- MarginAnalyst: Graham 임계 cycle 보정 15%/25%/10%
- OrderAdvisor: 분할 진입 30→30→40, D+A 우회 진입 시 1차 25%만+손절 -20%
- ValueScreener: 성장 5지표 임계값 G-A=16-20, G-B=12-15, G-C<12

## 2026-05-02 — 워치리스트 t3.small OOM 핫픽스

### 버그 수정
- `services/watchlist_service.py:226`: `ThreadPoolExecutor(max_workers=min(10, len(items)))` → `min(4, len(items))` — 워치리스트 26종목 × 3종 외부 API(price/metrics/financials) 호출이 10병렬로 진행되어 t3.small(1.9GB)에서 메모리 폭증 + swap thrashing → 모든 API hang(`/api/watchlist/dashboard nginx 499 timeout`). 동시성 축소로 OOM 방지

## 2026-05-02 — 워치리스트 안정화 추가 개선 4종

### 인프라
- `entrypoint.sh`: 컨테이너 시작 시 `cache.db` 무조건 초기화 → `CACHE_PURGE_ON_START=1` 환경변수일 때만 초기화. 기본 보존으로 t3.small cold cache 첫 진입 폭주 방지
- `entrypoint.sh`: uvicorn 실행에 `--limit-concurrency 20 --timeout-keep-alive 5` 추가. `UVICORN_CONCURRENCY`/`UVICORN_KEEPALIVE` 환경변수로 조정 가능. worker가 동시 21번째 요청은 즉시 503 반환하여 전체 hang 방지
- `db/repositories/stock_info_repo.py`: TTL 연장 — price off 6h→12h, metrics trading 2h→6h·off 12h→24h, returns off 6h→12h. 외부 API 호출 빈도 감소로 메모리/네트워크 부하 완화
- `infra/modules/compute/user_data.sh`: Swap 2GB→4GB 확장 + `vm.swappiness=10` 추가. 메모리 압박 시 swap thrashing 빈도 감소(다음 EC2 재생성 시 적용, 기존 인스턴스는 수동 적용 필요)

## 2026-05-01 — AI 입력 데이터 패널 통합 + 증권사 컨센서스 노출

### UI 개선
- `frontend/src/components/advisory/ResearchDataPanel.jsx` 전면 리팩토링 — 기본/리서치 2섹션 구분 제거, **16개 카테고리 단일 목록**으로 통합
- 신규 카테고리 **증권사 컨센서스(`analyst_consensus`)** 표시:
  - 통계 6종(목표가 중앙값/평균/std/dispersion/상승여력 중앙값/컨센수)
  - 의견 분포(매수/보유/매도) + 강력매수/강력매도 보조 표시
  - 모멘텀 5단계 배지(strong_up/up/flat/down/strong_down) + 과열 경고
  - 6개월 목표가 추이 + 최근 5건 리포트 카드(증권사·날짜·의견·TP·요약·PDF 링크)
- 계량지표 카드 보강: ROA / 주당배당금 / 시가총액 신규 표시
- 거시 경제 카테고리에 52주 가격 위치 통합 (52주 고가/저가/위치%/고점 대비%)

## 2026-05-01 — AI자문 프롬프트 누락 데이터 보강 + 미래지향/역발상 강화

### 프롬프트 개선
- 누락 데이터 6종을 `_build_prompt()`에 신규 섹션으로 추가:
  - `## 사업 개요`: `business_description` + `business_keywords` + `segments` 매출 비중 (역발상·미래지향 분석의 출발점)
  - `## 가격 위치`: 52주 고가/저가 대비 현재가 위치 (%)
  - `## 자본행위 분류`: 1년 공시에서 유증/CB/BW/감자/자사주매입·소각/배당/M&A 자동 분류
  - `## 장기(10년) 밸류에이션 사이클`: `valuation_history`로 PER/PBR 10년 범위·평균
  - `## 경쟁사 비교`: `peers` PER/PBR/시총 표
  - `## 계량지표`에 **배당수익률·주당배당금** 추가 (KR 골프존 등 배당 종목 미인지 버그 수정)
- 시스템 프롬프트 미래지향/역발상 강화 (`_build_system_prompt`):
  - "결정은 과거가 아닌 미래에 베팅" 원칙 명시
  - 역발상 4대 시그널 가이드 (과매도+펀더멘털 강건 / 사이클 턴어라운드 / 컨센서스 합의도 반박 / 자사주·내부자 매수)
  - catalyst 8종 식별 의무 (3개 이상 권장: 신규시장/제품/규제/M&A/자사주/배당정책/구조조정/사이클회복)
  - peak-out 선행지표 검증 지침
  - 6대 → **8대 분석 항목** 확장 (미래성장동력, 역발상관점 추가)

### JSON 스키마 확장
- `미래성장동력`: catalysts / turning_points / industry_tailwinds / peak_out_signals / growth_horizon / confidence
- `역발상관점`: contrarian_thesis / market_misperception / edge / rebut_consensus / asymmetric_payoff
- `services/schemas/advisory_report_v3.py`: `FutureGrowthDrivers`, `ContrarianView` Pydantic 모델 신규. 모두 Optional → 기존 응답 backward-compat

### 버그 수정
- `stock/yf_client.py:fetch_metrics_yf()`: `dividend_yield`/`dividend_per_share` 3단계 fallback 추가 (US 종목 배당 누락 보완)
- `services/advisory_service.py:_build_metrics_kr()`: `dividend_yield`/`dividend_per_share` pass-through 추가 (KR 종목 배당 누락 수정)
- `stock/research_collector.py:_compute_momentum()`: 컨센서스 과열 임계값 0.30 → 0.20 (strong_up 경계와 정합, CI 테스트 통과)

---

## 2026-05-01 — 애널리스트 보고서 본문 → 종목 AI 자문 통합

### 애널리스트 컨센서스 신규
- `stock/analyst_pdf.py`: 증권사 PDF 본문 추출+요약 신규. `pdfplumber` 첫 5페이지 → `gpt-4o-mini` JSON 응답으로 6항목 강제 추출(catalyst 2 / risk 2 / TP 산정 근거 1 / EPS 추정 변경 1) → 300자 결합 텍스트
- 환각 방지: 시스템 프롬프트에 "본문에 명시된 숫자만 인용. 추정·외삽·외부 지식 금지" 명시
- PDF 다운로드 보안: 10MB 한도, Content-Type 검증, 모든 예외 흡수, 짧은 본문(100자 미만) 시 요약 생략
- 영구 캐시: `cache.db`에 `analyst:summary:{md5(pdf_url)}` 키. 동일 PDF 재요청 시 OpenAI 호출 0회
- `services/ai_gateway`: `service_name="analyst_summary"`, `user_id=None`(시스템 호출, 유저 일일 쿼터 미차감, `ai_usage_log`엔 기록)

### research_collector 6번째 카테고리
- `stock/research_collector.py`: `analyst_consensus` 카테고리 추가 (5→6 카테고리). `ThreadPoolExecutor` 병렬 슬롯에 합류
- KR/US 의견 매핑 31개 (`Strong Buy`/`강력매수`/`Buy`/`매수`/`Outperform`/`Overweight`/`Hold`/`Neutral`/`보유`/`Sector Perform`/`Sell`/`Underperform`/`매도`/`Strong Sell`/`강력매도` 등) → 5단계 정규화 → 3단계 재집계
- 컨센서스 통계: 중앙값(평균 대비 극단치 강건) + 평균 + 표준편차 + dispersion(stdev/median) + upside_pct_median. `target_price=None` 행은 분모 제외, count는 전체
- 시간축 추이: 동일 broker 6개월 변화율 평균 → 5단계 라벨(`strong_up`/`up`/`flat`/`down`/`strong_down`). 30%+ 동시 상향 broker 50% 초과 → `consensus_overheated=True`
- 영속: `AnalystRepository.upsert_report` 호출로 `analyst_reports` 테이블에 저장 → `get_target_price_history(180일)` 조회

### 신규 DB 테이블
- `db/models/analyst.py` `AnalystReport`: `id, code, market, broker, target_price(BigInteger), opinion, title, pdf_url, summary(Text), published_at, fetched_at`. 유니크 `(code, market, broker, published_at, title)` + 인덱스 `(code, market, published_at)`
- `db/repositories/analyst_repo.py` `AnalystRepository`: `upsert_report` (UPSERT — 동일 키 시 summary/target_price/opinion/fetched_at만 갱신) / `list_reports(since=, limit=)` / `get_target_price_history(days=180)`. 미래 날짜·`YY.MM.DD` 형식 자동 보정
- `alembic/versions/b3d4e5f6a7c8_add_analyst_reports_table.py`: 단일 head 유지 (parent: `9cda1c3787e5`)

### advisory_service 12번 섹션
- `services/advisory_service.py`: `_build_consensus_section()` 헬퍼 추가 + `_build_prompt()` 끝에 합류
- 체제별 차등 표시: defensive → 빈 문자열(섹션 자체 미표시) / cautious → 정상 표시 + "50% 가중 감산" 경고 라인 / accumulation·selective → 정상
- KR 출력: 중앙 목표가 + 현재가 대비 upside% + 표준편차 + dispersion + 매수/보유/매도 분포 + momentum_signal + 과열 시 경고 + 최근 3건(증권사·날짜·의견·TP·요약 100자) + 6개월 추이
- US 출력: 등급 변경 이력 형식 (Goldman: Buy → Sell 등)
- 시스템 프롬프트 강화: "증권사 컨센서스를 무비판적으로 수용하지 말 것 — 합의도(dispersion)/과열(consensus_overheated)/체제 신뢰도를 종합 판단"
- Value Trap 5규칙 → 6규칙: 6) 증권사 컨센서스 과열(consensus_overheated=True 시 가산 1점)
- 사전 계산값(grade/score/진입가/손절가) 불변 — 컨센서스는 GPT reasoning input일 뿐 (`compute_grade_7point`/`compute_position_size` 시그니처 변경 없음)

### 테스트
- `tests/unit/test_analyst_imports.py` (17 LOC), `test_analyst_pdf.py` (299 LOC)
- `tests/integration/test_analyst_repo.py` (173 LOC), `test_research_collector_analyst.py` (343 LOC), `test_advisory_prompt_analyst.py` (317 LOC)
- 부서장 직접 검증: 의견 정규화 / 컨센서스 산출 / momentum 계산 / `_build_consensus_section` 6/6 시나리오 / SQLite 마이그레이션 + Repository CRUD 모두 PASS

### 의존성
- `requirements.txt`: `pdfplumber>=0.11` 추가

## 2026-04-30 — 스크리너 안정화 + 관심종목 UX + 섹터히트맵 3Y + Advisory 버그수정 + PER/DART 개선

### 버그 수정
- `screener/krx.py`: KRX 종목 목록 빈 응답 시 `force_relogin()` 후 1회 재시도 (세션 만료 자동 복구)
- `screener/krx_auth.py`: `force_relogin()` 함수 추가 — 세션 강제 만료 + 재로그인
- `services/advisory_service.py`: 기본적 분석 새로고침 HTTP 500 수정 — `_collect_fundamental_kr()`에 `user_id` 파라미터 미전달 `NameError` 해결
- `stock/dart_fin.py`: DART 재무 연도 클릭 시 잘못된 보고서 열리는 버그 수정 — 3년 배치 호출(rcept_no 공유)에서 연도별 API 호출(고유 rcept_no)로 변경
- `stock/market.py`: PER 산출 개선 — `forwardPE` 제거(한국 주식 비정상 값) + fallback을 `income_stmt` 연간 순이익 기반으로 변경 + `trailingPE` 존재 시 덮어쓰기 방지

### 증권사 목표가 팝업 신규
- `stock/naver_research.py`: 네이버 증권 리서치 스크래핑 — 증권사별 최신 목표가+투자의견+리포트 제목+PDF 링크. ThreadPoolExecutor 병렬 수집. 캐시 6시간
- `stock/yf_client.py`: `fetch_upgrades_downgrades()` 추가 — 해외 종목 증권사 등급 변경 이력 (yfinance)
- `routers/advisory.py`: `GET /{code}/analyst-reports` 엔드포인트 추가 (KR=네이버/US=yfinance)
- `AnalystReportsModal.jsx`: 목표주가 클릭 시 증권사별 목표가 팝업 (KR: 증권사+목표가+의견+리포트+PDF / US: 등급이력)
- `FundamentalPanel.jsx`: 목표주가 값을 클릭 가능한 링크로 변경 → 모달 연결

### 하이일드 스프레드 하워드 막스 프레임워크
- `stock/macro_fetcher.py`: FRED HY OAS(BAMLH0A0HYM2) 5년 시계열 무료 CSV 수집. 하워드 막스 시계추: OAS<3.5%=탐욕(수비), 3.5~7%=정상, >7%=공포(공격)
- `CreditSpreadSection.jsx`: 시계추 카드(해석+전략) + 게이지 바(3구간) + OAS 5년 차트(3.5%/7% 기준선) + 기존 HYG/LQD 차트 유지

### 코드 품질 개선
- `DetailPage.jsx`: `useState(false)` → `useRef(false)` 버그 수정 (`advLoadedRef`)
- `OrderPage.jsx`: setTimeout ref 관리 + 언마운트 시 clearTimeout (메모리 누수 방지)
- `stock/cache.py`: 4곳 `except: pass` → `logger.warning()` 추가 (디버깅 가능)
- `services/order_fno.py`: 3곳 hashkey 발급 실패 시 `logger.warning()` 추가

### UI 개선
- `SectorConceptTabs.jsx`: 데일리 추천 페이지에서 관심종목 기등록 종목 `★ 관심종목` 표시 (watchlist 로드 + `alreadyAdded` prop)
- `WatchlistButton.jsx`: 추가 완료 후 `✓ 추가됨` → `★ 관심종목`으로 통일
- `Header.jsx` + `ReportPage.jsx`: 메뉴명 "보고서" → "데일리 추천", 페이지 제목도 동일 변경
- `SectorHeatmapSection.jsx`: "현재가" 컬럼 제거 + "3Y" 컬럼 추가 (5기간: 1M/3M/6M/1Y/3Y)
- `stock/macro_fetcher.py`: 섹터 ETF 조회 기간 `1y` → `3y` 확장, `return_3y`(756거래일) 추가, `price` 필드 제거

---

## 2026-04-29 — AI 게이트웨이 + 섹터 추천 개선 + PER 수정 + 보고서 접근 수정

### AI 게이트웨이 + 사용량 관리 신규
- `services/ai_gateway.py`: 모든 OpenAI API 호출의 단일 진입점 (`call_openai_chat()`). 유저별 일일 쿼터 체크 + 사용량 기록. `AiQuotaExceededError`(429)
- 기존 6개 서비스의 OpenAI 직접 호출을 게이트웨이로 전환 (advisory_service, sector_recommendation_service, portfolio_advisor_service, macro_service×2, advisory_fetcher)
- `db/models/admin.py`: 3개 테이블 (ai_usage_log, ai_limits, audit_log)
- `db/repositories/admin_repo.py`: 사용량/한도/감사로그 CRUD
- `routers/admin.py`: Admin API 6개 엔드포인트 (사용량 조회, 한도 설정, 감사 로그)
- `AdminPage.jsx`: Admin 관리 페이지 3탭 (사용량/한도/감사로그)

### 섹터 추천 데이터 기반 개선
- `stock/macro_fetcher.py`: 한국 섹터 ETF 13종 수익률 수집 (`fetch_sector_returns_kr()`) — KODEX 반도체/2차전지/건설/바이오 등
- `services/sector_recommendation_service.py`: GPT 프롬프트에 실제 섹터 ETF 수익률 테이블 전달. defensive 하드코딩 규칙 제거 → 실제 가격 추세 기반 모멘텀/역발상 분류
- `services/pipeline_service.py`: 파이프라인에서 시장별 섹터 수익률 수집 후 전달

### 버그 수정
- `stock/market.py`: PER fallback — yfinance forwardPE 부정확(골프존 4.61→12.06) → 시총/TTM순이익 직접 계산 (PBR/ROE fallback과 동일 패턴)
- `ReportPage.jsx`: 비admin 유저 접근 시 "보고서 생성 실패" 에러 → fetchReportByDate로 기존 보고서 조회. 보고서 없을 때 안내 메시지 분기

---

## 2026-04-29 — DART 계정명 정규식 전환 + 밸류에이션 차트 이동 + UI 개선

### 리팩토링
- `dart_fin.py`: DART 계정명 매칭 전면 정규식 전환 — `_ACCOUNT_KEYS`/`_BS_KEYS`/`_IS_DETAIL_KEYS` tuple → `_ACCOUNT_REGEX`/`_BS_REGEX`/`_IS_DETAIL_REGEX` re.Pattern
- `dart_fin.py`: 공용 `_match_account()` 함수 (공백 제거 + 정��식 매칭) — 5개 추출 함수 통합
- `dart_fin.py`: EPS 계정명 `"기본주당손익"` 변형 정규식 대응 (한국가스공사 EPS=None 해결)

### UI 개선
- DetailPage: "CAGR 요약" → "요약" 서브탭 이름 변경 + 하단에 PER/PBR/시총/주식수 밸류에이션 차트 배치
- TechnicalPanel: 밸류에이션 차트 제거 (요약 탭으로 이동)
- WatchlistButton: code/market 변경 시 상태 리셋 (탭 전환 후 "추가됨" 고착 버그 수정)
- App.jsx: 사이트 하단 투자 면책 문구 footer 추가

## 2026-04-29 — 웹 보안 헤더 추가 (securityheaders.com F→A)

### 보안 강화
- nginx(HTTPS): 보안 헤더 6개 추가 (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, HSTS)
- nginx: `server_tokens off` + `proxy_hide_header Server` (서버 정보 숨김)
- FastAPI 미들웨어: 보안 헤더 5개 추가 (IP 직접 접근 시에도 적용, HSTS 제외)

## 2026-04-29 — 경기국면+투자체제 통합 + 스크리너 한글화 + 전략빌더 UX 개선

### UI 개선
- 매크로 경기사이클: 경기 국면(5지표)과 투자 체제(심리/밸류에이션)를 2컬럼으로 나란히 표시
- 매크로 경기사이클: 경기 국면·투자 체제 hover 시 판단 기준 상세 툴팁 표시
- 매크로 경기사이클: 국면과 체제 괴리 시 설명 메시지 자동 표시
- 매크로 경기사이클: 하단 지표 게이지바 제거 → 소형 카드(신호값만) 간결화
- 스크리너: 투자전략 드롭다운 6종 한글화 (마법공식/저PER총수익/기대수익률/순유동자산/저PSR턴어라운드/재무건전성)
- 스크리너: 구루/GB/NF/주의 컬럼 헤더에 hover 툴팁 추가
- 스크리너: DART 프리셋 선택 시 구루 컬럼 항상 표시 (데이터 미수집 시에도)
- 스크리너: 구루점수 분모 6 고정 (기존 formulas_available/formulas_available 버그 수정)
- 백테스트: 전략빌더 탭을 기본 탭으로 변경 (탭 순서: 전략빌더→프리셋→커스텀)
- 백테스트: 전략빌더에서 YAML 변환 후 바로 백테스트 실행 가능 (커스텀 탭 전환 불필요)
- 전략빌더: 리스크관리 최소 1개 필수 검증 + 에러 메시지
- 전략빌더: StepPreview에서 중복 버튼(YAML변환/검증하기/전략저장) 제거 → 하단 네비에 "전략 완성"+"전략 저장" 통합

### 백엔드 개선
- `macro_service.get_macro_cycle()`: 투자 체제(determine_regime) 데이터 동시 반환
- `portfolio_advisor_service`: 경기사이클 국면(phase/leader_sectors/confidence) GPT 입력에 추가 → 섹터 추천 품질 향상

## 2026-04-29 — 매크로 분석 버그수정 + 개선

### 버그 수정
- YieldCurveSection/CreditSpreadSection/MacroCycleSection: API 응답 래핑(`{yield_curve:{...}}`) 언래핑 누락 → `data.yield_curve || data` 패턴 추가
- 경기사이클 `scores` 응답: 영문 국면명 점수 → 지표별 한국어 신호(스프레드 +0.76%, 축소 중, VIX 16.5 보통 등)

### 매크로 분석 개선
- 장단기 금리차/하이일드 스프레드 시계열: `period="6mo"` → `period="max", interval="1wk"` (금리 60년+, HYG/LQD 18년)
- 원자재에 **우라늄 ETF(URA)** 추가 (WTI-금 사이, 총 6종)
- 주요 지수에 **유로스톡스 50/닛케이 225/상하이종합/인도 SENSEX** 추가 (총 8개)
- 경기사이클: "현재 경기 국면" 라벨+크기 강조
- `frontend-dev.md` 에이전트에 모바일 호환성 규칙 테이블(9패턴) + 자가 점검 체크리스트 추가

---

## 2026-04-29 — 매크로 분석 대규모 개선 (6개 섹션 신규)

### 매크로 분석 신규
- **경기 사이클 국면** (`MacroCycleSection`): 4단계(회복/확장/과열/수축) 순환 다이어그램 + confidence + 5지표 breakdown + 주도 섹터 태그
- **장단기 금리차** (`YieldCurveSection`): ^IRX/^FVX/^TNX/^TYX 수익률곡선 LineChart + 10Y-3M 스프레드 시계열 AreaChart + 역전 경고
- **하이일드 스프레드** (`CreditSpreadSection`): HYG/LQD yield 카드 + 가격 비율 시계열 + widening/narrowing 배지
- **환율** (`CurrencySection`): USD/KRW, USD/JPY, EUR/USD, DXY 4개 카드 + 1개월 스파크라인
- **원자재** (`CommoditySection`): WTI, 금, 옥수수, 밀, 대두 5개 카드 + 1개월 스파크라인
- **섹터 히트맵** (`SectorHeatmapSection`): 11개 S&P 섹터 ETF × 4기간(1M/3M/6M/1Y) 수익률 히트맵 (초록~빨강 그라데이션)
- `services/macro_cycle.py` 신규: 5지표 가중합산 경기 국면 판단 (macro_regime.py와 독립)
- `stock/macro_fetcher.py`: 6개 yfinance 수집 함수 추가 (금리, 신용, 환율, 원자재, 섹터, 국면입력)
- `routers/macro.py`: 6개 GET 엔드포인트 추가 (총 11개)
- MacroPage 10개 섹션 통합 (기존 4 + 신규 6)

---

## 2026-04-28 — 모바일 호환성 전면 점검

### UI 개선
- Header: 모바일 햄버거 메뉴 추가 (`md:hidden`), 세로 네비게이션 패널, 드롭다운 클릭 지원
- ToastNotification: `w-80` → `w-[calc(100vw-1rem)] sm:w-80` (모바일 뷰포트 초과 방지)
- ScreenerPage: 300px 고정 사이드바 → `grid-cols-1 md:grid-cols-[300px_1fr]` 반응형
- ScreenerPage: 체제 배너 `flex-col sm:flex-row` 세로 스택
- FilterPanel/ReservationForm/OrderForm: `grid-cols-2` → `grid-cols-1 sm:grid-cols-2` 반응형 (총 7곳)
- PortfolioSummary: `grid-cols-3` → `grid-cols-1 sm:grid-cols-3`
- BacktestResultPanel: 메트릭 카드 `grid-cols-1 sm:grid-cols-2 md:grid-cols-4`
- BacktestPage: 설정 그리드 `grid-cols-1 sm:grid-cols-2 md:grid-cols-3`
- FinancialTable: 추정치 그리드 반응형 추가
- ReportDetailView: 체제/지수 그리드 반응형 추가
- StockHeader: `gap-6` → `gap-3 md:gap-6` (모바일 간격 축소)
- CustomStockSection: 삭제 버튼 터치 영역 확대 + 모바일 항상 표시

---

## 2026-04-28 — 도메인 + HTTPS 설정 (dkstock.cloud)

### 인프라
- `dkstock.cloud` 도메인 연결 (가비아 DNS → EC2 Elastic IP `3.39.188.29`)
- nginx 리버스 프록시 컨테이너 추가: SSL 종료 + HTTP→HTTPS 리다이렉트 + WebSocket 프록시
- Let's Encrypt certbot 컨테이너: 12시간마다 자동 인증서 갱신
- `infra/nginx/app.conf` 신규: nginx 설정 (dkstock.cloud + www, TLS 1.2/1.3)
- `scripts/init-ssl.sh` 신규: EC2 초기 SSL 인증서 발급 스크립트
- `docker-compose.prod.yml`: app `ports: 80:8000` → `expose: 8000` (내부 전용) + nginx/certbot 추가
- `deploy.yml`: nginx 설정 인라인 배포 + 3컨테이너(app+nginx+certbot) 구성

---

## 2026-04-28 — 테스트 환경 PostgreSQL 전환

### 테스트 인프라
- 테스트 DB를 인메모리 SQLite → **PostgreSQL 16**으로 전환 (프로덕션 동일 DBMS)
- `docker-compose.test.yml` 신규: 테스트용 PostgreSQL 컨테이너 (tmpfs 메모리 기반, 포트 5433)
- `tests/conftest.py`: session scope 엔진 + 함수별 TRUNCATE 격리 패턴
- CI(`ci.yml`): PostgreSQL service container 추가, `TEST_DATABASE_URL` 환경변수

### 버그 수정 (PostgreSQL 전환으로 발견)
- `stock_info` 모델 `shares`/`revenue`/`operating_income`/`net_income` 컬럼: `Integer` → `BigInteger` (삼성전자 발행주식수 59.7억 등 32bit 오버플로우)
- Alembic 마이그레이션 추가 (`de1f3d32fb96`)

---

## 2026-04-28 — AI자문 v3 전면 통합 (프롬프트+입력데이터+보고서 일원화)

### 프롬프트 통합
- v2/v3 이중 프롬프트 구조를 **단일 통합 프롬프트**로 전면 재작성
- 시스템 프롬프트: "20년 경력 수석 애널리스트 비판적 검증 모드" + 6대 분석 항목 + 정량 프레임워크
- 유저 프롬프트: 10년 재무(이자보상배율 포함) + 기술지표 + 리서치 데이터를 하나의 맥락으로 구성
- 중복 제거: 포지션가이드+최종매매전략→최종매매전략, 밸류에이션심화+밴드→밸류에이션분석, 매크로환경+사이클→매크로및산업분석

### 입력 데이터 통합
- `refresh_stock_data()` 1회 호출로 기본분석+리서치 데이터 전체 수집 ("입력정보 획득" 버튼 제거)
- 재무 데이터 수집 범위 5년→10년 확장 (dart_fin/yf_client years=10), 분기 실적 4분기→8분기
- `stock/research_collector.py` 신규: 거시지표/밸류에이션밴드/경영진/공시/뉴스 5카테고리 병렬 수집 (LLM 비용 0)
- `advisory_cache` 테이블에 `research_data` JSON 컬럼 추가 (Alembic 마이그레이션)

### v3 통합 스키마
- `advisory_report_v3.py` 전면 재작성: v2 상속 제거, 독립 통합 스키마
- 6대 분석 섹션: 재무건전성분석/밸류에이션분석/매크로및산업분석/경영진트랙레코드/가치함정분석/최종매매전략
- `generate_ai_report()` v2/v3 분기 완전 제거, 항상 v3 검증

### 프론트엔드
- `ResearchDataPanel.jsx` 신규: 프롬프트 전체 입력 데이터 미리보기 (기본분석 10항목 + 리서치 5항목)
- `AIReportPanel.jsx` 중복 섹션 제거: 포지션가이드/밸류에이션심화/매크로환경분석 카드 삭제
- 통합 보고서 구조: 등급→의견→6대분석→전략→시그널→시나리오→리스크/포인트

### 백엔드 확장
- `yf_client.py`: `fetch_company_officers()`/`fetch_major_holders()`/`fetch_earnings_dates()`/`fetch_macro_indicators()`/`fetch_sector_peers()` 5개 함수 추가
- `dart_fin.py`: `calc_interest_coverage()` 이자보상배율 계산 헬퍼
- `advisory_repo.py`: `save_research_data()` 리서치 전용 저장 함수
- `routers/advisory.py`: `POST /{code}/research` 수동 리서치 수집 엔드포인트

## 2026-04-27 — CI segfault 수정 + 섹터 컬럼 + 계층형 하네스

### 버그 수정
- CI pytest segfault 해결: `main.py` lifespan 백그라운드 서비스(prewarm/WS/스케줄러)를 `TESTING` 환경변수로 테스트 시 스킵
- conftest `engine.dispose()` 제거: daemon 스레드(pipeline 등)가 DB 접근 중 dispose되면 segfault 발생하는 문제 해소

### 섹터 컬럼 추가
- `fetch_market_metrics()` 반환값에 `sector` 필드 추가 (yfinance `info.get("sector")`)
- 관심종목 대시보드: 종목명 우측에 섹터 컬럼 추가
- 스크리너 테이블: 종목명 우측에 섹터 컬럼 + 52주 고점 대비 하락률(`drop_from_high`) 컬럼 추가

### 계층형 하네스 재구성
- 부서장(`department-head.md`) 신규: 모든 개발 요청의 단일 진입점, 유형 A/B/C/D 자동 라우팅
- 도메인팀장(`domain-lead.md`) 신규: 도메인 전문가 4명 팀 관리
- 개발팀장(`dev-lead.md`) 신규: 개발/QA/리팩토링 5명 팀 관리
- `asset-dev` 스킬을 부서장 오케스트레이터로 재작성 (코드 변경 수반 모든 요청의 단일 트리거)

## 2026-04-26 — 스크리너 구루 프리셋 확장 + UI 개선

### 구루 프리셋 3종 추가
- Graham NCAV(`calc_graham_ncav`): 순유동자산가치/시총 비율. 적자기업 ��함. 청산가치 기반 절대 ���전마진
- Fisher PSR(`calc_fisher_psr`): 시총/매출액. 적자기업 포함. 매출 기반 턴어라운드 발굴
- Piotroski F-Score(`calc_piotroski_fscore`): 8항목 재무건전성(신주발행 제외). 수익성(4)+재무구조(2)+영업효율(2). 추가 API 호출 0회
- 구루 패널 12점→24점 확장 (6공식×4점). Value Trap 7규칙 (F-Score극저, 극저PSR+매출급감 추가)
- 체제별 파라미터(`REGIME_GURU_PARAMS`) ncav/psr/fscore 임계값 추가

### UI 개선
- 필터 패널 접기/펼치기 버튼 (테이블 전체 폭 활용)
- 서준식 프리셋 per_min=0 버그 수정 (PER=None 종목 필터링 문제)
- defensive 체제 센티넬값(999) roe_min 유입 버그 수정
- guru_top 별도 입력 제거 (top과 통일)
- 구루 프리셋별 전략 소개 패널 추가 (6개 전략 상세 설명)
- 프리셋 선택 시 정렬 필드 자동 전환

## 2026-04-26 — 스크리너 구루 공식 + 체제 연계

### 스크리너 구루 공식 신규
- `services/guru_formulas.py` 신규: Greenblatt Magic Formula(ROIC+Earnings Yield), Neff Total Return Ratio(EPS CAGR+배당/PER), 서준식 기대수익률(ROE/PBR)
- 통합 구루 패널 (12점=3공식×4점), Value Trap 경고 5규칙, 체제별 파라미터(`REGIME_GURU_PARAMS`)
- `screener/service.py` 확장: `enrich_seo_scores`(서준식 일괄 계산), `sort_by_greenblatt_rank`(Combined Rank), `get_preset_filters`(프리셋별 기본 필터)
- `routers/screener.py` 확장: DART guru enrichment(`_enrich_guru`), 신규 파라미터(`preset`/`regime_aware`/`include_guru`/`guru_top`), 체제 응답 포함
- 4단계 파이프라인: KRX 기본 필터 → yfinance enrichment → DART guru enrichment → 체제 연계
- 단위 테스트 32개 (`tests/unit/test_guru_formulas.py`)

### 스크리너 UI 재설계
- FilterPanel: 구루 프리셋 드롭다운(Greenblatt/Neff/서준식), 체제 연계 토글, DART 분석 대상 수, 필터 설명 보강
- StockTable: 서준식 기대수익률 컬럼(항상), 구루 점수 배지/개별 점수/Value Trap 경고(DART enrichment 시)
- ScreenerPage: 체제 배너(regime+VIX/버핏/F&G+한줄메시지), 프리셋 배지, DART 로딩 메시지

## 2026-04-26 — 투자보고서 전면 개선 + AI자문 리포트 강화

### 투자보고서 페이지 전면 개선
- GPT 섹터 추천 서비스 신규 (`sector_recommendation_service.py`): 매크로 현황 기반 3컨셉(모멘텀/역발상/3개월선점) 탑픽 섹터+종목 추천. `macro_store` 일일 캐싱
- 파이프라인 확장: Step 0 중복방지(날짜+market) + Step 1.5 매크로 수집+GPT 섹터 추천 + report_json version 2 구조
- 보고서 페이지 UI 전면 재설계: 3탭 제거 → 페이지 진입 시 KR/US 자동 실행, 매크로 체제 카드(공유) + KR/US 토글 + 섹터 추천 + 종목+관심종목 버튼, 하단 이력 카드
- 신규 컴포넌트: `ReportDetailView`, `SectorConceptTabs`, `ReportHistoryList`
- `DailyReport.to_summary_dict()`에 `sector_summary` 필드 추가 (이력 목록에 전략별 섹터 요약)
- `GET /api/reports/by-date` 엔드포인트 추가

### AI자문 리포트 강화
- System/User Prompt에 4개 신규 분석 가이드라인 추가 (매크로환경분석/밸류에이션심화/시나리오분석/관련투자대안)
- Pydantic v2 스키마 확장: `MacroAnalysis`, `ValuationDeepDive`, `ScenarioAnalysis`, `InvestmentAlternative` 모델
- AIReportPanel에 4개 신규 섹션 UI: 매크로 카드, 밸류에이션 심화, 시나리오 3컬럼(낙관/기본/비관), 관련 투자 대안
- `max_completion_tokens` 10000→14000 (재시도 12000→18000)

## 2026-04-26 — KLineChart 차트 추가 + ROE/PBR 버그 수정

### KLineChart 캔들차트 신규
- 관심종목 상세(`DetailPage`)에 KLineChart(Canvas 기반) 캔들차트 추가
- StockHeader와 탭(재무분석/종합리포트) 사이에 배치
- 타임프레임 선택(15분/60분/1일/1주), 기간 선택, 기술지표 토글(MA/BB/VOL/MACD/RSI)
- 한국식 색상 테마(상승=빨강, 하락=파랑), 기존 OHLCV API 재사용
- `klinecharts@9.8.12` 의존성 추가

### 버그 수정
- ROE 미표기: `fetch_market_metrics()` — yfinance `returnOnEquity` None 시 분기 TTM순이익/자기자본 fallback 추가
- PBR 미표기: `_get_report_kr()` ��� `fetch_detail()` PBR/PER None 시 `fetch_market_metrics()` 값으로 보충

---

## 2026-04-26 — 하네스 TDD 애자일 재구성 + 개발자 분리

### 하네스 재구성
- 도메인 전문가 4명: 수동적 자문 → **능동적 요건 정의 참여** + 팀 통신 프로토콜 추가
- TestEngineer: 구현 후 테스트 → **TDD RED phase** (테스트 선행 작성)
- DevArchitect → **BackendDev + FrontendDev 분리** (백엔드/프론트 전담)
- QA Inspector: 파이프라인 끝 검증 → **각 GREEN 직후 즉시 경계면 검증**
- asset-dev 오케스트레이터: Phase 1(도메인 전문가 팀 토론→요건서) + Phase 2(TDD RED-GREEN-VERIFY 사이클)
- CLAUDE.md 하네스 포인터 + 변경 이력 테이블 추가

---

## 2026-04-25 — 인프라 개선 + CI/CD 백테스터 연동

### 인프라 개선
- EC2 인스턴스 타입 `t3.micro`(1GB) → `t3.small`(2GB) 업그레이드 (Docker pull 시 OOM hang 방지)
- Swap 1GB → 2GB 증설 (`user_data.sh`)
- SSM `KIS_MCP_ENABLED` `false` → `true` 활성화

### CI/CD 개선
- `deploy.yml`: **Ensure Backtester MCP** 단계 추가 — 배포 전 백테스터 MCP 서버 생존 확인 + 자동 기동
- `deploy.yml`: Deploy to EC2에 `command_timeout: 5m` 추가 (무한 hang 방지)
- GitHub Secret `BACKTESTER_HOST` 추가

---

## 2026-04-25 — 전략빌더(Strategy Builder) 신규

### 전략빌더 백엔드 신규
- `services/strategy_builder_service.py`: BuilderState JSON → .kis.yaml 변환(`convert_builder_to_yaml`) + 검증(`validate_builder_state`) + YAML 요약 추출(`extract_strategy_summary`)
- `routers/backtest.py`: 6개 엔드포인트 추가 (8→15개) — `POST /strategy/convert`, `POST /strategy/validate`, `GET/POST /strategies`, `GET/DELETE /strategies/{name}`
- `db/models/backtest.py`: Strategy 모델에 `builder_state_json` 컬럼 추가
- `db/repositories/backtest_repo.py`: `get_strategy()`, `delete_strategy()` 추가, `save_strategy()`에 `builder_state_json` 파라미터
- `stock/strategy_store.py`: Strategy CRUD 래퍼 4개 추가 (`save_strategy`/`list_strategies`/`get_strategy`/`delete_strategy`)
- `services/backtest_service.py`: `run_custom_backtest`에 `strategy_display_name`, `builder_state` 파라미터 추가, `extract_strategy_summary` 연동
- `stock/symbol_map.py`: `_build_map()`에 DART corpCode fallback 추가 (pykrx 실패 시), 빈 결과 캐시 방지
- Alembic 마이그레이션: `f3a8b1c7d9e2_add_builder_state_json_to_strategies.py`
- `requirements.txt`: `pyyaml` 추가

### 전략빌더 프론트엔드 신규 (14개 파일)
- `frontend/src/components/strategy-builder/` 디렉토리 전체:
  - `strategyBuilderConstants.js` — 83개 기술지표 + 66종 캔들패턴 카탈로그, 연산자, 프리셋 6개
  - `useStrategyBuilder.js` — 빌더 상태 관리 훅
  - `StrategyBuilder.jsx` — 5단계 스테퍼 메인 컨테이너
  - `StepMetadata.jsx`/`StepIndicators.jsx`/`StepConditions.jsx`/`StepRisk.jsx`/`StepPreview.jsx` — 각 단계 UI
  - `IndicatorCard.jsx`/`IndicatorPickerModal.jsx` — 지표 카드 + 모달
  - `ConditionCard.jsx`/`ConditionGroupCard.jsx`/`OperandSelector.jsx` — 조건 빌더
  - `StrategyListPanel.jsx` — 저장된 전략 목록 + 프리셋
- `frontend/src/api/strategyBuilder.js` — 변환/검증/저장/로드/삭제 API 6개

### 프론트엔드 수정
- `StrategySelector.jsx`: "전략 빌더" 세 번째 탭 추가 (프리셋/커스텀 YAML/빌더)
- `BacktestPage.jsx`: 빌더 YAML → `runCustom` 연결, 저장 전략 직접 실행
- `BacktestHistoryTable.jsx`: builder/custom 전략은 지표+파라미터 형식으로 표시 (YAML 대신)
- `api/backtest.js`: `runCustomBacktest`에 `strategyDisplayName`, `builderState` 추가
- `hooks/useBacktest.js`: `runCustom`에 추가 파라미터 전달

### 테스트
- `tests/unit/test_strategy_builder.py` — 114개 단위 테스트 (변환/검증/연산자/리스크/프리셋/null방어/요약추출)
- `tests/api/test_backtest_api.py` — 전략빌더 API 10개 테스트 추가

## 2026-04-25 — Lean 백테스터 EC2 + 백테스트 UI 개선

### Lean 백테스터 EC2 신규
- **Terraform 모듈**: `infra/modules/backtester/` (EC2 t3.micro + EIP + IAM + 보안그룹)
- QuantConnect Lean Docker 이미지 (27.5GB) + FastAPI(8002) + Next.js(3001) + MCP(3846) 배포
- 50GB EBS + 2GB swap, `open-trading-api/backtester` 레포 clone
- stock-manager EC2 → `KIS_MCP_URL=http://<private-ip>:3846/mcp` VPC 내부 연결
- SSM Parameter Store에 `KIS_MCP_URL`, `KIS_MCP_ENABLED` 추가

### 백테스트 UI 개선
- **파라미터 슬라이더**: `StrategySelector` number input → range slider 변환 (min/max 있는 파라미터)
- **거래비용 입력**: 수수료(0.015%), 세금(0.23%), 슬리피지(0.05%) 3개 필드 추가
- **API 전체 레이어**: `commission_rate`/`tax_rate`/`slippage` 파라미터 전달 (프론트→API→서비스→MCP)
- **원화 절사**: `BacktestResultPanel` 모든 금액 `Math.floor()` 적용 (거래가격/순자산/Y축/툴팁)

## 2026-04-24 — AWS 배포 + CI/CD 구축

### AWS 인프라 신규
- **Terraform IaC**: `infra/` 디렉토리에 6개 모듈 (network, security, compute, database, ecr, secrets)
- **EC2 t3.micro** (프리티어): Amazon Linux 2023, Docker + docker-compose, 1GB swap, Elastic IP
- **RDS PostgreSQL 16**: db.t3.micro (프리티어), 프라이빗 서브넷, 자동 백업
- **ECR**: Docker 이미지 리포지토리, 최근 5개 유지 + 미태그 1일 삭제
- **SSM Parameter Store**: 15개 환경변수 SecureString 저장, 배포 시 .env 자동 생성
- **VPC**: 퍼블릭 서브넷 1개(EC2) + 프라이빗 서브넷 2개(RDS)

### CI/CD 신규
- **GitHub Actions**: `ci.yml` (모든 push: pytest + frontend build) + `deploy.yml` (main push: ECR → EC2)
- **자동 배포**: main push → Docker 빌드 → ECR 푸시 → SSH EC2 → SSM .env 생성 → docker-compose up
- **GitHub Secrets**: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, EC2_HOST, EC2_SSH_KEY

### 코드 변경
- `requirements.txt`: `psycopg2-binary` 추가 (PostgreSQL 드라이버)
- `main.py`: `/api/health` 엔드포인트 추가 (ALB/모니터링용)
- `docker-compose.prod.yml` 신규: ECR 이미지, 포트 80, 로그 로테이션
- `scripts/ec2-deploy.sh` 신규: EC2 수동 배포 스크립트
- `.gitignore`: Terraform 상태 파일 제외
- `.dockerignore`: `infra/`, `.github/` 제외

## 2026-04-20 — 시세판 카드 개선 (당일 OHLC + 전일대비 + 미니캔들)

### UI 개선
- **시세판 카드**: 현재가 + 전일대비 가격등락(+500) + 등락률% 표시
- **미니캔들**: 당일 OHLC 캔들 (양봉=빨강, 음봉=파랑) 카드 우측 배치
- **스파크라인 축소**: 카드 폭 80%, 미니캔들 20% 배분
- **당일 고가/저가**: 카드 하단에 H/L 표시
- `MiniCandleBar.jsx` 신규 컴포넌트 (CSS 기반, Recharts 불필요)

### 백엔드
- `POST /api/market-board/intraday-ohlc`: 복수 종목 당일 OHLC 배치 조회 (yfinance history, 캐시 6분/6시간)
- `_parse_execution()` 확장: H0STCNT0 t[7]=시가, t[8]=고가, t[9]=저가 추가 파싱
- WS `/ws/market-board` 전송 데이터에 change/open/high/low 필드 추가

## 2026-04-19 — 백테스트 결과 상세내역 + 파라미터 표시 수정

### 백테스트 결과 상세내역 신규
- **포지션 요약** 6카드: 평균보유기간/평균수익거래/평균손실거래/최대연승/최대연패/승패분포
- **연간 수익률** 테이블: 연도별 수익률+시작자산+종료자산
- **월별 수익률 히트맵**: 연×월 매트릭스, 6단계 색상 그라데이션(빨강=수익/파랑=손실) + 범례 + 연간 합계
- `backtestUtils.js` 순수 계산 유틸 신규 (computeAnnualReturns/computeMonthlyReturns/computePositionSummary)

### 버그 수정
- **입력 파라미터 미표시**: `params_json` lookup 누락 + 프리셋 기본값 미저장 → 기본값+사용자수정값 병합 저장
- **StrategySelector `mode` not defined**: props 구조분해에 `mode`/`onModeChange`/`yamlContent`/`onYamlChange` 누락
- **커스텀 YAML 템플릿 오류**: 잘못된 YAML 포맷 템플릿 제거, 안내 텍스트만 표시

### 백엔드 개선
- `params_json`, `strategy_display_name` 컬럼 추가 (Alembic 마이그레이션)
- MCP `param_overrides` 파라미터명 수정, YAML 검증 에러 전파 개선
- `preset_name` API 파라미터 추가 (MCP display name 저장)

### 이력 테이블 개선
- 전략명: MCP display name 우선 → STRATEGY_KR fallback
- 파라미터 펼침/접기 토글 버튼 (한글 라벨+설명 포함)
- STRATEGY_KR 매핑을 실제 MCP 10개 프리셋에 맞게 갱신

## 2026-04-19 — 백테스트 UI 추가 개선 (캔들차트 통합, 파라미터 한글화)

### UI 개선
- 수익률 곡선에 주가 캔들차트 + 거래량 바차트 오버레이 (이중 Y축: 좌=주가, 우=순자산)
- OHLCV 데이터 advisory API 별도 조회 + equity_curve 날짜 범위 자동 매칭
- 캔들차트 위 MA5/MA20 이동평균선 표시
- OHLCV 미조회 시 기존 수익률 곡선 전용 차트 fallback
- 매매 시그널: ReferenceDot → ReferenceArea 보유 구간 범위 표시 (수익=빨강/손실=파랑/보유중=회색)
- 전략 파라미터 한글명 + 비유적 설명 매핑 (PARAM_KR, 80+개)
- 파라미터 UI: 카드형 레이아웃 (한글명 + 영문키 서브텍스트 + 설명)
- 백테스트 종목 검색에서 US/FNO 제거 (SymbolSearchBar `markets` prop, 국내 KRX만 지원)
- 거래내역 날짜 KST 변환 (UTC 타임스탬프 → +9h, 날짜만이면 그대로)
- 메트릭 한글화: CAGR→연평균 수익률, Sortino→소르티노 비율, Profit Factor→손익비
- MetricsCard/추가 메트릭 각 항목 아래 간단 설명 텍스트 추가

### 개발 도구 신규
- `scripts/run-related-tests.sh` — 변경 파일에 대응하는 테스트만 자동 실행
- Claude Code postToolUse hook (Edit/Write 후 관련 pytest/npm build 자동 실행)

## 2026-04-19 — 백테스트 UI 6가지 개선

### UI 개선
- 거래 내역 Buy/Sell 색상 수정 (대소문자 무시 비교 → Buy=빨강, Sell=파랑)
- 거래 내역 날짜 표시 (date/entry_date/timestamp/time 폴백 체인)
- 매도 거래 수익률 자동 계산 (직전 매수가 대비)
- 이력 테이블 종목명 표시 (코드+이름, 백엔드 code_to_name 부착)
- 이력 테이블 한글 전략명 + 카테고리 배지 (STRATEGY_KR/STRATEGY_CATEGORY 매핑)
- 이력 삭제 기능 (DELETE /api/backtest/history/{job_id} + 프론트 삭제 버튼)
- 전략 파라미터 편집 UI (StrategySelector input + BacktestPage customParams state)
- 수익률 곡선 매매 시그널 마커 (Recharts ReferenceDot, 매수=빨간점/매도=파란점 + 범례)
- 백테스트 결과에 사용된 파라미터 표시 섹션

### 신규 API
- `DELETE /api/backtest/history/{job_id}` — 이력 삭제
- `PresetBacktestBody.params` — 전략 파라미터 오버라이드

## 2026-04-19 — 전체 기능 테스트 536개 구현

### 테스트 신규
- 단위 테스트 306개: indicators, safety_grade, macro_regime, exceptions, schemas, cache, utils
- 통합 테스트 138개: 9개 DB Repository 전체 CRUD + 엣지케이스
- API 테스트 91개: 16개 라우터 전체 엔드포인트 + WebSocket

## 2026-04-19 — 백테스트 MCP 파라미터 수정 + 비동기 2단계 + 이력 조회

### 버그 수정
- MCP 서버 `kis_devlp.yaml`에 `my_agent`/`prod`/`vps`/`ops`/`vops` 누락 → KeyError 해결
- `backtest_service.py` 파라미터 불일치 수정: `symbol`→`symbols`(배열), `preset`→`strategy_id`, `initial_cash`→`initial_capital`
- MCP 비동기 2단계 구조 적용: `run_preset_backtest_tool` → job_id → `get_backtest_result_tool(wait=true)`
- 실패 시 job 상태를 `"failed"`로 갱신 (기존: `"submitted"` 영구 잔류)
- `BacktestResultPanel` MCP 중첩 메트릭(basic/risk/trading) 자동 플래트닝 + equity_curve 오브젝트→배열 변환

### 이력 조회 신규
- `BacktestHistoryTable` 컴포넌트 신규 (일시/종목/전략/수익률/상태/보기)
- `useBacktestHistory` 훅 + `fetchBacktestHistory` API 함수 추가
- `BacktestPage`에 이력 섹션 통합 (마운트 시 로드, 완료 시 새로고침, 과거 결과 보기)
- 폴링 타임아웃 3분→10분 확장

## 2026-04-18 — MCP 백테스트 연동 + 백테스트 UX 개선

### MCP 연동
- `mcp_client.py` Streamable HTTP 세션 프로토콜 전환 (initialize → session ID → tools/call + SSE 파싱)
- Docker 내부에서 호스트 MCP 접근: `host.docker.internal` + `Host: 127.0.0.1` 헤더 고정
- `docker-compose.yml` `extra_hosts: host.docker.internal:host-gateway` 추가
- `backtest_service.py` `_extract_mcp_content()` — MCP content 구조에서 실제 데이터 추출

### 백테스트 UI 개선
- `StrategySelector`: 프리셋 선택 시 상세 설명 카드 표시 (description, category 배지, tags, params 기본값/범위)
- `BacktestPage`: 진행 현황 강화 — 단계별 메시지(전략 제출/시뮬레이션 중) + 경과 시간 카운터 + 프로그레스 바(배치)
- "다른 페이지로 이동해도 괜찮습니다" 백그라운드 실행 안내 배너 추가

## 2026-04-18 — 양도세 FIFO 엔진 전면 재설계 + 시뮬레이션

### 버그 수정 (근본)
- KIS API 연속조회(페이지네이션) 무한루프 — 요청 헤더 `tr_cont: "N"` 누락으로 동일 50건 반복. CTOS4001R+TTTS3035R 모두 수정
- FIFO 시간역행 — 매수 큐를 한꺼번에 구축하여 2025-09 매도가 2025-11 매수를 소진. **시간순 재생 방식**으로 전면 재작성 (매도 시점 이전 매수만 소진)
- FIFO lots 삭제 순서 — `delete_calculations` 후 `delete_fifo_lots` 호출 시 calc_ids가 이미 삭제됨. 순서 교정

### 양도세 엔진 개선
- 잔고 기반 적응적 동기화: 현재 보유 + 매도 역산 → 매수 충족될 때까지 과거 소급 (최대 2015년)
- CTOS4001R + TTTS3035R 병합 동기화 (fallback이 아닌 양쪽 모두 시도, 중복 자동 스킵)
- `tax_fifo_lots` 테이블 신규: 매도→매수 FIFO 매핑을 정규 테이블로 관리
- 잔고 `avg_price` fallback: 매수 내역 없지만 잔고에 있는 종목은 KIS 매입단가로 취득가 추정
- 동기화 후 자동 재계산 (stale 계산 방지)
- 환율 조회 실패 캐시 (yfinance 반복 조회 방지)

### 시뮬레이션 신규
- `POST /api/tax/simulate`: 현재 잔고 가상 매도 → 예상 양도세 (DB 저장 없음, 인메모리 FIFO)
- `GET /api/tax/simulate/holdings`: 시뮬레이션용 보유종목 목록
- TaxSimulationPanel 컴포넌트: 보유종목 선택 + 매도가/수량 입력 + 실제 vs 합산 세액 비교

### 도메인 문서
- `docs/TAX_DOMAIN.md` 신규: 양도세 규칙, FIFO 알고리즘, 잔고 역산, 환율/수수료 규칙

## 2026-04-18 — 양도세 FIFO 전용 전환 + 과거 매수 자동 탐색

### 버그 수정
- 양도세 동기화 시 과세 연도만 조회하여 과거 매수 내역 부족 발생 → 과거 5년(~2020) 자동 탐색으로 FIFO 매수풀 확보
- `sync_transactions(year)` → `_sync_single_year()` 추출, 다년도 순회 구조

### 리팩토링
- 이동평균법(AVG) 제거, FIFO 전용으로 단순화
- 백엔드 `method` 파라미터 제거 (tax_service / routers/tax.py)
- 프론트엔드 FIFO/AVG 토글 UI 제거 (TaxPage / api/tax.js / useTax.js)

## 2026-04-18 — 해외주식 양도소득세 계산 서비스 신규 + KIS API 문서

### 해외주식 양도소득세 신규
- 백엔드: `db/models/tax.py` (TaxTransaction/TaxCalculation 2 테이블) + `db/repositories/tax_repo.py` + `stock/tax_store.py` + `services/tax_service.py` + `routers/tax.py` (7개 엔드포인트)
- 환율 조회: yfinance `USDKRW=X` 연간 일괄 fetch → cache.db 영구 캐시. 주말/공휴일 직전 영업일 자동 fallback
- 데이터 수집: 3단계 KIS API 동기화 — `CTOS4001R`(일별거래내역, 환율+수수료 내장) → `TTTS3035R`(주문체결내역, 기간별) → 로컬 DB orders fallback → 수동 입력
- 양도세 계산: 선입선출법(FIFO) 기본 + 이동평균법 토글. 기본공제 250만원, 세율 22%
- 프론트엔드: `/tax` 페이지 (3탭: 요약/매매내역/계산상세), 4카드(양도차익/공제/과세표준/세액), 종목별 BarChart, 수동 추가 폼
- Header "매매" 드롭다운에 "양도세" 메뉴 추가

### KIS OpenAPI 전체 문서 기록
- `docs/KIS_API_REFERENCE.md` 전면 재작성: xlsx 338개 API → 22개 카테고리별 Markdown 테이블 (REST 278개 + WebSocket 60개)

## 2026-04-18 — 포트폴리오 자문 섹터 추천 + 뉴스 수집 품질 개선

### 포트폴리오 자문 — 신규 섹터 진입 추천
- GPT 프롬프트에 `sector_recommendations[]` JSON 스키마 + 규칙 29-32 추가
- 체제별 신규 섹터 한도: accumulation=3-5개, selective=2-3개, cautious=1개, defensive=금지
- `_get_macro_news_context()`: 한국 5개 + 해외 3개 뉴스 헤드라인을 GPT 컨텍스트에 주입
- `_REGIME_VALUATION_LIMITS`: 체제별 PER/PBR 한도 매핑 (규칙 31에서 참조)
- `SectorRecommendationCard.jsx` 신규: 섹터명+목표비중+타이밍 배지+대표종목→DetailPage 링크
- `AdvisorPanel.jsx`: DiagnosisCard와 RebalanceCard 사이에 SectorRecommendationCard 배치

### 뉴스 수집 품질 개선
- 한국 뉴스: 단일 검색어 → Google News **비즈니스 토픽 RSS**(편집 큐레이션) + `증시+금리+환율` 2개 소스 병합
- 해외 뉴스: NYT만 → NYT + Google News US 비즈니스 토픽 2개 소스 병합
- `_dedup_and_sort()` 신규: 제목 앞 30자 기반 중복 제거 + `published_ts` 최신순 정렬
- `_parse_published_ts()` 신규: RFC 2822 날짜 → Unix timestamp 파싱
- `_parse_rss()`: `published_ts` 필드 추가 (정렬 기준)
- `fetch_investor_news()`: 여유있게 수집 후 `_dedup_and_sort()` 적용
- `macro_service.py`: `source` 필드 NYT 하드코딩 → 동적 반영

### UI 개선
- `DiagnosisCard.jsx`: 섹터명 잘림 수정 (`w-20` → `w-28 shrink-0` + `title` 속성)

## 2026-04-17 — KIS AI Extensions 백테스트 연동 + 267260 가격 버그 수정

### 버그 수정
- `_kr_yf_ticker_str()` score 기준 강화: `best_score = -1` → `0` (score ≥ 1 필수, mktcap 또는 shares 존재해야 유효 suffix)
- 267260(HD현대일렉트릭) `.KQ` 잘못 캐시되어 307,000원 표시 → `.KS` 정상 선택으로 1,087,000원 복구
- `market_cap > 0`, `shares > 0` 양수 검증 추가
- `best_score >= 2` 시 조기 중단 (불필요한 suffix 추가 시도 방지)

## 2026-04-17 — KIS AI Extensions 백테스트 연동

### 백테스트 기능 신규
- KIS AI Extensions MCP 서버 연동 (`services/mcp_client.py` — httpx JSON-RPC 클라이언트)
- 백테스트 서비스 (`services/backtest_service.py` — 프리셋/커스텀/배치 실행, 전략 신호 생성)
- 백테스트 API (`routers/backtest.py` — 7개 엔드포인트: status/presets/indicators/run/result/history)
- DB 모델 (`db/models/backtest.py` — BacktestJob, Strategy) + Alembic 마이그레이션
- Store 래퍼 (`stock/strategy_store.py` — db/repositories/backtest_repo.py 위임)
- 환경변수 `KIS_MCP_URL`, `KIS_MCP_ENABLED` 추가 (기본 비활성화)
- httpx 의존성 추가

### AI 자문 전략 신호 통합
- `advisory_service.py`: `_collect_strategy_signals()` — MCP 대표 3전략 신호 병렬 수집
- `_build_strategy_signal_section()` — GPT 프롬프트에 전략 신호/백테스트 메트릭 섹션 추가
- System Prompt에 "전략 4: KIS 퀀트 전략 신호 (보조 지표)" 규칙 추가
- `advisory_store.save_cache()` + `advisory_cache` 테이블에 `strategy_signals` JSON 컬럼
- MCP 비활성화 시 기존 자문 시스템 100% 동작 (zero degradation)

### 포트폴리오 자문 연동
- `portfolio_advisor_service.py`: 각 holding에 `backtest_metrics` 필드 추가

### 프론트엔드 신규
- BacktestPage (`/backtest`) — 종목 선택 + 전략 선택(프리셋/YAML) + 기간/금액 + 실행 + 결과 차트
- components/backtest/ (StrategySelector, MetricsCard, BacktestResultPanel, BatchCompareTable)
- api/backtest.js + hooks/useBacktest.js (3초 폴링, 타임아웃 3분)
- Header 분석 드롭다운에 "백테스트" 메뉴 추가
- TechnicalPanel에 KIS 전략 신호 카드 (MCP 활성화 시만 표시)

---

## 2026-04-17 — AI자문 개선 (입력/프롬프트/출력 3축 개편)

### Phase 1: 프롬프트 보강 + 개별↔포트폴리오 연계
- `services/macro_regime.py` 신규: 공용 체제 판단 모듈 (REGIME_MATRIX 20셀 + VIX>35 오버라이드 + 하이스테리시스 ±5). 3개 서비스(advisory/portfolio_advisor/pipeline) 통합
- System Prompt에 도메인 에이전트 규칙 삽입: MarginAnalyst 7점 등급표, MacroSentinel 매트릭스, OrderAdvisor 등급별 손절폭(A=-8%/B+=-10%/B=-12%), ValueScreener Value Trap 5규칙
- User Prompt에 Forward 추정치 섹션 추가 (기존 수집 데이터 활용)
- 포트폴리오 자문에 개별 AI 리포트 연계 (각 보유 종목의 등급/요약/할인율/리스크 주입)
- 52주 고가 6시간 캐시 도입 (`advisor:52w:{market}:{code}`)

### Phase 2: 데이터 보강 + 정량 필드
- `services/safety_grade.py` 신규: 7점 등급(`compute_grade_7point`) + 복합점수(`compute_composite_score`) + 체제정합성(`compute_regime_alignment`) + 포지션사이징(`compute_position_sizing`)
- `stock/indicators.py`: `volume_signal`(거래량/5일평균 비율), `bb_position`(BB밴드 내 위치 0~100) 추가
- `stock/advisory_fetcher.py`: `fetch_valuation_stats()` 신규 (PER/PBR 5년 평균/최대/최소/편차%)
- `stock/dart_fin.py`: `fetch_quarterly_financials()` 신규 (DART 누계→분기 환산, 최근 4분기)
- `stock/yf_client.py`: `fetch_quarterly_financials_yf()` 신규 (yfinance 분기 실적)
- User Prompt +4섹션: PER/PBR 5년 비교, 분기 실적, 거래량·BB 신호, 7점 등급 사전 계산값
- v2 JSON 스키마: `schema_version`/`종목등급`(A~D)/`등급점수`(0-28)/`복합점수`(0-100)/`체제정합성점수`(0-100)/`Value_Trap_경고`/`등급팩터`/`recommendation`(ENTER/HOLD/SKIP)
- 포트폴리오 가중 등급 집계(`portfolio_grade_weighted_avg`) + 등급 분포 + 체제 정합성 점수

### Phase 3: DB 스키마 + Pydantic + UI
- `db/models/advisory.py`: AdvisoryReport +6컬럼(grade/grade_score/composite_score/regime_alignment/schema_version/value_trap_warning), PortfolioReport +3컬럼(weighted_grade_avg/regime/schema_version). 모두 nullable=True
- Alembic 마이그레이션 `2e051b80939e_add_advisory_grade_fields.py`
- `services/schemas/advisory_report_v2.py` 신규: Pydantic v2 스키마 검증 (11개 모델, validate/extract)
- 재시도 로직: max_tokens 10000→12000, 토큰 잘림/Pydantic 실패/일반 에러 각 1회 재시도. 2차 실패 시 저장 거부
- `AIReportPanel.jsx`: v2 등급 카드 (SafetyGradeBadge + ScoreBar + Value Trap 배너 + recommendation). v1 리포트 시 카드 숨김
- `AdvisorPanel.jsx`: 개별 종목 리포트 연계 요약 카드 (가중 등급 + 분포 바 + B미만 경고). weighted_grade_avg 부재 시 숨김
- npm run build 성공 (779 modules)

### QA 결과
- 45 PASS / 0 MAJOR / 4 MINOR
- 3중 일관성 확인: System Prompt(문자) = safety_grade.py(코드) = Pydantic(타입)
- E2E API 호출 성공: 삼성전자 v2 등급=B+, 등급점수=20, recommendation=SKIP (defensive 체제)

## 2026-04-15 — db/ 패키지 구조 리팩토링

### 리팩토링
- `db/utils.py` 신규: KST 타임존 헬퍼(`KST`, `now_kst`, `now_kst_iso`) 정의 원본. db/repositories/에서 직접 import하여 db/→stock/ 역방향 의존 해소
- `stock/db_base.py`: 자체 정의 제거 → `db/utils.py`에서 re-export (기존 caller 호환)
- `stock/report_store.py` 신규: 보고서 CRUD 래퍼 (다른 6개 store와 동일 패턴 통일)
- `services/report_service.py`: `db: Session` 파라미터 제거 → `stock/report_store.py` 경유
- `routers/report.py`: `Depends(get_db)` 제거 → 서비스 직접 호출
- `services/pipeline_service.py`: `get_session()` 직접 사용 제거 → 서비스 경유
- `db/repositories/stock_info_repo.py`: `batch_get()` N+1 → `or_(and_(...))` 단일 쿼리
- `db/repositories/stock_info_repo.py`: upsert 에러 로깅 `debug` → `warning`
- `db/repositories/macro_repo.py`: `get_today()` 내 5% 확률 cleanup → `cleanup_old()` 별도 메서드 분리
- Alembic 마이그레이션: orders/reservations 테이블 `server_default` 추가
- Reservation 모델: `status`, `market`, `memo`에 `server_default` 추가

## 2026-04-13 — 투자 파이프라인 서비스 + 스케줄러

### 투자 파이프라인 신규
- `services/pipeline_service.py`: 매크로 체제 판단(REGIME_MATRIX) → 체제별 스크리닝 → 심층 분석(7점 등급) → 추천 생성 → 보고서 저장
- 체제 판단: 버핏지수×공포탐욕 교차표, VIX>35 오버라이드, 버핏지수 백분율→소수 자동 변환
- 7점 등급: Graham 할인율/PER평균비교/PBR절대/부채비율/유동비율/FCF추세/매출CAGR (28점 만점 A~D)
- 추천 생성: B+ 이상 + 안전마진 임계값 초과 + R:R≥2.0 필터
- `services/scheduler_service.py`: APScheduler BackgroundScheduler (08:00 KR / 16:00 US KST)
- `routers/pipeline.py`: POST /run (비동기), POST /run-sync (동기), GET /status
- ReportPage에 KR/US 분석 실행 버튼 + 스케줄러 상태 + 실행 결과 표시 추가
- `apscheduler` 의존성 추가

## 2026-04-13 — 하네스 재구성 + 보고서 시스템 + 테스트 인프라

### 하네스 재구성
- 대화형 투자 스킬 6개 삭제 (macro-analysis, value-screening, graham-analysis, portfolio-check, order-recommend, value-invest)
- 도메인 에이전트 4명(MacroSentinel/ValueScreener/MarginAnalyst/OrderAdvisor) → **자문 전용**으로 전환 (API 호출 제거)
- DevArchitect 역할 확대: 투자 자동화 시스템 전체 개발 (파이프라인/스케줄러/Telegram)
- TestEngineer 에이전트 신규 추가 (pytest 기반 자동화 테스트 전담)
- asset-dev 스킬 범위 확장 (파이프라인/스케줄러/Telegram 개발 포함)
- qa-verify 스킬에 파이프라인 로직 검증 항목 추가

### 보고서 시스템 신규
- DB 모델 3개: RecommendationHistory, MacroRegimeHistory, DailyReport + ReportRepository
- Alembic 마이그레이션 (테이블 3개 + 인덱스 5개)
- `services/report_service.py`: 추천 이력/체제 이력/보고서 CRUD + 통합 Markdown 생성 + 성과 통계
- `routers/report.py`: 7개 GET 엔드포인트 (`/api/reports/*`)
- `frontend/src/pages/ReportPage.jsx`: 3탭 UI (일일 보고서/추천 이력/성과 통계)
- Header 분석 드롭다운에 "보고서" 메뉴 추가

### 테스트 인프라 신규
- `tests/` 디렉토리: conftest.py(인메모리 DB + TestClient) + unit/integration/api 3계층
- 27개 테스트: 단위 7개(Markdown 생성, is_domestic) + 통합 11개(Repository CRUD) + API 9개(엔드포인트)
- pytest + pytest-asyncio 의존성 추가

## 2026-04-04 — 역발상 매수 전략 + 밸류에이션 차트 확장 + UI 개선

### 프롬프트 개선
- 포트폴리오 AI자문: cautious/selective 체제에서 역발상 매수 규칙 10개 추가 (규칙 19~28)
- 역발상 매수 5대 적격 조건 (52주 -30%+, PBR<1.0, 부채비율<100%, 영업이익 흑자, FCF 양수)
- 보유종목 vs 신규종목 판단 분리, 포지션 한도 (cautious 1.5%/7.5%)
- 포트폴리오 자문 컨텍스트에 종목별 52주 고가·하락률 추가

### 신규 기능
- 스크리너 API: `drop_from_high` 쿼리 파라미터 추가 (52주 고점 대비 하락률 필터)
- 스크리너 enrichment: `high_52`, `low_52`, `drop_from_high` 필드 추가
- FilterPanel: "52주 고점 대비 (%)" 입력 필드 추가

### UI 개선
- 메뉴바 순서 변경: 시세판→관심종목→분석▼→포트폴리오→매매▼, 그룹 구분선 3개
- ValuationChart: 시가총액 추이(보라) + 발행주식수 추이(주황) 차트 추가
- 발행주식수: 분기별 시계열 반영 (자사주 소각 등 변동 추적)

### 버그 수정
- EPS fallback: DART EPS 미제공 종목(SK하이닉스 등)에서 net_income/shares로 직접 계산
- PBR fallback: yfinance priceToBook None 시 대차대조표 자본총계/주식수로 계산 (골프존 등)
- yf_client: tz-aware/tz-naive 비교 버그 수정 (밸류에이션 히스토리 빈 배열 반환)
- KRX 경로: pykrx 빈 결과 시 yfinance fallback 전환
- fetch_market_metrics: high_52/low_52 필드 추가

### UI 개선 (자동완성)
- AddStockForm에 자동완성 검색 추가 (KR: 400ms debounce + 드롭다운, US: 티커 직접 입력)
- 기존 searchStocks API 재사용, 외부 클릭 닫기, 시장 변경 시 상태 초기화

## 2026-04-04 — SQLAlchemy ORM 마이그레이션

### 리팩토링
- SQLite 직접 접근 → SQLAlchemy ORM 전환 (6개 비즈니스 DB → 단일 `app.db` 통합)
- `db/` 패키지 신규: `base.py`(DeclarativeBase) + `session.py`(Engine/Session) + `models/`(12개 모델) + `repositories/`(6개 Repository)
- 기존 6개 store 모듈(`store.py`, `order_store.py` 등)은 Repository 위임 래퍼로 전환 (함수 시그니처 100% 유지)
- Alembic 마이그레이션 도입 (`alembic/`): 스키마 버전 관리, `render_as_batch=True` (SQLite 호환)
- `config.py`에 `DATABASE_URL` 환경변수 추가 (기본값: SQLite, PostgreSQL/Oracle 전환 가능)
- `main.py` lifespan + `entrypoint.sh`에서 `alembic upgrade head` 자동 실행
- `scripts/migrate_sqlite_data.py` 신규: 기존 6개 DB → app.db 데이터 이관 스크립트
- cache.db, screener_cache.db는 raw SQLite 유지 (ORM 이점 없는 TTL 캐시)
- services/, routers/, frontend/ 변경 없음

## 2026-04-04 — 계량지표 확장 + 포워드차트 + 매출추정 개선

### 기본적분석 개선
- 계량지표 8개→10개 확장: EPS + 안전마진가격(Graham Number) 추가 (MarginAnalyst 자문)
- MetricCard integer prop: 부채/자본, 유동비율, EPS, 안전마진가격 소수점 제거
- 프론트엔드 "Graham" 표기 → "안전마진/안전마진가격"으로 통일 (백엔드 키명 유지)
- ForwardEstimatesSection: 매출/순이익 현재E+차기E sub 텍스트 추가
- IncomeChart: 추정치 연도(xxE) 반투명 바 추가 (매출E+순이익E, opacity 0.35)

### 버그 수정
- fetch_market_metrics()에 shares 필드 누락 → Graham Number 계산 불가 수정
- 매출 추정치 수집 3단계 fallback: revenue_estimate(신API) → analysis(레거시) → totalRevenue×growth

## 2026-04-04 — 성능 최적화 리팩토링 (DB 캐시 + 병렬화)

### 성능 최적화
- `stock/stock_info_store.py` 신규: 종목 정보 영속 캐시 DB (`stock_info.db`). Docker 재시작에도 유지
- `watchlist_service.py`: stock_info DB 우선 조회 → stale 영역만 외부 API 호출 (대시보드 응답 속도 개선)
- `advisory_service.py`: `_collect_fundamental_kr/us` 5~6개 데이터 소스 ThreadPoolExecutor 병렬 수집
- `advisory_fetcher.py`: KIS 1분봉 4시간대 순차→병렬 수집 (최악 80초→20초)
- `macro_service.py`: sparkline 병렬 결과 미사용 버그 수정 (결과 버려지고 순차 재호출되던 문제)
- `dart_fin.py`: 재무 캐시 TTL 24시간→7일(168시간) 확장 (사업보고서 분기 변동 주기에 맞춤)
- `market.py`/`yf_client.py`: write-through 패턴으로 stock_info DB에 시세/지표/재무 자동 저장

### DB 인덱스 추가
- `order_store.py`: orders 테이블에 status, order_no+market, symbol+market 인덱스 3개 추가
- `advisory_store.py`: advisory_reports 테이블에 code+market+generated_at 인덱스 추가

### 프론트엔드 최적화
- `OrderPage.jsx`: 탭/마켓 전환 useEffect 분리 — market 변경 시 현재 활성 탭만 리로드

## 2026-04-04 — 메뉴바 드롭다운 + 대시보드 재설계 + doc-commit 스킬

### UI 개선
- Header.jsx: 9개 평면 메뉴 → 5개 드롭다운 (포트폴리오|분석▼(매크로/스크리너/공시)|관심종목|매매▼(주문/잔고)|시세판)
- 드롭다운 hover 영역: `mt-1` gap → `pt-1` 투명 패딩으로 마우스 이탈 방지
- DashboardPage.jsx: 포트폴리오 요약(체제배너+자산현황+배분차트) + 오늘 공시로 재설계

### 스킬 신규
- `.claude/skills/doc-commit/`: 문서 반영 + 커밋 + compact 자동화 스킬

---

## 2026-04-04 — AI자문 프롬프트 고도화 + 포트폴리오 통합 + 버그 수정

### AI자문 프롬프트 고도화 (도메인 전문가 3명 자문)
- `advisory_service.py` 시스템 프롬프트: 재무 건전성 체크리스트, 적자 기업 규칙, PBR 역산 한계, 업종 상대평가, 체제별 투자 원칙 동적 삽입
- `advisory_service.py` 유저 프롬프트: `## 매크로 환경` 섹션 추가 (VIX/버핏/공포탐욕/체제/요구 안전마진)
- `advisory_service.py` 출력: `포지션가이드` 섹션 추가 (진입가/손절가/익절가/R:R/분할매수)
- `portfolio_advisor_service.py`: `_SYSTEM_PROMPT` → `_build_system_prompt(regime, cash_pct)` 함수화
  - 포지션 사이징 규칙 (단일 5%, 1회 30%, 현금 체제별), 손실 종목 3단계, urgency 3단계
  - 체제별 현금 비중 동적 삽입 (accumulation 25%/selective 35%/cautious 50%/defensive 75%)
  - trades JSON 확장: stop_loss, position_pct, urgency_reason
- `AIReportPanel.jsx`: 포지션가이드 4카드 섹션 (PosGuideCard 컴포넌트)
- `TradeTable.jsx`: 손절가/비중/긴급도 근거 컬럼 추가 (하위 호환)

### "AI자문" + "포트폴리오" 메뉴 통합
- `PortfolioPage.jsx` 재작성: 매크로 배너 + 자산 요약 + 차트 + AdvisorPanel(진단+리밸런싱+매매안) 통합
- `AdvisorPage.jsx` 라우트 제거 (App.jsx, Header.jsx)
- `BalancePage.jsx`: AdvisorPanel 제거 → "포트폴리오에서 AI 자문 보기 →" 링크
- Header: "AI자문" 메뉴 제거 (9개 메뉴)

### usePortfolioAdvisor 훅 재설계 (stale closure 버그 수정)
- `loadHistory()`: `[result]` 의존성 제거 → 이력 목록만 가져옴 (자동 리포트 로드 제거)
- `loadLatest()`: 마운트 시 최신 리포트 자동 로드 (신규)
- `analyze()`: `setResult(res)` 후 `loadHistory()` fire-and-forget (await 제거, 덮어쓰기 방지)

### max_completion_tokens 부족 버그 수정
- `advisory_service.py` + `portfolio_advisor_service.py`: 3500 → 8000
- 토큰 제한 잘림 감지 (`finish_reason == "length"` 로깅)
- JSON 파싱 실패 시 `ExternalAPIError` 반환 (빈 화면 대신 에러 메시지)
- `AdvisorPanel.jsx`: `analysis.raw` 존재 시 "다시 시도" 안내 표시

### 기타 버그 수정
- `cache.py`: aware/naive datetime 비교 TypeError → `.replace(tzinfo=None)` 통일
- `RegimeBanner.jsx`: `sentiment.buffett` → `sentiment.buffett_indicator` 필드명 수정
- `RegimeBanner.jsx`: `fg?.value` → `fg?.score` 우선 (실제 백엔드 필드)
- `TradeTable.jsx`: 매매근거 `truncate` 제거 → `whitespace-pre-line` 전체 표시
- `AdvisorPanel.jsx`: 링크 `/advisor` → `/portfolio`

---

## 2026-04-03 — 포트폴리오 대시보드

### 포트폴리오 대시보드 (`/portfolio`) 신규
- `PortfolioPage.jsx` — 5개 섹션 대시보드 (매크로 배너 + 자산 요약 + 배분 차트 + 수익률 바 + 보유종목)
- `usePortfolio.js` — balance + macro sentiment 병렬 로드 + Graham 안전마진 등급 프론트 계산
- `RegimeBanner.jsx` — 공포탐욕지수 기반 매크로 체제 배너 (공포/신중/중립/탐욕 4단계)
- `AllocationChart.jsx` — Recharts PieChart 자산 배분 (국내/해외/현금)
- `ProfitChart.jsx` — Recharts BarChart 종목별 수익률 비교
- `HoldingsOverview.jsx` — 보유 종목 테이블 + 안전마진 등급(A~D) + PER/PBR/ROE
- 신규 백엔드 없음 — 기존 `/api/balance` + `/api/macro/sentiment` API 100% 재활용
- Header 메뉴 추가 (10개)

---

## 2026-04-03 — AI 포트폴리오 자문 + 인프라 개선

### AI 포트폴리오 자문 기능 신규
- `services/portfolio_advisor_service.py` — 잔고 데이터 기반 GPT 포트폴리오 분석 (진단/리밸런싱/매매안)
- `routers/portfolio_advisor.py` — `POST /analyze`, `GET /history`, `GET /history/{id}` 3개 엔드포인트
- `stock/advisory_store.py` — `portfolio_reports` 테이블 추가 (자문 이력 영구 저장)
- `config.py` — `ADVISOR_CACHE_TTL_HOURS` 환경변수 (기본 0.5=30분)
- `stock/cache.py` — `ttl_hours` 타입 `int → float` (30분 TTL 지원)
- 프론트엔드: `AdvisorPage`(/advisor) + `AdvisorPanel`/`DiagnosisCard`/`RebalanceCard`/`TradeTable`/`TradeConfirmModal` 5개 컴포넌트
- `BalancePage` 하단에 AdvisorPanel 통합 + "AI자문 페이지에서 이력 보기" 링크
- 페이지 진입 시 최신 리포트 자동 로드 (이력 있으면 버튼 클릭 불필요)
- Header에 "AI자문" 메뉴 추가 (9개 메뉴)

### KST 타임존 통일
- `stock/db_base.py` — `KST`, `now_kst()`, `now_kst_iso()` 공용 헬퍼 신규
- `stock/cache.py` — `datetime.utcnow()` → `now_kst()` (캐시 만료 비교/저장)
- `stock/order_store.py` — `_now()` → `now_kst_iso()`
- `stock/advisory_store.py` — `datetime.now()` 4곳 → `now_kst_iso()`
- `stock/macro_store.py` — 자체 `_KST` 상수 제거, `db_base.KST` 공용 사용
- `services/macro_service.py` — `datetime.now(timezone.utc)` → `now_kst_iso()`
- `services/portfolio_advisor_service.py` — `datetime.now()` → `now_kst_iso()`
- 프론트: `EarningsPage`/`WatchlistDashboard` — `.toISOString()` → 로컬 날짜 헬퍼

### 관심종목 대시보드 속도 개선
- `services/watchlist_service.py` — 순차 for 루프 → `ThreadPoolExecutor` 병렬 (max 10 workers)
- `_fetch_dashboard_row()` 함수 추출, `time.sleep(0.05)` 제거
- 10종목 기준 12-30초 → 2-4초로 단축

### 기타
- `TradeTable` 매매근거 텍스트 잘림 수정 (`truncate` → `whitespace-pre-line`)
- `AdvisorPage` 불필요한 "잔고 새로고침" 버튼 제거

---

## 2026-04-03 — 시스템 리팩토링

### 시스템 리팩토링 (2026-04-03)

**HIGH (5건)**
- H1: `search.js`/`marketBoard.js` → `apiFetch()` 경유로 에러 처리 통일
- H2: `useAsyncState` 공통 훅 추출, 15개 훅 보일러플레이트 제거
- H3: `order_service.py`(1,338줄) → 4파일 분할 (order_service + order_kr/us/fno). Write-Ahead 패턴 dispatcher 중앙화
- H4: `quote_service.py`(964줄) → 3파일 분할 (quote_service + quote_kis + quote_overseas)
- H5: KIS 토큰 캐시 3곳 → `_kis_auth.py` 단일화 + TTL 관리

**MEDIUM (3건)**
- M2: `watchlist_service.py` silent `except: pass` 7건 → `logger.debug` 전환
- M5: 라우터 HTTPException 22건 → ServiceError 계층 통일. `ConflictError(409)` 신규
- M6: `advisory_fetcher.py` 기술지표 8개 순수 함수 → `stock/indicators.py` 분리

**LOW (1건)**
- L4: 미사용 import 정리 (Optional, math 등)

---

## 2026-04-03 — AI 에이전트 팀 (하네스) 구성

### 에이전트 7명 (`.claude/agents/`)

**도메인 전문가 4명:**
- `macro-sentinel.md` — 매크로 환경 분석 (버핏지수/VIX/공포탐욕 → 시장 체제 판단)
- `value-screener.md` — Graham 기준 PER/PBR/ROE 동적 필터 스크리닝
- `margin-analyst.md` — Graham Number + 재무 건전성 + 기술적 타이밍 심층 분석
- `order-advisor.md` — 포지션 사이징 + 지정가/손절/익절 주문 추천 (자동 주문 금지)

**빌더 3명:**
- `dev-architect.md` — 통합자산관리 풀스택 개발 (도메인 전문가 자문 기반)
- `qa-inspector.md` — 경계면 교차 비교 통합 정합성 검증
- `refactor-engineer.md` — 도메인 인지 리팩토링 (도메인 전문가 확인 후 변경)

### 스킬 9개 (`.claude/skills/`)
- `macro-analysis/` — MacroSentinel 전용: 매크로 데이터 수집 + 체제 판단
- `value-screening/` — ValueScreener 전용: Graham 멀티팩터 스크리닝
- `graham-analysis/` — MarginAnalyst 전용: 내재가치 + 재무 건전성 + 기술적 분석
- `portfolio-check/` — OrderAdvisor 전용: 포트폴리오 상태 + 포지션 사이징
- `order-recommend/` — OrderAdvisor 전용: 주문 추천 생성 + 예약주문 보조
- `value-invest/` — 오케스트레이터: 분석 파이프라인 (Macro→Screener→Analyst→Advisor)
- `asset-dev/` — 오케스트레이터: 개발 파이프라인 (자문→설계→구현→QA→보고)
- `qa-verify/` — QA Inspector 전용: 교차 비교 검증 체크리스트
- `refactor-audit/` — 오케스트레이터: 리팩토링 파이프라인 (감사→자문→실행→QA)

### 특징
- 기존 서비스 코드 변경 없음 — 에이전트는 기존 API 엔드포인트를 HTTP로 호출
- 도메인 전문가 4명이 분석/개발/리팩토링 3개 파이프라인 모두에서 자문 역할
- 워크스페이스 산출물: `_workspace/` 디렉토리에 단계별 JSON 파일 저장

---

## 2026-04-01 — 매크로 분석 페이지 신규

### 매크로 분석 (Macro Analysis) 메뉴 추가
- `stock/macro_fetcher.py`: yfinance 지수(KOSPI/KOSDAQ/S&P500/NASDAQ), RSS 뉴스, VIX/버핏지수/공포탐욕 심리지표, Google News 투자자 코멘트
- `services/macro_service.py`: 병렬 수집(ThreadPoolExecutor) + GPT 번역/추출 + 캐싱 오케스트레이션
- `routers/macro.py`: 5개 GET 엔드포인트 (`/api/macro/indices|news|sentiment|investor-quotes|summary`)
- `main.py`: macro 라우터 등록
- `requirements.txt`: `feedparser` 추가 (RSS 파싱)
- 프론트엔드: MacroPage + IndexSection(1년 스파크라인+툴팁) + SentimentSection + NewsSection + InvestorSection
- 데이터 소스: yfinance(지수/VIX/버핏), Google News RSS(한국 뉴스), NYT RSS + GPT 번역, Google News + GPT 추출(투자자 코멘트)
- 새 API 키 불필요 (기존 OPENAI_API_KEY만 활용, 없으면 영문 표시 graceful degradation)

---

## 2026-03-30 — FNO 캐싱 + 예약주문 수정 + DnD 순서변경

### FNO 마스터 인메모리 캐싱
- `stock/fno_master.py`: 인메모리 캐시(24h TTL) → cache.db(7일) → ZIP 다운로드 3단계 캐싱
- `main.py` lifespan: FNO pre-warm 추가 (기존 symbol_map 스레드에 병합)

### 예약주문 국내 시세 버그 수정
- `services/reservation_service.py`: `_fetch_current_price()` pykrx → `stock.market.fetch_price()` 교체
- pykrx KRX 서버 변경(2026-02-27) 이후 국내 가격조건 예약주문이 실패하던 문제 해결

### 시세판 드래그앤드롭 순서 변경
- `stock/market_board_store.py`: `market_board_order` 테이블 + `get_order()`/`save_order()`
- `routers/market_board.py`: `GET/PUT /api/market-board/order`
- 프론트엔드: `@dnd-kit/core` + `@dnd-kit/sortable` — 카드 그리드 DnD (`rectSortingStrategy`)
- `useDisplayStocks()`: orderMap 기반 정렬 + `reorder()` 낙관적 업데이트

### 관심종목 드래그앤드롭 순서 변경
- `stock/store.py`: `watchlist_order` 테이블 + `get_order()`/`save_order()`
- `routers/watchlist.py`: `GET/PUT /api/watchlist/order`
- 프론트엔드: 테이블 행 DnD (`verticalListSortingStrategy`) + 드래그 핸들(⠿)
- `useDashboard()`: orderMap 기반 정렬 + `reorder()` 낙관적 업데이트

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

---

## 버그 수정

### DART 공시 캐시 버그 수정 (2026-03)
- **원인**: `screener/cache.py`는 TTL 없는 영구 캐시. 당일 오전 조회 시 빈 결과가 캐시되면 이후 제출 공시가 보이지 않음 (골프존 3/19 사업보고서 미노출 사례)
- **수정**: `screener/dart.py`의 `fetch_filings()`에서 `end_date < today`인 경우만 캐시 사용. 오늘 이상 날짜 포함 범위는 항상 DART API 직접 호출.
