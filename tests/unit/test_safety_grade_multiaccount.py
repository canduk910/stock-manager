"""R5 (KIS 멀티 계좌) — compute_position_size binding_constraint 메타 검증.

REQ-DOMAIN-01: 합산 평가액 기준 portfolio 한도 + 주문 대상 계좌 단독 cash 가드 (이중 가드).
- target_pct = single_cap × grade_factor → max_amount = total_portfolio × target_pct
- available = min(max_amount, cash_available)
- binding_constraint = "portfolio" if max_amount ≤ cash_available else "cash"
- 응답에 position_meta = {total_portfolio_limit_qty, account_cash_limit_qty, binding_constraint}.

도메인 자문: order-advisor.md (주도), margin-analyst.md (동의), macro-sentinel.md (정합 확인).
"""


class TestBindingConstraintMeta:
    def test_portfolio_binding_when_cash_sufficient(self):
        """합산 1억, 단독 cash 1천만, A등급 selective(single_cap=4%):
        target=4%, max=400만 (portfolio). cash=1000만 > 400만 → portfolio 바인딩.
        """
        from services.safety_grade import compute_position_size
        res = compute_position_size(
            grade="A", regime_single_cap_pct=4.0,
            total_portfolio=100_000_000, cash_available=10_000_000,
            entry_price=80_000,
        )
        assert res["qty"] == 50  # 400만 / 8만 = 50주
        meta = res.get("position_meta")
        assert meta is not None
        assert meta["binding_constraint"] == "portfolio"
        assert meta["total_portfolio_limit_qty"] == 50  # 400만/8만
        assert meta["account_cash_limit_qty"] == 125    # 1000만/8만

    def test_cash_binding_when_cash_insufficient(self):
        """합산 1억, 단독 cash 100만, A등급 selective(4%) → target=400만 (portfolio).
        cash=100만 < 400만 → cash 바인딩. qty = 12 (100만/8만).
        """
        from services.safety_grade import compute_position_size
        res = compute_position_size(
            grade="A", regime_single_cap_pct=4.0,
            total_portfolio=100_000_000, cash_available=1_000_000,
            entry_price=80_000,
        )
        assert res["qty"] == 12  # 100만/8만 = 12 (floor)
        meta = res["position_meta"]
        assert meta["binding_constraint"] == "cash"
        assert meta["total_portfolio_limit_qty"] == 50
        assert meta["account_cash_limit_qty"] == 12

    def test_d_grade_returns_skip_no_meta_required(self):
        """D 등급 → factor=0 → qty=0, recommendation=SKIP (계좌 무관)."""
        from services.safety_grade import compute_position_size
        res = compute_position_size(
            grade="D", regime_single_cap_pct=4.0,
            total_portfolio=100_000_000, cash_available=10_000_000,
            entry_price=80_000,
        )
        assert res["qty"] == 0
        assert res["recommendation"] == "SKIP"

    def test_zero_qty_cash_insufficient_signals_hold(self):
        """portfolio 한도는 있지만 단독 cash 부족 → qty=0 → HOLD.

        cash=10000, portfolio=1억, target=4% (400만), entry=80000 → cash_qty=0 → 최종 0.
        """
        from services.safety_grade import compute_position_size
        res = compute_position_size(
            grade="A", regime_single_cap_pct=4.0,
            total_portfolio=100_000_000, cash_available=10_000,
            entry_price=80_000,
        )
        assert res["qty"] == 0
        assert res["recommendation"] == "HOLD"
        meta = res["position_meta"]
        # binding_constraint=cash + total_portfolio_limit_qty 는 50, account_cash_limit_qty 는 0.
        assert meta["binding_constraint"] == "cash"
        assert meta["total_portfolio_limit_qty"] == 50
        assert meta["account_cash_limit_qty"] == 0
