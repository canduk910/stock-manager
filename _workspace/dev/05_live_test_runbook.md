# KIS 해외시세 실키 통합 테스트 런북

**파일**: `tests/integration/test_kis_overseas_live.py`
**대상 API**: HHDFS76200100(REST 호가) / HHDFS76200200(REST 상세) / HDFSASP0(WS 호가)
**원천 요건**: REQ-INT-03 (`_workspace/dev/01_requirements.md`)

---

## 0. 사전 준비

### 0-1. 환경변수 (.env)

```bash
KIS_APP_KEY=<운영자 실계좌 앱키>
KIS_APP_SECRET=<운영자 실계좌 시크릿>
KIS_ACNT_NO=<8자리 계좌번호>
KIS_ACNT_PRDT_CD_STK=01
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
```

> KIS Developer Portal(`https://apiportal.koreainvestment.com`)에서 발급된 **실계좌 키**를 사용한다.
> 모의투자 키는 해외시세 조회가 차단될 수 있으므로 실계좌 키 권장.

### 0-2. 테스트 DB 불필요

본 테스트는 외부 API 응답만 검증하므로 PostgreSQL 테스트 DB 의존성 없음.

---

## 1. 실행 절차

### 1-1. 전체 실행 (REST 2건 + WS 1건)

```bash
KIS_LIVE_TEST=1 pytest tests/integration/test_kis_overseas_live.py -v -m live
```

### 1-2. REST 만 실행 (시간외에도 가능)

```bash
KIS_LIVE_TEST=1 pytest tests/integration/test_kis_overseas_live.py::test_live_kis_orderbook_rest_aapl_returns_non_empty_levels -v
KIS_LIVE_TEST=1 pytest tests/integration/test_kis_overseas_live.py::test_live_kis_price_detail_rest_aapl_returns_full_fields -v
```

### 1-3. WS 만 실행 (반드시 미국 정규장 ET 09:30~16:00)

```bash
KIS_LIVE_TEST=1 pytest tests/integration/test_kis_overseas_live.py::test_live_kis_ws_orderbook_aapl_receives_message_within_5s -v
```

> 시간외(애프터/프리/주말/공휴일)에는 자동으로 skip — 메시지 미수신 false-positive 방지.

---

## 2. 예상 결과

### 2-1. 정상 케이스

```
tests/integration/test_kis_overseas_live.py::test_live_kis_orderbook_rest_aapl_returns_non_empty_levels PASSED
tests/integration/test_kis_overseas_live.py::test_live_kis_price_detail_rest_aapl_returns_full_fields PASSED
tests/integration/test_kis_overseas_live.py::test_live_kis_ws_orderbook_aapl_receives_message_within_5s PASSED
```

### 2-2. CI(`KIS_LIVE_TEST` 미설정) 결과

```
3 skipped — 회귀 영향 0
```

---

## 3. 실패 시 응답 필드명 보정 가이드

KIS Developer Portal의 명세는 종종 가이드와 실제 응답이 다르다. 본 테스트는 실패 메시지에서 점검 위치를 명시한다.

### 3-1. HHDFS76200100 (REST 호가) 실패

**증상**: `[FAIL] asks 배열 비어있음. _normalize의 pask/vask 매핑 점검 필요`

**조치**:
1. `stock/kis_overseas_client.py` → `_normalize_orderbook_response()` 의 키 매핑 확인:
   ```python
   p_ask = _f(f"pask{i}")    # ← 가이드 추정
   v_ask = _i(f"vask{i}")
   p_bid = _f(f"pbid{i}")
   v_bid = _i(f"vbid{i}")
   ```
2. KIS Developer Portal의 HHDFS76200100 응답 명세에서 실제 키를 확인 (예: `output2.askp1` ~ `askp10` 일 수 있음).
3. 변경 후 단위 테스트(`tests/unit/test_kis_overseas_orderbook.py`) 회귀 확인 후 본 테스트 재실행.

### 3-2. HHDFS76200200 (REST 상세) 실패

**증상**: `[FAIL] 필드 누락/0: [('high_52w', None), ...]`

**조치**:
1. `stock/kis_overseas_client.py` → `_normalize_price_detail_response()` 의 키 매핑 확인:
   ```python
   "open": _f("open"),
   "high": _f("high"),
   "low": _f("low"),
   "last": _f("last"),
   "prev_close": _f("base"),     # ← 'base' 또는 'prdy_clpr' 가능성
   "high_52w": _f("h52p"),       # ← 'h52p' 또는 'w52_hgpr' 가능성
   "low_52w": _f("l52p"),
   ```
2. 다른 거래소(NYS/AMS) 응답이라면 거래소별 필드명 차이 가능.

### 3-3. HDFSASP0 (WS 호가) 실패

**증상**: `[FAIL] HDFSASP0 WS 메시지 5초 내 미수신`

**원인 후보**:

| 원인 | 점검 위치 |
|------|----------|
| approval_key 발급 실패 | `services/quote_overseas.py:KISOverseasOrderbookWS._issue_approval_key` 로그 |
| 토픽 키 형식 오류 | `services/quote_overseas.py:_build_kis_topic_async` — `f"D{exchange3}{symbol}"` |
| 메시지 offset 가정 오류 | `wrapper.py:parse_overseas_orderbook` — `t[7..16]=ask, t[17..26]=bid, t[27..36]=ask_vol, t[37..46]=bid_vol, t[47]=tot_ask, t[48]=tot_bid` |
| 정규장 외 | 테스트 자동 skip (조건 보강 필요 시 `_is_us_market_open_now()` 수정) |

**점검 방법** (실 메시지 로깅):
```python
# services/quote_overseas.py:KISOverseasOrderbookWS._handle_message 에 임시 로깅 추가
logger.info("[KIS-OB-WS] raw=%s", data[:300])
```
→ 실 페이로드 캡처 후 `wrapper.parse_overseas_orderbook` offset 보정.

---

## 4. 정상 응답 샘플 (참고)

### 4-1. HHDFS76200100 정상 응답 (예시)

```json
{
  "asks": [
    {"price": 200.10, "volume": 100},
    {"price": 200.15, "volume": 150},
    ...
  ],
  "bids": [
    {"price": 199.90, "volume": 120},
    ...
  ],
  "total_ask_volume": 5500,
  "total_bid_volume": 6700,
  "exchange": "NAS"
}
```

### 4-2. HHDFS76200200 정상 응답 (예시)

```json
{
  "open": 199.50,
  "high": 201.00,
  "low": 199.20,
  "last": 200.05,
  "prev_close": 199.80,
  "volume": 12345678,
  "high_52w": 215.50,
  "low_52w": 175.20,
  "high_52w_date": "20251215",
  "low_52w_date": "20260102",
  "currency": "USD",
  "exchange": "NAS"
}
```

### 4-3. HDFSASP0 WS 메시지 (수신 후 파싱 결과)

```json
{
  "symbol": "AAPL",
  "exchange": "NAS",
  "asks": [{"price": 200.10, "volume": 100}, ...],
  "bids": [{"price": 199.90, "volume": 120}, ...],
  "total_ask_volume": 5500,
  "total_bid_volume": 6700
}
```

---

## 5. 후속 작업 트리거

| 결과 | 후속 작업 |
|------|----------|
| 3개 테스트 모두 PASS | 별도 작업 불필요 — REQ-INT-03 완료 |
| HHDFS76200100/76200200 키 불일치 | `_normalize_*` 함수 키 매핑 보정 + 단위 테스트 회귀 |
| HDFSASP0 offset 불일치 | `wrapper.parse_overseas_orderbook` 보정 + `tests/unit/test_wrapper_overseas_orderbook_ws.py` 회귀 |
| approval_key 발급 실패 | KIS 키 갱신/재발급 (만료 가능성), `KIS_BASE_URL` 점검 |
| WS 연결 자체 실패 | 방화벽 — `ws://ops.koreainvestment.com:21000` 21000/TCP outbound 확인 |

---

## 6. 안전장치 — CI 회귀 0

- 모든 테스트는 `pytest.mark.live` + `pytest.mark.skipif(not KIS_LIVE_TEST)` 가드.
- GitHub Actions(`.github/workflows/ci.yml`)의 `pytest tests/ -v` 는 `KIS_LIVE_TEST` 미설정 → 자동 skip.
- 본 테스트가 실패해도 main 브랜치 배포 차단되지 않음 (사용자 로컬 검증용).
