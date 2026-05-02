#!/bin/bash
set -euo pipefail

# ── Docker 설치 ─────────────────────────────────────────────
dnf update -y
dnf install -y docker aws-cli jq
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# ── Docker Compose v2 설치 ──────────────────────────────────
DOCKER_CLI_PLUGINS=/usr/local/lib/docker/cli-plugins
mkdir -p "$DOCKER_CLI_PLUGINS"
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
  -o "$DOCKER_CLI_PLUGINS/docker-compose"
chmod +x "$DOCKER_CLI_PLUGINS/docker-compose"

# ── 4GB Swap 설정 (t3.small 1.9GB RAM 보완, 워치리스트 yfinance 병렬 호출 대응) ────────────
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile swap swap defaults 0 0" >> /etc/fstab
# swap 적극 활용 줄여 thrashing 방지 (기본 60 → 10)
echo "vm.swappiness=10" >> /etc/sysctl.conf
sysctl -p

# ── 앱 디렉토리 ─────────────────────────────────────────────
mkdir -p /opt/stock-manager
chown ec2-user:ec2-user /opt/stock-manager

echo "[user_data] Bootstrap complete"
