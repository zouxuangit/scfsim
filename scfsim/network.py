"""Generation of layered supply chain finance networks.

The generator produces a :class:`networkx.DiGraph` with three node types:

* ``core``  -- the single core enterprise (tier 0, the ultimate buyer);
* ``firm``  -- suppliers arranged in tiers 1..T; edges point *supplier ->
  buyer* and carry ``share``: the fraction of the buyer's input sourced from
  that supplier;
* ``bank``  -- financial institutions; every core/firm node stores the id of
  its house bank in the ``bank`` attribute (bank nodes carry no trade edges).

Users may also supply any custom ``networkx.DiGraph`` that follows this
attribute convention, which is what makes the simulator reusable on real
mapped supply networks or on synthetic topologies from other generators.
"""
from __future__ import annotations

from typing import Optional

import networkx as nx
import numpy as np

from .config import NetworkConfig

CORE = "core-0"


def generate_network(cfg: NetworkConfig,
                     rng: Optional[np.random.Generator] = None) -> nx.DiGraph:
    """Build a random layered SCF network from ``cfg``.

    Every tier-1 firm sells to the core. Each firm in tier t>=2 sells to a
    Poisson-distributed number (>=1) of buyers in tier t-1; input shares on
    each buyer are normalised to sum to one. Firms are assigned to banks
    uniformly at random. Node attribute ``tier`` gives the tier (0 = core).
    """
    if rng is None:
        rng = np.random.default_rng(cfg.seed)

    g = nx.DiGraph()
    g.add_node(CORE, tier=0, kind="core", bank=int(rng.integers(cfg.n_banks)))

    tiers: list[list[str]] = [[CORE]]
    for t in range(1, cfg.n_tiers + 1):
        names = [f"firm-{t}-{i}" for i in range(cfg.firms_per_tier[t - 1])]
        for name in names:
            g.add_node(name, tier=t, kind="firm",
                       bank=int(rng.integers(cfg.n_banks)))
        tiers.append(names)

    for b in range(cfg.n_banks):
        g.add_node(f"bank-{b}", tier=-1, kind="bank")

    # tier-1 firms all sell to the core
    for name in tiers[1]:
        g.add_edge(name, CORE, share=0.0)

    # deeper tiers: each supplier picks >=1 buyers in the tier below
    for t in range(2, cfg.n_tiers + 1):
        buyers = tiers[t - 1]
        for name in tiers[t]:
            k = max(1, int(rng.poisson(cfg.avg_buyers_per_firm)))
            k = min(k, len(buyers))
            chosen = rng.choice(buyers, size=k, replace=False)
            for b in chosen:
                g.add_edge(name, b, share=0.0)

    # make sure every buyer has at least one supplier (except deepest tier)
    for t in range(1, cfg.n_tiers):
        for buyer in tiers[t]:
            if g.in_degree(buyer) == 0:
                supplier = tiers[t + 1][int(rng.integers(len(tiers[t + 1])))]
                g.add_edge(supplier, buyer, share=0.0)

    _normalise_shares(g, rng)
    return g


def _normalise_shares(g: nx.DiGraph, rng: np.random.Generator) -> None:
    """Draw random input shares per buyer and normalise them to one."""
    for node, data in g.nodes(data=True):
        if data.get("kind") == "bank":
            continue
        suppliers = [u for u, _ in g.in_edges(node)]
        if not suppliers:
            continue
        weights = rng.dirichlet(np.ones(len(suppliers)))
        for u, w in zip(suppliers, weights):
            g[u][node]["share"] = float(w)


def core_node(g: nx.DiGraph) -> str:
    """Name of the single ``kind == "core"`` node of ``g``.

    The engine identifies the anchor by this attribute, not by name, so a
    user-supplied network may call its core enterprise anything.
    """
    cores = [n for n, k in nx.get_node_attributes(g, "kind").items()
             if k == "core"]
    if len(cores) != 1:
        raise ValueError("network must contain exactly one 'core' node")
    return cores[0]


def validate_network(g: nx.DiGraph, tol: float = 1e-6) -> None:
    """Raise ``ValueError`` if ``g`` violates the attribute convention.

    The convention the engine relies on, beyond the attributes themselves:

    * the core is the only node at tier 0, and every firm has tier >= 1;
    * every trade edge points from a supplier to a buyer in a strictly
      lower tier, so demand can be propagated tier by tier;
    * a buyer's incoming shares sum to one (within ``tol``), so that the
      input share of each supplier is a fraction of the buyer's purchases;
    * every firm sells to at least one buyer, otherwise it has no sales.

    Bank ids are integers; bank nodes themselves are optional, and the
    engine creates a bank for every id that a firm names.
    """
    kinds = nx.get_node_attributes(g, "kind")
    core = core_node(g)
    for node, kind in kinds.items():
        if kind not in ("core", "firm", "bank"):
            raise ValueError(f"node {node!r} has unknown kind {kind!r}")
        if kind in ("core", "firm") and "bank" not in g.nodes[node]:
            raise ValueError(f"node {node!r} lacks a 'bank' attribute")
        if kind in ("core", "firm") and "tier" not in g.nodes[node]:
            raise ValueError(f"node {node!r} lacks a 'tier' attribute")
    if g.nodes[core]["tier"] != 0:
        raise ValueError(f"the core {core!r} must be at tier 0")
    for node, kind in kinds.items():
        if kind == "firm":
            if g.nodes[node]["tier"] < 1:
                raise ValueError(f"firm {node!r} must be at tier >= 1")
            if g.out_degree(node) == 0:
                raise ValueError(f"firm {node!r} sells to nobody")
    for u, v, data in g.edges(data=True):
        if kinds.get(u) == "bank" or kinds.get(v) == "bank":
            raise ValueError("bank nodes must not carry trade edges")
        if "share" not in data:
            raise ValueError(f"edge ({u!r}, {v!r}) lacks a 'share' attribute")
        if data["share"] < 0:
            raise ValueError(f"edge ({u!r}, {v!r}) has a negative share")
        if g.nodes[u]["tier"] <= g.nodes[v]["tier"]:
            raise ValueError(
                f"edge ({u!r}, {v!r}) does not point to a lower tier: "
                "trade edges run from supplier to buyer, and a buyer must "
                "sit in a lower tier than its supplier")
    for node, kind in kinds.items():
        if kind in ("core", "firm") and g.in_degree(node) > 0:
            total = sum(d["share"] for _, _, d in g.in_edges(node, data=True))
            if abs(total - 1.0) > tol:
                raise ValueError(f"incoming shares of {node!r} sum to "
                                 f"{total:.6g}, not 1")


def network_from_edges(edges, core: str, banks=1) -> nx.DiGraph:
    """Build a compliant network from ``(supplier, buyer, share)`` triples.

    This is the entry point for a mapped supply network. Tiers are inferred
    as the longest path from a firm to the core, so a supplier that sells
    to buyers at different depths is placed above the deeper one, which is
    what the tier-by-tier order propagation requires. Shares are taken as
    given and must sum to one per buyer (they are not normalised, so that
    a mapping error is reported rather than hidden). ``banks`` is either an
    integer -- firms are assigned to that many banks round-robin in name
    order -- or a mapping from node name to bank id; the core is given
    bank 0 unless the mapping says otherwise. The result is validated.
    """
    g = nx.DiGraph()
    g.add_node(core, kind="core")
    for supplier, buyer, share in edges:
        g.add_node(supplier, kind="firm")
        if buyer != core:
            g.add_node(buyer, kind="firm")
        g.add_edge(supplier, buyer, share=float(share))
    if not nx.is_directed_acyclic_graph(g):
        raise ValueError("the trade graph contains a cycle")
    # tier = longest path to the core along supplier -> buyer edges
    tier = {core: 0}
    for node in reversed(list(nx.topological_sort(g))):
        if node == core:
            continue
        buyers = [tier[b] for b in g.successors(node) if b in tier]
        if not buyers:
            raise ValueError(f"firm {node!r} has no path to the core {core!r}")
        tier[node] = max(buyers) + 1
    nx.set_node_attributes(g, tier, "tier")
    firms = sorted(n for n in g.nodes if n != core)
    if isinstance(banks, int):
        if banks < 1:
            raise ValueError("banks must be at least 1")
        assignment = {n: i % banks for i, n in enumerate(firms)}
        assignment[core] = 0
    else:
        assignment = dict(banks)
        assignment.setdefault(core, 0)
        missing = [n for n in firms if n not in assignment]
        if missing:
            raise ValueError(f"no bank assigned to {missing}")
    nx.set_node_attributes(g, assignment, "bank")
    for b in sorted(set(assignment.values())):
        g.add_node(f"bank-{b}", tier=-1, kind="bank")
    validate_network(g)
    return g
