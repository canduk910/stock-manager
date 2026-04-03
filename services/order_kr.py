"""국내 주식 KIS API 주문 구현.

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

# 거래소별 TR_ID (매수/매도)
_KR_TR_IDS = {
    "buy": "TTTC0802U",
    "sell": "TTTC0801U",
}


def _strip_leading_zeros(order_no: str) -> str:
    """TTTC8036R의 10자리 제로패딩 주문번호를 KIS 정정/취소용 8자리로 변환.
    예: '0020551600' → '20551600'
    """
    try:
        return str(int(order_no))
    except (ValueError, TypeError):
        return order_no


def place_domestic_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    symbol, side, order_type, price, quantity,
) -> dict:
    """국내 주식 주문 발송 (KIS API 호출만).

    Returns:
        {"order_no": ..., "org_no": ..., "kis_response": ...}
    """
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
    return {
        "order_no": output.get("ODNO", ""),
        "org_no": output.get("KRX_FWDG_ORD_ORGNO", ""),
        "kis_response": json.dumps(data, ensure_ascii=False),
    }


def get_domestic_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type) -> dict:
    """국내 매수가능 금액/수량 조회."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
    headers = make_headers(token, app_key, app_secret, "TTTC8908R")
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


def get_domestic_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
    """국내 미체결 주문 목록 조회."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
    headers = make_headers(token, app_key, app_secret, "TTTC8036R")
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
            excg_id = item.get("excg_id_dvsn_cd", "")
            # excg_id_dvsn_cd 구분:
            #   'KRX' → API(OpenAPI)로 직접 발주 → 취소 가능
            #   'SOR' → HTS/MTS Smart Order Routing → API 취소 불가 (APBK0344)
            api_cancellable = (excg_id != "SOR")
            orders.append({
                "order_no": item.get("odno", ""),
                "org_no": item.get("ord_gno_brno", ""),        # KRX 전송 주문 기관번호
                "symbol": item.get("pdno", ""),
                "symbol_name": item.get("prdt_name", ""),
                "market": "KR",
                "side": "buy" if item.get("sll_buy_dvsn_cd") == "02" else "sell",
                "side_label": "매수" if item.get("sll_buy_dvsn_cd") == "02" else "매도",
                "order_type": item.get("ord_dvsn_cd") or "00", # 주문구분코드 (빈값→00 기본)
                "order_type_label": item.get("ord_dvsn_name", ""),
                "price": item.get("ord_unpr", "0"),
                "quantity": item.get("ord_qty", "0"),
                "remaining_qty": item.get("psbl_qty", "0"),    # 정정/취소 가능 수량
                "filled_qty": item.get("tot_ccld_qty", "0"),
                "ordered_at": item.get("ord_tmd", ""),
                "currency": "KRW",
                "excg_id_dvsn_cd": excg_id,                    # 채널 구분 (SOR=HTS/MTS)
                "api_cancellable": api_cancellable,             # API 취소 가능 여부
            })

        if res.headers.get("tr_cont") == "M":
            fk100 = data.get("ctx_area_fk100", "")
            nk100 = data.get("ctx_area_nk100", "")
        else:
            break

    return orders


def get_domestic_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
    """국내 당일 체결 내역 조회."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    headers = make_headers(token, app_key, app_secret, "TTTC8001R")
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
) -> dict:
    """국내 주문 정정."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-rvsecncl"
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "KRX_FWDG_ORD_ORGNO": org_no,
        "ORGN_ODNO": _strip_leading_zeros(order_no),  # 10자리→8자리 변환
        "ORD_DVSN": order_type or "00",  # 빈값 방어: 지정가(00) 기본
        "RVSE_CNCL_DVSN_CD": "01",  # 정정
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(int(price)),
        "QTY_ALL_ORD_YN": "Y" if total else "N",
    }
    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None
    headers = make_headers(token, app_key, app_secret, "TTTC0803U", hashkey=hashkey)
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
) -> dict:
    """국내 주문 취소."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-rvsecncl"
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "KRX_FWDG_ORD_ORGNO": org_no,
        "ORGN_ODNO": _strip_leading_zeros(order_no),  # 10자리→8자리 변환
        "ORD_DVSN": order_type or "00",  # 빈값 방어: 지정가(00) 기본
        "RVSE_CNCL_DVSN_CD": "02",  # 취소
        "ORD_QTY": str(quantity),
        "ORD_UNPR": "0",
        "QTY_ALL_ORD_YN": "Y" if total else "N",
    }
    try:
        hashkey = issue_hashkey(body)
    except Exception:
        hashkey = None
    headers = make_headers(token, app_key, app_secret, "TTTC0803U", hashkey=hashkey)
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        data = res.json()
    except Exception as e:
        raise ExternalAPIError(f"취소 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"취소 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}
