"""잔고 조회 API 라우터 (main.py에서 이동)."""

import json
import os

import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["balance"])

BASE_URL = os.getenv("KIS_BASE_URL") or "https://openapi.koreainvestment.com:9443"

# 인메모리 토큰 캐시 (재시작 시 재발급)
_access_token: str | None = None


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


@router.get("/balance")
def get_balance():
    """주식 잔고 조회 (실전 계좌).

    KIS API 키가 없으면 503을 반환한다.
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

    return {
        "total_evaluation": total_data.get("tot_evlu_amt", "0"),
        "deposit": total_data.get("dnca_tot_amt", "0"),
        "stock_eval": total_data.get("scts_evlu_amt", "0"),
        "stock_list": stocks,
    }
