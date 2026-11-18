# Research output dictionary

The original provider return panel is excluded from Git. These outputs are
transformations, diagnostics and research results produced by this implementation.

## `research_ledger.csv`

One row is one candidate in one chronological period. The final period additionally
contains the annual adaptive selector. All candidates remain visible.

| Field | Meaning |
|---|---|
| `period`, `candidate` | Development, validation or final period; deterministic procedure identifier |
| `cost_bps` | One-way cost per absolute traded notional, in basis points |
| `annual_mean` | 252 × arithmetic mean daily net return |
| `annual_volatility` | sqrt(252) × sample standard deviation of daily net return |
| `sharpe` | Arithmetic mean divided by standard deviation, annualized; zero cash return convention |
| `cagr`, `total_return` | Actual compounded growth statistics |
| `max_drawdown` | Worst loss from a prior equity peak, including initial equity 1 |
| `annual_turnover` | Absolute traded notional / pre-trade equity, summed and scaled to 252 days |
| `average_gross_exposure` | Mean absolute sum of post-close weights, including drift |
| `mean_absolute_net_exposure` | Mean absolute net risky weight; target neutrality does not prevent drift |
| `mean`, `hac_se`, `hac_t` | Daily mean, Bartlett HAC standard error and mean t-statistic |
| `p_one_sided`, `lower`, `upper` | Asymptotic normal one-sided p-value and two-sided 95% daily mean interval |
| `n`, `lags` | Daily observation count and HAC lag choice |
| `frozen_validation_winner` | Whether this candidate was chosen on validation data alone |

## `candidate_daily.csv.gz`

The key is `(period, candidate, date)`. A standalone period starts flat and
liquidates at its final close. Fields include:

- `gross_return`: current holdings' return before today's end-of-close trade costs.
- `net_return`: `(1 + gross_return) × (1 − cost_fraction) − 1`.
- `nav`: cumulative net equity from 1.
- `turnover`: full absolute one-way traded notional / pre-trade equity; no division by two.
- `cost_fraction`: today’s cost / pre-trade equity.
- `gross_exposure`, `net_exposure`: post-close weights, after any rebalancing.
- `cash_weight`: one minus the sum of risky weights under zero cash financing.
- `rebalanced`: a target was applied at this close.
- `terminal_liquidation`: the final close was explicitly liquidated to cash.

Values are stored to twelve significant digits. Reconstructing NAV from rounded
daily returns can differ in the last digits from the recorded full-precision NAV.

## Schedules and selection

`target_weights.csv.gz` has candidate, execution date and 49 target weights.
`decision_log.csv.gz` records the earlier decision close, execution close, eligible
industry count, gross and net target. Target weights affect only returns after
the execution close.

`validation_ranking.csv` retains every initial validation score, and
`frozen_selection.json` records the selected candidate, cutoff, primary cost and
protocol fingerprint. `annual_selection_scores.csv` retains each trailing
five-year ranking. `annual_selection_choices.csv` records the choice applied at
every execution date and the prior December information cutoff.

## Inference and diagnostics

`family_inference.csv` contains all 13 procedures' HAC t-statistics, individual
centered-bootstrap p-values and single-step family-adjusted p-values. The family
max distribution is retained in `bootstrap_maxima.csv`. Block-length sensitivity
is in `bootstrap_block_sensitivity.csv`.

`information_coefficients.csv` records signal decision date, later execution date,
forward-label start/end, rank IC and eligible cross-section size. `ic_summary.csv`
contains monthly HAC summaries; only fully contained labels enter each period.

`cost_sensitivity.csv` repeats the final-period evaluation at each declared cost
scenario. `break_even_cost.csv` reports a first-order arithmetic-mean threshold,
explicitly not an exact CAGR root. `holdout_subperiods.csv` summarizes slices of
the continuous final-period strategy path without restarting positions.

## Known-null experiment

`null_trials.csv` records the maximum HAC statistic and rejection indicators in
each synthetic replication. `null_summary.csv` contains false-positive probabilities
and Wilson intervals. `null_design.json` records the dependence structure, sample
sizes and thresholds. The known-null max threshold uses an independent calibration
stream; it is distinct from the empirical stationary-bootstrap procedure.

## Provenance

`manifest.json` records the source vintage, protocol hash, selected candidate,
tested family, package versions, runtime and source/output hashes. Hashes cover
the saved bytes, not a claim that a remote source will remain unchanged. Exact
provider data rights remain separate from this repository's code license.

