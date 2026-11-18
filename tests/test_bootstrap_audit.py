import numpy as np
from scipy.stats import norm

from alpha_research.bootstrap_audit import (
    gaussian_max_cutoff,
    matrix_hac_scales,
    null_sample,
    paired_max_tests,
    true_mean_variance,
    wilson_interval,
)
from alpha_research.inference import hac_mean, max_statistic_test


def test_batched_hac_matches_independent_scalar_implementation():
    sample = np.random.default_rng(617).normal(size=(3, 117, 4))
    expected = np.array([[hac_mean(sample[b, :, j], 13)["hac_se"]
                          for j in range(4)] for b in range(3)])
    np.testing.assert_allclose(matrix_hac_scales(sample, 13), expected, rtol=1e-13)


def test_audit_fixed_scale_result_is_the_actual_primary_function():
    sample = null_sample(80, 3, 719)
    original = max_statistic_test(sample, 99, 7, 5, 819)
    paired = paired_max_tests(sample, 99, 7, 5, 819, batch_size=16)
    assert paired["fixed_scale_p"] == original["global_p"]
    assert paired["observed_max"] == original["observed_max"]


def test_studentized_result_is_invariant_to_batch_partition():
    sample = null_sample(80, 3, 720)
    a = paired_max_tests(sample, 99, 7, 5, 820, batch_size=7)
    b = paired_max_tests(sample, 99, 7, 5, 820, batch_size=32)
    assert a == b


def test_null_generator_has_time_dependence_and_cross_column_correlation():
    sample = null_sample(30000, 6, 721)
    serial = np.mean([np.corrcoef(sample[1:, j], sample[:-1, j])[0, 1] for j in range(6)])
    cross = np.corrcoef(sample.T)[np.triu_indices(6, 1)].mean()
    assert abs(serial - .2) < .025
    assert abs(cross - .35) < .025


def test_exact_gaussian_oracle_matches_independent_candidates_and_review_reference():
    independent = gaussian_max_cutoff(6, 0)
    np.testing.assert_allclose(independent, norm.ppf(.95 ** (1 / 6)), atol=1e-10)
    np.testing.assert_allclose(gaussian_max_cutoff(6, .35), 2.337617783033043, atol=1e-10)


def test_oracle_mean_variance_matches_full_ar_covariance():
    n, rho = 32, .2
    covariance = rho ** np.abs(np.arange(n)[:, None] - np.arange(n))
    np.testing.assert_allclose(true_mean_variance(n, rho), covariance.sum() / n**2)


def test_wilson_interval_contains_frequency_and_stays_in_unit_interval():
    for count in (0, 5, 50, 100):
        low, high = wilson_interval(count, 100)
        assert -1e-15 <= low <= high <= 1 + 1e-15
        assert low - 1e-15 <= count / 100 <= high + 1e-15
