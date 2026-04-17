"""주문 비즈니스 로직 서비스.

routers/order.py의 유일한 의존 대상. 주문의 전체 생명주기를 관리한다.

핵심 패턴 — Write-Ahead:
1) PENDING 선행 기록 → 2) KIS API 호출 → 3) PLACED/REJECTED 상태 갱신
이 순서를 통해 API 호출 도중 장애가 발생해도 주문 기록이 유실되지 않는다
(split-brain 방지). PENDING 상태의 주문은 대사 시 KIS 상태와 비교하여 최종 상태를 결정.

시장별 KIS API 실행은 하위 모듈에 위임:
- order_kr.py (국내주식)
- order_us.py (해외주식)
- order_fno.py (선물옵션)

주요 흐름:
- place_order()  → 시장별 디스패치 (KR→order_kr, US→order_us, FNO→order_fno)
- modify_order() → KIS 정정 성공 후 로컬 DB 가격/수량 즉시 반영
- cancel_order() → KIS 취소 성공 후 로컬 DB 상태 즉시 갱신
- _maybe_reconcile() → 30초 쿨다운으로 자동 대사 (F5 연타 방지)
- sync_orders()  → 쿨다운 무시, 사용자 명시적 강제 대사
"""

import json
import logging
import time as _time
from datetime import datetime

import requests

logger = logging.getLogger(__name__)
from services.exceptions import ConfigError, ExternalAPIError, ServiceError

from routers._kis_auth import (
    BASE_URL,
    get_access_token,
    get_kis_credentials,
    make_headers,
)
from stock import order_store
from stock.utils import is_domestic

# ── 시장별 모듈 import ────────────────────────────────────────────────────────

from services.order_kr import (
    get_domestic_buyable,
    get_domestic_open_orders,
    get_domestic_executions,
    modify_domestic_order,
    cancel_domestic_order,
    place_domestic_order,
)
from services.order_us import (
    get_overseas_buyable,
    get_overseas_open_orders,
    get_overseas_executions,
    modify_overseas_order,
    cancel_overseas_order,
    place_overseas_order,
)
from services.order_fno import (
    get_fno_buyable,
    get_fno_orders,
    modify_fno_order,
    cancel_fno_order,
    place_fno_order,
)

# ── 상수 / 유틸 ──────────────────────────────────────────────────────────────

# 미국 거래소 코드 (주문용)
# NASD를 사용하면 NYSE/AMEX/NASDAQ 모든 미국 거래소를 통합 커버한다
_US_EXCHANGE_CODE = "NASD"

# place_order 디스패치 및 get_buyable 등에서 진입부 시장 코드 검증에 사용
_VALID_MARKETS = {"KR", "US", "FNO"}


def _validate_market(market: str) -> str:
    """시장 코드 검증. 유효하지 않으면 ServiceError.

    디스패치 함수(get_buyable/get_open_orders/get_executions) 진입부에서 호출하여
    잘못된 시장 코드가 하위 모듈까지 전파되는 것을 방지한다.
    """
    m = market.upper()
    if m not in _VALID_MARKETS:
        raise ServiceError(f"지원하지 않는 시장입니다: {market} (KR/US/FNO)")
    return m


def _strip_leading_zeros(order_no: str) -> str:
    """TTTC8036R의 10자리 제로패딩 주문번호를 KIS 정정/취소용 8자리로 변환.

    KIS 미체결 조회(TTTC8036R)는 주문번호를 10자리 제로패딩으로 반환하지만,
    정정/취소 API(TTTC0803U)는 8자리 주문번호를 요구한다.
    int()로 변환하여 앞의 0을 자연스럽게 제거한다.
    예: '0020551600' → '20551600'
    """
    try:
        return str(int(order_no))
    except (ValueError, TypeError):
        return order_no


def _get_exchange_code_for_symbol(symbol: str, market: str) -> str:
    """종목 market 기반으로 해외 거래소 코드 반환."""
    if market == "KR":
        return ""
    # 미국 주식은 기본 NASD (NYSE/AMEX 포함 미국전체)
    return _US_EXCHANGE_CODE


# ── 공개 dispatch 함수 ───────────────────────────────────────────────────────


def place_order(
    symbol: str,
    symbol_name: str,
    market: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    memo: str = "",
    nmpr_type_cd: str = "",
    krx_nmpr_cndt_cd: str = "",
    ord_dvsn_cd: str = "",
) -> dict:
    """주문 발송 (매수/매도).

    Write-Ahead 패턴: PENDING 선행 기록 → KIS API → PLACED/REJECTED.

    Args:
        symbol: 종목코드
        symbol_name: 종목명
        market: KR / US / FNO
        side: buy / sell
        order_type: 00(지정가) / 01(시장가) — FNO는 nmpr_type_cd로 별도 지정
        price: 주문가격 (시장가=0)
        quantity: 수량
        memo: 메모
        nmpr_type_cd: [FNO] 호가유형코드
        krx_nmpr_cndt_cd: [FNO] KRX 호가조건코드
        ord_dvsn_cd: [FNO] 주문구분코드

    Returns:
        로컬 DB에 저장된 주문 dict
    """
    app_key, app_secret, acnt_no, acnt_prdt_cd, acnt_prdt_cd_fno = get_kis_credentials()
    token = get_access_token()

    # 1단계: PENDING 선행 기록 (Write-Ahead)
    currency = "KRW" if market in ("KR", "FNO") else "USD"
    ot = order_type if market != "FNO" else "fno"
    pending = order_store.insert_order(
        symbol=symbol, symbol_name=symbol_name, market=market,
        side=side, order_type=ot, price=float(price),
        quantity=quantity, currency=currency, memo=memo,
        status="PENDING",
    )
    pending_id = pending["id"]

    # 2단계: 시장별 KIS API 호출
    try:
        if market == "KR":
            result = place_domestic_order(
                token, app_key, app_secret, acnt_no, acnt_prdt_cd,
                symbol, side, order_type, price, quantity,
            )
        elif market == "FNO":
            if not acnt_prdt_cd_fno:
                raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
            result = place_fno_order(
                token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
                symbol, side, price, quantity,
                nmpr_type_cd=nmpr_type_cd, krx_nmpr_cndt_cd=krx_nmpr_cndt_cd,
                ord_dvsn_cd=ord_dvsn_cd,
            )
        else:
            result = place_overseas_order(
                token, app_key, app_secret, acnt_no, acnt_prdt_cd,
                symbol, side, order_type, price, quantity,
            )
    except Exception:
        order_store.update_order_status(pending_id, "REJECTED")
        raise

    # 3단계: PENDING → PLACED
    return order_store.update_order_status(
        pending_id, "PLACED",
        order_no=result["order_no"], org_no=result.get("org_no", ""),
        kis_response=result.get("kis_response", ""),
    )


def get_buyable(symbol: str, market: str, price: float, order_type: str, side: str = "buy") -> dict:
    """매수가능 금액/수량 조회."""
    market = _validate_market(market)
    app_key, app_secret, acnt_no, acnt_prdt_cd, acnt_prdt_cd_fno = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return get_domestic_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type)
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        return get_fno_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno, symbol, price, side, order_type)
    else:
        return get_overseas_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type)


def get_open_orders(market: str = "KR") -> list[dict]:
    """미체결 주문 목록 (KIS)."""
    market = _validate_market(market)
    app_key, app_secret, acnt_no, acnt_prdt_cd, acnt_prdt_cd_fno = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return get_domestic_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd)
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        return get_fno_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno, ccld_nccs="02")
    else:
        return get_overseas_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd)


def modify_order(
    order_no: str,
    org_no: str,
    market: str,
    order_type: str,
    price: float,
    quantity: int,
    total: bool = True,
    nmpr_type_cd: str = "",
    krx_nmpr_cndt_cd: str = "",
    ord_dvsn_cd: str = "",
) -> dict:
    """주문 정정. KIS 정정 성공 후 로컬 DB에 가격/수량을 즉시 반영한다."""
    app_key, app_secret, acnt_no, acnt_prdt_cd, acnt_prdt_cd_fno = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        result = modify_domestic_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, price, quantity, total,
        )
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        result = modify_fno_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
            order_no, price, quantity, total,
            nmpr_type_cd=nmpr_type_cd, krx_nmpr_cndt_cd=krx_nmpr_cndt_cd, ord_dvsn_cd=ord_dvsn_cd,
        )
    else:
        result = modify_overseas_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, price, quantity, total,
        )

    # KIS 정정 성공 → 로컬 DB에 가격/수량 즉시 반영
    local_synced = _sync_local_order_details(order_no, market, price, quantity)
    result["local_synced"] = local_synced
    return result


def cancel_order(
    order_no: str,
    org_no: str,
    market: str,
    order_type: str = "00",
    quantity: int = 0,
    total: bool = True,
) -> dict:
    """주문 취소. KIS 취소 성공 후 로컬 DB 상태를 즉시 갱신한다."""
    app_key, app_secret, acnt_no, acnt_prdt_cd, acnt_prdt_cd_fno = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        result = cancel_domestic_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, quantity, total,
        )
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        result = cancel_fno_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
            order_no, quantity, total,
        )
    else:
        result = cancel_overseas_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, quantity, total,
        )

    # KIS 취소 성공 → 로컬 DB 즉시 갱신
    new_status = "CANCELLED" if total else "PARTIAL"
    local_synced = _sync_local_order_status(order_no, market, new_status)
    result["local_synced"] = local_synced
    result["order_status"] = new_status
    return result


def get_executions(market: str = "KR") -> list[dict]:
    """당일 체결 내역 조회 (KIS)."""
    _maybe_reconcile()  # 활성 주문 대사 트리거
    market = _validate_market(market)
    app_key, app_secret, acnt_no, acnt_prdt_cd, acnt_prdt_cd_fno = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return get_domestic_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd)
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        return get_fno_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno, ccld_nccs="01")
    else:
        return get_overseas_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd)


# ── 대사(Reconciliation) ─────────────────────────────────────────────────────


def sync_orders() -> dict:
    """로컬 DB와 KIS 상태 대사(Reconciliation) — 쿨다운 무시, 강제 실행.

    사용자가 명시적으로 "동기화" 버튼을 눌렀을 때 호출된다.
    _maybe_reconcile()의 쿨다운 타이머를 무시하고 즉시 KIS API를 호출한다.
    대사 완료 후 쿨다운 타이머를 리셋하여 직후 자동 대사가 중복 실행되지 않도록 한다.

    로컬 PLACED/PARTIAL 주문을 KIS 체결+미체결 내역과 비교하여 상태를 갱신한다.
    체결에도 미체결에도 없는 주문은 CANCELLED로 처리한다.
    """
    global _last_reconcile_ts
    synced, results = _reconcile_active_orders()
    _last_reconcile_ts = _time.time()  # 강제 대사 후 쿨다운 타이머 리셋
    if results is None:
        return {"synced": 0, "message": "동기화할 활성 주문이 없습니다."}
    return {"synced": synced, "details": results}


# ── 대사 쿨다운 ────────────────────────────────────────────────────────────────

_last_reconcile_ts: float = 0.0
# 30초 쿨다운 근거: KIS API 초당 호출 제한(20회/초)과 사용자 F5 연타를 감안.
# 미체결+체결 조회를 합치면 시장당 2회 API 호출이 필요하므로,
# 30초 미만으로 줄이면 빈번한 페이지 새로고침 시 KIS API 부하가 급증한다.
_RECONCILE_COOLDOWN = 30  # 초


def _maybe_reconcile():
    """쿨다운(30초) 경과 시 활성 주문을 KIS와 자동 대사.

    get_order_history()와 get_executions()에서 호출된다.
    쿨다운 시간 내에는 KIS API를 호출하지 않아 F5 연타 시 API 호출 0회를 보장한다.
    """
    global _last_reconcile_ts
    now = _time.time()
    if now - _last_reconcile_ts > _RECONCILE_COOLDOWN:
        try:
            _reconcile_active_orders()
            _last_reconcile_ts = now
        except Exception as e:
            logger.warning("자동 대사 중 예외 발생: %s", e)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────


def _sync_local_order_status(order_no: str, market: str, new_status: str) -> bool:
    """로컬 DB에서 order_no로 주문을 찾아 상태를 갱신한다. 성공 여부 반환."""
    try:
        local = order_store.get_order_by_order_no(order_no, market)
        if local:
            order_store.update_order_status(local["id"], new_status)
            return True
        logger.warning("로컬 DB에서 주문번호 %s 미발견 (market=%s)", order_no, market)
    except Exception as e:
        logger.error("로컬 DB 상태 동기화 실패 (order_no=%s, status=%s): %s", order_no, new_status, e)
    return False


def _sync_local_order_details(order_no: str, market: str, price: float, quantity: int) -> bool:
    """로컬 DB에서 order_no로 주문을 찾아 가격/수량을 갱신한다. 성공 여부 반환."""
    try:
        local = order_store.get_order_by_order_no(order_no, market)
        if local:
            order_store.update_order_details(local["id"], price=price, quantity=quantity)
            return True
        logger.warning("로컬 DB에서 주문번호 %s 미발견 (market=%s)", order_no, market)
    except Exception as e:
        logger.error("로컬 DB 상세 동기화 실패 (order_no=%s): %s", order_no, e)
    return False


def _reconcile_active_orders() -> tuple[int, list[dict] | None]:
    """활성 주문(PLACED/PARTIAL)을 KIS 상태와 대사.

    Returns:
        (변경 건수, 결과 리스트) 또는 활성 주문 없으면 (0, None)
    """
    local_active = order_store.list_active_orders()
    if not local_active:
        return 0, None

    # 시장 구분별로 체결 + 미체결 내역 조회
    markets = {o["market"] for o in local_active}
    kis_executions: list[dict] = []
    kis_open_orders: list[dict] = []
    for mkt in markets:
        try:
            kis_executions.extend(get_executions(mkt))
        except Exception as e:
            logger.warning("대사 중 체결내역 조회 실패 (market=%s): %s", mkt, e)
        try:
            kis_open_orders.extend(get_open_orders(mkt))
        except Exception as e:
            logger.warning("대사 중 미체결 조회 실패 (market=%s): %s", mkt, e)

    # order_no 기준 매핑
    exec_map = {e["order_no"]: e for e in kis_executions if e.get("order_no")}
    open_map = {e["order_no"]: e for e in kis_open_orders if e.get("order_no")}

    synced = 0
    results = []
    for local in local_active:
        ono = local.get("order_no")
        if not ono:
            continue

        kis_exec = exec_map.get(ono)
        kis_open = open_map.get(ono)

        if kis_exec:
            # 체결 내역에 존재 → 체결 상태 판단
            filled_qty = int(kis_exec.get("filled_qty") or 0)
            order_qty = int(local.get("quantity") or 0)
            if filled_qty >= order_qty:
                new_status = "FILLED"
            elif filled_qty > 0:
                new_status = "PARTIAL"
            else:
                new_status = local["status"]

            if new_status != local["status"]:
                order_store.update_order_status(
                    local["id"],
                    new_status,
                    filled_quantity=filled_qty,
                    filled_price=float(kis_exec.get("filled_price") or 0),
                )
                synced += 1
                results.append({"id": local["id"], "order_no": ono, "action": "updated", "new_status": new_status})
            else:
                results.append({"id": local["id"], "order_no": ono, "action": "no_change"})
        elif kis_open:
            # 미체결 목록에 존재 → 아직 살아있는 주문
            results.append({"id": local["id"], "order_no": ono, "action": "no_change"})
        else:
            # 체결에도 미체결에도 없음 → 취소된 주문
            order_store.update_order_status(local["id"], "CANCELLED")
            synced += 1
            results.append({"id": local["id"], "order_no": ono, "action": "updated", "new_status": "CANCELLED"})

    return synced, results


# ── 이력 조회 서비스 ───────────────────────────────────────────────────────────


def get_order_history(
    symbol: str = None,
    market: str = None,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
) -> list[dict]:
    """주문 이력 조회. 쿨다운(30초) 경과 시 활성 주문을 KIS와 대사하여 최신화한다."""
    # 기간 필터 검증
    if date_from and date_to and date_from > date_to:
        raise ServiceError("date_from이 date_to보다 클 수 없습니다.")

    # 활성 주문 자동 대사 (쿨다운 시간 게이팅 — F5 연타 방어)
    _maybe_reconcile()

    return order_store.list_orders(
        symbol=symbol,
        market=market,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


# ── FNO 시세 서비스 ───────────────────────────────────────────────────────────


def get_fno_price(symbol: str, mrkt_div: str = "F") -> dict:
    """선물옵션 현재가 조회 (TR_ID: FHMIF10000000).

    mrkt_div: 'F'=선물, 'O'=옵션. 기본값 'F'.
    """
    app_key, app_secret, _, _, _ = get_kis_credentials()
    token = get_access_token()
    headers = make_headers(token, app_key, app_secret, "FHMIF10000000")

    url = f"{BASE_URL}/uapi/domestic-futureoption/v1/quotations/inquire-price"
    params = {
        "FID_COND_MRKT_DIV_CODE": mrkt_div,
        "FID_INPUT_ISCD": symbol,
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
    except Exception as e:
        raise ExternalAPIError(f"선물옵션 시세 조회 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"선물옵션 시세 오류: {data.get('msg1', '알 수 없는 오류')}")

    out = data.get("output1", data.get("output", {}))
    return {
        "symbol": symbol,
        "mrkt_div": mrkt_div,
        "current_price": out.get("last", out.get("stck_prpr", "0")),
        "prev_price": out.get("base", out.get("stck_bstp_enu", "0")),
        "change": out.get("diff", "0"),
        "change_rate": out.get("rate", "0"),
        "volume": out.get("acml_vol", "0"),
        "name": out.get("hts_kor_isnm", ""),
        "raw": out,
    }


# ── 예약주문 서비스 ───────────────────────────────────────────────────────────
# 예약주문은 DB에 조건(시간/가격)만 저장하고, 실제 주문 발송은
# reservation_service.py의 asyncio 폴링 루프가 조건 충족 시 place_order()를 호출한다.

# 지원하는 예약 조건 유형:
# - scheduled: ISO 8601 시각이 되면 주문 발송
# - price_below: 현재가가 목표가 이하로 하락하면 주문 발송 (매수용)
# - price_above: 현재가가 목표가 이상으로 상승하면 주문 발송 (매도용)
_VALID_CONDITION_TYPES = {"scheduled", "price_below", "price_above"}


def create_reservation(
    symbol: str,
    symbol_name: str,
    market: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    condition_type: str,
    condition_value: str,
    memo: str = "",
) -> dict:
    """예약주문 등록. 도메인 규칙 검증 후 DB 삽입."""
    if condition_type not in _VALID_CONDITION_TYPES:
        raise ServiceError(f"잘못된 condition_type: {condition_type}. 허용: {', '.join(_VALID_CONDITION_TYPES)}")

    if condition_type == "scheduled":
        try:
            datetime.fromisoformat(condition_value)
        except ValueError:
            raise ServiceError(f"잘못된 예약 시간 형식: {condition_value} (ISO 8601 필요)")
    else:
        try:
            v = float(condition_value)
            if v <= 0:
                raise ValueError
        except (ValueError, TypeError):
            raise ServiceError(f"잘못된 목표 가격: {condition_value} (양수 필요)")

    if quantity <= 0:
        raise ServiceError("수량은 1 이상이어야 합니다.")
    if price < 0:
        raise ServiceError("가격은 0 이상이어야 합니다.")

    return order_store.insert_reservation(
        symbol=symbol,
        symbol_name=symbol_name,
        market=market,
        side=side,
        order_type=order_type,
        price=price,
        quantity=quantity,
        condition_type=condition_type,
        condition_value=condition_value,
        memo=memo,
    )


def get_reservations(status: str = None) -> list[dict]:
    """예약주문 목록 조회."""
    return order_store.list_reservations(status=status)


def delete_reservation(res_id: int) -> bool:
    """예약주문 삭제. WAITING 상태만 허용.

    존재 확인 + 상태 검증 2단계:
    1) 존재하지 않으면 NotFoundError
    2) WAITING이 아니면 ServiceError (TRIGGERED/COMPLETED 상태는 이력 보존을 위해 삭제 불가)
    """
    from services.exceptions import NotFoundError
    existing = order_store.get_reservation(res_id)
    if not existing:
        raise NotFoundError(f"예약주문 {res_id}를 찾을 수 없습니다.")
    if existing.get("status") != "WAITING":
        raise ServiceError(f"WAITING 상태의 예약주문만 삭제할 수 있습니다. (현재: {existing.get('status')})")
    return order_store.delete_reservation(res_id)
