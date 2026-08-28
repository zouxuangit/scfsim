"""The SCFSim discrete-time simulation engine.

Each period unfolds in five phases:

1. **Settlement.** Receivables booked ``payment_delay`` periods ago are
   collected. Buyers that defaulted in the meantime pay only the recovery
   rate -- the *counterparty-loss* contagion channel. Maturing SCF loans are
   repaid with interest.
2. **Orders.** The core enterprise draws stochastic demand and orders from
   tier 1; orders cascade upstream, scaled by each firm's input share and by
   its current ``supply_capacity`` (defaulted suppliers reduce it -- the
   *supply-disruption* channel).
3. **Production & liquidity.** Firms pay variable and fixed costs. A firm
   short of cash requests receivables financing from its house bank.
4. **Financing.** The bank advances up to ``advance_rate`` times the firm's
   *eligible* receivables, where eligibility depends on the scenario's
   visibility depth, haircut and fraud rate (the blockchain switch), and on
   the bank's own credit tightening -- the *credit-crunch* channel.
5. **Default resolution.** Firms still short of cash default: their unpaid
   payables become counterparty losses upstream, their bank writes down the
   loans, and their buyers lose supply capacity.
"""
from __future__ import annotations

from typing import Dict, Optional

import networkx as nx
import numpy as np

from .agents import BankState, FirmState
from .config import SimulationConfig
from .economics import check_drawing, check_economics
from .invariants import check_invariants
from .metrics import RunResult
from .network import CORE, core_node, generate_network, validate_network


class Simulation:
    """One SCF network + one scenario + one shock path."""

    def __init__(self, config: SimulationConfig,
                 network: Optional[nx.DiGraph] = None):
        self.cfg = config
        self.rng = np.random.default_rng(config.seed)
        if network is None:
            self.g = generate_network(config.network, self.rng)
        else:
            validate_network(network)
            self.g = network.copy()
        #: Name of the core enterprise. ``core-0`` in generated networks;
        #: whatever the ``kind == "core"`` node is called in a user's.
        self.core = core_node(self.g)
        self.firms: Dict[str, FirmState] = {}
        self.banks: Dict[int, BankState] = {}
        self.seeded: list = []   # names of the exogenously seeded defaults
        self._t = 0              # current period, used when booking loans
        self._books: Dict[str, float] = {}   # order book before delivery cap
        self._init_states()
        self.result = RunResult(config=config, core_name=self.core)

    # ------------------------------------------------------------------ #
    # initialisation
    # ------------------------------------------------------------------ #
    def _init_states(self) -> None:
        fc = self.cfg.firm
        core_demand = fc.core_demand

        # propagate baseline sales down the tiers using input shares
        baseline: Dict[str, float] = {self.core: core_demand}
        nodes_by_tier = self._nodes_by_tier()
        for t in range(1, len(nodes_by_tier)):
            for name in nodes_by_tier[t]:
                sales = 0.0
                for _, buyer, data in self.g.out_edges(name, data=True):
                    buyer_sales = baseline.get(buyer, 0.0)
                    demand_pool = (core_demand if buyer == self.core
                                   else fc.input_share * buyer_sales)
                    sales += data["share"] * demand_pool
                baseline[name] = sales

        for name, data in self.g.nodes(data=True):
            if data["kind"] == "bank":
                continue
            base = baseline.get(name, 0.0)
            firm = FirmState(
                name=name, tier=data["tier"], bank=data["bank"],
                baseline_sales=base,
                cash=(fc.initial_cash_ratio * base if name != self.core
                      else 1e7 * fc.core_demand),
            )
            # warm start: the trade-credit pipeline is already running, so
            # each firm holds one settlement cycle of in-transit receivables
            if name != self.core:
                for lag in range(fc.payment_delay):
                    firm.book_sale(lag, base)
            self.firms[name] = firm

        # Bank capital is sized against the credit book the bank could
        # plausibly hold -- the advance rate applied to its clients'
        # receivables outstanding at any moment -- rather than against total
        # chain sales, so that ``capital_ratio`` is an interpretable capital
        # ratio against SCF exposure.
        # Every bank id named by a firm gets a bank, plus the configured
        # range (so that generated networks keep client-less banks, whose
        # capital is zero and whose behaviour is unaffected).
        bank_ids = set(range(self.cfg.network.n_banks))
        bank_ids |= {f.bank for f in self.firms.values()}
        book = {b: 0.0 for b in bank_ids}
        for f in self.firms.values():
            if f.name == self.core:
                continue
            book[f.bank] += (self.cfg.bank.advance_rate * f.baseline_sales
                             * max(1, fc.payment_delay))
        for b in sorted(bank_ids):
            cap = self.cfg.bank.capital_ratio * book[b]
            self.banks[b] = BankState(bank_id=b, capital=cap,
                                      initial_capital=cap)

    def _nodes_by_tier(self):
        max_tier = max(d["tier"] for _, d in self.g.nodes(data=True))
        tiers = [[] for _ in range(max_tier + 1)]
        for name, data in self.g.nodes(data=True):
            if data["kind"] != "bank":
                tiers[data["tier"]].append(name)
        return tiers

    # ------------------------------------------------------------------ #
    # main loop
    # ------------------------------------------------------------------ #
    def run(self) -> RunResult:
        for t in range(self.cfg.n_periods):
            self._step(t)
        self.result.finalise(self.firms, self.banks, self.seeded)
        return self.result

    def _layer(self, name: str) -> bool:
        """True when ``strict`` is on and this verification layer is enabled."""
        return self.cfg.strict and name in self.cfg.strict_layers

    def _step(self, t: int) -> None:
        self._t = t
        self._settle(t)
        orders = self._place_orders(t)
        if self._layer("economics"):
            check_economics(self.firms, self.banks, self.cfg, orders,
                            self._books, t, self.core)
        self._produce_and_finance(t, orders)
        self._seed_defaults(t)
        self.result.record(t, self.firms, self.banks)
        if self._layer("books"):
            check_invariants(self.firms, self.banks, self.cfg, t, self.core)
        if self._layer("economics"):
            check_economics(self.firms, self.banks, self.cfg, None, None,
                            t, self.core)

    # ---------------------- phase 1: settlement ----------------------- #
    def _settle(self, t: int) -> None:
        fc, bc = self.cfg.firm, self.cfg.bank
        for firm in self.firms.values():
            if firm.name == self.core:
                continue  # the core always pays; its cash is not tracked
            # collect receivables that mature now; buyers that defaulted in
            # the meantime pay only the recovery rate (counterparty channel)
            due = firm.receivables_due.pop(t, 0.0)
            if due > 0 and not firm.defaulted:
                firm.cash += due * self._collection_rate(firm, t)
            # pay the suppliers' invoices that fall due (trade credit taken)
            payable = firm.payables_due.pop(t, 0.0)
            if payable > 0 and not firm.defaulted:
                firm.cash -= payable
            # repay the loan tranche falling due this period, with the
            # interest fixed when it was drawn
            principal = firm.loan_book.pop(t, 0.0)
            interest = firm.interest_book.pop(t, 0.0)
            if principal > 0 and not firm.defaulted:
                if bc.pricing_slope == 0:
                    firm.cash -= principal * (1 + bc.interest_rate)
                else:
                    firm.cash -= principal + interest
                firm.loans = max(0.0, firm.loans - principal)
                bank = self.banks[firm.bank]
                remaining = bank.outstanding.get(firm.name, 0.0) - principal
                if remaining > 1e-12:
                    bank.outstanding[firm.name] = remaining
                else:
                    bank.outstanding.pop(firm.name, None)

    def _collection_rate(self, firm: FirmState, t: int) -> float:
        """Weighted recovery over the firm's buyers as of period t."""
        if not self.cfg.channels.counterparty:
            return 1.0
        fc = self.cfg.firm
        rates, weights = [], []
        for _, buyer, data in self.g.out_edges(firm.name, data=True):
            b = self.firms[buyer]
            rates.append(fc.receivable_recovery if b.defaulted else 1.0)
            weights.append(max(data["share"], 1e-9))
        if not rates:
            return 1.0
        w = np.asarray(weights)
        return float(np.average(rates, weights=w / w.sum()))

    # ----------------------- phase 2: orders -------------------------- #
    def _place_orders(self, t: int) -> Dict[str, float]:
        """Propagate demand upstream and delivery capacity downstream.

        A firm's realised sales are its order book scaled by its own
        remaining supply capacity, so a failed supplier reduces what its
        buyers can deliver (downstream) and a distressed buyer reduces what
        it orders from its own suppliers (upstream). The two directions are
        separately switchable via :class:`ChannelConfig`; ``nominal`` tracks
        the counterfactual order book of an undisturbed chain, which is what
        suppliers see when the demand channel is off.
        """
        fc, sc, ch = self.cfg.firm, self.cfg.shock, self.cfg.channels
        shock = float(np.exp(self.rng.normal(0.0, sc.demand_sigma)))
        core_demand = fc.core_demand * shock
        if self.firms[self.core].defaulted:
            core_demand = 0.0      # a defaulted anchor places no orders
        orders: Dict[str, float] = {}
        books: Dict[str, float] = {}
        actual: Dict[str, float] = {self.core: core_demand}
        nominal: Dict[str, float] = {self.core: core_demand}
        nodes_by_tier = self._nodes_by_tier()

        for tier in range(1, len(nodes_by_tier)):
            for name in nodes_by_tier[tier]:
                firm = self.firms[name]
                s_actual = s_nominal = 0.0
                for _, buyer, data in self.g.out_edges(name, data=True):
                    if buyer == self.core:
                        pool_a, pool_n = actual[self.core], nominal[self.core]
                    else:
                        pool_a = fc.input_share * actual.get(buyer, 0.0)
                        pool_n = fc.input_share * nominal.get(buyer, 0.0)
                    s_actual += data["share"] * pool_a
                    s_nominal += data["share"] * pool_n
                book = s_actual if ch.demand else s_nominal
                cap = firm.supply_capacity if ch.supply else 1.0
                sales = 0.0 if firm.defaulted else book * cap
                books[name] = book
                orders[name] = sales
                actual[name] = sales
                nominal[name] = s_nominal
        self._books = books
        return orders

    # ----------------- phases 3-5: production, credit ------------------ #
    def _produce_and_finance(self, t: int, orders: Dict[str, float]) -> None:
        fc, bc, sc = self.cfg.firm, self.cfg.bank, self.cfg.scenario
        shk = self.cfg.shock
        delay = fc.payment_delay
        newly_defaulted = []

        for firm in self.firms.values():
            if firm.name == self.core or firm.defaulted:
                continue
            sales = orders.get(firm.name, 0.0)
            variable = fc.cost_ratio * sales
            cost = variable + fc.fixed_cost_ratio * firm.baseline_sales
            # idiosyncratic liquidity shock
            if self.rng.random() < shk.liquidity_shock_prob:
                cost += shk.liquidity_shock_size * firm.baseline_sales
            if fc.payables_delay == 0:
                firm.cash -= cost
            else:
                # variable costs are owed to suppliers on terms; fixed
                # costs and shocks are paid now
                firm.cash -= cost - variable
                if variable > 0:
                    firm.book_payable(t + fc.payables_delay, variable)
            if sales > 0:
                firm.book_sale(t + delay, sales)
            if firm.cash < 0:
                self._request_financing(firm)
            threshold = -fc.default_tolerance * max(firm.baseline_sales, 1e-12)
            if firm.cash < threshold:
                newly_defaulted.append(firm)

        for firm in newly_defaulted:
            self._resolve_default(firm, t)

    def _request_financing(self, firm: FirmState) -> None:
        bc, sc = self.cfg.bank, self.cfg.scenario
        bank = self.banks[firm.bank]
        eligible = self._eligible_receivables(firm)
        tight = bank.tightening() if self.cfg.channels.credit_crunch else 1.0
        headroom = bc.advance_rate * eligible * tight - firm.loans
        request = min(-firm.cash, max(0.0, headroom))
        if request <= 0:
            return
        firm.cash += request
        rate = (bank.loan_rate(bc.interest_rate, bc.pricing_slope)
                if self.cfg.channels.credit_crunch else bc.interest_rate)
        firm.book_loan(self._t + bc.loan_maturity, request, rate)
        firm.cum_financing += request
        bank.outstanding[firm.name] = bank.outstanding.get(firm.name, 0.0) + request
        bank.cum_credit += request
        if self._layer("economics"):
            check_drawing(firm, eligible, tight, self.cfg)

    def _eligible_receivables(self, firm: FirmState) -> float:
        """Receivables a bank will accept as SCF collateral.

        Visibility: receivables of firms within ``effective_visibility``
        tiers of the core are fully verifiable (confirmed payables that a
        blockchain platform can tokenise and transfer upstream); deeper
        receivables are financeable only at ``deep_tier_access``. A haircut
        and an expected-fraud discount are then applied.
        """
        sc = self.cfg.scenario
        total = firm.receivables_outstanding()
        if firm.tier <= sc.effective_visibility:
            accessible = total
        else:
            accessible = sc.deep_tier_access * total
        value = accessible * (1 - sc.effective_haircut) * (1 - sc.effective_fraud)
        return value

    def _resolve_default(self, firm: FirmState, t: int) -> None:
        fc, bc = self.cfg.firm, self.cfg.bank
        firm.defaulted = True
        firm.default_time = t
        firm.supply_capacity = 0.0
        # bank writes down the outstanding loan
        bank = self.banks[firm.bank]
        exposure = bank.outstanding.pop(firm.name, 0.0)
        bank.register_loss(exposure * (1 - bc.loan_recovery))
        firm.loans = 0.0
        firm.loan_book.clear()
        firm.interest_book.clear()
        firm.payables_due.clear()      # unpaid invoices die with the firm
        # buyers of this firm lose part of their input supply
        if self.cfg.channels.supply:
            for _, buyer, data in self.g.out_edges(firm.name, data=True):
                b = self.firms[buyer]
                b.supply_capacity = max(0.0, b.supply_capacity - data["share"])

    def _seed_defaults(self, t: int) -> None:
        shk = self.cfg.shock
        if shk.core_default_time is not None and t == shk.core_default_time:
            core = self.firms[self.core]
            if not core.defaulted:
                self._resolve_default(core, t)
        if t != shk.seed_time:
            return
        if not shk.seed_firms and shk.seed_defaults <= 0:
            return
        if shk.seed_firms:
            for name in shk.seed_firms:
                firm = self.firms.get(name)
                if firm is None:
                    raise ValueError(f"seed_firms names {name!r}, which is "
                                     "not a firm in this network")
                if not firm.defaulted:
                    self.seeded.append(name)
                    self._resolve_default(firm, t)
            return
        candidates = [f for f in self.firms.values()
                      if f.tier == shk.seed_tier and not f.defaulted]
        if not candidates:
            return
        k = min(shk.seed_defaults, len(candidates))
        idx = self.rng.choice(len(candidates), size=k, replace=False)
        for i in idx:
            self.seeded.append(candidates[i].name)
            self._resolve_default(candidates[i], t)


def _run_seeded(args) -> RunResult:
    """One Monte-Carlo path; module-level so that it can be pickled."""
    config, seed, network = args
    import copy
    cfg = copy.deepcopy(config)
    cfg.seed = seed
    cfg.network.seed = seed
    return Simulation(cfg, network=network).run()


def run_batch(config: SimulationConfig, n_runs: int = 100,
              base_seed: int = 0, n_jobs: int = 1,
              network: Optional[nx.DiGraph] = None) -> "list[RunResult]":
    """Monte-Carlo batch: same config, ``n_runs`` independent seeds.

    With ``network=None`` every path draws its own topology from
    ``config.network`` with the path's seed; with a user-supplied graph
    every path runs on that fixed topology and only the shocks vary,
    which is the setting for a mapped supply network. Configs are cloned
    with :func:`copy.deepcopy` (JSON serialisation is kept for archival,
    not for cloning, so non-serialisable future fields cannot silently
    corrupt a batch). Paths are independent, so ``n_jobs > 1`` runs them
    in a process pool; the result is identical to the serial run, in the
    same order, because every path carries its own seed. ``n_jobs=0``
    uses every available core. Callers on Windows and macOS must be
    guarded by ``if __name__ == "__main__":`` when ``n_jobs != 1``, as
    with any use of :mod:`multiprocessing`.
    """
    jobs = [(config, base_seed + i, network) for i in range(n_runs)]
    if n_jobs == 1 or n_runs <= 1:
        return [_run_seeded(j) for j in jobs]
    import multiprocessing
    workers = n_jobs if n_jobs > 0 else (multiprocessing.cpu_count() or 1)
    with multiprocessing.Pool(min(workers, n_runs)) as pool:
        return pool.map(_run_seeded, jobs)
