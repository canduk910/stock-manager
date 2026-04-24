#!/bin/bash
# EC2에서 수동 배포 시 사용하는 스크립트
# 사용법: ECR_REPO=xxxx.dkr.ecr.ap-northeast-2.amazonaws.com/stock-manager ./ec2-deploy.sh [IMAGE_TAG]
set -euo pipefail

REGION="${AWS_REGION:-ap-northeast-2}"
ECR_REPO="${ECR_REPO:?ECR_REPO 환경변수를 설정하세요}"
IMAGE_TAG="${1:-latest}"

echo "[1/5] ECR 로그인..."
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin "$ECR_REPO"

echo "[2/5] 이미지 pull ($ECR_REPO:$IMAGE_TAG)..."
docker pull "$ECR_REPO:$IMAGE_TAG"

echo "[3/5] SSM에서 환경변수 로드..."
aws ssm get-parameters-by-path \
  --path "/stock-manager/prod/" \
  --with-decryption \
  --region "$REGION" \
  --query "Parameters[*].[Name,Value]" \
  --output text | while IFS=$'\t' read -r name value; do
    echo "$(basename "$name")=$value"
done > /opt/stock-manager/.env

echo "[4/5] 컨테이너 시작..."
cd /opt/stock-manager

# docker-compose.prod.yml 생성
cat > docker-compose.prod.yml << COMPOSE_EOF
services:
  web:
    image: ${ECR_REPO}:${IMAGE_TAG}
    container_name: stock-manager
    restart: unless-stopped
    env_file: [.env]
    ports: ["80:8000"]
    volumes: [watchlist-data:/home/app/stock-watchlist]
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
volumes:
  watchlist-data:
COMPOSE_EOF

docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "[5/5] 이전 이미지 정리..."
docker image prune -f

echo ""
echo "=== 배포 완료 ==="
sleep 5
if curl -sf http://localhost/api/health > /dev/null; then
  echo "Health check: OK"
else
  echo "WARNING: Health check 실패 — docker logs stock-manager 확인"
fi
