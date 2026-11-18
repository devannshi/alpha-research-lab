# What the evidence does and does not support

## The actual conclusion

Under the declared historical experiment, the validation winner does not show a
credible net edge in the final period. The research contribution is the audited
selection and evaluation process, including its negative finding. The study does
not claim all momentum/reversal strategies are ineffective, that no industry
predictability exists, or that the chosen candidate family exhausts useful signals.

## Data are aggregated research portfolios

The French industries are constructed return portfolios, not exchange-traded
securities. Their holdings and reconstitution mechanisms are not replayed here.
There is no security-level short availability, borrow cost, delisting audit,
point-in-time constituent file, volume or capacity model. Current-vintage data
can revise earlier history. A 2025 cutoff does not make the source vintage 2025.
The study therefore makes no claim of a survivorship-free, investable backtest.

## Execution is a controlled accounting experiment

The model uses next-close execution because only close-to-close returns are
available. It does not estimate auction fills, spread, slippage, latency or market
impact. The 10 bps default and other cost levels are scenarios, not calibrated
costs of trading the underlying portfolios. Financing, cash interest, stock-loan
fees and short rebates are zero. Results cannot be read as deployable returns.

Gross exposure is 1.0 only at rebalancing; weights drift between trades. Net dollar
exposure also drifts. Neither zero net dollars at rebalancing nor inverse-volatility
tail weights enforce factor neutrality. No claim of risk-adjusted alpha is based
solely on mean long-short returns or Sharpe.

## Chronological validation has a limited meaning

The primary winner uses 2005–2014 results and remains fixed through 2015–2025.
The adaptive selector uses only previously observed years at each decision.
Nevertheless, this is a study performed after the historical period. Its protocol
is recorded before implementation outputs, not externally preregistered before
the market outcomes occurred. Known literature informed the candidate set.

The development stage is not machine-learning training: these are deterministic
lagged-return rules. Future extensions that fit models, normalize features with
estimated parameters, or tune allocation hyperparameters need an explicit nested
chronological fitting protocol.

## Statistical inference is approximate

HAC inference uses fixed bandwidths and normal approximations. The stationary
bootstrap assumes temporal regularity that financial regimes can violate. A shared
resample preserves observed contemporaneous candidate dependence but does not
repair nonstationarity or uncertain data vintages. Centering all candidate means
at zero gives a least-favorable max test and can sacrifice power.

The family bootstrap resamples the retained strategy-return columns. It does not
resimulate industry histories, refit the five-year annual selector, or recompute
turnover on every bootstrap path. It therefore assesses the means of those
realized procedure-return series under the stated dependence approximation;
it is not a full generative audit of how the entire research pipeline would
adapt to alternative market histories.

The tested family includes the 12 fixed candidates and adaptive selector at the
primary cost assumption. It does not automatically adjust every cost scenario,
IC diagnostic, subperiod comparison, research idea considered elsewhere, or future
revision to the family. Cost and IC plots are exploratory robustness diagnostics.
The bootstrap interval for the fixed winner's mean is not a simultaneous
selection-adjusted confidence interval.

The known-null experiment has a known synthetic Gaussian AR process. Its calibrated
max cutoff cannot be transplanted to market data. Bonferroni depends on valid
individual p-values, so its realized finite-sample level can differ from 5% when
HAC normal approximations are imperfect.

The known-null calibrated cutoff is not evidence that the actual empirical
bootstrap has nominal finite-sample size. The [separate bootstrap audit](../results/bootstrap_audit/report.md)
tests that procedure and a predeclared studentized alternative on a fresh seed
bank, with an exact Gaussian oracle and binomial uncertainty. Its six Gaussian
candidates and 499 inner replicates do not reproduce the thirteen empirical
return series or the primary 2,000-replicate analysis. Neither a favorable audit
cell nor a lower secondary empirical p-value establishes universal validity.

## Reproducibility has a source-vintage boundary

Original source fingerprints are recorded and changes are rejected by default.
The provider ZIP is not redistributed under the repository's MIT license. A
future download may differ; exact reproduction then requires the recorded source
bytes. An explicit revised-vintage run remains supported and is labeled as such.
Committed transformed research ledgers and figures are sufficient to audit the
published conclusions without re-downloading the raw panel.

## Next experiments that would add evidence

1. Add a point-in-time constituent-level dataset with documented delisting and
   stock-loan handling, then compare portfolio-level and security-level results.
2. Fit a risk model only on past data and compare dollar-neutral versus explicit
   factor-neutral weights under the same selection protocol and turnover budget.
3. Use a broker/venue cost model with uncertainty and participation constraints;
   test whether a proposed edge exceeds a defensible cost distribution.
4. Repeat the entire frozen procedure on a distinct market or future unseen period.
5. Add alternative bootstrap/subsampling methods that explicitly stress structural
   changes, while recording them as additional analyses rather than choosing the
   method with the most favorable p-value.

