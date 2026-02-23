"""종목코드 ↔ 종목명 매핑 (pykrx 기반, 7일 캐싱)."""

import re
from typing import Optional

from .cache import delete_prefix, get_cached, set_cached

_CACHE_KEY = "symbol_map:v1"
_TTL_HOURS = 24 * 7  # 7일


def _build_map() -> dict[str, dict]:
    """pykrx로 KOSPI + KOSDAQ 전 종목 코드/이름/시장 수집."""
    from pykrx import stock as krx

    result: dict[str, dict] = {}
    for market in ("KOSPI", "KOSDAQ"):
        for code in krx.get_market_ticker_list(market=market):
            name = krx.get_market_ticker_name(code)
            if name:
                result[code] = {"name": name, "market": market}
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
    set_cached(_CACHE_KEY, sym_map, ttl_hours=_TTL_HOURS)
    return sym_map


def code_to_name(code: str, refresh: bool = False) -> Optional[str]:
    entry = get_symbol_map(refresh).get(code)
    return entry["name"] if entry else None


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
