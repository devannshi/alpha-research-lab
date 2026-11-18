# Source data, rights and reproducibility

The source is the [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html),
specifically its [49 Industry Portfolios](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html)
daily value-weighted return panel. Download URL:

[49 Industry Portfolios daily CSV archive](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_Daily_CSV.zip).

The raw ZIP belongs under `data/raw/` and is **excluded from Git**. This repository's
MIT license covers its original implementation and documentation, not the provider's
dataset, source papers or external material. Users are responsible for the provider's
applicable data terms. No blanket permission to redistribute the source is implied.

`source_manifest.json` records the archive hash, size, CSV member hash, retrieved
coverage and missing-cell count. The initial source contains later observations
than the study cutoff; the pipeline excludes all returns after 2025-12-31 before
building features.

The source has many unavailable industry returns early in its history and one
missing software-industry observation in 1971. The development period begins in
1972, before any strategy outcomes were inspected, to avoid imputing held returns.
The complete analysis panel has 49 industries. Preperiod missing values affect
only rolling-feature eligibility until their windows become complete.

The current provider archive can change over time, including revisions to past
values. The downloader therefore rejects an unexpected hash by default. To make a
new-vintage replication, pass `--allow-revised-data`; its new fingerprint is written
to that run's manifest and the original recorded manifest is preserved. Exact
reproduction of the published run requires the recorded archive bytes.

The published repository includes transformed research outputs—candidate returns,
weights, selection diagnostics, figures and summary statistics—rather than the
49-column provider return panel. A reviewer can inspect all reported conclusions
without downloading the raw archive.

