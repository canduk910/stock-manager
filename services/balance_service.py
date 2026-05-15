"""잔고 서비스 — 멀티 계좌 합산 + 단일 계좌 조회 + 병렬 fetch.

R4 (KIS 멀티 계좌, 2026-05-15):
- `fetch_single_account_balance(user_id, account_label)` — 한 계좌 KIS 조회.
- `aggregate_balance_accounts(list[account_response])` — 종목 단위 합산 + 메타.
- `fetch_aggregated_balance(user_id, account_label=None)` — 멀티 진입점.
    - account_label=None → 사용자의 모든 등록 계좌 병렬 조회 + 합산.
    - account_label='주식' → 단독 조회 결과를 합산 함수에 1개 입력해 동일 응답 shape 반환.
- 병렬 호출 Semaphore cap=6 (REQ-BALANCE-03), 부분 실패 시 partial_failure 메타 부착.
- 환율은 첫 응답 환율 단일 (REQ-BALANCE-02).
- FNO 합산 안 함, account_label 부착 (REQ-BALANCE-04).

기존 라우터(`routers/balance.py`)의 KIS 조회 헬퍼는 본 모듈로 이전한다.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

from routers._kis_auth import (
    BASE_URL,
    get_access_token,
    get_kis_credentials,
    _get_user_base_url,
)
from services.exceptions import ExternalAPIError, ServiceError

# ──────────────────────────────────────────────────────────────────────────────
# KIS 조회 헬퍼 — routers/balance.py 에서 이전.
# ──────────────────────────────────────────────────────────────────────────────

_OVERSEAS_EXCHANGES = [
    ("NASD", "USD"),
    ("SEHK", "HKD"),
    ("SHAA", "CNY"),
    ("SZAA", "CNY"),
    ("TKSE", "JPY"),
    ("HASE", "VND"),
    ("VNSE", "VND"),
]


def _get_overseas_tr_id(base_url: str, token: str, app_key: str, app_secret: str) -> str:
    url = f"{base_url}/uapi/overseas-stock/v1/trading/dayornight"
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


def _fetch_overseas_rates_and_summary(
    base_url: str, token: str, app_key: str, app_secret: str, acnt_no: str, acnt_prdt_cd: str,
) -> tuple:
    url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-present-balance"
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
        "WCRC_FRCR_DVSN_CD": "01",
        "NATN_CD": "000",
        "TR_MKET_CD": "00",
        "INQR_DVSN_CD": "00",
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code != 200 or res.json().get("rt_cd") != "0":
            return {}, 0, 0
        data = res.json()
        exchange_rates: dict[str, float] = {}
        for item in data.get("output2", []):
            crcy = item.get("crcy_cd", "")
            exrt = float(item.get("frst_bltn_exrt", 0) or 0)
            if crcy and exrt > 0:
                exchange_rates[crcy] = exrt
        output3 = data.get("output3", {})
        stock_eval_krw = int(float(output3.get("evlu_amt_smtl", 0) or 0))
        deposit_krw = int(float(output3.get("frcr_evlu_tota", 0) or 0))
        return exchange_rates, stock_eval_krw, deposit_krw
    except Exception:
        return {}, 0, 0


def _fetch_overseas_balance(
    base_url: str, token: str, app_key: str, app_secret: str, acnt_no: str, acnt_prdt_cd: str,
) -> dict:
    exchange_rates, stock_eval_krw, deposit_krw = _fetch_overseas_rates_and_summary(
        base_url, token, app_key, app_secret, acnt_no, acnt_prdt_cd,
    )
    tr_id = _get_overseas_tr_id(base_url, token, app_key, app_secret)
    url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
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
        "exchange_rates": exchange_rates,
    }


def _fetch_futures_balance(
    base_url: str, token: str, app_key: str, app_secret: str, acnt_no: str, acnt_prdt_cd: str,
) -> list:
    url = f"{base_url}/uapi/domestic-futureoption/v1/trading/inquire-balance"
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
        "MGNA_DVSN": "01",
        "EXCC_STAT_CD": "1",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": "",
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code != 200:
            logger.warning("FNO 잔고 조회 실패 (HTTP %s): %s", res.status_code, res.text[:200])
            return []
        data = res.json()
        if data.get("rt_cd") != "0":
            logger.warning("FNO 잔고 API 오류 (rt_cd=%s, msg=%s): %s",
                           data.get("rt_cd"), data.get("msg_cd"), data.get("msg1", "unknown"))
            return []
        positions = []
        for item in data.get("output1", []):
            try:
                qty = abs(int(item.get("cblc_qty", "0") or "0"))
                if qty > 0:
                    pchs_amt = float(item.get("pchs_amt", "0") or "0")
                    pfls_amt = float(item.get("evlu_pfls_amt", "0") or "0")
                    profit_rate = round(pfls_amt / pchs_amt * 100, 2) if pchs_amt else 0
                    positions.append({
                        "name": item.get("prdt_name", ""),
                        "code": item.get("shtn_pdno", "") or item.get("pdno", ""),
                        "trade_type": item.get("sll_buy_dvsn_name", ""),
                        "quantity": str(qty),
                        "avg_price": item.get("ccld_avg_unpr1", "0"),
                        "current_price": item.get("idx_clpr", "0"),
                        "profit_loss": item.get("evlu_pfls_amt", "0"),
                        "profit_rate": str(profit_rate),
                        "eval_amount": item.get("evlu_amt", "0"),
                    })
            except Exception:
                continue
        return positions
    except Exception as e:
        logger.warning("FNO 잔고 조회 예외: %s", e)
        return []


def _fetch_domestic_balance(
    base_url: str, token: str, app_key: str, app_secret: str, acnt_no: str, acnt_prdt_cd: str,
) -> tuple:
    """국내주식 잔고 (TTTC8434R). (stocks, eval_amt, deposit, total) 반환."""
    url = f"{base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
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
        raise ExternalAPIError(f"KIS API 호출 실패: {e}")
    if res.status_code != 200:
        raise ExternalAPIError(f"잔고 조회 실패 (HTTP {res.status_code})")
    data = res.json()
    if data.get("rt_cd") != "0":
        raise ServiceError(f"API 오류: {data.get('msg1')}")

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
    eval_amt = int(total_data.get("scts_evlu_amt", 0) or 0)
    deposit = int(total_data.get("dnca_tot_amt", 0) or 0)
    total = int(total_data.get("tot_evlu_amt", 0) or 0)
    return stocks, eval_amt, deposit, total


# ──────────────────────────────────────────────────────────────────────────────
# 단일 계좌 조회 (KIS API 4 호출 — KR + 환율+해외 + FNO)
# ──────────────────────────────────────────────────────────────────────────────


def fetch_single_account_balance(
    user_id: Optional[int],
    account_label: Optional[str],
) -> dict:
    """단일 계좌의 KIS 잔고 + 보강 메트릭. 부분 실패는 partial_failure 리스트.

    응답 shape:
    {
      "label": str,
      "stock_list": [...], "overseas_list": [...], "futures_list": [...],
      "stock_eval_domestic": str, "stock_eval_overseas_krw": str,
      "deposit_domestic": str, "deposit_overseas_krw": str,
      "fno_enabled": bool,
      "exchange_rates": {"USD": 1400.0, ...},
      "partial_failure": [...]
    }
    """
    from stock.market import fetch_market_metrics
    from stock.yf_client import fetch_detail_yf

    app_key, app_secret, acnt_no, acnt_prdt_cd_stk, acnt_prdt_cd_fno = get_kis_credentials(
        user_id, account_label,
    )
    base_url = _get_user_base_url(user_id, account_label)
    token = get_access_token(user_id, account_label)
    partial_failure: list[str] = []
    label_display = account_label or "기본"

    # 1) 국내주식 (필수 — 실패 시 ExternalAPIError 그대로 raise)
    try:
        stocks, domestic_eval, domestic_deposit, _ = _fetch_domestic_balance(
            base_url, token, app_key, app_secret, acnt_no, acnt_prdt_cd_stk,
        )
    except Exception as e:
        logger.warning("[%s] 국내잔고 실패: %s", label_display, e)
        partial_failure.append(f"{label_display} KR 잔고 조회 실패")
        stocks, domestic_eval, domestic_deposit = [], 0, 0

    # 2) 해외주식 + 환율
    try:
        overseas = _fetch_overseas_balance(
            base_url, token, app_key, app_secret, acnt_no, acnt_prdt_cd_stk,
        )
        overseas_list = overseas["stocks"]
        overseas_eval_krw = overseas["stock_eval_krw"]
        overseas_deposit_krw = overseas["deposit_krw"]
        exchange_rates = overseas.get("exchange_rates", {})
    except Exception as e:
        logger.warning("[%s] 해외잔고 실패: %s", label_display, e)
        partial_failure.append(f"{label_display} US 잔고 조회 실패")
        overseas_list, overseas_eval_krw, overseas_deposit_krw, exchange_rates = [], 0, 0, {}

    # 3) FNO (옵셔널 — acnt_prdt_cd_fno 없으면 스킵)
    futures_list = []
    if acnt_prdt_cd_fno:
        try:
            futures_list = _fetch_futures_balance(
                base_url, token, app_key, app_secret, acnt_no, acnt_prdt_cd_fno,
            )
        except Exception as e:
            logger.warning("[%s] FNO 잔고 실패: %s", label_display, e)
            partial_failure.append(f"{label_display} FNO 잔고 조회 실패")
            futures_list = []

    # 4) 메트릭 보강 (실패 시 None — partial_failure 누적 안 함)
    for s in stocks:
        try:
            m = fetch_market_metrics(s["code"])
            s["exchange"] = m.get("market_type")
            s["mktcap"] = m.get("mktcap")
            s["per"] = m.get("per")
            s["pbr"] = m.get("pbr")
            s["roe"] = m.get("roe")
            s["dividend_yield"] = m.get("dividend_yield")
        except Exception:
            s["exchange"] = s["mktcap"] = s["per"] = s["pbr"] = s["roe"] = s["dividend_yield"] = None
        s["account_label"] = label_display

    for s in overseas_list:
        try:
            d = fetch_detail_yf(s["code"])
            if d:
                s["mktcap"] = d.get("mktcap")
                s["per"] = d.get("per")
                s["pbr"] = d.get("pbr")
                s["roe"] = d.get("roe")
                s["dividend_yield"] = d.get("dividend_yield")
            else:
                s["mktcap"] = s["per"] = s["pbr"] = s["roe"] = s["dividend_yield"] = None
        except Exception:
            s["mktcap"] = s["per"] = s["pbr"] = s["roe"] = s["dividend_yield"] = None
        s["account_label"] = label_display

    for f in futures_list:
        f["account_label"] = label_display

    return {
        "label": label_display,
        "stock_list": stocks,
        "overseas_list": overseas_list,
        "futures_list": futures_list,
        "stock_eval_domestic": str(domestic_eval),
        "stock_eval_overseas_krw": str(overseas_eval_krw),
        "deposit_domestic": str(domestic_deposit),
        "deposit_overseas_krw": str(overseas_deposit_krw),
        "fno_enabled": bool(acnt_prdt_cd_fno),
        "exchange_rates": exchange_rates,
        "partial_failure": partial_failure,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 합산 함수 (REQ-BALANCE-01/02/04)
# ──────────────────────────────────────────────────────────────────────────────


def _sum_weighted(rows: list[dict], qty_key: str = "quantity",
                  avg_key: str = "avg_price", eval_key: str = "eval_amount",
                  pl_key: str = "profit_loss") -> dict:
    """rows 합산 (1종목). qty 합산 + 가중평균 단가 + 합계 eval/pl."""
    total_qty = 0.0
    cost = 0.0
    total_eval = 0.0
    total_pl = 0.0
    for r in rows:
        try:
            q = float(r.get(qty_key) or 0)
        except (TypeError, ValueError):
            q = 0.0
        try:
            a = float(r.get(avg_key) or 0)
        except (TypeError, ValueError):
            a = 0.0
        try:
            e = float(r.get(eval_key) or 0)
        except (TypeError, ValueError):
            e = 0.0
        try:
            p = float(r.get(pl_key) or 0)
        except (TypeError, ValueError):
            p = 0.0
        total_qty += q
        cost += q * a
        total_eval += e
        total_pl += p
    avg = (cost / total_qty) if total_qty else 0.0
    rate = (total_pl / (total_eval - total_pl) * 100) if (total_eval - total_pl) else 0.0
    return {
        "quantity": total_qty,
        "avg_price": avg,
        "eval_amount": total_eval,
        "profit_loss": total_pl,
        "profit_rate": rate,
    }


def _aggregate_stock_list(per_account: list[dict], kind: str) -> list[dict]:
    """종목 단위 합산. kind='KR' 또는 'US'.

    KR: 키 = code
    US: 키 = (code, exchange)
    """
    if kind == "KR":
        get_key = lambda r: r["code"]
    else:
        get_key = lambda r: (r["code"], r.get("exchange", ""))

    groups: dict = {}
    for acc in per_account:
        label = acc.get("label", "기본")
        rows = acc.get("stock_list" if kind == "KR" else "overseas_list", []) or []
        for r in rows:
            key = get_key(r)
            groups.setdefault(key, []).append((label, r))

    result = []
    for key, items in groups.items():
        # 메타: 첫 row 의 기본 정보(name/exchange/currency 등) 유지
        first = items[0][1]
        labels = sorted({lbl for lbl, _ in items})
        rows = [r for _, r in items]
        agg = _sum_weighted(rows)
        merged = dict(first)  # name/exchange/메트릭 보존 (첫 row)
        # 합산 값으로 덮어쓰기
        merged["quantity"] = str(int(agg["quantity"]))
        merged["avg_price"] = str(round(agg["avg_price"], 2))
        merged["eval_amount"] = str(round(agg["eval_amount"], 2))
        merged["profit_loss"] = str(round(agg["profit_loss"], 2))
        merged["profit_rate"] = str(round(agg["profit_rate"], 2))
        # eval_amount_krw 보존 (US만)
        if kind == "US":
            # eval_amount_krw, profit_loss_krw 단순 합 (환율 단일 가정 — REQ-BALANCE-02)
            try:
                merged["eval_amount_krw"] = str(int(sum(
                    float(r.get("eval_amount_krw") or 0) for r in rows
                )))
                merged["profit_loss_krw"] = str(int(sum(
                    float(r.get("profit_loss_krw") or 0) for r in rows
                )))
            except Exception:
                pass
        merged["accounts"] = labels
        # 단일 라벨 위반 시 account_label 도 유지, 아니면 None
        merged["account_label"] = labels[0] if len(labels) == 1 else None
        result.append(merged)
    return result


def aggregate_balance_accounts(per_account: list[dict]) -> dict:
    """N계좌 응답을 통합 잔고 응답으로 합산.

    Args:
        per_account: [single_account_response, ...]

    Returns:
        통합 응답 dict — `/api/balance` 의 기존 shape 유지 + accounts/partial_failure 메타.
    """
    if not per_account:
        return {
            "total_evaluation": "0",
            "stock_eval": "0",
            "stock_eval_domestic": "0",
            "stock_eval_overseas_krw": "0",
            "deposit": "0",
            "deposit_domestic": "0",
            "deposit_overseas_krw": "0",
            "stock_list": [],
            "overseas_list": [],
            "futures_list": [],
            "fno_enabled": False,
            "accounts": [],
            "partial_failure": [],
        }

    domestic_eval = sum(int(float(a.get("stock_eval_domestic") or 0)) for a in per_account)
    overseas_eval_krw = sum(int(float(a.get("stock_eval_overseas_krw") or 0)) for a in per_account)
    domestic_deposit = sum(int(float(a.get("deposit_domestic") or 0)) for a in per_account)
    overseas_deposit_krw = sum(int(float(a.get("deposit_overseas_krw") or 0)) for a in per_account)
    fno_enabled = any(a.get("fno_enabled") for a in per_account)

    stock_list = _aggregate_stock_list(per_account, "KR")
    overseas_list = _aggregate_stock_list(per_account, "US")
    # FNO 는 합산 안 함 — 그대로 concat (REQ-BALANCE-04)
    futures_list: list = []
    for a in per_account:
        futures_list.extend(a.get("futures_list") or [])

    accounts_meta = []
    partial_failures: list[str] = []
    for a in per_account:
        # acnt_no_masked 는 단일 계좌 응답에 포함되지 않을 수 있으므로 옵셔널 처리.
        accounts_meta.append({
            "label": a.get("label", "기본"),
            "is_default": a.get("is_default", False),
            "acnt_no_masked": a.get("acnt_no_masked", ""),
            "fno_enabled": a.get("fno_enabled", False),
        })
        for msg in (a.get("partial_failure") or []):
            partial_failures.append(msg)

    stock_eval = domestic_eval + overseas_eval_krw
    deposit = domestic_deposit + overseas_deposit_krw
    total_evaluation = domestic_eval + overseas_eval_krw + overseas_deposit_krw

    return {
        "total_evaluation": str(total_evaluation),
        "stock_eval": str(stock_eval),
        "stock_eval_domestic": str(domestic_eval),
        "stock_eval_overseas_krw": str(overseas_eval_krw),
        "deposit": str(deposit),
        "deposit_domestic": str(domestic_deposit),
        "deposit_overseas_krw": str(overseas_deposit_krw),
        "stock_list": stock_list,
        "overseas_list": overseas_list,
        "futures_list": futures_list,
        "fno_enabled": fno_enabled,
        "accounts": accounts_meta,
        "partial_failure": partial_failures,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 멀티 계좌 진입점 (REQ-API-02, REQ-BALANCE-03)
# ──────────────────────────────────────────────────────────────────────────────


# 병렬 호출 cap (REQ-BALANCE-03): N계좌 동시 KIS 조회 보호.
# 2 계좌 × 3 시장 = 6 동시 호출 가정.
_PARALLEL_CAP = 6


def _user_account_labels(user_id: int) -> list[dict]:
    from db.session import get_session
    from db.repositories.user_kis_repo import UserKisRepository
    with get_session() as db:
        return UserKisRepository(db).list_accounts_masked(user_id)


async def _fetch_one_async(sem: asyncio.Semaphore, user_id: int, label: str, masked_meta: dict) -> dict:
    async with sem:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, fetch_single_account_balance, user_id, label,
            )
            # 메타 부착 (탭 렌더링용)
            result["is_default"] = masked_meta.get("is_default", False)
            result["acnt_no_masked"] = masked_meta.get("acnt_no_masked", "")
            return result
        except Exception as e:
            logger.warning("[%s] 잔고 조회 전체 실패: %s", label, e)
            return {
                "label": label,
                "is_default": masked_meta.get("is_default", False),
                "acnt_no_masked": masked_meta.get("acnt_no_masked", ""),
                "stock_list": [], "overseas_list": [], "futures_list": [],
                "stock_eval_domestic": "0", "stock_eval_overseas_krw": "0",
                "deposit_domestic": "0", "deposit_overseas_krw": "0",
                "fno_enabled": masked_meta.get("fno_enabled", False),
                "exchange_rates": {},
                "partial_failure": [f"{label} 전체 조회 실패: {e}"],
            }


def fetch_aggregated_balance(
    user_id: Optional[int],
    account_label: Optional[str] = None,
) -> dict:
    """멀티 계좌 진입점.

    - account_label=None → 사용자의 모든 등록 계좌 병렬 조회 후 합산.
    - account_label='주식' → 단독 조회 후 동일 합산 shape 반환.
    - user_id=None → 운영자 .env 키 1개 호출 (백워드 호환).
    - 등록 0개 + account_label=None → 200 + 빈 응답 (예외 raise 금지).
    """
    # 운영자 키 경로 (백워드 호환)
    if user_id is None:
        single = fetch_single_account_balance(None, None)
        # accounts 메타 1개 추가 후 합산
        single.setdefault("label", "기본")
        return aggregate_balance_accounts([single])

    # 등록 계좌 조회
    accounts_meta = _user_account_labels(user_id)
    if account_label is not None:
        # 단독 모드
        meta = next((a for a in accounts_meta if a["label"] == account_label), None)
        if meta is None:
            from services.exceptions import NotFoundError
            raise NotFoundError(f"라벨 '{account_label}' 의 계좌를 찾을 수 없습니다.")
        single = fetch_single_account_balance(user_id, account_label)
        single["is_default"] = meta.get("is_default", False)
        single["acnt_no_masked"] = meta.get("acnt_no_masked", "")
        return aggregate_balance_accounts([single])

    # 0계좌 → 빈 응답 (예외 raise 금지 — REQ-MIGRATION-01)
    if not accounts_meta:
        return aggregate_balance_accounts([])

    # 합산 모드 — 병렬 fetch
    async def run_all():
        sem = asyncio.Semaphore(_PARALLEL_CAP)
        return await asyncio.gather(*[
            _fetch_one_async(sem, user_id, m["label"], m) for m in accounts_meta
        ])

    per_account = asyncio.run(run_all())
    return aggregate_balance_accounts(per_account)
