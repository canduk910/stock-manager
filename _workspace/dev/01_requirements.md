# 요건서: 해외매매화면 후속 개선 — KIS WS 호가 통합 + 미국 공휴일 휴장 v2 + 실키 통합 테스트

**원천 plan**: `/Users/kimdukki/.claude/plans/yfinance-jolly-token.md` (이전 phase 완료)
**작성일**: 2026-05-09
**범위**: 풀스택 (백엔드 2 + 프론트 1 + 통합 테스트 1)
**도메인 의사결정**: 이전 phase에서 모두 확정 — 도메인팀장 단계 생략, OrderAdvisor만 ad-hoc

---

## 배경 (Context)

이전 phase에서 해외매매화면 호가창/상세/환율/거래시간이 도입되었으나 3개 후속 사항이 남았다:

1. **KIS WS HDFSASP0 실제 통합** — 현재 호가는 KIS REST(`HHDFS76200100`) 2초 폴링으로 구동(`services/quote_overseas.py:_orderbook_poll_loop`). `wrapper.py`에 `KoreaInvestmentWS.subscribe_overseas_orderbook` 인터페이스만 마련되어 있고 실제 WS 채널은 미연결. WS 우선 + REST 폴백이 사용자 결정이었으므로 후속 통합 필요.
2. **미국 공휴일 휴장 처리** — `useUsMarketClock`이 주말 휴장만 판정. NYSE/NASDAQ 정규 공휴일 9~10일을 추가 판정.
3. **실 키 통합 테스트** — KIS HHDFS76200100/76200200 응답 필드명은 가이드 추정값. `_normalize_orderbook_response`가 graceful 처리하지만 실 응답에서 빈 배열만 반환하면 호가창이 비어 보인다. 실 키로 응답 필드명 확정 필요.

---

## 요건 목록

### [REQ-WS-01] KIS 해외 호가 WS 채널 실제 통합 (HDFSASP0)

**설명**: `services/quote_overseas.py`에 KIS WS 호가 채널을 실제 연결하고, 종목 구독/해지 흐름에 연결한다. WS 정상 시 WS 우선, 끊김/실패/모의투자 시 기존 REST 폴링(`_orderbook_poll_loop`) 폴백.

**수용 기준**:
- `KISOverseasOrderbookWS` 신규 내부 클래스 (또는 함수 모음) — 다음 책임:
  - KIS WS 연결 1개로 다수 종목 호가 구독 (KIS WS는 1 connection 다중 토픽)
  - 인증: `routers/_kis_auth.get_access_token()` 재사용 (운영자 키 또는 사용자 키)
  - 토픽 키: `f"D{exchange3}{symbol}"` (실시간 D, 예: `DNASAAPL`)
  - 메시지 파서: `wrapper.parse_overseas_orderbook` 재사용
  - 재연결: 지수 백오프 (1s → 2s → 4s → ... 최대 30s, KIS 정책 준수)
  - 연결 해제 시 모든 종목 unsubscribe + REST 폴링으로 자동 폴백

- `OverseasQuoteManager`의 `_subscribe_symbol`/`_unsubscribe_symbol`에 통합:
  - 종목 구독 시: WS 연결 정상 → WS 토픽 등록 / WS 비정상 → 즉시 REST 폴링 시작
  - WS 메시지 수신 시: 해당 종목의 REST 폴링 태스크 자동 중단(중복 방지)
  - WS 끊김 감지 시: 모든 구독 종목에 대해 REST 폴링 시작
  - WS 재연결 + 토픽 재등록 시: REST 폴링 중단 (WS 우선 복귀)

- 메시지 broadcast shape는 기존 그대로:
  ```python
  {"type": "orderbook", "symbol": ..., "asks": [...], "bids": [...],
   "total_ask_volume": ..., "total_bid_volume": ...}
  ```
  → 프론트 변경 없음

- 텔레메트리: `quote_overseas.kis_orderbook_ws.{connect,disconnect,reconnect_attempt,topic_subscribe,topic_unsubscribe}` 카운터

- 실 KIS WS 키 부재 환경(개발/CI)에서는 자동으로 REST 폴링만 사용 (graceful)

**테스트 힌트**:
- `tests/unit/test_quote_overseas_kis_ws_orderbook.py`:
  - WS 연결 성공 시 종목 구독 → 토픽 등록 + REST 폴링 미시작
  - WS 끊김 시 종목별 REST 폴링 자동 시작
  - WS 재연결 시 REST 폴링 자동 중단
  - 메시지 수신 시 broadcast 형식 검증
  - 모의투자 환경(KIS WS 503) → REST 폴링 폴백 즉시 동작

**레이어**: `services/`

---

### [REQ-FE-02] useUsMarketClock 미국 공휴일 휴장 판정 추가

**설명**: `frontend/src/hooks/useUsMarketClock.js`에 NYSE/NASDAQ 공휴일 휴장 판정을 추가한다.

**수용 기준**:
- 2026~2028년 미국 정규 공휴일 명단 하드코딩 (10일):
  - New Year's Day (1/1, 일요일이면 다음 월요일 / 토요일이면 전 금요일)
  - MLK Day (1월 셋째 월요일)
  - Presidents Day (2월 셋째 월요일)
  - Good Friday (부활절 직전 금요일 — 직접 계산 또는 명시 매핑)
  - Memorial Day (5월 마지막 월요일)
  - Juneteenth (6/19, observed)
  - Independence Day (7/4, observed)
  - Labor Day (9월 첫째 월요일)
  - Thanksgiving (11월 넷째 목요일)
  - Christmas Day (12/25, observed)

- 명단은 ET 타임존 기준 날짜 매핑 객체로 정의 (예: `US_HOLIDAYS_ET = ["2026-01-01", "2026-01-19", ...]`)

- `resolveUsPhaseByClock(now)` 순수 함수에 휴장 판정 추가:
  - 주말(현재 로직) OR 공휴일이면 `phase: 'closed'`, `label: '휴장 (공휴일명)'`
  - 공휴일 라벨에는 영문 공휴일명 또는 한글 표기

- 단축 거래일(Black Friday 13:00 ET 조기마감 등)은 v3 (본 phase 제외) — 주석으로 표시

- 순수 함수 단위 테스트:
  - 2026/01/01 (목) → closed (New Year)
  - 2026/01/05 (월, 평일) → 정규/프리/애프터 정상 분기
  - 2026/05/25 (월, Memorial Day) → closed
  - 2026/11/26 (목, Thanksgiving) → closed

**테스트 힌트**:
- 백엔드 단위로 검증할 수 없는 프론트 훅이므로 Vitest 미설정 시 generation만 + `npm run build` 회귀 확인
- 또는 Python 측 동등 로직(존재하지 않으면 생략) — 본 요건은 프론트 한정

**레이어**: `frontend/src/hooks/`

---

### [REQ-INT-03] KIS 실키 통합 테스트 스크립트

**설명**: 실 KIS 키로 HHDFS76200100 (호가) / HHDFS76200200 (상세) / HDFSASP0 (WS 호가) 응답을 검증하는 통합 테스트 스크립트. 환경변수 가드로 실 키 부재 시 skip.

**수용 기준**:
- 파일: `tests/integration/test_kis_overseas_live.py`
- `pytest.mark.live` 마커 + `@pytest.mark.skipif(not os.getenv("KIS_LIVE_TEST"), reason=...)` 가드
- 실행: `KIS_LIVE_TEST=1 pytest tests/integration/test_kis_overseas_live.py -v`

- 검증 항목:
  1. **HHDFS76200100 (호가 REST)**: AAPL, NAS 거래소 → `_normalize_orderbook_response` 결과의 `asks`/`bids` 배열이 비어있지 않음 + 가격 > 0
  2. **HHDFS76200200 (상세 REST)**: AAPL → `open`/`high`/`low`/`prev_close`/`high_52w`/`low_52w` 모두 > 0
  3. **HDFSASP0 (WS 호가)**: 미국 정규 거래시간 중에만 활성 — `pytest.skip` if outside ET 09:30~16:00. 종목 구독 → 5초 대기 → 메시지 수신 확인 + 파싱 결과 비어있지 않음

- 응답 필드명이 가이드 추정과 다른 경우, 실패 시 명확한 메시지로 매핑 보정 필요한 키 출력 (디버깅 용이)

- CI에는 포함하지 않음 (`KIS_LIVE_TEST` 환경변수 미설정 시 skip이므로 안전)

- 별도 `_workspace/dev/05_live_test_runbook.md` 산출 — 사용자가 로컬에서 실행하는 절차 + 예상 결과 + 응답 필드 보정 가이드

**테스트 힌트**: 자체로 통합 테스트이므로 추가 테스트 불필요

**레이어**: `tests/integration/`

---

## 단계적 구현 순서 (TDD)

| Step | 요건 ID | 설명 |
|------|---------|------|
| 1 | REQ-WS-01 | KIS WS 호가 채널 통합 + 폴링 폴백 자동화 |
| 2 | REQ-FE-02 | useUsMarketClock 공휴일 판정 |
| 3 | REQ-INT-03 | 실키 통합 테스트 스크립트 + 런북 |

각 Step 단위 회귀 + (Step 2) `npm run build` 통과.

---

## 회귀 가드

- 호가 메시지 broadcast shape 변경 0건 (프론트 useQuote 무영향)
- 가격 채널(Finnhub WS / yfinance 폴링 / KIS 가격 폴링) 무영향 — 호가 채널만 신규
- KIS WS 키 부재 환경(개발/CI) graceful — REST 폴링 자동 사용
- 미국 공휴일 추가는 휴장 판정 강화만 — 평일 거래시간 동작 무영향
- 통합 테스트 스크립트는 환경변수 가드로 CI에서 skip — 회귀 0
- 도메인 알고리즘(safety_grade/macro_regime) 무영향
- DB 변경 0건
- 기존 단위 838 PASS / 0 FAIL 유지

## 도메인 자문 트리거

OrderAdvisor를 Agent로 호출:
- KIS WS 메시지 offset/필드명이 `parse_overseas_orderbook` 가정과 다를 때
- WS 재연결 백오프 정책이 KIS rate limit과 충돌 가능성 검토 필요 시

다른 도메인 전문가는 본 작업과 무관.
