# Step 1~3 GREEN 구현 산출

## Step 1 — REQ-WS-01 KIS WS 호가 채널 통합

### 변경 파일

**`services/quote_overseas.py`** (+220 lines)

#### 신규 클래스: `KISOverseasOrderbookWS`

```python
class KISOverseasOrderbookWS:
    """KIS 해외 호가(HDFSASP0) WebSocket 클라이언트."""

    KIS_OVERSEAS_WS_URL = "ws://ops.koreainvestment.com:21000"

    def __init__(self, on_orderbook=None, on_disconnect=None, on_reconnect=None): ...
    async def start(self): ...      # approval_key 발급 → ws connect → 메시지 루프
    async def stop(self): ...
    async def subscribe(self, rsym: str): ...
    async def unsubscribe(self, rsym: str): ...
    @property
    def is_connected(self) -> bool: ...
```

**핵심 동작**:
- `_issue_approval_key()` — `routers/_kis_auth.get_kis_credentials(None)` 운영자 키 → KIS `/oauth2/Approval` 호출
- `_connect_loop()` — 지수 백오프 1→2→4→8→16→30s 캡 (KIS rate limit 준수, OrderAdvisor 자문 반영)
- `_run_ws()` — websockets.connect + 모든 토픽 재등록 + `on_reconnect` 콜백
- `_send_subscribe(rsym, register=True/False)` — `tr_id="HDFSASP0"`, `tr_type="1"(등록)/"2"(해지)`, `tr_key=rsym`
- `_handle_message(data)` — `0|HDFSASP0|N|<payload>` 파싱 (wrapper.parse_overseas_orderbook 재사용) + PINGPONG 자동 응답
- 텔레메트리: `quote_overseas.kis_orderbook_ws.{connect,disconnect,reconnect_attempt,topic_subscribe,topic_unsubscribe,message,start,stop}`

#### `OverseasQuoteManager` 통합

| 변경점 | 동작 |
|--------|------|
| `__init__` | `_kis_ob_ws`, `_kis_ob_symbols: dict[str, str]` 추가 |
| `start()` | `KISOverseasOrderbookWS()` 생성 + start. 실패 시 `_kis_ob_ws=None` graceful (REST 폴백) |
| `stop()` | WS stop + 폴러 cancel + 캐시 정리 |
| `subscribe()` | 호가 라인을 `_subscribe_orderbook(symbol)`로 분기 |
| `_subscribe_orderbook()` | WS 정상 → 토픽 등록 / 비정상 → REST 폴러 시작 |
| `unsubscribe()` | WS 토픽 해제 + REST 폴러 cancel |
| `_on_kis_orderbook_ws_message()` | broadcast (shape 보존) + 해당 종목 REST 폴러 cancel(중복 방지) |
| `_on_kis_ob_ws_disconnect()` | 모든 구독 종목 REST 폴링 자동 시작 |
| `_on_kis_ob_ws_reconnect()` | 토픽 재등록 + 모든 REST 폴러 cancel |
| `_build_kis_topic_async()` | `_resolve_exchange()` executor 호출 → `f"D{excd}{symbol}"` |

### Broadcast Shape (불변)

```python
{
  "type": "orderbook",
  "symbol": "AAPL",
  "asks": [{"price": 200.10, "volume": 100}, ...],
  "bids": [...],
  "total_ask_volume": 5500,
  "total_bid_volume": 6700,
}
```
→ 프론트 `useQuote` 변경 0건.

### GREEN 결과
- `tests/unit/test_quote_overseas_kis_ws_orderbook.py` 6/6 PASS
- 회귀: `tests/unit/test_quote_overseas_kis_orderbook.py` 3/3 PASS, `test_quote_overseas_kis_first.py` 4/4 PASS

---

## Step 2 — REQ-FE-02 useUsMarketClock 공휴일

### 변경 파일

**`frontend/src/hooks/useUsMarketClock.js`** (+90 lines)

#### 신규 export

```js
export const US_HOLIDAYS_ET = new Set([
  // 2026: 10일 (NewYear/MLK/Pres/GoodFri/Memorial/Juneteenth/IndepDay observed/Labor/Thanks/Christmas)
  '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25',
  '2026-06-19', '2026-07-03', '2026-09-07', '2026-11-26', '2026-12-25',
  // 2027: 10일 (observed 보정 포함)
  '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26', '2027-05-31',
  '2027-06-18', '2027-07-05', '2027-09-06', '2027-11-25', '2027-12-24',
  // 2028: 10일
  '2028-01-03', '2028-01-17', '2028-02-21', '2028-04-14', '2028-05-29',
  '2028-06-19', '2028-07-04', '2028-09-04', '2028-11-23', '2028-12-25',
])

export function isUsHoliday(input) { ... }  // Date | 'YYYY-MM-DD' → boolean
```

#### `resolveUsPhaseByClock` 분기 추가

```js
// 주말 → closed
if (weekday === 'Sat' || weekday === 'Sun') {
  return { phase: 'closed', etTime, kstTime, holiday: null }
}
// 공휴일 → closed (REQ-FE-02 신규)
const etDate = _etDateStr(now)
if (US_HOLIDAYS_ET.has(etDate)) {
  return { phase: 'closed', etTime, kstTime, holiday: etDate }
}
```

#### 라벨 빌더

```js
function _buildLabel(r) {
  if (r.phase === 'closed' && r.holiday) {
    return `${PHASE_LABELS.closed} 휴장 (${r.holiday})`
  }
  return `${PHASE_LABELS[r.phase]} (ET ${r.etTime} / KST ${r.kstTime})`
}
```

훅 반환에 `holiday: 'YYYY-MM-DD' | null` 필드 추가 (백워드 호환 — 옵셔널).

### GREEN 결과
- `tests/unit/test_us_market_clock_holidays.py` 4/4 PASS
- `npm run build` ✓ built in 4.64s (1,472KB JS / 58KB CSS, 회귀 없음)

---

## Step 3 — REQ-INT-03 실키 통합 테스트

### 변경 파일

| 파일 | 변경 |
|------|------|
| `tests/integration/test_kis_overseas_live.py` | 신규 (145 lines) |
| `pytest.ini` | `live` 마커 등록 |
| `_workspace/dev/05_live_test_runbook.md` | 신규 (사용자 런북) |

### 가드

```python
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.getenv("KIS_LIVE_TEST"), reason="..."),
]
```

WS 테스트는 추가로 `_is_us_market_open_now()` (ET 09:30~16:00 평일) 가드 — 시간외 자동 skip.

### 검증 항목

1. **HHDFS76200100**: AAPL 호가 → asks/bids 비어있지 않음 + 가격 > 0
2. **HHDFS76200200**: AAPL 상세 → open/high/low/last/prev_close/high_52w/low_52w 모두 > 0
3. **HDFSASP0 WS**: AAPL 구독 → 5초 내 메시지 수신 + 파싱 결과 비어있지 않음

각 실패 메시지에 응답 필드명 보정 위치(예: `_normalize_orderbook_response`의 `pask{i}`/`vask{i}` 매핑)를 명시.

### CI 회귀 0
- `KIS_LIVE_TEST` 미설정 → 3/3 SKIP

---

## 신규/수정 라인 합계

| 파일 | 변경량 |
|------|--------|
| `services/quote_overseas.py` | +220 lines (KIS WS 클래스 + Manager 통합) |
| `frontend/src/hooks/useUsMarketClock.js` | +90 lines (공휴일 30개 + 분기 + 라벨) |
| `tests/unit/test_quote_overseas_kis_ws_orderbook.py` | +290 lines (신규) |
| `tests/unit/test_us_market_clock_holidays.py` | +75 lines (신규) |
| `tests/integration/test_kis_overseas_live.py` | +145 lines (신규) |
| `pytest.ini` | +1 line (live 마커) |
| `_workspace/dev/02_test_red.md` | 신규 |
| `_workspace/dev/03_implementation.md` | 신규 |
| `_workspace/dev/04_qa_report.md` | 신규 |
| `_workspace/dev/05_live_test_runbook.md` | 신규 (160 lines) |

**총 +820 lines (코드/테스트), +0 DB 변경, +0 프론트 컴포넌트 변경**.
