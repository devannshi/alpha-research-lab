"""Chronological candidate selection with explicit decision cutoffs."""
import numpy as np
import pandas as pd

from .backtest import backtest
from .inference import performance_metrics


def select_candidate(candidate_results, selection_end, hac_lags=21):
    """Rank only returns available on or before selection_end; deterministic ties."""
    cutoff = pd.Timestamp(selection_end)
    rows = []
    for name, frame in sorted(candidate_results.items()):
        available = frame.loc[:cutoff]
        if len(available) < 20:
            raise ValueError("Insufficient validation observations")
        metrics = performance_metrics(available, hac_lags)
        rows.append({"candidate": name, "last_observation": str(available.index.max().date()), **metrics})
    ranking = pd.DataFrame(rows).sort_values(["sharpe", "candidate"], ascending=[False, True]).reset_index(drop=True)
    return str(ranking.iloc[0].candidate), ranking


def annual_selector(returns, schedules, protocol, first_year=2005, last_year=2025):
    """Five trailing calendar years score each candidate; one subsequent year trades.

    Scoring windows start flat and pay their own entry and liquidation costs.
    The eventual combined strategy carries actual holdings between yearly choices,
    so changing candidate incurs real turnover rather than splicing return curves.
    """
    choices, diagnostics = {}, []
    years = protocol["adaptive_selection_trailing_years"]
    c = protocol["primary_one_way_cost_bps"]
    for year in range(first_year, last_year + 1):
        start, end = f"{year-years}-01-01", f"{year-1}-12-31"
        validation = {name: backtest(returns, schedule, c, start, end)
                      for name, schedule in schedules.items()}
        winner, ranking = select_candidate(validation, end, protocol["hac_lags"])
        choices[year] = winner
        rank = ranking.copy()
        rank["trade_year"], rank["validation_start"], rank["validation_end"] = year, start, end
        diagnostics.append(rank)
    rows, dates, chosen = [], [], []
    for date in next(iter(schedules.values())).index:
        if date.year not in choices:
            continue
        candidate = choices[date.year]
        rows.append(schedules[candidate].loc[date].to_numpy())
        dates.append(date)
        chosen.append({"execution_date": date, "candidate": candidate,
                       "selection_information_cutoff": f"{date.year-1}-12-31"})
    combined = pd.DataFrame(rows, index=pd.DatetimeIndex(dates, name="date"), columns=returns.columns)
    return combined, pd.concat(diagnostics, ignore_index=True), pd.DataFrame(chosen)


def information_coefficient(returns, scores, horizon=21, min_eligible=40):
    """Spearman rank IC for a month-end score versus execution-aligned forward return.

    Decision close i -> execution close i+1 -> label returns i+2 through i+1+horizon.
    The complete label must exist; period-specific inference additionally requires
    label_end to lie inside the period. Forward returns are used only for diagnosis.
    """
    from scipy.stats import rankdata

    from .signals import decision_pairs
    rows = []
    for decision_i, execution_i in decision_pairs(returns.index):
        begin, end = execution_i + 1, execution_i + 1 + horizon
        if end > len(returns):
            continue
        forward = np.expm1(np.log1p(returns.iloc[begin:end]).sum(axis=0, min_count=horizon))
        score = scores.iloc[decision_i]
        eligible = np.isfinite(score) & np.isfinite(forward)
        if eligible.sum() < min_eligible:
            continue
        a, b = rankdata(score[eligible]), rankdata(forward[eligible])
        if np.std(a) == 0 or np.std(b) == 0:
            continue
        rows.append({"decision_date": returns.index[decision_i],
                     "execution_date": returns.index[execution_i],
                     "label_start": returns.index[begin], "label_end": returns.index[end - 1],
                     "rank_ic": float(np.corrcoef(a, b)[0, 1]),
                     "industries": int(eligible.sum())})
    return pd.DataFrame(rows)

