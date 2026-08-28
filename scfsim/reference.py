"""An independent reference implementation, for differential testing.

Every earlier verification layer is written in terms of a property: a
bound, an identity, an economic proposition, an invariance. Differential
testing asks something different — does a second, independently written
implementation of the same specification produce the same numbers? — and
so catches a class of failure the property-based layers cannot: an
implementation slip that violates no stated property because nobody
thought to state the property it breaks.

The reference below re-derives, directly from the specification in
``docs/FINANCIAL_SPEC.md``, the behaviour of a deliberately restricted
model:

* a single linear chain — one firm per tier, each selling its entire
  output to the one firm in the tier below, and tier 1 to the core;
* no stochastic shocks, so demand is constant and no liquidity draws
  occur; exogenous defaults may still be named explicitly via
  ``ShockConfig.seed_firms``, which is what exercises the supply cascade.

Receivables financing **is** covered: collateral eligibility (visibility
depth, haircut, expected fraud), the advance-rate cap on the stock of
debt, dated repayment with interest fixed at drawing (including risk-based
pricing), write-offs on default, and the capital-driven credit tightening
of the single bank are all re-derived here, as is the payables ledger
when variable costs are paid on terms (``FirmConfig.payables_delay``). Version 0.7.0 excluded them,
which left the entire credit layer outside the differential comparison;
v0.8.0 closed that gap. The counterparty channel — a defaulted buyer pays
only the recovery rate on maturing receivables — is covered from v0.11.0.
Every earlier release had omitted it from the reference without saying
so: all differential parameterisations seeded the deepest tier, whose
default hits nobody's receivables, so the omission never produced a
disagreement. The anchor's own default (``ShockConfig.core_default_time``)
is covered as well.

Within those restrictions the model reduces to arithmetic that fits on one
screen and can be checked by reading. ``tests/test_reference.py`` asserts
that :class:`~scfsim.Simulation` reproduces it period by period.

**What this does and does not establish.** It is a re-derivation from the
same written specification, not a second opinion about what the model
*should* be. It therefore catches transcription and control-flow errors in
the engine, but a misconception shared by the specification and both
implementations would survive it. That limitation is the same one recorded
in ``docs/FINANCIAL_SPEC.md`` §7, and it is why independent domain review
remains on the submission checklist.

**What is shared with the engine.** The two implementations are logically
independent but not physically so: both read their parameters through the
dataclasses in :mod:`scfsim.config` — including the three ``effective_*``
properties of :class:`~scfsim.ScenarioConfig` that implement the blockchain
switch — and both use the node-naming constant in :mod:`scfsim.network`.
An error in that shared surface (a mis-mapped switch, a JSON round-trip
that drops a field) would affect both sides identically and is invisible
to the comparison. The surface is therefore kept small, guarded by a test
that fails if this module ever imports anything else from the package, and
covered directly by unit tests of the configuration layer rather than
indirectly by differential testing.

**The scope of this layer is final.** The remaining exclusions —
multi-buyer share splitting and stochastic shocks — are not oversights to
be closed in a later release. Covering them would require the reference to
reproduce the engine's network traversal and its random-number stream,
at which point it stops being a second implementation short enough to
verify by reading and becomes a copy of the engine, and a differential
test between an engine and its copy establishes nothing. The audit of
v0.8.0 recorded this ceiling; ``tests/test_reference.py`` enforces it with
a line-count tripwire on :func:`simulate_reference`, so that any future
extension has to be argued for rather than slipped in.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import networkx as nx

from .config import SimulationConfig
from .network import CORE


@dataclass
class ReferenceTrace:
    """Period-by-period record produced by the reference implementation."""

    cash: List[Dict[str, float]] = field(default_factory=list)
    sales: List[Dict[str, float]] = field(default_factory=list)
    loans: List[Dict[str, float]] = field(default_factory=list)
    defaulted: List[set] = field(default_factory=list)
    default_share: List[float] = field(default_factory=list)
    bank_losses: List[float] = field(default_factory=list)


def linear_chain(n_tiers: int = 3, n_banks: int = 1) -> nx.DiGraph:
    """One firm per tier, each selling its whole output to the tier below."""
    g = nx.DiGraph()
    g.add_node(CORE, tier=0, kind="core", bank=0)
    for b in range(n_banks):
        g.add_node(f"bank-{b}", tier=-1, kind="bank")
    previous = CORE
    for t in range(1, n_tiers + 1):
        name = f"firm-{t}-0"
        g.add_node(name, tier=t, kind="firm", bank=0)
        g.add_edge(name, previous, share=1.0)
        previous = name
    return g


def restricted_config(cfg: SimulationConfig) -> SimulationConfig:
    """Return ``cfg`` forced into the regime the reference model covers.

    Stochastic shocks and the random seed draw are disabled and the chain
    is served by a single bank; financing is left switched on.
    """
    import copy

    out = copy.deepcopy(cfg)
    out.shock.demand_sigma = 0.0
    out.shock.liquidity_shock_prob = 0.0
    out.shock.seed_defaults = 0      # no random draw; name seeds explicitly
    out.network.n_banks = 1          # one bank, so tightening is unambiguous
    return out


def simulate_reference(cfg: SimulationConfig,
                       n_tiers: Optional[int] = None) -> ReferenceTrace:
    """Run the restricted model from first principles.

    Written to be verified by reading rather than by testing: each step is
    one line of the specification.
    """
    fc = cfg.firm
    n_tiers = n_tiers or cfg.network.n_tiers
    names = [f"firm-{t}-0" for t in range(1, n_tiers + 1)]

    # baseline volumes: tier 1 supplies the core, each tier above supplies
    # the input share of the tier below
    baseline: Dict[str, float] = {}
    volume = fc.core_demand
    for name in names:
        baseline[name] = volume
        volume *= fc.input_share

    bc, sc = cfg.bank, cfg.scenario
    cash = {n: fc.initial_cash_ratio * baseline[n] for n in names}
    capacity = {n: 1.0 for n in names}
    defaulted: set = set()
    buyer_of = {n: (CORE if i == 0 else names[i - 1])
                for i, n in enumerate(names)}
    # loan ledger: principal (and the interest fixed at drawing) falling
    # due at each period, per firm
    loan_book: Dict[str, Dict[int, float]] = {n: {} for n in names}
    interest_book: Dict[str, Dict[int, float]] = {n: {} for n in names}
    payables: Dict[str, Dict[int, float]] = {n: {} for n in names}
    loans = {n: 0.0 for n in names}
    # the single bank: capital scaled to the SCF book it could hold
    bank_capital = cfg.bank.capital_ratio * sum(
        bc.advance_rate * baseline[n] * max(1, fc.payment_delay)
        for n in names)
    bank_losses = 0.0
    # warm start: one settlement cycle of receivables already in transit
    receivables: Dict[str, Dict[int, float]] = {
        n: {lag: baseline[n] for lag in range(fc.payment_delay)} for n in names
    }

    trace = ReferenceTrace()
    for t in range(cfg.n_periods):
        # 1. settlement -- collect what matured (a defaulted buyer pays
        #    only the recovery rate), then repay the loan tranche falling
        #    due together with the interest fixed when it was drawn
        for n in names:
            if n in defaulted:
                continue
            paid = 1.0
            if cfg.channels.counterparty and buyer_of[n] in defaulted:
                paid = fc.receivable_recovery
            cash[n] += receivables[n].pop(t, 0.0) * paid
            cash[n] -= payables[n].pop(t, 0.0)    # suppliers' invoices due
            principal = loan_book[n].pop(t, 0.0)
            interest = interest_book[n].pop(t, 0.0)
            if principal > 0:
                cash[n] -= principal + interest
                loans[n] = max(0.0, loans[n] - principal)

        # 2. orders and deliveries -- demand flows up the chain, each firm
        #    delivering its order book scaled by its remaining capacity
        sales: Dict[str, float] = {}
        upstream_demand = 0.0 if CORE in defaulted else fc.core_demand
        for n in names:
            if n in defaulted:
                sales[n] = 0.0
                upstream_demand = 0.0
                continue
            book = upstream_demand
            sales[n] = book * capacity[n]
            upstream_demand = fc.input_share * sales[n]

        # 3. production costs -- fixed costs now, variable costs now or on
        #    the suppliers' terms -- and the resulting receivable
        for n in names:
            if n in defaulted:
                continue
            cash[n] -= fc.fixed_cost_ratio * baseline[n]
            if fc.payables_delay == 0:
                cash[n] -= fc.cost_ratio * sales[n]
            elif sales[n] > 0:
                due = t + fc.payables_delay
                payables[n][due] = payables[n].get(due, 0.0) + fc.cost_ratio * sales[n]
            if sales[n] > 0:
                due = t + fc.payment_delay
                receivables[n][due] = receivables[n].get(due, 0.0) + sales[n]

        # 4. financing -- an illiquid firm draws against eligible
        #    receivables, capped by the advance rate on the stock of debt
        #    and by the bank's capital-driven credit multiplier
        tightening, rate = 1.0, bc.interest_rate
        if cfg.channels.credit_crunch and bank_capital > 0:
            tightening = max(0.0, 1.0 - bank_losses / bank_capital)
            rate = bc.interest_rate + bc.pricing_slope * (1.0 - tightening)
        for i, n in enumerate(names):
            if n in defaulted or cash[n] >= 0:
                continue
            outstanding = sum(receivables[n].values())
            tier = i + 1
            if tier <= sc.effective_visibility:
                accessible = outstanding
            else:
                accessible = sc.deep_tier_access * outstanding
            eligible = (accessible * (1 - sc.effective_haircut)
                        * (1 - sc.effective_fraud))
            headroom = bc.advance_rate * eligible * tightening - loans[n]
            draw = min(-cash[n], max(0.0, headroom))
            if draw > 0:
                cash[n] += draw
                loans[n] += draw
                due = t + bc.loan_maturity
                loan_book[n][due] = loan_book[n].get(due, 0.0) + draw
                interest_book[n][due] = (interest_book[n].get(due, 0.0)
                                         + draw * rate)

        # 5. default resolution -- illiquidity, then loss of supply for the
        #    buyer immediately downstream; the same book-keeping applies to
        #    the exogenous seeds, which the engine applies afterwards
        def fail(n: str) -> None:
            nonlocal bank_losses
            defaulted.add(n)
            capacity[n] = 0.0
            bank_losses += loans[n] * (1 - bc.loan_recovery)
            loans[n] = 0.0
            loan_book[n].clear()
            interest_book[n].clear()
            payables[n].clear()
            if buyer_of[n] != CORE:            # the firm it supplies
                capacity[buyer_of[n]] = max(0.0, capacity[buyer_of[n]] - 1.0)

        for n in names:
            if n not in defaulted and cash[n] < -fc.default_tolerance * baseline[n]:
                fail(n)
        if t == cfg.shock.core_default_time:
            defaulted.add(CORE)                # the anchor places no orders
        if t == cfg.shock.seed_time:
            for n in cfg.shock.seed_firms:
                if n not in defaulted:
                    fail(n)

        trace.cash.append(dict(cash))
        trace.sales.append(dict(sales))
        trace.loans.append(dict(loans))
        trace.defaulted.append(set(defaulted))
        trace.default_share.append(len(defaulted - {CORE}) / len(names))
        trace.bank_losses.append(bank_losses)
    return trace
