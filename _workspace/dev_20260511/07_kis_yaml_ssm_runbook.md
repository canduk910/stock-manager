# KIS Backtester yaml SSM Parameter Store 영속화 — 운영 절차

**대상**: 사용자(AWS SSM PutParameter 권한 보유)
**작성일**: 2026-05-09
**선행 phase**: 백테스트 500 버그픽스(`vts:` → `vps:` 복구) 완료, 메시지 정확도 보강 완료

---

## 배경

backtester EC2(`i-05c673384e1093d61`)의 `~/KIS/config/kis_devlp.yaml`은 KIS 자격증명(appkey/appsecret/계좌번호) 포함이라 `.gitignore`되어 git에 영속 보관 불가. 결과적으로:

- EC2 재생성/재배포 시 yaml 사라짐 → MCP `KeyError: 'vps'` 재발
- 사용자가 직접 yaml 작성 시 키 이름 오타(`vts:` vs `vps:`) 등 휴먼 에러 위험
- 백업 부재 → 단일 실패점

**해결**: SSM Parameter Store(SecureString, KMS 암호화)에 yaml 영속화. EC2 user_data.sh가 부팅 시 자동 다운로드.

## 변경 사항 (이번 phase)

| 파일 | 변경 |
|------|------|
| `infra/modules/backtester/user_data.sh` | yaml SSM 자동 다운로드 + 필수 키 검증(미노출) + 누락 시 WARNING |
| (기존) `infra/modules/backtester/main.tf` | IAM `aws_iam_role_policy.backtester_ssm_params`이 이미 `/stock-manager/*` SSM GetParameter 허용 — **변경 불필요** |

`terraform apply` 자체는 user_data.sh만 수정해도 EC2 인스턴스 교체 트리거. 즉 적용을 원하지 않으면 user_data.sh 변경 후 terraform apply 미실행 + 기존 EC2 그대로 운영 가능. 영속화는 SSM 등록만으로 효과 발생(다음 EC2 재생성 시 자동 복구).

## Step 1: SSM Parameter 등록 (사용자 1회 수동)

backtester EC2에 이미 동작 중인 yaml을 그대로 SSM에 영속화. SecureString 타입(KMS 자동 암호화).

### 옵션 A: 로컬 → SSM (자격증명을 로컬에서 다루지 않음 — 권장)

backtester EC2에서 yaml 내용을 SSM에 직접 put:

```bash
# AWS Console → Systems Manager → Session Manager → i-05c673384e1093d61 시작
# 또는 SSM Send-Command로 한 번에:

aws ssm send-command \
  --region ap-northeast-2 \
  --instance-ids i-05c673384e1093d61 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "YAML=/home/ec2-user/KIS/config/kis_devlp.yaml",
    "if [ ! -f \"$YAML\" ]; then echo YAML_NOT_FOUND; exit 1; fi",
    "VAL=$(sudo -u ec2-user cat \"$YAML\")",
    "REGION=$(curl -sf http://169.254.169.254/latest/meta-data/placement/region)",
    "aws ssm put-parameter --region \"$REGION\" --name /stock-manager/prod/kis_devlp_yaml --type SecureString --value \"$VAL\" --overwrite",
    "echo SSM_PUT_DONE",
    "aws ssm get-parameter --region \"$REGION\" --name /stock-manager/prod/kis_devlp_yaml --query Parameter.LastModifiedDate --output text"
  ]' \
  --query "Command.CommandId" --output text
```

⚠️ **중요**: 위 명령에서 yaml 본문(`$VAL`)이 SSM `put-parameter` 인자로 전달되지만, send-command 실행 로그(SSM history)에 일부 노출될 수 있음. 더 안전한 방법은 옵션 B.

### 옵션 B: backtester EC2 SSH로 직접 (가장 안전)

```bash
# 사용자 로컬에서:
aws ssm start-session --target i-05c673384e1093d61 --region ap-northeast-2

# (세션 안에서)
sudo -u ec2-user bash
YAML=~/KIS/config/kis_devlp.yaml

# Parameter 등록 (자격증명 본문이 send-command history에 남지 않음)
aws ssm put-parameter \
  --region ap-northeast-2 \
  --name /stock-manager/prod/kis_devlp_yaml \
  --type SecureString \
  --value "$(cat $YAML)" \
  --overwrite

# 검증
aws ssm get-parameter \
  --region ap-northeast-2 \
  --name /stock-manager/prod/kis_devlp_yaml \
  --query 'Parameter.[Name,Type,LastModifiedDate,Version]' \
  --output table
```

### 옵션 C: AWS Console (브라우저, 가장 단순)

1. Systems Manager → Parameter Store → "Create parameter"
2. **Name**: `/stock-manager/prod/kis_devlp_yaml`
3. **Tier**: Standard (yaml 4KB 이하면 무료)
4. **Type**: **SecureString** (KMS `alias/aws/ssm` 기본 키)
5. **Value**: yaml 전체 내용 붙여넣기
6. Save

## Step 2: user_data.sh 변경 적용 (선택)

방법 1: **다음 EC2 재생성 때 자동 적용** (대부분의 경우 권장)
- 코드만 main에 push, terraform apply 안 함
- 차후 backtester EC2 교체/재생성 시 user_data.sh의 SSM 다운로드가 자동 실행됨

방법 2: **즉시 user_data 재실행** (현재 EC2에 적용)
- terraform apply는 EC2 instance 교체를 트리거하므로 위험
- 대신 SSM Send-Command로 user_data.sh 부분만 직접 실행:

```bash
aws ssm send-command \
  --region ap-northeast-2 \
  --instance-ids i-05c673384e1093d61 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "YAML_PARAM=/stock-manager/prod/kis_devlp_yaml",
    "YAML_PATH=/home/ec2-user/KIS/config/kis_devlp.yaml",
    "REGION=$(curl -sf http://169.254.169.254/latest/meta-data/placement/region)",
    "if aws ssm get-parameter --name $YAML_PARAM --with-decryption --region $REGION --query Parameter.Value --output text > $YAML_PATH 2>/dev/null; then chmod 600 $YAML_PATH; chown ec2-user:ec2-user $YAML_PATH; echo SSM_DOWNLOAD_OK; else echo SSM_NOT_REGISTERED; fi",
    "for k in my_agent prod vps ops vops; do grep -q ^${k}: $YAML_PATH && echo OK_${k} || echo MISS_${k}; done"
  ]' \
  --query "Command.CommandId" --output text
```

이미 backtester EC2의 yaml은 정상 상태(`vps:` 키 복구 완료)이므로, Step 1만 완료되면 영속화 목적은 달성됨.

## Step 3: 회전(rotation) — 자격증명 변경 시

KIS 콘솔에서 appkey/appsecret/계좌번호가 바뀌었을 때:

```bash
# 새 yaml 로컬에 저장 후
aws ssm put-parameter \
  --region ap-northeast-2 \
  --name /stock-manager/prod/kis_devlp_yaml \
  --type SecureString \
  --value "$(cat path/to/new_kis_devlp.yaml)" \
  --overwrite

# backtester EC2에 즉시 반영
aws ssm send-command \
  --region ap-northeast-2 \
  --instance-ids i-05c673384e1093d61 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "YAML_PATH=/home/ec2-user/KIS/config/kis_devlp.yaml",
    "REGION=ap-northeast-2",
    "aws ssm get-parameter --name /stock-manager/prod/kis_devlp_yaml --with-decryption --region $REGION --query Parameter.Value --output text > $YAML_PATH",
    "chmod 600 $YAML_PATH; chown ec2-user:ec2-user $YAML_PATH",
    "sudo pkill -f kis_mcp.server || true",
    "sleep 2",
    "cd /opt/backtester/open-trading-api/backtester",
    "sudo -u ec2-user bash -c \"export MCP_HOST=0.0.0.0 MCP_PORT=3846; nohup /home/ec2-user/.local/bin/uv run python -m kis_mcp.server > /tmp/mcp.log 2>&1 &\"",
    "sleep 5",
    "curl -sf http://localhost:3846/health"
  ]' \
  --query "Command.CommandId" --output text
```

## Step 4: 회귀 가드 / 운영 영향

| 시나리오 | 동작 |
|----------|------|
| SSM Parameter 등록 + EC2 재생성 | user_data.sh가 자동 다운로드 → MCP 정상 부팅 |
| SSM Parameter 미등록 + EC2 재생성 | WARNING 출력 + 부팅 계속 → 운영자가 수동 yaml 작성 (기존 동작) |
| Parameter 갱신 + 기존 EC2 | Step 3 명령으로 즉시 반영 가능 |
| Parameter 삭제 (`aws ssm delete-parameter`) | 다음 EC2 재생성 시 yaml 누락 → WARNING + 수동 fallback |

기존 EC2 yaml은 Step 1만으로 영향 없음 — yaml 파일 자체는 그대로, SSM은 백업 역할.

## 비용

- SSM Parameter Store Standard tier: **무료** (10,000 parameters / 4KB 미만)
- KMS `alias/aws/ssm` 기본 키 사용: **추가 비용 없음**
- yaml 파일 크기: 1.1KB (현재) → Standard tier 충분

## Step 5: 검증 체크리스트

- [ ] Step 1 완료: `aws ssm get-parameter --name /stock-manager/prod/kis_devlp_yaml --query Parameter.LastModifiedDate` 출력
- [ ] Parameter Type = SecureString (Console에서 자물쇠 아이콘)
- [ ] (선택) Step 2 방법 2 실행 시 backtester yaml 정상 (필수 키 5개 OK)
- [ ] (선택) MCP health check 200
- [ ] 다음 분기 백테스트 1회 정상 동작

## 다음 단계 (선택, 별도 phase)

- **자동 회전**: KIS 자격증명 만료 알림 → SSM EventBridge 트리거 → 갱신 자동화 (구현 복잡, 우선순위 낮음)
- **모니터링**: CloudWatch Logs(이전 phase에서 설계됨)에서 user_data.sh의 `[user_data] kis_devlp.yaml SSM 다운로드 완료` 또는 WARNING 로그 검색
- **다른 자격증명 영속화**: stock-manager .env 일부도 동일 패턴으로 SSM 통합 (이미 SSM `/stock-manager/prod/*` 사용 중이므로 일부 적용됨)
