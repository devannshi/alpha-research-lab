"""HAC mean inference and dependence-preserving family-wise maximum statistics."""
import numpy as np
from scipy.stats import norm


def hac_mean(values, lags=21):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < 3 or not np.all(np.isfinite(x)) or lags < 0:
        raise ValueError("Need at least three finite scalar observations")
    n = len(x)
    u = x - x.mean()
    lrv = float(u @ u / n)
    used = min(int(lags), n - 1)
    for lag in range(1, used + 1):
        gamma = float(u[lag:] @ u[:-lag] / n)
        lrv += 2 * (1 - lag / (used + 1)) * gamma
    se = np.sqrt(max(lrv, 0) / n)
    t_stat = float(x.mean() / se) if se > 0 else (0.0 if x.mean() == 0 else np.sign(x.mean()) * np.inf)
    return {"mean": float(x.mean()), "hac_se": float(se), "hac_t": t_stat,
            "p_one_sided": float(norm.sf(t_stat)),
            "lower": float(x.mean() - norm.ppf(.975) * se),
            "upper": float(x.mean() + norm.ppf(.975) * se), "n": n, "lags": used}


def performance_metrics(backtest_frame, hac_lags=21):
    r = backtest_frame.net_return.to_numpy(float)
    n, mean, sd = len(r), float(np.mean(r)), float(np.std(r, ddof=1))
    equity = np.r_[1, np.cumprod(1 + r)]
    drawdown = equity / np.maximum.accumulate(equity) - 1
    inference = hac_mean(r, hac_lags)
    annual_turnover = float(backtest_frame.turnover.sum() * 252 / n)
    return {"annual_mean": 252 * mean, "annual_volatility": np.sqrt(252) * sd,
            "sharpe": np.sqrt(252) * mean / sd if sd > 0 else 0.0,
            "cagr": float(equity[-1] ** (252 / n) - 1), "total_return": float(equity[-1] - 1),
            "max_drawdown": float(drawdown.min()), "annual_turnover": annual_turnover,
            "average_gross_exposure": float(backtest_frame.gross_exposure.mean()),
            "mean_absolute_net_exposure": float(backtest_frame.net_exposure.abs().mean()),
            **inference}


def stationary_bootstrap_indices(n, mean_block_length, rng):
    if n < 1 or mean_block_length < 1:
        raise ValueError("Positive sample size and block length >= 1 required")
    pieces, remaining = [], n
    while remaining:
        length = min(int(rng.geometric(1 / mean_block_length)), remaining)
        start = int(rng.integers(n))
        pieces.append((start + np.arange(length)) % n)
        remaining -= length
    return np.concatenate(pieces)


def max_statistic_test(returns_matrix, replicates=2000, block_length=21, lags=21, seed=20261117):
    """One-sided, single-step, fixed-scale centered stationary-bootstrap max test.

    Null: every declared candidate's expected net return is <= 0. Shared block
    indices preserve contemporaneous cross-strategy dependence. Centering all
    columns at zero is the least-favorable null. HAC scales are fixed at original
    estimates; this is not advertised as Hansen SPA, DSR, CSCV or exact finite-
    sample inference. Standard mixing/stationarity approximations are required.
    """
    X = np.asarray(returns_matrix, float)
    if X.ndim != 2 or X.shape[0] < 20 or not np.all(np.isfinite(X)) or replicates < 99:
        raise ValueError("Need a finite observation-by-candidate matrix and >=99 replicates")
    n, m = X.shape
    means = X.mean(axis=0)
    scales = np.array([hac_mean(X[:, j], lags)["hac_se"] for j in range(m)])
    if np.any(scales <= 1e-16):
        raise ValueError("All candidate columns need positive HAC uncertainty")
    observed = means / scales
    centered = X - means
    rng = np.random.default_rng(seed)
    maximum, raw_samples = np.empty(replicates), np.empty((replicates, m))
    for b in range(replicates):
        index = stationary_bootstrap_indices(n, block_length, rng)
        raw_samples[b] = centered[index].mean(axis=0) / scales
        maximum[b] = max(0.0, float(raw_samples[b].max()))
    adjusted = (1 + (maximum[:, None] >= observed).sum(axis=0)) / (replicates + 1)
    naive_bootstrap = (1 + (raw_samples >= observed).sum(axis=0)) / (replicates + 1)
    observed_max = max(0.0, float(observed.max()))
    global_p = float((1 + np.count_nonzero(maximum >= observed_max)) / (replicates + 1))
    return {"observed_t": observed, "adjusted_p": adjusted, "individual_bootstrap_p": naive_bootstrap,
            "global_p": global_p, "observed_max": observed_max,
            "bootstrap_maxima": maximum, "replicates": replicates,
            "block_length": block_length, "hac_lags": lags}


def block_bootstrap_interval(values, replicates=2000, block_length=21, seed=917):
    x = np.asarray(values, float)
    if x.ndim != 1 or not np.all(np.isfinite(x)) or len(x) < 20:
        raise ValueError("Need a finite time series")
    rng = np.random.default_rng(seed)
    means = np.array([x[stationary_bootstrap_indices(len(x), block_length, rng)].mean()
                      for _ in range(replicates)])
    return {"mean": float(x.mean()), "lower": float(np.quantile(means, .025)),
            "upper": float(np.quantile(means, .975)), "replicates": replicates}

