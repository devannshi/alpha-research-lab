"""Known-null demonstration of selection-induced false positives."""
import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.stats import norm


def _null_statistics(rng, observations, candidates, ar_coefficient, correlation, lags):
    burn = 200
    common = rng.normal(size=(observations + burn, 1))
    independent = rng.normal(size=(observations + burn, candidates))
    innovations = np.sqrt(correlation) * common + np.sqrt(1 - correlation) * independent
    sample = lfilter([np.sqrt(1 - ar_coefficient**2)], [1, -ar_coefficient], innovations, axis=0)[burn:]
    mean = sample.mean(axis=0)
    u = sample - mean
    lrv = np.sum(u*u, axis=0) / observations
    for lag in range(1, lags + 1):
        lrv += 2 * (1 - lag / (lags + 1)) * np.sum(u[lag:] * u[:-lag], axis=0) / observations
    return mean / np.sqrt(np.maximum(lrv, 1e-15) / observations)


def run_null_experiment(replicates=1000, candidates=50, observations=756,
                        seed=20261117, ar_coefficient=.2, correlation=.35, lags=21):
    """All strategies have exactly zero mean, common correlation, and AR(1) dependence.

    A separate calibration stream supplies the oracle known-null 95% max cutoff.
    It is illustrative Monte Carlo calibration, not a substitute for the empirical
    stationary-bootstrap test or a claim of exact unknown-distribution coverage.
    """
    if not 0 <= correlation < 1 or not abs(ar_coefficient) < 1:
        raise ValueError("Invalid null dependence")
    calibration_seed, evaluation_seed = np.random.SeedSequence([seed, 44]).spawn(2)
    calibration_rng, evaluation_rng = np.random.default_rng(calibration_seed), np.random.default_rng(evaluation_seed)
    calibration_size = max(1000, replicates * 2)
    calibration = np.array([_null_statistics(calibration_rng, observations, candidates,
                                             ar_coefficient, correlation, lags).max()
                            for _ in range(calibration_size)])
    max_cutoff = float(np.quantile(calibration, .95))
    naive_cutoff, bonferroni_cutoff = float(norm.isf(.05)), float(norm.isf(.05 / candidates))
    rows = []
    for rep in range(replicates):
        t = _null_statistics(evaluation_rng, observations, candidates, ar_coefficient, correlation, lags)
        maximum = float(t.max())
        rows.append({"replicate": rep, "best_hac_t": maximum,
                     "naive_reject": maximum > naive_cutoff,
                     "bonferroni_reject": maximum > bonferroni_cutoff,
                     "known_null_max_reject": maximum > max_cutoff,
                     "prespecified_single_reject": float(t[0]) > naive_cutoff})
    metadata = {"replicates": replicates, "candidates": candidates, "observations": observations,
                "ar_coefficient": ar_coefficient, "cross_candidate_correlation": correlation,
                "calibration_replicates": calibration_size, "naive_cutoff": naive_cutoff,
                "bonferroni_cutoff": bonferroni_cutoff, "known_null_max_cutoff": max_cutoff,
                "calibration_and_evaluation_rng_streams": "independent SeedSequence children"}
    return pd.DataFrame(rows), metadata

