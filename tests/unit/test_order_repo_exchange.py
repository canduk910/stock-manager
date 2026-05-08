"""R_1 (KRX+NXT 통합시세): orders.exchange 컬럼 + Repository 단위 테스트."""

import pytest

from db.repositories.order_repo import OrderRepository


def _base_kwargs(**overrides):
    base = dict(
        symbol="005930",
        symbol_name="삼성전자",
        market="KR",
        side="buy",
        order_type="00",
        price=70000.0,
        quantity=10,
        currency="KRW",
        memo="",
        status="PLACED",
    )
    base.update(overrides)
    return base


def test_insert_order_with_exchange_sor(db_session):
    """exchange=SOR로 insert 시 to_dict에 'SOR' 그대로 반환."""
    repo = OrderRepository(db_session)
    row = repo.insert_order(**_base_kwargs(exchange="SOR"))
    assert row["exchange"] == "SOR"


def test_insert_order_with_exchange_nxt(db_session):
    """exchange=NXT로 insert 시 to_dict에 'NXT' 반환."""
    repo = OrderRepository(db_session)
    row = repo.insert_order(**_base_kwargs(exchange="NXT"))
    assert row["exchange"] == "NXT"


def test_insert_order_default_exchange_is_null_falls_back_to_krx(db_session):
    """exchange 미지정(NULL) 시 to_dict()에 'KRX' 폴백."""
    repo = OrderRepository(db_session)
    row = repo.insert_order(**_base_kwargs())
    # 신규 컬럼은 nullable. to_dict에서 None → "KRX" legacy 폴백.
    assert row["exchange"] == "KRX"


def test_insert_order_explicit_krx(db_session):
    """exchange=KRX 명시도 to_dict에 KRX."""
    repo = OrderRepository(db_session)
    row = repo.insert_order(**_base_kwargs(exchange="KRX"))
    assert row["exchange"] == "KRX"


def test_update_order_status_can_overwrite_exchange(db_session):
    """update_order_status에 exchange 인자 전달 시 SOR → SOR-KRX로 정밀 거래소 덮어쓰기."""
    repo = OrderRepository(db_session)
    row = repo.insert_order(**_base_kwargs(exchange="SOR", status="PENDING"))
    order_id = row["id"]
    updated = repo.update_order_status(
        order_id, "PLACED",
        order_no="0020551600",
        org_no="06010",
        exchange="SOR-KRX",
    )
    assert updated["exchange"] == "SOR-KRX"


def test_update_order_status_without_exchange_keeps_value(db_session):
    """update_order_status에 exchange 미지정 시 기존값 유지."""
    repo = OrderRepository(db_session)
    row = repo.insert_order(**_base_kwargs(exchange="NXT", status="PENDING"))
    order_id = row["id"]
    updated = repo.update_order_status(order_id, "PLACED", order_no="0020551601")
    assert updated["exchange"] == "NXT"


def test_to_dict_exchange_key_present(db_session):
    """to_dict 응답에 'exchange' 키가 항상 존재."""
    repo = OrderRepository(db_session)
    row = repo.insert_order(**_base_kwargs())
    assert "exchange" in row
