"""R1 (KIS 멀티 계좌) — orders/reservations.account_label 컬럼 검증.

REQ-SCHEMA-02: orders/reservations 에 account_label 컬럼 추가 (NULL=default 계좌 폴백).
- (user_id, account_label) 복합 인덱스 — 쿼리 성능.
- 기존 row 는 NULL 보존 (NOT NULL 강제 금지 — 마이그레이션 무결성).
- INSERT 시 account_label 명시 → SELECT WHERE account_label 필터 동작.
"""

from db.repositories.order_repo import OrderRepository


def _ord(symbol="005930", market="KR", side="buy", price=70000, qty=10, *, user_id=None, account_label=None):
    return dict(
        symbol=symbol,
        symbol_name="삼성전자",
        market=market,
        side=side,
        order_type="00",
        price=float(price),
        quantity=qty,
        currency="KRW" if market != "US" else "USD",
        memo="",
        status="PLACED",
        user_id=user_id,
        account_label=account_label,
    )


class TestOrderAccountLabel:
    def test_insert_with_account_label(self, db_session):
        repo = OrderRepository(db_session)
        row = repo.insert_order(**_ord(user_id=1, account_label="주식"))
        db_session.commit()
        assert row["account_label"] == "주식"

    def test_insert_without_account_label_is_null(self, db_session):
        """account_label 누락 → NULL 보존 (기존 row 호환)."""
        repo = OrderRepository(db_session)
        row = repo.insert_order(**_ord(user_id=1))
        db_session.commit()
        assert row.get("account_label") is None

    def test_list_orders_filter_by_account_label(self, db_session):
        repo = OrderRepository(db_session)
        repo.insert_order(**_ord(symbol="005930", user_id=1, account_label="주식"))
        repo.insert_order(**_ord(symbol="035720", user_id=1, account_label="연금"))
        repo.insert_order(**_ord(symbol="000660", user_id=1, account_label=None))  # 라벨 없음(legacy)
        db_session.commit()

        rows_all = repo.list_orders(user_id=1)
        assert len(rows_all) == 3

        rows_stock = repo.list_orders(user_id=1, account_label="주식")
        assert len(rows_stock) == 1
        assert rows_stock[0]["symbol"] == "005930"

        rows_pension = repo.list_orders(user_id=1, account_label="연금")
        assert len(rows_pension) == 1
        assert rows_pension[0]["symbol"] == "035720"


class TestReservationAccountLabel:
    def _res(self, *, user_id=1, account_label=None, symbol="005930"):
        return dict(
            symbol=symbol,
            symbol_name="삼성전자",
            market="KR",
            side="buy",
            order_type="00",
            price=70000.0,
            quantity=10,
            condition_type="price_below",
            condition_value="68000",
            memo="",
            user_id=user_id,
            account_label=account_label,
        )

    def test_insert_with_account_label(self, db_session):
        repo = OrderRepository(db_session)
        row = repo.insert_reservation(**self._res(account_label="주식"))
        db_session.commit()
        assert row["account_label"] == "주식"

    def test_insert_without_account_label_is_null(self, db_session):
        repo = OrderRepository(db_session)
        row = repo.insert_reservation(**self._res(account_label=None))
        db_session.commit()
        assert row.get("account_label") is None

    def test_list_reservations_fifo_order_by_created_at(self, db_session):
        """REQ-DOMAIN-02 — list_reservations 정렬은 created_at ASC (FIFO).

        과거 코드: Reservation.id.desc(). 본 작업 후: Reservation.id.asc().
        """
        repo = OrderRepository(db_session)
        # 순서대로 등록 → 같은 created_at(미세 차이)일 때 id ASC 정렬 확인
        r1 = repo.insert_reservation(**self._res(symbol="A001"))
        r2 = repo.insert_reservation(**self._res(symbol="B002"))
        r3 = repo.insert_reservation(**self._res(symbol="C003"))
        db_session.commit()
        rows = repo.list_reservations(status="WAITING")
        symbols = [r["symbol"] for r in rows]
        # FIFO: A001 → B002 → C003
        assert symbols == ["A001", "B002", "C003"], (
            "예약주문 list_reservations() 는 FIFO(created_at/id ASC) 정렬이어야 한다 (REQ-DOMAIN-02)"
        )
