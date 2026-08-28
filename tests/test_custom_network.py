"""Bringing your own network.

The paper's reuse claim rests on ``validate_network`` being the extension
point for mapped supply networks. Until v0.15.0 the engine identified the
core enterprise by the name ``core-0`` and created banks from the
configured count rather than from the ids the network names, so a graph
that passed validation could still fail or miscount. These tests pin the
contract a user-supplied graph gets.
"""
import networkx as nx
import pytest

from scfsim import (Simulation, SimulationConfig, ablation, batch_summary,
                    core_node, generate_network, leave_one_out_configs,
                    network_from_edges, outcome_signature, run_batch, sweep,
                    supply_reachable_set, validate_network)
from scfsim.config import NetworkConfig


EDGES = [
    # supplier, buyer, share of the buyer's inputs
    ("Alpha Castings", "Acme", 0.6), ("Beta Electronics", "Acme", 0.4),
    ("Gamma Steel", "Alpha Castings", 1.0),
    ("Delta Chips", "Beta Electronics", 0.7), ("Epsilon Boards", "Beta Electronics", 0.3),
    ("Zeta Ore", "Gamma Steel", 1.0),
    ("Eta Silicon", "Delta Chips", 0.5), ("Theta Silicon", "Delta Chips", 0.5),
    ("Eta Silicon", "Epsilon Boards", 1.0),
]


def cfg(periods=20, seed=3):
    c = SimulationConfig(n_periods=periods, seed=seed)
    c.shock.seed_defaults = 1
    c.shock.seed_tier = 2
    return c


# ------------------------------------------------------------------ #
# the builder
# ------------------------------------------------------------------ #

def test_edge_list_builds_a_valid_network_with_inferred_tiers():
    g = network_from_edges(EDGES, core="Acme", banks=2)
    validate_network(g)
    assert core_node(g) == "Acme" and g.nodes["Acme"]["tier"] == 0
    tiers = nx.get_node_attributes(g, "tier")
    assert tiers["Alpha Castings"] == 1 and tiers["Gamma Steel"] == 2
    # Eta Silicon sells to Delta Chips (tier 2) and Epsilon Boards (tier 2)
    assert tiers["Eta Silicon"] == 3 and tiers["Zeta Ore"] == 3
    assert {g.nodes[n]["bank"] for n in g if g.nodes[n]["kind"] == "firm"} == {0, 1}
    assert {n for n in g if g.nodes[n]["kind"] == "bank"} == {"bank-0", "bank-1"}


def test_edge_list_places_a_multi_depth_supplier_above_its_deepest_buyer():
    edges = EDGES + [("Eta Silicon", "Alpha Castings", 0.0)]
    # Alpha now has two suppliers; keep its shares summing to one
    edges = [(s, b, (1.0 if s == "Gamma Steel" else sh))
             for s, b, sh in edges if not (s == "Eta Silicon" and b == "Alpha Castings")]
    edges.append(("Eta Silicon", "Alpha Castings", 0.0))
    g = network_from_edges(edges, core="Acme")
    assert g.nodes["Eta Silicon"]["tier"] == 3   # longest path, not shortest


def test_edge_list_reports_mapping_errors_instead_of_hiding_them():
    with pytest.raises(ValueError, match="sum to"):
        network_from_edges([("A", "Acme", 0.5), ("B", "Acme", 0.4)], core="Acme")
    with pytest.raises(ValueError, match="cycle"):
        network_from_edges([("A", "Acme", 1.0), ("Acme", "A", 1.0)], core="Acme")
    with pytest.raises(ValueError, match="no bank assigned"):
        network_from_edges([("A", "Acme", 1.0)], core="Acme", banks={"Acme": 0})


def test_validation_rejects_edges_that_do_not_run_down_the_tiers():
    g = network_from_edges(EDGES, core="Acme")
    g.nodes["Gamma Steel"]["tier"] = 1     # now level with its buyer
    with pytest.raises(ValueError, match="lower tier"):
        validate_network(g)
    g = network_from_edges(EDGES, core="Acme")
    g.remove_edge("Zeta Ore", "Gamma Steel")
    with pytest.raises(ValueError, match="sells to nobody"):
        validate_network(g)


# ------------------------------------------------------------------ #
# the engine on a user network
# ------------------------------------------------------------------ #

def test_the_core_is_identified_by_kind_not_by_name():
    """Renaming the core must leave every outcome unchanged: the anonymity
    relation of the metamorphic layer, extended to the anchor."""
    g = generate_network(NetworkConfig(seed=5))
    renamed = nx.relabel_nodes(g, {"core-0": "Acme Industries"})
    a = Simulation(cfg(seed=5), network=g).run()
    b = Simulation(cfg(seed=5), network=renamed).run()
    assert outcome_signature(a) == outcome_signature(b)
    assert b.summary["n_firms"] == a.summary["n_firms"] == 56


def test_banks_are_created_for_every_id_the_network_names():
    """A mapped network's bank ids need not match ``network.n_banks``."""
    g = network_from_edges(EDGES, core="Acme", banks={
        "Acme": 7, "Alpha Castings": 7, "Beta Electronics": 12,
        "Gamma Steel": 7, "Delta Chips": 12, "Epsilon Boards": 12,
        "Zeta Ore": 7, "Eta Silicon": 12, "Theta Silicon": 12})
    sim = Simulation(cfg(), network=g)
    assert {7, 12} <= set(sim.banks)
    assert sim.banks[7].initial_capital > 0 and sim.banks[12].initial_capital > 0
    sim.run()


def test_batches_and_sweeps_run_on_a_fixed_user_network():
    g = network_from_edges(EDGES, core="Acme", banks=2)
    c = cfg()
    runs = run_batch(c, n_runs=4, base_seed=1, network=g)
    # the topology is fixed, so every path has the same eight firms and
    # only the shocks vary between paths
    assert all(r.summary["n_firms"] == 8 for r in runs)
    assert len({tuple(r.default_share) for r in runs}) > 1
    rows = sweep(c, "firm.initial_cash_ratio", [0.1, 0.5], n_runs=3,
                 base_seed=1, network=g)
    assert rows[0]["mean_default_share"] >= rows[1]["mean_default_share"] - 1e-9
    loo = ablation(leave_one_out_configs(c), n_runs=2, base_seed=1, network=g)
    assert set(loo) >= {"all", "without_supply"}
    assert batch_summary(runs)["runs"] == 4
    same = run_batch(c, n_runs=4, base_seed=1, network=g, n_jobs=2)
    assert [r.summary for r in same] == [r.summary for r in runs]


def test_reachability_bound_holds_on_a_user_network():
    g = network_from_edges(EDGES, core="Acme", banks=2)
    c = cfg(periods=25)
    c.shock.seed_defaults = 0
    c.shock.seed_firms = ("Gamma Steel",)
    c.channels.counterparty = c.channels.demand = c.channels.credit_crunch = False
    c.shock.liquidity_shock_prob = 0.0
    c.shock.demand_sigma = 0.0
    res = Simulation(c, network=g).run()
    allowed = supply_reachable_set(g, ["Gamma Steel"]) | {"Gamma Steel"}
    assert res.defaulted_firms <= allowed
