"""Figures from the retained empirical research ledger and null experiment."""
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

TEAL, BLUE, ORANGE, GRAY = "#087f8c", "#203a5c", "#de764b", "#a5afbc"


def short_name(name):
    return (name.replace("momentum_", "Mom ").replace("reversal_", "Rev ")
            .replace("_skip", " skip ").replace("__inverse_volatility", " / inv-vol")
            .replace("__equal", " / equal").replace("adaptive_selector", "Annual selector"))


def _save(fig, directory, name):
    fig.savefig(directory / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def make_figures(output, protocol, ledger, holdout, winner, ew, costs, inference,
                 max_test, ic_summary, choices, null_summary, subperiods):
    out = Path(output) / "figures"
    out.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.titlesize": 12, "axes.titleweight": "bold",
                         "axes.spines.top": False, "axes.spines.right": False,
                         "text.color": BLUE, "axes.labelcolor": BLUE, "grid.alpha": .2,
                         "legend.frameon": False, "savefig.facecolor": "white"})
    validation = ledger[ledger.period == "validation"].set_index("candidate")
    test = ledger[ledger.period == "holdout"].set_index("candidate")
    order = validation.sort_values("sharpe").index
    fig, ax = plt.subplots(figsize=(12, 7), layout="constrained")
    for i, name in enumerate(order):
        a, b = validation.loc[name].sharpe, test.loc[name].sharpe
        ax.plot([a, b], [i, i], color=GRAY, linewidth=2)
        ax.scatter(a, i, color=ORANGE, s=50, label="2005–2014 selection window" if i == 0 else None)
        ax.scatter(b, i, color=TEAL, s=65, label="2015–2025 final period" if i == 0 else None,
                   edgecolor=BLUE if name == winner else "none", linewidth=2)
        if name == winner:
            ax.annotate("Frozen winner", (b, i), xytext=(8, 8), textcoords="offset points", fontsize=9, weight="bold")
    ax.axvline(0, color=GRAY, linewidth=1)
    ax.set_yticks(range(len(order)), [short_name(n) for n in order])
    ax.set(xlabel="Annualized net Sharpe at 10 bps one-way cost",
           title="Every declared variant: validation performance versus final-period performance")
    ax.legend(loc="lower right")
    ax.grid(axis="x")
    _save(fig, out, "selection_decay")

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, layout="constrained")
    for name, frame in holdout.items():
        if name not in {winner, "adaptive_selector"}:
            axes[0].plot(frame.index, frame.nav, color=GRAY, alpha=.3, linewidth=.7)
    for name, label, color in [(winner, "Frozen validation winner", TEAL), ("adaptive_selector", "Annual past-only selector", ORANGE)]:
        frame = holdout[name]
        axes[0].plot(frame.index, frame.nav, color=color, linewidth=2, label=label)
        nav = np.r_[1, frame.nav.to_numpy()]
        dd = nav / np.maximum.accumulate(nav) - 1
        axes[1].plot(frame.index, dd[1:] * 100, color=color, linewidth=1.5, label=label)
    axes[0].axhline(1, color=BLUE, linestyle="--", linewidth=1, label="Zero-return cash benchmark")
    axes[0].set(ylabel="Net portfolio equity (start = 1)", title="Historical final period: selection is fixed before evaluation")
    axes[1].set(ylabel="Drawdown (%)", xlabel="Date", title="The path of risk, not only the endpoint")
    for ax in axes:
        ax.legend(fontsize=9)
        ax.grid(True)
    _save(fig, out, "holdout_equity")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    for name, sub in costs.groupby("candidate"):
        highlight = name in {winner, "adaptive_selector"}
        color = TEAL if name == winner else ORANGE if name == "adaptive_selector" else GRAY
        label = "Frozen winner" if name == winner else "Annual selector" if name == "adaptive_selector" else None
        for ax, metric in zip(axes, ["annual_mean", "sharpe"]):
            y = sub[metric] * (100 if metric == "annual_mean" else 1)
            ax.plot(sub.cost_bps, y, "o-" if highlight else "-", color=color,
                    linewidth=2 if highlight else .7, alpha=1 if highlight else .35, label=label)
    axes[0].set(title="Net mean return after turnover costs", ylabel="Annualized arithmetic mean (%)", xlabel="One-way cost (basis points)")
    axes[1].set(title="Cost can change the economic conclusion", ylabel="Annualized net Sharpe", xlabel="One-way cost (basis points)")
    for ax in axes:
        ax.axhline(0, color=BLUE, linewidth=.8)
        ax.grid(True)
        ax.legend(fontsize=9)
    _save(fig, out, "cost_frontier")

    table = inference.sort_values("hac_t")
    fig, axes = plt.subplots(1, 2, figsize=(13, 7), layout="constrained")
    y = np.arange(len(table))
    axes[0].barh(y, table.hac_t, color=[TEAL if n == winner else GRAY for n in table.candidate])
    axes[0].axvline(1.645, color=ORANGE, linestyle="--", label="Unadjusted normal 5% cutoff")
    axes[0].set_yticks(y, [short_name(n) for n in table.candidate])
    axes[0].set(xlabel="HAC t-statistic of mean net return", title="Apparent evidence before selection adjustment")
    axes[0].legend(fontsize=8)
    axes[1].scatter(table.individual_bootstrap_p, y, color=GRAY, label="Individual bootstrap p", s=40)
    axes[1].scatter(table.family_adjusted_p, y, color=TEAL, label="Family-adjusted p", s=45)
    for i, row in enumerate(table.itertuples()):
        axes[1].plot([row.individual_bootstrap_p, row.family_adjusted_p], [i, i], color=GRAY, linewidth=1)
    axes[1].axvline(.05, color=ORANGE, linestyle="--")
    axes[1].set(xscale="log", xlabel="One-sided p-value (log scale)", title="All 12 variants + adaptive procedure remain in the family")
    axes[1].set_yticks(y, [])
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis="x")
    _save(fig, out, "selection_adjusted_inference")

    fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    signals = [s["name"] for s in protocol["signals"]]
    for offset, period, color in [(-.2, "development", GRAY), (0, "validation", ORANGE), (.2, "holdout", TEAL)]:
        tab = ic_summary[ic_summary.period == period].set_index("signal").loc[signals]
        ax.errorbar(np.arange(len(signals)) + offset, tab["mean"],
                    yerr=[tab["mean"] - tab.lower, tab.upper - tab["mean"]], fmt="o", capsize=4,
                    color=color, label=period.title())
    ax.set_xticks(range(len(signals)), [short_name(n).replace(" ", "\n", 1) for n in signals])
    ax.axhline(0, color=BLUE, linewidth=.8)
    ax.set(ylabel="Mean cross-sectional rank IC", title="Does a lagged score predict the execution-aligned next 21 returns?")
    ax.legend(ncols=3)
    ax.grid(axis="y")
    _save(fig, out, "rank_ic")

    fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    labels = ["One fixed\nstrategy", "Best of 50,\nnaive threshold", "Best of 50,\nBonferroni", "Best of 50,\nknown-null max"]
    colors = [GRAY, ORANGE, BLUE, TEAL]
    for i, row in enumerate(null_summary.itertuples()):
        ax.bar(i, row.false_positive_rate * 100, color=colors[i], width=.6)
        ax.errorbar(i, row.false_positive_rate * 100,
                    yerr=[[(row.false_positive_rate - row.lower) * 100], [(row.upper - row.false_positive_rate) * 100]],
                    color=BLUE, capsize=4, fmt="none")
        ax.text(i, row.upper * 100 + 1.5, f"{row.false_positive_rate:.1%}", ha="center", weight="bold")
    ax.axhline(5, color=BLUE, linestyle="--", label="Nominal 5% level")
    ax.set_xticks(range(4), labels)
    ax.set(ylabel="Probability of at least one false positive (%)",
           title="Known-null simulation: choosing the best strategy changes the question")
    ax.legend()
    ax.grid(axis="y")
    _save(fig, out, "null_selection")

    annual = choices.copy()
    annual["year"] = annual.execution_date.dt.year
    selected = annual.groupby("year").candidate.first()
    all_names = sorted(validation.index)
    grid = np.zeros((len(all_names), len(selected)))
    for j, name in enumerate(selected):
        grid[all_names.index(name), j] = 1
    fig, ax = plt.subplots(figsize=(12, 6), layout="constrained")
    ax.imshow(grid, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_yticks(range(len(all_names)), [short_name(n) for n in all_names])
    ax.set_xticks(range(len(selected)), selected.index, rotation=45)
    ax.set(xlabel="Trading year (selection ends December of the previous year)",
           title="An adaptive selector is a trading strategy with its own turnover")
    _save(fig, out, "annual_selection")

    subperiods = subperiods.copy()
    subperiods["window"] = subperiods.start.str[:4] + "–" + subperiods.end.str[:4]
    table = subperiods.pivot(index="candidate", columns="window", values="sharpe").loc[sorted(holdout)]
    fig, ax = plt.subplots(figsize=(10, 7), layout="constrained")
    lim = max(1, abs(table.values).max())
    im = ax.imshow(table.values, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_yticks(range(len(table)), [short_name(n) for n in table.index])
    ax.set_xticks(range(len(table.columns)), table.columns)
    for i in range(len(table)):
        for j in range(len(table.columns)):
            value = table.iloc[i, j]
            ax.text(j, i, f"{value:+.2f}", ha="center", va="center",
                    color="white" if abs(value) > .6 * lim else BLUE)
    ax.set(title="Prespecified subperiods reveal unstable performance", xlabel="Final-period subwindow")
    fig.colorbar(im, ax=ax, label="Net Sharpe at 10 bps")
    _save(fig, out, "subperiod_robustness")

