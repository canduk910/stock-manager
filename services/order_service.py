"""주문 비즈니스 로직 서비스.

KIS API 직접 호출 + 로컬 DB 기록 + 대사(Reconciliation).
balance.py 패턴과 동일하게 requests 직접 호출.
"""

import json
import os

import requests
from fastapi import HTTPException

from routers._kis_auth import (
    BASE_URL,
    get_access_token,
    get_kis_credentials,
    clear_token_cache,
    issue_hashkey,
    make_headers,
)
from stock import order_store
from stock.utils import is_domestic

# 미국 거래소 코드 (주문용)
_US_EXCHANGE_CODE = "NASD"  # 미국전체 (NASD/NYSE/AMEX 통합)

# 거래소별 TR_ID (매수/매도)
_KR_TR_IDS = {
    "buy": "TTTC0802U",
    "sell": "TTTC0801U",
}
_US_TR_IDS = {
    "buy": "JTTT1002U",
    "sell": "JTTT1006U",
}


def _get_exchange_code_for_symbol(symbol: str, market: str) -> str:
    """종목 market 기반으로 해외 거래소 코드 반환."""
    if market == "KR":
        return ""
    # 미국 주식은 기본 NASD (NYSE/AMEX 포함 미국전체)
    return _US_EXCHANGE_CODE


def place_order(
    symbol: str,
    symbol_name: str,
    market: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    memo: str = "",
) -> dict:
    """주문 발송 (매수/매도).

    Args:
        symbol: 종목코드
        symbol_name: 종목명
        market: KR / US
        side: buy / sell
        order_type: 00(지정가) / 01(시장가)
        price: 주문가격 (시장가=0)
        quantity: 수량
        memo: 메모

    Returns:
        로컬 DB에 저장된 주문 dict
    """
    app_key, app_secret, acnt_no, acnt_prdt_cd = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return _place_domestic_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            symbol, symbol_name, side, order_type, price, quantity, memo,
        )
    else:
        return _place_overseas_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            symbol, symbol_name, market, side, order_type, price, quantity, memo,
        )


def _place_domestic_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    symbol, symbol_name, side, order_type, price, quantity, memo,
) -> dict:
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
        raise HTTPException(status_code=502, detail=f"KIS 주문 요청 실패: {e}")

    data = res.json()
    if data.get("rt_cd") != "0":
        if "토큰" in data.get("msg1", "") or "Token" in data.get("msg1", ""):
            clear_token_cache()
        raise HTTPException(status_code=400, detail=f"KIS 주문 오류: {data.get('msg1', '알 수 없는 오류')}")

    output = data.get("output", {})
    order_no = output.get("ODNO", "")
    org_no = output.get("KRX_FWDG_ORD_ORGNO", "")

    order = order_store.insert_order(
        symbol=symbol,
        symbol_name=symbol_name,
        market="KR",
        side=side,
        order_type=order_type,
        price=float(price),
        quantity=quantity,
        currency="KRW",
        memo=memo,
        order_no=order_no,
        org_no=org_no,
        kis_response=json.dumps(data, ensure_ascii=False),
    )
    return order


def _place_overseas_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    symbol, symbol_name, market, side, order_type, price, quantity, memo,
) -> dict:
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order"
    tr_id = _US_TR_IDS[side]

    # 미국 지정가: ord_dvsn="00", 시장가: 매수="00" 매도 MOO="31"
    if order_type == "01":
        # 시장가 처리 (매수=LOO, 매도=MOO)
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
        raise HTTPException(status_code=502, detail=f"KIS 해외주문 요청 실패: {e}")

    data = res.json()
    if data.get("rt_cd") != "0":
        if "토큰" in data.get("msg1", "") or "Token" in data.get("msg1", ""):
            clear_token_cache()
        raise HTTPException(status_code=400, detail=f"KIS 해외주문 오류: {data.get('msg1', '알 수 없는 오류')}")

    output = data.get("output", {})
    order_no = output.get("ODNO", "")
    org_no = output.get("KRX_FWDG_ORD_ORGNO", "")

    order = order_store.insert_order(
        symbol=symbol,
        symbol_name=symbol_name,
        market=market,
        side=side,
        order_type=order_type,
        price=float(price),
        quantity=quantity,
        currency="USD",
        memo=memo,
        order_no=order_no,
        org_no=org_no,
        kis_response=json.dumps(data, ensure_ascii=False),
    )
    return order


def get_buyable(symbol: str, market: str, price: float, order_type: str) -> dict:
    """매수가능 금액/수량 조회."""
    app_key, app_secret, acnt_no, acnt_prdt_cd = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return _get_domestic_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type)
    else:
        return _get_overseas_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type)


def _get_domestic_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type) -> dict:
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
            raise HTTPException(status_code=400, detail=f"매수가능조회 오류: {data.get('msg1')}")
        out = data.get("output", {})
        return {
            "buyable_amount": out.get("ord_psbl_cash", "0"),
            "buyable_quantity": out.get("max_buy_qty", "0"),
            "deposit": out.get("dnca_tot_amt", "0"),
            "currency": "KRW",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"매수가능조회 요청 실패: {e}")


def _get_overseas_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type) -> dict:
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
            raise HTTPException(status_code=400, detail=f"해외 매수가능조회 오류: {data.get('msg1')}")
        out = data.get("output", {})
        return {
            "buyable_amount": out.get("frcr_ord_psbl_amt1", "0"),
            "buyable_quantity": out.get("max_buy_qty", "0"),
            "deposit": out.get("frcr_dncl_amt_2", "0"),
            "currency": "USD",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"해외 매수가능조회 요청 실패: {e}")


def get_open_orders(market: str = "KR") -> list[dict]:
    """미체결 주문 목록 (KIS)."""
    app_key, app_secret, acnt_no, acnt_prdt_cd = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return _get_domestic_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd)
    else:
        return _get_overseas_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd)


def _get_domestic_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
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
            raise HTTPException(status_code=502, detail=f"미체결조회 요청 실패: {e}")

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


def _get_overseas_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
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
            raise HTTPException(status_code=502, detail=f"해외 미체결조회 요청 실패: {e}")

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


def modify_order(
    order_no: str,
    org_no: str,
    market: str,
    order_type: str,
    price: float,
    quantity: int,
    total: bool = True,
) -> dict:
    """주문 정정."""
    app_key, app_secret, acnt_no, acnt_prdt_cd = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return _modify_domestic_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, price, quantity, total,
        )
    else:
        return _modify_overseas_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, price, quantity, total,
        )


def _strip_leading_zeros(order_no: str) -> str:
    """TTTC8036R의 10자리 제로패딩 주문번호를 KIS 정정/취소용 8자리로 변환.
    예: '0020551600' → '20551600'
    """
    try:
        return str(int(order_no))
    except (ValueError, TypeError):
        return order_no


def _modify_domestic_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    order_no, org_no, order_type, price, quantity, total,
) -> dict:
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
        raise HTTPException(status_code=502, detail=f"정정 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise HTTPException(status_code=400, detail=f"정정 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}


def _modify_overseas_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    order_no, org_no, order_type, price, quantity, total,
) -> dict:
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order-rvsecncl"
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": _US_EXCHANGE_CODE,
        "PDNO": "",
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
    headers = make_headers(token, app_key, app_secret, "TTTS0309U", hashkey=hashkey)
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        data = res.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"해외 정정 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise HTTPException(status_code=400, detail=f"해외 정정 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}


def cancel_order(
    order_no: str,
    org_no: str,
    market: str,
    order_type: str = "00",
    quantity: int = 0,
    total: bool = True,
) -> dict:
    """주문 취소."""
    app_key, app_secret, acnt_no, acnt_prdt_cd = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return _cancel_domestic_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, quantity, total,
        )
    else:
        return _cancel_overseas_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, quantity, total,
        )


def _cancel_domestic_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    order_no, org_no, order_type, quantity, total,
) -> dict:
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
        raise HTTPException(status_code=502, detail=f"취소 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise HTTPException(status_code=400, detail=f"취소 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}


def _cancel_overseas_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    order_no, org_no, order_type, quantity, total,
) -> dict:
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order-rvsecncl"
    body = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": _US_EXCHANGE_CODE,
        "PDNO": "",
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
    headers = make_headers(token, app_key, app_secret, "TTTS0309U", hashkey=hashkey)
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        data = res.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"해외 취소 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise HTTPException(status_code=400, detail=f"해외 취소 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}


def get_executions(market: str = "KR") -> list[dict]:
    """당일 체결 내역 조회 (KIS)."""
    app_key, app_secret, acnt_no, acnt_prdt_cd = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return _get_domestic_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd)
    else:
        return _get_overseas_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd)


def _get_domestic_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
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
            raise HTTPException(status_code=502, detail=f"체결내역 조회 실패: {e}")

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


def _get_overseas_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd) -> list[dict]:
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-ccnl"
    headers = make_headers(token, app_key, app_secret, "JTTT3001R")
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
            raise HTTPException(status_code=502, detail=f"해외 체결내역 조회 실패: {e}")

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


def sync_orders() -> dict:
    """로컬 DB와 KIS 체결 내역 대사(Reconciliation).

    로컬 PLACED/PARTIAL 주문을 KIS 당일 체결 내역과 비교하여 상태를 갱신한다.
    """
    local_active = order_store.list_active_orders()
    if not local_active:
        return {"synced": 0, "message": "동기화할 활성 주문이 없습니다."}

    # 시장 구분별로 체결 내역 조회
    markets = {o["market"] for o in local_active}
    kis_executions: list[dict] = []
    for mkt in markets:
        try:
            execs = get_executions(mkt)
            kis_executions.extend(execs)
        except Exception:
            pass

    # order_no 기준 매핑
    exec_map = {e["order_no"]: e for e in kis_executions if e.get("order_no")}

    synced = 0
    results = []
    for local in local_active:
        ono = local.get("order_no")
        if not ono:
            continue
        kis_exec = exec_map.get(ono)
        if not kis_exec:
            results.append({"id": local["id"], "order_no": ono, "action": "no_change"})
            continue

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

    return {"synced": synced, "details": results}
