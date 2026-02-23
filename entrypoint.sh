#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8000}

# ── 환경변수 검증 ────────────────────────────────────────────
# KIS 잔고 조회: 선택 사항 (없으면 /api/balance가 503 반환)
if [ -z "${KIS_APP_KEY:-}" ] || [ -z "${KIS_APP_SECRET:-}" ]; then
  echo "[경고] KIS_APP_KEY / KIS_APP_SECRET 미설정 — 잔고 조회(/api/balance) 비활성화" >&2
fi

# 계좌번호: 두 값 중 하나라도 없으면 경고
if [ -z "${KIS_ACNT_NO:-}" ] || [ -z "${KIS_ACNT_PRDT_CD:-}" ]; then
  echo "[경고] KIS_ACNT_NO / KIS_ACNT_PRDT_CD 미설정 — 잔고 조회(/api/balance) 비활성화" >&2
fi

# DART API 키: 없으면 공시 조회 실패
if [ -z "${OPENDART_API_KEY:-}" ]; then
  echo "[경고] OPENDART_API_KEY 미설정 — 공시 조회(/api/earnings/filings) 비활성화" >&2
fi

# ── 프론트엔드 빌드 확인 ─────────────────────────────────────
if [ -d "/app/frontend/dist" ]; then
  echo "[정보] frontend/dist 감지 — FastAPI가 정적 파일을 서빙합니다 (http://0.0.0.0:${PORT})"
else
  echo "[정보] frontend/dist 없음 — API 전용 모드 (UI 비활성화)"
fi

# ── 캐시 디렉토리 쓰기 권한 확인 ────────────────────────────
if ! touch /app/screener_cache.db 2>/dev/null; then
  echo "[경고] /app 쓰기 권한 없음 — screener 캐시 비활성화 (매 요청마다 KRX/DART API 호출)" >&2
fi

# ── uvicorn 실행 ─────────────────────────────────────────────
echo "[시작] uvicorn main:app --host 0.0.0.0 --port ${PORT}"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT" "$@"
