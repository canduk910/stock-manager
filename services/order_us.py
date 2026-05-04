"""해외 주식 KIS API 주문 구현.

order_service.py에서 dispatch되며, KIS API 호출 + 응답 파싱만 담당한다.
DB 변경(order_store)은 order_service.py에서만 수행한다.
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

# 미국 거래소 코드 (주문용)
_US_EXCHANGE_CODE = "NASD"  # 미국전체 (NASD/NYSE/AMEX 통합)

# 거래소별 TR_ID (매수/매도) — 실전 환경
# KIS 공식: docs/KIS_API_REFERENCE.md:350 — TTTT1002U(매수)/TTTT1006U(매도)
# 모의: VTTT1002U/VTTT1001U (현재 코드는 실전만 지원, 모의 분기는 별도 사이클)
_US_TR_IDS = {
    "buy": "TTTT1002U",
    "sell": "TTTT1006U",
}


def place_overseas_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    symbol, side, order_type, price, quantity,
) -> dict:
    """해외 주식 주문 발송 (KIS API 호출만).

    Returns:
        {"order_no": ..., "org_no": ..., "kis_response": ...}
    """
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order"
    tr_id = _US_TR_IDS[side]

    # 미국 지정가: ord_dvsn="00", 시장가: 매수="00" 매도 MOO="31"
    if order_type == "01":
        ord_dvsn = "32" if side == "buy" else "31"
    else:
        ord_dvsn = "00"

    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": _US_EXCHANGE_CODE,
        "PDNO": symbol,
        "ORD_QTY": str(quantity),
        "OVRS_ORD_UNPR": "0" if order_type == "01" else str(price),
        "ORD_SVR_DVSN_CD": "0",
        "ORD_DVSN": ord_dvsn,
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
        raise ExternalAPIError(f"KIS 해외주문 요청 실패: {e}")

    data = res.json()
    if data.get("rt_cd") != "0":
        if "토큰" in data.get("msg1", "") or "Token" in data.get("msg1", ""):
            clear_token_cache()
        raise ServiceError(f"KIS 해외주문 오류: {data.get('msg1', '알 수 없는 오류')}")

    output = data.get("output", {})
    return {
        "order_no": output.get("ODNO", ""),
        "org_no": output.get("KRX_FWDG_ORD_ORGNO", ""),
        "kis_response": json.dumps(data, ensure_ascii=False),
    }


def get_overseas_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type) -> dict:
    """해외 매수가능 금액/수량 조회."""
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-psamount"
    headers = make_headers(token, app_key, app_secret, "TTTS3007R")
    params = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": _US_EXCHANGE_CODE,
        "OVRS_ORD_UNPR": str(price) if price else "0",
        "ITEM_CD": symbol,
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        if data.get("rt_cd") != "0":
            raise ServiceError(f"해외 매수가능조회 오류: {data.get('msg1')}")
        out = data.get("output", {})
        return {
            "buyable_amount": out.get("frcr_ord_psbl_amt1", "0"),
            "buyable_quantity": out.get("max_buy_qty", "0"),
            "deposit": out.get("frcr_dncl_amt_2", "0"),
            "currency": "USD",
        }
    except ServiceError:
        raise
    except Exception as e:
        raise ExternalAPIError(f"해외 매수가능조회 요청 실패: {e}")


def get_overseas_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
    """해외 미체결 주문 목록 조회."""
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-nccs"
    headers = make_headers(token, app_key, app_secret, "TTTS3018R")
    orders = []
    fk200, nk200 = "", ""
    while True:
        params = {
            "CANO": acnt_no,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "OVRS_EXCG_CD": "NASD",
            "SORT_SQN": "DS",
            "CTX_AREA_FK200": fk200,
            "CTX_AREA_NK200": nk200,
        }
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            data = res.json()
        except Exception as e:
            raise ExternalAPIError(f"해외 미체결조회 요청 실패: {e}")

        if data.get("rt_cd") != "0":
            break

        for item in data.get("output", []):
            if not item.get("odno"):
                continue
            orders.append({
                "order_no": item.get("odno", ""),
                "org_no": item.get("orgn_odno", ""),
                "symbol": item.get("pdno", ""),
                "symbol_name": item.get("prdt_name", ""),
                "market": "US",
                "side": "buy" if item.get("sll_buy_dvsn_cd") == "02" else "sell",
                "side_label": "매수" if item.get("sll_buy_dvsn_cd") == "02" else "매도",
                "order_type": item.get("ord_dvsn", ""),
                "order_type_label": item.get("ord_dvsn_name", ""),
                "price": item.get("ft_ord_unpr3", "0"),
                "quantity": item.get("ft_ord_qty", "0"),
                "remaining_qty": item.get("nccs_qty", "0"),
                "filled_qty": item.get("ft_ccld_qty", "0"),
                "ordered_at": item.get("ord_tmd", ""),
                "exchange": item.get("ovrs_excg_cd", ""),
                "currency": "USD",
            })

        if res.headers.get("tr_cont") == "M":
            fk200 = data.get("ctx_area_fk200", "")
            nk200 = data.get("ctx_area_nk200", "")
        else:
            break

    return orders


def get_overseas_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
    """해외 당일 체결 내역 조회."""
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-ccnl"
    # KIS 공식: docs/KIS_API_REFERENCE.md:345 — TTTS3035R(실전)/VTTS3035R(모의)
    headers = make_headers(token, app_key, app_secret, "TTTS3035R")
    executions = []
    fk200, nk200 = "", ""
    while True:
        params = {
            "CANO": acnt_no,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "PDNO": "",
            "ORD_STRT_DT": "",
            "ORD_END_DT": "",
            "SLL_BUY_DVSN_CD": "00",
            "CCLD_NCCS_DVSN": "00",
            "OVRS_EXCG_CD": "NASD",
            "SORT_SQN": "DS",
            "CTX_AREA_FK200": fk200,
            "CTX_AREA_NK200": nk200,
        }
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            data = res.json()
        except Exception as e:
            raise ExternalAPIError(f"해외 체결내역 조회 실패: {e}")

        if data.get("rt_cd") != "0":
            break

        for item in data.get("output", []):
            if not item.get("odno"):
                continue
            executions.append({
                "order_no": item.get("odno", ""),
                "symbol": item.get("pdno", ""),
                "symbol_name": item.get("prdt_name", ""),
                "market": "US",
                "side": "buy" if item.get("sll_buy_dvsn_cd") == "02" else "sell",
                "side_label": "매수" if item.get("sll_buy_dvsn_cd") == "02" else "매도",
                "order_type_label": item.get("ord_dvsn_name", ""),
                "price": item.get("ft_ccld_unpr3", "0"),
                "quantity": item.get("ft_ord_qty", "0"),
                "filled_qty": item.get("ft_ccld_qty", "0"),
                "filled_price": item.get("ft_ccld_unpr3", "0"),
                "filled_amount": item.get("ft_ccld_amt3", "0"),
                "ordered_at": item.get("ord_dt", "") + " " + item.get("ord_tmd", ""),
                "exchange": item.get("ovrs_excg_cd", ""),
                "currency": "USD",
            })

        if res.headers.get("tr_cont") == "M":
            fk200 = data.get("ctx_area_fk200", "")
            nk200 = data.get("ctx_area_nk200", "")
        else:
            break

    return executions


def modify_overseas_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    order_no, org_no, order_type, price, quantity, total,
    symbol: str = "",
) -> dict:
    """해외 주문 정정. PDNO(종목코드) 필수."""
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order-rvsecncl"
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": _US_EXCHANGE_CODE,
        "PDNO": symbol,  # KIS 미국 정정/취소는 PDNO 필수 (빈 문자열 시 "상품번호 확인" 오류)
        "ORGN_ODNO": order_no,
        "RVSE_CNCL_DVSN_CD": "01",  # 정정
        "ORD_QTY": str(quantity),
        "OVRS_ORD_UNPR": str(price),
        "CTAC_TLNO": "",
        "MGCO_APTM_ODNO": "",
        "ORD_SVR_DVSN_CD": "0",
    }
    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None
    # KIS 공식: docs/KIS_API_REFERENCE.md:341 — TTTT1004U(실전 정정·취소)/VTTT1004U(모의)
    headers = make_headers(token, app_key, app_secret, "TTTT1004U", hashkey=hashkey)
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        data = res.json()
    except Exception as e:
        raise ExternalAPIError(f"해외 정정 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"해외 정정 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}


def cancel_overseas_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    order_no, org_no, order_type, quantity, total,
    symbol: str = "",
) -> dict:
    """해외 주문 취소. PDNO(종목코드) 필수."""
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order-rvsecncl"
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": _US_EXCHANGE_CODE,
        "PDNO": symbol,  # KIS 미국 정정/취소는 PDNO 필수 (빈 문자열 시 "상품번호 확인" 오류)
        "ORGN_ODNO": order_no,
        "RVSE_CNCL_DVSN_CD": "02",  # 취소
        "ORD_QTY": str(quantity),
        "OVRS_ORD_UNPR": "0",
        "CTAC_TLNO": "",
        "MGCO_APTM_ODNO": "",
        "ORD_SVR_DVSN_CD": "0",
    }
    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None
    # KIS 공식: docs/KIS_API_REFERENCE.md:341 — TTTT1004U(실전 정정·취소)/VTTT1004U(모의)
    headers = make_headers(token, app_key, app_secret, "TTTT1004U", hashkey=hashkey)
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        data = res.json()
    except Exception as e:
        raise ExternalAPIError(f"해외 취소 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"해외 취소 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}
