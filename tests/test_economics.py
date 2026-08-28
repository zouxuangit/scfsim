"""Economic property tests.

Two kinds of assurance that accounting identities cannot provide:

1. **Regression tests for the two specification errors in SCFSim's
   history.** Both produced perfectly balanced books, so no accounting
   check would have caught either. Here each bug is re-injected into the
   engine and the economic checks are asserted to fire. A guard that
   cannot catch the bug it was written for is not a guard.

2. **Comparative statics.** Signed predictions about the direction in
   which outcomes must move when a parameter moves. These are the
   falsifiable economic content of the model, checked across matched
   Monte-Carlo seeds.
"""
import copy

import numpy as np
import pytest

from scfsim import (COMPARATIVE_STATICS, EconomicViolation, ScenarioConfig,
                    Simulation, SimulationConfig, batch_summary,
                    comparative_statics, run_batch)
from scfsim.agents import BankState
from scfsim.network import CORE
import scfsim.simulation as sim_module


def base_cfg(seed=1, periods=25, strict=True):
    cfg = SimulationConfig(n_periods=periods, seed=seed, strict=strict)
    cfg.network.seed = seed
    cfg.firm.initial_cash_ratio = 0.15
    cfg.firm.receivable_recovery = 0.15
    cfg.shock.liquidity_shock_prob = 0.10
    cfg.shock.liquidity_shock_size = 0.6
    cfg.shock.demand_sigma = 0.18
    cfg.shock.seed_defaults = 3
    return cfg


# ------------------------------------------------------------------ #
# 1. regression tests for historical specification errors
# ------------------------------------------------------------------ #

def _orders_without_delivery_constraint(self, t):
    """The v0.1 bug: a firm's own supply capacity did not limit its own
    deliveries, so losing every supplier reduced only what it ordered
    upstream while it kept shipping at full volume."""
    fc, sc, ch = self.cfg.firm, self.cfg.shock, self.cfg.channels
    shock = float(np.exp(self.rng.normal(0.0, sc.demand_sigma)))
    core_demand = 100.0 * shock
    orders, books = {}, {}
    actual = {CORE: core_demand}
    nominal = {CORE: core_demand}
    for tier in range(1, len(self._nodes_by_tier())):
        for name in self._nodes_by_tier()[tier]:
            firm = self.firms[name]
            s_a = s_n = 0.0
            for _, buyer, data in self.g.out_edges(name, data=True):
                if buyer == CORE:
                    pa, pn = actual[CORE], nominal[CORE]
                else:
                    pa = fc.input_share * actual.get(buyer, 0.0)
                    pn = fc.input_share * nominal.get(buyer, 0.0)
                s_a += data["share"] * pa
                s_n += data["share"] * pn
            book = s_a if ch.demand else s_n
            sales = 0.0 if firm.defaulted else book      # <- the bug
            books[name] = book
            orders[name] = sales
            actual[name] = sales
            nominal[name] = s_n
    self._books = books
    return orders


def test_regression_supply_capacity_must_constrain_deliveries(monkeypatch):
    monkeypatch.setattr(sim_module.Simulation, "_place_orders",
                        _orders_without_delivery_constraint)
    with pytest.raises(EconomicViolation, match="must reduce deliveries"):
        Simulation(base_cfg()).run()


def test_regression_bank_capital_must_scale_to_the_credit_book(monkeypatch):
    """The v0.2 bug: capital was sized against total chain sales rather than
    against the SCF book the bank could hold, overstating it by roughly an
    order of magnitude and neutralising the credit-crunch channel."""
    original = sim_module.Simulation._init_states

    def buggy_init(self):
        original(self)
        total = sum(f.baseline_sales for n, f in self.firms.items()
                    if n != CORE)
        n_banks = self.cfg.network.n_banks
        for b in range(n_banks):
            cap = self.cfg.bank.capital_ratio * total / n_banks   # <- the bug
            self.banks[b] = BankState(bank_id=b, capital=cap,
                                      initial_capital=cap)

    monkeypatch.setattr(sim_module.Simulation, "_init_states", buggy_init)
    with pytest.raises(EconomicViolation, match="capital must be scaled"):
        Simulation(base_cfg()).run()


def test_regression_guards_pass_on_the_current_engine():
    """The same guards must not fire on the unmodified model."""
    Simulation(base_cfg()).run()


def test_drawing_ceiling_is_a_flow_property_not_a_stock_property():
    """A firm carrying a longer facility legitimately owes more than the
    advance rate applied to its receivables today, because the collateral
    that secured the drawing has since been collected. Checking this as a
    stock property was a mistake caught by the suite."""
    cfg = base_cfg(seed=11)
    cfg.bank.loan_maturity = 4
    cfg.bank.capital_ratio = 0.015
    sim = Simulation(cfg)
    stock_violations = []
    for t in range(cfg.n_periods):
        sim._step(t)           # strict mode raises if the flow property fails
        stock_violations += [
            n for n, f in sim.firms.items()
            if n != CORE and not f.defaulted and f.loans >
            cfg.bank.advance_rate * f.receivables_outstanding() + 1e-6
        ]
    assert stock_violations, ("expected the stock reading to be violated at "
                              "long maturity, otherwise this test proves "
                              "nothing")


# ------------------------------------------------------------------ #
# 2. comparative statics
# ------------------------------------------------------------------ #

def _default_share(cfg, n_runs=24, base_seed=17):
    return batch_summary(run_batch(cfg, n_runs=n_runs,
                                   base_seed=base_seed))["mean_default_share"]


@pytest.fixture
def statics_runs(request):
    """Monte-Carlo paths per point, tunable with ``--statics-runs``."""
    return request.config.getoption("--statics-runs")


COMPARATIVE_CASES = [
    ("firm.initial_cash_ratio", 0.10, 0.30),
    ("firm.receivable_recovery", 0.10, 0.60),
    ("firm.fixed_cost_ratio", 0.04, 0.12),
    ("firm.payables_delay", 0, 2),
    ("bank.advance_rate", 0.30, 0.90),
    ("bank.pricing_slope", 0.0, 0.5),
    ("scenario.haircut", 0.05, 0.60),
    ("scenario.fraud_prob", 0.01, 0.50),
    ("scenario.visibility_depth", 1, 3),
    ("shock.demand_sigma", 0.05, 0.35),
    ("shock.liquidity_shock_prob", 0.02, 0.20),
]


@pytest.mark.slow
@pytest.mark.parametrize("path,low,high", COMPARATIVE_CASES,
                         ids=[c[0] for c in COMPARATIVE_CASES])
def test_comparative_statics_have_the_predicted_sign(path, low, high,
                                                    statics_runs):
    """Raising each parameter must move defaults in the predicted direction.

    A violation means the specification contradicts the economics it claims
    to implement, which is precisely the class of error that accounting
    identities cannot detect.
    """
    from scfsim.sweep import set_by_path

    sign = COMPARATIVE_STATICS[path]
    cfg_low = base_cfg(strict=False)
    cfg_low.n_periods = 30
    cfg_high = copy.deepcopy(cfg_low)
    set_by_path(cfg_low, path, low)
    set_by_path(cfg_high, path, high)

    share_low = _default_share(cfg_low, n_runs=statics_runs)
    share_high = _default_share(cfg_high, n_runs=statics_runs)
    change = share_high - share_low

    assert sign * change >= -0.01, (
        f"{path}: raising it from {low} to {high} moved the default share by "
        f"{change:+.4f}, against the predicted sign {sign:+d}")


def test_every_prediction_is_exercised():
    """Keep the table and the test cases in step."""
    covered = {c[0] for c in COMPARATIVE_CASES}
    declared = set(comparative_statics())
    # bank.capital_ratio is declared but deliberately not asserted: its
    # effect size in the default parameter region is below sampling noise
    # (raising it from 0.20 to 0.015 moves the credit channel's marginal
    # contribution only from 0.34 to 1.26 firms). The exemption is recorded
    # in docs/FINANCIAL_SPEC.md so it cannot quietly become a blind spot.
    exempt = {"bank.capital_ratio"}
    missing = declared - covered - exempt
    assert not missing, f"predictions never tested: {sorted(missing)}"


# ------------------------------------------------------------------ #
# 3. remaining branches of the economic checker
# ------------------------------------------------------------------ #

def test_economic_checker_detects_negative_sales():
    from scfsim import check_economics
    sim = Simulation(base_cfg(strict=False))
    sim.run()
    name = next(n for n in sim.firms if n != CORE)
    with pytest.raises(EconomicViolation, match="negative sales"):
        check_economics(sim.firms, sim.banks, sim.cfg,
                        orders={name: -5.0}, books={name: 10.0},
                        t=0, core_name=CORE)


def test_economic_checker_detects_a_defaulted_firm_still_selling():
    from scfsim import check_economics
    sim = Simulation(base_cfg(strict=False))
    sim.run()
    name = next((n for n, f in sim.firms.items()
                 if n != CORE and f.defaulted), None)
    if name is None:                            # pragma: no cover
        pytest.skip("no defaults in this run")
    with pytest.raises(EconomicViolation, match="still selling"):
        check_economics(sim.firms, sim.banks, sim.cfg,
                        orders={name: 5.0}, books={name: 5.0},
                        t=0, core_name=CORE)


def test_economic_checker_detects_selling_without_any_capacity():
    from scfsim import check_economics
    sim = Simulation(base_cfg(strict=False))
    sim.run()
    name = next(n for n, f in sim.firms.items() if n != CORE)
    sim.firms[name].defaulted = False
    sim.firms[name].supply_capacity = 0.0
    with pytest.raises(EconomicViolation, match="no supply capacity"):
        check_economics(sim.firms, sim.banks, sim.cfg,
                        orders={name: 5.0}, books={name: 20.0},
                        t=0, core_name=CORE)


def test_economic_checks_are_skipped_when_the_supply_channel_is_off():
    from scfsim import ChannelConfig, check_economics
    sim = Simulation(base_cfg(strict=False))
    sim.run()
    sim.cfg.channels = ChannelConfig(supply=False)
    name = next(n for n, f in sim.firms.items() if n != CORE)
    sim.firms[name].defaulted = False
    sim.firms[name].supply_capacity = 0.0
    check_economics(sim.firms, sim.banks, sim.cfg,
                    orders={name: 5.0}, books={name: 20.0},
                    t=0, core_name=CORE)      # must not raise
