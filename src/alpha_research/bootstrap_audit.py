"""Separate null-size audit: preserve the original empirical inference unchanged.

Compare its actual fixed-scale procedure with a predeclared bootstrap-t variant
on shared resamples. This module is never invoked by the primary research run.
"""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.signal import lfilter
from scipy.stats import norm

from .inference import max_statistic_test, stationary_bootstrap_indices


def null_sample(observations, candidates, seed, ar=.2, correlation=.35, burn=200):
    rng = np.random.default_rng(seed)
    common = rng.normal(size=(observations + burn, 1))
    separate = rng.normal(size=(observations + burn, candidates))
    innovations = np.sqrt(correlation) * common + np.sqrt(1 - correlation) * separate
    return lfilter([np.sqrt(1 - ar**2)], [1, -ar], innovations, axis=0)[burn:]


def matrix_hac_scales(values, lags=21):
    """Original Bartlett HAC SE, vectorized over columns and optional batches."""
    x = np.asarray(values, float)
    n = x.shape[-2]
    u = x - x.mean(axis=-2, keepdims=True)
    lrv = np.sum(u * u, axis=-2) / n
    used = min(lags, n - 1)
    for lag in range(1, used + 1):
        lrv += 2 * (1 - lag / (used + 1)) * np.sum(
            u[..., lag:, :] * u[..., :-lag, :], axis=-2) / n
    return np.sqrt(np.maximum(lrv, 0) / n)


def paired_max_tests(sample, replicates, block_length, lags, seed, batch_size=32):
    """Call the original test, then studentize the identical bootstrap draws."""
    fixed = max_statistic_test(sample, replicates, block_length, lags, seed)
    x = np.asarray(sample, float)
    centered = x - x.mean(axis=0)
    rng = np.random.default_rng(seed)
    maxima = np.empty(replicates)
    for start in range(0, replicates, batch_size):
        count = min(batch_size, replicates - start)
        index = np.stack([stationary_bootstrap_indices(len(x), block_length, rng)
                          for _ in range(count)])
        resampled = centered[index]
        scales = matrix_hac_scales(resampled, lags)
        if np.any(scales <= 1e-16):
            raise ValueError("Degenerate bootstrap HAC scale in audit")
        statistic = resampled.mean(axis=1) / scales
        maxima[start:start + count] = np.maximum(0, statistic.max(axis=1))
    studentized_p = (1 + np.count_nonzero(maxima >= fixed["observed_max"])) / (replicates + 1)
    return {"fixed_scale_p": fixed["global_p"], "studentized_p": float(studentized_p),
            "observed_max": fixed["observed_max"]}


def gaussian_max_cutoff(candidates, correlation, probability=.95):
    """Exact equicorrelated standard-Gaussian max CDF by one-dimensional quadrature."""
    def cdf(cutoff):
        value, _ = quad(lambda z: norm.pdf(z) * norm.cdf(
            (cutoff - np.sqrt(correlation) * z) / np.sqrt(1 - correlation))**candidates,
            -11, 11, epsabs=1e-11)
        return value
    return brentq(lambda cutoff: cdf(cutoff) - probability, -5, 8, xtol=1e-12)


def true_mean_variance(observations, ar):
    lags = np.arange(1, observations)
    return float((observations + 2 * np.sum((observations - lags) * ar**lags)) /
                 observations**2)


def wilson_interval(rejections, trials):
    z = float(norm.ppf(.975))
    p = rejections / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    half = z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials**2)) / denominator
    return float(center - half), float(center + half)


def run_audit(protocol_path, output):
    started = time.perf_counter()
    protocol_path, output = Path(protocol_path), Path(output)
    design = json.loads(protocol_path.read_text())
    output.mkdir(parents=True, exist_ok=True)
    cutoff = gaussian_max_cutoff(design["candidates"], design["correlation"], 1 - design["alpha"])
    rows = []
    for observations in design["sample_sizes"]:
        variance = true_mean_variance(observations, design["ar"])
        for trial in range(design["outer_trials"]):
            dataset_seed = design["dataset_seed_base"] + trial
            bootstrap_seed = design["bootstrap_seed_base"] + trial
            x = null_sample(observations, design["candidates"], dataset_seed,
                            design["ar"], design["correlation"], design["burn"])
            tests = paired_max_tests(x, design["bootstrap_replicates"],
                                     design["block_length"], design["hac_lags"], bootstrap_seed)
            oracle_max = float(x.mean(axis=0).max() / np.sqrt(variance))
            rows.append({"observations": observations, "trial": trial,
                         "dataset_seed": dataset_seed, "bootstrap_seed": bootstrap_seed,
                         **tests, "oracle_max": oracle_max,
                         "fixed_scale_reject": tests["fixed_scale_p"] <= design["alpha"],
                         "studentized_reject": tests["studentized_p"] <= design["alpha"],
                         "known_gaussian_reject": oracle_max > cutoff})
            if (trial + 1) % 100 == 0:
                print(f"Audit n={observations}: {trial + 1}/{design['outer_trials']}", flush=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "trials.csv", index=False)
    summaries, differences = [], []
    for observations, block in frame.groupby("observations"):
        for method in ("fixed_scale", "studentized", "known_gaussian"):
            count = int(block[f"{method}_reject"].sum())
            lower, upper = wilson_interval(count, len(block))
            summaries.append({"observations": observations, "method": method,
                              "rejections": count, "outer_trials": len(block),
                              "rejection_rate": count / len(block), "wilson_low": lower,
                              "wilson_high": upper, "nominal_alpha": design["alpha"]})
        paired = block.studentized_reject.astype(int) - block.fixed_scale_reject.astype(int)
        half = float(norm.ppf(.975) * paired.std(ddof=1) / np.sqrt(len(block)))
        differences.append({"observations": observations, "student_minus_fixed": paired.mean(),
                            "paired_normal_low": paired.mean() - half,
                            "paired_normal_high": paired.mean() + half,
                            "fixed_only_rejections": int((paired == -1).sum()),
                            "student_only_rejections": int((paired == 1).sum())})
    pd.DataFrame(summaries).to_csv(output / "summary.csv", index=False)
    pd.DataFrame(differences).to_csv(output / "paired_differences.csv", index=False)
    source = Path(__file__).parent
    manifest = {"design": design, "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "runtime_seconds": time.perf_counter() - started,
                "known_gaussian_max_cutoff": cutoff,
                "source_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                                  for name in ("bootstrap_audit.py", "inference.py")},
                "artifact_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in output.glob("*.csv")}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Audit complete in {manifest['runtime_seconds']:.1f}s", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", default="bootstrap_audit_protocol.json")
    parser.add_argument("--output", default="results/bootstrap_audit")
    args = parser.parse_args()
    run_audit(args.protocol, args.output)


if __name__ == "__main__":
    main()
