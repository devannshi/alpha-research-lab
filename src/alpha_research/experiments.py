"""Execute the frozen research ledger without selecting on holdout outcomes."""
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy.stats import norm

from . import __version__
from .backtest import backtest, equal_weight_schedule
from .data import load_dataset
from .inference import block_bootstrap_interval, hac_mean, max_statistic_test, performance_metrics
from .null_experiment import run_null_experiment
from .selection import annual_selector, information_coefficient, select_candidate
from .signals import build_schedules


def _write(frame, path):
    frame.to_csv(path, index=False, float_format="%.12g")


def _wilson(rejections, n):
    p, z = rejections / n, norm.ppf(.975)
    center = (p + z*z / (2*n)) / (1 + z*z/n)
    radius = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return p, center - radius, center + radius


def run_research(root, output, profile="full", allow_revised=False):
    started = time.perf_counter()
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if profile not in {"quick", "full"}:
        raise ValueError("Choose quick or full profile")
    protocol_bytes = (root / "research_protocol.json").read_bytes()
    protocol = json.loads(protocol_bytes)
    protocol_hash = hashlib.sha256(protocol_bytes).hexdigest()
    full = profile == "full"
    B = protocol["bootstrap_replicates"] if full else 199
    null_reps = protocol["null_experiment_replicates"] if full else 100
    returns, source = load_dataset(root, allow_revised)
    returns = returns.loc["1969-01-01":protocol["data_cutoff"]]
    analyzed = returns.loc[protocol["development_start"]:]
    if analyzed.isna().any().any():
        raise ValueError("The frozen research period contains missing returns; inspect source revisions")
    source["analysis_cutoff"] = protocol["data_cutoff"]
    source["analysis_first_date"] = str(analyzed.index.min().date())
    source["analysis_last_date"] = str(analyzed.index.max().date())
    source["analysis_rows"] = len(analyzed)
    print(f"Source verified; {len(analyzed)} complete daily rows × {returns.shape[1]} industries", flush=True)
    schedules, scores, decision_log = build_schedules(returns, protocol)
    # Every weighting choice is recorded; schedules are source-data transformations,
    # not copies of the provider return panel.
    weight_rows = pd.concat([table.assign(candidate=name).reset_index() for name, table in schedules.items()], ignore_index=True)
    weight_rows = weight_rows[weight_rows.date >= protocol["development_start"]]
    _write(weight_rows, output / "target_weights.csv.gz")
    _write(decision_log[decision_log.execution_date >= protocol["development_start"]], output / "decision_log.csv.gz")
    c = protocol["primary_one_way_cost_bps"]
    period_results, ledger_rows = {}, []
    for period in ["development", "validation"]:
        start, end = protocol[f"{period}_start"], protocol[f"{period}_end"]
        period_results[period] = {}
        for name, schedule in schedules.items():
            result = backtest(returns, schedule, c, start, end)
            period_results[period][name] = result
            ledger_rows.append({"period": period, "candidate": name, "cost_bps": c,
                                **performance_metrics(result, protocol["hac_lags"])})
    winner, ranking = select_candidate(period_results["validation"], protocol["validation_end"], protocol["hac_lags"])
    selection = {"selected_candidate": winner, "selection_metric": protocol["selection_metric"],
                 "information_cutoff": protocol["validation_end"], "one_way_cost_bps": c,
                 "protocol_sha256": protocol_hash,
                 "selection_scope": "2005-2014 validation returns only; holdout not scored yet"}
    (output / "frozen_selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    _write(ranking, output / "validation_ranking.csv")
    print(f"Frozen validation selection: {winner}; now evaluating holdout", flush=True)
    hstart, hend = protocol["holdout_start"], protocol["holdout_end"]
    period_results["holdout"] = {}
    for name, schedule in schedules.items():
        result = backtest(returns, schedule, c, hstart, hend)
        period_results["holdout"][name] = result
        ledger_rows.append({"period": "holdout", "candidate": name, "cost_bps": c,
                            **performance_metrics(result, protocol["hac_lags"])})
    print("Running annual past-only selection and execution accounting", flush=True)
    adaptive_schedule, annual_scores, annual_choices = annual_selector(returns, schedules, protocol)
    adaptive = backtest(returns, adaptive_schedule, c, hstart, hend)
    period_results["holdout"]["adaptive_selector"] = adaptive
    ledger_rows.append({"period": "holdout", "candidate": "adaptive_selector", "cost_bps": c,
                        **performance_metrics(adaptive, protocol["hac_lags"])})
    _write(annual_scores, output / "annual_selection_scores.csv")
    _write(annual_choices, output / "annual_selection_choices.csv")
    daily = pd.concat([result.assign(period=period, candidate=name).reset_index()
                       for period, candidates in period_results.items()
                       for name, result in candidates.items()], ignore_index=True)
    _write(daily, output / "candidate_daily.csv.gz")
    ew = backtest(returns, equal_weight_schedule(returns), c, hstart, hend)
    benchmark_metrics = performance_metrics(ew, protocol["hac_lags"])
    _write(ew.reset_index(), output / "equal_weight_context.csv")
    holdout = period_results["holdout"]
    names = sorted(holdout)
    matrix = np.column_stack([holdout[name].net_return.to_numpy() for name in names])
    print(f"Testing all {len(names)} declared holdout procedures with {B} block replicates", flush=True)
    max_test = max_statistic_test(matrix, B, protocol["bootstrap_mean_block_length_days"],
                                  protocol["hac_lags"], protocol["seed"])
    inference_table = pd.DataFrame({"candidate": names, "hac_t": max_test["observed_t"],
                                    "individual_bootstrap_p": max_test["individual_bootstrap_p"],
                                    "family_adjusted_p": max_test["adjusted_p"]})
    _write(inference_table, output / "family_inference.csv")
    _write(pd.DataFrame({"replicate": range(B), "max_t": max_test["bootstrap_maxima"]}), output / "bootstrap_maxima.csv")
    block_rows = []
    for block_length in protocol["bootstrap_block_length_robustness"]:
        result = (max_test if block_length == protocol["bootstrap_mean_block_length_days"] else
                  max_statistic_test(matrix, B, block_length, protocol["hac_lags"], protocol["seed"] + block_length))
        selected_index = names.index(winner)
        block_rows.append({"mean_block_length": block_length, "replicates": B,
                           "global_family_p": result["global_p"],
                           "frozen_winner_adjusted_p": result["adjusted_p"][selected_index]})
    _write(pd.DataFrame(block_rows), output / "bootstrap_block_sensitivity.csv")
    winner_ci = block_bootstrap_interval(holdout[winner].net_return.to_numpy(), B,
                                         protocol["bootstrap_mean_block_length_days"], protocol["seed"] + 83)
    print("Computing IC, costs, subperiods and the known-null selection experiment", flush=True)
    ic_rows, ic_summary = [], []
    for signal, score in scores.items():
        ic = information_coefficient(returns, score, protocol["ic_forward_horizon_days"],
                                      protocol["minimum_eligible_industries"])
        ic["signal"] = signal
        ic_rows.append(ic)
        for period in ["development", "validation", "holdout"]:
            sub = ic[(ic.decision_date >= protocol[f"{period}_start"])
                     & (ic.label_end <= protocol[f"{period}_end"])]
            ic_summary.append({"signal": signal, "period": period,
                               **hac_mean(sub.rank_ic.to_numpy(), protocol["ic_hac_lags_months"])})
    _write(pd.concat(ic_rows, ignore_index=True), output / "information_coefficients.csv")
    _write(pd.DataFrame(ic_summary), output / "ic_summary.csv")
    cost_rows = []
    evaluated_schedules = {**schedules, "adaptive_selector": adaptive_schedule}
    for name, schedule in evaluated_schedules.items():
        for cost in protocol["cost_grid_bps"]:
            result = backtest(returns, schedule, cost, hstart, hend)
            cost_rows.append({"candidate": name, "cost_bps": cost,
                              **performance_metrics(result, protocol["hac_lags"])})
    costs = pd.DataFrame(cost_rows)
    _write(costs, output / "cost_sensitivity.csv")
    # First-order, explicitly approximate cost threshold. Exact tested costs are above.
    zero_cost = costs[costs.cost_bps == 0].copy()
    zero_cost["first_order_break_even_bps"] = np.maximum(0, zero_cost.annual_mean / zero_cost.annual_turnover * 10000)
    _write(zero_cost[["candidate", "annual_mean", "annual_turnover", "first_order_break_even_bps"]],
           output / "break_even_cost.csv")
    subperiod_rows = []
    for start, end in protocol["holdout_subperiods"]:
        for name, result in holdout.items():
            subperiod_rows.append({"start": start, "end": end, "candidate": name,
                                   **performance_metrics(result.loc[start:end], protocol["hac_lags"])})
    _write(pd.DataFrame(subperiod_rows), output / "holdout_subperiods.csv")
    null, null_meta = run_null_experiment(null_reps, protocol["null_experiment_candidates"],
                                         protocol["null_experiment_observations"], protocol["seed"],
                                         protocol["null_ar_coefficient"],
                                         protocol["null_cross_candidate_correlation"], protocol["hac_lags"])
    _write(null, output / "null_trials.csv")
    null_summary = []
    for method in ["prespecified_single_reject", "naive_reject", "bonferroni_reject", "known_null_max_reject"]:
        rate, lower, upper = _wilson(int(null[method].sum()), len(null))
        null_summary.append({"method": method, "false_positive_rate": rate, "lower": lower,
                             "upper": upper, "replicates": len(null)})
    null_summary = pd.DataFrame(null_summary)
    _write(null_summary, output / "null_summary.csv")
    (output / "null_design.json").write_text(json.dumps(null_meta, indent=2) + "\n")
    ledger = pd.DataFrame(ledger_rows)
    ledger["frozen_validation_winner"] = ledger.candidate == winner
    _write(ledger, output / "research_ledger.csv")
    from .plotting import make_figures
    make_figures(output, protocol, ledger, holdout, winner, ew, costs,
                  inference_table, max_test, pd.DataFrame(ic_summary), annual_choices,
                  null_summary, pd.DataFrame(subperiod_rows))
    manifest = {
        "project": "alpha-research-lab", "version": __version__, "profile": profile,
        "protocol_sha256": protocol_hash, "source": source, "selected_candidate": winner,
        "candidate_count": len(schedules), "tested_procedures": names,
        "holdout_observations": len(matrix), "bootstrap_replicates": B,
        "global_family_p": max_test["global_p"], "selected_mean_bootstrap_interval": winner_ci,
        "equal_weight_context_metrics": benchmark_metrics,
        "null_replicates": null_reps, "runtime_seconds": time.perf_counter() - started,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "numpy": np.__version__, "scipy": scipy.__version__, "pandas": pd.__version__,
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(Path(__file__).parent.glob("*.py"))},
    }
    from .report import write_report
    write_report(output, protocol, manifest, ledger, costs, inference_table,
                  pd.DataFrame(ic_summary), null_summary, pd.DataFrame(subperiod_rows),
                  pd.DataFrame(block_rows))
    manifest["artifact_sha256"] = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(output.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Completed in {manifest['runtime_seconds']:.1f}s: {output / 'report.md'}", flush=True)
    return manifest

