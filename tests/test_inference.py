import numpy as np

from alpha_research.inference import (
    block_bootstrap_interval,
    hac_mean,
    max_statistic_test,
    stationary_bootstrap_indices,
)


def test_hac_zero_lag_matches_population_variance_mean_formula():
    x = np.arange(1., 101.)
    result = hac_mean(x, lags=0)
    np.testing.assert_allclose(result["hac_se"], x.std(ddof=0) / np.sqrt(len(x)))


def test_hac_positive_autocorrelation_increases_uncertainty():
    rng = np.random.default_rng(5)
    x = np.convolve(rng.normal(size=1100), np.ones(10), mode="valid")
    assert hac_mean(x, 21)["hac_se"] > 2 * hac_mean(x, 0)["hac_se"]


def test_stationary_resample_indices_are_valid_and_reproducible():
    a = stationary_bootstrap_indices(100, 21, np.random.default_rng(8))
    b = stationary_bootstrap_indices(100, 21, np.random.default_rng(8))
    np.testing.assert_array_equal(a, b)
    assert len(a) == 100 and a.min() >= 0 and a.max() < 100
    assert np.mean(np.diff(a) % 100 == 1) > .7


def test_max_adjustment_cannot_improve_individual_p_value():
    X = np.random.default_rng(6).normal(size=(250, 4)) + .02
    out = max_statistic_test(X, replicates=199, seed=7)
    assert np.all(out["adjusted_p"] >= out["individual_bootstrap_p"])
    assert 0 < out["global_p"] <= 1


def test_max_test_is_candidate_permutation_invariant():
    X = np.random.default_rng(6).normal(size=(250, 4))
    a = max_statistic_test(X, replicates=199, seed=8)
    b = max_statistic_test(X[:, [2, 1, 3, 0]], replicates=199, seed=8)
    np.testing.assert_allclose(a["bootstrap_maxima"], b["bootstrap_maxima"])


def test_declared_positive_mean_has_power():
    X = np.random.default_rng(9).normal(size=(800, 3))
    X[:, 0] += .3
    out = max_statistic_test(X, replicates=199, seed=7)
    assert out["adjusted_p"][0] < .025


def test_zero_series_has_zero_hac_score():
    out = hac_mean(np.zeros(100))
    assert out["mean"] == out["hac_se"] == out["hac_t"] == 0


def test_bootstrap_interval_contains_symmetric_sample_mean():
    x = np.linspace(-1, 1, 101)
    result = block_bootstrap_interval(x, replicates=199, block_length=5)
    assert result["lower"] < 0 < result["upper"]

