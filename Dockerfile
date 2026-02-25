# ============================================================
# Stage 1: 프론트엔드 빌드
# ============================================================
FROM node:22-slim AS frontend-builder

WORKDIR /frontend

# 의존성 레이어 캐싱 (package.json이 바뀌지 않으면 npm ci 생략)
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ============================================================
# Stage 2: Python 런타임
# ============================================================
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 (소스 변경과 독립적으로 캐싱)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스
COPY . /app

# Stage 1에서 빌드한 프론트엔드 dist 복사
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

RUN chmod +x /app/entrypoint.sh

# 비루트 사용자 생성 + /app 소유권 이전 (캐시 DB 쓰기 권한 필요)
RUN groupadd -r app && useradd -r -g app -m app \
    && chown -R app:app /app \
    && mkdir -p /home/app/stock-watchlist \
    && chown -R app:app /home/app
USER app

ENTRYPOINT ["/app/entrypoint.sh"]
