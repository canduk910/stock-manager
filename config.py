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
