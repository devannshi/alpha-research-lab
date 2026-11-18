"""Render a report from actual computed outputs, including unfavorable results."""


def markdown_table(frame, columns, formats=None):
    formats = formats or {}
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(formats.get(c, str)(row[c]) for c in columns) + " |")
    return "\n".join(lines)


def write_report(output, protocol, manifest, ledger, costs, inference, ic_summary,
                  null_summary, subperiods, block_sensitivity):
    winner = manifest["selected_candidate"]
    val = ledger[(ledger.period == "validation") & (ledger.candidate == winner)].iloc[0]
    test = ledger[ledger.period == "holdout"].set_index("candidate")
    chosen = test.loc[winner]
    adjusted = inference.set_index("candidate").loc[winner]
    ci = manifest["selected_mean_bootstrap_interval"]
    show = test.reset_index()[["candidate", "annual_mean", "sharpe", "max_drawdown", "annual_turnover"]]
    result_table = markdown_table(show, list(show.columns), {
        "annual_mean": lambda x: f"{x:.2%}", "sharpe": lambda x: f"{x:.3f}",
        "max_drawdown": lambda x: f"{x:.2%}", "annual_turnover": lambda x: f"{x:.2f}×"})
    infer_table = markdown_table(inference, ["candidate", "hac_t", "individual_bootstrap_p", "family_adjusted_p"],
                                 {"hac_t": lambda x: f"{x:.3f}", "individual_bootstrap_p": lambda x: f"{x:.4f}",
                                  "family_adjusted_p": lambda x: f"{x:.4f}"})
    null_table = markdown_table(null_summary, ["method", "false_positive_rate", "lower", "upper"],
                                {"false_positive_rate": lambda x: f"{x:.1%}",
                                 "lower": lambda x: f"{x:.1%}", "upper": lambda x: f"{x:.1%}"})
    cost_table = markdown_table(costs[costs.candidate == winner],
                                ["cost_bps", "annual_mean", "sharpe", "max_drawdown"],
                                {"annual_mean": lambda x: f"{x:.2%}", "sharpe": lambda x: f"{x:.3f}",
                                 "max_drawdown": lambda x: f"{x:.2%}"})
    source = manifest["source"]
    report = rf"""# Which industry signals survive selection and costs?

This report is generated from the frozen protocol and retained research ledger.
It studies historical **research portfolio returns**, not directly tradable securities.
Positive long-short returns are not automatically risk-adjusted alpha.

## The declared selection and its final-period outcome

The validation rule selected **`{winner}`** using only 2005–2014 net Sharpe at
10 basis points of one-way traded-notional cost. Its validation Sharpe was
**{val.sharpe:.3f}**. No final-period result was used to choose that candidate.

Over 2015–2025, its net annualized arithmetic mean was **{chosen.annual_mean:.2%}**,
net Sharpe **{chosen.sharpe:.3f}**, CAGR **{chosen.cagr:.2%}**, maximum drawdown
**{chosen.max_drawdown:.2%}**, and annual traded-notional turnover
**{chosen.annual_turnover:.2f} times equity**. These metrics use a 1.0 gross target
(0.5 long and 0.5 short), zero cash/short financing, delayed close execution, and
explicit entry and terminal-liquidation costs.

The selected mean daily return's stationary-block 95% percentile interval,
annualized arithmetically, is **[{252*ci['lower']:.2%}, {252*ci['upper']:.2%}]**.
It describes temporal sampling uncertainty under the bootstrap approximation;
it does not include historical data revisions, financing, model uncertainty,
unobserved trading costs or every research choice outside the declared family.

![Validation to final-period change](figures/selection_decay.png)

## All candidates remain visible

The six signals crossed with two weighting rules produce 12 fixed candidates.
A separately declared annual selector chooses from that family using only its
five preceding calendar years. Its actual holdings are rebalanced and costs paid
when the choice changes; no return series are spliced without transition trades.

{result_table}

The fixed validation winner is the primary selection result. The best strategy
found by sorting final-period outcomes is **not** promoted to a replacement winner.
All development, validation and final-period metrics are in `research_ledger.csv`,
and every candidate's daily accounting is in `candidate_daily.csv.gz`.

![Final-period paths](figures/holdout_equity.png)

## Did the best-looking result survive the declared family?

We test the one-sided null that every one of the **13** declared procedures
(12 fixed candidates plus the annual adaptive selector) has nonpositive expected
net return. The benchmark is zero return under the stated financing convention.
This is not a factor-alpha test.

The test jointly resamples centered candidate return vectors using stationary
blocks with mean length 21 trading days. All columns use the same resampled dates,
preserving observed cross-candidate dependence. The maximum positive HAC-scaled
mean is the family statistic. Original HAC scales are held fixed in the bootstrap;
this is a single-step fixed-scale max test, not a claim to implement Hansen SPA,
the Deflated Sharpe Ratio or combinatorial symmetric cross-validation.

This is approximate inference. The separate [fresh-seed null-size audit](../bootstrap_audit/report.md)
tests the actual procedure against a predeclared within-bootstrap HAC-studentized
alternative and an exact Gaussian covariance oracle. It preserves this original
analysis and reports both empirical family p-values as a secondary comparison.
The best-of-50 known-null illustration below is a different experiment and does
not validate this bootstrap's finite-sample size.

With **{manifest['bootstrap_replicates']}** replicates, the global family p-value is
**{manifest['global_family_p']:.4f}**. The frozen winner's individual bootstrap
p-value is **{adjusted.individual_bootstrap_p:.4f}**, and its family-adjusted value is
**{adjusted.family_adjusted_p:.4f}**. The initial winner was selected outside the
final period; showing the family correction also makes the later inspection of
every final-period candidate visible.

{infer_table}

![Family-wise evidence](figures/selection_adjusted_inference.png)

The least-favorable recentering sets every candidate mean to zero and may be
conservative when many candidates have negative true means. Stationarity/mixing
and sufficiently stable HAC estimation remain approximations. We retain block
lengths 5, 21 and 63 in `bootstrap_block_sensitivity.csv`; a favorable block length
is not selected after the fact. Selection errors outside this documented family
are not magically corrected by the bootstrap.

## What transaction costs change

Every trade uses current drifted holdings. With target weights defined on post-cost
equity, cost is solved from

$$c_t=\tau\sum_i|w^*_{{i,t}}(1-c_t)-w^-_{{i,t}}|.$$

Turnover is the full one-way absolute traded notional, without dividing by two.
The 10 bps default is a scenario, not an empirically calibrated execution estimate.
The provider's industry portfolios cannot themselves be purchased at this cost.

For the frozen winner:

{cost_table}

`break_even_cost.csv` additionally reports a **first-order approximate** threshold
equal to zero-cost annual mean divided by zero-cost annual turnover, converted to
basis points. It is an arithmetic-mean approximation, not an exact CAGR root or a
market impact/capacity estimate. Exact tested cost scenarios are retained above.

![Cost sensitivity](figures/cost_frontier.png)

## Signal diagnostics and temporal stability

Rank IC relates each month-end score to industry returns earned only after the
next trading close, over the subsequent 21 trading days. A complete forward label
must fit inside the reported period. Scores use past returns; forward returns
are diagnostic labels and never enter a trading decision. Monthly IC intervals
use three HAC lags and are exploratory, not a second family of confirmed alpha tests.

![Rank IC](figures/rank_ic.png)

The final period is partitioned into prespecified 2015–2019, 2020–2022 and 2023–2025
windows. Their returns are slices of the actual continuous strategy path, rather
than new backtests that reset holdings for favorable subperiods.

![Subperiod results](figures/subperiod_robustness.png)

![Annual selection record](figures/annual_selection.png)

## A known-null experiment: why choosing the maximum is different

All 50 simulated candidate strategies have exactly zero expected return. They share
cross-candidate correlation 0.35 and AR(1) coefficient 0.2; each series has 756
observations after burn-in. We repeat the selection exercise
**{manifest['null_replicates']}** times. A separate independent calibration stream
supplies the known-null maximum cutoff. The resulting Wilson 95% intervals describe
Monte Carlo uncertainty in the probability of at least one false rejection.

{null_table}

The known-null maximum adjustment is illustrative simulation calibration, not the
empirical block bootstrap and not a method available when the true data-generating
process is unknown. Bonferroni here uses asymptotic HAC normal p-values; finite-sample
HAC error can affect its realized level. This experiment exposes selection inflation
without presenting the adjusted procedure as infallible.

![Null selection experiment](figures/null_selection.png)

## Data provenance and reproducibility

- Source: Kenneth French's 49 Industry Portfolios, daily **value-weighted** panel.
- Complete research period: {source['analysis_first_date']} through {source['analysis_last_date']};
  {source['analysis_rows']} daily observations and 49 industries.
- Original archive SHA-256: `{source['archive_sha256']}`.
- Protocol SHA-256: `{manifest['protocol_sha256']}`.
- The raw provider archive is excluded from the Git repository. The downloader
  verifies its recorded hash; a changed vintage requires an explicit override.
- A 1971 missing software-industry observation motivated the documented move of the
  development start to 1972 before strategy outcomes were inspected.
- Current-vintage historical data can contain revisions. A date cutoff is not a
  guarantee of point-in-time historical availability or absence of survivorship effects.

The research portfolios are aggregated, annually reconstituted classifications.
They are not ticker-level holdings or a directly implementable shortable universe.
Dollar neutrality at rebalancing is not beta neutrality, and holdings drift between
rebalances. The equal-weight industry context series is long-only and is not used
as a risk-matched alpha benchmark. See [methodology](../../docs/methodology.md),
[limitations](../../docs/limitations.md), [data rights](../../data/README.md), and
[references](../../docs/references.md) before interpreting the economic result.
"""
    (output / "report.md").write_text(report)

