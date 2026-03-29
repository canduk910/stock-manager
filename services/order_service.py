"""주문 비즈니스 로직 서비스.

KIS API 직접 호출 + 로컬 DB 기록 + 대사(Reconciliation).
balance.py 패턴과 동일하게 requests 직접 호출.
"""

import json
import os
from datetime import datetime

import requests
from services.exceptions import ConfigError, ExternalAPIError, ServiceError

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
    nmpr_type_cd: str = "",
    krx_nmpr_cndt_cd: str = "",
    ord_dvsn_cd: str = "",
) -> dict:
    """주문 발송 (매수/매도).

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

    if market == "KR":
        return _place_domestic_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            symbol, symbol_name, side, order_type, price, quantity, memo,
        )
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        return _place_fno_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
            symbol, symbol_name, side, price, quantity, memo,
            nmpr_type_cd=nmpr_type_cd, krx_nmpr_cndt_cd=krx_nmpr_cndt_cd, ord_dvsn_cd=ord_dvsn_cd,
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
        raise ExternalAPIError(f"KIS 주문 요청 실패: {e}")

    data = res.json()
    if data.get("rt_cd") != "0":
        if "토큰" in data.get("msg1", "") or "Token" in data.get("msg1", ""):
            clear_token_cache()
        raise ServiceError(f"KIS 주문 오류: {data.get('msg1', '알 수 없는 오류')}")

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
        raise ExternalAPIError(f"KIS 해외주문 요청 실패: {e}")

    data = res.json()
    if data.get("rt_cd") != "0":
        if "토큰" in data.get("msg1", "") or "Token" in data.get("msg1", ""):
            clear_token_cache()
        raise ServiceError(f"KIS 해외주문 오류: {data.get('msg1', '알 수 없는 오류')}")

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


def _place_fno_order(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
    symbol, symbol_name, side, price, quantity, memo,
    nmpr_type_cd: str = "",
    krx_nmpr_cndt_cd: str = "",
    ord_dvsn_cd: str = "",
) -> dict:
    """선물옵션 주문 발송. SLL_BUY_DVSN_CD: 02=매수, 01=매도."""
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
    order_no = output.get("ODNO", "")
    org_no = output.get("KRX_FWDG_ORD_ORGNO", "")

    order = order_store.insert_order(
        symbol=symbol,
        symbol_name=symbol_name,
        market="FNO",
        side=side,
        order_type="fno",
        price=float(price),
        quantity=quantity,
        currency="KRW",
        memo=memo,
        order_no=order_no,
        org_no=org_no,
        kis_response=json.dumps(data, ensure_ascii=False),
    )
    return order


def get_buyable(symbol: str, market: str, price: float, order_type: str, side: str = "buy") -> dict:
    """매수가능 금액/수량 조회."""
    app_key, app_secret, acnt_no, acnt_prdt_cd, acnt_prdt_cd_fno = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return _get_domestic_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd, symbol, price, order_type)
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        return _get_fno_buyable(token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno, symbol, price, side, order_type)
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
            raise ServiceError(f"매수가능조회 오류: {data.get('msg1')}")
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
        raise ExternalAPIError(f"매수가능조회 요청 실패: {e}")


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
            raise ServiceError(f"해외 매수가능조회 오류: {data.get('msg1')}")
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
        raise ExternalAPIError(f"해외 매수가능조회 요청 실패: {e}")


def _get_fno_buyable(
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


def get_open_orders(market: str = "KR") -> list[dict]:
    """미체결 주문 목록 (KIS)."""
    app_key, app_secret, acnt_no, acnt_prdt_cd, acnt_prdt_cd_fno = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return _get_domestic_open_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd)
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        return _get_fno_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno, ccld_nccs="02")
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


def _get_fno_orders(
    token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
    ccld_nccs: str = "00",
) -> list[dict]:
    """선물옵션 주문체결내역 조회.

    ccld_nccs: 00=전체, 01=체결, 02=미체결
    """
    from datetime import date
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
        result = _modify_domestic_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, price, quantity, total,
        )
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        result = _modify_fno_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
            order_no, price, quantity, total,
            nmpr_type_cd=nmpr_type_cd, krx_nmpr_cndt_cd=krx_nmpr_cndt_cd, ord_dvsn_cd=ord_dvsn_cd,
        )
    else:
        result = _modify_overseas_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, price, quantity, total,
        )

    # KIS 정정 성공 → 로컬 DB에 가격/수량 즉시 반영
    local_synced = _sync_local_order_details(order_no, market, price, quantity)
    result["local_synced"] = local_synced
    return result


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
        raise ExternalAPIError(f"정정 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"정정 오류: {data.get('msg1')}")
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
        raise ExternalAPIError(f"해외 정정 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"해외 정정 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}


def _modify_fno_order(
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
        result = _cancel_domestic_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, quantity, total,
        )
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        result = _cancel_fno_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
            order_no, quantity, total,
        )
    else:
        result = _cancel_overseas_order(
            token, app_key, app_secret, acnt_no, acnt_prdt_cd,
            order_no, org_no, order_type, quantity, total,
        )

    # KIS 취소 성공 → 로컬 DB 즉시 갱신
    new_status = "CANCELLED" if total else "PARTIAL"
    local_synced = _sync_local_order_status(order_no, market, new_status)
    result["local_synced"] = local_synced
    result["order_status"] = new_status
    return result


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
        raise ExternalAPIError(f"취소 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"취소 오류: {data.get('msg1')}")
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
        raise ExternalAPIError(f"해외 취소 요청 실패: {e}")

    if data.get("rt_cd") != "0":
        raise ServiceError(f"해외 취소 오류: {data.get('msg1')}")
    return {"success": True, "data": data.get("output", {})}


def _cancel_fno_order(
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


def get_executions(market: str = "KR") -> list[dict]:
    """당일 체결 내역 조회 (KIS)."""
    app_key, app_secret, acnt_no, acnt_prdt_cd, acnt_prdt_cd_fno = get_kis_credentials()
    token = get_access_token()

    if market == "KR":
        return _get_domestic_executions(token, app_key, app_secret, acnt_no, acnt_prdt_cd)
    elif market == "FNO":
        if not acnt_prdt_cd_fno:
            raise ConfigError("KIS_ACNT_PRDT_CD_FNO 환경변수가 설정되지 않았습니다.")
        return _get_fno_orders(token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno, ccld_nccs="01")
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


def sync_orders() -> dict:
    """로컬 DB와 KIS 상태 대사(Reconciliation).

    로컬 PLACED/PARTIAL 주문을 KIS 체결+미체결 내역과 비교하여 상태를 갱신한다.
    체결에도 미체결에도 없는 주문은 CANCELLED로 처리한다.
    """
    synced, results = _reconcile_active_orders()
    if results is None:
        return {"synced": 0, "message": "동기화할 활성 주문이 없습니다."}
    return {"synced": synced, "details": results}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────


def _sync_local_order_status(order_no: str, market: str, new_status: str) -> bool:
    """로컬 DB에서 order_no로 주문을 찾아 상태를 갱신한다. 성공 여부 반환."""
    try:
        local = order_store.get_order_by_order_no(order_no, market)
        if local:
            order_store.update_order_status(local["id"], new_status)
            return True
    except Exception:
        pass
    return False


def _sync_local_order_details(order_no: str, market: str, price: float, quantity: int) -> bool:
    """로컬 DB에서 order_no로 주문을 찾아 가격/수량을 갱신한다. 성공 여부 반환."""
    try:
        local = order_store.get_order_by_order_no(order_no, market)
        if local:
            order_store.update_order_details(local["id"], price=price, quantity=quantity)
            return True
    except Exception:
        pass
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
        except Exception:
            pass
        try:
            kis_open_orders.extend(get_open_orders(mkt))
        except Exception:
            pass

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
    """주문 이력 조회. 반환 전 활성 주문을 KIS와 대사하여 최신화한다."""
    # 기간 필터 검증
    if date_from and date_to and date_from > date_to:
        raise ServiceError("date_from이 date_to보다 클 수 없습니다.")

    # 활성 주문 자동 대사 (best-effort)
    try:
        _reconcile_active_orders()
    except Exception:
        pass

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
    """선물옵션 현재가 조회 (FHMIF10000000)."""
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
    """예약주문 삭제. WAITING 상태만 허용."""
    return order_store.delete_reservation(res_id)
