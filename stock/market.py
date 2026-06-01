"""국내 주식 시세 · 시가총액 · 52주 고저 조회 — yfinance 기반.

pykrx KRX 스크래핑이 2026-02-27 이후 KRX 서버 변경(로그인 필수화)으로
동작 불가해짐. yfinance (.KS KOSPI / .KQ KOSDAQ suffix)로 대체.

제약사항:
  - PER / PBR: yfinance 국내 주식 미지원 → None 반환
  - 밸류에이션 히스토리: 미지원 → 빈 배열 반환
  - 섹터명: 영문 반환
"""

import logging
import threading
import time as _time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from .cache import delete_prefix, get_cached, set_cached

logger = logging.getLogger(__name__)


# ── 장중/장외 판별 ──────────────────────────────────────────────────────────────

_KST = timezone(timedelta(hours=9))


def _is_kr_trading_hours() -> bool:
    """KST 기준 월-금 09:00~15:30 여부."""
    now = datetime.now(_KST)
    if now.weekday() >= 5:  # 토, 일
        return False
    t = now.time()
    from datetime import time as dt_time
    return dt_time(9, 0) <= t <= dt_time(15, 30)


def _is_us_trading_hours() -> bool:
    """미국 동부 기준 월-금 09:30~16:00 여부 (DST 자동 반영)."""
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
        now = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        # fallback: UTC-5 고정
        now = datetime.now(timezone(timedelta(hours=-5)))
    if now.weekday() >= 5:
        return False
    t = now.time()
    from datetime import time as dt_time
    return dt_time(9, 30) <= t <= dt_time(16, 0)


# ── yfinance ticker 헬퍼 ──────────────────────────────────────────────────────

def _kr_yf_ticker_str(code: str) -> Optional[str]:
    """국내 종목코드 → yfinance ticker 문자열 ('XXXXXX.KS' 또는 'XXXXXX.KQ').

    양쪽 suffix 모두 조회한 후 market_cap + shares가 있는 것을 우선 선택.
    (일부 코드가 .KS/.KQ 양쪽에 존재할 수 있으므로 데이터 완전성으로 판별)
    결과 7일 캐시.
    """
    cache_key = f"market:kr_yf_ticker:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached or None  # 빈 문자열 '' → None

    from .yf_client import _ticker

    best: Optional[str] = None
    # 최소 score ≥ 1 요구 (mktcap 또는 shares 중 하나 이상 필수).
    # score=0(price만 있고 mktcap/shares 없음)이면 잘못된 suffix일 가능성 높음.
    # 예: 267260(HD현대일렉트릭)은 .KS(KOSPI)가 정상이나, .KQ 조회 시
    #     price만 반환되고 mktcap=None → 잘못된 데이터가 7일 캐시되는 버그 방지.
    best_score = 0

    for suffix in [".KS", ".KQ"]:
        try:
            fi = _ticker(f"{code}{suffix}").fast_info
            price = fi.last_price
            if not price or price <= 0:
                continue
            score = 0
            if fi.market_cap and fi.market_cap > 0:
                score += 1
            if fi.shares and fi.shares > 0:
                score += 1
            if score > best_score:
                best = f"{code}{suffix}"
                best_score = score
            # score=2이면 완전한 데이터 → 추가 suffix 시도 불필요
            if best_score >= 2:
                break
        except Exception:
            pass

    if best:
        set_cached(cache_key, best, ttl_hours=24 * 7)
    else:
        set_cached(cache_key, "", ttl_hours=1)
    return best


def _market_type(ticker_str: str) -> str:
    """ticker suffix → KOSPI / KOSDAQ 구분."""
    return "KOSPI" if ticker_str.endswith(".KS") else "KOSDAQ"


# ── 공개 API ──────────────────────────────────────────────────────────────────

def fetch_price(code: str, refresh: bool = False) -> Optional[dict]:
    """현재가, 전일대비(%), 시가총액, 상장주식수 조회.

    현재가 캐시 금지 — 호출 시마다 외부 API 호출.
    refresh=True는 보조 캐시(ticker resolver 등) 무효화 용도.

    반환: dict 또는 None (종목 없음)
    """
    if refresh:
        delete_prefix(f"market:kr_yf_ticker:{code}")

    from .yf_client import _ticker

    ticker_str = _kr_yf_ticker_str(code)
    if not ticker_str:
        return None

    try:
        fi = _ticker(ticker_str).fast_info

        close = fi.last_price
        prev_close = fi.previous_close

        if not close or close <= 0:
            return None

        change = round(close - prev_close) if prev_close else 0
        change_pct = (
            round((close - prev_close) / prev_close * 100, 2) if prev_close else 0.0
        )

        mktcap = fi.market_cap
        shares = fi.shares

        result = {
            "code": code,
            "close": int(close),
            "change": int(change),
            "change_pct": change_pct,
            "mktcap": int(mktcap) if mktcap else None,
            "shares": int(shares) if shares else None,
            "trading_date": date.today().strftime("%Y%m%d"),
        }
        # 영속 캐시 write-through (조회 시 stale 판정으로 우회됨, 디버깅용 잔존)
        try:
            from .stock_info_store import upsert_price
            upsert_price(code, "KR", result)
        except Exception:
            pass
        return result

    except Exception as e:
        raise RuntimeError(f"시세 조회 실패 ({code}): {e}") from e


def fetch_detail(code: str, refresh: bool = False) -> Optional[dict]:
    """info 커맨드용 상세정보: 시장구분, 업종, 52주 고저, PER, PBR 추가.

    현재가는 캐시하지 않는다 — 항상 fetch_price()로 신선한 값 사용.
    메타(market_type/sector/high_52/low_52/per/pbr)만 6시간 캐시.
    """
    meta_cache_key = f"market:detail_meta:{code}"
    if refresh:
        delete_prefix(f"market:detail_meta:{code}")
        delete_prefix(f"market:kr_yf_ticker:{code}")

    # 가격은 매번 새로 (캐시 우회)
    price = fetch_price(code, refresh=refresh)
    if price is None:
        return None

    # 메타는 6시간 캐시 — 가격과 분리
    if not refresh:
        cached_meta = get_cached(meta_cache_key)
        if cached_meta is not None:
            return {**cached_meta, **price}

    from .yf_client import _ticker

    ticker_str = _kr_yf_ticker_str(code)
    if not ticker_str:
        return None

    try:
        t = _ticker(ticker_str)
        fi = t.fast_info
        info = t.info

        market_type = _market_type(ticker_str)
        # REQ-BACK-004: KR 종목 sector 한글 정규화 (코드 직접 매핑 → industry → sector 순)
        from stock.sector_normalize import normalize_sector
        sector = normalize_sector(
            info.get("sector"), "KR", code=code, industry=info.get("industry"),
        )
        high_52 = fi.year_high
        low_52 = fi.year_low
        per_raw = info.get("trailingPE")
        pbr_raw = info.get("priceToBook")

        meta = {
            "market_type": market_type,
            "sector": sector,
            "high_52": int(high_52) if high_52 else None,
            "low_52": int(low_52) if low_52 else None,
            "per": round(per_raw, 2) if per_raw else None,
            "pbr": round(pbr_raw, 2) if pbr_raw else None,
        }
        set_cached(meta_cache_key, meta, ttl_hours=6)
        return {**meta, **price}

    except Exception as e:
        raise RuntimeError(f"상세정보 조회 실패 ({code}): {e}") from e


def _fetch_valuation_history_yf_kr(code: str, years: int) -> list[dict]:
    """KRX 인증 없을 때 yfinance로 국내 종목 PER/PBR 히스토리 추정.

    fetch_valuation_history_yf()와 동일한 로직. .KS/.KQ ticker 자동 선택.
    결과를 market:val_hist 캐시에도 저장하여 일관된 응답 보장.
    """
    ticker_str = _kr_yf_ticker_str(code)
    if not ticker_str:
        return []
    try:
        from stock.yf_client import fetch_valuation_history_yf
        result = fetch_valuation_history_yf(ticker_str, min(years, 5))
        if result:
            cache_key = f"market:val_hist:{code}:{years}"
            set_cached(cache_key, result, ttl_hours=24)
        return result
    except Exception:
        return []


def fetch_valuation_history(code: str, years: int = 10) -> list[dict]:
    """월말 기준 PER/PBR 히스토리 반환.

    pykrx get_market_fundamental 사용. KRX 인증(KRX_ID/KRX_PASSWORD) 필요.
    미인증 또는 조회 실패 시 yfinance(분기 EPS/BPS + 일별 주가)로 fallback.
    """
    cache_key = f"market:val_hist:{code}:{years}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    # KRX 인증 시도
    try:
        from screener.krx_auth import ensure_krx_session
        if not ensure_krx_session():
            return _fetch_valuation_history_yf_kr(code, years)
    except Exception:
        return _fetch_valuation_history_yf_kr(code, years)

    from pykrx import stock as krx
    import pandas as pd

    end = date.today()
    start = date(end.year - years, end.month, end.day)

    try:
        df = krx.get_market_fundamental(
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d"),
            code,
        )
    except Exception:
        return _fetch_valuation_history_yf_kr(code, years)

    if df is None or df.empty:
        return _fetch_valuation_history_yf_kr(code, years)

    # 시가총액 계산용: 종가 + 발행주식수
    try:
        ohlcv = krx.get_market_ohlcv_by_date(
            start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), code
        )
    except Exception:
        ohlcv = pd.DataFrame()

    shares_current = None
    shares_series = None
    try:
        ticker_str = _kr_yf_ticker_str(code)
        if ticker_str:
            import yfinance as yf
            t_yf = yf.Ticker(ticker_str)
            shares_current = int(t_yf.fast_info.shares or 0) or None
            qbs = t_yf.quarterly_balance_sheet
            if qbs is not None and not qbs.empty:
                for name in ("Ordinary Shares Number", "Share Issued"):
                    if name in qbs.index:
                        shares_series = qbs.loc[name].dropna().sort_index()
                        break
    except Exception:
        pass

    # 월말 기준 리샘플 (pandas 2.2+: "ME", 이전: "M")
    try:
        df = df.resample("ME").last()
    except Exception:
        df = df.resample("M").last()

    # 종가 월말 리샘플
    close_monthly = {}
    if not ohlcv.empty and "종가" in ohlcv.columns:
        try:
            cm = ohlcv["종가"].resample("ME").last().dropna()
        except Exception:
            cm = ohlcv["종가"].resample("M").last().dropna()
        close_monthly = {ts.strftime("%Y-%m"): float(v) for ts, v in cm.items()}

    result = []
    for dt, row in df.iterrows():
        per_val = row.get("PER", 0)
        pbr_val = row.get("PBR", 0)
        per = round(float(per_val), 2) if per_val and float(per_val) not in (0.0,) else None
        pbr = round(float(pbr_val), 2) if pbr_val and float(pbr_val) not in (0.0,) else None
        if per is None and pbr is None:
            continue
        date_label = dt.strftime("%Y-%m")
        close = close_monthly.get(date_label)
        # 해당 월 기준 발행주식수 (분기별 시계열에서 최근값)
        shares = shares_current
        if shares_series is not None and len(shares_series) > 0:
            dt_naive = dt.tz_localize(None) if hasattr(dt, 'tz_localize') and dt.tzinfo else dt
            past_s = shares_series[shares_series.index <= dt_naive]
            if len(past_s) >= 1:
                shares = int(past_s.iloc[-1])
        mktcap = round(close * shares) if close and shares else None
        result.append({
            "date": date_label,
            "per": per,
            "pbr": pbr,
            "mktcap": mktcap,
            "shares": int(shares) if shares else None,
        })

    set_cached(cache_key, result, ttl_hours=24)
    return result


def fetch_market_metrics(code: str) -> dict:
    """잔고 페이지용 시가총액·PER·PBR·ROE·배당수익률 단일 종목 조회 (52주 고저 없음).

    반환: {mktcap(원), per, pbr, roe(%, None 가능), market_type, dividend_yield(%)}
    """
    cache_key = f"market:metrics:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    from .yf_client import _ticker

    ticker_str = _kr_yf_ticker_str(code)
    result: dict = {
        "market_type": None,
        "mktcap": None,
        "shares": None,
        "per": None,
        "pbr": None,
        "roe": None,
        "dividend_yield": None,
        "dividend_per_share": None,
        "sector": None,
    }

    if not ticker_str:
        set_cached(cache_key, result, ttl_hours=1)
        return result

    try:
        t = _ticker(ticker_str)
        fi = t.fast_info
        info = t.info

        result["market_type"] = _market_type(ticker_str)
        # REQ-BACK-004: KR 종목 sector 한글 정규화 (코드 직접 매핑 → industry → sector 순)
        from stock.sector_normalize import normalize_sector
        result["sector"] = normalize_sector(
            info.get("sector"), "KR", code=code, industry=info.get("industry"),
        )
        result["mktcap"] = int(fi.market_cap) if fi.market_cap else None
        result["shares"] = int(fi.shares) if fi.shares else None
        result["high_52"] = int(fi.year_high) if fi.year_high else None
        result["low_52"] = int(fi.year_low) if fi.year_low else None

        per_raw = info.get("trailingPE")
        pbr_raw = info.get("priceToBook")
        roe_raw = info.get("returnOnEquity")
        # dividendYield: 이미 % 형태 (0.4, 1.3) → 우선 사용
        # trailingAnnualDividendYield: 소수점 형태 → ×100 변환 (ADR 오계산 가능)
        # dividendRate(연간 주당배당금) ÷ 현재가 → 마지막 fallback
        div_yield_pct  = info.get("dividendYield")
        trailing_yield = info.get("trailingAnnualDividendYield")
        div_rate       = info.get("dividendRate")
        price_now      = fi.last_price
        if div_yield_pct is not None:
            div_yield = round(float(div_yield_pct), 2)
        elif trailing_yield is not None:
            div_yield = round(trailing_yield * 100, 2)
        elif div_rate and price_now and price_now > 0:
            computed = float(div_rate) / float(price_now) * 100
            div_yield = round(computed, 2) if 0 < computed < 50 else None
        else:
            div_yield = None

        div_per_share_raw = info.get("dividendRate")  # 연간 주당배당금 (원)
        result["per"] = round(per_raw, 2) if per_raw else None
        # PER fallback: trailingPE 미제공 시(한국 주식) 연간 순이익 기반 직접 계산
        if result["per"] is None and fi.market_cap and fi.market_cap > 0:
            try:
                ann = t.income_stmt
                if ann is not None and not ann.empty:
                    ni_row = None
                    for name in ("Net Income", "Net Income Common Stockholders"):
                        if name in ann.index:
                            ni_row = ann.loc[name].dropna()
                            break
                    if ni_row is not None and len(ni_row) >= 1:
                        latest_ni = float(ni_row.iloc[0])
                        if latest_ni > 0:
                            result["per"] = round(fi.market_cap / latest_ni, 2)
            except Exception:
                pass
        result["pbr"] = round(pbr_raw, 2) if pbr_raw else None
        # PBR fallback: priceToBook이 None이면 자본총계/주식수로 직접 계산
        if result["pbr"] is None and fi.last_price and fi.shares:
            try:
                qbs = t.quarterly_balance_sheet
                if qbs is not None and not qbs.empty:
                    for eq_name in ("Stockholders Equity", "Common Stock Equity"):
                        if eq_name in qbs.index:
                            eq_val = float(qbs.loc[eq_name].dropna().iloc[0])
                            if eq_val > 0:
                                bps = eq_val / fi.shares
                                result["pbr"] = round(fi.last_price / bps, 2)
                            break
            except Exception:
                pass
        result["roe"] = round(roe_raw * 100, 2) if roe_raw else None
        # ROE fallback: returnOnEquity가 None이면 분기 재무로 직접 계산
        if result["roe"] is None:
            try:
                qi = t.quarterly_income_stmt
                qbs = t.quarterly_balance_sheet
                if qi is not None and not qi.empty and qbs is not None and not qbs.empty:
                    ni_row = None
                    for name in ("Net Income", "Net Income Common Stockholders"):
                        if name in qi.index:
                            ni_row = qi.loc[name].dropna()
                            break
                    eq_row = None
                    for name in ("Stockholders Equity", "Common Stock Equity"):
                        if name in qbs.index:
                            eq_row = qbs.loc[name].dropna()
                            break
                    if ni_row is not None and len(ni_row) >= 4 and eq_row is not None and len(eq_row) > 0:
                        ttm_ni = float(ni_row.iloc[:4].sum())
                        equity = float(eq_row.iloc[0])
                        if equity > 0:
                            result["roe"] = round(ttm_ni / equity * 100, 2)
            except Exception:
                pass
        result["dividend_yield"] = div_yield
        result["dividend_per_share"] = round(float(div_per_share_raw)) if div_per_share_raw else None

    except Exception:
        pass

    ttl = 1 if _is_kr_trading_hours() else 12  # 장중 1시간, 장외 12시간
    set_cached(cache_key, result, ttl_hours=ttl)
    # 영속 캐시 write-through
    try:
        from .stock_info_store import upsert_metrics
        upsert_metrics(code, "KR", result)
    except Exception:
        pass
    return result


def fetch_period_returns(code: str) -> dict:
    """당일/3개월/6개월/1년 주가 수익률 반환 (%).

    반환: {change_pct, return_3m, return_6m, return_1y}
    각 값은 None 가능 (데이터 없을 때)
    """
    cache_key = f"market:period_returns:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    from .yf_client import _ticker

    ticker_str = _kr_yf_ticker_str(code)
    empty = {
        "change_pct": None,
        "return_3m": None,
        "return_6m": None,
        "return_1y": None,
    }

    if not ticker_str:
        return empty

    try:
        hist = _ticker(ticker_str).history(period="14mo")
    except Exception:
        return empty

    if hist is None or hist.empty:
        return empty

    # tz-aware 인덱스를 tz-naive로 변환
    try:
        hist.index = hist.index.tz_convert(None)
    except Exception:
        hist.index = hist.index.tz_localize(None)

    df = hist[["Close"]].copy().sort_index()
    current_close = float(df["Close"].iloc[-1])

    if len(df) >= 2:
        prev_val = float(df["Close"].iloc[-2])
        day_pct = round((current_close - prev_val) / prev_val * 100, 2) if prev_val else None
    else:
        day_pct = None

    today = pd.Timestamp.today().normalize()

    def get_past_close(days: int) -> Optional[float]:
        target = today - pd.Timedelta(days=days)
        subset = df[df.index <= target]
        return float(subset["Close"].iloc[-1]) if not subset.empty else None

    def pct(past: Optional[float]) -> Optional[float]:
        if past is None or past == 0:
            return None
        return round((current_close - past) / abs(past) * 100, 1)

    result = {
        "change_pct": day_pct,
        "return_3m": pct(get_past_close(90)),
        "return_6m": pct(get_past_close(180)),
        "return_1y": pct(get_past_close(365)),
    }
    ttl = 0.25 if _is_kr_trading_hours() else 6  # 장중 15분, 장외 6시간
    set_cached(cache_key, result, ttl_hours=ttl)
    # 영속 캐시 write-through
    try:
        from .stock_info_store import upsert_returns
        upsert_returns(code, "KR", result)
    except Exception:
        pass
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 시세판 일괄 폴링 (yfinance 우선 + KIS REST 폴백)
# 2026-05-12: 시세판 WS slot 잠식 문제 해소 → REST 폴링 전환.
# ─────────────────────────────────────────────────────────────────────────────

# In-memory TTL 캐시: key = (market, tuple(sorted(codes))) → (timestamp, result)
_prices_batch_cache: dict[tuple, tuple[float, dict]] = {}
_prices_batch_cache_lock = threading.Lock()


def _prices_batch_ttl_seconds(market: str) -> int:
    """장중 10초 / 장외 60초 (yfinance rate limit 방지)."""
    if market == "US":
        return 10 if _is_us_trading_hours() else 60
    # KR 기본
    return 10 if _is_kr_trading_hours() else 60


def _resolve_kr_yf_tickers(codes: list[str]) -> dict[str, Optional[str]]:
    """KR 코드 → yfinance ticker(.KS/.KQ) 매핑. 캐시 활용."""
    out: dict[str, Optional[str]] = {}
    for code in codes:
        try:
            out[code] = _kr_yf_ticker_str(code)
        except Exception:
            out[code] = None
    return out


def _resolve_us_yf_tickers(codes: list[str]) -> dict[str, Optional[str]]:
    """US 티커 → 그대로 (대문자화). 알파벳/숫자 ticker는 그대로."""
    return {code: code.upper() for code in codes}


def _yf_batch_fast_info(yf_tickers: list[str], market: str):
    """yfinance.Tickers 일괄 호출 → {ticker_str: fast_info} dict.

    실패하거나 빈 결과 시 빈 dict 반환 (예외는 호출자에게 전파).
    """
    if not yf_tickers:
        return {}
    import yfinance as yf
    out: dict = {}
    # 30개 단위 청크 (yfinance 권장)
    CHUNK = 30
    for i in range(0, len(yf_tickers), CHUNK):
        chunk = yf_tickers[i : i + CHUNK]
        try:
            tickers = yf.Tickers(" ".join(chunk))
            for t_str in chunk:
                try:
                    ticker_obj = tickers.tickers.get(t_str) if hasattr(tickers, "tickers") else None
                    if ticker_obj is None:
                        # 일부 yfinance 버전: dict 형태가 아닌 attribute
                        ticker_obj = getattr(tickers, "tickers", {}).get(t_str)
                    if ticker_obj is None:
                        continue
                    fi = ticker_obj.fast_info
                    last = getattr(fi, "last_price", None)
                    if last is None or last <= 0:
                        continue
                    out[t_str] = fi
                except Exception as e:
                    logger.debug("[fetch_prices_batch] yfinance %s fast_info 실패: %s", t_str, e)
        except Exception as e:
            logger.debug("[fetch_prices_batch] yfinance Tickers(%s) 실패: %s", chunk, e)
    return out


def _kis_rest_price_batch(codes: list[str], market: str) -> dict[str, dict]:
    """KIS REST FHKST01010100 종목별 호출 (폴백 경로).

    분당 제한 보호: N≤20 가드 적용.
    실패한 종목은 결과에서 제외 (부분 결과 정책).
    """
    if not codes:
        return {}
    # KIS는 KR만 의미. US는 호출 의미 없으므로 빈 반환.
    if market != "KR":
        return {}
    if len(codes) > 20:
        logger.warning(
            "[fetch_prices_batch] KIS 폴백 생략: N=%d > 20 (분당 제한 보호)",
            len(codes),
        )
        return {}

    try:
        from wrapper import KISWrapper
        from config import (
            KIS_APP_KEY,
            KIS_APP_SECRET,
            KIS_ACNT_NO,
            KIS_ACNT_PRDT_CD_STK,
            KIS_BASE_URL,
        )
    except Exception as e:
        logger.debug("[fetch_prices_batch] KIS import 실패: %s", e)
        return {}

    if not (KIS_APP_KEY and KIS_APP_SECRET):
        return {}

    out: dict[str, dict] = {}
    try:
        kw = KISWrapper(
            api_key=KIS_APP_KEY,
            api_secret=KIS_APP_SECRET,
            acnt_no=KIS_ACNT_NO or "",
            acnt_prdt_cd=KIS_ACNT_PRDT_CD_STK or "",
            base_url=KIS_BASE_URL,
            exchange="서울",
        )
    except Exception as e:
        logger.debug("[fetch_prices_batch] KISWrapper 초기화 실패: %s", e)
        return {}

    for code in codes:
        try:
            resp = kw.fetch_domestic_price("J", code)
            if not resp or resp.get("rt_cd") != "0":
                continue
            o = resp.get("output", {}) or {}
            price = float(o.get("stck_prpr") or 0)
            if price <= 0:
                continue
            prev_close = float(o.get("stck_sdpr") or 0) or None
            change = float(o.get("prdy_vrss") or 0)
            change_pct = float(o.get("prdy_ctrt") or 0)
            volume = int(float(o.get("acml_vol") or 0))
            out[code] = {
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "prev_close": prev_close,
                "volume": volume,
            }
        except Exception as e:
            logger.debug("[fetch_prices_batch] KIS REST %s 실패: %s", code, e)
    return out


def _build_price_record(fi) -> Optional[dict]:
    """yfinance fast_info → 표준 응답 record."""
    try:
        price = getattr(fi, "last_price", None)
        if price is None or price <= 0:
            return None
        prev_close = getattr(fi, "previous_close", None)
        volume = getattr(fi, "last_volume", None)
        change = None
        change_pct = None
        if prev_close and prev_close > 0:
            change = float(price) - float(prev_close)
            change_pct = round((float(price) - float(prev_close)) / float(prev_close) * 100, 2)
        return {
            "price": float(price),
            "change": float(change) if change is not None else 0.0,
            "change_pct": float(change_pct) if change_pct is not None else 0.0,
            "prev_close": float(prev_close) if prev_close else None,
            "volume": int(volume) if volume else None,
        }
    except Exception:
        return None


def fetch_prices_batch(codes: list[str], market: str = "KR") -> dict[str, dict]:
    """시세판용 다중 종목 가격 일괄 조회.

    1차: yfinance ``yf.Tickers(...).fast_info`` 일괄
    2차 폴백: yfinance 빈 결과/예외 시 KIS REST FHKST01010100 종목별 호출 (N≤20 가드)
    부분 실패해도 성공한 종목만 채워서 반환.
    in-memory TTL 캐시 (장중 10s / 장외 60s) — yfinance rate limit 방지.

    Args:
        codes: 종목코드 리스트 (KR: 6자리, US: 티커)
        market: "KR" 또는 "US"

    Returns:
        ``{code: {price, change, change_pct, prev_close, volume}}``
    """
    if not codes:
        return {}

    market = (market or "KR").upper()
    # 중복 제거 (입력 순서 보존)
    seen = set()
    unique_codes = []
    for c in codes:
        if c and c not in seen:
            seen.add(c)
            unique_codes.append(c)

    # 현재가 캐시 금지 도메인 원칙 — in-memory TTL 캐시 우회, 매 호출 외부 API
    # 1차: yfinance
    if market == "KR":
        ticker_map = _resolve_kr_yf_tickers(unique_codes)
    else:
        ticker_map = _resolve_us_yf_tickers(unique_codes)

    yf_tickers = [t for t in ticker_map.values() if t]
    fi_by_ticker = {}
    try:
        fi_by_ticker = _yf_batch_fast_info(yf_tickers, market) or {}
    except Exception as e:
        logger.debug("[fetch_prices_batch] yfinance 일괄 실패: %s", e)
        fi_by_ticker = {}

    result: dict[str, dict] = {}
    for code, t_str in ticker_map.items():
        if not t_str:
            continue
        fi = fi_by_ticker.get(t_str)
        if fi is None:
            continue
        rec = _build_price_record(fi)
        if rec:
            result[code] = rec

    # 2차 폴백: yfinance가 빈 결과이거나 일부 코드만 채워졌으면 KIS REST 시도
    # 분당 제한 보호: N≤20 가드 (호출 측에서 슬라이스)
    missing = [c for c in unique_codes if c not in result]
    if missing:
        if len(missing) > 20:
            logger.warning(
                "[fetch_prices_batch] KIS 폴백 N=%d > 20 — 상위 20개만 호출 (분당 제한 보호)",
                len(missing),
            )
            missing = missing[:20]
        try:
            kis_result = _kis_rest_price_batch(missing, market) or {}
        except Exception as e:
            logger.debug("[fetch_prices_batch] KIS REST 폴백 실패: %s", e)
            kis_result = {}
        for code, rec in kis_result.items():
            result[code] = rec

    # 현재가 캐시 금지 — 결과 캐시 저장 생략
    return result
