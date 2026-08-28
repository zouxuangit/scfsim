"""Analytical benchmarks used to verify the simulation engine.

Simulation engines of this kind are easy to get subtly wrong, so SCFSim
ships reference quantities that are computed *without* running the model
and that the engine is tested against (``tests/test_benchmark.py``).

When the trade-graph channels are isolated, contagion becomes directional
and its support is an exactly known graph object:

* supply channel alone -- a failed supplier destroys its buyers' ability to
  deliver, so distress can only travel supplier -> buyer: the affected set
  is contained in the **descendants** of the seeds
  (:func:`supply_reachable_set`);
* demand channel alone -- a distressed buyer cuts its order book, so
  distress can only travel buyer -> supplier: the affected set is contained
  in the **ancestors** of the seeds (:func:`demand_reachable_set`).

Because ordinary operating losses also produce defaults that have nothing
to do with contagion, these bounds constrain the *attributable* cascade:
the defaults observed with seeds minus those observed in an otherwise
identical run without seeds (:func:`attributable_defaults`).
"""
from __future__ import annotations

import copy
from typing import Dict, Iterable, Set

import networkx as nx

from .config import SimulationConfig


def _firms_only(g: nx.DiGraph, nodes: Iterable[str]) -> Set[str]:
    return {n for n in nodes if g.nodes[n].get("kind") == "firm"}


def supply_reachable_set(g: nx.DiGraph, seeds: Iterable[str]) -> Set[str]:
    """Firms reachable from ``seeds`` along trade edges (supplier -> buyer).

    Upper bound on the support of the cascade when the supply-disruption
    channel acts alone.
    """
    reach: Set[str] = set()
    for s in seeds:
        if s in g:
            reach.add(s)
            reach |= nx.descendants(g, s)
    return _firms_only(g, reach)


def demand_reachable_set(g: nx.DiGraph, seeds: Iterable[str]) -> Set[str]:
    """Firms that can reach ``seeds`` along trade edges (buyer -> supplier).

    Upper bound on the support of the cascade when the demand-contraction
    channel acts alone.
    """
    reach: Set[str] = set()
    for s in seeds:
        if s in g:
            reach.add(s)
            reach |= nx.ancestors(g, s)
    return _firms_only(g, reach)


def attributable_defaults(treated, control) -> Set[str]:
    """Defaults present in the seeded run but not in the matched control.

    ``treated`` and ``control`` are :class:`~scfsim.metrics.RunResult`
    objects from two runs that differ only in the seed defaults.
    """
    return set(treated.defaulted_firms) - set(control.defaulted_firms)


def isolated_channel_configs(base: SimulationConfig
                             ) -> Dict[str, SimulationConfig]:
    """Ablation configs switching the channels on one at a time.

    Keys: ``"none"``, ``"counterparty"``, ``"supply"``, ``"demand"``,
    ``"credit_crunch"`` and ``"all"``. This measures the *first-order*
    effect of each channel acting alone.
    """
    names = ("counterparty", "supply", "demand", "credit_crunch")
    variants: Dict[str, SimulationConfig] = {}
    for key in ("none",) + names + ("all",):
        cfg = copy.deepcopy(base)
        for n in names:
            setattr(cfg.channels, n, key in (n, "all"))
        variants[key] = cfg
    return variants


def leave_one_out_configs(base: SimulationConfig
                          ) -> Dict[str, SimulationConfig]:
    """Ablation configs switching the channels off one at a time.

    Keys: ``"all"`` and ``"without_<channel>"``. Second-order channels --
    notably the credit crunch, which only bites once other channels have
    eroded bank capital -- contribute almost nothing when isolated but a
    measurable amount when removed from the fully coupled model, so both
    ablation designs are needed to characterise them.
    """
    names = ("counterparty", "supply", "demand", "credit_crunch")
    variants: Dict[str, SimulationConfig] = {}
    full = copy.deepcopy(base)
    for n in names:
        setattr(full.channels, n, True)
    variants["all"] = full
    for drop in names:
        cfg = copy.deepcopy(base)
        for n in names:
            setattr(cfg.channels, n, n != drop)
        variants[f"without_{drop}"] = cfg
    return variants
