# Research discussion guide

## The one-minute account

The project investigates whether an industry momentum/reversal signal survives
chronological selection and execution costs. It declares a family of 12 variants,
selects one using 2005–2014 data, and evaluates it unchanged over 2015–2025. The
winner fails to establish a net edge. A joint block-bootstrap test also finds no
credible positive result in the full declared family. A separate known-null
simulation shows why selecting the best of many strategies changes false-positive
rates. The useful artifact is a rigorous falsification pipeline, not a flattering
equity curve.

## Be able to defend these choices

**Why use the next trading close?** The source gives close-to-close returns, not
opening or intraday prices. A signal observed at month-end close cannot justify
earning the return that ends at the next close while claiming execution at that
same next close. Trades happen after that return, and new holdings earn subsequent
returns. The extra delay is explicit and tested.

**Why solve a scalar transaction-cost equation?** Target weights are fractions of
post-cost equity, while traded notional and costs are measured relative to pre-trade
equity. Ignoring that distinction either misses costs or shifts the stated leverage.
The scalar equation is a contraction at the declared cost/gross levels and has a
simple analytic initial-entry check.

**Why keep losing candidates in the family test?** Removing them after seeing
results changes the search family. Resampling the whole aligned matrix preserves
correlation among variants; perfect duplicate candidates do not increase the max
penalty. The tests verify that invariance.

**Does the bootstrap repair every research choice?** No. It approximates a defined
family-wise null under temporal regularity assumptions. It does not account for
unrecorded ideas, arbitrary changes to the family, historical revisions or every
diagnostic that a researcher chooses to inspect later.

**Why is the annual adaptive selector not a splice of return series?** When a new
candidate is selected, the portfolio has actual current holdings. The execution
engine trades from those holdings to the new target and charges turnover. Splicing
candidate returns would omit transition costs and could inherit unearned positions.

**What does a negative finding show?** It shows that this implementation did not
establish an edge for the declared family under the stated data and cost convention.
It does not prove markets are efficient or that every implementation of momentum
is useless. It demonstrates the ability to reject a hypothesis without hiding
unfavorable evidence.

**Is a positive mean long-short return alpha?** Not necessarily. The portfolio is
dollar-neutral at rebalancing, not factor-neutral. Industry exposures, market beta,
short financing and data-construction effects can matter. A security-level study
and a risk model would be needed for a stronger claim.

## Reproduction exercises

1. Reconstruct final NAV from the committed daily net returns and reconcile cost
   days against the decision/execution log.
2. Change only observations after a chosen date and verify earlier scores,
   schedules and annual choices remain identical.
3. Duplicate a candidate return column and confirm that the joint max distribution
   is unchanged when dependence is preserved.
4. Compare all three declared bootstrap block lengths without selecting the one
   that yields the smallest p-value.
5. Re-run the known-null experiment with a different seed and check whether its
   observed rejection rates are compatible with the reported Monte Carlo intervals.
6. Replicate using a revised provider archive and label the result as a different
   vintage, rather than silently treating a hash mismatch as the same dataset.

