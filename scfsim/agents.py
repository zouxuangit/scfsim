"""Agent state containers for firms and banks.

Agents are deliberately lightweight: all decision logic lives in the
simulation engine so that alternative behavioural rules can be swapped in
without touching the state containers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class FirmState:
    """Financial state of one firm (or the core enterprise)."""

    name: str
    tier: int
    bank: int
    baseline_sales: float = 0.0
    cash: float = 0.0
    loans: float = 0.0            # outstanding SCF loan principal (total)
    defaulted: bool = False
    default_time: int = -1
    # receivables[t] -> amount due to be collected at period t
    receivables_due: Dict[int, float] = field(default_factory=dict)
    # loan_book[t] -> principal falling due for repayment at period t
    loan_book: Dict[int, float] = field(default_factory=dict)
    # interest_book[t] -> interest falling due with that principal, fixed
    # at the rate in force when each drawing was made (risk-based pricing)
    interest_book: Dict[int, float] = field(default_factory=dict)
    # payables_due[t] -> variable costs to be paid at period t (trade
    # credit received from suppliers; empty when payables_delay is 0)
    payables_due: Dict[int, float] = field(default_factory=dict)
    supply_capacity: float = 1.0  # share of input needs currently met
    cum_financing: float = 0.0    # total credit drawn over the run

    def book_sale(self, due: int, amount: float) -> None:
        self.receivables_due[due] = self.receivables_due.get(due, 0.0) + amount

    def book_payable(self, due: int, amount: float) -> None:
        self.payables_due[due] = self.payables_due.get(due, 0.0) + amount

    def book_loan(self, due: int, amount: float, rate: float = 0.0) -> None:
        self.loan_book[due] = self.loan_book.get(due, 0.0) + amount
        self.interest_book[due] = self.interest_book.get(due, 0.0) + amount * rate
        self.loans += amount

    def receivables_outstanding(self) -> float:
        return sum(self.receivables_due.values())


@dataclass
class BankState:
    """Financial state of one bank."""

    bank_id: int
    capital: float = 0.0
    initial_capital: float = 0.0
    losses: float = 0.0
    outstanding: Dict[str, float] = field(default_factory=dict)
    failed: bool = False
    cum_credit: float = 0.0

    def loan_rate(self, base_rate: float, slope: float) -> float:
        """Rate on a new drawing under risk-based pricing.

        The premium is ``slope × (1 − credit multiplier)``: zero for an
        unimpaired bank, rising linearly as losses erode its capital.
        """
        return base_rate + slope * (1.0 - self.tightening())

    def tightening(self) -> float:
        """Credit-supply multiplier in [0, 1].

        Losses erode capital linearly; a bank with losses >= capital stops
        lending entirely (bank failure), transmitting the shock to every firm
        it serves -- the credit-crunch contagion channel.
        """
        if self.failed or self.initial_capital <= 0:
            return 0.0
        remaining = max(0.0, 1.0 - self.losses / self.initial_capital)
        return remaining

    def register_loss(self, amount: float) -> None:
        self.losses += amount
        if self.losses >= self.initial_capital:
            self.failed = True
