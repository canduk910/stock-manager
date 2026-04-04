#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8000}

# ── 환경변수 검증 ────────────────────────────────────────────
# KIS 잔고 조회: 선택 사항 (없으면 /api/balance가 503 반환)
if [ -z "${KIS_APP_KEY:-}" ] || [ -z "${KIS_APP_SECRET:-}" ]; then
  echo "[경고] KIS_APP_KEY / KIS_APP_SECRET 미설정 — 잔고 조회(/api/balance) 비활성화" >&2
fi

# 계좌번호: 두 값 중 하나라도 없으면 경고
if [ -z "${KIS_ACNT_NO:-}" ] || [ -z "${KIS_ACNT_PRDT_CD_STK:-}" ]; then
  echo "[경고] KIS_ACNT_NO / KIS_ACNT_PRDT_CD_STK 미설정 — 잔고 조회(/api/balance) 비활성화" >&2
fi

if [ -z "${KIS_ACNT_PRDT_CD_FNO:-}" ]; then
  echo "[정보] KIS_ACNT_PRDT_CD_FNO 미설정 — 선물옵션 잔고 조회 비활성화" >&2
fi

# DART API 키: 없으면 공시 조회 실패
if [ -z "${OPENDART_API_KEY:-}" ]; then
  echo "[경고] OPENDART_API_KEY 미설정 — 공시 조회(/api/earnings/filings) 비활성화" >&2
fi

# KRX 로그인: 없으면 스크리너 비활성화 (2026-02-27 이후 필수)
if [ -z "${KRX_ID:-}" ] || [ -z "${KRX_PASSWORD:-}" ]; then
  echo "[경고] KRX_ID / KRX_PASSWORD 미설정 — 종목 스크리너(/api/screener/stocks) 비활성화" >&2
  echo "[경고]         KRX 회원가입: https://data.krx.co.kr" >&2
fi

# OpenAI API 키: 없으면 AI자문 리포트 생성 불가
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "[경고] OPENAI_API_KEY 미설정 — AI자문 리포트 생성(/api/advisory/*/analyze) 비활성화" >&2
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

# ── 시작 시 캐시 초기화 ──────────────────────────────────────
# 배포마다 구버전 캐시(필드 누락, NaN 등)가 남지 않도록 전체 초기화
# 주의: stock_info.db는 영속 캐시이므로 초기화하지 않음
python3 - <<'PYEOF'
import sys
sys.path.insert(0, '/app')
try:
    from stock.cache import delete_prefix
    delete_prefix('')   # 빈 prefix → 전체 삭제 (watchlist.db 별개, 영향 없음)
    print('[정보] 캐시 초기화 완료 (cache.db)')
except Exception as e:
    print(f'[경고] 캐시 초기화 실패: {e}', file=sys.stderr)
PYEOF

# ── DB 마이그레이션 (Alembic) ─────────────────────────────────
echo "[정보] DB 마이그레이션 실행 (alembic upgrade head)..."
python3 -m alembic upgrade head 2>&1 || echo "[경고] DB 마이그레이션 실패 (서버 시작 시 재시도)" >&2

# ── uvicorn 실행 ─────────────────────────────────────────────
echo "[시작] uvicorn main:app --host 0.0.0.0 --port ${PORT}"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT" "$@"
