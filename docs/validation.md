# Executed validation

The published initial study was validated locally with Python 3.12.6.

| Check | Result |
|---|---|
| `pytest -q` | 48 passed |
| `ruff check src tests scripts` | All checks passed |
| Editable package installation | Succeeded |
| Full empirical pipeline | Completed in approximately 44 seconds on the recorded host; exact runtime in manifest |
| Source panel | 13,614 complete daily rows × 49 industries in the research period |
| Candidate ledger | All 12 candidates across three periods, plus the adaptive final-period procedure |
| Family inference | 2,000 replicates at each of three block lengths; all 13 procedures retained |
| Known-null study | 2,000 independent calibration replicates and 1,000 evaluation replicates |
| Fresh bootstrap-size audit | 1,000 datasets at each of two lengths, 499 paired resamples; completed in 989 seconds |
| Mandatory secondary empirical pair | Original fixed-scale p = 0.792104; studentized p = 0.786107; original conclusion preserved |
| Notebook | All 7 code cells executed, stdout retained, notebook schema validated |
| Figures | All 9 PNGs visually inspected for legibility and layout |
| Fingerprints | Source-module, protocol and generated-artifact hashes verified |

Tests cover the provider-panel parser, missing-value handling, exact signal windows,
deterministic ranking, portfolio neutrality, complete schedule prefix causality,
next-close execution, entry/liquidation costs, drifted turnover, cash/holding
compounding, the transaction-cost fixed point (including feasible high-cost
overshoots, slow contractions and genuinely unaffordable liquidation), chronological annual selection,
HAC uncertainty, shared block resampling, candidate-permutation invariance and
invariance to adding a perfectly duplicate candidate.

The separate bootstrap audit adds comparisons of batched HAC against scalar
implementations, invariance to bootstrap batching, original-function equivalence,
time-axis and cross-candidate dependence, exact Gaussian cutoff quadrature,
finite-sample AR mean covariance, and binomial uncertainty. A scalar bootstrap
loop reproduced the studentized p-value as a separate computational cross-check;
this does not constitute external peer review.

The notebook also reconstructs the published winner's final equity from the
retained daily net returns and checks the difference against CSV rounding tolerance.

GitHub Actions is configured to repeat the offline tests on Python 3.10 and 3.12.
Those tests use synthetic fixtures and require no data-provider access. A local
test result is not a claim that a remote workflow has already run; the GitHub
workflow history becomes the source of truth after publication.

