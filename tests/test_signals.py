import numpy as np
import pandas as pd
import pytest

from alpha_research.signals import SignalSpec, construct_weights, decision_pairs, momentum_score


def panel(days=300, assets=49):
    rng = np.random.default_rng(8)
    return pd.DataFrame(rng.normal(0, .01, (days, assets)),
                        index=pd.bdate_range("2000-01-03", periods=days),
                        columns=[f"A{i:02}" for i in range(assets)])


def test_momentum_window_and_skip_are_explicit():
    r = pd.DataFrame({"a": [.01, .02, .03, .04, .05]})
    s = momentum_score(r, SignalSpec("m", 4, 1, 1))
    np.testing.assert_allclose(s.iloc[4, 0], np.log1p([.02, .03, .04]).sum())


def test_reversal_negates_momentum():
    r = panel()
    np.testing.assert_allclose(momentum_score(r, SignalSpec("r", 21, 0, -1)),
                              -momentum_score(r, SignalSpec("m", 21, 0, 1)), equal_nan=True)


def test_signal_prefix_invariance():
    r = panel()
    changed = r.copy()
    changed.iloc[200:] += .5
    spec = SignalSpec("m", 126, 21, 1)
    pd.testing.assert_frame_equal(momentum_score(r, spec).iloc[:200],
                                  momentum_score(changed, spec).iloc[:200])


@pytest.mark.parametrize("weighting", ["equal", "inverse_volatility"])
def test_weights_have_balanced_legs_and_target_gross(weighting):
    scores = pd.Series(np.arange(49), index=[f"A{i}" for i in range(49)])
    vol = pd.Series(np.linspace(.01, .03, 49), index=scores.index)
    w = construct_weights(scores, vol, weighting)
    np.testing.assert_allclose(w.sum(), 0, atol=1e-15)
    np.testing.assert_allclose(w.abs().sum(), 1)
    assert (w > 0).sum() == (w < 0).sum() == 9


def test_equal_score_ties_are_deterministic_under_column_permutation():
    scores = pd.Series(1., index=[f"A{i:02}" for i in range(49)])
    vol = scores * .01
    w = construct_weights(scores, vol)
    permutation = np.random.default_rng(6).permutation(49)
    shuffled = construct_weights(scores.iloc[permutation], vol.iloc[permutation])
    pd.testing.assert_series_equal(w.sort_index(), shuffled.sort_index())


def test_missing_features_do_not_get_positions():
    scores = pd.Series(np.arange(49), dtype=float)
    scores.iloc[:3] = np.nan
    w = construct_weights(scores, pd.Series(.01, index=scores.index))
    assert (w.iloc[:3] == 0).all()


def test_insufficient_universe_goes_flat():
    scores = pd.Series(np.arange(10))
    assert construct_weights(scores, scores * 0 + .01).abs().sum() == 0


def test_execution_is_next_trading_close():
    dates = pd.to_datetime(["2024-01-30", "2024-01-31", "2024-02-01", "2024-02-02"])
    assert decision_pairs(dates) == [(1, 2)]


def test_invalid_skip_rejected():
    with pytest.raises(ValueError):
        SignalSpec("bad", 21, 21, 1)

