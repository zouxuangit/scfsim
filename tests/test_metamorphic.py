"""Metamorphic tests.

Each relation is asserted twice: once on the real engine, where it must
hold, and once against a deliberately faulted engine, where it must fail.
The second assertion is the important one. A relation that cannot be
broken is not testing anything, and the audit of v0.5 recorded exactly
that failure mode — an economic check that looked sound but was too weak
to catch the bug it was written for.
"""
import copy

import numpy as np
import pytest

from scfsim import (Simulation, SimulationConfig, generate_network,
                    outcome_signature, relabelled, scaled, truncated)
from scfsim.config import NetworkConfig
from scfsim.network import CORE
import scfsim.simulation as sim_module

SEED = 5
SEED_FIRMS = ("firm-2-0", "firm-2-1", "firm-2-2")


def deterministic_cfg(seed=SEED, periods=30):
    """A configuration with no exogenous randomness.

    The relations below are statements about the engine, not about the
    shock process, so the shocks are switched off to make any difference
    attributable to the transformation under test.
    """
    cfg = SimulationConfig(n_periods=periods, seed=seed)
    cfg.network.seed = seed
    cfg.firm.initial_cash_ratio = 0.15
    cfg.firm.receivable_recovery = 0.15
    cfg.shock.liquidity_shock_prob = 0.0
    cfg.shock.demand_sigma = 0.0
    cfg.shock.seed_firms = SEED_FIRMS
    return cfg


def signature(cfg, network=None):
    return outcome_signature(Simulation(cfg, network=network).run())


# ------------------------------------------------------------------ #
# relation 1: dimensional homogeneity
# ------------------------------------------------------------------ #

@pytest.mark.extra_case
@pytest.mark.parametrize("factor", [1e-9, 1e-6, 0.01, 10.0, 1e3, 1e6, 1e9, 1e12])
def test_outcomes_are_invariant_to_the_monetary_unit(factor):
    """Every quantity is a ratio of the core's order volume, so rescaling
    that volume must leave every default outcome untouched.

    The range covers twenty-one orders of magnitude, which is the declared
    validity band: far outside it, ordinary floating-point resolution would
    eventually dominate and the relation would fail for reasons that have
    nothing to do with the model.
    """
    assert signature(scaled(deterministic_cfg(), factor)) == \
        signature(deterministic_cfg())


def test_homogeneity_holds_with_every_optional_ledger_in_use():
    """Payables on terms, priced credit and an anchor default add ledgers;
    all of them must still scale with the monetary unit."""
    cfg = deterministic_cfg()
    cfg.firm.payables_delay = 2
    cfg.bank.pricing_slope = 0.3
    cfg.shock.core_default_time = 12
    for factor in (1e-6, 1e6):
        assert signature(scaled(cfg, factor)) == signature(cfg)


def test_scale_relation_detects_an_unscaled_absolute_term(monkeypatch):
    """Sensitivity check: an absolute cost that does not scale with the
    economy must break dimensional homogeneity."""
    original = sim_module.Simulation._produce_and_finance

    def with_absolute_cost(self, t, orders):
        for name, firm in self.firms.items():
            if name != CORE and not firm.defaulted:
                firm.cash -= 1.0          # <- an absolute, unscaled charge
        return original(self, t, orders)

    monkeypatch.setattr(sim_module.Simulation, "_produce_and_finance",
                        with_absolute_cost)
    assert signature(scaled(deterministic_cfg(), 50.0)) != \
        signature(deterministic_cfg())


# ------------------------------------------------------------------ #
# relation 2: anonymity of firm labels
# ------------------------------------------------------------------ #

def _relabelled_pair(cfg):
    g = generate_network(NetworkConfig(seed=SEED))
    rng = np.random.default_rng(0)
    g2, mapping = relabelled(g, rng)
    cfg2 = copy.deepcopy(cfg)
    cfg2.shock.seed_firms = tuple(mapping[n] for n in cfg.shock.seed_firms)
    return (g, cfg), (g2, cfg2)


def test_outcomes_are_invariant_to_firm_names():
    """Names are labels, not data: permuting them within tiers, and moving
    the seed shock with them, must not change aggregate outcomes."""
    (g, cfg), (g2, cfg2) = _relabelled_pair(deterministic_cfg())
    assert signature(cfg, network=g) == signature(cfg2, network=g2)


def test_relabelling_relation_detects_name_dependent_behaviour(monkeypatch):
    """Sensitivity check: contagion that depends on a firm's index within
    its tier — a label, not a structural property — must break anonymity.

    Note that the fault must depend on the position *within* a tier. An
    earlier attempt compared full names, which are ordered by tier, so the
    condition was constant across every edge and the fault cancelled out in
    both runs. A fault that cannot distinguish the two inputs proves
    nothing, which is the same trap this suite exists to avoid.
    """
    original = sim_module.Simulation._resolve_default

    def index_dependent(self, firm, t):
        original(self, firm, t)
        for _, buyer, data in self.g.out_edges(firm.name, data=True):
            if int(buyer.split("-")[-1]) % 2 == 0:   # <- depends on the label
                b = self.firms[buyer]
                b.supply_capacity = min(1.0, b.supply_capacity
                                        + data["share"])

    monkeypatch.setattr(sim_module.Simulation, "_resolve_default",
                        index_dependent)
    (g, cfg), (g2, cfg2) = _relabelled_pair(deterministic_cfg())
    assert signature(cfg, network=g) != signature(cfg2, network=g2)


# ------------------------------------------------------------------ #
# relation 3: no lookahead
# ------------------------------------------------------------------ #

@pytest.mark.extra_case
@pytest.mark.parametrize("horizon", [8, 12, 20])
def test_a_short_run_reproduces_the_prefix_of_a_long_one(horizon):
    """Nothing at period t may depend on information from after t."""
    long_run = Simulation(deterministic_cfg(periods=30)).run()
    short_run = Simulation(truncated(deterministic_cfg(), horizon)).run()
    assert [round(x, 9) for x in short_run.default_share] == \
        [round(x, 9) for x in long_run.default_share[:horizon]]


def test_prefix_relation_detects_dependence_on_the_horizon(monkeypatch):
    """Sensitivity check: letting the run length influence period-t demand
    is a form of lookahead and must break the prefix relation."""
    original = sim_module.Simulation._place_orders

    def horizon_dependent(self, t):
        orders = original(self, t)
        factor = 1.0 - 0.5 * t / self.cfg.n_periods   # <- uses the horizon
        return {k: v * factor for k, v in orders.items()}

    monkeypatch.setattr(sim_module.Simulation, "_place_orders",
                        horizon_dependent)
    long_run = Simulation(deterministic_cfg(periods=30)).run()
    short_run = Simulation(truncated(deterministic_cfg(), 12)).run()
    assert [round(x, 9) for x in short_run.default_share] != \
        [round(x, 9) for x in long_run.default_share[:12]]


# ------------------------------------------------------------------ #
# supporting behaviour
# ------------------------------------------------------------------ #

def test_seed_firms_override_the_random_draw():
    cfg = deterministic_cfg()
    sim = Simulation(cfg)
    result = sim.run()
    assert set(result.seeded_firms) == set(SEED_FIRMS)


def test_seed_firms_rejects_an_unknown_name():
    cfg = deterministic_cfg()
    cfg.shock.seed_firms = ("firm-9-9",)
    with pytest.raises(ValueError, match="not a firm in this network"):
        Simulation(cfg).run()


def test_transform_helpers_validate_their_arguments():
    with pytest.raises(ValueError):
        scaled(deterministic_cfg(), 0.0)
    with pytest.raises(ValueError):
        truncated(deterministic_cfg(), 0)


def test_strict_layers_can_be_enabled_independently():
    cfg = deterministic_cfg(periods=10)
    cfg.strict = True
    cfg.strict_layers = ("books",)
    sim = Simulation(cfg)
    assert sim._layer("books") and not sim._layer("economics")
    sim.run()
    cfg.strict_layers = ("economics",)
    sim2 = Simulation(cfg)
    assert sim2._layer("economics") and not sim2._layer("books")
    sim2.run()


# ------------------------------------------------------------------ #
# anonymity on the default (randomly seeded) code path
# ------------------------------------------------------------------ #

@pytest.mark.slow
def test_anonymity_also_holds_when_the_seeds_are_drawn_at_random():
    """The relation is not confined to explicitly named seeds.

    The random draw selects a *position* in the tier's candidate list, not
    a name, and relabelling preserves that ordering — so the same
    structural firms are shocked and outcomes are unchanged. Note that
    sorting the candidates by name before drawing, which looks like the
    tidier implementation, would *introduce* the name dependence this
    relation exists to rule out.
    """
    import copy

    from scfsim import batch_summary

    g = generate_network(NetworkConfig(seed=7))
    g2, _ = relabelled(g, np.random.default_rng(1))

    def batch(graph, n=40):
        results = []
        for i in range(n):
            cfg = SimulationConfig(n_periods=30)
            cfg.firm.initial_cash_ratio = 0.15
            cfg.firm.receivable_recovery = 0.15
            cfg.shock.liquidity_shock_prob = 0.10
            cfg.shock.demand_sigma = 0.18
            cfg.shock.seed_defaults = 3
            cfg.shock.seed_tier = 2
            cfg.seed = 100 + i
            results.append(Simulation(cfg, network=graph).run())
        return batch_summary(results)

    original, permuted = batch(g), batch(g2)
    assert original["mean_default_share"] == \
        pytest.approx(permuted["mean_default_share"], abs=1e-12)
    assert original["mean_cascade_size"] == \
        pytest.approx(permuted["mean_cascade_size"], abs=1e-12)


def test_anonymity_is_invariance_to_renaming_not_to_reordering():
    """Document the boundary: because the draw is positional, a graph whose
    nodes are *inserted* in a different order is a different input, not a
    relabelling of the same one."""
    import networkx as nx

    g = generate_network(NetworkConfig(seed=7))
    reordered = nx.DiGraph()
    for node, data in sorted(g.nodes(data=True), reverse=True):
        reordered.add_node(node, **data)
    reordered.add_edges_from(g.edges(data=True))

    cfg = deterministic_cfg(periods=20)
    cfg.shock.seed_firms = ()
    cfg.shock.seed_defaults = 2
    assert signature(cfg, network=g) != signature(cfg, network=reordered)
