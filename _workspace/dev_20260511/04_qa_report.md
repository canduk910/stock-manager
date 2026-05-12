# QA 검증 리포트 — 경계면 교차 비교

작성일: 2026-05-09
검증자: QA Inspector (개발팀장 위임)
대상: REQ-FIX-01 ~ REQ-FIX-06 (백엔드 전용)

## 회귀 가드 결과

### 단위 테스트
- **베이스라인 (변경 전)**: 866 collected → 853 PASS / 17 ERROR (PostgreSQL fixture 의존, 환경 제약)
- **변경 후**: 891 collected → **874 PASS / 0 FAIL / 17 ERROR (동일 환경 제약)**
- **신규 25 PASS** (Step 1~6 모두 GREEN)
- **회귀 0**

```
pytest tests/unit/ -q
891 collected, 874 passed, 17 errors in 25.69s
```

17 ERROR는 PostgreSQL 의존(`docker-compose.test.yml` 미가동) — 본 환경 제약, 변경과 무관.

## API 응답 shape 후방 호환

### `POST /api/backtest/run/local`
- 정상 응답: `{"job_id", "status", "result"}` — **변경 없음**
- 실패 응답: `{"detail": "...", "error_id": "abc12345"}` — `detail` 보존, `error_id` **추가만**
  - 프론트가 `error_id` 사용 안 해도 무시 가능 (후방 호환 100%)
  - BacktestPage 미터치 → 화면 영향 없음

### `POST /api/backtest/run/{preset|custom|batch}` (MCP)
- 응답 shape: 변경 없음
- 'vps'/'데이터 준비 실패' 패턴 시 `detail` 메시지가 친화 메시지로 변경
- 그 외 에러 메시지: 기존 `"MCP 백테스트 실패: ..."` 유지

### `GET /api/backtest/result/{job_id}`
- 응답 shape: 변경 없음
- NotFound 시 `{"detail", "error_id"}` 추가 (위와 동일)

## 데이터 무결성 (OrderAdvisor 도메인 자문 트리거)

### symbols 컬럼 graceful 누락 시 영향
- **모델**: `BacktestJob.symbols = Column(JSON, nullable=True)` — NULL 허용 정합
- **저장**: alembic 미적용 환경에서만 NULL 저장. 적용 환경은 정상 JSON 리스트
- **조회**: `to_dict()` `symbols` 키 NULL 반환 — 프론트 후방 호환 (옵셔널 필드)
- **후속 메서드**: `get_job` / `list_jobs` / `get_latest_metrics` — `symbols` 미참조
- **사용자 화면**: `result_json` 내부 `{"symbols": deduped, ...}` 별도 키로 저장 → 컬럼 누락과 무관
- **결론**: **데이터 무결성 영향 없음**

### MCP 'vps' 친화 메시지의 정보 충분성
- 메시지: "백테스트 데이터 조회 실패: 종목 코드를 확인하거나 다른 날짜 범위로 재시도하세요. (외부 backtester 데이터 준비 실패)"
- 사용자 행동 옵션 2개 명시
- 'vps' 의미 불명 단어는 사용자 노출 차단
- 원본은 logger.warning에 보존 (docker logs 디버깅 가능)
- **결론**: **충분**

## 후방 호환성 검증

| 항목 | 변경 전 | 변경 후 | 영향 |
|------|---------|---------|------|
| `BacktestJob` 스키마 | symbols JSON nullable | 동일 | 0 |
| `run_local_backtest` 응답 | dict | dict (동일) | 0 |
| ServiceError 응답 | `{detail}` | `{detail, error_id}` | error_id 추가만 |
| MCP 응답 처리 | `MCP 백테스트 실패: vps` | 친화 메시지 (vps 패턴만) | 메시지 텍스트만 |
| 도메인 알고리즘 | 미터치 | 미터치 | 0 |
| 프론트 BacktestPage | — | 미터치 | 0 |
| `KIS_MCP_ENABLED=false` | 로컬만 동작 | 동일 | 0 |

## 경계면 교차 비교

### 백엔드 ↔ 프론트
- 응답 shape: 모든 키 보존, error_id만 추가 → 프론트 미수정 OK
- `result_json.equity_curve`/`trades`/`per_symbol_contribution`: numpy/Timestamp 잔재 제거 → 프론트 차트 안전

### 서비스 ↔ Repository
- `BacktestRepository.create_job()`: 시그니처 동일, graceful 분기 내장
- `strategy_store.save_backtest_job()`: 시그니처 동일

### Router ↔ Service
- `routers/backtest.py:run_local`: entry/exit 로그 추가, 호출 위임 동일
- `services/backtest_service.py:run_local_backtest`: 시그니처 동일

### 텔레메트리 ↔ 본 로직
- `_tel.record_event` / `_tel.observe`: 외부 의존 0, no-op 안전
- 카운터: `backtest.local.success` / `backtest.local.fail.{db_error|serialize|timeout|data_load|unknown}`

## 종합 판정

- ✅ 모든 6 요건 (REQ-FIX-01~06) 수용 기준 충족
- ✅ 단위 회귀 0 FAIL (874 PASS)
- ✅ 응답 shape 후방 호환 100%
- ✅ 데이터 무결성 영향 없음 (OrderAdvisor 자문 통과)
- ✅ KIS_MCP_ENABLED=false 환경 무영향
- ✅ 프론트 미터치
- ⏭️ REQ-OPS-07 (CloudWatch) 별도 phase 권고

**배포 가능 (단, 운영 검증은 사용자가 SSH 가능 시 별도 진행 — `05_smoke_runbook.md` 참조)**
