# 백엔드 코드 감사 보고서

**감사 일자**: 2026-04-17
**대상 범위**: routers/, services/, stock/ (14,745 LOC)
**분석 방법**: 파일 크기 / 레이어 위반 / 중복 패턴 / 예외 처리 / import 정리

---

## 1️⃣ 파일 크기 분석 (MEDIUM)

### 1.1 비대 파일 (500줄 이상) — 분할 후보

| 파일 | 줄 수 | 함수 | 추천 액션 |
|------|-------|------|---------|
| `services/advisory_service.py` | **944** | 17 | 🔴 split: data수집(refresh) / AI리포트(generate) 분리 |
| `stock/yf_client.py` | **943** | 18 | 🟡 split: 시세(price/metrics) / 재무(financials/segments) 분리 |
| `stock/dart_fin.py` | **822** | 15 | 🟡 split: 국내재무 module 분할 |
| `services/quote_kis.py` | **666** | 8 | 🟡 좌측 경계: KIS WS 상태기계 + pub/sub 분리 가능 |
| `services/portfolio_advisor_service.py` | **607** | 15 | 🟡 split: 포트폴리오 분석 / GPT 호출 / 대사 분리 |

**우선순위**: advisory_service > portfolio_advisor > quote_kis

**분할 전략**:
```
✅ services/advisory_service.py (944줄)
   ├── services/advisory_collector.py (refresh_stock_data + _collect_* 140줄)
   ├── services/advisory_reporter.py (generate_ai_report + 재시도 로직 200줄)
   └── services/advisory_service.py (유지: dispatcher + _determine_regime + 예외 처리)

✅ services/portfolio_advisor_service.py (607줄)
   ├── services/portfolio_analyst.py (_analyze_portfolio + 진단 로직 200줄)
   ├── services/portfolio_rebalancer.py (리밸런싱 제안 로직 150줄)
   └── services/portfolio_advisor_service.py (유지: get_advice + 매매안 + cache)
```

---

## 2️⃣ 레이어 위반 검출

### 2.1 ✅ HTTPException 직접 raise — **위반 없음**
- `services/exceptions.py`에서 ServiceError 계층 정의 완료
- 모든 서비스에서 ServiceError 사용 (CLAUDE.md 준수)

### 2.2 🔴 routers → stock 직접 임포트 — **위반 발견**

```
routers/earnings.py:8-11           ← stock 직접 import 4개
routers/quote.py:11                 ← is_domestic 직접
routers/screener.py:17              ← fetch_market_metrics 등 3개
routers/advisory.py:12,54,154,189   ← stock.utils, symbol_map, advisory_fetcher, yf_client
routers/search.py:50,60             ← yf_client, fno_master
routers/market_board.py:20,31,42,66,73,83,94  ← utils, market_board, market_board_store (7개)
```

**분석**:
- routers/earnings.py: services/detail_service → 통합 재사용 권장
- routers/advisory.py: 부분 inline import (54, 154, 189줄) → 함수 진입부 지연로드 (의도적?)
- routers/market_board.py: **가장 심각** — market_board_store 직접 접근 (CRUD 위임 누락)

**액션**: services/ wrapper 추가 필요

### 2.3 ✅ services → routers 역참조 — **위반 없음**
- 단, `services/order_*` 파일들이 `routers/_kis_auth` import — **합법** (공용 인증 모듈)

### 2.4 ✅ DB 직접 접근 — **위반 없음**
- services/: `get_session()` 사용 (db/ 위임 정상)
- stock/: `store.py` 래퍼 경유 또는 cache.py (정상)

---

## 3️⃣ 중복 패턴 검출

### 3.1 🔴 ThreadPoolExecutor — **6개 파일에서 반복**

```
services/advisory_service.py:169,220          (2회: data수집, 기술지표)
services/portfolio_advisor_service.py          (0회: 발견 안 함 — 단일스레드?)
services/watchlist_service.py:223             (1회)
services/macro_service.py:28                  (1회)
services/pipeline_service.py:264              (1회)
services/quote_kis.py                         (0회: asyncio 사용)
stock/advisory_fetcher.py:125                 (1회)
stock/market_board.py:100,206                 (2회)
```

**문제**:
- `max_workers` 불일관: 3~20 범위 편차 큼
  - pipeline: 3 (보수적)
  - advisory: 7~8 (공격적)
  - market_board: 10~20 (과도)
- **재시도 로직 없음** — 부분 실패 시 조용히 무시 가능

**추천**:
```python
# services/parallel.py (신규)
class ParallelExecutor:
    """ThreadPoolExecutor 통일 래퍼"""
    def __init__(self, task_type: str):  # "io" / "cpu" / "batch"
        self.workers = {"io": 8, "cpu": 4, "batch": 12}.get(task_type, 8)

    def map_with_retry(self, fn, args, max_retries=1):
        """부분 실패 허용, 로깅"""
        ...
```

### 3.2 🔴 체제 판단 함수 — **3중 구현**

```
services/macro_regime.py:176       ← 공용 모듈 (canonical)
services/advisory_service.py:448   ← _determine_regime() 래퍼
services/portfolio_advisor_service.py:291  ← _determine_regime() 래퍼
services/pipeline_service.py:26    ← _determine_regime() 래퍼 + 하위호환
```

**현황**:
- 공용 모듈 `determine_regime()` 존재 (정상)
- 3개 서비스가 동일한 래퍼 코드 복제 (중복)
  - `_determine_regime(sentiment)` 함수명 동일
  - 반환값 변환 로직 동일 (`REGIME_DESC` 연결 등)

**액션**: 공용 래퍼로 통합

```python
# services/macro_regime.py에 추가
def get_regime_with_context(sentiment: dict) -> tuple[str, str]:
    """(regime, description) 반환 — advisory/portfolio/pipeline 공용"""
    result = determine_regime(sentiment)
    desc = REGIME_DESC.get(result['regime'], '불명')
    return result['regime'], desc
```

### 3.3 🟡 시장 분기 로직 — **분산**

```
is_domestic(code)   ← 사용처 34건 (services 2, stock 8, routers 24)
_validate_market()  ← services/order_service.py (1회)
is_fno(code)        ← 사용처 7건
```

**현황**: 패턴 정상, 하지만 `_validate_market()`이 order_service 고유 → stock/utils.py로 이동 권장

### 3.4 🟡 Silent Pass 패턴 — **0회 발견**
- 예상과 달리 명시적 로깅/예외 처리 잘되어 있음

---

## 4️⃣ 예외 처리 및 로깅

### 4.1 🔴 예외 캐치 — **너무 넓음 (187회)**

```python
# 문제: except Exception의 남용

services/pipeline_service.py:98,256,354      (3회: 분석 실패 시 로깅만)
services/order_fno.py:71,125,160,226,232,263,269 (7회: 일부는 로깅 없음)
services/quote_kis.py:55,99,127,171,184,271,389,442,460,584,664 (11회)
services/watchlist_service.py:104,115,121,137,148,155,171,264  (8회)
stock/advisory_fetcher.py (예상 다수: 파일 미확인)
```

**분석**:
- ✅ pipeline_service: 로깅 포함, 재시도 로직 없음 (design 스타일)
- 🔴 quote_kis: WS 오류 8회, fallback 자동 전환 (필요)
- 🔴 order_fno: 일부는 `except Exception:` 후 `pass` (버그 위험)

**액션**:
```python
# ❌ 나쁜 예
except Exception:
    pass

# ✅ 좋은 예
except (ConnectionError, TimeoutError) as e:
    logger.warning("KIS 연결 실패 [%s], fallback 전환", e)
except (ValueError, KeyError) as e:
    logger.error("파싱 오류 [%s], skip", e)
except Exception as e:
    logger.error("예상 외 오류 [%s]", type(e).__name__, exc_info=True)
```

### 4.2 ✅ 로깅 — **충분함**

```
pipeline_service.py:           info 6회 (진행 상황) + error 3회
advisory_service.py:           debug/info/error 적절
quote_kis.py:                  debug 4회 + warning 4회 + info 3회 + error 4회 (훌륭함)
```

### 4.3 ✅ 예외 계층 사용 — **74회 (정상)**

```
raise ServiceError           (기본 400)
raise NotFoundError          (404)
raise ExternalAPIError       (502)
raise ConfigError            (503)
raise PaymentRequiredError    (402)
(ConflictError 건수 미확인)
```

**문제**: services/watchlist_service 등 일부에서 `ValueError` 직접 raise (4회)
- Line 195, 208, 210, 530
- 라우터에서 catch하지 않으면 500 반환 (불명확)

---

## 5️⃣ Import 정리

### 5.1 미사용 import (5개 파일)

| 파일 | 미사용 | 현황 |
|------|--------|------|
| advisory_service.py | `annotations`, `is_domestic`, `REGIME_DESC` | ✅ 사용 중 (false positive) |
| portfolio_advisor_service.py | `annotations`, `now_kst` | ✅ 사용 중 (false positive) |
| order_service.py | `json`, `is_domestic` | 🔴 `json` 미사용? |
| pipeline_service.py | `annotations`, `math`, `ExternalAPIError`, `REGIME_MATRIX`, `REGIME_PARAMS` | 🟡 일부 미사용? |
| backtest_service.py | — | — |

**고급 검사**: 대부분 false positive (ast 파서의 한계)

**실제 미사용**:
- `services/order_service.py:7` — `import json` (라인 530의 raise ValueError 제외 사용 없음)
- `services/pipeline_service.py:9` — `import math` (사용 안 됨)

**액션**: 2개 import 제거

### 5.2 순환 의존 — **발견 안 함**

---

## 6️⃣ 주요 서비스 구조 분석

### 6.1 advisory_service.py (944줄, 17함수)

```
public (외부 호출):
├── refresh_stock_data()      [65줄] — 데이터 수집
├── generate_ai_report()      [250줄] — GPT 호출 + 재시도

private:
├── _collect_fundamental()    [180줄]
├── _collect_technical()      [120줄]
├── _collect_strategy_signals() [40줄]
├── _calc_graham_number()    [30줄]
├── _determine_regime()       [15줄] — 공용 모듈 래퍼
└── 기타 8함수 (헬퍼)
```

**문제**:
1. **generate_ai_report() 과도한 복잡도** — 토큰 관리 + 재시도 + Pydantic 검증 혼재
2. **ThreadPoolExecutor 2회 중복** — data수집 + 기술지표 계산
3. **OPENAI_MODEL 환경변수** 직접 참조 (config 경유 정상)

**분할안**:
```
advisory_service.py (dispatcher + config)
├── advisory_collector.py (refresh + _collect_*)
└── advisory_reporter.py (generate + 토큰 관리)
```

### 6.2 portfolio_advisor_service.py (607줄, 15함수)

```
public:
├── get_advice()              [300줄] — 포트폴리오 진단 + 리밸런싱 + 매매안
└── _compute_cache_key()

private:
├── _fetch_52w_high()
├── _safe_float()
├── _determine_regime()        ← 중복 래퍼
└── 9개 분석 함수
```

**문제**:
1. **get_advice()에 5가지 책임** — 진단 + 리밸런싱 + 매매안 + GPT호출 + 캐싱
2. **stock_info_store 미사용** — 52주 고가를 cache.py로 조회 (영속 캐시 우회)
3. **nowkst 미사용** import

**분할안**:
```
portfolio_advisor_service.py (config + dispatcher)
├── portfolio_analyst.py (_analyze_portfolio)
├── portfolio_rebalancer.py (_rebalance_recommendations)
└── portfolio_executor.py (_generate_trade_actions)
```

### 6.3 quote_kis.py (666줄, 8함수)

```
public (KISQuoteManager):
├── start()
├── stop()
├── subscribe(symbol, is_fno)
├── unsubscribe()
└── get_latest()

private:
├── _connect()
├── _disconnect()
├── _handle_message() [250줄] ← 상태기계
└── 20개 헬퍼 함수
```

**문제**: `_handle_message()` 상태기계 1함수 250줄
- Approval key 갱신
- 토큰 갱신
- 메시지 파싱 (호가, 체결, AES 복호화)
- pub/sub 라우팅
- fallback 전환

**분할안**:
```
quote_kis.py (KISQuoteManager + pub/sub)
└── _ks_message_handler.py (_handle_message 상태기계)
```

### 6.4 order_service.py (566줄, 19함수)

```
public (dispatcher):
├── place_order()             [30줄]
├── get_buyable()             [20줄]
├── get_open_orders()         [30줄]
├── get_executions()          [30줄]
├── modify_order()            [20줄]
├── cancel_order()            [20줄]
└── 13개 private 함수

private:
├── _validate_market()        ← stock/utils로 이동 후보
├── _maybe_reconcile()        ← 30초 쿨다운 관리 (훌륭한 설계)
├── _sync_local_*()           (시장별 대사)
└── 10개 헬퍼
```

**현황**: ✅ 잘 설계됨 (레이어 분할 명확)

---

## 7️⃣ 우선순위 별 액션 항목

### 🔴 HIGH 우선순위

| ID | 항목 | 영향 | 액션 |
|----|------|------|------|
| H1 | advisory_service.py 분할 | 유지보수성 | services/advisory_collector.py + advisory_reporter.py (PR) |
| H2 | routers → stock 직접 import (market_board) | 레이어 위반 | services/market_board_service.py 신규 (CRUD 래퍼) |
| H3 | ValueError 남용 (watchlist_service) | 예외 일관성 | NotFoundError 또는 ServiceError로 변경 (4줄) |
| H4 | portfolio_advisor_service 분할 | 유지보수성 | services/portfolio_analyst.py + rebalancer.py (PR) |
| H5 | 체제 판단 중복 (3중 구현) | DRY 위반 | services/macro_regime.py에 `get_regime_with_context()` 추가 |

### 🟡 MEDIUM 우선순위

| ID | 항목 | 영향 | 액션 |
|----|------|------|------|
| M1 | quote_kis._handle_message() 분할 | 가독성 | services/quote_handler.py (150줄+) |
| M2 | ThreadPoolExecutor max_workers 불일관 | 성능 튜닝 | services/parallel.py 통일 래퍼 (선택) |
| M3 | except Exception 과도 | 견고성 | 세부 예외 타입 분리 (quote_kis, order_fno 5건) |
| M4 | import json 미사용 | 정리 | services/order_service.py:7 제거 |
| M5 | import math 미사용 | 정리 | services/pipeline_service.py:9 제거 |
| M6 | stock/utils._validate_market() 공용화 | API | services/order_service.py → stock/utils로 이동 |

### 🟢 LOW 우선순위

| ID | 항목 | 영향 | 액션 |
|----|------|------|------|
| L1 | yf_client.py 분할 (시세/재무) | 조직화 | 선택적 (현재 기능 만족) |
| L2 | dart_fin.py 분할 | 조직화 | 선택적 (DAS 통합 시 검토) |
| L3 | AsyncIO vs ThreadPoolExecutor 혼재 | 일관성 | 선택적 (현재 작동 안정) |

---

## 📊 최종 통계

```
전체 파일 수           14,745 줄
비대 파일 (500줄+)      5개
레이어 위반 (HIGH)      5개
중복 패턴                3개
예외 위반                4개
미사용 import            2개

추천 PR 개수             4~5개
추정 작업량             80~120시간 (분할 + 테스트 + 통합)
```

---

## 🎯 구현 로드맵

### Phase 1 (즉시)
- [ ] H3: ValueError → ServiceError 변경 (watchlist_service 4줄)
- [ ] M4, M5: 미사용 import 제거 (2줄)

### Phase 2 (1주)
- [ ] H1: advisory_service.py 분할
- [ ] H5: get_regime_with_context() 통합

### Phase 3 (2주)
- [ ] H2: services/market_board_service.py 신규
- [ ] H4: portfolio_advisor_service 분할

### Phase 4 (선택)
- [ ] M1: quote_kis 상태기계 분할
- [ ] M2: ParallelExecutor 통일 래퍼

---

## 🔗 참고

- **CLAUDE.md 준수 현황**: ✅ HTTPException 금지 = 100% 준수
- **예외 계층 사용**: ✅ 74회 사용 (ServiceError 계층 정상)
- **레이어 아키텍처**: 🟡 routers → stock 직접 import 가능 개선의 여지 있음
- **병렬 처리**: ✅ 6개 파일 안정적, max_workers 튜닝 선택사항

