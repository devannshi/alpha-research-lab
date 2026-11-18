# Protocol decisions before strategy evaluation

The candidate family, cutoff, chronology, costs, portfolio rules and inference
settings are frozen in `research_protocol.json`. This is a historical research
protocol recorded before inspecting this implementation's strategy results; it is
not an external preregistration or an assertion that the historical holdout was
unknown to the researcher.

The initial design considered starting the development period in 1970. A source
data availability audit found one missing `Softw` return on 1971-03-11, in addition
to many missing observations early in the archive. Before computing any strategy
outcomes, the development start was changed to 1972-01-01. This yields a complete
49-industry return panel over the evaluation period without imputing an unobserved
held-asset return or selecting an industry universe using future performance.
Pre-1972 data are used only to initialize lagged features; a missing observation
makes that industry's rolling feature unavailable until its window becomes valid.

Daily returns after 2025-12-31 are excluded before feature generation. The archive
is a later provider vintage, so this cutoff does not remove retrospective revisions
to earlier observations. Historical vintage certainty is not claimed.

The six signals and two weighting rules define the complete 12-candidate family.
The validation winner is chosen using 2005–2014 net Sharpe at the declared 10 bps
one-way cost. It is then frozen for the 2015–2025 final comparison. A separate
prespecified annual adaptive selector uses only each year's five preceding years;
it is analyzed as a different strategy and pays turnover when its selection changes.

## Separate inference audit after the primary study

A computational audit checked the actual fixed-scale bootstrap on an
exploratory 200-dataset Gaussian null bank. Its rejection frequencies warranted
further study; an exact-covariance oracle also rejected unusually often on that
small bank. Those diagnostic frequencies were not treated as a definitive size
estimate, a reason to change block lengths, or a correction factor for empirical
p-values.

Before evaluating fresh seeds, `bootstrap_audit_protocol.json` froze a separate
comparison of the original procedure, within-bootstrap HAC studentization, and
an exact Gaussian covariance oracle. It uses 1,000 outer datasets at each of
500 and 2,766 observations, six candidates, block/HAC bandwidth 21 and 499 inner
replicates. The latter choice followed a timing-only benchmark. Dataset and
bootstrap seed banks were separated after a pre-execution review found draft
address overlap. No outcome from the fresh bank informed those choices.

While this new audit was running, before any rejection counts were inspected,
`bootstrap_empirical_followup_protocol.json` also required a secondary empirical
comparison on all thirteen original strategies, at the original 2,000 replicates
and bandwidths. Both results must be reported regardless of the null-size study
or the p-values' ordering. The original empirical protocol, winner and primary
inference are preserved. These are documented follow-up analyses, not claims
that the alternatives were part of the original design.

