"""종목코드 ↔ 종목명 매핑 (pykrx 기반, 7일 캐싱)."""

import re
from datetime import datetime, timedelta
from typing import Optional

from .cache import delete_prefix, get_cached, set_cached

_CACHE_KEY = "symbol_map:v1"
_TTL_HOURS = 24 * 7  # 7일


def _find_latest_trading_day() -> str:
    """오늘 또는 가장 최근 거래일 날짜 문자열(YYYYMMDD) 반환."""
    from pykrx import stock as krx

    dt = datetime.now()
    for _ in range(10):
        candidate = dt.strftime("%Y%m%d")
        try:
            tickers = krx.get_market_ticker_list(candidate, market="KOSPI")
            if tickers:
                return candidate
        except Exception:
            pass
        dt -= timedelta(days=1)
    return datetime.now().strftime("%Y%m%d")


def _build_map() -> dict[str, dict]:
    """KOSPI + KOSDAQ 전 종목 코드/이름/시장 수집.

    1단계: pykrx로 KRX API 조회 (KRX_ID 인증 세션 시도)
    2단계: pykrx 실패 시 DART corpCode.xml fallback (시장 구분 없이 종목명만)
    """
    # KRX 인증 세션 주입 시도 (실패해도 계속 진행)
    try:
        from screener.krx_auth import ensure_krx_session
        ensure_krx_session()
    except Exception:
        pass

    from pykrx import stock as krx

    trading_date = _find_latest_trading_day()
    result: dict[str, dict] = {}
    for market_name in ("KOSPI", "KOSDAQ"):
        try:
            for code in krx.get_market_ticker_list(trading_date, market=market_name):
                name = krx.get_market_ticker_name(code)
                if name:
                    result[code] = {"name": name, "market": market_name}
        except Exception:
            pass

    # pykrx 결과가 너무 적으면 DART corpCode.xml fallback
    if len(result) < 100:
        try:
            from .dart_fin import _load_corp_name_map
            dart_map = _load_corp_name_map()
            for code, name in dart_map.items():
                if code not in result and re.match(r"^\d{6}$", code):
                    result[code] = {"name": name, "market": "KRX"}
        except Exception:
            pass

    return result


def get_symbol_map(refresh: bool = False) -> dict[str, dict]:
    """종목 맵 반환. refresh=True 이면 캐시 무시하고 재수집."""
    if refresh:
        delete_prefix("symbol_map:")
    else:
        cached = get_cached(_CACHE_KEY)
        if cached:
            return cached
    sym_map = _build_map()
    # 빈 결과는 캐시하지 않음 (다음 호출에서 재시도)
    if sym_map:
        set_cached(_CACHE_KEY, sym_map, ttl_hours=_TTL_HOURS)
    return sym_map


def code_to_name(code: str, refresh: bool = False) -> Optional[str]:
    entry = get_symbol_map(refresh).get(code)
    if entry:
        return entry["name"]
    # 심볼맵 빌드 실패(KRX 서버 이슈 등) 시 pykrx 직접 조회 시도
    try:
        from pykrx import stock as krx
        name = krx.get_market_ticker_name(code)
        if name:
            return name
    except Exception:
        pass
    # pykrx도 실패하면 DART corpCode.xml에서 종목명 조회
    try:
        from .dart_fin import _load_corp_name_map
        name_map = _load_corp_name_map()
        return name_map.get(code)
    except Exception:
        return None


def code_to_market(code: str, refresh: bool = False) -> Optional[str]:
    entry = get_symbol_map(refresh).get(code)
    return entry["market"] if entry else None


def name_to_results(query: str, refresh: bool = False) -> list[tuple[str, str, str]]:
    """
    이름(부분 일치)으로 검색.
    반환: [(code, name, market), ...] 정확한 일치 우선.
    """
    sym_map = get_symbol_map(refresh)
    query_lower = query.lower()
    exact, partial = [], []
    for code, info in sym_map.items():
        name, market = info["name"], info["market"]
        if name == query:
            exact.append((code, name, market))
        elif query_lower in name.lower():
            partial.append((code, name, market))
    return exact + partial


def resolve(code_or_name: str, refresh: bool = False) -> tuple[str, str] | None:
    """
    종목코드(6자리) 또는 종목명 → (code, name).
    존재하지 않거나 여러 개 매칭이면 None 반환.
    """
    if re.match(r"^\d{6}$", code_or_name):
        name = code_to_name(code_or_name, refresh)
        return (code_or_name, name) if name else None

    results = name_to_results(code_or_name, refresh)
    if len(results) == 1:
        code, name, _ = results[0]
        return code, name
    return None  # 0개 or 복수 매칭
