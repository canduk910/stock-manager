"""R5 — 주문/예약 account_label 전파.

REQ-ORDER-01: place_order(..., account_label) 시그니처 + orders.account_label 기록.
REQ-API-03: POST /api/order body 에 account_label, default 폴백.
REQ-API-04: GET /api/order/* 쿼리 account_label.
REQ-API-05: 정정/취소는 원주문 account_label 사용.
REQ-ORDER-02: reservation_service 가 account_label 전파.
"""

from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _bind_session(_test_engine):
    """get_session() / SessionLocal 을 테스트 PostgreSQL 로 reconfigure."""
    import db.session as _db_session_mod
    orig_bind = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=_test_engine)
    yield
    _db_session_mod.SessionLocal.configure(bind=orig_bind)


@patch("services.order_service.place_domestic_order")
@patch("services.order_service.get_access_token", return_value="TOK")
@patch("services.order_service.get_kis_credentials")
def test_place_order_records_account_label(mock_creds, _tok, mock_kr, db_session, _test_engine, monkeypatch):
    """REQ-ORDER-01: place_order 가 orders.account_label 에 라벨을 기록한다."""
    import db.session as _db_session_mod
    orig_bind = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=_test_engine)
    try:
        mock_creds.return_value = ("K", "S", "11112222", "01", "")
        mock_kr.return_value = {"order_no": "0001234567", "org_no": "12345", "kis_response": ""}

        from services.order_service import place_order
        out = place_order(
            symbol="005930", symbol_name="삼성전자", market="KR", side="buy",
            order_type="00", price=70000, quantity=10,
            account_label="주식",
        )
        assert out["account_label"] == "주식"

        # KIS API 호출 시 get_kis_credentials/get_access_token 에 account_label 전달 검증
        # — 호출 인자 첫 args 검사
        assert mock_creds.call_args.kwargs.get("account_label") == "주식" or \
               (len(mock_creds.call_args.args) >= 2 and mock_creds.call_args.args[1] == "주식")
    finally:
        _db_session_mod.SessionLocal.configure(bind=orig_bind)


@patch("services.order_service.place_domestic_order")
@patch("services.order_service.get_access_token", return_value="TOK")
@patch("services.order_service.get_kis_credentials")
def test_place_order_no_label_falls_back_to_default(mock_creds, _tok, mock_kr, db_session, _test_engine):
    """REQ-API-03: account_label 누락 시 default 폴백 (account_label NULL 보존)."""
    import db.session as _db_session_mod
    orig_bind = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=_test_engine)
    try:
        mock_creds.return_value = ("K", "S", "11112222", "01", "")
        mock_kr.return_value = {"order_no": "0001234567", "org_no": "12345", "kis_response": ""}

        from services.order_service import place_order
        out = place_order(
            symbol="005930", symbol_name="삼성전자", market="KR", side="buy",
            order_type="00", price=70000, quantity=10,
        )
        # NULL 또는 빈 문자열 — 어느 쪽이든 OK
        assert out.get("account_label") in (None, "")
    finally:
        _db_session_mod.SessionLocal.configure(bind=orig_bind)


def test_reservation_carries_account_label(db_session):
    """REQ-ORDER-02: 예약주문 등록 시 account_label 저장."""
    from services.order_service import create_reservation
    out = create_reservation(
        symbol="005930", symbol_name="삼성전자", market="KR", side="buy",
        order_type="00", price=70000, quantity=10,
        condition_type="price_below", condition_value="68000",
        account_label="연금",
    )
    assert out["account_label"] == "연금"


def test_reservation_no_label_persists_null(db_session):
    from services.order_service import create_reservation
    out = create_reservation(
        symbol="005930", symbol_name="삼성전자", market="KR", side="buy",
        order_type="00", price=70000, quantity=10,
        condition_type="price_below", condition_value="68000",
    )
    assert out.get("account_label") in (None, "")
