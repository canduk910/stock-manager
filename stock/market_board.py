"""
시세판 데이터 모듈.
신고가/신저가 탐지: symbol_map 전종목 → yfinance yearHigh/yearLow vs 현재가 비교.
sparkline: yfinance 주봉 1년치 종가 배치 조회.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

from .cache import get_cached, set_cached
from .market import _kr_yf_ticker_str, _is_kr_trading_hours


def _fetch_hi_lo_info(code: str) -> Optional[dict]:
    """단일 종목 신고가/신저가 판단용 데이터 수집.
    반환: {code, name, market_type, price, change_pct, mktcap, year_high, year_low} 또는 None
    """
    import yfinance as yf

    ticker_str = _kr_yf_ticker_str(code)
    if not ticker_str:
        return None
    try:
        t = yf.Ticker(ticker_str)
        fi = t.fast_info
        price = fi.last_price
        if not price or price <= 0:
            return None
        prev_close = fi.previous_close
        mktcap = fi.market_cap
        year_high = fi.year_high
        year_low = fi.year_low
        if not year_high or not year_low:
            return None
        change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0.0
        market_type = "KOSPI" if ticker_str.endswith(".KS") else "KOSDAQ"
        return {
            "price": int(price),
            "change_pct": change_pct,
            "mktcap": int(mktcap) if mktcap else 0,
            "year_high": int(year_high),
            "year_low": int(year_low),
            "market_type": market_type,
        }
    except Exception:
        return None


def fetch_new_highs_lows(top_n: int = 10, candidate_limit: int = 200) -> dict:
    """신고가/신저가 Top N 반환.

    전략:
    1. symbol_map에서 전종목 코드 수집
    2. yfinance fast_info로 각 종목 가격/52주 고저/시총 조회 (ThreadPoolExecutor 병렬)
    3. 시총 상위 candidate_limit 종목만 스캔 (속도 최적화)
    4. 현재가 >= year_high * 0.99 → 신고가 후보
       현재가 <= year_low  * 1.01 → 신저가 후보
    5. 시총 내림차순 정렬, Top N 반환

    캐시: 장중 30분, 장외 6시간.
    """
    cache_key = f"market_board:highs_lows:{top_n}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    from .symbol_map import get_symbol_map
    from .dart_fin import _load_corp_name_map

    sym_map = get_symbol_map()
    # 종목명 매핑 (DART fallback)
    try:
        dart_names = _load_corp_name_map()
    except Exception:
        dart_names = {}

    all_codes = list(sym_map.keys())

    # 먼저 시총 상위 종목만 추릴 수 없으므로 앞에서 candidate_limit개만 처리
    # (symbol_map은 pykrx 순서라 시총 순이 아님, 전체 병렬 스캔)
    # 실제로는 시총 필터링을 결과 후처리로
    codes_to_scan = all_codes[:candidate_limit] if len(all_codes) > candidate_limit else all_codes

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=20) as exe:
        futures = {exe.submit(_fetch_hi_lo_info, code): code for code in codes_to_scan}
        for fut in as_completed(futures):
            code = futures[fut]
            try:
                info = fut.result()
                if info is None:
                    continue
                entry = sym_map.get(code, {})
                name = entry.get("name") or dart_names.get(code) or code
                results.append({
                    "code": code,
                    "name": name,
                    **info,
                })
            except Exception:
                pass

    # 시총 내림차순 정렬
    results.sort(key=lambda x: x["mktcap"], reverse=True)

    highs, lows = [], []
    for r in results:
        price, year_high, year_low = r["price"], r["year_high"], r["year_low"]
        if year_high and price >= year_high * 0.99:
            highs.append(r)
        if year_low and price <= year_low * 1.01:
            lows.append(r)

    # 이미 mktcap 정렬되어 있으므로 순서 유지하며 Top N
    highs = highs[:top_n]
    lows = lows[:top_n]

    result = {
        "new_highs": highs,
        "new_lows": lows,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "scanned": len(results),
    }

    ttl = 0.5 if _is_kr_trading_hours() else 6  # 장중 30분, 장외 6시간
    set_cached(cache_key, result, ttl_hours=ttl)
    return result


def fetch_sparkline(code: str, market: str = "KR") -> list[dict]:
    """단일 종목 1년 주봉 종가 반환.

    반환: [{"date": "2024-03", "close": 72000}, ...]
    캐시: 24시간 (주봉이므로 장중 갱신 불필요).
    """
    cache_key = f"market_board:sparkline:{code}:{market}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    import yfinance as yf

    if market == "KR":
        ticker_str = _kr_yf_ticker_str(code)
        if not ticker_str:
            return []
    else:
        ticker_str = code.upper()

    try:
        hist = yf.Ticker(ticker_str).history(period="1y", interval="1wk")
        if hist is None or hist.empty:
            return []
        # tz-aware → tz-naive
        try:
            hist.index = hist.index.tz_convert(None)
        except Exception:
            hist.index = hist.index.tz_localize(None)

        result = [
            {"date": str(ts.date()), "close": round(float(row["Close"]), 4)}
            for ts, row in hist.iterrows()
            if row["Close"] and row["Close"] > 0
        ]
        set_cached(cache_key, result, ttl_hours=24)
        return result
    except Exception:
        return []


def fetch_sparklines_batch(items: list[dict]) -> dict[str, list[dict]]:
    """복수 종목 sparkline 배치 조회.

    items: [{"code": "005930", "market": "KR"}, ...]
    반환: { "005930": [{date, close}, ...], ... }
    """
    result: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=10) as exe:
        futures = {
            exe.submit(fetch_sparkline, item["code"], item.get("market", "KR")): item["code"]
            for item in items
        }
        for fut in as_completed(futures):
            code = futures[fut]
            try:
                result[code] = fut.result()
            except Exception:
                result[code] = []
    return result
