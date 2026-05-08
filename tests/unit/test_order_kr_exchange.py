"""R_2 (KRX+NXT 통합시세): order_kr.py 신 TR_ID + EXCG_ID_DVSN_CD 단위 테스트."""

from unittest.mock import MagicMock, patch

import pytest

from services import order_kr
from services.exceptions import ServiceError


# ── _KR_TR_IDS 신 TR_ID 검증 ─────────────────────────────────────────────────


def test_new_tr_ids_match_kis_spec():
    """신 TR_ID 일괄 전환: 매수=TTTC0012U / 매도=TTTC0011U / 정정·취소=TTTC0013U / 미체결=TTTC0084R / 체결=TTTC0081R."""
    assert order_kr._KR_TR_IDS["buy"] == "TTTC0012U"
    assert order_kr._KR_TR_IDS["sell"] == "TTTC0011U"
    assert order_kr._KR_TR_IDS["modify"] == "TTTC0013U"
    assert order_kr._KR_TR_IDS["cancel"] == "TTTC0013U"
    assert order_kr._KR_TR_IDS["open"] == "TTTC0084R"
    assert order_kr._KR_TR_IDS["executions"] == "TTTC0081R"


# ── _validate_ord_dvsn ──────────────────────────────────────────────────────


def test_validate_ord_dvsn_krx_allows_00_01():
    """KRX는 00(지정가)/01(시장가) 등 표준 ORD_DVSN 허용."""
    order_kr._validate_ord_dvsn("KRX", "00")
    order_kr._validate_ord_dvsn("KRX", "01")


def test_validate_ord_dvsn_nxt_disallows_01_market():
    """NXT는 시장가(01) 미지원 — KIS 명세상 NXT 단독은 IOC/FOK 등 제한적."""
    with pytest.raises(ServiceError) as excinfo:
        order_kr._validate_ord_dvsn("NXT", "01")
    assert "NXT" in str(excinfo.value) or "지원" in str(excinfo.value)


def test_validate_ord_dvsn_sor_allows_00_01():
    """SOR은 지정가(00) + 시장가(01) 모두 허용."""
    order_kr._validate_ord_dvsn("SOR", "00")
    order_kr._validate_ord_dvsn("SOR", "01")


def test_validate_ord_dvsn_unknown_exchange_raises():
    """SOR/KRX/NXT 외 거래소는 ServiceError."""
    with pytest.raises(ServiceError):
        order_kr._validate_ord_dvsn("UNKNOWN", "00")


# ── place_domestic_order: EXCG_ID_DVSN_CD 주입 ───────────────────────────────


def _mock_kis_success_response():
    res = MagicMock()
    res.json.return_value = {
        "rt_cd": "0",
        "msg1": "정상",
        "output": {
            "ODNO": "0020551600",
            "KRX_FWDG_ORD_ORGNO": "06010",
        },
    }
    return res


def test_place_order_injects_excg_id_dvsn_cd_sor(monkeypatch):
    """exchange='SOR' 호출 시 body에 EXCG_ID_DVSN_CD='SOR' 주입."""
    captured = {}

    def fake_post(url, headers=None, data=None, **kwargs):
        import json as _json
        captured["body"] = _json.loads(data)
        captured["headers"] = headers
        return _mock_kis_success_response()

    monkeypatch.setattr(order_kr.requests, "post", fake_post)
    monkeypatch.setattr(order_kr, "issue_hashkey", lambda body: "fakehash")

    order_kr.place_domestic_order(
        token="t", app_key="k", app_secret="s",
        acnt_no="50000000", acnt_prdt_cd="01",
        symbol="005930", side="buy", order_type="00",
        price=70000, quantity=10,
        exchange="SOR",
    )
    assert captured["body"]["EXCG_ID_DVSN_CD"] == "SOR"
    # 신 TR_ID
    assert captured["headers"]["tr_id"] == "TTTC0012U"


def test_place_order_injects_excg_id_dvsn_cd_krx(monkeypatch):
    """exchange='KRX' 호출 시 body에 EXCG_ID_DVSN_CD='KRX' 주입."""
    captured = {}

    def fake_post(url, headers=None, data=None, **kwargs):
        import json as _json
        captured["body"] = _json.loads(data)
        captured["headers"] = headers
        return _mock_kis_success_response()

    monkeypatch.setattr(order_kr.requests, "post", fake_post)
    monkeypatch.setattr(order_kr, "issue_hashkey", lambda body: "fakehash")

    order_kr.place_domestic_order(
        token="t", app_key="k", app_secret="s",
        acnt_no="50000000", acnt_prdt_cd="01",
        symbol="005930", side="sell", order_type="00",
        price=70000, quantity=10,
        exchange="KRX",
    )
    assert captured["body"]["EXCG_ID_DVSN_CD"] == "KRX"
    # 매도 신 TR_ID
    assert captured["headers"]["tr_id"] == "TTTC0011U"


def test_place_order_injects_excg_id_dvsn_cd_nxt(monkeypatch):
    """exchange='NXT' 호출 시 body에 EXCG_ID_DVSN_CD='NXT' 주입."""
    captured = {}

    def fake_post(url, headers=None, data=None, **kwargs):
        import json as _json
        captured["body"] = _json.loads(data)
        return _mock_kis_success_response()

    monkeypatch.setattr(order_kr.requests, "post", fake_post)
    monkeypatch.setattr(order_kr, "issue_hashkey", lambda body: "fakehash")

    order_kr.place_domestic_order(
        token="t", app_key="k", app_secret="s",
        acnt_no="50000000", acnt_prdt_cd="01",
        symbol="005930", side="buy", order_type="00",
        price=70000, quantity=10,
        exchange="NXT",
    )
    assert captured["body"]["EXCG_ID_DVSN_CD"] == "NXT"


def test_place_order_default_exchange_is_sor(monkeypatch):
    """exchange 미지정 시 기본 'SOR' 적용 (사용자 결정 — SOR 기본)."""
    captured = {}

    def fake_post(url, headers=None, data=None, **kwargs):
        import json as _json
        captured["body"] = _json.loads(data)
        return _mock_kis_success_response()

    monkeypatch.setattr(order_kr.requests, "post", fake_post)
    monkeypatch.setattr(order_kr, "issue_hashkey", lambda body: "fakehash")

    order_kr.place_domestic_order(
        token="t", app_key="k", app_secret="s",
        acnt_no="50000000", acnt_prdt_cd="01",
        symbol="005930", side="buy", order_type="00",
        price=70000, quantity=10,
    )
    assert captured["body"]["EXCG_ID_DVSN_CD"] == "SOR"


# ── modify/cancel: 신 TR_ID + EXCG_ID_DVSN_CD ────────────────────────────────


def test_modify_uses_new_tr_id_and_exchange(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, data=None, **kwargs):
        import json as _json
        captured["body"] = _json.loads(data)
        captured["headers"] = headers
        return _mock_kis_success_response()

    monkeypatch.setattr(order_kr.requests, "post", fake_post)
    monkeypatch.setattr(order_kr, "issue_hashkey", lambda body: "fakehash")

    order_kr.modify_domestic_order(
        token="t", app_key="k", app_secret="s",
        acnt_no="50000000", acnt_prdt_cd="01",
        order_no="0020551600", org_no="06010",
        order_type="00", price=70500, quantity=10, total=True,
        exchange="NXT",
    )
    # 신 정정 TR_ID
    assert captured["headers"]["tr_id"] == "TTTC0013U"
    assert captured["body"]["EXCG_ID_DVSN_CD"] == "NXT"


def test_cancel_uses_new_tr_id_and_exchange(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, data=None, **kwargs):
        import json as _json
        captured["body"] = _json.loads(data)
        captured["headers"] = headers
        return _mock_kis_success_response()

    monkeypatch.setattr(order_kr.requests, "post", fake_post)
    monkeypatch.setattr(order_kr, "issue_hashkey", lambda body: "fakehash")

    order_kr.cancel_domestic_order(
        token="t", app_key="k", app_secret="s",
        acnt_no="50000000", acnt_prdt_cd="01",
        order_no="0020551600", org_no="06010",
        order_type="00", quantity=10, total=True,
        exchange="SOR",
    )
    assert captured["headers"]["tr_id"] == "TTTC0013U"
    assert captured["body"]["EXCG_ID_DVSN_CD"] == "SOR"


# ── _normalize_excg_code ─────────────────────────────────────────────────────


def test_normalize_excg_code_known_values():
    """KRX/NXT/SOR 그대로 표준화."""
    assert order_kr._normalize_excg_code({"excg_id_dvsn_cd": "KRX"}) == "KRX"
    assert order_kr._normalize_excg_code({"excg_id_dvsn_cd": "NXT"}) == "NXT"
    assert order_kr._normalize_excg_code({"excg_id_dvsn_cd": "SOR"}) == "SOR"


def test_normalize_excg_code_sor_routed():
    """SOR 라우팅 결과 SOR-KRX/SOR-NXT 처리. 신 응답 필드 흡수."""
    # ord_exg_gb '3' → SOR-KRX, '4' → SOR-NXT
    assert order_kr._normalize_excg_code({"ord_exg_gb": "3"}) == "SOR-KRX"
    assert order_kr._normalize_excg_code({"ord_exg_gb": "4"}) == "SOR-NXT"
    assert order_kr._normalize_excg_code({"ord_exg_gb": "1"}) == "KRX"
    assert order_kr._normalize_excg_code({"ord_exg_gb": "2"}) == "NXT"


def test_normalize_excg_code_missing_falls_back_to_krx():
    """필드 누락 시 'KRX' 폴백 (legacy 응답 호환)."""
    assert order_kr._normalize_excg_code({}) == "KRX"
    assert order_kr._normalize_excg_code({"excg_id_dvsn_cd": ""}) == "KRX"


# ── get_domestic_open_orders: 3거래소 순회 + dedup ──────────────────────────


def test_get_open_orders_calls_three_exchanges(monkeypatch):
    """KRX/NXT/SOR 각각 1회씩 호출 (TTTC0084R + EXCG_ID_DVSN_CD 변경)."""
    calls = []

    def fake_get(url, headers=None, params=None, **kwargs):
        # 호출별 EXCG_ID_DVSN_CD 캡처
        calls.append(params.get("EXCG_ID_DVSN_CD", ""))
        res = MagicMock()
        res.headers = {}
        res.json.return_value = {"rt_cd": "0", "output": []}
        return res

    monkeypatch.setattr(order_kr.requests, "get", fake_get)

    order_kr.get_domestic_open_orders(
        token="t", app_key="k", app_secret="s",
        acnt_no="50000000", acnt_prdt_cd="01",
    )
    # KRX/NXT/SOR 각각 호출됨 (순서 무관)
    assert set(calls) == {"KRX", "NXT", "SOR"}


def test_get_open_orders_dedup_by_order_no_and_exchange(monkeypatch):
    """동일 주문번호+거래소 중복 시 dedup."""
    iter_idx = {"i": 0}
    samples = [
        # KRX 응답
        [{"odno": "1001", "pdno": "005930", "prdt_name": "삼성전자",
          "sll_buy_dvsn_cd": "02", "ord_dvsn_cd": "00",
          "ord_unpr": "70000", "ord_qty": "10", "psbl_qty": "10",
          "tot_ccld_qty": "0", "ord_tmd": "090000",
          "excg_id_dvsn_cd": "KRX"}],
        # NXT 응답 — 동일 (1001, KRX)는 없음, 신규 (1002, NXT)
        [{"odno": "1002", "pdno": "005930", "prdt_name": "삼성전자",
          "sll_buy_dvsn_cd": "02", "ord_dvsn_cd": "00",
          "ord_unpr": "70100", "ord_qty": "5", "psbl_qty": "5",
          "tot_ccld_qty": "0", "ord_tmd": "090100",
          "excg_id_dvsn_cd": "NXT"}],
        # SOR 응답 — KRX와 동일 주문번호(1001)지만 거래소가 'SOR' → 별개로 취급
        [{"odno": "1001", "pdno": "005930", "prdt_name": "삼성전자",
          "sll_buy_dvsn_cd": "02", "ord_dvsn_cd": "00",
          "ord_unpr": "70000", "ord_qty": "10", "psbl_qty": "10",
          "tot_ccld_qty": "0", "ord_tmd": "090000",
          "excg_id_dvsn_cd": "KRX"}],  # SOR 호출 결과 — KRX와 dedup되어야 함
    ]

    def fake_get(url, headers=None, params=None, **kwargs):
        idx = iter_idx["i"]
        iter_idx["i"] += 1
        res = MagicMock()
        res.headers = {}
        res.json.return_value = {"rt_cd": "0", "output": samples[idx % 3]}
        return res

    monkeypatch.setattr(order_kr.requests, "get", fake_get)

    orders = order_kr.get_domestic_open_orders(
        token="t", app_key="k", app_secret="s",
        acnt_no="50000000", acnt_prdt_cd="01",
    )
    # (1001, KRX), (1002, NXT) 2건 (1001+KRX dedup)
    keys = {(o["order_no"], o["exchange"]) for o in orders}
    assert ("1001", "KRX") in keys
    assert ("1002", "NXT") in keys
    assert len(orders) == 2


# ── get_domestic_executions: TTTC0081R + EXCG_ID_DVSN_CD=ALL ─────────────────


def test_get_executions_uses_new_tr_id_and_all_exchange(monkeypatch):
    captured = {"params": None, "headers": None}

    def fake_get(url, headers=None, params=None, **kwargs):
        if captured["params"] is None:
            captured["params"] = dict(params)
            captured["headers"] = headers
        res = MagicMock()
        res.headers = {}
        res.json.return_value = {"rt_cd": "0", "output1": []}
        return res

    monkeypatch.setattr(order_kr.requests, "get", fake_get)

    order_kr.get_domestic_executions(
        token="t", app_key="k", app_secret="s",
        acnt_no="50000000", acnt_prdt_cd="01",
    )
    # 신 TR_ID
    assert captured["headers"]["tr_id"] == "TTTC0081R"
    # EXCG_ID_DVSN_CD=ALL
    assert captured["params"].get("EXCG_ID_DVSN_CD") == "ALL"
