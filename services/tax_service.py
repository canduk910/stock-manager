"""해외주식 양도소득세 계산 서비스.

데이터 수집(KIS API / 로컬 DB / 수동 입력) + 환율 조회 + FIFO/이동평균 계산.
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

        return None
    except Exception as e:
        logger.warning("yfinance 환율 조회 실패 (%s %s): %s", currency, date, e)
        return None


# ── KIS API 체결 조회 + 동기화 ────────────────────────────────────────────────

def sync_transactions(year: int) -> dict:
    """KIS API에서 해외 체결내역을 동기화.

    1순위: CTOS4001R (일별거래내역 — 환율+수수료 포함)
    2순위: TTTS3035R (주문체결내역 — 기간별, 환율 없음 → yfinance 보충)
    3순위: 로컬 DB orders 테이블

    Returns:
        {"source": str, "synced": int, "skipped": int, "message": str}
    """
    # 1순위: CTOS4001R (일별거래내역 — 환율/수수료 내장)
    try:
        result = _fetch_from_ctos4001r(year)
        if result["synced"] > 0 or result["source"] == "KIS_DAILY":
            return result
    except Exception as e:
        logger.info("CTOS4001R 조회 실패: %s", e)

    # 2순위: TTTS3035R (주문체결내역 — 기간별)
    try:
        result = _fetch_from_ttts3035r(year)
        if result["synced"] > 0 or result["source"] == "KIS_CCNL":
            return result
    except Exception as e:
        logger.info("TTTS3035R 조회 실패: %s", e)

    # 3순위: 로컬 DB
    result = _sync_from_orders(year)
    if result["synced"] == 0 and result["skipped"] == 0:
        result["message"] = "KIS API 및 로컬 주문 이력에 해당 연도 체결 내역이 없습니다. '매매내역' 탭에서 수동으로 추가해주세요."
    return result


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
            if synced == 0:
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

        # 연속 조회
        tr_cont = data.get("tr_cont", "")
        if tr_cont in ("D", "E", ""):
            break
        fk100 = data.get("ctx_area_fk100", "")
        nk100 = data.get("ctx_area_nk100", "")
        if not fk100:
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
            if synced == 0:
                raise ExternalAPIError(f"TTTS3035R 오류: {data.get('msg1', '')}")
            break

        items = data.get("output", [])
        if not items:
            break

        for item in items:
            if not item.get("odno"):
                continue
            qty = int(item.get("ft_ccld_qty", "0") or "0")
            if qty <= 0:
                continue

            symbol = item.get("pdno", "")
            side = "buy" if item.get("sll_buy_dvsn_cd") == "02" else "sell"
            price = float(item.get("ft_ccld_unpr3", "0") or "0")
            trade_date_raw = item.get("ord_dt", "")
            trade_date = f"{trade_date_raw[:4]}-{trade_date_raw[4:6]}-{trade_date_raw[6:8]}" if len(trade_date_raw) == 8 else trade_date_raw

            currency = item.get("tr_crcy_cd", "USD") or "USD"
            exchange_rate = get_exchange_rate(trade_date, currency)
            price_krw = price * exchange_rate if exchange_rate else None

            amount = price * qty
            commission = amount * _DEFAULT_COMMISSION_RATE
            commission_krw = commission * exchange_rate if exchange_rate else 0

            if tax_store.exists_by_key(symbol, side, trade_date, price, qty):
                skipped += 1
                continue

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

        # 연속 조회
        tr_cont = data.get("tr_cont", "")
        if tr_cont in ("D", "E", ""):
            break
        fk200 = data.get("ctx_area_fk200", "")
        nk200 = data.get("ctx_area_nk200", "")
        if not fk200:
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

def calculate_tax(year: int, method: str = "FIFO") -> list[dict]:
    """양도세 계산 (FIFO 또는 이동평균법).

    해당 연도의 매도 건에 대해 양도차익을 계산하고 DB에 저장한다.
    """
    method = method.upper()
    if method not in ("FIFO", "AVG"):
        raise ExternalAPIError("method는 'FIFO' 또는 'AVG'이어야 합니다.")

    # 기존 계산 결과 삭제
    tax_store.delete_calculations_by_year(year, method)

    # 전체 매매내역 조회 (연도 제한 없음 — 매수 풀 구축용)
    all_transactions = tax_store.list_transactions()

    # 해당 연도 매도 건 조회
    sell_transactions = [
        tx for tx in tax_store.list_transactions(year=year, side="sell")
    ]

    if method == "FIFO":
        return _calculate_fifo(all_transactions, sell_transactions, year)
    else:
        return _calculate_avg(all_transactions, sell_transactions, year)


def _calculate_fifo(
    all_transactions: list[dict],
    sell_transactions: list[dict],
    year: int,
) -> list[dict]:
    """선입선출법(FIFO) 양도차익 계산."""
    # 종목별 매수 큐 구축 (전체 이력)
    buy_queues: dict[str, deque] = {}
    for tx in all_transactions:
        if tx["side"] != "buy":
            continue
        sym = tx["symbol"]
        if sym not in buy_queues:
            buy_queues[sym] = deque()
        buy_queues[sym].append({
            "tx_id": tx["id"],
            "remaining": tx["quantity"],
            "price_foreign": tx["price_foreign"],
            "price_krw": tx.get("price_krw") or 0,
            "exchange_rate": tx.get("exchange_rate") or 0,
            "commission_per_unit": (tx.get("commission_krw") or 0) / tx["quantity"] if tx["quantity"] > 0 else 0,
            "trade_date": tx["trade_date"],
        })

    # 매도 건 발생 전까지의 매수 큐에서 소진 (매도 이전의 매수만 사용)
    # 단순화: 전체 매수 큐에서 순서대로 소진
    # 이전 연도 매도 건에서 이미 소진된 분을 반영
    for tx in all_transactions:
        if tx["side"] != "sell":
            continue
        # 해당 연도 이전의 매도 건은 매수 풀에서 차감
        tx_year = int(tx["trade_date"][:4]) if tx["trade_date"] else 0
        if tx_year >= year:
            continue  # 해당 연도 이후 매도는 아래에서 처리

        sym = tx["symbol"]
        remaining_sell = tx["quantity"]
        queue = buy_queues.get(sym, deque())

        while remaining_sell > 0 and queue:
            buy = queue[0]
            consume = min(remaining_sell, buy["remaining"])
            buy["remaining"] -= consume
            remaining_sell -= consume
            if buy["remaining"] <= 0:
                queue.popleft()

    # 해당 연도 매도 건 처리
    results = []
    for sell_tx in sell_transactions:
        sym = sell_tx["symbol"]
        queue = buy_queues.get(sym, deque())

        sell_qty = sell_tx["quantity"]
        sell_rate = sell_tx.get("exchange_rate") or 0
        sell_price_krw_unit = (sell_tx.get("price_krw") or 0)
        sell_commission_krw = sell_tx.get("commission_krw") or 0

        sell_total_krw = sell_price_krw_unit * sell_qty
        acquisition_total_krw = 0.0
        buy_commission_total_krw = 0.0
        detail = []
        remaining_sell = sell_qty
        warning = False

        while remaining_sell > 0 and queue:
            buy = queue[0]
            consume = min(remaining_sell, buy["remaining"])
            cost = buy["price_krw"] * consume
            buy_comm = buy["commission_per_unit"] * consume

            acquisition_total_krw += cost
            buy_commission_total_krw += buy_comm
            detail.append({
                "buy_tx_id": buy["tx_id"],
                "quantity": consume,
                "cost_krw": round(cost),
                "trade_date": buy["trade_date"],
            })

            buy["remaining"] -= consume
            remaining_sell -= consume
            if buy["remaining"] <= 0:
                queue.popleft()

        if remaining_sell > 0:
            # 매수 풀 부족
            warning = True
            detail.append({
                "buy_tx_id": None,
                "quantity": remaining_sell,
                "cost_krw": 0,
                "trade_date": None,
                "warning": "매수 내역 부족",
            })

        commission_total_krw = sell_commission_krw + buy_commission_total_krw
        gain_loss = sell_total_krw - acquisition_total_krw - commission_total_krw

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
            detail_json=json.dumps(detail, ensure_ascii=False),
        )
        if warning:
            calc["warning"] = "매수 내역 부족"
        results.append(calc)

    return results


def _calculate_avg(
    all_transactions: list[dict],
    sell_transactions: list[dict],
    year: int,
) -> list[dict]:
    """이동평균법 양도차익 계산."""
    # 종목별 이동평균 단가 추적
    avg_pool: dict[str, dict] = {}  # symbol -> {total_cost_krw, total_qty, avg_commission_per_unit_krw}

    for tx in all_transactions:
        sym = tx["symbol"]
        if sym not in avg_pool:
            avg_pool[sym] = {"total_cost_krw": 0.0, "total_qty": 0, "total_commission_krw": 0.0}

        pool = avg_pool[sym]
        qty = tx["quantity"]
        price_krw = (tx.get("price_krw") or 0)
        commission_krw = tx.get("commission_krw") or 0

        if tx["side"] == "buy":
            pool["total_cost_krw"] += price_krw * qty
            pool["total_qty"] += qty
            pool["total_commission_krw"] += commission_krw

        elif tx["side"] == "sell":
            tx_year = int(tx["trade_date"][:4]) if tx["trade_date"] else 0
            if tx_year < year:
                # 이전 연도 매도: 풀에서 차감
                if pool["total_qty"] > 0:
                    avg_cost = pool["total_cost_krw"] / pool["total_qty"]
                    avg_comm = pool["total_commission_krw"] / pool["total_qty"]
                    consume = min(qty, pool["total_qty"])
                    pool["total_cost_krw"] -= avg_cost * consume
                    pool["total_qty"] -= consume
                    pool["total_commission_krw"] -= avg_comm * consume

    # 해당 연도 매도 건 처리
    results = []
    for sell_tx in sell_transactions:
        sym = sell_tx["symbol"]
        pool = avg_pool.get(sym, {"total_cost_krw": 0, "total_qty": 0, "total_commission_krw": 0})

        sell_qty = sell_tx["quantity"]
        sell_price_krw_unit = sell_tx.get("price_krw") or 0
        sell_commission_krw = sell_tx.get("commission_krw") or 0

        sell_total_krw = sell_price_krw_unit * sell_qty

        warning = False
        if pool["total_qty"] <= 0:
            acquisition_total_krw = 0
            buy_commission_total_krw = 0
            warning = True
        else:
            avg_cost = pool["total_cost_krw"] / pool["total_qty"]
            avg_comm = pool["total_commission_krw"] / pool["total_qty"]
            consume = min(sell_qty, pool["total_qty"])
            acquisition_total_krw = avg_cost * consume
            buy_commission_total_krw = avg_comm * consume

            # 풀에서 차감
            pool["total_cost_krw"] -= avg_cost * consume
            pool["total_qty"] -= consume
            pool["total_commission_krw"] -= avg_comm * consume

            if sell_qty > consume:
                warning = True

        commission_total_krw = sell_commission_krw + buy_commission_total_krw
        gain_loss = sell_total_krw - acquisition_total_krw - commission_total_krw

        calc = tax_store.insert_calculation(
            sell_tx_id=sell_tx["id"],
            symbol=sym,
            method="AVG",
            sell_quantity=sell_qty,
            sell_price_krw=round(sell_total_krw),
            acquisition_cost_krw=round(acquisition_total_krw),
            commission_total_krw=round(commission_total_krw),
            gain_loss_krw=round(gain_loss),
            trade_date=sell_tx["trade_date"],
            year=year,
            detail_json=json.dumps({"method": "이동평균법"}, ensure_ascii=False),
        )
        if warning:
            calc["warning"] = "매수 내역 부족"
        results.append(calc)

    return results


# ── 연간 요약 ─────────────────────────────────────────────────────────────────

def get_annual_summary(year: int, method: str = "FIFO") -> dict:
    """연간 양도세 요약."""
    method = method.upper()
    calculations = tax_store.list_calculations(year=year, method=method)

    # 계산 결과가 없으면 계산 실행
    if not calculations:
        calculations = calculate_tax(year, method)

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
        "method": method,
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


def get_calculations(year: int, method: str = "FIFO", symbol: str = None) -> list[dict]:
    """계산 상세 결과 조회."""
    return tax_store.list_calculations(year=year, method=method, symbol=symbol)
