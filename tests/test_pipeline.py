import numpy as np
import pandas as pd

from alpha_research.inference import max_statistic_test
from alpha_research.selection import annual_selector
from alpha_research.signals import build_schedules


def test_complete_weight_schedule_is_prefix_causal():
    dates = pd.bdate_range("2000-01-03", periods=400)
    r = pd.DataFrame(np.random.default_rng(3).normal(0, .01, (400, 8)), index=dates)
    protocol = {"volatility_lookback": 21, "signals": [
        {"name": "m", "lookback": 63, "skip": 5, "direction": 1}],
        "weighting_rules": ["equal", "inverse_volatility"], "tail_fraction": .25,
        "gross_exposure": 1., "volatility_floor_daily": .001, "minimum_eligible_industries": 6}
    original, _, log = build_schedules(r, protocol)
    changed = r.copy()
    changed.iloc[250:] += .2
    altered, _, _ = build_schedules(changed, protocol)
    for name in original:
        pd.testing.assert_frame_equal(original[name].loc[:dates[249]], altered[name].loc[:dates[249]])
    assert (log.execution_date > log.decision_date).all()


def test_annual_selection_does_not_read_its_trading_year():
    dates = pd.bdate_range("2004-01-01", "2005-12-31")
    r = pd.DataFrame(np.random.default_rng(33).normal(0, .01, (len(dates), 2)), index=dates, columns=["a", "b"])
    trade_dates = dates[dates.to_period("M") != pd.Series(dates.to_period("M")).shift(1).to_numpy()]
    schedules = {"a": pd.DataFrame(np.tile([.5, -.5], (len(trade_dates), 1)), index=trade_dates, columns=r.columns),
                 "b": pd.DataFrame(np.tile([-.5, .5], (len(trade_dates), 1)), index=trade_dates, columns=r.columns)}
    protocol = {"adaptive_selection_trailing_years": 1, "primary_one_way_cost_bps": 10, "hac_lags": 5}
    a, scores, choices = annual_selector(r, schedules, protocol, first_year=2005, last_year=2005)
    changed = r.copy()
    changed.loc["2005":] *= -10
    b, _, choices2 = annual_selector(changed, schedules, protocol, first_year=2005, last_year=2005)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(choices, choices2)
    assert (pd.to_datetime(scores.last_observation) <= "2004-12-31").all()


def test_perfectly_duplicate_candidate_does_not_change_max_penalty():
    X = np.random.default_rng(9).normal(size=(200, 3))
    a = max_statistic_test(X, replicates=199, seed=80)
    b = max_statistic_test(np.column_stack([X, X[:, 0]]), replicates=199, seed=80)
    np.testing.assert_allclose(a["bootstrap_maxima"], b["bootstrap_maxima"])
    np.testing.assert_allclose(a["adjusted_p"], b["adjusted_p"][:3])

