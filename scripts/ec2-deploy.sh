#!/bin/bash
# EC2에서 수동 배포 시 사용하는 스크립트 (긴급/디버깅용 — nginx/HTTPS 없는 단순 배포)
# 사용법: ECR_REPO=xxxx.dkr.ecr.ap-northeast-2.amazonaws.com/stock-manager ./ec2-deploy.sh [IMAGE_TAG]
#
# ⚠ 주의: 이 스크립트는 운영용 nginx 리버스 프록시 + HTTPS 를 포함하지 않는다.
#   정식 배포는 GitHub Actions (.github/workflows/deploy.yml) 가 담당.
#   이 스크립트는 GitHub Actions 가 동작하지 않는 비상 상황에서만 사용.
#   docker-compose.prod.yml 과는 별개 인라인 compose 를 생성하므로,
#   운영 nginx 설정과 drift 가 발생하지 않는다 (nginx 자체를 띄우지 않음).
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
