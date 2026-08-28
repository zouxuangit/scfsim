"""Validation tests.

The engine is checked against reference quantities that are computed
without running it (graph-theoretic reachability bounds), and against the
expected ordering of channel ablations.
"""
import copy

import pytest

from scfsim import (ChannelConfig, ScenarioConfig, Simulation,
                    SimulationConfig, ablation, attributable_defaults,
                    demand_reachable_set, isolated_channel_configs,
                    leave_one_out_configs, supply_reachable_set, sweep)
from scfsim.sweep import set_by_path


def deterministic(channels, seeds, seed=11):
    """A noise-free stressed configuration, so that a matched control run
    isolates exactly the defaults attributable to the seeds."""
    cfg = SimulationConfig(n_periods=25, seed=seed)
    cfg.network.seed = seed
    cfg.firm.initial_cash_ratio = 0.10
    cfg.firm.fixed_cost_ratio = 0.10
    cfg.bank.advance_rate = 0.5
    cfg.shock.liquidity_shock_prob = 0.0
    cfg.shock.demand_sigma = 0.0
    cfg.shock.seed_defaults = seeds
    cfg.channels = channels
    return cfg


def stressed(seed=11):
    cfg = SimulationConfig(n_periods=25, seed=seed)
    cfg.network.seed = seed
    cfg.firm.initial_cash_ratio = 0.15
    cfg.firm.receivable_recovery = 0.15
    cfg.shock.liquidity_shock_prob = 0.10
    cfg.shock.seed_defaults = 3
    return cfg


def _attributable(channels):
    treated_sim = Simulation(deterministic(channels, 3))
    treated = treated_sim.run()
    control = Simulation(deterministic(channels, 0)).run()
    return treated_sim, treated, attributable_defaults(treated, control)


def test_supply_channel_confined_to_descendants():
    """Supply disruption travels supplier -> buyer only, so the
    attributable cascade must lie inside the descendants of the seeds."""
    ch = ChannelConfig(counterparty=False, supply=True, demand=False,
                       credit_crunch=False)
    sim, res, attr = _attributable(ch)
    bound = supply_reachable_set(sim.g, res.seeded_firms)
    assert len(attr) > len(res.seeded_firms)   # a real cascade occurred
    assert attr <= bound


def test_demand_channel_confined_to_ancestors():
    """Demand contraction travels buyer -> supplier only, so the
    attributable cascade must lie inside the ancestors of the seeds."""
    ch = ChannelConfig(counterparty=False, supply=False, demand=True,
                       credit_crunch=False)
    sim, res, attr = _attributable(ch)
    bound = demand_reachable_set(sim.g, res.seeded_firms)
    assert len(attr) > len(res.seeded_firms)
    assert attr <= bound


def test_trade_channels_off_leaves_no_trade_graph_cascade():
    """With both trade-graph channels off, a seed default cannot reach any
    other firm through the network."""
    ch = ChannelConfig(counterparty=False, supply=False, demand=False,
                       credit_crunch=False)
    _, res, attr = _attributable(ch)
    assert attr == set(res.seeded_firms)


@pytest.mark.slow
def test_coupled_model_dominates_every_ablation():
    """The fully coupled model must not produce a smaller cascade than any
    single-channel variant, i.e. the channels do not cancel out."""
    out = ablation(isolated_channel_configs(stressed()), n_runs=25,
                   base_seed=5)
    full = out["all"]["mean_cascade_size"]
    assert out["none"]["mean_cascade_size"] <= full + 1e-9
    for ch in ("counterparty", "supply", "demand", "credit_crunch"):
        assert out["none"]["mean_cascade_size"] <= out[ch]["mean_cascade_size"] + 1e-9
        assert out[ch]["mean_cascade_size"] <= full + 1e-9


def test_sweep_is_monotone_in_fraud_rate():
    """Raising the fraud rate degrades collateral quality, so the default
    share under the blockchain scenario must not fall."""
    cfg = stressed()
    cfg.scenario = ScenarioConfig(blockchain=True)
    rows = sweep(cfg, "scenario.bc_fraud_prob", [0.0, 0.3, 0.6],
                 n_runs=20, base_seed=3)
    shares = [r["mean_default_share"] for r in rows]
    assert shares[0] <= shares[-1] + 1e-9
    assert [r["value"] for r in rows] == [0.0, 0.3, 0.6]


def test_set_by_path_rejects_unknown_field():
    cfg = stressed()
    set_by_path(cfg, "firm.initial_cash_ratio", 0.4)
    assert cfg.firm.initial_cash_ratio == 0.4
    with pytest.raises(AttributeError):
        set_by_path(cfg, "firm.not_a_field", 1.0)


def test_channel_config_json_roundtrip():
    cfg = stressed()
    cfg.channels = ChannelConfig(counterparty=False, supply=True,
                                 demand=False, credit_crunch=False)
    clone = SimulationConfig.from_json(cfg.to_json())
    assert clone.channels.counterparty is False
    assert clone.channels.supply is True
    assert clone.channels.demand is False


# --------------------------------------------------------------------- #
# Randomised property tests: the reachability bounds must hold across the
# parameter space, not only at the single point used above.
# --------------------------------------------------------------------- #

import numpy as np  # noqa: E402

from scfsim import ChannelConfig, Simulation, SimulationConfig  # noqa: E402
from scfsim.config import NetworkConfig  # noqa: E402


def _random_config(rng, channels):
    """Draw a noise-free but otherwise randomised stressed configuration."""
    tiers = int(rng.integers(2, 4))
    sizes = tuple(int(rng.integers(3, 10)) for _ in range(tiers))
    cfg = SimulationConfig(n_periods=int(rng.integers(12, 30)))
    cfg.network = NetworkConfig(
        n_tiers=tiers, firms_per_tier=sizes,
        n_banks=int(rng.integers(1, 4)),
        avg_buyers_per_firm=float(rng.uniform(1.0, 2.5)))
    cfg.firm.initial_cash_ratio = float(rng.uniform(0.05, 0.20))
    cfg.firm.fixed_cost_ratio = float(rng.uniform(0.05, 0.15))
    cfg.firm.cost_ratio = float(rng.uniform(0.65, 0.80))
    cfg.bank.advance_rate = float(rng.uniform(0.2, 0.9))
    cfg.bank.loan_maturity = int(rng.integers(1, 4))
    # the bounds are statements about contagion, so exogenous noise is off
    cfg.shock.liquidity_shock_prob = 0.0
    cfg.shock.demand_sigma = 0.0
    cfg.shock.seed_tier = min(2, tiers)
    cfg.channels = channels
    return cfg


def _bound_holds(direction, seed):
    rng = np.random.default_rng(seed)
    channels = ChannelConfig(
        counterparty=False, credit_crunch=False,
        supply=(direction == "supply"), demand=(direction == "demand"))
    cfg = _random_config(rng, channels)
    cfg.seed = cfg.network.seed = int(seed)

    treated_cfg = copy.deepcopy(cfg)
    treated_cfg.shock.seed_defaults = int(rng.integers(1, 4))
    sim = Simulation(treated_cfg)
    treated = sim.run()

    control_cfg = copy.deepcopy(treated_cfg)
    control_cfg.shock.seed_defaults = 0
    control = Simulation(control_cfg).run()

    attributable = attributable_defaults(treated, control)
    bound = (supply_reachable_set if direction == "supply"
             else demand_reachable_set)(sim.g, treated.seeded_firms)
    return attributable <= bound, len(attributable), len(bound)


@pytest.mark.slow
@pytest.mark.parametrize("direction", ["supply", "demand"])
def test_reachability_bound_holds_across_random_configurations(direction):
    """The bound must hold for every draw, and must bite on some of them."""
    non_trivial = 0
    for seed in range(30):
        holds, n_attr, n_bound = _bound_holds(direction, seed)
        assert holds, (f"{direction} bound violated at seed {seed}: "
                       f"{n_attr} attributable vs bound of {n_bound}")
        if 0 < n_bound < 1000:
            non_trivial += 1
    assert non_trivial >= 25, "bounds were trivial in too many draws"


def test_grid_sweep_covers_cartesian_product():
    from scfsim import grid_sweep
    cfg = stressed()
    cfg.scenario = ScenarioConfig(blockchain=True)
    rows = grid_sweep(cfg, {"scenario.bc_visibility_depth": [1, 3],
                            "scenario.bc_haircut": [0.05, 0.4]},
                      n_runs=8, base_seed=3)
    assert len(rows) == 4
    combos = {(r["scenario.bc_visibility_depth"], r["scenario.bc_haircut"])
              for r in rows}
    assert combos == {(1, 0.05), (1, 0.4), (3, 0.05), (3, 0.4)}
    # deeper visibility must not increase defaults at equal haircut
    by = {(r["scenario.bc_visibility_depth"], r["scenario.bc_haircut"]):
          r["mean_default_share"] for r in rows}
    for h in (0.05, 0.4):
        assert by[(3, h)] <= by[(1, h)] + 1e-9


def test_channel_decomposition_is_internally_consistent():
    from scfsim import channel_decomposition
    cfg = stressed()
    iso = ablation(isolated_channel_configs(cfg), n_runs=12, base_seed=5)
    loo = ablation(leave_one_out_configs(cfg), n_runs=12, base_seed=5)
    dec = channel_decomposition(iso, loo)
    assert set(dec["channels"]) == {"counterparty", "supply", "demand",
                                    "credit_crunch"}
    assert dec["coupled_effect"] == pytest.approx(
        dec["coupled"] - dec["baseline_no_channels"])
    assert dec["interaction"] == pytest.approx(
        dec["coupled_effect"] - dec["sum_of_first_order"])
    assert dec["sum_of_first_order"] == pytest.approx(
        sum(v["alone"] for v in dec["channels"].values()))


@pytest.mark.slow
def test_credit_crunch_binds_when_bank_capital_is_thin():
    """The credit-crunch channel is second order in SCF but must become
    measurably stronger as bank capital falls relative to the credit book."""
    def marginal(capital_ratio):
        cfg = stressed()
        cfg.bank.capital_ratio = capital_ratio
        variants = leave_one_out_configs(cfg)
        out = ablation({k: variants[k] for k in
                        ("all", "without_credit_crunch")},
                       n_runs=25, base_seed=7)
        return (out["all"]["mean_cascade_size"]
                - out["without_credit_crunch"]["mean_cascade_size"])

    assert marginal(0.015) > marginal(0.20)


def test_loan_maturity_extends_bank_exposure():
    """A longer facility keeps principal outstanding for longer, so the
    bank's book cannot shrink faster than under invoice-tenor lending."""
    from scfsim import Simulation

    def peak_outstanding(maturity):
        cfg = stressed()
        cfg.bank.loan_maturity = maturity
        sim = Simulation(cfg)
        sim.run()
        return max(sum(b.outstanding.values()) for b in sim.banks.values())

    assert peak_outstanding(4) >= peak_outstanding(1) - 1e-9


def test_loan_maturity_must_be_positive():
    from scfsim.config import BankConfig
    with pytest.raises(ValueError):
        BankConfig(loan_maturity=0)
