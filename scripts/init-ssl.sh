#!/bin/bash
# init-ssl.sh — EC2에서 1회 실행하여 Let's Encrypt SSL 인증서를 발급한다.
# 사용법: ./init-ssl.sh <도메인> [이메일]
# 예시:   ./init-ssl.sh dkstock.cloud admin@dkstock.cloud
set -euo pipefail

DOMAIN=${1:?"사용법: ./init-ssl.sh <도메인> [이메일]"}
EMAIL=${2:-"admin@$DOMAIN"}

cd /opt/stock-manager

echo "[1/4] 디렉토리 생성..."
mkdir -p certbot/conf certbot/www nginx

echo "[2/4] 기존 컨테이너 중지 (포트 80 확보)..."
docker compose -f docker-compose.prod.yml down 2>/dev/null || true

echo "[3/4] certbot standalone 모드로 인증서 발급..."
docker run --rm -p 80:80 \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --standalone \
  --email "$EMAIL" --agree-tos --no-eff-email \
  -d "$DOMAIN" -d "www.$DOMAIN"

echo "[4/4] 전체 스택 시작 (app + nginx + certbot)..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "=== SSL 인증서 발급 완료 ==="
echo "https://$DOMAIN 에서 확인하세요."
echo ""
echo "인증서 갱신 테스트:"
echo "  docker exec stock-certbot certbot renew --dry-run"
