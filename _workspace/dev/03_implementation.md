# GREEN 단계 — 구현 결과

작성일: 2026-05-09
작성자: BackendDev (개발팀장 위임)

## 변경/신규 파일 목록

### 코드 변경 (6 파일)

| 파일 | 변경 유형 | 라인 증감 | 요건 |
|------|----------|----------|------|
| `db/repositories/backtest_repo.py` | 수정 | +35 / -3 | REQ-FIX-01 |
| `services/backtest_service.py` | 수정 | +85 / -10 | REQ-FIX-01/04/05/06 |
| `services/local_backtest/data_loader.py` | 전면 재작성 | +100 / -65 | REQ-FIX-02 |
| `services/local_backtest/engine.py` | 수정 | +75 / -8 | REQ-FIX-03/04 |
| `routers/backtest.py` | 수정 | +50 / -10 | REQ-FIX-06 |
| `main.py` | 수정 | +35 / -3 | REQ-FIX-01/06 |

### 테스트 신규 (6 파일, 25 케이스)

| 파일 | 라인 |
|------|------|
| `tests/unit/test_backtest_local_alembic_safe.py` | 152 |
| `tests/unit/test_local_backtest_data_loader_cache.py` | 116 |
| `tests/unit/test_local_backtest_engine_datetime.py` | 132 |
| `tests/unit/test_local_backtest_jsonable.py` | 75 |
| `tests/unit/test_backtest_mcp_vps_error.py` | 90 |
| `tests/unit/test_backtest_router_logging.py` | 130 |

## 핵심 구현 요약

### REQ-FIX-01: alembic 안전화 (1순위, 가장 유력)

**`db/repositories/backtest_repo.py`**:
- `_is_symbols_column_missing(err)` 헬퍼: PostgreSQL/SQLite/MySQL 메시지 패턴 매칭
- `BacktestRepository.create_job()`: `OperationalError`/`ProgrammingError` 캐치 후
  `symbols` 컬럼 부재 패턴이면 페이로드에서 제외하고 1회 재시도
- 다른 SQL 에러는 그대로 raise → 상위에서 ServiceError 변환

**`services/backtest_service.py:run_local_backtest`**:
- `save_backtest_job` 호출을 try/except로 감싸 `ServiceError("백테스트 작업 등록 실패 ...")` 변환
- raw 500 → 400 ServiceError로 변환 (사용자 친화)

**`main.py:lifespan`**:
- `alembic upgrade head` 후 `script.get_current_head()` vs `MigrationContext.get_current_revision()`
  비교 → 불일치 시 `print("[오류] alembic 미적용 감지: current=... head=...")` 명확 알림
- 부팅은 막지 않음 (graceful 운영)

### REQ-FIX-02: data_loader 캐시

**`services/local_backtest/data_loader.py`** 전면 재작성:
- 캐시 값을 `(df, ts)` 튜플로 변경
- `_cache_get(key)`: `time.time() - ts > 600` (10분) 시 stale 판정
- `load()`: 1차 None 시 `time.sleep(5)` 후 1회 재시도
- 최종 None은 캐시 미저장 (다음 호출 재시도 가능)
- `logger.warning("[REQ-FIX-02] data_loader 미스 ...")` 가시화

### REQ-FIX-03: engine datetime normalize

**`services/local_backtest/engine.py`**:
- 종목별 OHLCV fetch 직후: `df.index.tz_localize(None).normalize()` 통일
- `_idx_for(df, d)`: `pd.Timestamp(d).normalize()` 검색
- 매칭 실패 시 `logger.debug("[REQ-FIX-03] _idx_for 매칭 실패 ...")` (silent skip 가시화)

### REQ-FIX-04: JSON 직렬화 안전화

**`services/local_backtest/engine.py:_to_jsonable(obj)`** 신규:
- numpy float* / int* / bool_ / ndarray → Python native
- pd.Timestamp / datetime / date → ISO 문자열
- NaN / Inf → None (JSON spec 호환)
- dict / list / tuple → 재귀 변환
- numpy import 실패 시 graceful (try/except ImportError)

**`services/backtest_service.py:run_local_backtest`**:
- `_to_jsonable(result_json)` + `_to_jsonable(sim.metrics)` 응답 직전 적용 (이중 안전망)
- 직렬화 실패 시 `ExternalAPIError("결과 직렬화 실패: ...")` + telemetry `backtest.local.fail.serialize`

### REQ-FIX-05: MCP 'vps' 친화 메시지

**`services/backtest_service.py:_extract_mcp_content`**:
- `_DATA_PREP_FAILURE_PATTERNS = ("vps", "데이터 준비 실패", "data preparation failed")`
- `_is_data_prep_failure(error_msg)` 패턴 매칭 헬퍼
- success=false 분기에서 패턴 일치 시:
  - 사용자: "백테스트 데이터 조회 실패: 종목 코드를 확인하거나 다른 날짜 범위로 재시도하세요. (외부 backtester 데이터 준비 실패)"
  - 운영: `logger.warning("MCP backtester data preparation error: %s", error_msg)` 보존
- `# TODO: backtester 'vps' 키 누락 fix 필요 (open-trading-api/backtester)` 코멘트

### REQ-FIX-06: 라우터 로깅 + error_id + telemetry

**`services/backtest_service.py`**:
- `_classify_local_failure(exc)` — db_error/serialize/timeout/data_load/unknown 분류
- `run_local_backtest` 진입부 entry 로그 + 모든 except에서 `_tel.record_event("backtest.local.fail.{cause}")` 증가
- 정상 종료 시 `_tel.record_event("backtest.local.success")` + `_tel.observe("backtest.local.duration_ms", ...)` + exit 로그

**`routers/backtest.py`**:
- `run_local`/`run_preset`/`run_custom`/`run_batch` 4개 핸들러에 entry/exit 로그
  (preset, len(symbols), market, dates, user_id / job_id, status)

**`main.py:service_error_handler`**:
- `error_id = uuid.uuid4().hex[:8]` 발행
- 응답 본문에 `error_id` 추가 (기존 `detail` 보존, 후방 호환 100%)
- `logger.error("[%s] ServiceError ...", error_id, exc_info=True)` — 운영 stack trace 매칭용

## 도메인 자문 (OrderAdvisor) 검토

1. **symbols 컬럼 NULL 시 데이터 무결성**
   - `BacktestJob.symbols`는 `nullable=True` JSON 컬럼 — NULL 허용
   - `to_dict()` 정상 NULL 반환
   - 후속 조회/리스트는 `symbols` 미참조
   - 응답 `result_json` 내 `symbols` 리스트는 별도 저장 → 사용자 화면 영향 없음
   - **결론: 데이터 무결성 영향 없음**

2. **MCP 'vps' 친화 메시지의 사용자 의사결정 충분성**
   - 행동 가이드 2개: 종목 코드 확인 / 날짜 범위 변경
   - 'vps' 단어는 의미 불명 → 노출 차단 정당
   - 운영 디버깅: `docker logs`에 원본 보존
   - **결론: 충분**

## REQ-OPS-07 (CloudWatch) — 미실행

본 phase 범위 외. Terraform 변경 + IAM 역할 별도 phase 권고. 본 작업에서
`docker-compose.prod.yml` 미터치.
