# 요건서: 백테스트 500 버그 픽스 — 두 갈래

**원천 plan**: `/Users/kimdukki/.claude/plans/yfinance-jolly-token.md` (사용자 승인 완료, 2026-05-09)
**작성일**: 2026-05-09
**범위**: 백엔드 전용 (라우터 + 서비스 + 마이그레이션 안전화)
**도메인 의사결정**: plan 승인 단계 확정 — 도메인팀장 단계 생략. 필요 시 OrderAdvisor만 ad-hoc 호출.

---

## 배경 (Context)

운영 환경(dkstock.cloud)에서 백테스트 500 오류 두 갈래 보고:

1. **MCP 단일 종목**: `오류: MCP 백테스트 실패: 백테스트 실패: 데이터 준비 실패: 'vps'` — 외부 backtester(QuantConnect Lean, 별도 EC2) 측 데이터 준비 단계 에러를 stock-manager가 그대로 wrap만 함.
2. **로컬 포트폴리오 (2종목 이상)**: 메시지 없이 raw HTTP 500 — 종목 무관 100% 재현.

두 번째 케이스는 종목 무관·100% 재현 = 입력 독립 = 인프라/SQL 레이어 에러 패턴. 가장 유력한 원인은 `e1f2a3b4c5d6_add_backtest_symbols.py` 마이그레이션이 운영 EC2에 미적용되어 `BacktestJob.symbols` 컬럼 부재 → `save_backtest_job(..., symbols=...)` SQL 에러 → ServiceError 변환 회피 → raw 500.

**사용자 합의 수정 범위**: 추정 4건 모두 + 로깅 강화 + 운영 에러 가시성 개선.

운영 docker logs는 SSH 차단으로 미확보 — 사용자 측 직접 실행 필요(런북). 그동안 코드 수정은 4 후보 모두 graceful 처리하여 stack trace 없이도 진행 가능.

---

## 요건 목록

### [REQ-FIX-01] save_backtest_job alembic 마이그레이션 안전화 (1순위)

**설명**: alembic 미적용 환경에서 `BacktestJob.symbols` 컬럼 부재 시 SQL 에러가 `try/except Exception` 보다 앞 라인에서 raise → ServiceError 변환 회피 → raw 500.

**수용 기준**:
- `services/backtest_service.py:534-545` `strategy_store.save_backtest_job(..., symbols=deduped, ...)` 호출을 `try/except (Exception)` + `logger.exception` 으로 감싸 `ServiceError("백테스트 작업 등록 실패 (DB 마이그레이션 필요): {detail}")` 변환
- `db/repositories/backtest_repo.py` 또는 `stock/strategy_store.py`의 `create_job`/`save_backtest_job`: `symbols` 컬럼 부재 감지 시 INSERT 페이로드에서 자동 제외 (graceful) — `inspect(engine).get_columns("backtest_jobs")` 또는 SQLAlchemy `OperationalError` 캐치 후 재시도
- `main.py` lifespan: `alembic upgrade head` 실행 후 `alembic_command.current()`로 `alembic_version` head 일치 검증 → 불일치 시 `logger.error("alembic 미적용: current={}, head={}")` 명확 알림 (현재는 무음 실패 가능)
- 후방 호환: 마이그레이션 적용된 환경에선 그대로 `symbols` JSON 저장

**테스트 힌트**: `tests/unit/test_backtest_local_alembic_safe.py`
- (a) symbols 컬럼 존재 → 정상 저장
- (b) symbols 컬럼 부재 mock(SQLAlchemy `OperationalError`) → graceful INSERT(symbols 누락) + 로그 + 200 응답
- (c) save 단계에서 진짜 SQL 에러(다른 컬럼) → `ServiceError` 변환 + 사용자 친화 메시지

**레이어**: `services/`, `db/repositories/` 또는 `stock/strategy_store.py`, `main.py`

---

### [REQ-FIX-02] data_loader 캐시 None 영구화 버그 (2순위)

**설명**: `services/local_backtest/data_loader.py:89-100`이 yfinance None 응답을 영구 캐시 → 후속 호출도 None → 포트폴리오 일부 종목 데이터 부재.

**수용 기준**:
- `if df is None or (isinstance(df, pd.DataFrame) and df.empty): return None` — 캐시 저장 안 함 (조기 return, 다음 호출에서 재시도 가능)
- yfinance 1회 재시도 (5초 대기) — 일시적 rate limit 대응
- `_cache` TTL 10분 추가 (`time.time()` 기반 dict) — 영구 캐시 안 함
- 부분 실패는 `failures` 리스트로 기존 흐름 보존 (engine 측이 처리)

**테스트 힌트**: `tests/unit/test_local_backtest_data_loader_cache.py`
- (a) yfinance 정상 → 캐시 저장 + 두번째 호출 캐시 적중
- (b) yfinance None → 캐시 저장 안 함 + 두번째 호출 재시도
- (c) 1차 None → 5s 대기 → 2차 정상 → 정상 데이터 반환
- (d) TTL 만료 → 재조회

**레이어**: `services/local_backtest/`

---

### [REQ-FIX-03] engine.py datetime 미스매치 (3순위)

**설명**: `services/local_backtest/engine.py:118-160`에서 `pd.Timestamp(date_obj)` vs `df.index` 비교 시 timezone/precision 차이로 `_idx_for()` None 반환 → 거래 신호 silent skip 또는 IndexError.

**수용 기준**:
- 모든 종목 DataFrame 로드 직후 `df.index = df.index.normalize().tz_localize(None) if df.index.tz else df.index.normalize()` — 시간 부분 00:00:00 + naive 통일
- `_idx_for()`에서 `pd.Timestamp(d).normalize()` 검색
- `_idx_for()` None 반환 시 `logger.debug(f"거래일 매칭 실패: {sym}/{d}")` (현재 silent)

**테스트 힌트**: `tests/unit/test_local_backtest_engine_datetime.py`
- (a) tz-aware index (Asia/Seoul, UTC) → naive 통일 후 정상 매칭
- (b) 시간 포함 index (10:00:00) → normalize 후 매칭
- (c) 하루 누락된 종목 → silent skip + 로그 + 다른 종목 정상

**레이어**: `services/local_backtest/`

---

### [REQ-FIX-04] JSON 직렬화 안전화 (4순위)

**설명**: `result_json` 안의 numpy float/int, pd.Timestamp가 FastAPI JSON 인코딩 단계에서 실패 → raw 500.

**수용 기준**:
- `services/local_backtest/engine.py` 결과 빌드 시 모든 numeric → Python native(`float()`/`int()`) 변환
- `equity_curve`/`trades`의 datetime은 `.isoformat()` 문자열로 직렬화
- `services/backtest_service.py:run_local_backtest` 응답 직전 `_to_jsonable(obj)` 헬퍼 적용 — numpy/pandas 타입을 재귀적으로 native 변환

**테스트 힌트**: `tests/unit/test_local_backtest_jsonable.py`
- (a) numpy float64/int64 포함 dict → `json.dumps` 통과
- (b) pd.Timestamp 포함 → ISO 문자열 변환
- (c) 중첩 dict/list 재귀 처리

**레이어**: `services/local_backtest/`, `services/backtest_service.py`

---

### [REQ-FIX-05] MCP `'vps'` 사용자 친화 메시지

**설명**: `services/backtest_service.py:67-68`에서 backtester 측 `'vps'` 에러를 그대로 사용자에게 노출. 외부 backtester 본질 fix는 stock-manager 권한 외이므로 사용자 친화 메시지 변환만 처리.

**수용 기준**:
- `_extract_mcp_content` line 66-68에서 `parsed.get("success") is False` 분기 시 `error_msg` 패턴 매칭:
  - `"vps"` / `"데이터 준비 실패"` / `"data preparation failed"` 패턴 포함 시:
    - 사용자 메시지: `"백테스트 데이터 조회 실패: 종목 코드를 확인하거나 다른 날짜 범위로 재시도하세요. (외부 backtester 데이터 준비 실패)"`
  - 그 외 패턴: 기존 `f"MCP 백테스트 실패: {error_msg}"` 유지 (정상)
- 원본 error_msg는 `logger.warning("MCP backtester error: %s", error_msg)`로 보존
- `# TODO: backtester 'vps' 키 누락 fix 필요 (open-trading-api/backtester)` 코멘트 추가 — 외부 레포 트래킹

**테스트 힌트**: `tests/unit/test_backtest_mcp_vps_error.py`
- (a) `success: false + error: "백테스트 실패: 데이터 준비 실패: 'vps'"` → 친화 메시지 ExternalAPIError
- (b) `success: false + error: "데이터 준비 실패: timeout"` → 친화 메시지 (패턴 일치)
- (c) `success: false + error: "전략 검증 실패"` → 기존 메시지(패턴 불일치)
- (d) `success: true + data: [...]` → data 반환 (변경 없음)

**레이어**: `services/`

---

### [REQ-FIX-06] 백테스트 라우터 로깅 강화 + ServiceError error_id

**설명**: 운영에서 stack trace가 docker logs에만 남고 외부 모니터링 부재 — 다음 버그 발생 시 빠른 매칭을 위한 디버깅 인프라 강화.

**수용 기준**:
- `routers/backtest.py`의 `run_local`/`run_preset`/`run_custom`/`run_batch` 4개 엔드포인트에 entry 로그 (preset, len(symbols), market, dates, user_id) + exit 로그 (job_id, duration_ms, status)
- `main.py`의 `@app.exception_handler(ServiceError)` (또는 일괄 예외 핸들러)에 `error_id = uuid.uuid4().hex[:8]` 추가 — 응답 본문에 `error_id` 포함 + `logger.error(f"[{error_id}] {e}", exc_info=True)`로 기록 → 사용자 보고 시 즉시 stack trace 매칭 가능
- `services/_telemetry.py`에 `record_event("backtest.local.success")` / `record_event("backtest.local.fail.{cause}")` 추가 — fail 분류: `db_error`/`data_load`/`timeout`/`serialize`/`unknown`
- 중요: 기존 ServiceError handler가 응답 형식을 이미 가지고 있다면 후방 호환 유지 (`detail`/`message` 필드는 그대로, `error_id`만 추가)

**테스트 힌트**: `tests/unit/test_backtest_router_logging.py`
- (a) `run_local` 정상 호출 → entry/exit 로그 각 1건 + telemetry success
- (b) `run_local` 실패 → entry 로그 + telemetry fail.{cause}
- (c) ServiceError 응답 본문에 `error_id` 키 + 8자리 hex

**레이어**: `routers/`, `main.py`, `services/_telemetry.py`

---

### [REQ-OPS-07] 운영 에러 가시성 (선택, 본 phase 미실행)

**설명**: docker-compose.prod.yml의 `logging.driver: json-file`이 EC2 로컬에만 저장 → CloudWatch 통합 부재.

**상태**: **본 phase 미실행** — Terraform 변경(`infra/modules/compute` IAM 역할 추가) 필요. 별도 phase에서 처리 권고. 본 작업에서는 plan 명시만.

권고 옵션 (다음 phase):
- (A) docker-compose.prod.yml에 `awslogs` 드라이버 추가 + EC2 IAM 역할에 `CreateLogStream`/`PutLogEvents` 권한 부여
- (B) stock-manager 내부 daily 로테이트 파일 핸들러 + nginx 볼륨 마운트로 외부 tail

---

## 단계적 구현 순서 (TDD)

각 Step RED → GREEN → 회귀(`pytest tests/unit/ -v` 전체) → 다음.

| Step | 요건 ID | 사이클 |
|------|---------|--------|
| 1 | REQ-FIX-01 | save_backtest_job alembic 안전화 + main.py 부팅 알림 (가장 유력 1순위 fix) |
| 2 | REQ-FIX-02 | data_loader 캐시 None 미저장 + 재시도 + TTL |
| 3 | REQ-FIX-03 | engine datetime normalize + silent skip 로그 |
| 4 | REQ-FIX-04 | JSON 직렬화 안전화 (`_to_jsonable`) |
| 5 | REQ-FIX-05 | MCP 'vps' 친화 메시지 패턴 매칭 |
| 6 | REQ-FIX-06 | 라우터 entry/exit 로그 + ServiceError error_id + telemetry |

각 Step 완료 시 QA Inspector 경계면 검증.

---

## 회귀 가드

- 기존 MCP 백테스트(preset/custom/batch) 4종 흐름 미터치 — 메시지 변환 한 줄만 추가
- 기존 단위 849 PASS 유지 (베이스라인 + 신규 ~25 PASS)
- DB 스키마 변경 0건 (alembic 마이그레이션 자동 적용 알림만 추가)
- 도메인 알고리즘(safety_grade/macro_regime/포지션사이징) 무영향
- 프론트 변경 0건 (BacktestPage 응답 dict shape 보존)
- KIS_MCP_ENABLED=false 환경 무영향 (로컬 백테스트 단독 동작)
- 후방 호환: alembic 적용된 환경에선 모든 기존 동작 보존, 미적용 환경에선 graceful

## 도메인 자문 트리거

OrderAdvisor를 Agent로 호출:
- alembic 미적용 graceful 처리가 데이터 무결성에 영향 미치는지 검토 (예: symbols 컬럼 누락 저장 시 후속 조회/이력 정합성)
- MCP 'vps' 메시지 변환 시 사용자 의사결정에 충분한 정보가 남는지

다른 도메인 전문가는 본 작업과 무관 (인프라 + 에러 처리 레이어, 알고리즘 미터치).

---

## 검증

```bash
# 단위 회귀
pytest tests/unit/ -v   # 기존 849 + 신규 ~25 PASS

# 로컬 docker-compose 다중 종목 백테스트 (배포 전)
docker-compose up --build
curl -X POST http://localhost:8000/api/backtest/run/local \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"preset":"momentum","symbols":["005930","000660"],"market":"KR","start_date":"2024-01-01","end_date":"2024-12-31"}'
# 200 + equity_curve/trades/per_symbol_contribution 정상

# alembic 미적용 시뮬레이션
alembic downgrade -1
# 다중 종목 백테스트 → 친화적 ServiceError 메시지 확인
alembic upgrade head
# 정상 동작 복귀
```

## 운영 배포 후 사용자 검증 (별도)

```bash
# main 브랜치 push → GitHub Actions 자동 배포 후
ssh -i scripts/stock-manager-bigmac.pem ubuntu@<EC2 호스트>
docker exec stock-manager alembic current
# → e1f2a3b4c5d6 (head)

# 운영 다중 종목 백테스트
# → 200 + 정상 응답
```

운영 docker logs는 사용자 직접 실행 — 본 phase 미포함.
