"""국내 주식 KIS API 주문 구현.

order_service.py에서 dispatch되며, KIS API 호출 + 응답 파싱만 담당한다.
DB 변경(order_store)은 order_service.py에서만 수행한다.

KRX+NXT 통합시세 + SOR (2026-05-08): 신 TR_ID 일괄 전환.
- 매수 TTTC0012U / 매도 TTTC0011U / 정정·취소 TTTC0013U
- 미체결 TTTC0084R / 당일체결 TTTC0081R (EXCG_ID_DVSN_CD 필수)
- exchange 인자: SOR(기본) / KRX / NXT — body의 EXCG_ID_DVSN_CD에 일관 주입
"""

import json
import logging

import requests

from routers._kis_auth import (
    BASE_URL,
    clear_token_cache,
    issue_hashkey,
    make_headers,
)
from services.exceptions import ExternalAPIError, ServiceError

logger = logging.getLogger(__name__)

# 신 TR_ID 일괄 전환 (KRX+NXT 통합시세, 2026-05-08).
# 구 TR_ID(TTTC0802U/TTTC0801U/TTTC0803U/TTTC8036R/TTTC8001R)는 KIS 사전 고지 후 차단 가능.
_KR_TR_IDS = {
    "buy":        "TTTC0012U",   # 매수 (구 TTTC0802U)
    "sell":       "TTTC0011U",   # 매도 (구 TTTC0801U)
    "modify":     "TTTC0013U",   # 정정 (구 TTTC0803U)
    "cancel":     "TTTC0013U",   # 취소 (구 TTTC0803U)
    "open":       "TTTC0084R",   # 미체결 (구 TTTC8036R)
    "executions": "TTTC0081R",   # 당일체결 (구 TTTC8001R, EXCG_ID_DVSN_CD 필수)
    "buyable":    "TTTC8908R",   # 변경 없음
}


# ORD_DVSN 검증 매트릭스 (거래소별).
# KIS 명세 정확한 코드는 docs/kis 참조. 아래는 사용자 결정에 따른 검증 규칙.
_VALID_ORD_DVSN_BY_EXCHANGE = {
    "KRX": {"00", "01", "02", "03", "04", "05", "06", "07", "08", "09",
            "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
            "20", "21", "22", "23", "24"},
    "NXT": {"00", "03", "04",
            "11", "12", "13", "14", "15", "16",
            "21", "22", "23", "24"},  # NXT는 시장가(01) 미지원
    "SOR": {"00", "01", "03", "04",
            "11", "12", "13", "14", "15", "16"},
}


def _validate_ord_dvsn(exchange: str, order_type: str) -> None:
    """거래소별 허용 ORD_DVSN 검증. 위반 시 ServiceError."""
    exchange = (exchange or "").upper()
    valid = _VALID_ORD_DVSN_BY_EXCHANGE.get(exchange)
    if valid is None:
        raise ServiceError(f"지원하지 않는 거래소입니다: {exchange} (SOR/KRX/NXT)")
    if order_type and order_type not in valid:
        raise ServiceError(
            f"{exchange} 거래소에서 지원하지 않는 주문구분입니다: {order_type}"
        )


def _strip_leading_zeros(order_no: str) -> str:
    """10자리 제로패딩 주문번호를 KIS 정정/취소용 8자리로 변환."""
    try:
        return str(int(order_no))
    except (ValueError, TypeError):
        return order_no


def _normalize_excg_code(item: dict) -> str:
    """KIS 응답 거래소 필드 정규화.

    신/구 응답 필드명 차이를 흡수한다.
    - excg_id_dvsn_cd: 신 응답 (KRX/NXT/SOR)
    - ord_exg_gb: 체결통보 토큰 (1=KRX, 2=NXT, 3=SOR-KRX, 4=SOR-NXT)
    누락 시 'KRX' 폴백.
    """
    raw = item.get("excg_id_dvsn_cd") or item.get("EXCG_ID_DVSN_CD")
    if raw:
        v = str(raw).upper().strip()
        if v in ("KRX", "NXT", "SOR", "SOR-KRX", "SOR-NXT"):
            return v

    ord_exg_gb = item.get("ord_exg_gb") or item.get("ORD_EXG_GB")
    if ord_exg_gb is not None:
        v = str(ord_exg_gb).strip()
        return {
            "1": "KRX",
            "2": "NXT",
            "3": "SOR-KRX",
            "4": "SOR-NXT",
        }.get(v, "KRX")

    return "KRX"


def place_domestic_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    symbol, side, order_type, price, quantity,
    *, exchange: str = "SOR",
) -> dict:
    """국내 주식 주문 발송 (KIS API 호출만).

    Args:
        exchange: SOR(기본) / KRX / NXT.
                  KIS 응답에 따라 SOR-KRX/SOR-NXT로 정밀 갱신은 호출자 책임.

    Returns:
        {"order_no": ..., "org_no": ..., "exchange": ..., "kis_response": ...}
    """
    exchange = (exchange or "SOR").upper()
    _validate_ord_dvsn(exchange, order_type)

    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
    tr_id = _KR_TR_IDS[side]

    unpr = "0" if order_type == "01" else str(int(price))
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": symbol,
        "ORD_DVSN": order_type,
        "ORD_QTY": str(quantity),
        "ORD_UNPR": unpr,
        "EXCG_ID_DVSN_CD": exchange,
    }

    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None

    headers = make_headers(token, app_key, app_secret, tr_id, hashkey=hashkey)
    headers["appkey"] = app_key
    headers["appsecret"] = app_secret

    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
    except requests.RequestException as e:
        raise ExternalAPIError(f"KIS 주문 요청 실패: {e}")

    data = res.json()
    if data.get("rt_cd") != "0":
        if "토큰" in data.get("msg1", "") or "Token" in data.get("msg1", ""):
            clear_token_cache()
        raise ServiceError(f"KIS 주문 오류: {data.get('msg1', '알 수 없는 오류')}")

    output = data.get("output", {})
    # KIS 응답에 정밀 거래소 코드가 오면 그쪽을 우선
    response_exchange = _normalize_excg_code(output) if output else exchange
    if response_exchange == "KRX" and exchange != "KRX":
        # output에 거래소 정보가 없을 때는 입력 exchange 보존
        response_exchange = exchange
    return {
        "order_no": output.get("ODNO", ""),
        "org_no": output.get("KRX_FWDG_ORD_ORGNO", ""),
        "exchange": response_exchange,
        "kis_response": json.dumps(data, ensure_ascii=False),
    }


def get_domestic_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type) -> dict:
    """국내 매수가능 금액/수량 조회."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
    headers = make_headers(token, app_key, app_secret, _KR_TR_IDS["buyable"])
    params = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": symbol,
        "ORD_UNPR": str(int(price)) if price else "0",
        "ORD_DVSN": order_type,
        "CMA_EVLU_AMT_ICLD_YN": "1",
        "OVRS_ICLD_YN": "1",
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        if data.get("rt_cd") != "0":
            raise ServiceError(f"매수가능조회 오류: {data.get('msg1')}")
        out = data.get("output", {})
        return {
            "buyable_amount": out.get("ord_psbl_cash", "0"),
            "buyable_quantity": out.get("max_buy_qty", "0"),
            "deposit": out.get("dnca_tot_amt", "0"),
            "currency": "KRW",
        }
    except ServiceError:
        raise
    except Exception as e:
        raise ExternalAPIError(f"매수가능조회 요청 실패: {e}")


def _fetch_open_orders_one_exchange(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd, exchange: str,
) -> list[dict]:
    """단일 거래소(KRX/NXT/SOR) 미체결 조회. TTTC0084R + EXCG_ID_DVSN_CD."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
    headers = make_headers(token, app_key, app_secret, _KR_TR_IDS["open"])
    orders = []
    fk100, nk100 = "", ""
    while True:
        params = {
            "CANO": acnt_no,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "CTX_AREA_FK100": fk100,
            "CTX_AREA_NK100": nk100,
            "INQR_DVSN_1": "1",
            "INQR_DVSN_2": "0",
            "EXCG_ID_DVSN_CD": exchange,
        }
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            data = res.json()
        except Exception as e:
            raise ExternalAPIError(f"미체결조회 요청 실패: {e}")

        if data.get("rt_cd") != "0":
            break

        for item in data.get("output", []):
            if not item.get("odno"):
                continue
            excg_label = _normalize_excg_code(item)
            # SOR 채널은 API 취소 불가 (APBK0344). KRX/NXT 직접 채널은 취소 가능.
            api_cancellable = not str(excg_label).startswith("SOR")
            orders.append({
                "order_no": item.get("odno", ""),
                "org_no": item.get("ord_gno_brno", ""),
                "symbol": item.get("pdno", ""),
                "symbol_name": item.get("prdt_name", ""),
                "market": "KR",
                "side": "buy" if item.get("sll_buy_dvsn_cd") == "02" else "sell",
                "side_label": "매수" if item.get("sll_buy_dvsn_cd") == "02" else "매도",
                "order_type": item.get("ord_dvsn_cd") or "00",
                "order_type_label": item.get("ord_dvsn_name", ""),
                "price": item.get("ord_unpr", "0"),
                "quantity": item.get("ord_qty", "0"),
                "remaining_qty": item.get("psbl_qty", "0"),
                "filled_qty": item.get("tot_ccld_qty", "0"),
                "ordered_at": item.get("ord_tmd", ""),
                "currency": "KRW",
                "exchange": excg_label,
                "excg_id_dvsn_cd": item.get("excg_id_dvsn_cd", excg_label),
                "api_cancellable": api_cancellable,
            })

        if res.headers.get("tr_cont") == "M":
            fk100 = data.get("ctx_area_fk100", "")
            nk100 = data.get("ctx_area_nk100", "")
        else:
            break

    return orders


def get_domestic_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
    """국내 미체결 주문 목록 조회 (KRX/NXT/SOR 3거래소 합산)."""
    all_orders: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for exchange in ("KRX", "NXT", "SOR"):
        try:
            orders = _fetch_open_orders_one_exchange(
                token, app_key, app_secret, acnt_no, acnt_prdt_cd, exchange,
            )
        except ExternalAPIError as e:
            # 한 거래소 실패해도 나머지는 진행
            logger.warning("[order_kr] %s 미체결 조회 실패: %s", exchange, e)
            continue

        for order in orders:
            key = (order["order_no"], order["exchange"])
            if key in seen:
                continue
            seen.add(key)
            all_orders.append(order)

    return all_orders


def get_domestic_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
    """국내 당일 체결 내역 조회. TTTC0081R + EXCG_ID_DVSN_CD=ALL (전 거래소)."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    headers = make_headers(token, app_key, app_secret, _KR_TR_IDS["executions"])
    executions = []
    fk100, nk100 = "", ""
    while True:
        params = {
            "CANO": acnt_no,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "INQR_STRT_DT": "",
            "INQR_END_DT": "",
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "00",
            "PDNO": "",
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "INQR_DVSN_3": "00",
            "INQR_DVSN_1": "",
            "EXCG_ID_DVSN_CD": "ALL",
            "CTX_AREA_FK100": fk100,
            "CTX_AREA_NK100": nk100,
        }
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            data = res.json()
        except Exception as e:
            raise ExternalAPIError(f"체결내역 조회 실패: {e}")

        if data.get("rt_cd") != "0":
            break

        for item in data.get("output1", []):
            if not item.get("odno"):
                continue
            executions.append({
                "order_no": item.get("odno", ""),
                "symbol": item.get("pdno", ""),
                "symbol_name": item.get("prdt_name", ""),
                "market": "KR",
                "side": "buy" if item.get("sll_buy_dvsn_cd") == "02" else "sell",
                "side_label": "매수" if item.get("sll_buy_dvsn_cd") == "02" else "매도",
                "order_type_label": item.get("ord_dvsn_name", ""),
                "price": item.get("avg_prvs", "0"),
                "quantity": item.get("ord_qty", "0"),
                "filled_qty": item.get("tot_ccld_qty", "0"),
                "filled_price": item.get("avg_prvs", "0"),
                "filled_amount": item.get("tot_ccld_amt", "0"),
                "ordered_at": item.get("ord_dt", "") + " " + item.get("ord_tmd", ""),
                "status": item.get("ord_stf_yn", ""),
                "currency": "KRW",
                "exchange": _normalize_excg_code(item),
            })

        if res.headers.get("tr_cont") == "M":
            fk100 = data.get("ctx_area_fk100", "")
            nk100 = data.get("ctx_area_nk100", "")
        else:
            break

    return executions


def modify_domestic_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    order_no, org_no, order_type, price, quantity, total,
    *, exchange: str = "KRX",
) -> dict:
    """국내 주문 정정. exchange는 원주문 거래소(거래소 변경 불가)."""
    exchange = (exchange or "KRX").upper()
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-rvsecncl"
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "KRX_FWDG_ORD_ORGNO": org_no,
        "ORGN_ODNO": _strip_leading_zeros(order_no),
        "ORD_DVSN": order_type or "00",
        "RVSE_CNCL_DVSN_CD": "01",  # 정정
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(int(price)),
        "QTY_ALL_ORD_YN": "Y" if total else "N",
        "EXCG_ID_DVSN_CD": exchange,
    }
    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None
    headers = make_headers(token, app_key, app_secret, _KR_TR_IDS["modify"], hashkey=hashkey)
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        data = res.json()
    except Exception as e:
        raise ExternalAPIError(f"정정 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"정정 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}


def cancel_domestic_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    order_no, org_no, order_type, quantity, total,
    *, exchange: str = "KRX",
) -> dict:
    """국내 주문 취소. exchange는 원주문 거래소(거래소 변경 불가)."""
    exchange = (exchange or "KRX").upper()
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-rvsecncl"
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "KRX_FWDG_ORD_ORGNO": org_no,
        "ORGN_ODNO": _strip_leading_zeros(order_no),
        "ORD_DVSN": order_type or "00",
        "RVSE_CNCL_DVSN_CD": "02",  # 취소
        "ORD_QTY": str(quantity),
        "ORD_UNPR": "0",
        "QTY_ALL_ORD_YN": "Y" if total else "N",
        "EXCG_ID_DVSN_CD": exchange,
    }
    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None
    headers = make_headers(token, app_key, app_secret, _KR_TR_IDS["cancel"], hashkey=hashkey)
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        data = res.json()
    except Exception as e:
        raise ExternalAPIError(f"취소 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"취소 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}
