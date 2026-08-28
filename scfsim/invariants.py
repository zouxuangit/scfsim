"""Accounting identities and state invariants.

An agent-based financial model is only as trustworthy as its book-keeping.
Rather than relying on inspection alone, SCFSim states the properties its
ledgers must satisfy at every point in time and checks them mechanically.

Two kinds of property are covered:

* **Accounting identities** -- statements that must hold exactly, such as
  "a bank's recorded exposure to a firm equals that firm's outstanding
  principal" and "a firm's loan ledger sums to its loan balance". A
  violation is a book-keeping bug, not a modelling choice.
* **Domain bounds** -- statements that follow from the economics, such as
  "supply capacity lies in [0, 1]", "a defaulted firm carries no loans"
  and "cumulative write-offs cannot exceed cumulative lending net of
  recoveries".

Set ``SimulationConfig.strict = True`` to have :class:`~scfsim.Simulation`
check every identity after each period; the checks are off by default
because they cost roughly a quarter of runtime. They are always exercised by the
test suite.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .agents import BankState, FirmState
    from .config import SimulationConfig

TOL = 1e-9


class InvariantViolation(AssertionError):
    """Raised when the model's book-keeping is internally inconsistent."""


def check_invariants(firms: Dict[str, "FirmState"],
                     banks: Dict[int, "BankState"],
                     cfg: "SimulationConfig",
                     t: int = -1,
                     core_name: str = "core-0") -> None:
    """Verify every accounting identity and domain bound. Raises on failure."""
    problems: List[str] = []
    problems += _firm_identities(firms, cfg, core_name)
    problems += _bank_identities(firms, banks, cfg, core_name)
    if problems:
        head = f"invariants violated at period {t}:" if t >= 0 else \
            "invariants violated:"
        raise InvariantViolation(head + "\n  - " + "\n  - ".join(problems))


def _firm_identities(firms, cfg, core_name) -> List[str]:
    out: List[str] = []
    for name, f in firms.items():
        if name == core_name:
            continue
        # identity: the dated loan ledger must reconcile to the balance
        booked = sum(f.loan_book.values())
        if abs(booked - f.loans) > TOL:
            out.append(f"{name}: loan ledger {booked:.6g} != loan balance "
                       f"{f.loans:.6g}")
        if f.loans < -TOL:
            out.append(f"{name}: negative loan balance {f.loans:.6g}")
        if any(v < -TOL for v in f.loan_book.values()):
            out.append(f"{name}: negative principal in the loan ledger")
        # identity: interest is only ever owed on principal that is owed
        if any(v < -TOL for v in f.interest_book.values()):
            out.append(f"{name}: negative interest in the interest ledger")
        orphaned = {d for d, v in f.interest_book.items()
                    if v > TOL and d not in f.loan_book}
        if orphaned:
            out.append(f"{name}: interest booked for periods {sorted(orphaned)} "
                       "with no principal falling due")
        ceiling = cfg.bank.interest_rate + cfg.bank.pricing_slope
        for due, principal in f.loan_book.items():
            if f.interest_book.get(due, 0.0) > principal * ceiling * (1 + 1e-9) + TOL:
                out.append(f"{name}: interest due at {due} exceeds principal "
                           f"x the maximum rate {ceiling:g}")
        if any(v < -TOL for v in f.receivables_due.values()):
            out.append(f"{name}: negative receivable booked")
        if any(v < -TOL for v in f.payables_due.values()):
            out.append(f"{name}: negative payable booked")
        if cfg.firm.payables_delay == 0 and f.payables_due:
            out.append(f"{name}: payables booked although costs are paid "
                       "immediately")
        if (cfg.bank.instrument == "receivables_purchase"
                and (f.loans > TOL or f.loan_book or f.interest_book)):
            out.append(f"{name}: carries loans under a receivables-purchase "
                       "instrument")
        # a drawing can never exceed the total ever drawn
        if f.loans > f.cum_financing + TOL:
            out.append(f"{name}: outstanding {f.loans:.6g} exceeds cumulative "
                       f"drawings {f.cum_financing:.6g}")
        if not (-TOL <= f.supply_capacity <= 1 + TOL):
            out.append(f"{name}: supply capacity {f.supply_capacity:.6g} "
                       "outside [0, 1]")
        # a defaulted firm is out of the credit system entirely
        if f.defaulted:
            if f.loans > TOL or f.loan_book or f.interest_book:
                out.append(f"{name}: defaulted but still carries loans")
            if f.payables_due:
                out.append(f"{name}: defaulted but still owes suppliers")
            if f.supply_capacity > TOL:
                out.append(f"{name}: defaulted but still able to supply")
            if f.default_time < 0:
                out.append(f"{name}: defaulted without a default time")
    return out


def _bank_identities(firms, banks, cfg, core_name) -> List[str]:
    out: List[str] = []
    for b in banks.values():
        # identity: recorded exposure must equal the borrower's balance
        for firm_name, exposure in b.outstanding.items():
            f = firms[firm_name]
            if abs(exposure - f.loans) > TOL:
                out.append(f"bank {b.bank_id}: exposure to {firm_name} "
                           f"{exposure:.6g} != borrower balance {f.loans:.6g}")
            if f.bank != b.bank_id:
                out.append(f"bank {b.bank_id}: exposure to {firm_name}, "
                           f"which banks with {f.bank}")
        # every live borrowing must be recorded by exactly one bank
        for name, f in firms.items():
            if name == core_name or f.bank != b.bank_id:
                continue
            if f.loans > TOL and name not in b.outstanding:
                out.append(f"bank {b.bank_id}: unrecorded exposure to {name}")
        if b.losses < -TOL:
            out.append(f"bank {b.bank_id}: negative cumulative losses")
        # write-offs are bounded by what was lent, net of recoveries; under
        # a receivables purchase the bank can lose at most what it paid
        if cfg.bank.instrument == "receivables_purchase":
            ceiling = b.cum_credit + TOL
            if b.losses > ceiling:
                out.append(f"bank {b.bank_id}: losses {b.losses:.6g} exceed "
                           f"total purchase consideration {ceiling:.6g}")
            if b.outstanding:
                out.append(f"bank {b.bank_id}: records loan exposure under a "
                           "receivables-purchase instrument")
            if b.purchased_cost_outstanding < -TOL:
                out.append(f"bank {b.bank_id}: negative purchased cost "
                           "outstanding")
            for seller, tranches in b.purchased.items():
                if any(v < -TOL for v in tranches.values()):
                    out.append(f"bank {b.bank_id}: negative purchased face "
                               f"from {seller}")
        else:
            ceiling = b.cum_credit * (1 - cfg.bank.loan_recovery) + TOL
            if b.losses > ceiling:
                out.append(f"bank {b.bank_id}: write-offs {b.losses:.6g} exceed "
                           f"lending net of recovery {ceiling:.6g}")
            if b.purchased or b.purchased_cost_outstanding > TOL:
                out.append(f"bank {b.bank_id}: holds purchased receivables "
                           "under a loan instrument")
        tight = b.tightening()
        if not (-TOL <= tight <= 1 + TOL):
            out.append(f"bank {b.bank_id}: credit multiplier {tight:.6g} "
                       "outside [0, 1]")
        if b.failed and tight > TOL:
            out.append(f"bank {b.bank_id}: failed but still lending")
    # every drawing is funded by exactly one bank
    drawn = sum(f.cum_financing for n, f in firms.items() if n != core_name)
    supplied = sum(b.cum_credit for b in banks.values())
    if abs(drawn - supplied) > 1e-6:
        out.append(f"aggregate: firms drew {drawn:.6g} but banks supplied "
                   f"{supplied:.6g}")
    return out


def network_invariants(g) -> List[str]:
    """Structural properties a valid SCF network must satisfy."""
    out: List[str] = []
    for node, data in g.nodes(data=True):
        if data.get("kind") == "bank" or g.in_degree(node) == 0:
            continue
        total = sum(d["share"] for _, _, d in g.in_edges(node, data=True))
        if abs(total - 1.0) > 1e-9:
            out.append(f"{node}: input shares sum to {total:.6g}, not 1")
    return out
