# 운영 스모크 검증 런북

작성일: 2026-05-09
대상: 사용자 (SSH 가능 시)

본 phase는 코드 fix만 적용. 운영 SSH 접근 차단 환경이라 사용자 측에서 직접 실행.

## 1. 배포 후 alembic 검증

```bash
ssh -i scripts/stock-manager-bigmac.pem ubuntu@<EC2 host>

# 컨테이너 내부 alembic 상태
docker exec stock-manager alembic current
# 기대: e1f2a3b4c5d6 (head)

# 만약 head 미달 시 컨테이너 lifespan 에 다음 라인 출력:
docker logs stock-manager 2>&1 | grep -E "alembic 미적용|alembic head 일치"
# 기대: [정보] alembic head 일치: e1f2a3b4c5d6

# 만약 [오류] alembic 미적용 감지: ... 이면 수동 적용:
docker exec stock-manager alembic upgrade head
docker compose -f docker-compose.prod.yml restart app
```

## 2. 다중 종목 로컬 백테스트 스모크

```bash
TOKEN="<JWT>"

curl -X POST https://dkstock.cloud/api/backtest/run/local \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "momentum",
    "symbols": ["005930", "000660"],
    "market": "KR",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'

# 기대: 200 + {"job_id":"...", "status":"completed", "result":{"equity_curve":[...], "trades":[...], ...}}
# 만약 500 이면 응답 본문에 `error_id` 8자리 hex 확인:
#   {"detail": "...", "error_id": "abc12345"}
# → docker logs 에서 동일 error_id 매칭:
docker logs stock-manager 2>&1 | grep "abc12345"
```

## 3. MCP 'vps' 메시지 재현 (선택)

이전 'vps' 에러가 발생했던 종목/날짜 범위로 재현 시도:

```bash
curl -X POST https://dkstock.cloud/api/backtest/run/preset \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "sma_crossover",
    "symbol": "<문제 종목>",
    "market": "KR",
    "start_date": "<문제 날짜>",
    "end_date": "<문제 날짜>"
  }'

# 기대 (변환 후): 502 + {"detail": "백테스트 데이터 조회 실패: 종목 코드를 확인하거나 다른 날짜 범위로 재시도하세요. (외부 backtester 데이터 준비 실패)", "error_id": "..."}

# 원본 메시지는 docker logs 보존:
docker logs stock-manager 2>&1 | grep "MCP backtester data preparation error"
# 기대: ... MCP backtester data preparation error: 백테스트 실패: 데이터 준비 실패: 'vps'
```

## 4. 텔레메트리 5분 dump 확인

```bash
docker logs stock-manager 2>&1 | grep "telemetry counter backtest.local"
# 기대 (5분 후):
#   telemetry counter backtest.local.success=N
#   telemetry counter backtest.local.fail.db_error=M  (있다면)

docker logs stock-manager 2>&1 | grep "telemetry observe backtest.local"
# 기대:
#   telemetry observe backtest.local.duration_ms p50=... p95=... p99=... n=...
```

## 5. ServiceError error_id 동작 확인

존재하지 않는 job_id 조회로 강제 트리거:

```bash
curl -i https://dkstock.cloud/api/backtest/result/non-existent-test \
  -H "Authorization: Bearer ${TOKEN}"

# 기대: HTTP/1.1 404 Not Found
#   {"detail": "백테스트 작업을 찾을 수 없습니다: non-existent-test", "error_id": "abc12345"}

docker logs stock-manager 2>&1 | grep "abc12345"
# 기대: [abc12345] ServiceError GET /api/backtest/result/non-existent-test status=404 ...
```

## 6. 회귀 가드 스모크 (빠른 점검)

| 기능 | curl | 기대 |
|------|------|------|
| MCP 단일 종목 정상 백테스트 | `POST /api/backtest/run/preset` | 200 + 기존 응답 shape |
| 백테스트 이력 조회 | `GET /api/backtest/history` | 200 + 기존 |
| 전략빌더 저장 | `POST /api/backtest/strategies` | 200 + 기존 |
| 헬스체크 | `GET /api/health` | 200 |

## 트러블슈팅

| 증상 | 원인 추정 | 대응 |
|------|----------|------|
| `error_id` 본문에 없음 | nginx에서 응답 캐시 | nginx -s reload |
| 'vps' 원본 메시지 노출 | 패턴 매칭 실패 | docker logs 패턴 매칭 로그 확인 |
| alembic 미적용 알림 출력 | EC2 재시작 직후 마이그레이션 락 | 1분 대기 후 재확인 |
| run/local 여전히 raw 500 | 컨테이너 갱신 안됨 | `docker pull` + `docker-compose up -d --force-recreate app` |
