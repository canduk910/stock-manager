#!/bin/bash
set -euo pipefail

# ── Docker 설치 ─────────────────────────────────────────────
dnf update -y
dnf install -y docker git aws-cli jq
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# ── Docker Compose v2 설치 ──────────────────────────────────
DOCKER_CLI_PLUGINS=/usr/local/lib/docker/cli-plugins
mkdir -p "$DOCKER_CLI_PLUGINS"
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
  -o "$DOCKER_CLI_PLUGINS/docker-compose"
chmod +x "$DOCKER_CLI_PLUGINS/docker-compose"

# ── 2GB Swap 설정 (t3.micro 1GB RAM 보완) ───────────────────
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile swap swap defaults 0 0" >> /etc/fstab

# ── Python 3.11 설치 ────────────────────────────────────────
dnf install -y python3.11 python3.11-pip

# ── Node.js 18 설치 ─────────────────────────────────────────
dnf install -y nodejs18 npm

# ── uv 설치 (Python 패키지 관리) ─────────────────────────────
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> /home/ec2-user/.bashrc

# ── 앱 디렉토리 + 레포 clone ────────────────────────────────
mkdir -p /opt/backtester
cd /opt/backtester
git clone https://github.com/koreainvestment/open-trading-api.git
chown -R ec2-user:ec2-user /opt/backtester

# ── KIS 설정 디렉토리 준비 ──────────────────────────────────
sudo -u ec2-user mkdir -p /home/ec2-user/KIS/config

# ── kis_devlp.yaml SSM Parameter Store 자동 복구 (2026-05-09) ──────
# Parameter name: /stock-manager/prod/kis_devlp_yaml (SecureString)
# 사전 등록 필요 — `_workspace/dev/07_kis_yaml_ssm_runbook.md` 참조.
# 미등록 시 WARNING 만 출력하고 부팅은 계속 (운영자 수동 작성 fallback).
YAML_PARAM="/stock-manager/prod/kis_devlp_yaml"
YAML_PATH="/home/ec2-user/KIS/config/kis_devlp.yaml"
REGION="$(curl -sf http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo ap-northeast-2)"

if aws ssm get-parameter \
    --name "$YAML_PARAM" \
    --with-decryption \
    --region "$REGION" \
    --query Parameter.Value \
    --output text > "$YAML_PATH" 2>/dev/null; then
  chmod 600 "$YAML_PATH"
  chown ec2-user:ec2-user "$YAML_PATH"
  echo "[user_data] kis_devlp.yaml SSM 다운로드 완료 ($(wc -c < "$YAML_PATH") bytes)"
  # 필수 키 검증 (자격증명 본문 미노출, 키 라벨만)
  for k in my_agent prod vps ops vops; do
    if grep -q "^${k}:" "$YAML_PATH"; then
      echo "  [OK]    ${k}"
    else
      echo "  [WARN]  ${k} 누락 — SSM Parameter 갱신 필요"
    fi
  done
else
  rm -f "$YAML_PATH"  # 부분 실패 흔적 제거
  echo "[user_data] WARNING: kis_devlp.yaml SSM ($YAML_PARAM) 미등록 또는 접근 실패."
  echo "[user_data]          운영자가 다음 명령으로 등록 후 재배포 또는 수동 작성:"
  echo "[user_data]          aws ssm put-parameter --name $YAML_PARAM --type SecureString --value \"\$(cat path/to/kis_devlp.yaml)\""
fi

# ── Lean 데이터 초기화 (Docker 이미지 pull + 마켓 데이터) ────
cd /opt/backtester/open-trading-api/backtester
sudo -u ec2-user bash setup_lean_data.sh || true

echo "[user_data] Backtester bootstrap complete"
