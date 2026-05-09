# RED 단계 — 테스트 선행 작성 결과

작성일: 2026-05-09
작성자: TestEngineer (개발팀장 위임)

## 신규 테스트 파일 6개 (25 케이스)

| 파일 | 케이스 수 | 요건 ID |
|------|----------|---------|
| `tests/unit/test_backtest_local_alembic_safe.py` | 4 | REQ-FIX-01 |
| `tests/unit/test_local_backtest_data_loader_cache.py` | 4 | REQ-FIX-02 |
| `tests/unit/test_local_backtest_engine_datetime.py` | 3 | REQ-FIX-03 |
| `tests/unit/test_local_backtest_jsonable.py` | 5 | REQ-FIX-04 |
| `tests/unit/test_backtest_mcp_vps_error.py` | 6 | REQ-FIX-05 |
| `tests/unit/test_backtest_router_logging.py` | 3 | REQ-FIX-06 |
| **합계** | **25** | — |

## 케이스 상세

### REQ-FIX-01 (alembic 안전화)
- (a) symbols 컬럼 존재 → 정상 저장
- (b) symbols 컬럼 부재 (mock OperationalError) → graceful 재시도 + symbols 누락 INSERT
- (c) 다른 SQL 에러 (NULL 위반 등) → 그대로 raise (graceful 미적용)
- (d) `run_local_backtest` save 단계 SQL 에러 → ServiceError 변환 (raw 500 방지)

### REQ-FIX-02 (data_loader 캐시)
- (a) 정상 → 캐시 적중 (외부 호출 1회)
- (b) None → 캐시 미저장 → 두번째 호출 재시도 발생
- (c) 1차 None → 즉시 재시도 → 2차 성공 → 정상 데이터 반환
- (d) TTL 10분 경과 → 캐시 무효화 → 재조회

### REQ-FIX-03 (engine datetime)
- (a) tz-aware (Asia/Seoul) + 시간 포함 → entry/exit 신호 실행 (trades > 0)
- (b) naive + 시간 포함 → 매칭 성공
- (c) `_idx_for` 매칭 실패 시 silent skip (logger.debug)

### REQ-FIX-04 (`_to_jsonable`)
- (a) numpy float64/int64 → Python native + json.dumps 통과
- (b) pd.Timestamp → ISO 문자열
- (c) 중첩 dict/list 재귀
- (d) NaN/Inf → None
- (e) Python native passthrough

### REQ-FIX-05 (MCP 'vps' 친화 메시지)
- (a) 'vps' 패턴 → 친화 메시지 변환
- (b) 'data preparation failed' → 친화 메시지
- (b-2) '데이터 준비 실패' (한글) → 친화 메시지
- (c) 매칭 안되는 패턴 → 기존 메시지 유지
- (d) success=true → 변경 없음
- (e) 친화 변환 시 원본 error_msg 는 logger.warning 보존

### REQ-FIX-06 (라우터 로깅 + error_id + telemetry)
- (a) run_local 정상 → telemetry `backtest.local.success` 증가
- (b) save SQL 에러 → telemetry `backtest.local.fail.{cause}` 증가
- (c) ServiceError 응답 본문에 `error_id` 8자리 hex 포함

## RED 확인 (구현 전)

```
test_backtest_local_alembic_safe.py: 1 fail / 3 error (PostgreSQL 의존)
test_local_backtest_data_loader_cache.py: 3 fail / 1 pass
test_local_backtest_engine_datetime.py: 2 fail / 1 pass
test_local_backtest_jsonable.py: collection error (`_to_jsonable` 미존재)
test_backtest_mcp_vps_error.py: 4 fail / 2 pass
test_backtest_router_logging.py: 2 fail / 1 error
```

이후 GREEN 단계로 구현 완료.
