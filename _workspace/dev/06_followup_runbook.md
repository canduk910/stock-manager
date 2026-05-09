# 후속 작업 적용 절차 — CloudWatch Logs + Backtester 'vps' 진단

**대상**: 사용자(EC2/AWS 관리 권한 보유)
**작성일**: 2026-05-09
**선행 작업**: 백테스트 500 버그픽스 phase 완료 (단위 874 PASS, 코드 6 파일 + 테스트 6 파일)

---

## 1. CloudWatch Logs 통합 (REQ-OPS-07)

### 1-A. 변경 요약

| 파일 | 변경 |
|------|------|
| `infra/modules/compute/main.tf` | `aws_cloudwatch_log_group.main` + `aws_iam_role_policy.cloudwatch_logs` 신규. `log_retention_days` 변수(기본 14). outputs 2건. |
| `docker-compose.cloudwatch.yml` | **신규** override 파일 — app/nginx 서비스에 `awslogs` 드라이버. Terraform 적용 후에만 사용. |
| `.github/workflows/deploy.yml` | `CLOUDWATCH_LOGS` env 추가. SCP 대상에 cloudwatch override 포함. 배포 시 분기(`if CLOUDWATCH_LOGS=true → -f override 추가`). |

기본 동작(`CLOUDWATCH_LOGS=false`): docker-compose.prod.yml 단독 → 기존 json-file 로그(EC2 로컬). **운영 영향 0건**.

### 1-B. 활성화 절차 (사용자 액션)

#### Step 1: Terraform 적용
```bash
cd infra
terraform plan
# 검토:
#   + aws_cloudwatch_log_group.main /stock-manager/prod (retention 14일)
#   + aws_iam_role_policy.cloudwatch_logs (logs:CreateLogStream/PutLogEvents/DescribeLogStreams)
#   + outputs: log_group_name, log_group_arn

terraform apply
# yes 확인
```

검증:
```bash
aws logs describe-log-groups \
  --log-group-name-prefix /stock-manager \
  --region ap-northeast-2

aws iam list-role-policies --role-name stock-manager-ec2-role
# stock-manager-cloudwatch-logs 포함 확인
```

#### Step 2: GitHub Actions Variables 설정

`https://github.com/<org>/<repo>/settings/variables/actions` →
- 신규 Variable: `CLOUDWATCH_LOGS` = `true`

(Secret이 아닌 Variable로 등록 — 비밀값 아님, 토글 플래그)

#### Step 3: 배포 트리거
```bash
git push origin main
# 또는 GitHub Actions에서 "Re-run all jobs"
```

배포 로그에서 다음 메시지 확인:
```
[5/6] 컨테이너 시작...
  → CloudWatch Logs 활성: docker-compose.cloudwatch.yml override 적용
```

#### Step 4: CloudWatch에서 로그 확인
```bash
# 로그 스트림 목록
aws logs describe-log-streams \
  --log-group-name /stock-manager/prod \
  --order-by LastEventTime --descending \
  --region ap-northeast-2 --max-items 10

# 최근 로그 tail
aws logs tail /stock-manager/prod --follow --region ap-northeast-2

# 백테스트 500 stack trace 검색
aws logs filter-log-events \
  --log-group-name /stock-manager/prod \
  --filter-pattern '"backtest" "Traceback"' \
  --region ap-northeast-2 --max-items 50
```

### 1-C. 비활성화 (롤백)

GitHub Actions Variables에서 `CLOUDWATCH_LOGS=false`(또는 삭제) → 다음 배포 시 자동 json-file 복귀.

Terraform 리소스를 영구 제거하려면 `terraform destroy -target=module.compute.aws_cloudwatch_log_group.main` 후 IAM policy도 별도 제거.

### 1-D. 비용

- CloudWatch Logs: 수집 $0.50/GB + 저장 $0.03/GB·월 (서울 리전 기준)
- 14일 retention + stock-manager + nginx 평균 50MB/일 → 약 $0.05/월 미만 (무시할 수준)

### 1-E. 알려진 한계

- nginx 컨테이너의 access log가 stdout으로 나오지 않을 수 있음 (nginx:alpine 기본 stderr만). 필요 시 `infra/nginx/app.conf`에서 `access_log /var/log/nginx/access.log;` → `/dev/stdout` 로 변경 권고 (별도 phase).
- backtester EC2(t3.micro)는 별도 모듈 — 본 phase에서 미터치. 동일 패턴으로 `infra/modules/backtester/main.tf`에 적용 가능.

---

## 2. Backtester 'vps' 본질 fix (외부 레포)

### 2-A. 상황

- 외부 레포 `open-trading-api/backtester` (KIS AI Extensions, QuantConnect Lean 기반) 측 데이터 준비 단계에서 `'vps'` 키 누락 → 응답 `{"success": false, "error": "백테스트 실패: 데이터 준비 실패: 'vps'"}`.
- stock-manager 측은 **친화 메시지 변환만 처리 완료**(REQ-FIX-05). 본질 fix는 backtester 레포에서.
- 로컬 stock-manager에 backtester 레포 미clone — backtester EC2(t3.micro)에 `/opt/backtester/open-trading-api/`로 존재.

### 2-B. 진단 절차 (사용자 액션)

backtester EC2에 SSH:
```bash
# backtester EC2 IP/DNS 확인 (Terraform output 또는 AWS Console EC2)
# ssh 키는 stock-manager와 동일하거나 별도 — Terraform infra/modules/backtester 확인

ssh -i scripts/stock-manager-bigmac.pem ec2-user@<backtester EC2>

# 1. 'vps' 키 사용처 grep
cd /opt/backtester/open-trading-api/backtester
grep -rn "'vps'\|\"vps\"\|\\['vps'\\]\|\\[\"vps\"\\]" . | head -30

# 2. MCP 서버 로그 확인 (최근 백테스트 시도 stack trace)
tail -300 /tmp/mcp.log | grep -B 5 -A 30 "vps\|Traceback"

# 3. 데이터 준비 단계 코드 위치 추정
grep -rn "데이터 준비\|prepare_data\|prepare data" . | head -20
```

### 2-C. 가설 (확인 필요)

`'vps'` 후보 의미:
- (a) **`volume_per_share`** — 종목별 평균 거래량 — 데이터 준비 dict 키 누락 시 KeyError
- (b) **`value_per_share`** — 주당 가치 (PER 역수 등) — 동일
- (c) **`vol_per_symbol`** — 시뮬레이션 변동성 매핑 키 — 특정 종목 데이터셋이 비어 빌드 실패
- (d) Lean 엔진 내부 식별자 — QuantConnect 측 변경

진단 후 fix 방법:
- Public 레포(GitHub `koreainvestment/open-trading-api`)면 Issue/PR 제출
- Internal fork면 직접 수정 후 backtester EC2 재배포

### 2-D. 임시 우회 방법

backtester 본질 fix 전까지:
1. **MCP 백테스트 사용 자제** — UI에서 "MCP 프리셋" 탭 비활성화 권고
2. **로컬 백테스트 사용** — stock-manager 자체 엔진(`services/local_backtest/`) 4개 KR 전략은 정상 동작 (이번 phase에서 검증 완료)
3. **친화 메시지로 안내** — 사용자가 'vps' 메시지 보면 종목/날짜 변경 후 재시도 권고 (REQ-FIX-05 적용으로 자동 안내됨)

---

## 3. 본 phase 변경 검증 (배포 전)

```bash
# Terraform 코드 syntax 검증
cd infra
terraform validate
terraform fmt -check -diff

# docker-compose override syntax 검증 (로컬)
docker compose -f docker-compose.prod.yml -f docker-compose.cloudwatch.yml config > /dev/null && echo OK

# deploy.yml syntax 검증 (GitHub Actions가 자동)
# 로컬: actionlint 또는 yamllint
```

본 변경의 회귀 가드:
- `CLOUDWATCH_LOGS` 미설정 시 기존 동작 100% 보존 (json-file 그대로)
- terraform apply 전이면 deploy.yml은 false 분기로 안전 동작
- backtester 레포는 본 phase 미터치 — 운영 영향 0
