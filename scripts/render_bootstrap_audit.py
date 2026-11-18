"""Render retained null-size results and execute the separately frozen empirical pair."""
import hashlib
import json
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from alpha_research.bootstrap_audit import paired_max_tests


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "results/bootstrap_audit"
    summary = pd.read_csv(output / "summary.csv")
    differences = pd.read_csv(output / "paired_differences.csv")
    manifest = json.loads((output / "manifest.json").read_text())
    protocol_path = root / "bootstrap_empirical_followup_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    input_path = root / protocol["input"]
    daily = pd.read_csv(input_path, parse_dates=["date"])
    matrix = daily[daily.period == protocol["period"]].pivot(
        index="date", columns="candidate", values="net_return").sort_index().sort_index(axis=1)
    assert matrix.shape == (protocol["observations"], 13)
    assert matrix.index.is_unique and matrix.index.is_monotonic_increasing
    assert not matrix.isna().any().any()
    comparison = paired_max_tests(matrix.to_numpy(), protocol["bootstrap_replicates"],
                                  protocol["block_length"], protocol["hac_lags"], protocol["seed"])
    primary = json.loads((root / "results/published/manifest.json").read_text())
    assert comparison["fixed_scale_p"] == primary["global_family_p"]
    comparison.update({"protocol": protocol, "candidates": list(matrix.columns),
                       "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
                       "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest()})
    (output / "empirical_comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")

    labels = {"fixed_scale": "Original fixed scale", "studentized": "Bootstrap HAC studentized",
              "known_gaussian": "Known Gaussian covariance"}
    colors = {"fixed_scale": "#de764b", "studentized": "#087f8c", "known_gaussian": "#203a5c"}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "savefig.facecolor": "white"})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True, layout="constrained")
    xmax = max(10, summary.wilson_high.max() * 100 + 1)
    for ax, (n, block) in zip(axes, summary.groupby("observations")):
        indexed = block.set_index("method")
        for y, method in enumerate(labels):
            row = indexed.loc[method]
            value = 100 * row.rejection_rate
            ax.errorbar(value, y, xerr=[[value - 100 * row.wilson_low],
                                      [100 * row.wilson_high - value]],
                        fmt="o", color=colors[method], markersize=8, capsize=4)
            ax.annotate(f"{row.rejection_rate:.1%}", (value, y), xytext=(0, 11),
                        textcoords="offset points", ha="center", fontsize=9)
        ax.axvline(5, color="#a5afbc", linestyle="--", label="Nominal 5%")
        ax.set(xlim=(0, xmax), ylim=(-.5, 2.6), yticks=range(3),
               yticklabels=list(labels.values()), xlabel="False-positive frequency (%)",
               title=f"{n:,} observations per dataset")
        ax.grid(axis="x", alpha=.2)
        ax.legend(loc="lower right", frameon=False)
    axes[0].invert_yaxis()
    fig.suptitle("Auditing the inference itself: fresh null datasets and paired procedures\n"
                 "1,000 datasets per panel · 499 shared resamples · 95% Wilson intervals", fontsize=12)
    fig.savefig(output / "bootstrap_size.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    rows = []
    for row in summary.itertuples():
        rows.append(f"| {row.observations:,} | {labels[row.method]} | "
                    f"{row.rejections}/{row.outer_trials} | {row.rejection_rate:.2%} | "
                    f"[{row.wilson_low:.2%}, {row.wilson_high:.2%}] |")
    paired_rows = []
    for row in differences.itertuples():
        paired_rows.append(f"| {row.observations:,} | {100 * row.student_minus_fixed:+.2f} pp | "
                           f"[{100 * row.paired_normal_low:+.2f}, {100 * row.paired_normal_high:+.2f}] pp | "
                           f"{row.fixed_only_rejections} / {row.student_only_rejections} |")
    rates = summary.set_index(["observations", "method"]).rejection_rate
    text = rf"""# Does the family test control false positives in a known null?

This is a **separate follow-up study**, motivated by a computational
calibration check. It does not replace the frozen historical analysis or choose a preferred method
after inspecting its outcome. Its [protocol](../../bootstrap_audit_protocol.json)
was fixed before evaluating this fresh seed bank; all three procedures are retained.

## Executed design

- **1,000 independent outer datasets per sample-size cell**, with six zero-mean,
  equicorrelated Gaussian AR(1) series: time coefficient 0.2, cross-candidate
  correlation 0.35, and 200 burn-in observations.
- Sample sizes **500 and 2,766**; the latter matches the empirical holdout length.
  Six candidates isolate this audit and do not reproduce the thirteen empirical
  strategies or their return distribution.
- **499 stationary-bootstrap replicates**, mean block length 21 and Bartlett HAC
  bandwidth 21. The original and studentized tests use identical datasets and
  identical date indices. Each global p-value uses the same plus-one rule.
- The oracle uses the exact Gaussian covariance, finite-sample AR mean variance
  and a maximum cutoff computed by one-dimensional quadrature: **{manifest['known_gaussian_max_cutoff']:.12f}**.
  It checks outer Monte Carlo variability; it is unavailable for market returns.

The primary historical inference retains **2,000** replicates. The audit's 499
replicates trade inner Monte Carlo precision for 1,000 genuinely separate outer
datasets; the audit estimates the behavior of this specific finite-replicate test.
Sample-size cells reuse trial addresses and must not be pooled as independent data.

## Results

With 500 observations, the original fixed-scale test rejected a true null in
**{rates.loc[(500, 'fixed_scale')]:.1%}** of datasets, compared with
**{rates.loc[(500, 'studentized')]:.1%}** for studentization. At the actual holdout
length of 2,766 observations, the corresponding frequencies were
**{rates.loc[(2766, 'fixed_scale')]:.1%}** and **{rates.loc[(2766, 'studentized')]:.1%}**.
The shorter-sample result identifies a material limitation of the original
approximation in this design; the longer-sample intervals below include the
nominal 5% level for both procedures. This motivates reporting finite-sample
calibration rather than asserting that an adjusted p-value automatically has
correct size.

![Fresh-seed null-size audit](bootstrap_size.png)

| Observations | Procedure | Rejections | Rejection frequency | 95% Wilson interval |
|---|---|---|---|---|
{chr(10).join(rows)}

The nominal rejection probability is 5%. These are Monte Carlo estimates for the
declared Gaussian process, with uncertainty shown. They do not establish exact
size control over other dependence structures, heavy tails, regime changes,
candidate families or bandwidth choices.

| Observations | Studentized minus fixed | Paired approximate 95% interval | Fixed-only / student-only rejections |
|---|---|---|---|
{chr(10).join(paired_rows)}

The difference uses paired rejection indicators on the same outer datasets.
Negative values mean fewer false positives for studentization in this experiment;
that does not prove uniform superiority or justify selecting the most favorable
empirical p-value.

## What changes mathematically

Both methods compare the largest positive observed HAC-scaled mean with a
centered bootstrap maximum. The original method holds the original HAC scale
fixed within each resample. The alternative recomputes Bartlett HAC uncertainty
inside each bootstrap sample. Its numerator retains the sample mean of resampled,
originally centered returns; only its variance calculation centers that sample
again. Shared date indices preserve cross-candidate dependence.

The vectorized HAC calculation was checked against independent scalar calls;
studentized p-values were checked against a scalar-loop implementation and across
batch partitions. The fixed-scale branch calls the actual original research
function, rather than a separate approximation to it.

## Mandatory empirical comparison

Before seeing fresh null-size outcomes, a [separate protocol](../../bootstrap_empirical_followup_protocol.json)
required reporting both procedures on all thirteen original empirical holdout
series, using 2,000 shared replicates, block/HAC bandwidth 21 and the original
seed. The daily ledger retains 12 significant digits; the reconstructed original
fixed-scale p-value matches the published value exactly.

- Original primary fixed-scale family p: **{comparison['fixed_scale_p']:.6f}**.
- Separately labeled studentized family p: **{comparison['studentized_p']:.6f}**.

Both are reported regardless of their order. Neither replaces the other. A null
rejection frequency in the Gaussian audit is not a post-hoc correction factor for
these empirical p-values. The original validation winner and historical ledger
remain unchanged.

## Why this is separate from the best-of-50 illustration

The primary report's best-of-50 experiment compares naive selection, Bonferroni
and a known-null calibrated cutoff. That demonstrates selection inflation; it
does **not** validate the empirical stationary-bootstrap procedure. This follow-up
actually runs that procedure on new null datasets and compares a predeclared
studentized alternative.

An exploratory 200-dataset reviewer check motivated the follow-up. Its oracle
also rejected more often than expected, which is why this report uses a separate
1,000-dataset seed bank rather than treating the exploratory frequencies as a
universal calibration failure. The fresh protocol, all trial p-values and both
method outcomes are retained; no bandwidth was selected from these results.

## Reproduce and inspect

```bash
python -m alpha_research.bootstrap_audit
python scripts/render_bootstrap_audit.py
```

The audit took {manifest['runtime_seconds'] / 60:.1f} minutes on the recorded host;
runtime varies. [trials.csv](trials.csv) retains every dataset seed, bootstrap seed,
p-value and rejection indicator. [summary.csv](summary.csv),
[paired_differences.csv](paired_differences.csv),
[empirical_comparison.json](empirical_comparison.json) and [manifest.json](manifest.json)
provide counts, uncertainty, input fingerprints and source hashes.
"""
    (output / "report.md").write_text(text)
    manifest["rendering"] = {"script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                             "empirical_input_sha256": comparison["input_sha256"],
                             "empirical_protocol_sha256": comparison["protocol_sha256"]}
    manifest["artifact_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in output.iterdir() if path.is_file() and path.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Audit report written; empirical fixed={comparison['fixed_scale_p']:.6f}, "
          f"studentized={comparison['studentized_p']:.6f}")


if __name__ == "__main__":
    main()
