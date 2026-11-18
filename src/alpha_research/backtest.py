"""Self-financing close-to-close accounting with delayed, close-only execution."""
import numpy as np
import pandas as pd
from scipy.optimize import brentq


def rebalance_cost(drifted_weights, target_weights, one_way_cost):
    """Solve cost = c * ||target*(1-cost) - drifted||_1.

    Weights target post-cost equity; trade notional and costs are normalized by
    pre-trade equity. Charging costs without this adjustment violates exact
    target leverage. The contraction constant is c * target gross exposure.
    """
    old, target = np.asarray(drifted_weights, float), np.asarray(target_weights, float)
    if old.shape != target.shape or not np.all(np.isfinite(old)) or not np.all(np.isfinite(target)):
        raise ValueError("Finite aligned weights required")
    if not 0 <= one_way_cost < 1 or one_way_cost * np.abs(target).sum() >= 1:
        raise ValueError("Cost/gross combination does not define a contraction")
    # The residual C-c*||target*(1-C)-old|| is strictly increasing under
    # the contraction bound. Its value at C=1 determines affordability;
    # an intermediate fixed-point iterate can exceed one even if the root does not.
    if one_way_cost * np.abs(old).sum() >= 1:
        raise ValueError("Transaction costs exhaust portfolio equity")
    cost = 0.0
    for _ in range(100):
        turnover = float(np.abs(target * (1 - cost) - old).sum())
        updated = one_way_cost * turnover
        if abs(updated - cost) < 1e-14:
            return updated, turnover
        cost = updated
    # Contraction may be arbitrarily slow near its bound; the unique feasible
    # root is bracketed by [0,1], so do not reject a valid trade for slow iteration.
    cost = brentq(lambda value: value - one_way_cost *
                  np.abs(target * (1 - value) - old).sum(), 0.0, 1.0, xtol=5e-15)
    return cost, float(np.abs(target * (1 - cost) - old).sum())


def backtest(returns, schedule, cost_bps=10.0, start=None, end=None, liquidate=True):
    """Start flat. Orders execute after today's return and affect tomorrow's P&L.

    No overnight/close return can be earned using a target constructed at its end.
    All legs use the same quoted one-way cost. Cash and short financing earn zero
    in the normalized research accounting; no implementability is asserted.
    """
    if cost_bps < 0 or not np.isfinite(cost_bps):
        raise ValueError("Cost must be finite and nonnegative")
    frame = returns.loc[start:end]
    if len(frame) < 1:
        raise ValueError("Empty backtest interval")
    schedule = schedule.reindex(columns=returns.columns)
    if not schedule.index.is_unique or schedule.isna().any().any():
        raise ValueError("Schedule must have unique dates and complete aligned weights")
    scheduled = {date: row.to_numpy(float) for date, row in schedule.iterrows()
                 if frame.index[0] <= date <= frame.index[-1]}
    w = np.zeros(frame.shape[1])
    nav, c = 1.0, cost_bps / 10000
    rows = []
    for i, (date, row) in enumerate(frame.iterrows()):
        r = row.to_numpy(float)
        if np.any(~np.isfinite(r) & (np.abs(w) > 1e-14)):
            raise ValueError(f"Missing return for a held industry on {date.date()}")
        r = np.where(np.isfinite(r), r, 0)
        gross_return = float(w @ r)
        if 1 + gross_return <= 0:
            raise ValueError("Portfolio equity is exhausted")
        drifted = w * (1 + r) / (1 + gross_return)
        target = scheduled.get(date)
        is_final = liquidate and i == len(frame) - 1
        if is_final:
            target = np.zeros_like(w)
        if target is not None:
            cost, turnover = rebalance_cost(drifted, target, c)
            w = target.copy()
        else:
            cost, turnover, w = 0.0, 0.0, drifted
        net_return = (1 + gross_return) * (1 - cost) - 1
        nav *= 1 + net_return
        rows.append({"date": date, "gross_return": gross_return, "net_return": net_return,
                     "nav": nav, "turnover": turnover, "cost_fraction": cost,
                     "gross_exposure": float(np.abs(w).sum()), "net_exposure": float(w.sum()),
                     "cash_weight": float(1 - w.sum()), "rebalanced": target is not None,
                     "terminal_liquidation": is_final})
    result = pd.DataFrame(rows).set_index("date")
    return result


def equal_weight_schedule(returns):
    """Long-only economic context, not a risk-matched long-short benchmark."""
    from .signals import decision_pairs
    dates, rows = [], []
    for i, j in decision_pairs(returns.index):
        available = returns.iloc[i].notna().to_numpy()
        rows.append(available / available.sum())
        dates.append(returns.index[j])
    return pd.DataFrame(rows, index=pd.DatetimeIndex(dates), columns=returns.columns)

