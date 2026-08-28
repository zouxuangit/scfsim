"""Plotting helpers for SCFSim results (matplotlib).

The backend is left untouched: SCFSim never calls ``matplotlib.use()``, so
these helpers work unchanged inside notebooks and interactive sessions. On
a headless machine, set ``MPLBACKEND=Agg`` in the environment.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

from .metrics import RunResult

_LABELS = {
    "counterparty": "Counterparty\nloss only",
    "supply": "Supply\ndisruption only",
    "demand": "Demand\ncontraction only",
    "credit_crunch": "Credit\ncrunch only",
    "none": "No contagion\nchannel",
    "all": "All channels\n(coupled)",
}


def plot_scenario_comparison(batches: Dict[str, List[RunResult]],
                             save: Optional[str] = None):
    """Compare scenarios: default-share trajectories and cascade histograms.

    ``batches`` maps a scenario label to a list of :class:`RunResult`.
    Returns the matplotlib figure.
    """
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    colors = plt.cm.tab10.colors

    for i, (label, results) in enumerate(batches.items()):
        series = np.array([r.default_share for r in results])
        mean = series.mean(axis=0)
        lo, hi = (np.percentile(series, q, axis=0) for q in (10, 90))
        x = np.arange(series.shape[1])
        axes[0].plot(x, mean, label=label, color=colors[i % 10], lw=2)
        axes[0].fill_between(x, lo, hi, color=colors[i % 10], alpha=0.18)

        shares = [r.summary["final_default_share"] for r in results]
        axes[1].hist(shares, bins=np.linspace(0, 1, 26), alpha=0.55,
                     label=label, color=colors[i % 10])

    axes[0].set_xlabel("Period")
    axes[0].set_ylabel("Share of defaulted firms")
    axes[0].set_title("Default propagation (mean, 10-90% band)")
    axes[0].legend(frameon=False)
    axes[1].set_xlabel("Final default share")
    axes[1].set_ylabel("Monte-Carlo runs")
    axes[1].set_title("Distribution of cascade outcomes")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
    return fig


def plot_sensitivity(sweeps: Dict[str, List[Dict]], xlabel: str,
                     metric: str = "mean_default_share",
                     baseline: Optional[Dict[str, float]] = None,
                     ax=None, save: Optional[str] = None):
    """Plot one line per scenario from :func:`scfsim.sweep.sweep` output.

    ``baseline`` optionally maps a label to a horizontal reference level
    (e.g. the traditional-SCF outcome), which makes the break-even point
    where the two regimes cross directly readable.
    """
    import matplotlib.pyplot as plt

    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
    colors = plt.cm.tab10.colors
    for i, (label, rows) in enumerate(sweeps.items()):
        xs = [r["value"] for r in rows]
        ys = [r[metric] for r in rows]
        ax.plot(xs, ys, marker="o", ms=4, lw=1.8, color=colors[i % 10],
                label=label)
    if baseline:
        for label, level in baseline.items():
            ax.axhline(level, ls="--", lw=1.4, color="0.35")
            ax.text(ax.get_xlim()[1], level, f" {label}", va="center",
                    fontsize=8, color="0.35")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(metric.replace("_", " "))
    ax.legend(frameon=False, fontsize=9)
    if fig is not None:
        fig.tight_layout()
        if save:
            fig.savefig(save, dpi=200, bbox_inches="tight")
    return ax


def plot_channel_ablation(ablation: Dict[str, Dict],
                          metric: str = "mean_cascade_size",
                          order: Optional[Sequence[str]] = None,
                          ax=None, save: Optional[str] = None):
    """Bar chart of an ablation produced by :func:`scfsim.sweep.ablation`."""
    import matplotlib.pyplot as plt

    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
    keys = list(order or ablation.keys())
    vals = [ablation[k][metric] for k in keys]
    bars = ax.bar(range(len(keys)), vals, color="#4c78a8", width=0.6)
    if "all" in keys:
        bars[keys.index("all")].set_color("#e45756")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([_LABELS.get(k, k) for k in keys], fontsize=8)
    ax.set_ylabel(metric.replace("_", " "))
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}", ha="center",
                va="bottom", fontsize=8.5)
    if fig is not None:
        fig.tight_layout()
        if save:
            fig.savefig(save, dpi=200, bbox_inches="tight")
    return ax


def plot_channel_contributions(isolated: Dict[str, Dict],
                               loo: Dict[str, Dict],
                               metric: str = "mean_cascade_size",
                               channels: Optional[Sequence[str]] = None,
                               ax=None, save: Optional[str] = None):
    """Compare first-order and marginal contributions of each channel.

    ``isolated`` comes from an :func:`scfsim.ablation` over
    :func:`scfsim.isolated_channel_configs` (each channel acting alone) and
    ``loo`` from one over :func:`scfsim.leave_one_out_configs` (each channel
    removed from the coupled model). A channel whose two bars differ is one
    that interacts with the others rather than acting additively.
    """
    import matplotlib.pyplot as plt

    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(6.4, 4.0))
    names = list(channels or ("counterparty", "supply", "demand",
                              "credit_crunch"))
    base = isolated["none"][metric]
    full = loo["all"][metric]
    first = [isolated[c][metric] - base for c in names]
    marginal = [full - loo[f"without_{c}"][metric] for c in names]

    x = np.arange(len(names))
    w = 0.38
    ax.bar(x - w / 2, first, w, label="Acting alone (first order)",
           color="#4c78a8")
    ax.bar(x + w / 2, marginal, w, label="Removed from coupled model "
           "(marginal)", color="#e45756")
    for xi, v in zip(x - w / 2, first):
        ax.text(xi, v, f"{v:+.1f}", ha="center", va="bottom", fontsize=8)
    for xi, v in zip(x + w / 2, marginal):
        ax.text(xi, v, f"{v:+.1f}", ha="center", va="bottom", fontsize=8)
    short = {"counterparty": "Counterparty\nloss", "supply": "Supply\ndisruption",
             "demand": "Demand\ncontraction", "credit_crunch": "Credit\ncrunch"}
    ax.set_xticks(x)
    ax.set_xticklabels([short.get(c, c) for c in names], fontsize=8.5)
    ax.set_ylabel(f"contribution to {metric.replace('_', ' ')}")
    ax.legend(frameon=False, fontsize=8.5)
    if fig is not None:
        fig.tight_layout()
        if save:
            fig.savefig(save, dpi=200, bbox_inches="tight")
    return ax
