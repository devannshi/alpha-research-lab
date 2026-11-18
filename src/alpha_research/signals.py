"""Declared cross-sectional predictors and past-only portfolio construction."""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SignalSpec:
    name: str
    lookback: int
    skip: int
    direction: int

    def __post_init__(self):
        if self.lookback < 1 or not 0 <= self.skip < self.lookback or self.direction not in {-1, 1}:
            raise ValueError("Invalid signal specification")


def momentum_score(returns, spec):
    """Use returns t-lookback+1 through t-skip, inclusive.

    lookback=252, skip=21 means a 231-observation window ending 21 days ago.
    A positive score always means the industry is favored for a long position.
    """
    logs = np.log1p(returns)
    width = spec.lookback - spec.skip
    return spec.direction * logs.rolling(width, min_periods=width).sum().shift(spec.skip)


def construct_weights(scores, volatility, weighting="equal", tail_fraction=.2,
                      gross_exposure=1.0, volatility_floor=.001, min_eligible=40):
    """Each leg has half of target gross exposure; deterministic tie breaking."""
    scores = pd.Series(scores, dtype=float)
    volatility = pd.Series(volatility, index=scores.index, dtype=float)
    if weighting not in {"equal", "inverse_volatility"}:
        raise ValueError("Unknown weighting rule")
    if not 0 < tail_fraction <= .5 or gross_exposure < 0 or volatility_floor <= 0:
        raise ValueError("Invalid portfolio controls")
    eligible = np.isfinite(scores) & np.isfinite(volatility) & (volatility >= 0)
    weights = pd.Series(0.0, index=scores.index)
    names = scores.index[eligible]
    if len(names) < min_eligible:
        return weights
    count = max(1, int(np.floor(len(names) * tail_fraction)))
    order = np.lexsort((names.astype(str), scores.loc[names].to_numpy()))
    shorts, longs = names[order[:count]], names[order[-count:]]
    for group, sign in [(longs, 1), (shorts, -1)]:
        raw = (np.ones(len(group)) if weighting == "equal"
               else 1 / np.maximum(volatility.loc[group].to_numpy(), volatility_floor))
        weights.loc[group] = sign * .5 * gross_exposure * raw / raw.sum()
    return weights


def decision_pairs(index):
    """Month-end decision, next available trading CLOSE execution."""
    month = index.to_period("M")
    return [(i, i + 1) for i in range(len(index) - 1) if month[i] != month[i + 1]]


def build_schedules(returns, protocol):
    vol = returns.rolling(protocol["volatility_lookback"],
                           min_periods=protocol["volatility_lookback"]).std(ddof=1)
    pairs = decision_pairs(returns.index)
    schedules, score_frames, records = {}, {}, []
    for entry in protocol["signals"]:
        spec = SignalSpec(**entry)
        scores = momentum_score(returns, spec)
        score_frames[spec.name] = scores
        for weighting in protocol["weighting_rules"]:
            candidate = f"{spec.name}__{weighting}"
            rows, dates = [], []
            for decision_i, execution_i in pairs:
                weight = construct_weights(
                    scores.iloc[decision_i], vol.iloc[decision_i], weighting,
                    protocol["tail_fraction"], protocol["gross_exposure"],
                    protocol["volatility_floor_daily"], protocol["minimum_eligible_industries"])
                rows.append(weight.to_numpy())
                dates.append(returns.index[execution_i])
                records.append({"candidate": candidate,
                                "decision_date": returns.index[decision_i],
                                "execution_date": returns.index[execution_i],
                                "eligible_industries": int((scores.iloc[decision_i].notna()
                                                            & vol.iloc[decision_i].notna()).sum()),
                                "gross_target": float(weight.abs().sum()),
                                "net_target": float(weight.sum())})
            schedules[candidate] = pd.DataFrame(rows, index=pd.DatetimeIndex(dates, name="date"),
                                                 columns=returns.columns)
    return schedules, score_frames, pd.DataFrame(records)

