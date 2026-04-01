# services/ — 서비스 레이어

`stock/` 패키지의 데이터 소스를 조합해 웹 API용 응답을 조립한다.

## 모듈 목록

| 파일 | 역할 |
|------|------|
| `exceptions.py` | 공용 예외 계층 |
| `watchlist_service.py` | 관심종목 대시보드 + 종목 상세 (국내=pykrx+DART, 해외=yfinance) |
| `detail_service.py` | 재무 테이블 + PER/PBR 히스토리 + CAGR 종합 리포트 |
| `order_service.py` | 국내/해외/FNO 주문 전체 관리 (KIS API 직접 호출) |
| `reservation_service.py` | 예약주문 실행 엔진 (asyncio 20초 폴링) |
| `quote_service.py` | 실시간 시세 WebSocket 관리 (국내 KIS WS + 해외 Finnhub/yfinance) |
| `advisory_service.py` | AI자문 데이터 수집 + GPT-4o 리포트 생성 |
| `macro_service.py` | 매크로 분석 오케스트레이션: 병렬 수집 + GPT 번역/추출 + 섹션별 독립 실패 허용 |

---

## 예외 계층 (중요)

```
ServiceError (기본 400)
├── NotFoundError (404)
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
- **Write-Ahead 주문 패턴**: PENDING 선행 기록 → KIS API → 성공 시 PLACED / 실패 시 REJECTED (split-brain 방지)
- `cancel_order()` → 로컬 DB 즉시 CANCELLED + `local_synced`/`order_status` 응답. 동기화 실패 시 로깅
- `modify_order()` → 로컬 DB 가격/수량 즉시 반영 + `local_synced`. 동기화 실패 시 로깅
- `get_order_history()` → **60초 쿨다운** 대사 (`_RECONCILE_COOLDOWN`). F5 연타 시 KIS API 호출 0회
- `sync_orders()` → 쿨다운 무시, 강제 대사. 사용자 명시적 동기화 요청용
- `_validate_market()`: 디스패치 함수(get_buyable/get_open_orders/get_executions) 진입부 시장 코드 검증
- `_strip_leading_zeros()`: 10자리→8자리 주문번호 변환
- **FNO**: `_is_fno_night_session()`으로 주간/야간 TR_ID 자동 선택. `KIS_ACNT_PRDT_CD_FNO` 미설정 시 `ConfigError` → 503

### quote_service.py
- **KISQuoteManager**: KIS WS 단일 연결 + 심볼별 `asyncio.Queue` pub/sub
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
- **OverseasQuoteManager**: Finnhub WS(30 심볼) 또는 yfinance 2초 폴링
  - `fast_info.last_price or previous_close` 패턴 (비개장일 직전 종가)
  - 구독자 0 → on-demand cancel

### reservation_service.py
- `asyncio` 20초 간격 폴링
- 가격 조건(`price_below`/`price_above`) + 시간 조건(`scheduled`) 체크 후 자동 주문 발송
- `_fetch_current_price(symbol, market)`: 국내=`stock.market.fetch_price()`, 해외=`stock.yf_client.fetch_price_yf()` (yfinance 통일)

### advisory_service.py
- **3전략 프레임워크**:
  - 변동성 돌파 (Larry Williams, K=0.3/0.5/0.7)
  - 안전마진 (Graham Number = √(22.5×EPS×BPS))
  - 추세추종 (MA정배열 + MACD + RSI)
- `max_completion_tokens=2500`
- `response_format={"type":"json_object"}`
- 출력 JSON에 `전략별평가` 섹션 포함
- fundamental 응답에 `business_description`, `business_keywords` 필드 포함 (fetch_segments 반환 dict에서 추출, 구 캐시 list 형태 하위호환)
- ServiceError 계층 사용 (HTTPException 직접 raise 없음)

### watchlist_service.py
- `resolve_symbol(name_or_code, market)`: 종목명/코드 해석
- `get_stock_detail()`: basic에 roe, dividend_yield, dividend_per_share 포함
- financial rows에 `oi_margin`(영업이익률), `net_margin`(순이익률) 포함

### detail_service.py
- 해외는 yfinance 최대 4년, 밸류에이션 차트 빈 데이터 반환
- `_get_report_kr()`/`_get_report_us()` 모두 `fetch_forward_estimates_yf()` 호출 — 응답에 `forward_estimates` 필드 포함

> 메서드 시그니처 상세 → `docs/SERVICES.md`
