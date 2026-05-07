"""4개 KR 전략 레지스트리."""

from services.local_backtest.strategies._base import (
    EntrySignal,
    ExitSignal,
    Position,
    Strategy,
)
from services.local_backtest.strategies.donchian_swing import DonchianSwingStrategy
from services.local_backtest.strategies.long_tail_volatility import (
    LongTailVolatilityStrategy,
)
from services.local_backtest.strategies.momentum import MomentumStrategy
from services.local_backtest.strategies.volatility_breakout import (
    VolatilityBreakoutStrategy,
)

STRATEGY_REGISTRY: dict[str, type[Strategy]] = {
    "momentum": MomentumStrategy,
    "volatility_breakout": VolatilityBreakoutStrategy,
    "donchian_swing": DonchianSwingStrategy,
    "long_tail_volatility": LongTailVolatilityStrategy,
}


def get_strategy(strategy_id: str) -> Strategy:
    """전략 ID로 인스턴스 반환."""
    cls = STRATEGY_REGISTRY.get(strategy_id)
    if cls is None:
        raise KeyError(f"unknown strategy: {strategy_id}")
    return cls()


__all__ = [
    "EntrySignal",
    "ExitSignal",
    "Position",
    "Strategy",
    "STRATEGY_REGISTRY",
    "get_strategy",
    "MomentumStrategy",
    "VolatilityBreakoutStrategy",
    "DonchianSwingStrategy",
    "LongTailVolatilityStrategy",
]
