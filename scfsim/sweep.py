"""Parameter sweeps for sensitivity analysis.

A sweep varies one dotted configuration path over a grid of values,
re-running a matched Monte-Carlo batch at each point. This is the tool
used to answer questions of the form "at what fraud rate does deep-tier
financing stop paying off?".
"""
from __future__ import annotations

import copy
import itertools
from typing import Dict, Iterable, List, Sequence

from .config import SimulationConfig
from .metrics import batch_summary
from .simulation import run_batch

#: Keyword arguments every driver below forwards to :func:`run_batch`
#: unchanged: ``n_jobs`` and a fixed ``network``.

CHANNELS = ("counterparty", "supply", "demand", "credit_crunch")


def set_by_path(cfg: SimulationConfig, path: str, value) -> None:
    """Set ``cfg`` attribute addressed by a dotted path, e.g.
    ``"scenario.bc_fraud_prob"`` or ``"firm.initial_cash_ratio"``."""
    parts = path.split(".")
    target = cfg
    for p in parts[:-1]:
        target = getattr(target, p)
    if not hasattr(target, parts[-1]):
        raise AttributeError(f"unknown configuration path: {path!r}")
    setattr(target, parts[-1], value)


def sweep(config: SimulationConfig, path: str, values: Sequence,
          n_runs: int = 50, base_seed: int = 0, n_jobs: int = 1,
          network=None) -> List[Dict]:
    """Run one matched Monte-Carlo batch per value of ``path``.

    Returns a list of dicts, each holding the swept ``value`` plus every
    field of :func:`scfsim.batch_summary` for that point. Seeds are matched
    across grid points, so differences are attributable to the parameter
    rather than to sampling noise.
    """
    rows: List[Dict] = []
    for v in values:
        cfg = copy.deepcopy(config)
        set_by_path(cfg, path, v)
        row = {"value": v}
        row.update(batch_summary(run_batch(cfg, n_runs=n_runs,
                                           base_seed=base_seed,
                                           n_jobs=n_jobs, network=network)))
        rows.append(row)
    return rows


def ablation(configs: Dict[str, SimulationConfig], n_runs: int = 50,
             base_seed: int = 0, n_jobs: int = 1,
             network=None) -> Dict[str, Dict]:
    """Run a matched batch for every named configuration variant."""
    return {name: batch_summary(run_batch(cfg, n_runs=n_runs,
                                          base_seed=base_seed, n_jobs=n_jobs,
                                          network=network))
            for name, cfg in configs.items()}


def grid_sweep(config: SimulationConfig, grid: Dict[str, Sequence],
               n_runs: int = 50, base_seed: int = 0,
               max_simulations: int = 20000,
               progress: bool = False, n_jobs: int = 1,
               network=None) -> List[Dict]:
    """Sweep several configuration paths jointly over their Cartesian product.

    ``grid`` maps dotted paths to the values each should take, e.g.
    ``{"scenario.bc_visibility_depth": [1, 2, 3],
       "scenario.bc_haircut": [0.05, 0.25]}``. Each returned row holds the
    value of every swept path plus the batch summary at that point, which
    makes interaction effects between frictions directly inspectable.

    Because the cost is the product of the grid sizes and ``n_runs``, the
    function refuses to start a sweep larger than ``max_simulations``
    rather than running silently for hours; pass ``progress=True`` to see
    grid points as they complete.
    """
    paths = list(grid)
    n_points = 1
    for p in paths:
        n_points *= len(grid[p])
    total = n_points * n_runs
    if total > max_simulations:
        raise ValueError(
            f"grid_sweep would run {n_points} grid points x {n_runs} paths "
            f"= {total} simulations, above max_simulations={max_simulations}. "
            "Coarsen the grid, lower n_runs, or raise max_simulations "
            "deliberately.")
    rows: List[Dict] = []
    for i, combo in enumerate(itertools.product(*(grid[p] for p in paths)), 1):
        if progress:
            print(f"  grid point {i}/{n_points}", flush=True)
        cfg = copy.deepcopy(config)
        for path, value in zip(paths, combo):
            set_by_path(cfg, path, value)
        row = {p: v for p, v in zip(paths, combo)}
        row.update(batch_summary(run_batch(cfg, n_runs=n_runs,
                                           base_seed=base_seed,
                                           n_jobs=n_jobs, network=network)))
        rows.append(row)
    return rows


def channel_decomposition(isolated: Dict[str, Dict], loo: Dict[str, Dict],
                          metric: str = "mean_cascade_size",
                          channels: Sequence[str] = CHANNELS) -> Dict:
    """Decompose a coupled outcome into per-channel and interaction terms.

    Returns the baseline with no channel active, the fully coupled outcome,
    each channel's first-order effect (acting alone) and marginal effect
    (removed from the coupled model), and the interaction term -- the gap
    between the coupled effect and the sum of the first-order effects. A
    negative interaction means the channels overlap: the same firm can be
    pushed into default by more than one of them, so their effects do not
    add up.
    """
    base = isolated["none"][metric]
    full = loo["all"][metric]
    per = {c: {"alone": isolated[c][metric] - base,
               "marginal": full - loo[f"without_{c}"][metric]}
           for c in channels}
    solo_sum = sum(v["alone"] for v in per.values())
    return {
        "metric": metric,
        "baseline_no_channels": base,
        "coupled": full,
        "coupled_effect": full - base,
        "sum_of_first_order": solo_sum,
        "interaction": (full - base) - solo_sum,
        "channels": per,
    }
