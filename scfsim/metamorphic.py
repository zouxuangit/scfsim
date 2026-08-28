"""Metamorphic relations: verification without a known answer.

Every check SCFSim had before this module shares a weakness: someone had
to know in advance what the right answer looked like. The reachability
bounds encode a fact about graphs; the accounting identities encode
book-keeping; the economic properties and comparative statics encode
economics that a person wrote down. All of them are blind to a failure
mode nobody anticipated — which is exactly the limitation the audit of
v0.5 identified.

Metamorphic testing attacks that gap from the other side. Instead of
asking "is this output correct?", it asks "if I transform the input in a
way that *must not* change the output, does the output change?". No
oracle is required, and the relations are generic rather than derived
from bugs already found.

Three relations hold for SCFSim by construction:

* :func:`scaled` — **dimensional homogeneity.** Every quantity in the
  model is either a ratio or a monetary amount proportional to the core
  enterprise's order volume, so multiplying that volume by any positive
  constant must leave every default outcome unchanged. An absolute
  constant or a mis-scaled term anywhere in the engine breaks this.
* :func:`relabelled` — **anonymity.** Firm names are labels, not data.
  Permuting them within tiers, and permuting the seed shock with them,
  must leave aggregate outcomes unchanged. Any dependence on iteration
  order or on name ordering breaks this.
* :func:`truncated` — **no lookahead.** A run of ``n`` periods must
  reproduce the first ``n`` periods of a longer run exactly. Any use of
  information that is not yet available at time ``t`` breaks this.

The helpers here build the transformed inputs; the assertions live in
``tests/test_metamorphic.py``.
"""
from __future__ import annotations

import copy
from typing import Dict, Optional, Tuple

import networkx as nx

from .config import SimulationConfig
from .network import CORE


def scaled(cfg: SimulationConfig, factor: float) -> SimulationConfig:
    """Return ``cfg`` with the monetary unit multiplied by ``factor``.

    Only the core enterprise's order volume is touched: everything else in
    the model is a ratio of it, so this rescales the entire economy.
    """
    if factor <= 0:
        raise ValueError("factor must be positive")
    out = copy.deepcopy(cfg)
    out.firm.core_demand = cfg.firm.core_demand * factor
    return out


def relabelled(g: nx.DiGraph, rng) -> Tuple[nx.DiGraph, Dict[str, str]]:
    """Permute firm names within each tier; return the graph and the mapping.

    The core enterprise and the banks keep their identities: the relation
    under test is that *which* firm carries a given name is irrelevant, not
    that the structure may change.
    """
    by_tier: Dict[int, list] = {}
    for node, data in g.nodes(data=True):
        if data.get("kind") != "firm":
            continue
        by_tier.setdefault(data["tier"], []).append(node)

    mapping: Dict[str, str] = {}
    for names in by_tier.values():
        ordered = sorted(names)
        shuffled = list(ordered)
        rng.shuffle(shuffled)
        mapping.update(dict(zip(ordered, shuffled)))
    mapping[CORE] = CORE
    for node, data in g.nodes(data=True):
        if data.get("kind") == "bank":
            mapping[node] = node

    relabelled_graph = nx.relabel_nodes(g, mapping, copy=True)
    return relabelled_graph, mapping


def truncated(cfg: SimulationConfig, n_periods: int) -> SimulationConfig:
    """Return ``cfg`` stopped after ``n_periods`` periods."""
    if n_periods < 1:
        raise ValueError("n_periods must be at least 1")
    out = copy.deepcopy(cfg)
    out.n_periods = n_periods
    return out


def outcome_signature(result, places: int = 9) -> tuple:
    """A comparable fingerprint of a run's aggregate trajectory.

    Rounded so that floating-point noise from a different order of
    summation does not masquerade as a broken relation.
    """
    return (
        tuple(round(x, places) for x in result.default_share),
        round(result.summary["final_default_share"], places),
        result.summary["cascade_size"],
    )
