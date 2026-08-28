"""Result containers and summary statistics for SCFSim runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from .agents import BankState, FirmState
    from .config import SimulationConfig


@dataclass
class RunResult:
    """Time series and end-of-run summary of a single simulation."""

    config: "SimulationConfig"
    core_name: str = "core-0"
    default_share: List[float] = field(default_factory=list)
    credit_outstanding: List[float] = field(default_factory=list)
    bank_losses: List[float] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    defaulted_firms: set = field(default_factory=set)
    seeded_firms: set = field(default_factory=set)

    def record(self, t: int, firms: Dict[str, "FirmState"],
               banks: Dict[int, "BankState"]) -> None:
        active = [f for f in firms.values() if f.name != self.core_name]
        n = len(active)
        self.default_share.append(
            sum(1 for f in active if f.defaulted) / n if n else 0.0)
        self.credit_outstanding.append(
            sum(f.loans for f in active)
            + sum(b.purchased_cost_outstanding for b in banks.values()))
        self.bank_losses.append(sum(b.losses for b in banks.values()))

    def finalise(self, firms: Dict[str, "FirmState"],
                 banks: Dict[int, "BankState"],
                 seeded: "List[str] | None" = None) -> None:
        active = [f for f in firms.values() if f.name != self.core_name]
        by_tier: Dict[int, List[int]] = {}
        for f in active:
            by_tier.setdefault(f.tier, []).append(1 if f.defaulted else 0)
        seed_n = self.config.shock.seed_defaults
        total_defaults = sum(1 for f in active if f.defaulted)
        self.defaulted_firms = {f.name for f in active if f.defaulted}
        self.seeded_firms = set(seeded or [])
        self.summary = {
            "n_firms": len(active),
            "final_default_share": self.default_share[-1] if self.default_share else 0.0,
            "cascade_size": max(0, total_defaults - seed_n),
            "default_share_by_tier": {
                t: float(np.mean(v)) for t, v in sorted(by_tier.items())},
            "total_credit_extended": float(
                sum(f.cum_financing for f in active)),
            "total_bank_losses": float(sum(b.losses for b in banks.values())),
            "banks_failed": int(sum(1 for b in banks.values() if b.failed)),
        }


def batch_summary(results: List[RunResult]) -> Dict[str, float]:
    """Aggregate Monte-Carlo statistics across a batch of runs."""
    shares = np.array([r.summary["final_default_share"] for r in results])
    cascades = np.array([r.summary["cascade_size"] for r in results])
    credit = np.array([r.summary["total_credit_extended"] for r in results])
    losses = np.array([r.summary["total_bank_losses"] for r in results])
    return {
        "runs": len(results),
        "mean_default_share": float(shares.mean()),
        "p95_default_share": float(np.percentile(shares, 95)),
        "mean_cascade_size": float(cascades.mean()),
        "p95_cascade_size": float(np.percentile(cascades, 95)),
        "mean_credit_extended": float(credit.mean()),
        "mean_bank_losses": float(losses.mean()),
        "systemic_event_freq": float((shares > 0.25).mean()),
    }
