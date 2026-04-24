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

# ── 1GB Swap 설정 (t3.micro 1GB RAM 보완) ───────────────────
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile swap swap defaults 0 0" >> /etc/fstab

# ── 앱 디렉토리 ─────────────────────────────────────────────
mkdir -p /opt/stock-manager
chown ec2-user:ec2-user /opt/stock-manager

echo "[user_data] Bootstrap complete"
