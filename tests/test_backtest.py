import numpy as np
import pandas as pd
import pytest

from alpha_research.backtest import backtest, rebalance_cost


def make_data():
    index = pd.bdate_range("2020-01-01", periods=5)
    r = pd.DataFrame([[.4, -.4], [.1, 0], [0, -.1], [.02, -.02], [0, 0]], index=index, columns=["a", "b"])
    schedule = pd.DataFrame([[.5, -.5]], index=index[:1], columns=r.columns)
    return r, schedule


def test_trade_cannot_earn_the_return_that_preceded_execution():
    r, schedule = make_data()
    result = backtest(r, schedule, cost_bps=0)
    assert result.iloc[0].net_return == 0
    np.testing.assert_allclose(result.iloc[1].net_return, .05)


def test_cash_and_holdings_compound_consistently():
    r, schedule = make_data()
    result = backtest(r, schedule, cost_bps=0)
    long_value = .5 * np.prod(1 + r.a.iloc[1:])
    short_value = -.5 * np.prod(1 + r.b.iloc[1:])
    np.testing.assert_allclose(result.nav.iloc[-1], 1 + long_value + short_value)


def test_opening_transaction_cost_has_exact_post_cost_target():
    c = .01
    cost, turnover = rebalance_cost([0, 0], [.5, -.5], c)
    np.testing.assert_allclose(cost, c / (1 + c), atol=1e-13)
    np.testing.assert_allclose(cost, c * turnover)


def test_final_liquidation_is_charged():
    r, schedule = make_data()
    a, b = backtest(r, schedule, 10, liquidate=True), backtest(r, schedule, 10, liquidate=False)
    assert a.nav.iloc[-1] < b.nav.iloc[-1]
    assert a.iloc[-1].gross_exposure == 0
    assert a.iloc[-1].turnover > 0


def test_turnover_uses_drifted_holdings_not_previous_targets():
    cost, turnover = rebalance_cost([.55, -.45], [.5, -.5], 0)
    np.testing.assert_allclose(turnover, .1)
    assert cost == 0


def test_future_return_changes_cannot_change_prefix():
    r, schedule = make_data()
    changed = r.copy()
    changed.iloc[3:] = .8
    a, b = backtest(r, schedule, 10), backtest(changed, schedule, 10)
    pd.testing.assert_frame_equal(a.iloc[:3], b.iloc[:3])


def test_start_flat_for_separate_holdout():
    r, schedule = make_data()
    result = backtest(r, schedule, start=r.index[2], cost_bps=0)
    assert (result.net_return == 0).all()


def test_missing_held_return_raises_instead_of_silent_imputation():
    r, schedule = make_data()
    r.iloc[2, 0] = np.nan
    with pytest.raises(ValueError, match="Missing return"):
        backtest(r, schedule)


def test_missing_unheld_return_does_not_change_nav():
    r, schedule = make_data()
    r.iloc[0, 0] = np.nan
    result = backtest(r, schedule, 0)
    assert result.nav.iloc[0] == 1


def test_self_financing_cost_equation_for_general_weights():
    old, target, c = np.array([.7, -.3]), np.array([.4, -.6]), .003
    cost, turnover = rebalance_cost(old, target, c)
    np.testing.assert_allclose(cost, c * np.abs(target * (1 - cost) - old).sum(), atol=1e-13)
    np.testing.assert_allclose(turnover, cost / c)


def test_feasible_cost_root_survives_an_intermediate_iterate_above_equity():
    cost, turnover = rebalance_cost([-.9], [1.0], .6)
    np.testing.assert_allclose(cost, .7125, atol=1e-13)
    np.testing.assert_allclose(turnover, 1.1875, atol=1e-13)


def test_near_boundary_contraction_uses_bracketed_root_fallback():
    c = .999
    cost, turnover = rebalance_cost([-.001], [1.0], c)
    np.testing.assert_allclose(cost, c * 1.001 / (1 + c), atol=1e-13)
    np.testing.assert_allclose(cost, c * turnover, atol=1e-13)


@pytest.mark.parametrize("old", [[-2.0], [-2.1]])
def test_truly_unaffordable_liquidation_is_rejected(old):
    with pytest.raises(ValueError, match="exhaust portfolio equity"):
        rebalance_cost(old, [0.0], .5)

