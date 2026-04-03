"""실시간 시세 서비스 공개 API.

구현체:
  - quote_kis.py: KISQuoteManager (국내/FNO WS + REST fallback + 체결통보)
  - quote_overseas.py: OverseasQuoteManager (Finnhub WS / yfinance 폴링)

FastAPI lifespan에서 start() / stop() 호출.
"""
from services.quote_kis import KISQuoteManager
from services.quote_overseas import OverseasQuoteManager

# ── 싱글턴 ────────────────────────────────────────────────────────────────────

_manager: KISQuoteManager | None = None
_overseas_manager: OverseasQuoteManager | None = None


def get_manager() -> KISQuoteManager:
    global _manager
    if _manager is None:
        _manager = KISQuoteManager()
    return _manager


def get_overseas_manager() -> OverseasQuoteManager:
    global _overseas_manager
    if _overseas_manager is None:
        _overseas_manager = OverseasQuoteManager()
    return _overseas_manager
