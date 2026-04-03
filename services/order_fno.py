"""선물옵션 KIS API 주문 구현.

order_service.py에서 dispatch되며, KIS API 호출 + 응답 파싱만 담당한다.
DB 변경(order_store)은 order_service.py에서만 수행한다.
"""

import json
import logging
from datetime import datetime, date

import requests

from routers._kis_auth import (
    BASE_URL,
    clear_token_cache,
    issue_hashkey,
    make_headers,
)
from services.exceptions import ExternalAPIError, ServiceError

logger = logging.getLogger(__name__)

# 선물옵션 TR_ID (주간/야간, 매수·매도 동일 TR_ID — SLL_BUY_DVSN_CD로 구분)
_FNO_TR_ID_ORDER = "TTTO1101U"        # 주문 (주간)
_FNO_TR_ID_ORDER_NIGHT = "STTN1101U"  # 주문 (야간)
_FNO_TR_ID_MODIFY = "TTTO1103U"       # 정정/취소 (주간)
_FNO_TR_ID_MODIFY_NIGHT = "TTTN1103U" # 정정/취소 (야간)
_FNO_TR_ID_PSBL = "TTTO5105R"         # 주문가능 조회
_FNO_TR_ID_CCNL = "TTTO5201R"         # 주문체결내역 조회 (미체결 포함)


def _is_fno_night_session() -> bool:
    """선물옵션 야간거래 시간대 여부 (18:00 ~ 다음날 06:00)."""
    hour = datetime.now().hour
    return hour >= 18 or hour < 6


def place_fno_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
    symbol, side, price, quantity,
    nmpr_type_cd: str = "",
    krx_nmpr_cndt_cd: str = "",
    ord_dvsn_cd: str = "",
) -> dict:
    """선물옵션 주문 발송 (KIS API 호출만). SLL_BUY_DVSN_CD: 02=매수, 01=매도.

    Returns:
        {"order_no": ..., "org_no": ..., "kis_response": ...}
    """
    url = f"{BASE_URL}/uapi/domestic-futureoption/v1/trading/order"
    tr_id = _FNO_TR_ID_ORDER_NIGHT if _is_fno_night_session() else _FNO_TR_ID_ORDER

    sll_buy = "02" if side == "buy" else "01"
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd_fno,
        "ORD_PRCS_DVSN_CD": "02",           # 02: 일반주문
        "SLL_BUY_DVSN_CD": sll_buy,
        "SHTN_PDNO": symbol,
        "ORD_QTY": str(quantity),
        "UNIT_PRICE": str(price) if price else "0",
        "NMPR_TYPE_CD": nmpr_type_cd or "01",        # 01: 지정가 (기본)
        "KRX_NMPR_CNDT_CD": krx_nmpr_cndt_cd or "0", # 0: 없음
        "ORD_DVSN_CD": ord_dvsn_cd or "",
        "CTAC_TLNO": "",
        "FUOP_ITEM_DVSN_CD": "",
    }

    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None

    headers = make_headers(token, app_key, app_secret, tr_id, hashkey=hashkey)

    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
    except requests.RequestException as e:
        raise ExternalAPIError(f"선물옵션 주문 요청 실패: {e}")

    data = res.json()
    if data.get("rt_cd") != "0":
        if "토큰" in data.get("msg1", "") or "Token" in data.get("msg1", ""):
            clear_token_cache()
        raise ServiceError(f"선물옵션 주문 오류: {data.get('msg1', '알 수 없는 오류')}")

    output = data.get("output", {})
    return {
        "order_no": output.get("ODNO", ""),
        "org_no": output.get("KRX_FWDG_ORD_ORGNO", ""),
        "kis_response": json.dumps(data, ensure_ascii=False),
    }


def get_fno_buyable(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
    symbol, price, side, ord_dvsn_cd,
) -> dict:
    """선물옵션 주문가능 수량/증거금 조회."""
    url = f"{BASE_URL}/uapi/domestic-futureoption/v1/trading/inquire-psbl-order"
    headers = make_headers(token, app_key, app_secret, _FNO_TR_ID_PSBL)
    sll_buy = "02" if side == "buy" else "01"
    params = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd_fno,
        "PDNO": symbol,
        "SLL_BUY_DVSN_CD": sll_buy,
        "UNIT_PRICE": str(price) if price else "0",
        "ORD_DVSN_CD": ord_dvsn_cd or "",
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        if data.get("rt_cd") != "0":
            raise ServiceError(f"선물옵션 주문가능조회 오류: {data.get('msg1')}")
        out = data.get("output", {})
        return {
            "buyable_quantity": out.get("ord_psbl_qty", "0"),
            "buyable_amount": out.get("ord_psbl_amt", "0"),
            "margin": out.get("ncsst_mgna_amt", "0"),
            "currency": "KRW",
        }
    except ServiceError:
        raise
    except Exception as e:
        raise ExternalAPIError(f"선물옵션 주문가능조회 요청 실패: {e}")


def get_fno_orders(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
    ccld_nccs: str = "00",
) -> list[dict]:
    """선물옵션 주문체결내역 조회.

    ccld_nccs: 00=전체, 01=체결, 02=미체결
    """
    today = date.today().strftime("%Y%m%d")

    url = f"{BASE_URL}/uapi/domestic-futureoption/v1/trading/inquire-ccnl"
    headers = make_headers(token, app_key, app_secret, _FNO_TR_ID_CCNL)
    orders = []
    fk200, nk200 = "", ""

    while True:
        params = {
            "CANO": acnt_no,
            "ACNT_PRDT_CD": acnt_prdt_cd_fno,
            "STRT_ORD_DT": today,
            "END_ORD_DT": today,
            "SLL_BUY_DVSN_CD": "00",
            "CCLD_NCCS_DVSN": ccld_nccs,
            "SORT_SQN": "DS",
            "PDNO": "",
            "CTX_AREA_FK200": fk200,
            "CTX_AREA_NK200": nk200,
        }
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            data = res.json()
        except Exception as e:
            raise ExternalAPIError(f"선물옵션 주문조회 요청 실패: {e}")

        if data.get("rt_cd") != "0":
            break

        for item in data.get("output1", []):
            odno = item.get("odno") or item.get("ord_no", "")
            if not odno:
                continue
            sll_buy = item.get("sll_buy_dvsn_cd", "")
            orders.append({
                "order_no": odno,
                "org_no": item.get("orgn_odno", ""),
                "symbol": item.get("pdno", "") or item.get("shtn_pdno", ""),
                "symbol_name": item.get("prdt_name", ""),
                "market": "FNO",
                "side": "buy" if sll_buy == "02" else "sell",
                "side_label": "매수" if sll_buy == "02" else "매도",
                "order_type": "fno",
                "order_type_label": item.get("nmpr_type_name", item.get("ord_dvsn_name", "")),
                "price": item.get("unit_price", item.get("ord_unpr", "0")),
                "quantity": item.get("ord_qty", "0"),
                "remaining_qty": item.get("rmn_qty", item.get("psbl_qty", "0")),
                "filled_qty": item.get("ccld_qty", item.get("tot_ccld_qty", "0")),
                "filled_price": item.get("ccld_pric", item.get("avg_prvs", "0")),
                "ordered_at": item.get("ord_dt", "") + " " + item.get("ord_tmd", ""),
                "currency": "KRW",
                "api_cancellable": True,
            })

        if res.headers.get("tr_cont") == "M":
            fk200 = data.get("ctx_area_fk200", "")
            nk200 = data.get("ctx_area_nk200", "")
        else:
            break

    return orders


def modify_fno_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
    order_no, price, quantity, total,
    nmpr_type_cd: str = "",
    krx_nmpr_cndt_cd: str = "",
    ord_dvsn_cd: str = "",
) -> dict:
    """선물옵션 주문 정정."""
    url = f"{BASE_URL}/uapi/domestic-futureoption/v1/trading/order-rvsecncl"
    tr_id = _FNO_TR_ID_MODIFY_NIGHT if _is_fno_night_session() else _FNO_TR_ID_MODIFY
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd_fno,
        "ORD_PRCS_DVSN_CD": "02",
        "ORGN_ODNO": order_no,
        "RVSE_CNCL_DVSN_CD": "01",  # 정정
        "ORD_QTY": str(quantity),
        "UNIT_PRICE": str(price) if price else "0",
        "NMPR_TYPE_CD": nmpr_type_cd or "01",
        "KRX_NMPR_CNDT_CD": krx_nmpr_cndt_cd or "0",
        "RMN_QTY_YN": "Y" if total else "N",
        "ORD_DVSN_CD": ord_dvsn_cd or "",
        "FUOP_ITEM_DVSN_CD": "",
    }
    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None
    headers = make_headers(token, app_key, app_secret, tr_id, hashkey=hashkey)
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        data = res.json()
    except Exception as e:
        raise ExternalAPIError(f"선물옵션 정정 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"선물옵션 정정 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}


def cancel_fno_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
    order_no, quantity, total,
) -> dict:
    """선물옵션 주문 취소."""
    url = f"{BASE_URL}/uapi/domestic-futureoption/v1/trading/order-rvsecncl"
    tr_id = _FNO_TR_ID_MODIFY_NIGHT if _is_fno_night_session() else _FNO_TR_ID_MODIFY
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd_fno,
        "ORD_PRCS_DVSN_CD": "02",
        "ORGN_ODNO": order_no,
        "RVSE_CNCL_DVSN_CD": "02",  # 취소
        "ORD_QTY": str(quantity),
        "UNIT_PRICE": "0",
        "NMPR_TYPE_CD": "01",
        "KRX_NMPR_CNDT_CD": "0",
        "RMN_QTY_YN": "Y" if total else "N",
        "ORD_DVSN_CD": "",
        "FUOP_ITEM_DVSN_CD": "",
    }
    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None
    headers = make_headers(token, app_key, app_secret, tr_id, hashkey=hashkey)
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        data = res.json()
    except Exception as e:
        raise ExternalAPIError(f"선물옵션 취소 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"선물옵션 취소 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}
