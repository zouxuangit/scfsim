"""Tests for the accounting identities.

Two levels of assurance:

1. Every simulation in this file runs in ``strict`` mode, so the identities
   are checked after each period of each run.
2. Mutation tests deliberately corrupt the ledgers in eleven different ways
   and assert that the checker catches each one. A checker that never
   fails is worthless, so its sensitivity is itself tested.
"""
import copy

import pytest

from scfsim import (InvariantViolation, ScenarioConfig, Simulation,
                    SimulationConfig, check_invariants, generate_network,
                    network_invariants, run_batch)
from scfsim.config import ChannelConfig, NetworkConfig
from scfsim.network import CORE


def strict_cfg(seed=1, periods=25, **kw):
    cfg = SimulationConfig(n_periods=periods, seed=seed, strict=True)
    cfg.network.seed = seed
    cfg.firm.initial_cash_ratio = 0.15
    cfg.firm.receivable_recovery = 0.15
    cfg.shock.liquidity_shock_prob = 0.10
    cfg.shock.liquidity_shock_size = 0.6
    cfg.shock.demand_sigma = 0.18
    cfg.shock.seed_defaults = 3
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


# ------------------------------------------------------------------ #
# 1. the identities hold on real runs
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_identities_hold_throughout_a_stressed_run(seed):
    Simulation(strict_cfg(seed)).run()   # strict=True checks every period


def test_identities_hold_under_blockchain_scenario():
    cfg = strict_cfg(9)
    cfg.scenario = ScenarioConfig(blockchain=True)
    Simulation(cfg).run()


def test_identities_hold_with_long_facilities_and_thin_capital():
    cfg = strict_cfg(11)
    cfg.bank.loan_maturity = 4
    cfg.bank.capital_ratio = 0.015
    Simulation(cfg).run()


def test_identities_hold_with_payables_on_terms():
    for delay in (1, 3):
        cfg = strict_cfg(17)
        cfg.firm.payables_delay = delay
        Simulation(cfg).run()


def test_identities_hold_under_risk_based_pricing_and_an_anchor_default():
    cfg = strict_cfg(13)
    cfg.bank.pricing_slope = 0.3
    cfg.bank.loan_maturity = 3
    cfg.shock.core_default_time = 6
    res = Simulation(cfg).run()
    assert res.summary["n_firms"] == 56, "the core must never be counted"


def test_identities_hold_for_every_channel_ablation():
    for cp in (True, False):
        for sup in (True, False):
            cfg = strict_cfg(13)
            cfg.channels = ChannelConfig(counterparty=cp, supply=sup,
                                         demand=not sup, credit_crunch=cp)
            Simulation(cfg).run()


def test_generated_networks_satisfy_structural_invariants():
    for seed in range(5):
        g = generate_network(NetworkConfig(seed=seed))
        assert network_invariants(g) == []


# ------------------------------------------------------------------ #
# 2. mutation tests: the checker must actually catch corruption
# ------------------------------------------------------------------ #

def _finished_sim():
    cfg = strict_cfg(1, periods=12)
    cfg.strict = False          # corrupt state after the run, then check
    sim = Simulation(cfg)
    sim.run()
    return sim


def _some_firm(sim, index=1):
    return [f for n, f in sim.firms.items() if n != CORE][index]


def _break_loan_ledger(sim):
    _some_firm(sim).loans += 5.0


def _break_bank_exposure(sim):
    sim.banks[0].outstanding["firm-1-0"] = 999.0


def _break_supply_capacity(sim):
    sim.firms["firm-1-0"].supply_capacity = 1.5


def _break_defaulted_firm_still_borrowing(sim):
    f = sim.firms["firm-1-0"]
    f.defaulted = True
    f.book_loan(99, 3.0)


def _break_writeoffs_exceed_lending(sim):
    sim.banks[0].losses = sim.banks[0].cum_credit * 10 + 100


def _break_aggregate_funding(sim):
    _some_firm(sim, 2).cum_financing += 7.0


def _break_interest_ledger(sim):
    f = _some_firm(sim, 1)
    f.interest_book[123] = 5.0        # interest owed on no principal


def _break_negative_interest(sim):
    f = _some_firm(sim, 1)
    f.book_loan(88, 10.0, rate=0.0)
    f.interest_book[88] = -1.0


def _break_negative_payable(sim):
    sim.cfg.firm.payables_delay = 1
    _some_firm(sim, 2).book_payable(90, -4.0)


def _break_defaulted_firm_owing_suppliers(sim):
    sim.cfg.firm.payables_delay = 1
    f = sim.firms["firm-1-0"]
    f.defaulted = True
    f.default_time = 3
    f.supply_capacity = 0.0
    f.book_payable(91, 2.0)


def _break_interest_rate_ceiling(sim):
    f = _some_firm(sim, 1)
    f.book_loan(77, 10.0, rate=0.5)   # far above interest_rate + slope


MUTATIONS = [
    ("loan ledger vs balance", _break_loan_ledger),
    ("interest owed on no principal", _break_interest_ledger),
    ("negative interest booked", _break_negative_interest),
    ("negative payable booked", _break_negative_payable),
    ("defaulted firm still owes suppliers", _break_defaulted_firm_owing_suppliers),
    ("interest above the maximum rate", _break_interest_rate_ceiling),
    ("bank exposure vs borrower balance", _break_bank_exposure),
    ("supply capacity out of bounds", _break_supply_capacity),
    ("defaulted firm still carries loans", _break_defaulted_firm_still_borrowing),
    ("write-offs exceed lending", _break_writeoffs_exceed_lending),
    ("aggregate drawings vs supply", _break_aggregate_funding),
]


@pytest.mark.parametrize("label,mutate", MUTATIONS,
                         ids=[m[0] for m in MUTATIONS])
def test_checker_detects_injected_book_keeping_errors(label, mutate):
    sim = _finished_sim()
    check_invariants(sim.firms, sim.banks, sim.cfg, 0, CORE)   # clean first
    mutate(sim)
    with pytest.raises(InvariantViolation):
        check_invariants(sim.firms, sim.banks, sim.cfg, 0, CORE)


def test_broken_network_shares_are_reported():
    g = generate_network(NetworkConfig(seed=1))
    u, v = next(iter(g.edges()))
    g[u][v]["share"] += 0.5
    assert network_invariants(g) != []


def test_strict_mode_is_off_by_default():
    assert SimulationConfig().strict is False
    assert SimulationConfig.from_json(
        SimulationConfig(strict=True).to_json()).strict is True


# ------------------------------------------------------------------ #
# 3. remaining error branches of the checkers
# ------------------------------------------------------------------ #

def test_checker_detects_negative_and_orphaned_balances():
    sim = _finished_sim()
    f = _some_firm(sim)
    f.loans = -1.0
    f.loan_book = {5: -1.0}
    with pytest.raises(InvariantViolation, match="negative"):
        check_invariants(sim.firms, sim.banks, sim.cfg, 0, CORE)


def test_checker_detects_negative_receivable():
    sim = _finished_sim()
    _some_firm(sim).receivables_due[99] = -3.0
    with pytest.raises(InvariantViolation, match="negative receivable"):
        check_invariants(sim.firms, sim.banks, sim.cfg, 0, CORE)


def test_checker_detects_default_without_a_timestamp():
    sim = _finished_sim()
    f = _some_firm(sim)
    f.defaulted = True
    f.loans = 0.0
    f.loan_book = {}
    f.supply_capacity = 0.0
    f.default_time = -1
    with pytest.raises(InvariantViolation, match="without a default time"):
        check_invariants(sim.firms, sim.banks, sim.cfg, 0, CORE)


def _make_borrower(sim, amount=2.0):
    """Give a surviving firm a live drawing, recorded by its own bank."""
    name = next(n for n, f in sim.firms.items()
                if n != CORE and not f.defaulted)
    f = sim.firms[name]
    f.book_loan(999, amount)
    f.cum_financing += amount
    bank = sim.banks[f.bank]
    bank.outstanding[name] = f.loans
    bank.cum_credit += amount
    return name, f


def test_checker_detects_exposure_recorded_by_the_wrong_bank():
    sim = _finished_sim()
    name, f = _make_borrower(sim)
    wrong = (f.bank + 1) % len(sim.banks)
    sim.banks[wrong].outstanding[name] = f.loans
    with pytest.raises(InvariantViolation, match="which banks with"):
        check_invariants(sim.firms, sim.banks, sim.cfg, 0, CORE)


def test_checker_detects_unrecorded_exposure():
    sim = _finished_sim()
    name, f = _make_borrower(sim)
    sim.banks[f.bank].outstanding.pop(name)
    with pytest.raises(InvariantViolation, match="unrecorded exposure"):
        check_invariants(sim.firms, sim.banks, sim.cfg, 0, CORE)


def test_checker_detects_a_failed_bank_that_still_lends(monkeypatch):
    """Defence in depth: BankState.tightening() currently returns zero for a
    failed bank, so this branch is unreachable through the public API. The
    guard exists in case that ever changes, and is tested by forcing it."""
    from scfsim.agents import BankState
    monkeypatch.setattr(BankState, "tightening", lambda self: 1.0)
    sim = _finished_sim()
    sim.banks[0].failed = True
    with pytest.raises(InvariantViolation, match="failed but still lending"):
        check_invariants(sim.firms, sim.banks, sim.cfg, 0, CORE)
