"""예약주문 실행 엔진.

FastAPI lifespan 백그라운드 태스크에서 주기적으로 호출된다.
조건 충족 시 자동으로 주문을 발송하고 reservations 테이블을 갱신한다.
"""

import asyncio
import logging
from datetime import datetime

from stock import order_store
from stock.utils import is_domestic

logger = logging.getLogger(__name__)

# 폴링 간격 (초)
_POLL_INTERVAL = 20

# 실행 중 플래그
_running = False


async def start_scheduler():
    """FastAPI lifespan에서 호출. 백그라운드 루프 시작."""
    global _running
    _running = True
    logger.info("[ReservationService] 예약주문 스케줄러 시작 (간격: %ds)", _POLL_INTERVAL)
    while _running:
        try:
            await asyncio.get_event_loop().run_in_executor(None, _check_and_execute)
        except Exception as e:
            logger.error("[ReservationService] 예약주문 체크 오류: %s", e)
        await asyncio.sleep(_POLL_INTERVAL)


def stop_scheduler():
    global _running
    _running = False
    logger.info("[ReservationService] 예약주문 스케줄러 중지")


def _check_and_execute():
    """대기 중인 예약주문을 체크하고 조건 충족 시 발송."""
    waiting = order_store.list_reservations(status="WAITING")
    if not waiting:
        return

    for res in waiting:
        try:
            _process_reservation(res)
        except Exception as e:
            logger.error("[ReservationService] 예약주문 처리 실패 (id=%s): %s", res["id"], e)


def _process_reservation(res: dict):
    """단일 예약주문 조건 체크 및 발송."""
    ctype = res["condition_type"]
    cvalue = res["condition_value"]
    symbol = res["symbol"]
    market = res["market"]

    # 조건 체크
    triggered = False

    if ctype == "scheduled":
        # 시간 예약: condition_value = ISO 8601 datetime
        try:
            target_dt = datetime.fromisoformat(cvalue)
            if datetime.now() >= target_dt:
                triggered = True
        except ValueError:
            pass

    elif ctype in ("price_below", "price_above"):
        # 가격 조건: 현재가 조회
        try:
            current_price = _fetch_current_price(symbol, market)
            target_price = float(cvalue)
            if ctype == "price_below" and current_price <= target_price:
                triggered = True
            elif ctype == "price_above" and current_price >= target_price:
                triggered = True
        except Exception:
            return

    if not triggered:
        return

    # 주문 발송
    try:
        from services.order_service import place_order

        order = place_order(
            symbol=symbol,
            symbol_name=res.get("symbol_name", symbol),
            market=market,
            side=res["side"],
            order_type=res["order_type"],
            price=res["price"],
            quantity=res["quantity"],
            memo=f"예약주문 자동발송 (reservation_id={res['id']})",
        )
        order_no = order.get("order_no", "")
        order_store.update_reservation_status(
            res["id"],
            "TRIGGERED",
            result_order_no=order_no,
        )
        logger.info(
            "[ReservationService] 예약주문 발동: id=%s symbol=%s order_no=%s",
            res["id"], symbol, order_no,
        )
    except Exception as e:
        order_store.update_reservation_status(res["id"], "FAILED")
        logger.error("[ReservationService] 예약주문 발송 실패 (id=%s): %s", res["id"], e)


def _fetch_current_price(symbol: str, market: str) -> float:
    """현재가 조회 (조건 체크용)."""
    if is_domestic(symbol):
        from stock.market import fetch_market_metrics
        metrics = fetch_market_metrics(symbol)
        # fetch_market_metrics는 시가총액·PER 등을 반환하므로 pykrx로 현재가 직접 조회
        from pykrx import stock as pykrx_stock
        from datetime import date
        today = date.today().strftime("%Y%m%d")
        price_data = pykrx_stock.get_market_ohlcv_by_date(today, today, symbol)
        if price_data.empty:
            raise ValueError(f"현재가 조회 실패: {symbol}")
        return float(price_data.iloc[-1]["종가"])
    else:
        from stock.yf_client import fetch_price_yf
        price = fetch_price_yf(symbol)
        if price is None:
            raise ValueError(f"해외 현재가 조회 실패: {symbol}")
        return float(price)
