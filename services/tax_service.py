"""해외주식 양도소득세 계산 서비스.

데이터 수집(KIS API / 로컬 DB / 수동 입력) + 환율 조회 + FIFO 계산.
잔고 기반 적응적 동기화 + 시뮬레이션.
도메인 규칙: docs/TAX_DOMAIN.md 참조.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

import requests

from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK, KIS_BASE_URL
from services.exceptions import ExternalAPIError, NotFoundError
from stock import cache, tax_store
from stock.order_store import list_orders

logger = logging.getLogger(__name__)

# 해외주식 기본 수수료율
_DEFAULT_COMMISSION_RATE = 0.0025  # 0.25%

# 양도세 상수
_BASIC_DEDUCTION = 2_500_000  # 250만원
_TAX_RATE = 0.22  # 22% (양도소득세 20% + 지방소득세 2%)


# ── 환율 조회 ─────────────────────────────────────────────────────────────────

def get_exchange_rate(date: str, currency: str = "USD") -> Optional[float]:
    """체결일 기준 환율 조회. cache.db 캐시 + yfinance fallback.

    Args:
        date: "YYYY-MM-DD" 형식
        currency: 통화코드 (USD, HKD, JPY 등)

    Returns:
        환율 (KRW/외화). 조회 실패 시 None.
    """
    cache_key = f"fx:{currency}:{date}"
    cached = cache.get_cached(cache_key)
    if cached is not None:
        if cached == "" or cached == 0:
            return None  # 이전 조회 실패 기록
        return float(cached)

    # yfinance 연간 일괄 조회
    rate = _fetch_exchange_rate_yf(date, currency)
    if rate:
        # 과거 환율은 불변이므로 장기 캐시 (10년)
        cache.set_cached(cache_key, rate, ttl_hours=87600)
        return rate

    return None


def _fetch_exchange_rate_yf(date: str, currency: str) -> Optional[float]:
    """yfinance로 환율 조회. 연간 일괄 fetch 후 개별 캐시 저장."""
    try:
        import yfinance as yf

        ticker_symbol = f"{currency}KRW=X"
        year = date[:4]

        # 해당 연도 전체 환율을 한 번에 조회
        year_cache_key = f"fx:year_fetched:{currency}:{year}"
        if cache.get_cached(year_cache_key) is None:
            start = f"{year}-01-01"
            end_year = int(year)
            # 미래 연도면 오늘까지만
            today = datetime.now().strftime("%Y-%m-%d")
            end = min(f"{end_year}-12-31", today)

            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(start=start, end=end, auto_adjust=False)

            if hist is not None and not hist.empty:
                for idx, row in hist.iterrows():
                    d = idx.strftime("%Y-%m-%d")
                    close = float(row["Close"])
                    if close > 0:
                        day_key = f"fx:{currency}:{d}"
                        cache.set_cached(day_key, close, ttl_hours=87600)

                cache.set_cached(year_cache_key, True, ttl_hours=87600)
                logger.info("환율 연간 캐시 완료: %s %s (%d일)", currency, year, len(hist))

        # 캐시에서 다시 조회
        cached = cache.get_cached(f"fx:{currency}:{date}")
        if cached is not None:
            return float(cached)

        # 주말/공휴일 → 직전 영업일 환율
        dt = datetime.strptime(date, "%Y-%m-%d")
        for i in range(1, 8):
            prev = (dt - timedelta(days=i)).strftime("%Y-%m-%d")
            prev_cached = cache.get_cached(f"fx:{currency}:{prev}")
            if prev_cached is not None:
                rate = float(prev_cached)
                cache.set_cached(f"fx:{currency}:{date}", rate, ttl_hours=87600)
                return rate

        # 조회 실패 기록 (반복 시도 방지, 1일 TTL)
        cache.set_cached(f"fx:{currency}:{date}", "", ttl_hours=24)
        return None
    except Exception as e:
        logger.warning("yfinance 환율 조회 실패 (%s %s): %s", currency, date, e)
        # 실패 기록 (반복 시도 방지)
        cache.set_cached(f"fx:year_fetched:{currency}:{date[:4]}", True, ttl_hours=24)
        return None


# ── 잔고 기반 역산 ────────────────────────────────────────────────────────────

def _get_current_holdings() -> dict[str, dict]:
    """현재 해외주식 보유 잔고 → {symbol: {quantity, avg_price, currency}}.

    KIS API TTTS3012R로 현재 잔고 조회.
    KIS 키 미설정 시 빈 dict 반환.
    """
    creds = _kis_credentials()
    if not creds:
        return {}

    try:
        from routers._kis_auth import get_access_token, make_headers

        token = get_access_token()

        # 주야간 원장 구분
        tr_id = "TTTS3012R"
        try:
            url_dn = f"{KIS_BASE_URL}/uapi/overseas-stock/v1/trading/dayornight"
            headers_dn = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": creds[0],
                "appsecret": creds[1],
                "tr_id": "JTTT3010R",
            }
            res_dn = requests.get(url_dn, headers=headers_dn, timeout=5)
            if res_dn.status_code == 200:
                psbl = res_dn.json().get("output", {}).get("PSBL_YN", "N")
                if psbl == "Y":
                    tr_id = "JTTT3012R"
        except Exception:
            pass

        # 거래소 순회
        exchanges = [
            ("NASD", "USD"), ("SEHK", "HKD"), ("SHAA", "CNY"),
            ("SZAA", "CNY"), ("TKSE", "JPY"), ("HASE", "VND"), ("VNSE", "VND"),
        ]
        url = f"{KIS_BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
        headers = make_headers(token, creds[0], creds[1], tr_id)
        headers["custtype"] = "P"

        holdings: dict[str, dict] = {}
        for excg_cd, crcy_cd in exchanges:
            params = {
                "CANO": creds[2],
                "ACNT_PRDT_CD": creds[3],
                "OVRS_EXCG_CD": excg_cd,
                "TR_CRCY_CD": crcy_cd,
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": "",
            }
            try:
                res = requests.get(url, headers=headers, params=params, timeout=10)
                if res.status_code != 200:
                    continue
                data = res.json()
                if data.get("rt_cd") != "0":
                    continue
                for item in data.get("output1", []):
                    qty = int(item.get("ovrs_cblc_qty", 0) or 0)
                    if qty > 0:
                        sym = item.get("ovrs_pdno", "")
                        avg_price = float(item.get("pchs_avg_pric", 0) or 0)
                        crcy = item.get("tr_crcy_cd", crcy_cd)
                        holdings[sym] = {
                            "quantity": qty,
                            "avg_price": avg_price,
                            "currency": crcy,
                        }
            except Exception:
                continue

        logger.info("현재 해외주식 잔고: %d종목", len(holdings))
        return holdings
    except Exception as e:
        logger.warning("잔고 조회 실패: %s", e)
        return {}


def _compute_buy_shortfall(year: int) -> dict[str, int]:
    """종목별 매수 부족 수량 계산.

    필요 매수 = 현재 보유 + (year~현재)의 모든 매도 수량
    보유 매수 = DB에 저장된 buy 건의 총 수량
    부족분 = 필요 - 보유 (양수이면 부족)
    """
    holdings = _get_current_holdings()

    # year~현재 매도 수량 합산
    all_sells = tax_store.list_transactions(side="sell")
    sell_qty: dict[str, int] = {}
    for tx in all_sells:
        if tx["trade_date"] >= f"{year}-01-01":
            sell_qty[tx["symbol"]] = sell_qty.get(tx["symbol"], 0) + tx["quantity"]

    # 필요 매수 = 보유 + 매도
    required: dict[str, int] = {}
    for sym in set(list(holdings.keys()) + list(sell_qty.keys())):
        hold_qty = holdings[sym]["quantity"] if sym in holdings else 0
        required[sym] = hold_qty + sell_qty.get(sym, 0)

    # 보유 매수 수량
    all_buys = tax_store.list_transactions(side="buy")
    buy_qty: dict[str, int] = {}
    for tx in all_buys:
        buy_qty[tx["symbol"]] = buy_qty.get(tx["symbol"], 0) + tx["quantity"]

    # 부족분
    shortfall: dict[str, int] = {}
    for sym, need in required.items():
        gap = need - buy_qty.get(sym, 0)
        if gap > 0:
            shortfall[sym] = gap

    return shortfall


# ── KIS API 체결 조회 + 적응적 동기화 ─────────────────────────────────────────

def sync_transactions(year: int) -> dict:
    """잔고 기반 적응적 동기화.

    1. 과세연도~현재 전체 동기화 (기본)
    2. 잔고 역산으로 매수 부족분 계산
    3. 부족 시 과거를 1년씩 소급 (최대 2015년까지)

    Returns:
        {"source": str, "synced": int, "skipped": int, "sync_years": list, "shortfall": dict, "message": str}
    """
    current_year = datetime.now().year
    total_synced, total_skipped = 0, 0
    source = "LOCAL"
    synced_years = []

    # Phase 1: 과세연도 ~ 현재 동기화
    for y in range(year, current_year + 1):
        result = _sync_single_year(y)
        total_synced += result["synced"]
        total_skipped += result["skipped"]
        if result["source"] != "LOCAL":
            source = result["source"]
        synced_years.append(y)

    # Phase 2: 잔고 기반 매수 부족 계산 + 추가 소급
    shortfall = _compute_buy_shortfall(year)
    lookback = year - 1
    while shortfall and lookback >= 2015:
        result = _sync_single_year(lookback)
        total_synced += result["synced"]
        total_skipped += result["skipped"]
        if result["source"] != "LOCAL":
            source = result["source"]
        synced_years.append(lookback)
        shortfall = _compute_buy_shortfall(year)
        lookback -= 1

    synced_years.sort()

    # 응답 메시지
    msg_parts = [f"{source} 동기화: {total_synced}건 추가"]
    if total_skipped:
        msg_parts.append(f"{total_skipped}건 스킵(중복)")
    msg_parts.append(f"(탐색 기간: {synced_years[0]}~{synced_years[-1]}년)")
    if shortfall:
        names = ", ".join(f"{s}({q}주)" for s, q in shortfall.items())
        msg_parts.append(f"[매수 부족: {names}]")
    if total_synced == 0 and total_skipped == 0:
        msg = f"KIS API 조회 완료: {synced_years[0]}~{synced_years[-1]}년 체결 내역 없음. '매매내역' 탭에서 수동으로 추가해주세요."
    else:
        msg = " ".join(msg_parts)

    # Phase 3: 동기화 후 자동 재계산 (stale 계산 방지)
    calculate_tax(year)

    return {
        "source": source,
        "synced": total_synced,
        "skipped": total_skipped,
        "sync_years": synced_years,
        "shortfall": shortfall,
        "message": msg,
    }


# 연도별 동기화 완료 캐시 (세션 내 중복 방지)
_synced_years_cache: set[int] = set()


def _sync_single_year(year: int, *, force: bool = False) -> dict:
    """단일 연도 KIS API 동기화.

    CTOS4001R + TTTS3035R을 **모두** 시도하여 누락을 최소화한다.
    이미 동기화된 연도는 건너뛴다 (force=True 제외).
    """
    if not force and year in _synced_years_cache:
        return {"source": "CACHED", "synced": 0, "skipped": 0, "message": ""}

    total_synced, total_skipped = 0, 0
    source = "LOCAL"

    # 1순위: CTOS4001R (일별거래내역 — 환율/수수료 내장)
    try:
        result = _fetch_from_ctos4001r(year)
        total_synced += result["synced"]
        total_skipped += result["skipped"]
        if result["source"] != "LOCAL":
            source = result["source"]
    except Exception as e:
        logger.info("CTOS4001R 조회 실패 (%d): %s", year, e)

    # 2순위: TTTS3035R (주문체결내역 — CTOS4001R 누락 보충)
    try:
        result = _fetch_from_ttts3035r(year)
        total_synced += result["synced"]
        total_skipped += result["skipped"]
        if result["source"] != "LOCAL" and source == "LOCAL":
            source = result["source"]
    except Exception as e:
        logger.info("TTTS3035R 조회 실패 (%d): %s", year, e)

    # 3순위: 로컬 DB (KIS API에서 못 가져온 건 보충)
    if source == "LOCAL":
        result = _sync_from_orders(year)
        total_synced += result["synced"]
        total_skipped += result["skipped"]

    _synced_years_cache.add(year)
    return {"source": source, "synced": total_synced, "skipped": total_skipped, "message": ""}


def _kis_credentials():
    """KIS API 인증 정보 확인. 미설정 시 None 반환."""
    if not all([KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK]):
        return None
    return KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK


def _fetch_from_ctos4001r(year: int) -> dict:
    """CTOS4001R 해외주식 일별거래내역 — 환율+수수료 포함."""
    creds = _kis_credentials()
    if not creds:
        raise ValueError("KIS API 키 미설정")

    from routers._kis_auth import get_access_token, make_headers

    token = get_access_token()
    headers = make_headers(token, creds[0], creds[1], "CTOS4001R")
    headers["custtype"] = "P"

    synced, skipped = 0, 0
    fk100, nk100 = "", ""

    while True:
        params = {
            "CANO": creds[2],
            "ACNT_PRDT_CD": creds[3],
            "ERLM_STRT_DT": f"{year}0101",
            "ERLM_END_DT": f"{year}1231",
            "OVRS_EXCG_CD": "",
            "PDNO": "",
            "SLL_BUY_DVSN_CD": "00",
            "LOAN_DVSN_CD": "",
            "CTX_AREA_FK100": fk100,
            "CTX_AREA_NK100": nk100,
        }

        url = f"{KIS_BASE_URL}/uapi/overseas-stock/v1/trading/inquire-period-trans"
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()

        if data.get("rt_cd") != "0":
            if synced == 0 and skipped == 0:
                raise ExternalAPIError(f"CTOS4001R 오류: {data.get('msg1', '')}")
            break

        items = data.get("output1", [])
        if not items:
            break

        for item in items:
            qty = int(item.get("ccld_qty", "0") or "0")
            if qty <= 0:
                continue

            symbol = item.get("pdno", "")
            side_code = item.get("sll_buy_dvsn_cd", "")
            side = "sell" if side_code == "01" else "buy"
            price_str = item.get("ft_ccld_unpr2") or item.get("ovrs_stck_ccld_unpr", "0")
            price = float(price_str or "0")
            trade_date_raw = item.get("trad_dt", "")
            trade_date = f"{trade_date_raw[:4]}-{trade_date_raw[4:6]}-{trade_date_raw[6:8]}" if len(trade_date_raw) == 8 else trade_date_raw

            # 환율 (API에서 제공!)
            exrt = float(item.get("erlm_exrt", "0") or "0")
            exchange_rate = exrt if exrt > 0 else get_exchange_rate(trade_date, item.get("crcy_cd", "USD"))

            # 수수료 (API에서 제공!)
            commission = float(item.get("frcr_fee1", "0") or "0")
            commission_krw = float(item.get("dmst_wcrc_fee", "0") or "0")

            price_krw = price * exchange_rate if exchange_rate else None

            if tax_store.exists_by_key(symbol, side, trade_date, price, qty):
                skipped += 1
                continue

            tax_store.insert_transaction(
                source="KIS",
                symbol=symbol,
                symbol_name=item.get("ovrs_item_name", ""),
                side=side,
                quantity=qty,
                price_foreign=price,
                currency=item.get("crcy_cd", "USD"),
                exchange_rate=exchange_rate,
                price_krw=price_krw,
                commission=commission,
                commission_krw=commission_krw,
                trade_date=trade_date,
            )
            synced += 1

        # 연속 조회 — tr_cont는 응답 헤더에 있음
        tr_cont = res.headers.get("tr_cont", "")
        if tr_cont != "M":
            break
        headers["tr_cont"] = "N"  # 연속 조회 요청 헤더 필수
        fk100 = data.get("ctx_area_fk100", "")
        nk100 = data.get("ctx_area_nk100", "")
        if not fk100:
            break
        if synced + skipped > 5000:  # 안전장치
            logger.warning("CTOS4001R %d: 5000건 초과, 중단", year)
            break

    msg = f"KIS 일별거래내역(CTOS4001R): {synced}건 동기화" + (f", {skipped}건 스킵" if skipped else "")
    if synced == 0 and skipped == 0:
        msg = f"KIS API 조회 완료: {year}년 체결 내역 없음"
    return {"source": "KIS_DAILY", "synced": synced, "skipped": skipped, "message": msg}


def _fetch_from_ttts3035r(year: int) -> dict:
    """TTTS3035R 해외주식 주문체결내역 — 기간별 조회 (환율 없음 → yfinance 보충)."""
    creds = _kis_credentials()
    if not creds:
        raise ValueError("KIS API 키 미설정")

    from routers._kis_auth import get_access_token, make_headers

    token = get_access_token()
    headers = make_headers(token, creds[0], creds[1], "TTTS3035R")

    synced, skipped = 0, 0
    fk200, nk200 = "", ""

    while True:
        params = {
            "CANO": creds[2],
            "ACNT_PRDT_CD": creds[3],
            "PDNO": "%",
            "ORD_STRT_DT": f"{year}0101",
            "ORD_END_DT": f"{year}1231",
            "SLL_BUY_DVSN": "00",
            "CCLD_NCCS_DVSN": "01",
            "OVRS_EXCG_CD": "%",
            "SORT_SQN": "DS",
            "ORD_DT": "",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "CTX_AREA_FK200": fk200,
            "CTX_AREA_NK200": nk200,
        }

        url = f"{KIS_BASE_URL}/uapi/overseas-stock/v1/trading/inquire-ccnl"
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()

        if data.get("rt_cd") != "0":
            if synced == 0 and skipped == 0:
                raise ExternalAPIError(f"TTTS3035R 오류: {data.get('msg1', '')}")
            break

        items = data.get("output", [])
        if not items:
            break

        for item in items:
            qty = int(item.get("ft_ccld_qty", "0") or "0")
            if qty <= 0:
                continue

            symbol = item.get("pdno", "")
            side = "buy" if item.get("sll_buy_dvsn_cd") == "02" else "sell"
            price = float(item.get("ft_ccld_unpr3", "0") or "0")
            trade_date_raw = item.get("ord_dt", "")
            trade_date = f"{trade_date_raw[:4]}-{trade_date_raw[4:6]}-{trade_date_raw[6:8]}" if len(trade_date_raw) == 8 else trade_date_raw

            # 중복 체크를 환율 조회 전에 수행 (성능)
            if tax_store.exists_by_key(symbol, side, trade_date, price, qty):
                skipped += 1
                continue

            currency = item.get("tr_crcy_cd", "USD") or "USD"
            exchange_rate = get_exchange_rate(trade_date, currency)
            price_krw = price * exchange_rate if exchange_rate else None

            amount = price * qty
            commission = amount * _DEFAULT_COMMISSION_RATE
            commission_krw = commission * exchange_rate if exchange_rate else 0

            tax_store.insert_transaction(
                source="KIS",
                symbol=symbol,
                symbol_name=item.get("prdt_name", ""),
                side=side,
                quantity=qty,
                price_foreign=price,
                currency=currency,
                exchange_rate=exchange_rate,
                price_krw=price_krw,
                commission=commission,
                commission_krw=commission_krw,
                trade_date=trade_date,
            )
            synced += 1

        # 연속 조회 — tr_cont는 응답 헤더에 있음
        tr_cont = res.headers.get("tr_cont", "")
        if tr_cont != "M":
            break
        headers["tr_cont"] = "N"  # 연속 조회 요청 헤더 필수
        fk200 = data.get("ctx_area_fk200", "")
        nk200 = data.get("ctx_area_nk200", "")
        if not fk200:
            break
        if synced + skipped > 5000:  # 안전장치
            logger.warning("TTTS3035R %d: 5000건 초과, 중단", year)
            break

    msg = f"KIS 주문체결내역(TTTS3035R): {synced}건 동기화" + (f", {skipped}건 스킵" if skipped else "")
    if synced == 0 and skipped == 0:
        msg = f"KIS API 조회 완료: {year}년 체결 내역 없음"
    return {"source": "KIS_CCNL", "synced": synced, "skipped": skipped, "message": msg}


def _sync_from_orders(year: int) -> dict:
    """로컬 DB orders 테이블에서 해외 체결 기록 동기화."""
    orders = list_orders(
        market="US",
        status="FILLED",
        date_from=f"{year}-01-01",
        date_to=f"{year}-12-31",
        limit=10000,
    )

    synced = 0
    skipped = 0

    for order in orders:
        order_id = order.get("id")
        if not order_id:
            continue

        # 이미 동기화된 건 skip
        existing = tax_store.get_by_source_order_id(order_id)
        if existing:
            skipped += 1
            continue

        filled_qty = order.get("filled_quantity") or order.get("quantity", 0)
        filled_price = order.get("filled_price") or order.get("price", 0)
        if filled_qty <= 0 or filled_price <= 0:
            continue

        # trade_date: filled_at 또는 placed_at에서 추출
        raw_date = order.get("filled_at") or order.get("placed_at", "")
        trade_date = raw_date[:10] if len(raw_date) >= 10 else raw_date

        exchange_rate = get_exchange_rate(trade_date, order.get("currency", "USD"))
        price_krw = filled_price * exchange_rate if exchange_rate else None

        amount = filled_price * filled_qty
        commission = amount * _DEFAULT_COMMISSION_RATE
        commission_krw = commission * exchange_rate if exchange_rate else 0

        tax_store.insert_transaction(
            source="LOCAL",
            source_order_id=order_id,
            symbol=order.get("symbol", ""),
            symbol_name=order.get("symbol_name", ""),
            side=order.get("side", ""),
            quantity=filled_qty,
            price_foreign=filled_price,
            currency=order.get("currency", "USD"),
            exchange_rate=exchange_rate,
            price_krw=price_krw,
            commission=commission,
            commission_krw=commission_krw,
            trade_date=trade_date,
        )
        synced += 1

    msg = f"로컬 DB: {synced}건 동기화" + (f", {skipped}건 스킵" if skipped else "")
    return {"source": "LOCAL", "synced": synced, "skipped": skipped, "message": msg}


# ── 수동 입력 ─────────────────────────────────────────────────────────────────

def add_manual_transaction(
    symbol: str,
    symbol_name: str,
    side: str,
    quantity: int,
    price_foreign: float,
    trade_date: str,
    currency: str = "USD",
    commission: float = 0,
    memo: str = "",
) -> dict:
    """수동 매매내역 추가."""
    if side not in ("buy", "sell"):
        raise ExternalAPIError("side는 'buy' 또는 'sell'이어야 합니다.")

    exchange_rate = get_exchange_rate(trade_date, currency)
    price_krw = price_foreign * exchange_rate if exchange_rate else None
    commission_krw = commission * exchange_rate if exchange_rate else 0

    return tax_store.insert_transaction(
        source="MANUAL",
        symbol=symbol.upper(),
        symbol_name=symbol_name,
        side=side,
        quantity=quantity,
        price_foreign=price_foreign,
        currency=currency,
        exchange_rate=exchange_rate,
        price_krw=price_krw,
        commission=commission,
        commission_krw=commission_krw,
        trade_date=trade_date,
        memo=memo,
    )


def delete_transaction(tx_id: int) -> bool:
    """매매내역 삭제."""
    tx = tax_store.get_transaction(tx_id)
    if not tx:
        raise NotFoundError(f"매매내역 #{tx_id}를 찾을 수 없습니다.")
    return tax_store.delete_transaction(tx_id)


def get_transactions(year: int, side: str = None) -> list[dict]:
    """매매내역 목록 조회."""
    return tax_store.list_transactions(year=year, side=side)


# ── FIFO 계산 ─────────────────────────────────────────────────────────────────

def calculate_tax(year: int) -> list[dict]:
    """FIFO 양도세 계산.

    해당 연도의 매도 건에 대해 양도차익을 계산하고 DB에 저장한다.
    매도→매수 매핑을 tax_fifo_lots 테이블에 기록한다.
    """
    # 기존 계산 결과 삭제
    # lots를 먼저 삭제 (calculations의 ID를 참조하므로)
    tax_store.delete_fifo_lots_by_year(year)
    tax_store.delete_calculations_by_year(year, "FIFO")

    # 전체 매매내역 조회 (연도 제한 없음 — 매수 풀 구축용)
    all_transactions = tax_store.list_transactions()

    # 해당 연도 매도 건 조회
    sell_transactions = [
        tx for tx in tax_store.list_transactions(year=year, side="sell")
    ]

    # 잔고 매입단가 fallback (매수 내역 부족 시 사용)
    holdings = _get_current_holdings()

    return _calculate_fifo(all_transactions, sell_transactions, year, holdings_fallback=holdings)


def _calculate_fifo(
    all_transactions: list[dict],
    sell_transactions: list[dict],
    year: int,
    *,
    persist: bool = True,
    holdings_fallback: dict[str, dict] = None,
) -> list[dict]:
    """선입선출법(FIFO) 양도차익 계산.

    시간순으로 거래를 재생하며, 매수는 큐에 추가하고
    매도는 **매도 시점 이전의 매수**에서만 소진한다.

    Args:
        persist: True이면 DB에 저장 (실제 계산). False이면 인메모리만 (시뮬레이션).
        holdings_fallback: {symbol: {quantity, avg_price, currency}} — 매수 부족 시 잔고 매입단가로 취득가 추정.
    """
    # 시간순으로 모든 거래를 재생하여 종목별 매수 큐 구축
    # 매도 시점에서 큐에 있는 매수만 소진 (시간역행 방지)
    buy_queues: dict[str, deque] = {}
    sorted_all = sorted(all_transactions, key=lambda t: (t["trade_date"], t["id"]))

    def _make_buy_entry(tx):
        return {
            "tx_id": tx["id"],
            "remaining": tx["quantity"],
            "price_foreign": tx["price_foreign"],
            "price_krw": tx.get("price_krw") or 0,
            "exchange_rate": tx.get("exchange_rate") or 0,
            "commission_per_unit": (tx.get("commission_krw") or 0) / tx["quantity"] if tx["quantity"] > 0 else 0,
            "trade_date": tx["trade_date"],
        }

    # Phase 1: 시간순 재생 — 과세연도 이전 거래 처리
    for tx in sorted_all:
        sym = tx["symbol"]
        if sym not in buy_queues:
            buy_queues[sym] = deque()

        if tx["side"] == "buy":
            buy_queues[sym].append(_make_buy_entry(tx))
        elif tx["side"] == "sell":
            tx_year = int(tx["trade_date"][:4]) if tx["trade_date"] else 0
            if tx_year >= year:
                continue  # 과세연도 이후 매도는 Phase 2에서 처리
            # 이전 연도 매도: 큐에서 소진 (이 시점까지의 매수만 큐에 있음)
            remaining_sell = tx["quantity"]
            queue = buy_queues[sym]
            while remaining_sell > 0 and queue:
                buy = queue[0]
                consume = min(remaining_sell, buy["remaining"])
                buy["remaining"] -= consume
                remaining_sell -= consume
                if buy["remaining"] <= 0:
                    queue.popleft()

    # Phase 2: 과세연도 매도 건 처리 — 시간순 재생 계속
    # 과세연도의 매수도 큐에 추가하면서 처리
    target_sells = {tx["id"]: tx for tx in sell_transactions}
    results = []

    for tx in sorted_all:
        if tx["trade_date"] < f"{year}-01-01":
            continue  # 이미 Phase 1에서 처리
        sym = tx["symbol"]
        if sym not in buy_queues:
            buy_queues[sym] = deque()

        if tx["side"] == "buy":
            buy_queues[sym].append(_make_buy_entry(tx))
            continue

        if tx["side"] == "sell" and tx["id"] not in target_sells:
            # 과세연도 이후 연도의 매도 (시뮬레이션에서 발생 가능) — 큐 소진
            remaining_sell = tx["quantity"]
            queue = buy_queues.get(sym, deque())
            while remaining_sell > 0 and queue:
                buy = queue[0]
                consume = min(remaining_sell, buy["remaining"])
                buy["remaining"] -= consume
                remaining_sell -= consume
                if buy["remaining"] <= 0:
                    queue.popleft()
            continue

        if tx["id"] not in target_sells:
            continue

        # 과세연도 매도 건 — 상세 기록
        sell_tx = target_sells[tx["id"]]
        sym = sell_tx["symbol"]
        queue = buy_queues.get(sym, deque())

        sell_qty = sell_tx["quantity"]
        sell_price_krw_unit = (sell_tx.get("price_krw") or 0)
        sell_commission_krw = sell_tx.get("commission_krw") or 0

        sell_total_krw = sell_price_krw_unit * sell_qty
        acquisition_total_krw = 0.0
        buy_commission_total_krw = 0.0
        lots = []
        remaining_sell = sell_qty
        warning = False

        while remaining_sell > 0 and queue:
            buy = queue[0]
            consume = min(remaining_sell, buy["remaining"])
            cost = buy["price_krw"] * consume
            buy_comm = buy["commission_per_unit"] * consume

            acquisition_total_krw += cost
            buy_commission_total_krw += buy_comm
            lots.append({
                "buy_tx_id": buy["tx_id"],
                "symbol": sym,
                "quantity": consume,
                "buy_price_krw": buy["price_krw"],
                "buy_trade_date": buy["trade_date"],
                "cost_krw": round(cost),
            })

            buy["remaining"] -= consume
            remaining_sell -= consume
            if buy["remaining"] <= 0:
                queue.popleft()

        if remaining_sell > 0:
            # 잔고 매입단가 fallback: KIS 잔고의 avg_price로 취득가 추정
            fb = (holdings_fallback or {}).get(sym, {})
            fb_avg_price = fb.get("avg_price", 0)
            fb_currency = fb.get("currency", "USD")
            if fb_avg_price > 0:
                fb_rate = get_exchange_rate(
                    sell_tx.get("trade_date", datetime.now().strftime("%Y-%m-%d")),
                    fb_currency,
                ) or (sell_tx.get("exchange_rate") or 0)
                fb_price_krw = fb_avg_price * fb_rate
                fb_cost = round(fb_price_krw * remaining_sell)
                acquisition_total_krw += fb_cost
                warning = True
                lots.append({
                    "buy_tx_id": None,
                    "symbol": sym,
                    "quantity": remaining_sell,
                    "buy_price_krw": fb_price_krw,
                    "buy_trade_date": None,
                    "cost_krw": fb_cost,
                    "warning": f"잔고 매입단가 추정 (${fb_avg_price:.2f})",
                })
            else:
                warning = True
                lots.append({
                    "buy_tx_id": None,
                    "symbol": sym,
                    "quantity": remaining_sell,
                    "buy_price_krw": 0,
                    "buy_trade_date": None,
                    "cost_krw": 0,
                    "warning": "매수 내역 부족",
                })

        commission_total_krw = sell_commission_krw + buy_commission_total_krw
        gain_loss = sell_total_krw - acquisition_total_krw - commission_total_krw

        # detail_json (하위 호환)
        detail_json = json.dumps([
            {"buy_tx_id": l["buy_tx_id"], "quantity": l["quantity"],
             "cost_krw": l["cost_krw"], "trade_date": l.get("buy_trade_date"),
             **({"warning": l["warning"]} if l.get("warning") else {})}
            for l in lots
        ], ensure_ascii=False)

        if persist:
            calc = tax_store.insert_calculation(
                sell_tx_id=sell_tx["id"],
                symbol=sym,
                method="FIFO",
                sell_quantity=sell_qty,
                sell_price_krw=round(sell_total_krw),
                acquisition_cost_krw=round(acquisition_total_krw),
                commission_total_krw=round(commission_total_krw),
                gain_loss_krw=round(gain_loss),
                trade_date=sell_tx["trade_date"],
                year=year,
                detail_json=detail_json,
            )
            # FIFO lots 기록
            for lot in lots:
                tax_store.insert_fifo_lot(
                    calculation_id=calc["id"],
                    sell_tx_id=sell_tx["id"],
                    buy_tx_id=lot["buy_tx_id"],
                    symbol=sym,
                    quantity=lot["quantity"],
                    buy_price_krw=lot["buy_price_krw"],
                    buy_trade_date=lot.get("buy_trade_date"),
                    cost_krw=lot["cost_krw"],
                    warning=lot.get("warning"),
                )
        else:
            calc = {
                "sell_tx_id": sell_tx["id"],
                "symbol": sym,
                "method": "FIFO",
                "sell_quantity": sell_qty,
                "sell_price_krw": round(sell_total_krw),
                "acquisition_cost_krw": round(acquisition_total_krw),
                "commission_total_krw": round(commission_total_krw),
                "gain_loss_krw": round(gain_loss),
                "trade_date": sell_tx["trade_date"],
                "year": year,
                "lots": lots,
            }

        if warning:
            calc["warning"] = "매수 내역 부족"
        results.append(calc)

    return results


# ── 시뮬레이션 ────────────────────────────────────────────────────────────────

def get_simulation_holdings() -> list[dict]:
    """현재 해외주식 보유 종목 목록 (시뮬레이션 입력용).

    Returns:
        [{"symbol", "name", "quantity", "avg_price", "current_price", "currency"}]
    """
    creds = _kis_credentials()
    if not creds:
        return []

    try:
        from routers._kis_auth import get_access_token, make_headers

        token = get_access_token()

        # 주야간 원장 구분
        tr_id = "TTTS3012R"
        try:
            url_dn = f"{KIS_BASE_URL}/uapi/overseas-stock/v1/trading/dayornight"
            headers_dn = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": creds[0],
                "appsecret": creds[1],
                "tr_id": "JTTT3010R",
            }
            res_dn = requests.get(url_dn, headers=headers_dn, timeout=5)
            if res_dn.status_code == 200:
                psbl = res_dn.json().get("output", {}).get("PSBL_YN", "N")
                if psbl == "Y":
                    tr_id = "JTTT3012R"
        except Exception:
            pass

        exchanges = [
            ("NASD", "USD"), ("SEHK", "HKD"), ("SHAA", "CNY"),
            ("SZAA", "CNY"), ("TKSE", "JPY"), ("HASE", "VND"), ("VNSE", "VND"),
        ]
        url = f"{KIS_BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
        headers = make_headers(token, creds[0], creds[1], tr_id)
        headers["custtype"] = "P"

        holdings = []
        for excg_cd, crcy_cd in exchanges:
            params = {
                "CANO": creds[2],
                "ACNT_PRDT_CD": creds[3],
                "OVRS_EXCG_CD": excg_cd,
                "TR_CRCY_CD": crcy_cd,
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": "",
            }
            try:
                res = requests.get(url, headers=headers, params=params, timeout=10)
                if res.status_code != 200:
                    continue
                data = res.json()
                if data.get("rt_cd") != "0":
                    continue
                for item in data.get("output1", []):
                    qty = int(item.get("ovrs_cblc_qty", 0) or 0)
                    if qty > 0:
                        holdings.append({
                            "symbol": item.get("ovrs_pdno", ""),
                            "name": item.get("ovrs_item_name", ""),
                            "quantity": qty,
                            "avg_price": float(item.get("pchs_avg_pric", 0) or 0),
                            "current_price": float(item.get("now_pric2", 0) or 0),
                            "currency": item.get("tr_crcy_cd", crcy_cd),
                        })
            except Exception:
                continue

        return holdings
    except Exception as e:
        logger.warning("시뮬레이션용 잔고 조회 실패: %s", e)
        return []


def simulate_tax(year: int, simulations: list[dict]) -> dict:
    """가상 매도 시뮬레이션 (DB 저장 없음, 인메모리 계산).

    Args:
        year: 과세연도
        simulations: [{"symbol": "AAPL", "quantity": 5, "price_foreign": 200.0, "currency": "USD"}]

    Returns:
        실제 양도세 + 가상 매도 분 합산 요약
    """
    today = datetime.now().strftime("%Y-%m-%d")
    all_transactions = tax_store.list_transactions()

    # 실제 당해 매도 건
    real_sells = [tx for tx in tax_store.list_transactions(year=year, side="sell")]

    # 가상 매도 건 생성 (음수 ID)
    virtual_sells = []
    for i, sim in enumerate(simulations):
        currency = sim.get("currency", "USD")
        exchange_rate = get_exchange_rate(today, currency)
        price_foreign = sim["price_foreign"]
        price_krw = price_foreign * exchange_rate if exchange_rate else 0
        amount = price_foreign * sim["quantity"]
        commission = amount * _DEFAULT_COMMISSION_RATE
        commission_krw = commission * exchange_rate if exchange_rate else 0

        virtual_sells.append({
            "id": -(i + 1),
            "symbol": sim["symbol"].upper(),
            "side": "sell",
            "quantity": sim["quantity"],
            "price_foreign": price_foreign,
            "price_krw": price_krw,
            "exchange_rate": exchange_rate,
            "commission": commission,
            "commission_krw": commission_krw,
            "trade_date": today,
            "currency": currency,
            "_virtual": True,
        })

    combined_sells = real_sells + virtual_sells
    holdings = _get_current_holdings()
    results = _calculate_fifo(all_transactions, combined_sells, year, persist=False, holdings_fallback=holdings)

    # 실제 vs 가상 구분
    real_results = [r for r in results if r["sell_tx_id"] > 0]
    virtual_results = [r for r in results if r["sell_tx_id"] < 0]

    def _summarize(calcs):
        total_gain = sum(c["gain_loss_krw"] for c in calcs if c["gain_loss_krw"] >= 0)
        total_loss = sum(c["gain_loss_krw"] for c in calcs if c["gain_loss_krw"] < 0)
        net = total_gain + total_loss
        taxable = max(0, net - _BASIC_DEDUCTION)
        return {
            "total_gain": round(total_gain),
            "total_loss": round(total_loss),
            "net_gain": round(net),
            "taxable_amount": taxable,
            "estimated_tax": round(taxable * _TAX_RATE),
        }

    real_summary = _summarize(real_results)
    combined_summary = _summarize(results)

    return {
        "year": year,
        "real_summary": real_summary,
        "combined_summary": combined_summary,
        "additional_tax": combined_summary["estimated_tax"] - real_summary["estimated_tax"],
        "simulated_details": virtual_results,
        "disclaimer": "가상 시뮬레이션 결과입니다. 실제 세금과 다를 수 있습니다.",
    }


# ── 연간 요약 ─────────────────────────────────────────────────────────────────

def get_annual_summary(year: int) -> dict:
    """연간 양도세 요약 (FIFO)."""
    calculations = tax_store.list_calculations(year=year, method="FIFO")

    # 계산 결과가 없으면 계산 실행
    if not calculations:
        calculations = calculate_tax(year)

    total_gain = 0
    total_loss = 0
    by_symbol: dict[str, dict] = {}
    warnings = []

    for calc in calculations:
        gl = calc.get("gain_loss_krw", 0)
        sym = calc.get("symbol", "")

        if gl >= 0:
            total_gain += gl
        else:
            total_loss += gl

        if sym not in by_symbol:
            by_symbol[sym] = {
                "symbol": sym,
                "symbol_name": "",
                "gain_loss": 0,
                "sell_count": 0,
                "total_sell_krw": 0,
                "total_acquisition_krw": 0,
            }
        entry = by_symbol[sym]
        entry["gain_loss"] += gl
        entry["sell_count"] += 1
        entry["total_sell_krw"] += calc.get("sell_price_krw", 0)
        entry["total_acquisition_krw"] += calc.get("acquisition_cost_krw", 0)

        if calc.get("warning"):
            warnings.append(f"{sym}: {calc['warning']}")

    # 종목명 보충
    transactions = tax_store.list_transactions(year=year)
    name_map = {tx["symbol"]: tx.get("symbol_name", "") for tx in transactions if tx.get("symbol_name")}
    for entry in by_symbol.values():
        entry["symbol_name"] = name_map.get(entry["symbol"], "")

    # 매매 건수
    buy_count = sum(1 for tx in transactions if tx["side"] == "buy")
    sell_count = sum(1 for tx in transactions if tx["side"] == "sell")

    net_gain = total_gain + total_loss  # total_loss는 음수
    taxable_amount = max(0, net_gain - _BASIC_DEDUCTION)
    estimated_tax = round(taxable_amount * _TAX_RATE)

    return {
        "year": year,
        "method": "FIFO",
        "total_gain": round(total_gain),
        "total_loss": round(total_loss),
        "net_gain": round(net_gain),
        "basic_deduction": _BASIC_DEDUCTION,
        "taxable_amount": taxable_amount,
        "tax_rate": _TAX_RATE,
        "estimated_tax": estimated_tax,
        "transaction_count": {"buy": buy_count, "sell": sell_count},
        "by_symbol": sorted(by_symbol.values(), key=lambda x: abs(x["gain_loss"]), reverse=True),
        "warnings": warnings,
        "disclaimer": "yfinance 환율 기준 참고용입니다. 실제 세금 신고 시 서울외국환중개 공시 매매기준율을 사용하십시오.",
    }


def get_calculations(year: int, symbol: str = None) -> list[dict]:
    """계산 상세 결과 조회 (FIFO). lots 포함."""
    calculations = tax_store.list_calculations(year=year, method="FIFO", symbol=symbol)

    # 각 계산에 lots 배열 추가
    for calc in calculations:
        calc["lots"] = tax_store.list_fifo_lots(calc["id"])

    return calculations
