"""포트폴리오 일봉 시뮬레이터 — 4 전략 공통 엔진.

루프 (매 거래일 t):
  a) 보유 포지션 exit 평가 (손절 우선)
     - 청산 시 자본 풀에 회수 (수수료 + 세금 + 슬리피지 차감)
  b) 신규 매수 후보 수집 (모든 종목 entry 체크)
  c) 가용 슬롯만큼 균등 배분 → cash / 슬롯 수 = 종목당 자금
     - 수수료 + 슬리피지 가산
  d) MTM 평가 → equity_curve 갱신
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd

from services.local_backtest.data_loader import DataLoader
from services.local_backtest.metrics import compute_metrics
from services.local_backtest.portfolio import PortfolioState
from services.local_backtest.strategies import get_strategy
from services.local_backtest.strategies._base import (
    EntrySignal,
    ExitSignal,
    Position,
    Strategy,
)

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    equity_curve: list[dict]
    trades: list[dict]
    metrics: dict
    per_symbol_contribution: dict
    params: dict
    failures: list[str] = field(default_factory=list)


def _apply_buy_costs(
    target_price: float, slippage: float, commission_rate: float
) -> float:
    """매수 단가 보정: target × (1+slippage). 수수료는 cost 계산에서 별도 가산."""
    return target_price * (1.0 + slippage)


def _apply_sell_costs(
    target_price: float, slippage: float
) -> float:
    """매도 단가 보정: target × (1-slippage). 수수료/세금은 proceeds에서 별도 차감."""
    return target_price * (1.0 - slippage)


def _date_of(idx: int, df: pd.DataFrame) -> date:
    ts = df.index[idx]
    if hasattr(ts, "date"):
        return ts.date()
    return ts


def simulate(
    symbols: list[str],
    strategy_id: str,
    market: str,
    start: date,
    end: date,
    initial_capital: float,
    commission_rate: float = 0.0015,
    tax_rate: float = 0.0023,
    slippage: float = 0.001,
    params: Optional[dict] = None,
) -> SimulationResult:
    """4개 전략 + 포트폴리오 균등 배분 일봉 시뮬레이션.

    매수: target × (1+slippage), 수수료=매수액×commission_rate
    매도: target × (1-slippage), 수수료=매도액×commission_rate, 세금=매도액×tax_rate
    """
    if not symbols:
        raise ValueError("symbols 비어있음")
    if len(symbols) > 10:
        raise ValueError("최대 10종목까지 지원")
    if start >= end:
        raise ValueError("start ≥ end")

    strategy: Strategy = get_strategy(strategy_id)
    eff_params = dict(strategy.default_params)
    if params:
        eff_params.update({k: v for k, v in params.items() if v is not None})

    # 1. 종목별 OHLCV fetch
    loader = DataLoader(market=market)
    failures: list[str] = []
    symbol_data: dict[str, pd.DataFrame] = {}
    history_buffer = max(strategy.required_history_days() + 20, 80)
    for sym in symbols:
        df = loader.load(sym, start, end, history_buffer_days=history_buffer)
        if df is None or df.empty:
            failures.append(sym)
            continue
        symbol_data[sym] = df

    if not symbol_data:
        return SimulationResult(
            equity_curve=[],
            trades=[],
            metrics=compute_metrics([], [], initial_capital),
            per_symbol_contribution={},
            params=eff_params,
            failures=failures,
        )

    # 2. 거래일 = start ≤ d ≤ end 인 모든 종목 합집합
    all_dates: set[date] = set()
    for df in symbol_data.values():
        for ts in df.index:
            d = ts.date() if hasattr(ts, "date") else ts
            if start <= d <= end:
                all_dates.add(d)
    trading_days = sorted(all_dates)
    if not trading_days:
        return SimulationResult(
            equity_curve=[],
            trades=[],
            metrics=compute_metrics([], [], initial_capital),
            per_symbol_contribution={},
            params=eff_params,
            failures=failures,
        )

    max_slots = min(10, len(symbols))
    state = PortfolioState(initial_capital=initial_capital, max_slots=max_slots)

    equity_curve: list[dict] = []
    trades: list[dict] = []
    per_symbol_contribution: dict[str, dict] = {
        s: {
            "symbol": s,
            "trades": 0,
            "realized_pnl": 0.0,
            "wins": 0,
            "losses": 0,
        }
        for s in symbol_data.keys()
    }

    # 종목별 idx 추적 (trading day → df 행 매핑)
    def _idx_for(df: pd.DataFrame, d: date) -> Optional[int]:
        try:
            ts = pd.Timestamp(d)
            if ts in df.index:
                return df.index.get_loc(ts)
        except Exception:
            pass
        return None

    for d in trading_days:
        # ── (a) Exit 평가 ──────────────────────────────────────────────
        to_close: list[tuple[str, ExitSignal]] = []
        for sym, pos in list(state.positions.items()):
            df = symbol_data.get(sym)
            if df is None:
                continue
            i = _idx_for(df, d)
            if i is None:
                continue
            exit_sig = strategy.check_exit(df, i, pos, eff_params)
            if exit_sig is not None:
                to_close.append((sym, exit_sig))

        for sym, exit_sig in to_close:
            pos = state.get_position(sym)
            if pos is None:
                continue
            sell_unit = _apply_sell_costs(exit_sig.price, slippage)
            gross_proceeds = sell_unit * pos.qty
            commission = gross_proceeds * commission_rate
            tax = gross_proceeds * tax_rate
            net_proceeds = gross_proceeds - commission - tax
            entry_cost_unit = pos.entry_price  # buy_unit (slippage 이미 반영된 단가)
            pnl = net_proceeds - entry_cost_unit * pos.qty
            pnl_pct = (
                (sell_unit - entry_cost_unit) / entry_cost_unit * 100.0
                if entry_cost_unit > 0
                else 0.0
            )
            state.close_position(sym, exit_date=d, exit_price=sell_unit, proceeds=net_proceeds)
            trades.append(
                {
                    "symbol": sym,
                    "entry_date": pos.entry_date.isoformat(),
                    "entry_price": entry_cost_unit,
                    "exit_date": d.isoformat(),
                    "exit_price": sell_unit,
                    "qty": pos.qty,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "exit_reason": exit_sig.reason,
                }
            )
            agg = per_symbol_contribution.setdefault(sym, {"symbol": sym, "trades": 0,
                                                            "realized_pnl": 0.0,
                                                            "wins": 0, "losses": 0})
            agg["trades"] += 1
            agg["realized_pnl"] += pnl
            if pnl > 0:
                agg["wins"] += 1
            elif pnl < 0:
                agg["losses"] += 1

        # ── (b) Entry 후보 수집 ────────────────────────────────────────
        candidates: list[tuple[str, EntrySignal]] = []
        for sym, df in symbol_data.items():
            if state.has_position(sym):
                continue
            i = _idx_for(df, d)
            if i is None:
                continue
            sig = strategy.check_entry(df, i, eff_params)
            if sig is not None:
                candidates.append((sym, sig))

        # ── (c) 균등 배분 매수 ─────────────────────────────────────────
        if candidates:
            available_slots = state.available_slots()
            num_to_buy = min(len(candidates), available_slots)
            if num_to_buy > 0:
                # 후보 N개 중 슬롯만큼만 매수. 단순화: 입력 순서 우선
                buy_targets = candidates[:num_to_buy]
                # 종목당 자금 = 현재 cash / 매수할 종목 수 (균등 배분)
                per_symbol_budget = state.cash / num_to_buy if num_to_buy > 0 else 0.0
                for sym, entry_sig in buy_targets:
                    buy_unit = _apply_buy_costs(entry_sig.price, slippage, commission_rate)
                    if buy_unit <= 0:
                        continue
                    # 수수료를 고려한 종목당 가능 수량 = budget / (buy_unit × (1+commission))
                    qty = math.floor(
                        per_symbol_budget / (buy_unit * (1.0 + commission_rate))
                    )
                    if qty <= 0:
                        continue
                    cost = buy_unit * qty
                    commission = cost * commission_rate
                    total_cost = cost + commission
                    if total_cost > state.cash + 1e-6:
                        continue
                    pos = Position(
                        symbol=sym,
                        entry_date=d,
                        entry_price=buy_unit,
                        qty=qty,
                        extra={},
                    )
                    state.open_position(pos, cost=total_cost)
                    trades.append(
                        {
                            "symbol": sym,
                            "entry_date": d.isoformat(),
                            "entry_price": buy_unit,
                            "exit_date": None,
                            "exit_price": None,
                            "qty": qty,
                            "pnl": None,
                            "pnl_pct": None,
                            "exit_reason": None,
                            "side": "buy",
                        }
                    )

        # ── (d) MTM 평가 ──────────────────────────────────────────────
        mtm: dict[str, float] = {}
        for sym, pos in state.positions.items():
            df = symbol_data.get(sym)
            i = _idx_for(df, d) if df is not None else None
            if i is not None:
                mtm[sym] = float(df["close"].iloc[i])
            else:
                mtm[sym] = pos.entry_price
        eq = state.equity(mtm)
        equity_curve.append({"date": d.isoformat(), "equity": eq})

    # 미청산 포지션은 마지막 거래일 종가로 강제 정리하지 않음 — pnl=None으로 trades에 표시
    metrics = compute_metrics(equity_curve, [t for t in trades if t.get("exit_date")], initial_capital)
    return SimulationResult(
        equity_curve=equity_curve,
        trades=trades,
        metrics=metrics,
        per_symbol_contribution=per_symbol_contribution,
        params=eff_params,
        failures=failures,
    )
