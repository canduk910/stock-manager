# QA Inspector 경계면 교차 비교 리포트

**검증 대상**: REQ-WS-01 / REQ-FE-02 / REQ-INT-03 (해외매매 후속 3건)
**검증 일시**: 2026-05-09
**회귀 베이스라인**: 단위 839 PASS / 신규 후 849 PASS

---

## 1. 경계면 매트릭스

### A. WS → Manager → 프론트 broadcast 경계

| 항목 | 기대 | 검증 결과 |
|------|------|----------|
| broadcast shape 키 | `{type:"orderbook", symbol, asks, bids, total_ask_volume, total_bid_volume}` | OK — `_on_kis_orderbook_ws_message`에서 동일 5키 |
| asks/bids 항목 형식 | `[{price: float, volume: int}]` | OK — `wrapper.parse_overseas_orderbook` 결과 그대로 전달 |
| 프론트 `useQuote.js` 영향 | 0건 (REST 폴링 broadcast와 동일) | OK — 기존 형식 100% 보존 |
| 가격(price) 채널 영향 | 0건 (호가 채널만 신규) | OK — `_poll_loop`/`_on_finnhub_trade` 미터치 |

### B. WS 우선 / REST 폴백 자동화 경계

| 시나리오 | 기대 동작 | 검증 결과 |
|---------|----------|----------|
| WS 정상 + subscribe | WS 토픽 등록, REST 폴러 미시작 | OK (test_ws_connected_subscribe_does_not_start_rest_orderbook_poller) |
| WS 메시지 도달 | 해당 종목 REST 폴러 cancel | OK — `_orderbook_pollers.pop+cancel` |
| WS 끊김 (`on_disconnect`) | 모든 구독 종목 REST 폴러 자동 시작 | OK (test_ws_disconnect_starts_rest_orderbook_polling_for_all_subs) |
| WS 재연결 (`on_reconnect`) | 토픽 재등록 + REST 폴러 cancel | OK (test_ws_reconnect_stops_rest_orderbook_polling) |
| 생성 자체 실패 (KIS 키 부재) | `_kis_ob_ws=None`, REST 즉시 폴백 | OK (test_ws_construction_failure_falls_back_to_rest_polling) |
| `start()` 예외 | `_kis_ob_ws=None`, REST 즉시 폴백 | OK (test_ws_start_failure_falls_back_to_rest_polling) |

### C. 인증 / 토픽 / 파서 재사용 경계

| 항목 | 기대 | 결과 |
|------|------|------|
| 토큰/approval 발급 | `routers/_kis_auth.get_kis_credentials(None)` 재사용 | OK — `_issue_approval_key()` |
| 토픽 키 형식 | `f"D{exchange3}{symbol}"` (예: `DNASAAPL`) | OK — `_build_kis_topic_async()` |
| 거래소 resolve | `stock.kis_overseas_client._resolve_exchange()` (캐시 우선 + NAS/NYS/AMS 순회) | OK — executor 호출 |
| 메시지 파서 | `wrapper.parse_overseas_orderbook` 재사용 | OK — `_handle_message`에서 import |
| 백오프 정책 | 1→2→4→8→16→30s 캡 (OrderAdvisor 자문 반영) | OK — KIS rate limit 충돌 가능성 0 |

### D. 텔레메트리 경계

| 카운터 | 기대 호출처 | 결과 |
|--------|-------------|------|
| `quote_overseas.kis_orderbook_ws.start` | `KISOverseasOrderbookWS.start()` | OK |
| `quote_overseas.kis_orderbook_ws.stop` | `KISOverseasOrderbookWS.stop()` | OK |
| `quote_overseas.kis_orderbook_ws.connect` | `_run_ws` 연결 성공 | OK |
| `quote_overseas.kis_orderbook_ws.disconnect` | `_connect_loop` 끊김 감지 | OK |
| `quote_overseas.kis_orderbook_ws.reconnect_attempt` | `_connect_loop` 재시도 | OK |
| `quote_overseas.kis_orderbook_ws.topic_subscribe/unsubscribe` | `subscribe/unsubscribe` | OK |
| `quote_overseas.kis_orderbook_ws.message` | `_on_kis_orderbook_ws_message` | OK |

### E. 프론트 공휴일 분기 경계

| 항목 | 기대 | 결과 |
|------|------|------|
| `US_HOLIDAYS_ET` Set 구조 | 30일 (2026/2027/2028 각 10일, observed 보정) | OK — pytest 명단 검증 |
| 공휴일 `phase` 결과 | `'closed'` + `holiday: 'YYYY-MM-DD'` | OK — `resolveUsPhaseByClock` 분기 |
| 평일 거래시간 영향 | 0건 | OK — 기존 분기 미터치 |
| 라벨 표기 | `⚪ 휴장 (2026-11-26)` | OK — `_buildLabel` |
| 빌드 | `npm run build` ✓ | OK (4.64s, 0 error) |

### F. 실키 테스트 가드 경계

| 항목 | 기대 | 결과 |
|------|------|------|
| `KIS_LIVE_TEST` 미설정 | 3/3 SKIP | OK — `pytest tests/integration/test_kis_overseas_live.py -v` 확인 |
| `live` 마커 등록 | `pytest.ini` `markers =` 추가 | OK |
| WS 테스트 시간 가드 | ET 09:30~16:00 외 자동 skip | OK — `_is_us_market_open_now()` |
| CI 회귀 영향 | 0건 | OK |

---

## 2. 회귀 결과

### 단위 테스트 (전체)

```
849 passed, 16 warnings, 17 errors in 14.15s
```

- **신규 PASS**: 10건 (WS 6 + holiday 4)
- **베이스라인 대비 +10 PASS**: 839 → 849
- **17 ERROR**: 베이스라인과 동일 — 테스트 PostgreSQL DB(`localhost:5433`) 미가동 환경. `test_order_repo_exchange.py` / `test_page_view_repo_count_by_user.py` / `test_stock_info_repo_exchange.py` — 본 작업 변경과 무관(이전 phase 산출물).
- **신규 FAIL**: 0건

### 호가/가격 채널 회귀 (대상 파일 단위)

```
tests/unit/test_quote_overseas_kis_orderbook.py 3/3 PASS
tests/unit/test_quote_overseas_kis_first.py     4/4 PASS
tests/unit/test_quote_overseas_kis_ws_orderbook.py (신규) 6/6 PASS
tests/unit/test_us_market_clock_holidays.py     (신규) 4/4 PASS
tests/integration/test_kis_overseas_live.py     (신규) 3/3 SKIP (의도된 가드)
```

### 프론트 빌드

```
vite v6.4.1 building for production...
✓ 857 modules transformed.
dist/index.html                     0.39 kB │ gzip:   0.27 kB
dist/assets/index-CR-b5z0i.css     58.34 kB │ gzip:  10.55 kB
dist/assets/index-uHgHrghW.js   1,472.51 kB │ gzip: 402.43 kB
✓ built in 4.64s
```
0 error / chunk size 경고는 기존(미해결) — 본 작업 미영향.

---

## 3. 도메인 / DB / 보안 영향

| 영역 | 영향 |
|------|------|
| 도메인 알고리즘 (safety_grade/macro_regime/macro_cycle) | 0건 |
| DB 스키마 (Alembic) | 0건 |
| 사용자 데이터 / KIS 자격증명 | 0건 (운영자 키만 사용) |
| 응답 스키마 (Pydantic) | 0건 |
| 보안 헤더 / CORS / nginx | 0건 |

---

## 4. 이슈 / 우려 / 후속 작업

| 항목 | 상태 | 비고 |
|------|------|------|
| KIS HDFSASP0 메시지 offset 가정 | 개발 한정 미검증 | 실 키 통합 테스트(REQ-INT-03)로 사용자가 직접 검증. 런북에 보정 가이드 명시. |
| 백오프 캡 30s | 검증 완료 | OrderAdvisor 자문: KIS WS rate limit(분당 30 connect)와 안전 마진 |
| WS 사용자 키(KIS_HTS_ID 등) 분기 | 본 phase 미포함 | 사용자별 키 분기는 다음 phase. 현재는 운영자 키 단일. |
| 공휴일 단축 거래일 (Black Friday 13:00 마감) | v3 | 본 phase 제외 — 주석 표시 |

---

## VERIFY 결과: PASS

요건 3건(REQ-WS-01 / REQ-FE-02 / REQ-INT-03) 모두 수용 기준 충족. 회귀 0건.
