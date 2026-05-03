"""환경변수 중앙 관리.

모든 모듈은 os.getenv() 직접 호출 대신 이 모듈에서 import.
.env 파일은 main.py에서 dotenv.load_dotenv()로 로드됨.
"""

import os

# ── KIS API ──────────────────────────────────────────────────────────────────
KIS_APP_KEY = os.getenv("KIS_APP_KEY", "")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "")
KIS_ACNT_NO = os.getenv("KIS_ACNT_NO", "")
KIS_ACNT_PRDT_CD_STK = os.getenv("KIS_ACNT_PRDT_CD_STK", "")
KIS_ACNT_PRDT_CD_FNO = os.getenv("KIS_ACNT_PRDT_CD_FNO", "")
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")

# ── OpenDart ─────────────────────────────────────────────────────────────────
OPENDART_API_KEY = os.getenv("OPENDART_API_KEY", "")

# ── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

# ── Finnhub ──────────────────────────────────────────────────────────────────
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# ── Portfolio Advisor ─────────────────────────────────────────────────────────
ADVISOR_CACHE_TTL_HOURS = float(os.getenv("ADVISOR_CACHE_TTL_HOURS", "0.5"))

# ── KRX 인증 (스크리너용, 선택) ──────────────────────────────────────────────
KRX_ID = os.getenv("KRX_ID", "")
KRX_PASSWORD = os.getenv("KRX_PASSWORD", "")

# ── KIS WS 체결통보 ────────────────────────────────────────────────────────
KIS_HTS_ID = os.getenv("KIS_HTS_ID", "")

# ── 사용자별 KIS 자격증명 암호화 (Phase 4 D.1) ─────────────────────────────
# 32-byte urlsafe-base64 마스터 키. 미설정 시 사용자별 KIS 기능 비활성화.
# 발급: python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
KIS_ENCRYPTION_KEY = os.getenv("KIS_ENCRYPTION_KEY", "")
KIS_VALIDATION_TTL_HOURS = float(os.getenv("KIS_VALIDATION_TTL_HOURS", "24"))

# ── Database ──────────────────────────────────────────────────────────────
from pathlib import Path  # noqa: E402
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{Path.home() / 'stock-watchlist' / 'app.db'}",
)

# ── KIS AI Extensions (MCP 서버) ──────────────────────────────────────
KIS_MCP_URL = os.getenv("KIS_MCP_URL", "http://127.0.0.1:3846/mcp")
KIS_MCP_ENABLED = os.getenv("KIS_MCP_ENABLED", "false").lower() == "true"

# ── JWT 인증 ──────────────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-please")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
