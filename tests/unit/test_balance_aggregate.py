"""R4 (KIS 멀티 계좌) — 잔고 합산 로직 단위 테스트.

REQ-BALANCE-01: 종목 단위 합산 — qty/avg_price(가중평균)/eval/pl
REQ-BALANCE-02: 환율 단일 (계좌 무관)
REQ-BALANCE-03: 병렬 asyncio.gather (Semaphore cap=6) + partial_failure
REQ-BALANCE-04: FNO 통합 (any 계좌 fno_enabled → true, futures 합산 안 함 + account_label 부착)

본 테스트는 합산 함수(`aggregate_balance_accounts`)를 직접 호출하여 검증.
"""

import pytest


def _kr_row(code, name, qty, avg, current=None, *, account_label=None):
    cp = current if current is not None else int(float(avg) * 1.05)
    quantity_i = int(qty)
    eval_amt = quantity_i * cp
    cost = quantity_i * float(avg)
    pl = eval_amt - cost
    return {
        "code": code,
        "name": name,
        "quantity": str(quantity_i),
        "avg_price": str(avg),
        "current_price": str(cp),
        "eval_amount": str(eval_amt),
        "profit_loss": str(int(pl)),
        "profit_rate": str(round(pl / cost * 100, 2)) if cost else "0",
        "exchange": "KOSPI",
        "mktcap": None,
        "per": None,
        "pbr": None,
        "roe": None,
        "dividend_yield": None,
        "account_label": account_label,
    }


def _us_row(code, name, qty, avg, current=None, *, exrt=1400.0, currency="USD", account_label=None):
    cp = current if current is not None else float(avg) * 1.10
    quantity_i = int(qty)
    eval_amt = quantity_i * cp
    cost = quantity_i * float(avg)
    pl = eval_amt - cost
    return {
        "code": code,
        "name": name,
        "exchange": "NASD",
        "currency": currency,
        "quantity": str(quantity_i),
        "avg_price": str(avg),
        "current_price": str(cp),
        "profit_loss": str(round(pl, 2)),
        "profit_loss_krw": str(round(pl * exrt)),
        "profit_rate": str(round(pl / cost * 100, 2)),
        "eval_amount": str(round(eval_amt, 2)),
        "eval_amount_krw": str(round(eval_amt * exrt)),
        "account_label": account_label,
    }


def _account_response(label, *, stock_list=None, overseas_list=None, futures_list=None,
                      domestic_eval=0, domestic_deposit=0,
                      overseas_eval_krw=0, overseas_deposit_krw=0,
                      fno_enabled=False, exchange_rates=None):
    return {
        "label": label,
        "stock_list": stock_list or [],
        "overseas_list": overseas_list or [],
        "futures_list": futures_list or [],
        "stock_eval_domestic": str(domestic_eval),
        "stock_eval_overseas_krw": str(overseas_eval_krw),
        "deposit_domestic": str(domestic_deposit),
        "deposit_overseas_krw": str(overseas_deposit_krw),
        "fno_enabled": fno_enabled,
        "exchange_rates": exchange_rates or {},
    }


class TestAggregateBalance:
    """REQ-BALANCE-01: 종목 단위 합산."""

    def test_weighted_avg_same_kr_stock_in_two_accounts(self):
        """계좌A: 005930 10주 @70000, 계좌B: 005930 5주 @80000 → 15주 @73333."""
        from services.balance_service import aggregate_balance_accounts

        a = _account_response("주식",
            stock_list=[_kr_row("005930", "삼성전자", 10, 70000, 75000, account_label="주식")],
            domestic_eval=750000, domestic_deposit=1000000,
        )
        b = _account_response("연금",
            stock_list=[_kr_row("005930", "삼성전자", 5, 80000, 75000, account_label="연금")],
            domestic_eval=375000, domestic_deposit=500000,
        )

        result = aggregate_balance_accounts([a, b])

        # 종목 단일 row 로 합산
        stock_list = result["stock_list"]
        assert len(stock_list) == 1
        row = stock_list[0]
        assert row["code"] == "005930"
        assert int(row["quantity"]) == 15
        # 가중평균 = (10*70000 + 5*80000) / 15 = 73333
        avg = float(row["avg_price"])
        assert 73332 <= round(avg) <= 73334
        # eval_amount = 15 * 75000 = 1,125,000
        assert int(float(row["eval_amount"])) == 1_125_000
        # accounts 메타
        assert sorted(row["accounts"]) == sorted(["주식", "연금"])

    def test_distinct_stocks_keep_separate(self):
        """다른 종목은 별도 row 로."""
        from services.balance_service import aggregate_balance_accounts

        a = _account_response("주식",
            stock_list=[_kr_row("005930", "삼성전자", 10, 70000, account_label="주식")],
        )
        b = _account_response("연금",
            stock_list=[_kr_row("035720", "카카오", 8, 50000, account_label="연금")],
        )

        result = aggregate_balance_accounts([a, b])
        codes = sorted(r["code"] for r in result["stock_list"])
        assert codes == ["005930", "035720"]

    def test_single_holding_accounts_list_one(self):
        """단독 보유 종목 → accounts 메타 1개."""
        from services.balance_service import aggregate_balance_accounts

        a = _account_response("주식",
            stock_list=[_kr_row("005930", "삼성전자", 10, 70000, account_label="주식")],
        )
        b = _account_response("연금")

        result = aggregate_balance_accounts([a, b])
        row = result["stock_list"][0]
        assert row["accounts"] == ["주식"]

    def test_overseas_sum_with_single_exchange_rate(self):
        """REQ-BALANCE-02: 환율은 계좌 무관 단일. 다른 환율 들어와도 첫 응답 환율 사용."""
        from services.balance_service import aggregate_balance_accounts

        a = _account_response("주식",
            overseas_list=[_us_row("AAPL", "Apple", 10, 150, 180, exrt=1400.0, account_label="주식")],
            overseas_eval_krw=2_520_000,
            exchange_rates={"USD": 1400.0},
        )
        b = _account_response("연금",
            overseas_list=[_us_row("AAPL", "Apple", 5, 160, 180, exrt=1410.0, account_label="연금")],
            overseas_eval_krw=1_269_000,
            exchange_rates={"USD": 1410.0},
        )

        result = aggregate_balance_accounts([a, b])

        # AAPL 합산: 15주, 가중평균 (10*150+5*160)/15 = 153.33
        rows = [r for r in result["overseas_list"] if r["code"] == "AAPL"]
        assert len(rows) == 1
        row = rows[0]
        assert int(row["quantity"]) == 15
        assert 153 <= float(row["avg_price"]) <= 154

    def test_fno_not_summed_keeps_individual_with_label(self):
        """REQ-BALANCE-04: FNO 는 합산 안 함 — account_label 부착하여 그대로 합쳐 반환."""
        from services.balance_service import aggregate_balance_accounts

        a = _account_response("주식", fno_enabled=True,
            futures_list=[{
                "name": "KOSPI200선물", "code": "101W06", "trade_type": "매수",
                "quantity": "1", "avg_price": "350.0", "current_price": "352.0",
                "profit_loss": "200", "profit_rate": "0.57", "eval_amount": "352",
                "account_label": "주식",
            }],
        )
        b = _account_response("연금", fno_enabled=False,
            futures_list=[],
        )

        result = aggregate_balance_accounts([a, b])
        assert result["fno_enabled"] is True
        assert len(result["futures_list"]) == 1
        assert result["futures_list"][0]["account_label"] == "주식"


class TestAggregateMetaFields:
    """accounts 메타 / partial_failure / 총계 합산."""

    def test_total_evaluation_sum(self):
        from services.balance_service import aggregate_balance_accounts

        a = _account_response("주식",
            domestic_eval=1_000_000, domestic_deposit=500_000,
            overseas_eval_krw=2_000_000, overseas_deposit_krw=300_000,
        )
        b = _account_response("연금",
            domestic_eval=500_000, domestic_deposit=200_000,
        )

        result = aggregate_balance_accounts([a, b])
        # total_eval = 1_000_000 + 500_000 (domestic) + 2_000_000 + 0 (overseas) + 0 + 300_000 (deposit_overseas)
        # stock_eval = 1_500_000 (KR) + 2_000_000 (overseas) = 3_500_000
        assert int(result["stock_eval_domestic"]) == 1_500_000
        assert int(result["stock_eval_overseas_krw"]) == 2_000_000
        assert int(result["stock_eval"]) == 3_500_000
        # deposit
        assert int(result["deposit_domestic"]) == 700_000
        assert int(result["deposit_overseas_krw"]) == 300_000
        assert int(result["deposit"]) == 1_000_000

    def test_accounts_meta_includes_label_list(self):
        from services.balance_service import aggregate_balance_accounts

        a = _account_response("주식", stock_list=[
            _kr_row("005930", "삼성전자", 10, 70000, account_label="주식"),
        ])
        b = _account_response("연금")

        result = aggregate_balance_accounts([a, b])
        # 응답에 accounts 메타 (탭 렌더링용)
        assert "accounts" in result
        labels = sorted(a["label"] for a in result["accounts"])
        assert labels == sorted(["주식", "연금"])

    def test_partial_failure_propagates(self):
        from services.balance_service import aggregate_balance_accounts

        a = _account_response("주식", stock_list=[
            _kr_row("005930", "삼성전자", 10, 70000, account_label="주식"),
        ])
        b = _account_response("연금")
        b["partial_failure"] = ["연금 KR 조회 실패"]

        result = aggregate_balance_accounts([a, b])
        assert any("연금" in m for m in result.get("partial_failure", []))

    def test_fno_enabled_any(self):
        """계좌 중 1개라도 fno_enabled → True."""
        from services.balance_service import aggregate_balance_accounts
        result = aggregate_balance_accounts([
            _account_response("A", fno_enabled=False),
            _account_response("B", fno_enabled=True),
        ])
        assert result["fno_enabled"] is True

    def test_empty_accounts_returns_empty_response(self):
        from services.balance_service import aggregate_balance_accounts
        result = aggregate_balance_accounts([])
        assert result["stock_list"] == []
        assert result["overseas_list"] == []
        assert result["futures_list"] == []
        assert result["fno_enabled"] is False
        assert result["accounts"] == []
        assert int(result["total_evaluation"]) == 0
