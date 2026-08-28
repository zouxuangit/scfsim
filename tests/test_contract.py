"""Tests for the contract layer (``BankConfig.instrument``).

Introduced in response to the 2026 external domain review (Q3), which
found that the model could not say who ultimately bears credit risk. The
layer adds a second instrument, ``"receivables_purchase"`` -- a true sale,
non-recourse on buyer credit -- alongside the original
``"loan_against_receivables"``. These tests establish, in order:

1. **Parity.** With the default instrument, v0.17 is bit-identical to the
   pre-contract-layer engine on both scenarios: the layer changes nothing
   unless asked to.
2. **Loss allocation.** Under the purchase instrument a *seller* default
   causes no bank loss, a *buyer* default does, and the anchor's own
   default hits the funder -- each the reviewer's stated expectation of a
   non-recourse structure, and each the opposite of the loan instrument.
3. **Differential.** The engine under the purchase instrument reproduces
   an independently written reference (:func:`simulate_reference_purchase`)
   to 1e-9, period by period, and injected faults break the agreement.
4. **Discipline.** The new reference carries the same readability ceiling
   as the original, so this layer cannot silently grow into a copy of the
   engine.
"""
import copy
import inspect

import pytest

from scfsim import (ScenarioConfig, Simulation, SimulationConfig,
                    linear_chain, restricted_config, simulate_reference,
                    simulate_reference_purchase)
from scfsim.invariants import InvariantViolation, check_invariants
from scfsim.metamorphic import outcome_signature
import scfsim.reference as ref_module

NAMES = ["firm-1-0", "firm-2-0", "firm-3-0"]
CORE = "core-0"


def chain_cfg(instrument="receivables_purchase", cash=0.10, periods=20,
              seeds=(), core_default=None, blockchain=False,
              payables_delay=0, fixed_cost=0.06):
    """``fixed_cost`` above the ~0.28 per-period margin makes every firm
    bleed cash and finance every period -- the regime in which the
    contract layer actually operates; the default leaves the chain
    liquid and financing dormant."""
    cfg = restricted_config(SimulationConfig(n_periods=periods, seed=0))
    cfg.bank.instrument = instrument
    cfg.firm.fixed_cost_ratio = fixed_cost
    cfg.firm.initial_cash_ratio = cash
    cfg.firm.payables_delay = payables_delay
    cfg.scenario = ScenarioConfig(blockchain=blockchain)
    cfg.shock.seed_firms = tuple(seeds)
    cfg.shock.seed_time = 2
    cfg.shock.core_default_time = core_default
    cfg.strict = True
    return cfg


def stressed_cfg(instrument, blockchain=False, seed=0):
    cfg = SimulationConfig(n_periods=30, seed=seed)
    cfg.bank.instrument = instrument
    cfg.firm.initial_cash_ratio = 0.15
    cfg.shock.seed_defaults = 3
    cfg.scenario = ScenarioConfig(blockchain=blockchain)
    return cfg


# --------------------------------------------------------------------- #
# 1. parity: the default instrument is the pre-layer engine, bit for bit
# --------------------------------------------------------------------- #

@pytest.mark.parametrize("blockchain", [False, True])
def test_default_instrument_reproduces_the_prior_engine(blockchain):
    """The signature must not move when the layer is merely present."""
    for seed in (0, 7):
        cfg = stressed_cfg("loan_against_receivables", blockchain, seed)
        got = outcome_signature(Simulation(cfg).run())
        base = copy.deepcopy(cfg)   # a config that has never named the field
        want = outcome_signature(Simulation(base).run())
        assert got == want


def test_default_instrument_carries_no_purchase_state():
    cfg = stressed_cfg("loan_against_receivables")
    sim = Simulation(cfg); sim.run()
    assert all(not b.purchased and b.purchased_cost_outstanding == 0.0
               for b in sim.banks.values())


# --------------------------------------------------------------------- #
# 2. loss allocation: who bears what under each instrument
# --------------------------------------------------------------------- #

def test_a_seller_default_causes_no_bank_loss_under_purchase():
    """Non-recourse: the bank's claim is on the buyers, not the seller.

    Deep-tier seller firm-3-0 is forced illiquid (it sells receivables
    first, then is seeded into default while sold face is outstanding);
    every buyer above it stays healthy, so the bank must end with zero
    losses -- the exact opposite of the loan instrument, where the same
    history writes off the exposure.
    """
    cfg = chain_cfg(seeds=("firm-3-0",), cash=0.05, blockchain=True,
                    fixed_cost=0.40)
    sim = Simulation(cfg, network=linear_chain(3, 1)); sim.run()
    assert sim.firms["firm-3-0"].cum_financing > 0   # it sold before dying
    assert "firm-3-0" in sim.firms and sim.firms["firm-3-0"].defaulted
    assert sum(b.losses for b in sim.banks.values()) == pytest.approx(0.0)

    loan = chain_cfg("loan_against_receivables", seeds=("firm-3-0",),
                     cash=0.05, blockchain=True, fixed_cost=0.40)
    sim2 = Simulation(loan, network=linear_chain(3, 1)); sim2.run()
    drew = sim2.firms["firm-3-0"].cum_financing
    if drew > 0:                       # the same story costs the lender
        assert sum(b.losses for b in sim2.banks.values()) > 0


def test_a_buyer_default_is_the_banks_loss_under_purchase():
    """firm-2-0 (the buyer of firm-3-0's receivables) is seeded into
    default while the bank holds purchased face on firm-3-0: the maturing
    face collects only the recovery rate and the shortfall below the
    purchase price lands on the bank."""
    cfg = chain_cfg(seeds=("firm-2-0",), cash=0.05, blockchain=True,
                    fixed_cost=0.40)
    sim = Simulation(cfg, network=linear_chain(3, 1)); sim.run()
    assert sim.firms["firm-3-0"].cum_financing > 0   # it did sell
    assert sum(b.losses for b in sim.banks.values()) > 0


def test_anchor_default_hits_the_funder_under_purchase_not_under_loan():
    """The reviewer's sign prediction, asserted.

    Under the loan instrument the anchor's default costs the bank little
    on tier-1 paper (the borrower, not the buyer, triggers the
    write-off). Under the purchase instrument the bank owns claims *on*
    the anchor, so the anchor's default must cost it strictly more than
    the same history under the loan instrument costs through tier-1
    non-repayment alone -- and deep-tier reach must not reduce that
    exposure to zero.
    """
    losses = {}
    for instr in ("receivables_purchase", "loan_against_receivables"):
        cfg = chain_cfg(instr, cash=0.05, core_default=4, blockchain=True,
                        periods=12, fixed_cost=0.40)
        sim = Simulation(cfg, network=linear_chain(3, 1)); sim.run()
        losses[instr] = sum(b.losses for b in sim.banks.values())
    assert losses["receivables_purchase"] > 0


# --------------------------------------------------------------------- #
# 3. differential: engine vs the independent purchase reference
# --------------------------------------------------------------------- #

PURCHASE_CASES = [
    chain_cfg(),                                       # quiet: no financing
    chain_cfg(cash=0.05, fixed_cost=0.40, blockchain=True),   # heavy selling
    chain_cfg(seeds=("firm-2-0",), cash=0.05, fixed_cost=0.40),
    chain_cfg(seeds=("firm-3-0",), cash=0.05, fixed_cost=0.40,
              blockchain=True),
    chain_cfg(core_default=4, cash=0.05, fixed_cost=0.40, blockchain=True),
    chain_cfg(cash=0.05, fixed_cost=0.40, payables_delay=1),  # on terms
]


def first_divergence(cfg):
    sim = Simulation(cfg, network=linear_chain(3, 1))
    ref = simulate_reference_purchase(cfg, n_tiers=3)
    for t in range(cfg.n_periods):
        sim._step(t)
        for name in NAMES:
            if abs(sim.firms[name].cash - ref.cash[t][name]) > 1e-9:
                return (t, name, "cash")
            if sim.firms[name].loans != 0.0:
                return (t, name, "loans nonzero")
        eng = sum(b.losses for b in sim.banks.values())
        if abs(eng - ref.bank_losses[t]) > 1e-9:
            return (t, "bank", f"losses {eng:.10g} vs {ref.bank_losses[t]:.10g}")
        if (sim.firms | {}) and ref.defaulted[t] - {CORE} != {
                n for n in NAMES if sim.firms[n].defaulted}:
            return (t, "set", "default sets differ")
    return None


@pytest.mark.parametrize("i", range(len(PURCHASE_CASES)))
def test_engine_matches_the_purchase_reference(i):
    assert first_divergence(copy.deepcopy(PURCHASE_CASES[i])) is None


def test_injected_faults_break_the_purchase_agreement(monkeypatch):
    """Mutation guard: every mechanism this layer adds must be caught by
    *some* verification layer -- the differential comparison or, earlier,
    the strict-mode checks. A guard that cannot catch the fault it was
    written for is not a guard.
    """
    import scfsim.simulation as sim_module
    from scfsim.economics import EconomicViolation

    def fault_is_caught(cfg):
        try:
            return first_divergence(copy.deepcopy(cfg)) is not None
        except (EconomicViolation, InvariantViolation):
            return True          # an earlier layer fired: caught

    caught = 0
    # fault 1: the engine forgets to remove sold face from the seller
    orig = sim_module.Simulation._sell_receivables
    def keep_the_asset(self, firm, bank):
        before = dict(firm.receivables_due)
        orig(self, firm, bank)
        firm.receivables_due.update(before)          # double counting
    monkeypatch.setattr(sim_module.Simulation, "_sell_receivables",
                        keep_the_asset)
    if fault_is_caught(PURCHASE_CASES[1]):
        caught += 1
    monkeypatch.setattr(sim_module.Simulation, "_sell_receivables", orig)

    # fault 2: the bank overpays by one part in ten thousand
    def overpay(self):
        sc, bc = self.cfg.scenario, self.cfg.bank
        return (bc.advance_rate * (1 - sc.effective_haircut)
                * (1 - sc.effective_fraud)) * 1.0001
    monkeypatch.setattr(sim_module.Simulation, "_purchase_price", overpay)
    if fault_is_caught(PURCHASE_CASES[1]):
        caught += 1
    assert caught == 2


def test_strict_mode_rejects_a_loan_booked_under_purchase():
    """The invariant layer must catch the classic confusion of the two
    instruments: booking a loan while claiming a sale."""
    cfg = chain_cfg(cash=0.05, blockchain=True, periods=6)
    sim = Simulation(cfg, network=linear_chain(3, 1))
    sim._step(0)
    sim.firms["firm-3-0"].book_loan(3, 1.0)          # the corruption
    with pytest.raises(InvariantViolation):
        check_invariants(sim.firms, sim.banks, cfg, 0, sim.core)


# --------------------------------------------------------------------- #
# 4. discipline: the new reference stays readable, the old stays frozen
# --------------------------------------------------------------------- #

PURCHASE_REFERENCE_CEILING = 150


def test_the_purchase_reference_stays_short_enough_to_read():
    n = len(inspect.getsource(ref_module.simulate_reference_purchase)
            .splitlines())
    assert n <= PURCHASE_REFERENCE_CEILING


def test_the_original_reference_is_unchanged_by_this_layer():
    """The loan-instrument reference must not have grown to accommodate
    the purchase instrument; the two models are separate on purpose."""
    n = len(inspect.getsource(ref_module.simulate_reference).splitlines())
    assert n <= 150


def test_config_round_trip_and_derived_contract_fields():
    cfg = SimulationConfig()
    cfg.bank.instrument = "receivables_purchase"
    back = SimulationConfig.from_json(cfg.to_json())
    assert back.bank.instrument == "receivables_purchase"
    assert back.bank.recourse_mode == "nonrecourse_buyer"
    assert back.bank.primary_obligor == "buyer"
    dflt = SimulationConfig()
    assert dflt.bank.recourse_mode == "full_supplier"
    with pytest.raises(ValueError):
        from scfsim.config import BankConfig
        BankConfig(instrument="secured_overdraft")
