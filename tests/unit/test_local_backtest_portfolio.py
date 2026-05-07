"""local_backtest.portfolio (균등 배분 자본 관리) 단위 테스트.

룰:
  - 슬롯 max_slots = min(10, len(symbols))
  - 매 거래일 신규 매수 후보 수집 → (가용 슬롯 = max_slots - 보유) 만큼 균등 배분
  - 자본 풀에서 (현재 가용 자본 / 가용 슬롯)만큼 종목당 매수
  - 슬롯이 차면 신규 신호 스킵
  - 청산 후 자본 회수 → 다음 거래일에 재배분 가능
"""

from __future__ import annotations

import pytest


def test_portfolio_initial_state_5_symbols():
    """5종목 → max_slots=5, 보유 0, 가용 자본 = 초기자본."""
    from services.local_backtest.portfolio import PortfolioState

    state = PortfolioState(initial_capital=10_000_000, max_slots=5)
    assert state.cash == 10_000_000
    assert state.max_slots == 5
    assert state.available_slots() == 5
    assert state.position_count() == 0


def test_portfolio_buy_distributes_capital_equally():
    """5종목 모두 매수 후보 → 종목당 자본의 1/5씩 사용."""
    from services.local_backtest.portfolio import PortfolioState

    state = PortfolioState(initial_capital=10_000_000, max_slots=5)
    # 5개 종목 후보. allocate_amount 호출.
    candidates = ["A", "B", "C", "D", "E"]
    allocations = state.allocate(len(candidates))
    assert allocations == 5
    # 종목당 2,000,000원 가용
    per_symbol = state.cash / state.available_slots()
    assert per_symbol == pytest.approx(2_000_000)


def test_portfolio_skip_when_slots_full():
    """슬롯이 가득 차면 신규 매수 후보를 스킵."""
    from datetime import date
    from services.local_backtest.portfolio import PortfolioState
    from services.local_backtest.strategies._base import Position

    state = PortfolioState(initial_capital=10_000_000, max_slots=2)
    state.open_position(Position(symbol="A", entry_date=date(2024, 1, 2), entry_price=100.0, qty=10), cost=1_000.0)
    state.open_position(Position(symbol="B", entry_date=date(2024, 1, 2), entry_price=200.0, qty=5), cost=1_000.0)
    assert state.available_slots() == 0
    # 신규 신호가 와도 매수 못함
    allowed = state.allocate(num_candidates=3)
    assert allowed == 0


def test_portfolio_close_position_returns_capital():
    """청산 후 가용 자본 + 슬롯이 회수돼야 한다."""
    from datetime import date
    from services.local_backtest.portfolio import PortfolioState
    from services.local_backtest.strategies._base import Position

    state = PortfolioState(initial_capital=10_000_000, max_slots=2)
    initial_cash_after_buy = 10_000_000 - 1_000_000  # 매수 비용 100만
    pos = Position(symbol="A", entry_date=date(2024, 1, 2), entry_price=100.0, qty=10000)
    state.open_position(pos, cost=1_000_000.0)
    assert state.cash == pytest.approx(initial_cash_after_buy)
    assert state.available_slots() == 1

    # 청산: proceeds=1,200,000(20% 익) → 자본 회수
    state.close_position("A", exit_date=date(2024, 1, 5), exit_price=120.0, proceeds=1_200_000.0)
    # 1,200,000 회수 + 청산 후 슬롯 1 → 2 회복
    assert state.cash == pytest.approx(initial_cash_after_buy + 1_200_000)
    assert state.available_slots() == 2
    assert state.position_count() == 0


def test_portfolio_max_slots_capped_at_10():
    """11종목 입력해도 max_slots=10 (룰)."""
    from services.local_backtest.portfolio import PortfolioState

    state = PortfolioState(initial_capital=10_000_000, max_slots=10)
    # 후보 11개 → 슬롯 10개만 분배
    allowed = state.allocate(num_candidates=11)
    assert allowed == 10


def test_portfolio_allocate_exact_capital_split():
    """allocate(N) → 종목당 매수 금액 = cash / N. N>슬롯이면 슬롯 수로 제한."""
    from services.local_backtest.portfolio import PortfolioState

    state = PortfolioState(initial_capital=9_000_000, max_slots=3)
    # 후보 3, 슬롯 3 → per_symbol=3,000,000
    allowed = state.allocate(num_candidates=3)
    per = state.allocation_amount(allowed)
    assert allowed == 3
    assert per == pytest.approx(3_000_000)
