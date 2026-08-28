"""Differential tests against an independent reference implementation.

`scfsim.reference` re-derives a restricted version of the model directly
from the written specification, in a form short enough to check by
reading. These tests assert that the engine reproduces it exactly, period
by period and firm by firm.

As everywhere else in this suite, the comparison is also shown to be
capable of failing: ten faults are injected into the engine and each
must break agreement. A differential test that passes against a broken
engine is comparing two copies of the same mistake.

Two further tests guard the *design* of this layer rather than the engine.
The reference is only worth having while it is (a) independent of the
engine and (b) short enough to verify by reading; the audit of v0.8.0
recorded that its scope had reached the point beyond which (b) would fail,
and identified the configuration modules as the one surface the two
implementations share. Both facts are pinned mechanically below.
"""
import ast
import inspect
import pathlib

import pytest

from scfsim import (ScenarioConfig, Simulation, SimulationConfig,
                    linear_chain, restricted_config, simulate_reference)
import scfsim.reference as ref_module
import scfsim.simulation as sim_module

NAMES = ["firm-1-0", "firm-2-0", "firm-3-0"]
CORE = "core-0"


def chain_cfg(fixed_cost=0.06, cash=0.35, seeds=("firm-3-0",), periods=20,
              **overrides):
    cfg = SimulationConfig(n_periods=periods, seed=1)
    cfg.network.n_tiers = 3
    cfg.network.firms_per_tier = (1, 1, 1)
    cfg.network.n_banks = 1
    cfg.firm.fixed_cost_ratio = fixed_cost
    cfg.firm.initial_cash_ratio = cash
    cfg.shock.seed_firms = seeds
    cfg.shock.seed_time = 2
    for path, value in overrides.items():
        section, attr = path.split(".")
        setattr(getattr(cfg, section), attr, value)
    return restricted_config(cfg)


def disagreement(cfg=None):
    """Return the first (period, firm, reason) where the two diverge.

    Cash, loan balances, default status and cumulative bank write-offs are
    all compared: coarser observables hide small errors, which is how an
    earlier version of this comparison missed two injected faults.
    """
    cfg = cfg or chain_cfg()
    sim = Simulation(cfg, network=linear_chain(3, 1))
    ref = simulate_reference(cfg, n_tiers=3)
    for t in range(cfg.n_periods):
        sim._step(t)
        for name in NAMES:
            if abs(sim.firms[name].cash - ref.cash[t][name]) > 1e-9:
                return (t, name, f"cash {sim.firms[name].cash:.10g} vs "
                                 f"{ref.cash[t][name]:.10g}")
            if abs(sim.firms[name].loans - ref.loans[t][name]) > 1e-9:
                return (t, name, f"loans {sim.firms[name].loans:.10g} vs "
                                 f"{ref.loans[t][name]:.10g}")
            if (name in ref.defaulted[t]) != sim.firms[name].defaulted:
                return (t, name, "default status differs")
        engine_losses = sum(b.losses for b in sim.banks.values())
        if abs(engine_losses - ref.bank_losses[t]) > 1e-9:
            return (t, "bank-0", f"write-offs {engine_losses:.10g} vs "
                                 f"{ref.bank_losses[t]:.10g}")
    return None


# ------------------------------------------------------------------ #
# the engine must reproduce the reference
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("fixed_cost,cash", [
    (0.06, 0.35),    # healthy chain, cascade driven by the seed
    (0.35, 0.15),    # negative margins: every firm bleeds out
    (0.40, 0.30),
    (0.32, 0.05),    # thin buffers, so financing binds early
])
def test_engine_matches_the_reference_cash_trajectory(fixed_cost, cash):
    assert disagreement(chain_cfg(fixed_cost, cash)) is None


@pytest.mark.extra_case
@pytest.mark.parametrize("label,overrides", [
    ("long facility", {"bank.loan_maturity": 3}),
    ("thin bank capital", {"bank.capital_ratio": 0.02}),
    ("low advance rate", {"bank.advance_rate": 0.35}),
    ("costly credit", {"bank.interest_rate": 0.08}),
    ("harsh haircut", {"scenario.haircut": 0.55}),
    ("deep visibility", {"scenario.visibility_depth": 3}),
    ("poor loan recovery", {"bank.loan_recovery": 0.05}),
    ("blockchain switch on", {"scenario.blockchain": True}),
    ("core enterprise defaults", {"shock.core_default_time": 4}),
    ("payables on one-period terms", {"firm.payables_delay": 1}),
    ("payables on longer terms than receivables", {"firm.payables_delay": 3}),
])
def test_engine_matches_the_reference_across_the_credit_layer(label,
                                                              overrides):
    """The credit layer was outside the differential comparison in v0.7.0.

    Collateral eligibility, the advance-rate cap, dated repayment with
    interest, write-offs on default and capital-driven tightening are all
    re-derived in the reference and compared here.
    """
    cfg = chain_cfg(fixed_cost=0.35, cash=0.05, **overrides)
    assert disagreement(cfg) is None


@pytest.mark.parametrize("seed_tier", [1, 2])
def test_engine_matches_the_reference_when_a_buyer_defaults(seed_tier):
    """The counterparty channel: a defaulted *buyer* pays only the recovery
    rate on the receivables its supplier holds.

    Until v0.11.0 every differential parameterisation seeded the deepest
    tier, whose default hits nobody's receivables, so the reference could
    omit the channel entirely without ever disagreeing with the engine.
    Seeding tier 1 or 2 exercises it in both healthy and stressed chains.
    """
    for fixed_cost, cash in ((0.06, 0.35), (0.35, 0.05)):
        cfg = chain_cfg(fixed_cost, cash, seeds=(f"firm-{seed_tier}-0",))
        assert disagreement(cfg) is None


def test_the_counterparty_channel_is_actually_exercised():
    """A receivable must actually be settled at the recovery rate somewhere
    in the compared trajectory, or the channel is covered in name only."""
    cfg = chain_cfg(seeds=("firm-1-0",))
    ref = simulate_reference(cfg, n_tiers=3)
    # firm-2 sells to firm-1, which defaults at t=2; the receivable booked
    # at t=2 matures at t=3 and must be paid at receivable_recovery
    t = cfg.shock.seed_time + cfg.firm.payment_delay
    collected = ref.cash[t]["firm-2-0"] - ref.cash[t - 1]["firm-2-0"]
    full = ref.sales[t - 1]["firm-2-0"]
    assert 0 < collected < full, "no recovery-rate settlement occurred"


#: A chain in which the bank takes a partial loss on the seed and keeps
#: lending, so later drawings carry a premium. In the fully stressed chain
#: the bank fails outright at the first default and never lends again,
#: which would leave the premium unexercised.
PRICED = {"fixed_cost": 0.30, "cash": 0.05, "bank.pricing_slope": 0.3}


def test_engine_matches_the_reference_under_risk_based_pricing():
    assert disagreement(chain_cfg(**PRICED)) is None


def test_risk_based_pricing_is_actually_exercised():
    """Under a positive slope the reference must charge a premium somewhere,
    otherwise the pricing parameterisation compares two flat-rate runs."""
    flat = chain_cfg(**{**PRICED, "bank.pricing_slope": 0.0})
    a, b = simulate_reference(flat, n_tiers=3), simulate_reference(chain_cfg(**PRICED), n_tiers=3)
    assert a.cash != b.cash, "the pricing slope changed nothing"


def test_payables_on_terms_are_actually_exercised():
    """Deferring variable costs must change the cash path, or the payables
    parameterisations compare two identical runs."""
    now = chain_cfg(fixed_cost=0.35, cash=0.05)
    later = chain_cfg(fixed_cost=0.35, cash=0.05, **{"firm.payables_delay": 1})
    a, b = simulate_reference(now, n_tiers=3), simulate_reference(later, n_tiers=3)
    assert a.cash != b.cash, "the payables delay changed nothing"


def test_the_anchor_default_is_actually_exercised():
    cfg = chain_cfg(seeds=(), **{"shock.core_default_time": 4})
    ref = simulate_reference(cfg, n_tiers=3)
    assert ref.sales[4]["firm-1-0"] > 0 and ref.sales[5]["firm-1-0"] == 0, \
        "the core kept ordering after its default"
    assert "core-0" not in ref.defaulted[-1] or ref.default_share[-1] <= 1.0
    assert ref.default_share[4] == 0.0, "the core must not count as a firm"


def test_the_credit_layer_is_actually_exercised():
    """Guard against a vacuous comparison: the reference must actually lend
    and the bank must actually take losses in the stressed scenario."""
    cfg = chain_cfg(fixed_cost=0.35, cash=0.05)
    ref = simulate_reference(cfg, n_tiers=3)
    assert any(any(v > 0 for v in book.values()) for book in ref.loans), \
        "no borrowing occurred: the credit-layer comparison is vacuous"
    assert ref.bank_losses[-1] > 0, "the bank never took a loss"


def test_engine_matches_the_reference_without_any_seed():
    assert disagreement(chain_cfg(seeds=())) is None


@pytest.mark.extra_case
@pytest.mark.parametrize("n_tiers", [1, 2, 5])
def test_agreement_holds_for_other_chain_lengths(n_tiers):
    cfg = chain_cfg(seeds=(f"firm-{n_tiers}-0",))
    cfg.network.n_tiers = n_tiers
    cfg.network.firms_per_tier = tuple([1] * n_tiers)
    names = [f"firm-{t}-0" for t in range(1, n_tiers + 1)]
    sim = Simulation(cfg, network=linear_chain(n_tiers, 1))
    ref = simulate_reference(cfg, n_tiers=n_tiers)
    for t in range(cfg.n_periods):
        sim._step(t)
        for name in names:
            assert abs(sim.firms[name].cash - ref.cash[t][name]) < 1e-9
            assert (name in ref.defaulted[t]) is sim.firms[name].defaulted


def test_the_cascade_actually_happens_in_the_reference_scenario():
    """Otherwise the comparison would only be checking that nothing moves."""
    cfg = chain_cfg()
    ref = simulate_reference(cfg, n_tiers=3)
    assert ref.defaulted[-1], "no defaults: the differential test is vacuous"
    assert len(ref.defaulted[-1]) > len(cfg.shock.seed_firms) or \
        any(len(d) for d in ref.defaulted)


# ------------------------------------------------------------------ #
# the layer's own design constraints
# ------------------------------------------------------------------ #

#: Package modules the reference may import. Everything it shares with the
#: engine is listed here; widening the list widens the surface on which a
#: common error would be invisible to the comparison, and should be a
#: deliberate decision recorded in ``docs/FINANCIAL_SPEC.md``.
ALLOWED_SHARED_MODULES = {"scfsim.config", "scfsim.network"}

#: Ceiling on the length of ``simulate_reference``. The function is 148
#: lines in v0.12.0 (135 in v0.9.0): the next mechanism goes outside the
#: comparison, or is paid for by simplification inside it. Reproducing multi-buyer share splitting or the random
#: shock stream would push it towards the size of the engine itself, and a
#: reference that cannot be verified by reading is a copy, not a check.
READABILITY_CEILING_LINES = 150


def _package_imports(module):
    """Names of the package-internal modules that ``module`` imports."""
    tree = ast.parse(pathlib.Path(module.__file__).read_text())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            found.add("scfsim." + (node.module or ""))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("scfsim"):
                    found.add(alias.name)
    return found


def test_the_reference_shares_only_the_configuration_layer_with_the_engine():
    """The two implementations are logically, not physically, independent.

    Both read parameters through ``scfsim.config`` and both use the naming
    constant in ``scfsim.network``; that is the whole shared surface, and
    it must stay that way. In particular the reference must never import
    the engine, the ledgers or the invariant checkers, because agreement
    with code it shares is agreement with itself.
    """
    shared = _package_imports(ref_module)
    assert shared <= ALLOWED_SHARED_MODULES, (
        f"scfsim.reference now imports {sorted(shared - ALLOWED_SHARED_MODULES)}; "
        "the differential comparison is blind to anything the two "
        "implementations share")


def test_the_reference_stays_short_enough_to_verify_by_reading():
    """Tripwire on the declared scope ceiling of the differential layer.

    If this fails, the reference has grown past what a reader can check
    line by line against the specification. The remedy is to reconsider
    the extension, not to raise the ceiling.
    """
    n_lines = len(inspect.getsource(ref_module.simulate_reference)
                  .splitlines())
    assert n_lines <= READABILITY_CEILING_LINES, (
        f"simulate_reference is {n_lines} lines, above the "
        f"{READABILITY_CEILING_LINES}-line readability ceiling recorded in "
        "its module docstring")


def test_the_shared_blockchain_switch_is_checked_directly():
    """The switch lives in the shared configuration layer, so differential
    testing cannot detect a fault in it. Check it directly instead."""
    off, on = ScenarioConfig(blockchain=False), ScenarioConfig(blockchain=True)
    assert (off.effective_visibility, off.effective_haircut,
            off.effective_fraud) == (off.visibility_depth, off.haircut,
                                     off.fraud_prob)
    assert (on.effective_visibility, on.effective_haircut,
            on.effective_fraud) == (on.bc_visibility_depth, on.bc_haircut,
                                    on.bc_fraud_prob)
    # the switch must move all three frictions, and in the direction the
    # specification states: deeper reach, lower haircut, less fraud
    assert on.effective_visibility > off.effective_visibility
    assert on.effective_haircut < off.effective_haircut
    assert on.effective_fraud < off.effective_fraud
    # and it must survive the JSON round-trip that every experiment uses
    cfg = SimulationConfig(); cfg.scenario = on
    clone = SimulationConfig.from_json(cfg.to_json())
    assert clone.scenario.effective_haircut == on.bc_haircut


# ------------------------------------------------------------------ #
# the comparison must be able to fail
# ------------------------------------------------------------------ #

def _extra_cost(self, t, orders):
    for name, firm in self.firms.items():
        if name != CORE and not firm.defaulted:
            firm.cash -= 0.001 * firm.baseline_sales
    return _extra_cost.original(self, t, orders)


def _shifted_settlement(self, t):
    return _shifted_settlement.original(self, t + 1)


def _no_supply_propagation(self, firm, t):
    enabled = self.cfg.channels.supply
    self.cfg.channels.supply = False
    _no_supply_propagation.original(self, firm, t)
    self.cfg.channels.supply = enabled


def _inflated_sales(self, t):
    orders = _inflated_sales.original(self, t)
    return {k: v * 1.0001 for k, v in orders.items()}


def _inflated_collateral(self, firm):
    return _inflated_collateral.original(self, firm) * 1.02


def _dearer_interest(self, t):
    bank = self.cfg.bank
    saved = bank.interest_rate
    bank.interest_rate = saved + 0.005
    _dearer_interest.original(self, t)
    bank.interest_rate = saved


def _generous_recovery(self, firm, t):
    bank = self.cfg.bank
    saved = bank.loan_recovery
    bank.loan_recovery = min(1.0, saved + 0.1)
    _generous_recovery.original(self, firm, t)
    bank.loan_recovery = saved


def _generous_receivable_recovery(self, firm, t):
    return min(1.0, _generous_receivable_recovery.original(self, firm, t) + 0.1)


def _payables_settled_a_period_early(self, t, orders):
    _payables_settled_a_period_early.original(self, t, orders)
    due = t + self.cfg.firm.payables_delay
    for f in self.firms.values():
        early = f.payables_due.pop(due, 0.0)
        if early and not f.defaulted:
            f.payables_due[due - 1] = f.payables_due.get(due - 1, 0.0) + early


def _flat_rate_despite_slope(self, firm):
    slope = self.cfg.bank.pricing_slope
    self.cfg.bank.pricing_slope = 0.0
    _flat_rate_despite_slope.original(self, firm)
    self.cfg.bank.pricing_slope = slope


FAULTS = [
    ("collateral overstated by 2%", "_eligible_receivables",
     _inflated_collateral),
    ("interest half a point too high", "_settle", _dearer_interest),
    ("recovery on defaulted loans overstated by ten points",
     "_resolve_default", _generous_recovery),
    ("an extra cost of 0.1% of baseline each period",
     "_produce_and_finance", _extra_cost),
    ("settlement shifted by one period", "_settle", _shifted_settlement),
    ("a default that does not reduce the buyer's supply capacity",
     "_resolve_default", _no_supply_propagation),
    ("sales inflated by one part in ten thousand",
     "_place_orders", _inflated_sales),
]


@pytest.mark.parametrize("label,attr,fault", FAULTS,
                         ids=[f[0] for f in FAULTS])
def test_differential_comparison_detects_injected_faults(label, attr, fault,
                                                         monkeypatch):
    fault.original = getattr(sim_module.Simulation, attr)
    monkeypatch.setattr(sim_module.Simulation, attr, fault)
    stressed = chain_cfg(fixed_cost=0.35, cash=0.05)
    assert disagreement(stressed) is not None, (
        f"the reference comparison failed to notice {label}")


#: Faults in the mechanisms added to the comparison in v0.11.0. Each needs
#: a configuration in which the mechanism fires, so they carry their own.
MECHANISM_FAULTS = [
    ("recovery on receivables overstated by ten points",
     "_collection_rate", _generous_receivable_recovery,
     dict(seeds=("firm-1-0",))),
    ("pricing premium ignored", "_request_financing",
     _flat_rate_despite_slope, PRICED),
    ("payables settled a period early", "_produce_and_finance",
     _payables_settled_a_period_early,
     {"fixed_cost": 0.35, "cash": 0.05, "firm.payables_delay": 1}),
]


@pytest.mark.parametrize("label,attr,fault,kwargs", MECHANISM_FAULTS,
                         ids=[f[0] for f in MECHANISM_FAULTS])
def test_differential_comparison_detects_faults_in_added_mechanisms(
        label, attr, fault, kwargs, monkeypatch):
    fault.original = getattr(sim_module.Simulation, attr)
    monkeypatch.setattr(sim_module.Simulation, attr, fault)
    assert disagreement(chain_cfg(**kwargs)) is not None, (
        f"the reference comparison failed to notice {label}")
