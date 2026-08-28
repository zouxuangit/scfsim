"""Unit tests for SCFSim (pytest)."""
import numpy as np
import pytest

from scfsim import (ScenarioConfig, Simulation, SimulationConfig,
                    batch_summary, generate_network, run_batch,
                    validate_network)
from scfsim.config import NetworkConfig


def make_cfg(**kw):
    cfg = SimulationConfig(n_periods=15, seed=7)
    cfg.network.seed = 7
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


def test_network_structure():
    g = generate_network(NetworkConfig(seed=1))
    validate_network(g)
    tiers = {}
    for n, d in g.nodes(data=True):
        tiers.setdefault(d["tier"], []).append(n)
    assert len(tiers[0]) == 1                      # one core
    assert len(tiers[1]) == 8 and len(tiers[3]) == 32
    # every buyer's incoming shares sum to ~1
    for node, d in g.nodes(data=True):
        if d["kind"] == "bank" or g.in_degree(node) == 0:
            continue
        s = sum(data["share"] for _, _, data in g.in_edges(node, data=True))
        assert abs(s - 1.0) < 1e-9


def test_reproducibility():
    r1 = Simulation(make_cfg()).run()
    r2 = Simulation(make_cfg()).run()
    assert r1.default_share == r2.default_share
    assert r1.summary == r2.summary


def test_seed_defaults_appear():
    cfg = make_cfg()
    cfg.shock.seed_defaults = 3
    res = Simulation(cfg).run()
    assert res.summary["final_default_share"] > 0
    assert res.summary["n_firms"] == 8 + 16 + 32


def test_no_shock_no_defaults():
    cfg = make_cfg()
    cfg.shock.seed_defaults = 0
    cfg.shock.liquidity_shock_prob = 0.0
    cfg.shock.demand_sigma = 0.0
    res = Simulation(cfg).run()
    assert res.summary["final_default_share"] == 0.0


def test_blockchain_weakly_reduces_mean_cascade():
    """On matched seeds, blockchain financing should not worsen cascades."""
    base = make_cfg()
    base.shock.seed_defaults = 2
    a = SimulationConfig.from_json(base.to_json())
    a.scenario = ScenarioConfig(blockchain=False)
    b = SimulationConfig.from_json(base.to_json())
    b.scenario = ScenarioConfig(blockchain=True)
    sa = batch_summary(run_batch(a, n_runs=40, base_seed=100))
    sb = batch_summary(run_batch(b, n_runs=40, base_seed=100))
    assert sb["mean_default_share"] <= sa["mean_default_share"] + 1e-9


def test_config_json_roundtrip():
    cfg = make_cfg()
    cfg.scenario.blockchain = True
    clone = SimulationConfig.from_json(cfg.to_json())
    assert clone.scenario.blockchain is True
    assert clone.network.firms_per_tier == cfg.network.firms_per_tier


def test_custom_network_validation():
    import networkx as nx
    g = nx.DiGraph()
    g.add_node("core-0", tier=0, kind="core", bank=0)
    g.add_node("firm-1-0", tier=1, kind="firm", bank=0)
    g.add_edge("firm-1-0", "core-0", share=1.0)
    validate_network(g)  # should not raise
    g2 = g.copy()
    del g2.nodes["firm-1-0"]["bank"]
    with pytest.raises(ValueError):
        validate_network(g2)


def test_anchor_default_stops_orders_and_hits_its_suppliers():
    """A defaulted core places no orders and pays its maturing payables at
    the recovery rate; it is never counted among the firms.

    The horizon is long because a firm that has lost its only customer
    bleeds only its fixed cost: with a 35% cash buffer and a 6% fixed-cost
    ratio the first tier survives some thirty periods on its cash.
    """
    cfg = make_cfg(n_periods=40)
    cfg.shock.seed_defaults = 0
    cfg.shock.liquidity_shock_prob = 0.0
    cfg.shock.demand_sigma = 0.0
    cfg.shock.core_default_time = 4
    sim = Simulation(cfg)
    for t in range(cfg.n_periods):
        sim._step(t)
        orders = sim._place_orders(t) if t >= 5 else None
        if orders is not None:
            assert all(v == 0.0 for k, v in orders.items()), \
                "suppliers still receive orders after the anchor defaulted"
            break
    res = Simulation(cfg).run()
    assert res.summary["n_firms"] == 8 + 16 + 32
    assert res.summary["final_default_share"] > 0.0, \
        "an anchor default with no other shock should still cascade"


def test_anchor_default_weakly_worsens_outcomes_on_matched_seeds():
    """Over a horizon long enough for fixed costs to bite.

    Over a short horizon the sign can reverse: a firm whose orders stop
    also stops paying variable costs before it stops collecting, so a
    demand collapse relieves working-capital pressure for a few periods.
    That is the working-capital unwind, recorded in FINANCIAL_SPEC §4,
    not a bug, and the horizon here is chosen to be past it.
    """
    base = make_cfg(n_periods=40)
    base.shock.seed_defaults = 2
    with_core = SimulationConfig.from_json(base.to_json())
    with_core.shock.core_default_time = 5
    a = batch_summary(run_batch(base, n_runs=30, base_seed=7))
    b = batch_summary(run_batch(with_core, n_runs=30, base_seed=7))
    assert b["mean_default_share"] >= a["mean_default_share"] - 1e-9


def test_negative_pricing_slope_is_rejected():
    from scfsim import BankConfig
    with pytest.raises(ValueError):
        BankConfig(pricing_slope=-0.1)


def test_payables_on_terms_defer_variable_costs():
    """With a one-period payables delay a firm's cash after production is
    higher by exactly its variable cost, and the invoice is paid next period."""
    cfg = make_cfg()
    cfg.shock.seed_defaults = 0
    cfg.shock.liquidity_shock_prob = 0.0
    cfg.shock.demand_sigma = 0.0
    cfg.firm.payables_delay = 1
    sim = Simulation(cfg)
    sim._step(0)
    f = sim.firms["firm-1-0"]
    variable = cfg.firm.cost_ratio * f.baseline_sales
    assert abs(f.payables_due[1] - variable) < 1e-9
    sim._step(1)
    assert 1 not in f.payables_due, "the invoice was not paid when due"
    with pytest.raises(ValueError):
        from scfsim import FirmConfig
        FirmConfig(payables_delay=-1)


def test_paying_suppliers_on_terms_weakly_reduces_defaults():
    base = make_cfg(n_periods=30)
    base.shock.seed_defaults = 2
    terms = SimulationConfig.from_json(base.to_json())
    terms.firm.payables_delay = 1
    a = batch_summary(run_batch(base, n_runs=30, base_seed=11))
    b = batch_summary(run_batch(terms, n_runs=30, base_seed=11))
    assert b["mean_default_share"] <= a["mean_default_share"] + 1e-9


def test_parallel_batches_reproduce_the_serial_result_in_order():
    cfg = make_cfg()
    cfg.shock.seed_defaults = 2
    serial = run_batch(cfg, n_runs=6, base_seed=3)
    parallel = run_batch(cfg, n_runs=6, base_seed=3, n_jobs=2)
    assert [r.summary for r in serial] == [r.summary for r in parallel]
    assert [r.default_share for r in serial] == [r.default_share for r in parallel]
    everything = run_batch(cfg, n_runs=3, base_seed=3, n_jobs=0)
    assert [r.summary for r in everything] == [r.summary for r in serial[:3]]
