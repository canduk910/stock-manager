"""균등 배분 자본 관리 (max 10 슬롯)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from services.local_backtest.strategies._base import Position


@dataclass
class PortfolioState:
    """포트폴리오 상태 — 자본 풀 + 보유 포지션 + 슬롯.

    룰:
      - max_slots = min(10, len(symbols))
      - 매 거래일 신규 후보 → (가용 슬롯) 만큼 균등 배분
      - 자본 풀 / 가용 슬롯 = 종목당 매수 금액
      - 슬롯 가득 차면 신규 신호 스킵 (라이브 자본 부족 거동)
      - 청산 → 자본 회수 → 다음 거래일 재배분
    """

    initial_capital: float
    max_slots: int  # 사용자 지정 최대 슬롯 (1~10)
    cash: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_slots < 1 or self.max_slots > 10:
            self.max_slots = max(1, min(self.max_slots, 10))
        self.cash = float(self.initial_capital)

    def position_count(self) -> int:
        return len(self.positions)

    def available_slots(self) -> int:
        return self.max_slots - self.position_count()

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions

    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    def allocate(self, num_candidates: int) -> int:
        """num_candidates 후보에 대해 실제 매수 가능 종목 수 반환.

        가용 슬롯과 후보 수 중 작은 값. (자본 부족은 호출자 책임)
        """
        return min(max(num_candidates, 0), max(self.available_slots(), 0))

    def allocation_amount(self, num_to_buy: int) -> float:
        """매수 금액(종목당) = cash / num_to_buy. 0 분할은 0.0 반환."""
        if num_to_buy <= 0:
            return 0.0
        return self.cash / num_to_buy

    def open_position(self, position: Position, cost: float) -> None:
        """포지션 등록 + 자본 차감."""
        if position.symbol in self.positions:
            raise ValueError(f"already holding {position.symbol}")
        if cost > self.cash + 1e-6:
            raise ValueError(
                f"insufficient cash: need={cost:.2f}, have={self.cash:.2f}"
            )
        self.positions[position.symbol] = position
        self.cash -= cost

    def close_position(
        self,
        symbol: str,
        exit_date: date,
        exit_price: float,
        proceeds: float,
    ) -> Position:
        """포지션 청산 → 매도 대금을 cash에 회수. 청산된 Position 반환."""
        if symbol not in self.positions:
            raise KeyError(f"no position: {symbol}")
        pos = self.positions.pop(symbol)
        self.cash += proceeds
        return pos

    def equity(self, mark_to_market: dict[str, float]) -> float:
        """현재 평가 자본 = cash + Σ(보유수량 × MTM가격).

        mark_to_market: {symbol: 현재가}. 누락된 심볼은 entry_price로 대체.
        """
        eq = self.cash
        for sym, pos in self.positions.items():
            px = float(mark_to_market.get(sym, pos.entry_price))
            eq += pos.qty * px
        return eq
