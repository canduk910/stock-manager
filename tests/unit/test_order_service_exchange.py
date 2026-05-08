"""R_4 (KRX+NXT 통합시세): order_service.place_order exchange 흐름 단위 테스트.

검증 항목:
- KR market 에서 exchange='SOR'/'KRX'/'NXT' 입력 → place_domestic_order 에 exchange 인자 forward
- KR market 에서 exchange 검증 실패 → ServiceError
- 모의투자 환경(_is_simulation=True)에서 SOR/NXT 차단
- KIS 응답에 정밀 거래소(SOR-KRX 등)가 들어오면 PLACED 갱신 시 덮어쓰기
- US/FNO market 에서는 exchange 컬럼이 NULL(=KRX 폴백)로 저장
- modify_order/cancel_order 가 DB orders.exchange 를 조회하여 하위 함수에 전달
"""
from unittest.mock import MagicMock, patch

import pytest

from services import order_service
from services.exceptions import ServiceError


def _patch_kis_creds(mp):
    mp.setattr(
        order_service, "get_kis_credentials",
        lambda: ("AK", "AS", "12345678", "01", "03"),
    )
    mp.setattr(order_service, "get_access_token", lambda: "TKN")


def _patch_order_store(mp, *, get_by_no=None):
    """insert_order/update_order_status/get_order_by_order_no 를 in-memory dict로 대체."""
    inserted = {"calls": [], "rows": {}}
    next_id = {"v": 1}

    def fake_insert(**kwargs):
        oid = next_id["v"]
        next_id["v"] += 1
        row = {"id": oid, **kwargs}
        inserted["calls"].append(kwargs)
        inserted["rows"][oid] = row
        return row

    def fake_update(oid, status, **kwargs):
        row = inserted["rows"].get(oid, {"id": oid}).copy()
        row["status"] = status
        row.update(kwargs)
        inserted["rows"][oid] = row
        return row

    def fake_get_by_no(order_no, market):
        return get_by_no

    mp.setattr(order_service.order_store, "insert_order", fake_insert)
    mp.setattr(order_service.order_store, "update_order_status", fake_update)
    mp.setattr(order_service.order_store, "get_order_by_order_no", fake_get_by_no)
    return inserted


def test_place_order_kr_default_exchange_is_sor(monkeypatch):
    """KR market 에서 exchange 인자 미입력 시 기본값 SOR 로 forward."""
    _patch_kis_creds(monkeypatch)
    monkeypatch.setattr(order_service, "_is_simulation", lambda: False)
    inserted = _patch_order_store(monkeypatch)

    captured = {}

    def fake_place(*a, **kw):
        captured.update(kw)
        return {"order_no": "0020551600", "org_no": "06010", "exchange": "SOR-KRX", "kis_response": "{}"}

    monkeypatch.setattr(order_service, "place_domestic_order", fake_place)

    order_service.place_order(
        symbol="005930", symbol_name="삼성전자", market="KR",
        side="buy", order_type="00", price=70000.0, quantity=10,
    )
    assert captured["exchange"] == "SOR"


def test_place_order_kr_with_explicit_nxt(monkeypatch):
    """KR market 에서 exchange='NXT' 입력 시 place_domestic_order 에 NXT forward."""
    _patch_kis_creds(monkeypatch)
    monkeypatch.setattr(order_service, "_is_simulation", lambda: False)
    inserted = _patch_order_store(monkeypatch)

    captured = {}

    def fake_place(*a, **kw):
        captured.update(kw)
        return {"order_no": "X1", "org_no": "06010", "exchange": "NXT", "kis_response": "{}"}

    monkeypatch.setattr(order_service, "place_domestic_order", fake_place)

    order_service.place_order(
        symbol="005930", symbol_name="삼성전자", market="KR",
        side="buy", order_type="00", price=70000.0, quantity=10,
        exchange="NXT",
    )
    assert captured["exchange"] == "NXT"


def test_place_order_kr_invalid_exchange_raises(monkeypatch):
    """KR market 에서 미지원 exchange 입력 시 ServiceError."""
    _patch_kis_creds(monkeypatch)
    monkeypatch.setattr(order_service, "_is_simulation", lambda: False)
    _patch_order_store(monkeypatch)

    with pytest.raises(ServiceError):
        order_service.place_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="00", price=70000.0, quantity=10,
            exchange="UN",  # 통합은 시세 전용, 주문값 X
        )


def test_place_order_simulation_blocks_sor(monkeypatch):
    """모의투자 환경에서 SOR 선택 시 ServiceError."""
    _patch_kis_creds(monkeypatch)
    monkeypatch.setattr(order_service, "_is_simulation", lambda: True)
    _patch_order_store(monkeypatch)

    with pytest.raises(ServiceError, match="모의투자"):
        order_service.place_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="00", price=70000.0, quantity=10,
            exchange="SOR",
        )


def test_place_order_simulation_blocks_nxt(monkeypatch):
    """모의투자 환경에서 NXT 선택 시 ServiceError."""
    _patch_kis_creds(monkeypatch)
    monkeypatch.setattr(order_service, "_is_simulation", lambda: True)
    _patch_order_store(monkeypatch)

    with pytest.raises(ServiceError, match="모의투자"):
        order_service.place_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="00", price=70000.0, quantity=10,
            exchange="NXT",
        )


def test_place_order_simulation_allows_krx(monkeypatch):
    """모의투자 환경에서 KRX 선택은 허용."""
    _patch_kis_creds(monkeypatch)
    monkeypatch.setattr(order_service, "_is_simulation", lambda: True)
    _patch_order_store(monkeypatch)

    monkeypatch.setattr(
        order_service, "place_domestic_order",
        lambda *a, **kw: {"order_no": "X1", "org_no": "06010", "exchange": "KRX", "kis_response": "{}"},
    )

    result = order_service.place_order(
        symbol="005930", symbol_name="삼성전자", market="KR",
        side="buy", order_type="00", price=70000.0, quantity=10,
        exchange="KRX",
    )
    assert result["status"] == "PLACED"


def test_place_order_pending_records_exchange(monkeypatch):
    """PENDING insert 시 exchange 인자가 함께 기록된다."""
    _patch_kis_creds(monkeypatch)
    monkeypatch.setattr(order_service, "_is_simulation", lambda: False)
    inserted = _patch_order_store(monkeypatch)

    monkeypatch.setattr(
        order_service, "place_domestic_order",
        lambda *a, **kw: {"order_no": "X1", "org_no": "06010", "exchange": "SOR-KRX", "kis_response": "{}"},
    )

    order_service.place_order(
        symbol="005930", symbol_name="삼성전자", market="KR",
        side="buy", order_type="00", price=70000.0, quantity=10,
        exchange="SOR",
    )
    assert inserted["calls"][0]["exchange"] == "SOR"


def test_place_order_placed_overwrites_with_kis_exchange(monkeypatch):
    """PLACED 갱신 시 KIS 응답의 정밀 거래소(SOR-KRX 등)가 입력 SOR을 덮어쓴다."""
    _patch_kis_creds(monkeypatch)
    monkeypatch.setattr(order_service, "_is_simulation", lambda: False)
    inserted = _patch_order_store(monkeypatch)

    monkeypatch.setattr(
        order_service, "place_domestic_order",
        lambda *a, **kw: {"order_no": "X1", "org_no": "06010", "exchange": "SOR-NXT", "kis_response": "{}"},
    )

    result = order_service.place_order(
        symbol="005930", symbol_name="삼성전자", market="KR",
        side="buy", order_type="00", price=70000.0, quantity=10,
        exchange="SOR",
    )
    assert result["exchange"] == "SOR-NXT"


def test_place_order_us_does_not_send_exchange(monkeypatch):
    """US market 에서는 exchange 인자가 PENDING insert 에 None 으로 저장된다."""
    _patch_kis_creds(monkeypatch)
    monkeypatch.setattr(order_service, "_is_simulation", lambda: False)
    inserted = _patch_order_store(monkeypatch)

    monkeypatch.setattr(
        order_service, "place_overseas_order",
        lambda *a, **kw: {"order_no": "USX1", "org_no": "", "kis_response": "{}"},
    )

    order_service.place_order(
        symbol="AAPL", symbol_name="Apple", market="US",
        side="buy", order_type="00", price=180.0, quantity=1,
    )
    assert inserted["calls"][0].get("exchange") is None


def test_modify_order_uses_db_exchange(monkeypatch):
    """modify_order 진입부에서 DB orders.exchange 조회 → modify_domestic_order 에 forward."""
    _patch_kis_creds(monkeypatch)
    _patch_order_store(monkeypatch, get_by_no={"id": 1, "exchange": "NXT"})

    captured = {}

    def fake_modify(*a, **kw):
        captured.update(kw)
        return {"success": True, "data": {}}

    monkeypatch.setattr(order_service, "modify_domestic_order", fake_modify)
    monkeypatch.setattr(order_service, "_sync_local_order_details", lambda *a, **kw: True)

    order_service.modify_order(
        order_no="X1", org_no="06010", market="KR",
        order_type="00", price=70500.0, quantity=10,
    )
    assert captured["exchange"] == "NXT"


def test_modify_order_sor_routed_strips_prefix(monkeypatch):
    """SOR-KRX 라우팅된 주문 정정 시 EXCG 코드는 'KRX'로 환원."""
    _patch_kis_creds(monkeypatch)
    _patch_order_store(monkeypatch, get_by_no={"id": 1, "exchange": "SOR-KRX"})

    captured = {}

    def fake_modify(*a, **kw):
        captured.update(kw)
        return {"success": True, "data": {}}

    monkeypatch.setattr(order_service, "modify_domestic_order", fake_modify)
    monkeypatch.setattr(order_service, "_sync_local_order_details", lambda *a, **kw: True)

    order_service.modify_order(
        order_no="X1", org_no="06010", market="KR",
        order_type="00", price=70500.0, quantity=10,
    )
    assert captured["exchange"] == "KRX"


def test_cancel_order_uses_db_exchange(monkeypatch):
    """cancel_order 진입부에서 DB orders.exchange 조회 → cancel_domestic_order 에 forward."""
    _patch_kis_creds(monkeypatch)
    _patch_order_store(monkeypatch, get_by_no={"id": 1, "exchange": "NXT"})

    captured = {}

    def fake_cancel(*a, **kw):
        captured.update(kw)
        return {"success": True, "data": {}}

    monkeypatch.setattr(order_service, "cancel_domestic_order", fake_cancel)
    monkeypatch.setattr(order_service, "_sync_local_order_status", lambda *a, **kw: True)

    order_service.cancel_order(
        order_no="X1", org_no="06010", market="KR",
        order_type="00", quantity=10, total=True,
    )
    assert captured["exchange"] == "NXT"


def test_cancel_order_no_db_record_falls_back_to_krx(monkeypatch):
    """cancel_order 시 DB 누락 → KRX 폴백."""
    _patch_kis_creds(monkeypatch)
    _patch_order_store(monkeypatch, get_by_no=None)

    captured = {}

    def fake_cancel(*a, **kw):
        captured.update(kw)
        return {"success": True, "data": {}}

    monkeypatch.setattr(order_service, "cancel_domestic_order", fake_cancel)
    monkeypatch.setattr(order_service, "_sync_local_order_status", lambda *a, **kw: True)

    order_service.cancel_order(
        order_no="X1", org_no="06010", market="KR",
        order_type="00", quantity=10, total=True,
    )
    assert captured["exchange"] == "KRX"
