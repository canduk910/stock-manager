# Step 1~3 RED 산출

## Step 1 — REQ-WS-01 RED

**파일**: `tests/unit/test_quote_overseas_kis_ws_orderbook.py` (신규, 290 lines)

**테스트 6건**:
1. `test_ws_connected_subscribe_does_not_start_rest_orderbook_poller` — WS 연결 정상 시 토픽 등록 + REST 폴러 미시작
2. `test_ws_message_broadcasts_orderbook_with_correct_shape` — WS 메시지 도달 → broadcast shape 보존
3. `test_ws_disconnect_starts_rest_orderbook_polling_for_all_subs` — WS 끊김 → 모든 구독 종목 REST 폴링 자동 시작
4. `test_ws_reconnect_stops_rest_orderbook_polling` — 재연결 → REST 폴러 자동 중단
5. `test_ws_construction_failure_falls_back_to_rest_polling` — `KISOverseasOrderbookWS()` 생성 실패 → REST 폴백
6. `test_ws_start_failure_falls_back_to_rest_polling` — `start()` 예외 → REST 폴백

**RED 결과**: 6/6 FAIL — `services.quote_overseas` 모듈에 `KISOverseasOrderbookWS` 미정의 (`AttributeError`).

## Step 2 — REQ-FE-02 RED

**파일**: `tests/unit/test_us_market_clock_holidays.py` (신규, 75 lines)

**테스트 4건** (Vitest 미설정 환경 — 정적 검증):
1. `test_hook_exposes_us_holidays_constant` — `US_HOLIDAYS_ET` 상수 정의
2. `test_hook_holiday_list_includes_2026_core_dates` — 2026 핵심 10일 포함
3. `test_hook_holiday_list_includes_2027_2028_years` — 2027/2028 핵심일 포함
4. `test_resolve_phase_by_clock_handles_holiday_branch` — `resolveUsPhaseByClock`에 공휴일 분기

**RED 결과**: 4/4 FAIL.

## Step 3 — REQ-INT-03 RED

**파일**: `tests/integration/test_kis_overseas_live.py` (신규, 145 lines)
**파일**: `pytest.ini` (live 마커 추가)

**테스트 3건**:
1. `test_live_kis_orderbook_rest_aapl_returns_non_empty_levels` — HHDFS76200100 응답 검증
2. `test_live_kis_price_detail_rest_aapl_returns_full_fields` — HHDFS76200200 응답 검증
3. `test_live_kis_ws_orderbook_aapl_receives_message_within_5s` — HDFSASP0 WS 메시지 5s 수신 검증

**RED 결과**: CI 환경에서는 `KIS_LIVE_TEST` 미설정 → 3/3 SKIP (회귀 0). 실 키로는 실제 검증.
