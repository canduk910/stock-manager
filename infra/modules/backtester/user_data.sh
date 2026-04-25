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

# ── Lean 데이터 초기화 (Docker 이미지 pull + 마켓 데이터) ────
cd /opt/backtester/open-trading-api/backtester
sudo -u ec2-user bash setup_lean_data.sh || true

echo "[user_data] Backtester bootstrap complete"
