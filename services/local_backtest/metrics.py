"""8개 메트릭 계산.

total_return_pct / cagr / sharpe_ratio / sortino_ratio /
max_drawdown / win_rate / profit_factor / total_trades
"""

from __future__ import annotations

import math
from datetime import date
from typing import Optional


def _to_date(v) -> Optional[date]:
    if isinstance(v, date):
        return v
    if hasattr(v, "date"):
        try:
            return v.date()
        except Exception:
            return None
    return None


def compute_metrics(
    equity_curve: list[dict],
    trades: list[dict],
    initial_capital: float,
) -> dict:
    """일자별 자본곡선 + 거래내역 → 8개 메트릭 dict.

    equity_curve: [{"date": date, "equity": float}, ...]
    trades: 청산 거래 [{"symbol", "entry_date", "entry_price", "exit_date",
                       "exit_price", "qty", "pnl", "pnl_pct"}, ...]
    """
    out: dict = {
        "total_return_pct": 0.0,
        "cagr": None,
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "max_drawdown": 0.0,
        "win_rate": None,
        "profit_factor": None,
        "total_trades": 0,
    }

    if not equity_curve or initial_capital <= 0:
        return out

    eq_values = [float(p["equity"]) for p in equity_curve]
    final_eq = eq_values[-1]
    initial_eq = float(equity_curve[0].get("equity", initial_capital))

    # total_return
    out["total_return_pct"] = (final_eq - initial_capital) / initial_capital * 100.0

    # CAGR
    first_d = _to_date(equity_curve[0]["date"])
    last_d = _to_date(equity_curve[-1]["date"])
    if first_d and last_d and last_d > first_d and initial_capital > 0:
        days = (last_d - first_d).days
        if days > 0 and final_eq > 0:
            years = days / 365.25
            try:
                cagr = (final_eq / initial_capital) ** (1 / years) - 1
                out["cagr"] = cagr * 100.0
            except Exception:
                out["cagr"] = None

    # MDD
    peak = eq_values[0]
    mdd = 0.0
    for v in eq_values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak
            if dd < mdd:
                mdd = dd
    out["max_drawdown"] = mdd * 100.0  # 음수(낙폭)

    # Sharpe / Sortino — 일별 수익률 기반 (연환산 252)
    daily_returns: list[float] = []
    for i in range(1, len(eq_values)):
        prev = eq_values[i - 1]
        if prev > 0:
            daily_returns.append((eq_values[i] - prev) / prev)
    if daily_returns:
        mean_r = sum(daily_returns) / len(daily_returns)
        # std
        if len(daily_returns) > 1:
            var = sum((r - mean_r) ** 2 for r in daily_returns) / (
                len(daily_returns) - 1
            )
            std = math.sqrt(var)
        else:
            std = 0.0
        if std > 0:
            out["sharpe_ratio"] = (mean_r / std) * math.sqrt(252)
        # Sortino: 음수 수익률만
        neg = [r for r in daily_returns if r < 0]
        if neg:
            neg_mean = 0.0  # downside 기준 0
            neg_var = sum((r - neg_mean) ** 2 for r in neg) / len(neg)
            neg_std = math.sqrt(neg_var)
            if neg_std > 0:
                out["sortino_ratio"] = (mean_r / neg_std) * math.sqrt(252)

    # 거래 메트릭
    out["total_trades"] = len(trades)
    if trades:
        wins = [t for t in trades if (t.get("pnl") or 0) > 0]
        losses = [t for t in trades if (t.get("pnl") or 0) < 0]
        total = len(trades)
        out["win_rate"] = len(wins) / total * 100.0 if total else None

        gross_profit = sum((t.get("pnl") or 0) for t in wins)
        gross_loss = abs(sum((t.get("pnl") or 0) for t in losses))
        if gross_loss > 0:
            out["profit_factor"] = gross_profit / gross_loss
        elif gross_profit > 0:
            out["profit_factor"] = math.inf
        else:
            out["profit_factor"] = None

    return out
