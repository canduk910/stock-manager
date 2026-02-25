"""잔고 조회 API 라우터 (main.py에서 이동)."""

import json
import os

import requests
from fastapi import APIRouter, HTTPException

from stock.market import fetch_market_metrics
from stock.yf_client import fetch_detail_yf

router = APIRouter(prefix="/api", tags=["balance"])

BASE_URL = os.getenv("KIS_BASE_URL") or "https://openapi.koreainvestment.com:9443"

# 인메모리 토큰 캐시 (재시작 시 재발급)
_access_token: str | None = None

# 해외주식 거래소 코드 → 통화 매핑 (미국전체, 홍콩, 상해, 심천, 도쿄, 하노이, 호치민)
_OVERSEAS_EXCHANGES = [
    ("NASD", "USD"),
    ("SEHK", "HKD"),
    ("SHAA", "CNY"),
    ("SZAA", "CNY"),
    ("TKSE", "JPY"),
    ("HASE", "VND"),
    ("VNSE", "VND"),
]


def _get_access_token() -> str:
    global _access_token
    if _access_token:
        return _access_token

    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    if not app_key or not app_secret:
        raise HTTPException(
            status_code=503,
            detail="KIS API 키가 설정되지 않았습니다. .env에 KIS_APP_KEY, KIS_APP_SECRET를 설정해주세요.",
        )

    url = f"{BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    try:
        res = requests.post(url, headers={"content-type": "application/json"}, data=json.dumps(body), timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"KIS 토큰 발급 요청 실패: {e}")

    if res.status_code != 200:
        raise HTTPException(status_code=502, detail=f"KIS 토큰 발급 실패: {res.text}")

    _access_token = res.json()["access_token"]
    return _access_token


def _get_overseas_tr_id(token: str, app_key: str, app_secret: str) -> str:
    """해외주식 주야간원장 구분 조회 (JTTT3010R).

    야간 원장(PSBL_YN=Y)이면 JTTT3012R, 주간이면 TTTS3012R 반환.
    조회 실패 시 기본값 TTTS3012R.
    """
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/dayornight"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "JTTT3010R",
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            psbl = res.json().get("output", {}).get("PSBL_YN", "N")
            return "JTTT3012R" if psbl == "Y" else "TTTS3012R"
    except Exception:
        pass
    return "TTTS3012R"


def _fetch_overseas_rates_and_summary(token: str, app_key: str, app_secret: str, acnt_no: str, acnt_prdt_cd: str) -> tuple:
    """CTRP6504R(해외주식 체결기준현재잔고)로 통화별 기준환율 + KRW 합계 조회.

    Returns:
        (exchange_rates, stock_eval_krw, deposit_krw)
        exchange_rates: {"USD": 1442.0, "HKD": 184.5, ...}
        stock_eval_krw: 해외주식 평가금액 합계 (원화)
        deposit_krw:    외화 예수금 합계 (원화환산)
    """
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-present-balance"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "CTRP6504R",
        "custtype": "P",
    }
    params = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "WCRC_FRCR_DVSN_CD": "01",  # 원화 기준
        "NATN_CD": "000",            # 전체 국가
        "TR_MKET_CD": "00",
        "INQR_DVSN_CD": "00",
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code != 200 or res.json().get("rt_cd") != "0":
            return {}, 0, 0
        data = res.json()

        # output2: 통화별 기준환율 (frst_bltn_exrt)
        exchange_rates: dict[str, float] = {}
        for item in data.get("output2", []):
            crcy = item.get("crcy_cd", "")
            exrt = float(item.get("frst_bltn_exrt", 0) or 0)
            if crcy and exrt > 0:
                exchange_rates[crcy] = exrt

        # output3: 해외주식 평가금액 합계(KRW) + 외화 예수금 합계(KRW 환산)
        output3 = data.get("output3", {})
        stock_eval_krw = int(float(output3.get("evlu_amt_smtl", 0) or 0))
        deposit_krw = int(float(output3.get("frcr_evlu_tota", 0) or 0))

        return exchange_rates, stock_eval_krw, deposit_krw
    except Exception:
        return {}, 0, 0


def _fetch_overseas_balance(token: str, app_key: str, app_secret: str, acnt_no: str, acnt_prdt_cd: str) -> dict:
    """해외주식 잔고 조회 (전 거래소 순회).

    1단계: CTRP6504R로 통화별 기준환율 + KRW 합계 확보
    2단계: TTTS3012R로 종목별 외화 잔고 조회 → 기준환율 적용해 profit_loss_krw 산출
    실패한 거래소는 조용히 건너뜀.
    """
    # ── 1단계: 기준환율 + KRW 합계 ───────────────────────────────────────────
    exchange_rates, stock_eval_krw, deposit_krw = _fetch_overseas_rates_and_summary(
        token, app_key, app_secret, acnt_no, acnt_prdt_cd
    )

    # ── 2단계: 종목별 외화 잔고 (TTTS3012R) ──────────────────────────────────
    tr_id = _get_overseas_tr_id(token, app_key, app_secret)
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }

    stocks = []
    for excg_cd, crcy_cd in _OVERSEAS_EXCHANGES:
        fk200, nk200 = "", ""
        while True:
            params = {
                "CANO": acnt_no,
                "ACNT_PRDT_CD": acnt_prdt_cd,
                "OVRS_EXCG_CD": excg_cd,
                "TR_CRCY_CD": crcy_cd,
                "CTX_AREA_FK200": fk200,
                "CTX_AREA_NK200": nk200,
            }
            try:
                res = requests.get(url, headers=headers, params=params, timeout=10)
                if res.status_code != 200:
                    break
                data = res.json()
                if data.get("rt_cd") != "0":
                    break

                for item in data.get("output1", []):
                    try:
                        if int(item.get("ovrs_cblc_qty", 0) or 0) <= 0:
                            continue
                        crcy = item.get("tr_crcy_cd", crcy_cd)
                        exrt = exchange_rates.get(crcy, 0)
                        frcr_pfls = float(item.get("frcr_evlu_pfls_amt", 0) or 0)
                        profit_loss_krw = str(round(frcr_pfls * exrt)) if exrt > 0 else ""
                        eval_amount_raw = float(item.get("ovrs_stck_evlu_amt", 0) or 0)
                        eval_amount_krw = str(round(eval_amount_raw * exrt)) if exrt > 0 else ""
                        stocks.append({
                            "name": item.get("ovrs_item_name", ""),
                            "code": item.get("ovrs_pdno", ""),
                            "exchange": item.get("ovrs_excg_cd", excg_cd),
                            "currency": crcy,
                            "quantity": item.get("ovrs_cblc_qty", "0"),
                            "avg_price": item.get("pchs_avg_pric", "0"),
                            "current_price": item.get("now_pric2", "0"),
                            "profit_loss": item.get("frcr_evlu_pfls_amt", "0"),
                            "profit_loss_krw": profit_loss_krw,
                            "profit_rate": item.get("evlu_pfls_rt", "0"),
                            "eval_amount": item.get("ovrs_stck_evlu_amt", "0"),
                            "eval_amount_krw": eval_amount_krw,
                        })
                    except Exception:
                        continue

                tr_cont = res.headers.get("tr_cont", "")
                if tr_cont == "M":
                    fk200 = data.get("ctx_area_fk200", "")
                    nk200 = data.get("ctx_area_nk200", "")
                else:
                    break
            except Exception:
                break

    return {
        "stocks": stocks,
        "stock_eval_krw": stock_eval_krw,
        "deposit_krw": deposit_krw,
    }


def _fetch_futures_balance(token: str, app_key: str, app_secret: str, acnt_no: str, acnt_prdt_cd: str) -> list:
    """국내선물옵션 잔고 조회 (CTFO6118R)."""
    url = f"{BASE_URL}/uapi/domestic-futureoption/v1/trading/inquire-balance"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "CTFO6118R",
        "custtype": "P",
    }
    params = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "MGNA_DVSN_CD": "1",
        "EXCC_YN": "N",
        "PDNO": "",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": "",
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code != 200:
            return []
        data = res.json()
        if data.get("rt_cd") != "0":
            return []
        positions = []
        for item in data.get("output1", []):
            try:
                qty = abs(int(item.get("thdt_nccs_qty", "0") or "0"))
                if qty > 0:
                    positions.append({
                        "name": item.get("prdt_name", ""),
                        "code": item.get("pdno", ""),
                        "trade_type": item.get("trad_dvsn_name", ""),
                        "quantity": item.get("thdt_nccs_qty", "0"),
                        "avg_price": item.get("pchs_avg_pric", "0"),
                        "current_price": item.get("prpr", "0"),
                        "profit_loss": item.get("evlu_pfls_amt", "0"),
                        "profit_rate": item.get("evlu_pfls_rt", "0"),
                        "eval_amount": item.get("evlu_amt", "0"),
                    })
            except Exception:
                continue
        return positions
    except Exception:
        return []


@router.get("/balance")
def get_balance():
    """주식 잔고 조회 (국내주식 + 해외주식 + 국내선물옵션).

    KIS API 키가 없으면 503을 반환한다.
    해외주식/선물옵션 조회 실패 시 해당 목록을 빈 배열로 반환 (국내주식은 정상 반환).
    """
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    acnt_no = os.getenv("KIS_ACNT_NO")
    acnt_prdt_cd = os.getenv("KIS_ACNT_PRDT_CD")

    if not all([app_key, app_secret, acnt_no, acnt_prdt_cd]):
        missing = [
            name for name, val in [
                ("KIS_APP_KEY", app_key),
                ("KIS_APP_SECRET", app_secret),
                ("KIS_ACNT_NO", acnt_no),
                ("KIS_ACNT_PRDT_CD", acnt_prdt_cd),
            ] if not val
        ]
        raise HTTPException(
            status_code=503,
            detail=f"KIS API 키가 설정되지 않았습니다. 누락된 환경변수: {', '.join(missing)}",
        )

    token = _get_access_token()

    # 국내주식 잔고
    path = "/uapi/domestic-stock/v1/trading/inquire-balance"
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "TTTC8434R",
        "custtype": "P",
    }
    params = {
        "CANO": acnt_no,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "N",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"KIS API 호출 실패: {e}")

    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail="잔고 조회 실패")

    data = res.json()
    if data.get("rt_cd") != "0":
        # 토큰 만료일 수 있으므로 캐시 초기화
        global _access_token
        _access_token = None
        raise HTTPException(status_code=400, detail=f"API 오류: {data.get('msg1')}")

    stocks = []
    for item in data.get("output1", []):
        try:
            if int(item.get("hldg_qty", 0)) > 0:
                stocks.append({
                    "name": item.get("prdt_name"),
                    "code": item.get("pdno"),
                    "quantity": item.get("hldg_qty"),
                    "current_price": item.get("prpr"),
                    "profit_loss": item.get("evlu_pfls_amt"),
                    "profit_rate": item.get("evlu_pfls_rt"),
                    "eval_amount": item.get("evlu_amt"),
                    "avg_price": item.get("pchs_avg_pric"),
                })
        except Exception:
            continue

    total_data = data.get("output2", [{}])[0]
    domestic_stock_eval = int(total_data.get("scts_evlu_amt", 0) or 0)
    domestic_deposit = int(total_data.get("dnca_tot_amt", 0) or 0)
    domestic_total = int(total_data.get("tot_evlu_amt", 0) or 0)

    # 해외주식 잔고 (오류 발생 시 빈 결과)
    try:
        overseas_result = _fetch_overseas_balance(token, app_key, app_secret, acnt_no, acnt_prdt_cd)
        overseas_list = overseas_result["stocks"]
        stock_eval_overseas_krw = overseas_result["stock_eval_krw"]
        deposit_overseas_krw = overseas_result["deposit_krw"]
    except Exception:
        overseas_list = []
        stock_eval_overseas_krw = 0
        deposit_overseas_krw = 0

    # 국내선물옵션 잔고 (오류 발생 시 빈 목록)
    try:
        futures_list = _fetch_futures_balance(token, app_key, app_secret, acnt_no, acnt_prdt_cd)
    except Exception:
        futures_list = []

    # 국내주식 시가총액·PER·PBR·ROE 보강 (캐시 기반, 실패 시 None)
    for s in stocks:
        try:
            m = fetch_market_metrics(s["code"])
            s["exchange"] = m.get("market_type")
            s["mktcap"] = m.get("mktcap")
            s["per"] = m.get("per")
            s["pbr"] = m.get("pbr")
            s["roe"] = m.get("roe")
        except Exception:
            s["exchange"] = s["mktcap"] = s["per"] = s["pbr"] = s["roe"] = None

    # 해외주식 시가총액·PER·PBR·ROE 보강 (yfinance, 캐시 기반, 실패 시 None)
    for s in overseas_list:
        try:
            d = fetch_detail_yf(s["code"])
            if d:
                s["mktcap"] = d.get("mktcap")
                s["per"] = d.get("per")
                s["pbr"] = d.get("pbr")
                s["roe"] = d.get("roe")
            else:
                s["mktcap"] = s["per"] = s["pbr"] = s["roe"] = None
        except Exception:
            s["mktcap"] = s["per"] = s["pbr"] = s["roe"] = None

    return {
        # 합산 총계
        "total_evaluation": str(domestic_total + stock_eval_overseas_krw + deposit_overseas_krw),
        # 주식 평가금액
        "stock_eval": str(domestic_stock_eval + stock_eval_overseas_krw),
        "stock_eval_domestic": str(domestic_stock_eval),
        "stock_eval_overseas_krw": str(stock_eval_overseas_krw),
        # 예수금
        "deposit": str(domestic_deposit + deposit_overseas_krw),
        "deposit_domestic": str(domestic_deposit),
        "deposit_overseas_krw": str(deposit_overseas_krw),
        # 종목 목록
        "stock_list": stocks,
        "overseas_list": overseas_list,
        "futures_list": futures_list,
    }