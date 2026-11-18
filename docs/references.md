# Sources and implementation provenance

## Data provider

Kenneth R. French Data Library,
[49 Industry Portfolios](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html),
daily value-weighted return panel. The
[library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)
provides the source dataset and industry definitions. The provider's dataset and
linked definitions are not relicensed as MIT. See [data rights](../data/README.md).

## Primary methodological references

1. Halbert White (2000), *A Reality Check for Data Snooping*, Econometrica 68(5),
   1097–1126. [Paper](https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf).
   Motivates accounting for the full search family and preserving joint dependence
   when measuring the best observed result. This repository uses a clearly specified
   fixed-scale HAC-normalized max statistic rather than claiming to reproduce
   White's original unstandardized implementation.
2. David H. Bailey, Jonathan M. Borwein, Marcos López de Prado and Qiji Jim Zhu
   (2015 revision), *The Probability of Backtest Overfitting*.
   [Author-hosted paper](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).
   Motivates the distinction between an apparent backtest winner and a reliable
   research conclusion. This project does **not** implement or label its result as
   PBO or combinatorially symmetric cross-validation.
3. Whitney K. Newey and Kenneth D. West (1987), *A Simple, Positive Semi-Definite,
   Heteroskedasticity and Autocorrelation Consistent Covariance Matrix*, Econometrica
   55(3), 703–708. [NBER working-paper record](https://www.nber.org/papers/t0055).
   Supplies the Bartlett HAC construction used for mean uncertainty. Finite-sample
   normal-reference accuracy remains an assumption, not a guaranteed property.
4. Dimitris N. Politis and Joseph P. Romano (1994), *The Stationary Bootstrap*,
   Journal of the American Statistical Association 89(428), 1303–1313.
   [DOI](https://doi.org/10.1080/01621459.1994.10476870).
   Motivates resampling time-series segments with random lengths and shared row
   indices for dependent candidate-return vectors.

## Original work in this repository

All Python implementations, tests, execution/cost accounting, candidate-selection
pipeline, experiment definitions, null simulations, figures, notebooks and report
generation were developed for this repository. No existing strategy repository's
code, charts, performance numbers or author identity were copied.

The project's numerical claims are
backed by retained outputs, analytic and invariance tests, source fingerprints,
and reproducible commands. Established ideas—momentum, reversal, HAC estimation,
chronological evaluation and selection-aware inference—are not presented as new
discoveries. The contribution is their auditable implementation and the measured
negative result under one declared empirical design.

The source papers describe broader methods and assumptions than the particular
implementation here. Attribution does not imply their authors endorse this
project or that this project inherits all their theoretical guarantees.

