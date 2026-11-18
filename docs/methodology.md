# Methodology: from a declared predictor to a credible result

## 1. Data and the unit of analysis

The input is the **daily value-weighted** panel of Kenneth French's 49 industry
research portfolios. The parser selects that panel explicitly, stops before the
equal-weighted panel, converts percent returns to decimals, recognizes provider
missing-value sentinels, and checks ordered unique dates and industry names.

The complete evaluation period is 1972–2025. Earlier observations initialize
lagged features only. Returns after 2025-12-31 are discarded before constructing
signals. A current-vintage archive may revise historical values; this is not a
point-in-time security-level dataset. The ZIP's exact SHA-256 and the CSV member's
fingerprint are recorded, while the third-party archive is excluded from Git.

No surviving ticker universe is reconstructed. The underlying portfolios are
industry aggregates, not tradeable ticker-level positions. The study measures
relationships among research return series under a stylized portfolio accounting
convention.

## 2. The complete signal family

At close t, with daily industry return $r_{i,t}$, define

$$s_{i,t}=d\sum_{u=t-L+1}^{t-S}\log(1+r_{i,u}),$$

where $L$ is the lookback, $S$ is the number of recent skipped returns, and
$d\in\{-1,+1\}$ chooses reversal or momentum. Thus $L=252,S=21$ means 231
observations ending 21 trading days ago, not a 252-observation window plus a skip.

| Signal | L | S | Direction |
|---|---:|---:|---:|
| reversal_5 | 5 | 0 | −1 |
| reversal_21 | 21 | 0 | −1 |
| momentum_63_skip5 | 63 | 5 | +1 |
| momentum_126_skip21 | 126 | 21 | +1 |
| momentum_252_skip21 | 252 | 21 | +1 |
| momentum_252 | 252 | 0 | +1 |

Each signal is crossed with equal or inverse-volatility weighting. Daily volatility
is the sample standard deviation over the last 63 observations, floored at 0.001
for inverse weighting. An industry needs a complete signal window and finite
volatility. If fewer than 40 industries qualify, the target is cash. This rule
uses information at the decision date rather than future completeness.

Rank the eligible industries by score with industry-name tie breaking. Let
$k=\lfloor0.2N_t\rfloor$. Allocate +0.5 gross to the top k and −0.5 gross to the
bottom k, normalizing each leg separately. At 49 eligible industries, each leg
contains nine industries. Inverse-volatility allocation changes weights within
the legs, not the selected ranks. Target gross exposure is 1 and target net
exposure is zero. Exposure can drift between rebalances.

## 3. Information and execution timing

Daily source returns are close-to-close. They contain no opening prices or
intraday execution prices. Consequently:

| Time | Available information or action |
|---|---|
| Month-end close t | Observe returns through t; compute score, volatility and target |
| Next trading close t+1 | Existing holdings earn the t+1 return; then rebalance and pay costs |
| Following interval t+2 | The new target first earns a source daily return |

The delay is intentional. Crediting the t+1 return to a target built at close t
while pretending to trade at close t+1 would leak a full return. Future-suffix
perturbation tests cover scores, schedules, accounting and annual selection.

## 4. Exact self-financing transaction-cost accounting

Let $w_{t-1}$ be risky weights on portfolio equity after the previous close's
trades. Cash earns zero in the research convention. Before today's trades,

$$r^g_t=\sum_iw_{i,t-1}r_{i,t},\qquad
w^-_{i,t}=\frac{w_{i,t-1}(1+r_{i,t})}{1+r^g_t}.$$

These are **drifted** weights. Reusing the old target ignores changes in asset
values and portfolio equity and mismeasures turnover, especially for shorts.

If the new weights $w^*$ are defined on equity after paying transaction costs,
and $c_t$ is costs as a fraction of pre-trade equity, traded dollar notional
normalized by pre-trade equity is

$$u_{i,t}=w^*_{i,t}(1-c_t)-w^-_{i,t}.$$

At proportional one-way rate $\tau$,

$$c_t=\tau\sum_i|u_{i,t}|.$$

The map is a contraction whenever $\tau\|w^*\|_1<1$. The implementation iterates
the scalar fixed point to $10^{-14}$ absolute tolerance, with a bracketed root
fallback for slow convergence near the contraction bound. It rejects cost/gross
combinations outside the contraction domain. Within that domain a feasible root
below one exists exactly when $\tau\|w^-\|_1<1$: affordability is checked at the
root boundary, not at intermediate iterates, which may temporarily exceed one. For an
initial gross-one portfolio started from cash, the exact entry cost is
$c=\tau/(1+\tau)$, a useful analytic test.

Net daily return and post-trade weights are

$$r^n_t=(1+r^g_t)(1-c_t)-1,\qquad w_t=w^*.$$

On nontrading days, $c_t=0$ and $w_t=w^-_t$. Every standalone development,
validation or final-period run starts flat and explicitly liquidates at its final
close. The adaptive procedure carries its actual holdings across annual choices;
it does not concatenate independent candidate return curves without paying for
the change. Missing returns for held assets raise an error rather than being
silently filled with zero. Missing returns on zero holdings do not alter wealth.

The turnover variable is $\sum_i|u_i|$, the **full one-way traded notional**. No
half-turnover convention is used. Costs are applied symmetrically to buys/sells
and long/short legs. Financing, borrow fees, short rebates, spread variation,
market impact, underlying industry-portfolio reconstitution costs, and taxes are
outside this research convention.

## 5. Selection chronology

- **1972–2004: development/initialization.** The rule family and pipeline are
  evaluated; there is no fitted forecasting model or hidden parameter training.
- **2005–2014: fixed-candidate selection.** Rank all 12 candidates by daily net
  Sharpe at 10 bps one-way costs. Use lexicographic candidate identifiers to break
  exact ties. Write the winner and information cutoff before computing final-period
  performance.
- **2015–2025: final historical evaluation.** Keep the winner fixed. Retain all
  candidates to show the difference between the actual selection and a hindsight
  choice. The family-aware inference includes that later inspection.

The annual adaptive selector is a separately declared procedure. For each trading
year y, every candidate is scored over calendar years y−5 through y−1, with
standalone entry/liquidation costs in that scoring window. The chosen candidate's
monthly target governs year y. Only returns through December of y−1 enter the
choice. Later years can use earlier final-period observations because that
adaptation rule was specified in advance; the fixed primary winner does not change.

The protocol is recorded before this implementation's outputs, but the study is
historical and the strategy family is informed by known financial research.
Neither temporal splitting nor a protocol JSON proves that historical outcomes
were unknown to the researcher. This distinction is explicitly retained.

## 6. Performance statistics

For daily net return sample $x_1,\dots,x_n$, annualized arithmetic mean is
$252\bar x$, volatility is $\sqrt{252}\,s_x$, and Sharpe is
$\sqrt{252}\bar x/s_x$, under a zero-cash-return convention. CAGR compounds
actual daily returns. Maximum drawdown includes initial equity 1, so initial
entry costs and losses before the first observed peak are not omitted.

The long-short return is not automatically factor-adjusted alpha. Dollar neutrality
does not enforce market-beta, volatility, sector-factor or macro-exposure neutrality.
The equal-weight industry context series is long-only and is not used as a
risk-matched hypothesis-test benchmark.

For centered observations $u_t=x_t-\bar x$, the Bartlett HAC estimate is

$$\widehat\Omega=\widehat\gamma_0+
2\sum_{\ell=1}^{L}\left(1-\frac{\ell}{L+1}\right)\widehat\gamma_\ell,
\qquad \widehat\gamma_\ell=\frac1n\sum_{t=\ell+1}^{n}u_tu_{t-\ell}.$$

The mean standard error is $\sqrt{\widehat\Omega/n}$. Daily return inference uses
L=21, while monthly rank-IC inference uses L=3. Normal-reference HAC p-values and
intervals are asymptotic approximations; finite-sample accuracy is not guaranteed.

## 7. Selection-aware maximum-statistic bootstrap

The final-period family contains 12 fixed candidates plus the adaptive selector.
For column j of the aligned daily net-return matrix, let

$$T_j=\bar x_j/\widehat{se}_j,\qquad
T_{\max}=\max(0,\max_jT_j).$$

The null is that every declared procedure has nonpositive expected net return
relative to zero under the accounting convention. Each column is centered by its
sample mean, placing all candidates at the least-favorable zero-mean boundary.

Stationary bootstrap segments have geometrically distributed lengths with mean
21 trading days, random starts and circular wraparound. The **same sampled row
indices are used for every candidate**, preserving contemporaneous dependence.
For replicate b,

$$T^*_{b,j}=\bar x^*_{b,j}/\widehat{se}_j,\qquad
M_b=\max(0,\max_jT^*_{b,j}).$$

HAC scales are held fixed at the original sample estimates. The global p-value
uses $(1+\sum_b1\{M_b\ge T_{\max}\})/(B+1)$, and the single-step adjusted
p-value for candidate j uses the same formula with $T_j$ on the right-hand side.
The plus-one convention prevents reporting zero Monte Carlo p-values.

The procedure is a centered, fixed-scale, one-sided max test using a stationary
bootstrap. It is not advertised as Hansen SPA, a studentized-bootstrap refinement,
the Deflated Sharpe Ratio, White's unstandardized original statistic, or PBO/CSCV.
Its dependence and stationarity approximations are material. Setting all means to
zero can be conservative when some candidates are truly poor. Its adjustment
addresses the declared candidate family, not unrecorded human choices or all
later analyses; finite-sample size control is not guaranteed.

The study retains 2,000 replicates at mean block lengths 5, 21 and 63. The central
result uses 21; the favorable robustness setting is not selected. The frozen
winner's mean-return percentile interval uses separately seeded uncentered
stationary resamples and is not a selection-adjusted confidence region.

### Separate audit and studentization follow-up

The [follow-up protocol](../bootstrap_audit_protocol.json) compares the actual
primary function with a distinct bootstrap-t variant on shared indices:

$$T^{*,\mathrm{student}}_{b,j}
=\bar x^*_{b,j}/\widehat{se}^{\,*}_{b,j}.$$

Here $\widehat{se}^{\,*}_{b,j}$ is the same Bartlett HAC calculation applied to
the resampled series, including centering by that bootstrap sample's mean for
its autocovariances. The numerator retains the mean of the originally centered,
then resampled data. The maximum, one-sided null, plus-one p-value convention,
block length and HAC bandwidth are unchanged. This is a separately declared
approximation, not a replacement selected after inspecting the historical p-value.

Each null dataset has six Gaussian AR(1) columns with coefficient $a=0.2$,
unit marginal variance and equicorrelation $\rho=0.35$. Its exact stationary
sample-mean variance is

$$v_n=\frac{n+2\sum_{h=1}^{n-1}(n-h)a^h}{n^2}.$$

The known-covariance oracle compares $\max_j\bar x_j/\sqrt{v_n}$ to a Gaussian
maximum cutoff. For six equicorrelated standard normals its CDF is

$$F(c)=\int_{-\infty}^{\infty}\phi(z)
\Phi\!\left(\frac{c-\sqrt\rho z}{\sqrt{1-\rho}}\right)^6\,dz.$$

Numerical quadrature and a scalar root find $F(c)=0.95$. This oracle is available
only because the null generator is fully known. The audit reports Wilson
intervals across independent outer datasets, plus paired uncertainty in the
studentized-minus-fixed rejection rate. It does not transplant the oracle cutoff
or a measured size distortion to empirical returns. The primary best-of-50
illustration uses a different known-null calibrated comparison; it does not
validate either bootstrap method.

## 8. Rank information coefficient

For each month-end score at t, the execution-aligned forward label is the industry
compound return over indices t+2 through t+1+H, with H=21. The rank IC is the
cross-sectional Spearman correlation between scores and those labels. A complete
label must be observed and must end within the reported period. Future labels
are used only for diagnostics. Monthly ICs may still be dependent; their intervals
use HAC rather than pretending each cross-sectional stock rank is independent.

## 9. Known-null selection experiment

The synthetic experiment has 50 zero-mean candidate series, 756 observations,
AR(1) coefficient 0.2 and shared innovation correlation 0.35. A 200-observation
burn-in precedes measurement. Each replicate records the largest HAC t-statistic.
The experiment compares one prespecified candidate, the selected maximum with a
naive normal threshold, a Bonferroni threshold and a known-null max threshold.

The known-null threshold is calibrated using 2,000 **independent** simulation
replicates, then evaluated on a separate 1,000-replication RNG stream. It is an
illustration of the selection problem, not the empirical bootstrap and not a
recipe for knowing an actual financial data-generating process. Wilson intervals
describe Monte Carlo uncertainty in the probability of at least one false rejection.

## 10. Cost thresholds and subperiods

All candidates are evaluated at 0, 5, 10, 25 and 50 bps one-way costs. The reported
first-order break-even estimate is

$$10^4\frac{\text{zero-cost annual arithmetic mean}}
{\text{zero-cost annual traded-notional turnover}},$$

clipped to zero if the zero-cost mean is nonpositive. It is not an exact CAGR
break-even root, transaction-cost estimate or capacity calculation. Subperiod
statistics use slices of the actual continuous final-period return path, with
boundaries fixed before evaluation; portfolios are not reset to flatter each slice.

