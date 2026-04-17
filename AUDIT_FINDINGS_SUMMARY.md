# 백엔드 코드 감사 — 우선순위별 발견 사항

**감사 일자**: 2026-04-17
**대상 범위**: routers/, services/, stock/ (14,745 LOC)
**감사자**: backend-audit agent

---

## 🔴 HIGH 우선순위 (5개 항목)

### H1: advisory_service.py 분할
**파일**: `services/advisory_service.py` (944줄, 17함수)
**심각도**: 🔴 HIGH
**범주**: 파일 크기 / 유지보수성

**문제**:
- 단일 파일에 5가지 책임:
  1. 데이터 수집 (fundamental + technical + strategy_signals)
  2. OpenAI GPT 호출 및 응답 처리
  3. 토큰 관리 + 재시도 로직
  4. Pydantic v2 검증
  5. 공용 헬퍼 함수들

**현황**:
```python
# 함수별 라인 수
refresh_stock_data()        65줄   ← 데이터 수집 dispatcher
generate_ai_report()        250줄  ← GPT 호출 (너무 복잡)
_collect_fundamental()      180줄  ← DART + yfinance
_collect_technical()        120줄  ← 15분봉 + 기술지표
_determine_regime()         15줄   ← 공용 모듈 래퍼 (3중 구현)
_calc_graham_number()       30줄
기타 헬퍼들                 284줄
```

**영향**:
- 테스트 어려움 (GPT 호출 모킹)
- 수정 시 전체 파일 영향
- 재시도 로직 재사용 불가

**권장 액션**:
```
services/advisory_service.py (현재)
├── services/advisory_service.py (dispatcher 유지: 50줄)
├── services/advisory_collector.py (refresh_stock_data + _collect_* : 400줄)
└── services/advisory_reporter.py (generate_ai_report + 토큰 관리: 300줄)
```

**구현 방법**:
1. `advisory_collector.py` 신규: `refresh_stock_data()`, `_collect_fundamental()`, `_collect_technical()`, `_collect_strategy_signals()`
2. `advisory_reporter.py` 신규: `generate_ai_report()`, 토큰 관리, 재시도 로직
3. `advisory_service.py` 유지: dispatcher만, `from . import advisory_collector, advisory_reporter`

**예상 작업량**: 8시간 (파일 분할 + unit test + 임포트 통합)

---

### H2: routers → stock 직접 import (레이어 위반)
**파일**: `routers/earnings.py`, `routers/advisory.py`, `routers/market_board.py` 등 (6개)
**심각도**: 🔴 HIGH
**범주**: 레이어 아키텍처 / 예외 처리

**문제**:
라우터에서 services를 우회하고 stock 패키지를 직접 임포트. 특히 market_board.py는 CRUD를 직접 접근.

**위반 사항**:
```python
# ❌ routers/market_board.py:66
from stock.market_board_store import all_items  # DB CRUD 직접

# ❌ routers/earnings.py:8-11
from stock.dart_fin import fetch_financials
from stock.market import fetch_period_returns
from stock.sec_filings import fetch_sec_filings  # 3개 직접 import

# ❌ routers/advisory.py:54,154,189
from stock.symbol_map import name_to_results
from stock.advisory_fetcher import fetch_ohlcv_by_interval
from stock.yf_client import validate_ticker
```

**정상 패턴**:
```python
# ✅ routers/balance.py
from services import watchlist_service  # services 경유
```

**영향**:
- 예외 처리 일관성 없음 (ValueError vs ServiceError)
- 테스트 시 mock 범위 불명확
- 비즈니스 로직이 여러 곳에 분산

**권장 액션**:
```
신규 services/market_board_service.py 생성:
├── get_custom_stocks()              ← routers/market_board.py:66 대체
├── add_custom_stock()               ← routers/market_board.py:73
├── remove_custom_stock()            ← routers/market_board.py:83
└── get_order() / update_order()     ← routers/market_board.py:94

routers/market_board.py 수정:
- from stock.market_board_store import → from services.market_board_service import
```

**구현 방법**:
1. `services/market_board_service.py` 신규 (60줄)
2. `routers/market_board.py` 임포트 변경 (4줄)
3. 마찬가지로 `earnings.py`, `advisory.py` 등 리팩토링 (선택적)

**예상 작업량**: 6시간 (market_board + earnings 통합)

---

### H3: ValueError 남용 (예외 계층 위반)
**파일**: `services/watchlist_service.py` (4건)
**심각도**: 🔴 HIGH (하지만 수정 쉬움)
**범주**: 예외 처리 / 일관성

**문제**:
서비스 레이어에서 ValueError를 직접 raise. 라우터에서 catch하지 않으면 500 오류 반환 (사용자에게 불명확).

**위반 코드**:
```python
# services/watchlist_service.py:195
raise ValueError(f"종목을 찾을 수 없습니다: '{ticker}'")  # ❌ 404 아님

# services/watchlist_service.py:208
raise ValueError(f"'{name_or_code}'에 여러 종목이 매칭됩니다: {names}")  # ❌ 409 아님

# services/watchlist_service.py:210
raise ValueError(f"종목을 찾을 수 없습니다: '{name_or_code}'")  # ❌ 404 아님

# services/order_service.py:530
raise ValueError  # ❌ 무의미
```

**정상 패턴** (services/exceptions.py에 정의됨):
```python
from services.exceptions import NotFoundError  # 404
raise NotFoundError(f"종목을 찾을 수 없습니다: {ticker}")
```

**영향**:
- HTTP 상태 코드 불명확 (500으로 반환)
- 클라이언트가 에러 원인 파악 불가
- CLAUDE.md 규칙 위반

**수정 방법**:
```python
# watchlist_service.py:195 → 208 → 210
from services.exceptions import NotFoundError, ConflictError

# Line 195
raise NotFoundError(f"종목을 찾을 수 없습니다: '{ticker}'")

# Line 208
raise ConflictError(f"'{name_or_code}'에 여러 종목이 매칭됩니다: {names}")

# Line 210
raise NotFoundError(f"종목을 찾을 수 없습니다: '{name_or_code}'")

# order_service.py:530
raise ServiceError("유효하지 않은 요청")
```

**예상 작업량**: 0.5시간 (4줄 수정)

---

### H4: portfolio_advisor_service.py 분할
**파일**: `services/portfolio_advisor_service.py` (607줄, 15함수)
**심각도**: 🔴 HIGH
**범주**: 파일 크기 / 책임 분리

**문제**:
단일 파일에 3가지 책임 혼재:
1. 포트폴리오 분석 (진단, 점수 계산)
2. 리밸런싱 제안 생성
3. 매매 실행 계획 수립

**현황**:
```python
# 함수별 책임
get_advice()                 300줄  ← 모든 로직 하나로 묶여있음
_analyze_portfolio()         100줄
_rebalance_recommendations() 80줄
_generate_trade_actions()    70줄
_fetch_52w_high()            30줄
_determine_regime()          15줄  ← 중복 래퍼
```

**문제점**:
```python
# get_advice() 내부 (300줄):
# 1. balance_data 파싱
# 2. 52주 고가 조회 (stock_info_store 우회, cache.py 직접)
# 3. 체제 판단
# 4. 개별 종목 분석 연계 (advisory_service)
# 5. 포트폴리오 분석
# 6. 리밸런싱 제안
# 7. 매매 계획
# 8. GPT 호출
# 9. 결과 캐싱
```

**권장 액션**:
```
services/portfolio_advisor_service.py (현재)
├── services/portfolio_advisor_service.py (dispatcher: 50줄)
├── services/portfolio_analyst.py (_analyze_portfolio + 점수: 150줄)
├── services/portfolio_rebalancer.py (_rebalance + 제안: 150줄)
└── services/portfolio_executor.py (_generate_trade_actions + GPT: 150줄)
```

**예상 작업량**: 10시간 (분할 + 데이터 흐름 정리 + 테스트)

---

### H5: 체제 판단 함수 3중 구현 (DRY 위반)
**파일**: `services/macro_regime.py` (공용), `services/advisory_service.py`, `services/portfolio_advisor_service.py`, `services/pipeline_service.py`
**심각도**: 🔴 HIGH (하지만 수정 간단)
**범주**: DRY / 중복 제거

**문제**:
동일한 `_determine_regime()` 함수가 3개 서비스에서 반복 구현.

**현황**:
```python
# services/macro_regime.py:176 (canonical)
def determine_regime(sentiment: dict) -> dict:
    """⬅ 이것이 정의"""
    result = ...
    return {
        "regime": ...,
        "params": {...},
        "vix": ...,
        ...
    }

# services/advisory_service.py:448 (래퍼)
def _determine_regime(sentiment: dict) -> tuple[str, str]:
    result = _shared_determine_regime(sentiment)  # ← 공용 호출
    return result['regime'], REGIME_DESC.get(result['regime'])

# services/portfolio_advisor_service.py:291 (동일 래퍼)
def _determine_regime(sentiment: dict) -> tuple[str, str]:
    result = _shared_determine_regime(sentiment)  # ← 동일 코드
    return result['regime'], ...

# services/pipeline_service.py:26 (다른 호환성 래퍼)
def _determine_regime(sentiment: dict, previous_regime=None) -> dict:
    base = _determine_regime_shared(sentiment, previous_regime)
    params = dict(base["params"])
    params["margin_threshold"] = ...  # ← 하위호환 키 매핑
    return { ... }
```

**문제점**:
- 동일 로직이 3곳에 복제
- 마이그레이션 시 3곳 모두 수정 필요
- 테스트 할 곳이 많음

**수정 방법**:
```python
# services/macro_regime.py에 추가
def get_regime_with_context(sentiment: dict) -> tuple[str, str]:
    """(regime, description) 반환 — advisory/portfolio 공용"""
    result = determine_regime(sentiment)
    desc = REGIME_DESC.get(result['regime'], '불명')
    return result['regime'], desc

# services/advisory_service.py 수정 (1줄)
from services.macro_regime import get_regime_with_context
regime, regime_desc = get_regime_with_context(macro_ctx)  # ← 직접 호출

# services/portfolio_advisor_service.py 수정 (1줄)
regime, regime_desc = get_regime_with_context(macro_ctx)  # ← 직접 호출

# services/pipeline_service.py는 유지 (하위호환 래퍼 필요)
```

**예상 작업량**: 2시간 (매크로 모듈 추가 + 3개 서비스 수정 + 테스트)

---

## 🟡 MEDIUM 우선순위 (6개 항목)

### M1: quote_kis._handle_message() 분할
**파일**: `services/quote_kis.py:_handle_message()` (250줄)
**심각도**: 🟡 MEDIUM
**범주**: 가독성 / 복잡도

**문제**:
단일 함수가 5가지 역할:
```python
def _handle_message(self, msg: dict):
    # 1. Approval key 갱신
    if tr_id == "COSOPTX1":
        self._aes_key = ...

    # 2. 토큰 갱신
    elif tr_id == "COSOPTX2":
        self._rest_token = ...

    # 3. 메시지 파싱 (호가/체결)
    elif tr_id == "H0STASP0":  # 호가
        price = ...
    elif tr_id == "TTTC8001R":  # 체결
        qty = ...

    # 4. AES 복호화
    decrypt_msg = ...

    # 5. pub/sub 라우팅
    self.queues[symbol].put(...)
```

**권장 액션**:
```
services/quote_kis.py (현재)
├── services/quote_kis.py (_handle_message 제거)
└── services/_kis_message_handler.py (신규: 상태기계)
    ├── handle_approval_key(msg)
    ├── handle_token_update(msg)
    ├── handle_quote(msg)
    ├── handle_execution(msg)
    └── _aes_decrypt(msg)
```

**예상 작업량**: 6시간 (분할 + 상태기계 리팩토링)

---

### M2: ThreadPoolExecutor max_workers 불일관
**파일**: 6개 (advisory_service, watchlist_service, macro_service, pipeline_service, market_board, advisory_fetcher)
**심각도**: 🟡 MEDIUM
**범주**: 성능 튜닝

**현황**:
```
services/advisory_service.py:169,220      max_workers=7, 8
services/watchlist_service.py:223         max_workers=min(10, len(items))
services/macro_service.py:28              max_workers=8
services/pipeline_service.py:264          max_workers=3
stock/advisory_fetcher.py:125             max_workers=4
stock/market_board.py:100,206             max_workers=10, 20
```

**문제**:
- 튜닝 기준 불명확 (왜 pipeline은 3일까?)
- I/O vs CPU 혼동
- 시스템 리소스 낭비/부족 가능

**권장 액션**:
```python
# services/parallel.py (신규)
import os
from concurrent.futures import ThreadPoolExecutor

class ParallelExecutor:
    """ThreadPoolExecutor 통일 래퍼"""

    # 기본값 (CPU 코어 기준)
    WORKERS = {
        "io_light": 4,           # 빠른 I/O (KIS API)
        "io_heavy": 8,           # 무거운 I/O (DART, yfinance)
        "cpu": 2,                # CPU 집약적 (지표 계산)
        "batch": 12,             # 배치 병렬 (스크리닝)
    }

    @staticmethod
    def map(task_type: str, fn, args, max_retries=0):
        """병렬 실행 + 선택적 재시도"""
        workers = ParallelExecutor.WORKERS.get(task_type, 4)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            results = [ex.submit(fn, *arg) for arg in args]
            return [r.result() for r in results]  # 예외 전파

# 사용 예
from services.parallel import ParallelExecutor
results = ParallelExecutor.map("io_heavy", fetch_data, symbols)
```

**예상 작업량**: 4시간 (래퍼 작성 + 6개 서비스 마이그레이션)

**선택 여부**: ⭐ 선택 (현재 안정적이면 후순위)

---

### M3: except Exception 과도 (세부 예외 분리)
**파일**: `services/quote_kis.py` (11회), `services/order_fno.py` (7회), `services/watchlist_service.py` (8회)
**심각도**: 🟡 MEDIUM
**범주**: 견고성 / 디버깅

**문제**:
너무 넓은 예외 캐치로 버그 추적 어려움.

**현황**:
```python
# ❌ 나쁜 예 (quote_kis.py:55)
try:
    data = json.loads(msg)
except Exception:  # JSON, 네트워크, 파싱 모두 캐치
    pass  # 버그 무시!

# ❌ 나쁜 예 (order_fno.py:71)
try:
    order = ...
except Exception:
    pass  # 어떤 예외인지 모름

# ✅ 좋은 예 (quote_kis.py:272)
except Exception as e:
    logger.error("[QuoteService] WS 오류: %s — %.0f초 후 재연결", e, backoff)
    # 로깅은 있지만 여전히 Exception
```

**권장 액션**:
```python
# ❌ Before
except Exception:
    pass

# ✅ After
except json.JSONDecodeError as e:
    logger.warning("메시지 파싱 실패: %s", e)
except (ConnectionError, TimeoutError) as e:
    logger.warning("KIS 연결 실패: %s", e)
    # fallback 전환
except ValueError as e:
    logger.error("데이터 변환 실패: %s", e)
except Exception as e:
    logger.error("예상 외 오류: %s", type(e).__name__, exc_info=True)
    raise  # 중요한 에러는 전파
```

**적용 파일**:
- `quote_kis.py`: 11건 → 5건 선택 (WS, fallback 관련)
- `order_fno.py`: 7건 → 3건 선택 (API 실패, 파싱)
- `watchlist_service.py`: 8건 → 2건 선택 (데이터 조회 실패)

**예상 작업량**: 4시간 (선택적 수정)

---

### M4: import json 미사용 제거
**파일**: `services/order_service.py:7`
**심각도**: 🟡 MEDIUM (하지만 사소함)
**범주**: Import 정리

**코드**:
```python
# services/order_service.py:7
import json  # ❌ 사용 안 됨

# (파일 전체 검사 결과 json.* 호출 없음)
```

**수정**:
```python
# 7번 줄 삭제
```

**예상 작업량**: 0.1시간

---

### M5: import math 미사용 제거
**파일**: `services/pipeline_service.py:9`
**심각도**: 🟡 MEDIUM (하지만 사소함)
**범주**: Import 정리

**코드**:
```python
# services/pipeline_service.py:9
import math  # ❌ 사용 안 됨

# (파일 전체 검사 결과 math.* 호출 없음)
```

**수정**:
```python
# 9번 줄 삭제
```

**예상 작업량**: 0.1시간

---

### M6: _validate_market() 공용화
**파일**: `services/order_service.py:_validate_market()`
**심각도**: 🟡 MEDIUM
**범주**: API 공용화

**문제**:
`order_service.py`에만 있는 헬퍼 함수. 다른 서비스도 필요할 수 있음.

**현황**:
```python
# services/order_service.py:XX
def _validate_market(market: str) -> bool:
    """시장 코드 검증 (KR/US/FNO)"""
    return market in ("KR", "US", "FNO")
```

**권장 액션**:
```python
# stock/utils.py에 추가
def is_valid_market(market: str) -> bool:
    """시장 코드 유효성 검증"""
    return market in ("KR", "US", "FNO")

# services/order_service.py에서 사용
from stock.utils import is_valid_market
if not is_valid_market(market):
    raise ValueError(...)
```

**예상 작업량**: 0.5시간

---

## 🟢 LOW 우선순위 (3개 항목)

### L1: yf_client.py 분할 (시세/재무)
**파일**: `stock/yf_client.py` (943줄, 18함수)
**심각도**: 🟢 LOW
**범주**: 조직화 (선택적)

**현황**:
- 시세 함수 (price, metrics, valuation)
- 재무 함수 (financials, segments, forward_estimates)
- 검증 함수 (validate_ticker)

**참고**: 현재 기능이 만족스러우면 분할 불필요

**예상 작업량**: 10시간 (선택적)

---

### L2: dart_fin.py 분할
**파일**: `stock/dart_fin.py` (822줄, 15함수)
**심각도**: 🟢 LOW
**범주**: 조직화 (선택적)

**참고**: DART API 통합/마이그레이션 시 검토

**예상 작업량**: 10시간 (선택적)

---

### L3: AsyncIO vs ThreadPoolExecutor 혼재
**파일**: 다수
**심각도**: 🟢 LOW
**범주**: 일관성 (선택적)

**현황**:
- `quote_kis.py`, `quote_overseas.py`, `reservation_service.py` → `asyncio`
- 6개 서비스 → `ThreadPoolExecutor`

**참고**: 각각 용도가 명확하면 유지 가능 (WS는 asyncio, 배치는 ThreadPoolExecutor)

**예상 작업량**: 비용 대비 이득 없음 (선택 안 함)

---

## 📊 종합 액션 계획

### Phase 1: 즉시 (1일, 2시간)
```
- [ ] H3: ValueError → ServiceError (watchlist_service 4줄)
- [ ] M4, M5: import 정리 (2줄)
작업량: 1시간
```

### Phase 2: 1주 (40시간)
```
- [ ] H1: advisory_service.py 분할 (8시간)
- [ ] H5: get_regime_with_context() 통합 (2시간)
- [ ] M6: _validate_market() 공용화 (1시간)
작업량: 11시간
```

### Phase 3: 2주 (60시간)
```
- [ ] H2: market_board_service.py 신규 (6시간)
- [ ] H4: portfolio_advisor_service 분할 (10시간)
- [ ] M1: quote_kis 분할 (6시간)
- [ ] M3: except Exception 세부화 (4시간)
- [ ] M2: ParallelExecutor 래퍼 (4시간, 선택)
작업량: 30시간
```

### Phase 4: 선택 (후순위)
```
- [ ] L1: yf_client.py 분할
- [ ] L2: dart_fin.py 분할
```

---

## ✅ 체크리스트

### 즉시 실행 (우선순위)
- [ ] H3, M4, M5 → PR #1 (1시간, 1일 내)
- [ ] H1, H5 → PR #2 (11시간, 1주)
- [ ] H2, H4 → PR #3 (16시간, 2주)
- [ ] M1, M3 → PR #4 (10시간, 2주)

### 최종 검증
- [ ] 각 PR별 unit test 추가
- [ ] 통합 테스트 실행
- [ ] CLAUDE.md 규칙 재확인

---

## 📈 예상 효과

| 항목 | 현재 | 개선 후 |
|------|------|--------|
| 평균 파일 크기 | 944줄 | <500줄 |
| 함수당 라인 수 | 70줄 | <50줄 |
| 테스트 용이성 | 어려움 | 쉬움 |
| 유지보수 난도 | 높음 | 중간 |
| CLAUDE.md 준수 | 95% | 100% |

---

## 📝 최종 통계

```
총 발견 항목        14개
├─ HIGH            5개
├─ MEDIUM          6개
└─ LOW             3개

즉시 처리 필요      3개 (H3, M4, M5)
1주 내 처리        2개 (H1, H5)
2주 내 처리        6개 (H2, H4, M1, M2, M3, M6)
선택적 처리         3개 (L1, L2, L3)

추정 총 작업량     80~120시간
권장 PR 개수        4~5개
예상 리스크        낮음 (레거시 변경 없음)
```

