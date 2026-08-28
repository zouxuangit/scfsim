"""Economic invariants: properties the model must satisfy to be *right*,
not merely self-consistent.

The accounting identities in :mod:`scfsim.invariants` verify that the
ledgers reconcile. They cannot detect a specification that books
everything correctly but means the wrong thing — and both specification
errors found in SCFSim's history were of exactly that kind:

* v0.1 let a firm deliver at full volume after every one of its suppliers
  had failed, because its own supply capacity did not constrain its own
  sales. Every ledger balanced; the economics was wrong.
* v0.1–v0.2 sized bank capital against total chain sales rather than
  against the SCF credit book the bank could actually hold, overstating
  capital by roughly an order of magnitude. Again, the books balanced.

This module states the economic content that those errors violated, so
that a regression of either kind fails loudly. Two families:

* **Structural properties** (:func:`check_economics`) — statements that
  must hold at every point in time, e.g. a firm with no supply capacity
  makes no sales, a bank's capital is commensurate with the book it could
  hold, a borrower never owes more than its collateral supports.
* **Comparative statics** (:func:`comparative_statics`) — signed
  predictions about how outcomes must move when a parameter moves, e.g.
  more cash cannot raise defaults, a larger haircut cannot lower them.
  These are checked across matched Monte-Carlo seeds in the test suite.

Structural properties run alongside the accounting identities whenever
``SimulationConfig.strict`` is set.
"""
from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .agents import BankState, FirmState
    from .config import SimulationConfig

TOL = 1e-7


class EconomicViolation(AssertionError):
    """Raised when the model's behaviour contradicts its own economics."""


def check_economics(firms: Dict[str, "FirmState"],
                    banks: Dict[int, "BankState"],
                    cfg: "SimulationConfig",
                    orders: Dict[str, float] | None = None,
                    books: Dict[str, float] | None = None,
                    t: int = -1,
                    core_name: str = "core-0") -> None:
    """Verify the structural economic properties. Raises on failure.

    ``orders`` are realised sales for the period and ``books`` the order
    book before the delivery constraint is applied; supplying both lets the
    delivery property be checked exactly rather than only in the limit.
    """
    problems: List[str] = []
    problems += _delivery_properties(firms, cfg, orders, books, core_name)
    problems += _credit_properties(firms, banks, cfg, core_name)
    if problems:
        head = (f"economic properties violated at period {t}:" if t >= 0
                else "economic properties violated:")
        raise EconomicViolation(head + "\n  - " + "\n  - ".join(problems))


def _delivery_properties(firms, cfg, orders, books, core_name) -> List[str]:
    """A firm cannot sell what it cannot make.

    This is the property v0.1 violated: supply capacity is the share of a
    firm's input needs that is still being met, so realised sales must be
    bounded by it. If capacity is zero, sales must be zero.
    """
    out: List[str] = []
    if orders is None:
        return out
    for name, f in firms.items():
        if name == core_name:
            continue
        sales = orders.get(name, 0.0)
        if sales < -TOL:
            out.append(f"{name}: negative sales {sales:.6g}")
        if f.defaulted and sales > TOL:
            out.append(f"{name}: defaulted but still selling {sales:.6g}")
        if not cfg.channels.supply:
            continue          # the delivery constraint is deliberately off
        if f.supply_capacity <= TOL and sales > TOL:
            out.append(
                f"{name}: sells {sales:.6g} with no supply capacity - a firm "
                "that has lost every supplier cannot deliver")
        # deliveries are bounded by the order book scaled by capacity: a
        # firm short of inputs must ship less, not merely order less
        if books is not None:
            ceiling = books.get(name, 0.0) * f.supply_capacity + 1e-6
            if sales > ceiling:
                out.append(
                    f"{name}: delivers {sales:.6g} against an order book of "
                    f"{books.get(name, 0.0):.6g} at capacity "
                    f"{f.supply_capacity:.4g} (ceiling {ceiling:.6g}) - lost "
                    "input supply must reduce deliveries, not just orders")
    return out


def _credit_properties(firms, banks, cfg, core_name) -> List[str]:
    """Credit must be commensurate with collateral, and capital with the book.

    The second property is the one v0.1-v0.2 violated: a bank's capital was
    scaled to total chain sales rather than to the SCF exposure it could
    ever hold, which silently neutralised the credit-crunch channel.
    """
    out: List[str] = []
    bc = cfg.bank

    # a bank's capital must be scaled to its own potential credit book
    client_book = {b: 0.0 for b in banks}
    for name, f in firms.items():
        if name == core_name:
            continue
        if f.bank in client_book:
            client_book[f.bank] += (bc.advance_rate * f.baseline_sales
                                    * max(1, cfg.firm.payment_delay))
    for b_id, bank in banks.items():
        ceiling = bc.capital_ratio * client_book[b_id] * (1 + 1e-6) + TOL
        if bank.initial_capital > ceiling:
            out.append(
                f"bank {b_id}: capital {bank.initial_capital:.6g} exceeds "
                f"{bc.capital_ratio:g} x its potential SCF book "
                f"{client_book[b_id]:.6g} - capital must be scaled to the "
                "credit book, not to chain turnover")
    return out


def check_drawing(firm: "FirmState", eligible: float, tightening: float,
                  cfg: "SimulationConfig",
                  proceeds: "float | None" = None) -> None:
    """A new drawing must be supported by collateral at the time it is made.

    This is a property of the *flow*, not of the stock: once drawn, a loan
    stays on the books while the receivables that secured it are collected,
    so a firm carrying a longer facility can legitimately owe more than the
    advance rate applied to its receivables *today*. Checking the stock
    instead of the flow is a mistake this project made and caught here.

    Under ``instrument == "receivables_purchase"`` there are no loans;
    ``proceeds`` is the cash paid for the sold face, and it must not
    exceed the advance rate applied to the eligible value the seller held
    *before* the sale, scaled by the bank's willingness to buy.
    """
    if proceeds is not None:
        ceiling = cfg.bank.advance_rate * eligible * tightening + 1e-6
        if proceeds > ceiling:
            raise EconomicViolation(
                f"{firm.name}: sale proceeds {proceeds:.6g} exceed the "
                f"advance-rate ceiling {ceiling:.6g} on eligible collateral")
        if firm.loans > 1e-9:
            raise EconomicViolation(
                f"{firm.name}: carries loans {firm.loans:.6g} under a "
                "receivables-purchase instrument")
        return
    ceiling = cfg.bank.advance_rate * eligible * tightening + 1e-6
    if firm.loans > ceiling:
        raise EconomicViolation(
            f"{firm.name}: owes {firm.loans:.6g} immediately after drawing, "
            f"above the advance-rate ceiling {ceiling:.6g} on eligible "
            "collateral")


# --------------------------------------------------------------------- #
# comparative statics
# --------------------------------------------------------------------- #

#: Signed predictions the model must satisfy. Each entry maps a dotted
#: configuration path to the direction in which the mean default share must
#: move as that parameter increases: ``+1`` means defaults must weakly rise,
#: ``-1`` that they must weakly fall.
COMPARATIVE_STATICS = {
    "firm.initial_cash_ratio": -1,      # deeper cash buffers help
    "firm.receivable_recovery": -1,     # recovering more from failed buyers helps
    "firm.fixed_cost_ratio": +1,        # operating leverage hurts
    "firm.payables_delay": -1,          # paying suppliers on terms helps
    "bank.advance_rate": -1,            # more credit against collateral helps
    "bank.capital_ratio": -1,           # better capitalised banks lend through
    "bank.pricing_slope": +1,           # dearer credit under stress hurts
    "scenario.haircut": +1,             # harsher valuation of collateral hurts
    "scenario.fraud_prob": +1,          # unverifiable invoices hurt
    "scenario.visibility_depth": -1,    # financing that reaches deeper helps
    "shock.demand_sigma": +1,           # volatility hurts
    "shock.liquidity_shock_prob": +1,   # more shocks hurt
}


def comparative_statics() -> Dict[str, int]:
    """Return the signed predictions, keyed by configuration path."""
    return dict(COMPARATIVE_STATICS)
