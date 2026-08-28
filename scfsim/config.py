"""Configuration dataclasses for SCFSim.

All model parameters are grouped into small, serialisable dataclasses so that
scenarios can be defined declaratively, swept in batch experiments, and stored
alongside results for reproducibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class NetworkConfig:
    """Topology of the supply chain finance network.

    The network is a layered directed graph: one core enterprise (tier 0),
    ``n_tiers`` upstream supplier tiers, and ``n_banks`` financial
    institutions. Edges point from supplier to buyer and carry trade shares.
    """

    n_tiers: int = 3                  # number of supplier tiers (excl. core)
    firms_per_tier: tuple = (8, 16, 32)  # length must equal n_tiers
    n_banks: int = 3
    avg_buyers_per_firm: float = 1.6  # mean out-degree for tier >= 2 firms
    seed: Optional[int] = None

    def __post_init__(self):
        if len(self.firms_per_tier) != self.n_tiers:
            raise ValueError(
                f"firms_per_tier has {len(self.firms_per_tier)} entries "
                f"but n_tiers={self.n_tiers}"
            )


@dataclass
class FirmConfig:
    """Balance-sheet and production parameters shared by firm agents."""

    cost_ratio: float = 0.72          # variable production cost / sales
    input_share: float = 0.55         # value of upstream inputs / sales
    fixed_cost_ratio: float = 0.06    # per-period fixed cost / baseline sales
    initial_cash_ratio: float = 0.35  # starting cash / baseline sales
    payment_delay: int = 1            # trade-credit settlement lag (periods)
    #: Periods after which a firm pays its variable costs. At the default
    #: of 0 payables are settled immediately while receivables arrive
    #: ``payment_delay`` later, which is the widest working-capital gap a
    #: chain can have and the assumption ranked second among the model's
    #: limitations. ``payables_delay = payment_delay`` gives symmetric
    #: trade-credit terms. Fixed costs and liquidity shocks are always paid
    #: immediately.
    payables_delay: int = 0
    receivable_recovery: float = 0.35 # recovery rate on a defaulted buyer
    core_demand: float = 100.0        # baseline order volume of the core
    #: Default is triggered when cash falls below
    #: ``-default_tolerance * baseline_sales``. Expressing the threshold
    #: relative to the firm's own scale keeps the model dimensionally
    #: homogeneous: multiplying every monetary quantity by a constant must
    #: leave outcomes unchanged (see :mod:`scfsim.metamorphic`).
    default_tolerance: float = 1e-9

    def __post_init__(self):
        if self.core_demand <= 0:
            raise ValueError("core_demand must be positive")
        if self.payables_delay < 0:
            raise ValueError("payables_delay must be non-negative")


@dataclass
class BankConfig:
    """Financial-institution parameters."""

    advance_rate: float = 0.80        # max loan / eligible receivables
    interest_rate: float = 0.02       # per-period rate on SCF loans
    capital_ratio: float = 0.12       # bank capital / initial credit supply
    loan_recovery: float = 0.40       # recovery on loans to defaulted firms
    loan_maturity: int = 1            # periods before a drawing is repaid
    #: Risk-based pricing. The rate charged on a new drawing is
    #: ``interest_rate + pricing_slope × (1 − credit multiplier)``, i.e. it
    #: rises with the lending bank's capital erosion and is locked in for
    #: the life of the drawing. At the default of 0 every loan is priced
    #: at the flat ``interest_rate``, which is the exogenous-pricing
    #: assumption ranked first among the model's limitations; a positive
    #: slope makes credit dearer precisely when the chain is in distress.
    #: Part of the credit-crunch channel: switched off with it.
    pricing_slope: float = 0.0

    def __post_init__(self):
        if self.loan_maturity < 1:
            raise ValueError("loan_maturity must be at least 1 period")
        if self.pricing_slope < 0:
            raise ValueError("pricing_slope must be non-negative")


@dataclass
class ScenarioConfig:
    """Information / technology scenario, incl. the blockchain switch.

    ``blockchain`` toggles a blockchain-enabled SCF platform in the spirit of
    Du et al. (2020): confirmed payables of the core enterprise become
    transferable and verifiable deep into the chain, which (i) extends the
    financing visibility depth, (ii) lowers the verification haircut, and
    (iii) suppresses fraudulent (unverifiable) receivables, echoing the
    secure-transaction protocol analysed by Li et al. (2024).
    """

    blockchain: bool = False
    visibility_depth: int = 1         # deepest tier with financeable receivables
    bc_visibility_depth: int = 99     # visibility depth when blockchain=True
    haircut: float = 0.25             # verification haircut without blockchain
    bc_haircut: float = 0.05          # haircut with blockchain
    fraud_prob: float = 0.06          # prob. a receivable is unenforceable
    bc_fraud_prob: float = 0.005      # ... with blockchain verification
    deep_tier_access: float = 0.15    # financeable share beyond visibility

    @property
    def effective_visibility(self) -> int:
        return self.bc_visibility_depth if self.blockchain else self.visibility_depth

    @property
    def effective_haircut(self) -> float:
        return self.bc_haircut if self.blockchain else self.haircut

    @property
    def effective_fraud(self) -> float:
        return self.bc_fraud_prob if self.blockchain else self.fraud_prob


@dataclass
class ChannelConfig:
    """Switches for the four contagion channels.

    Disabling channels is what makes the model *verifiable*. A default
    spreads downstream when a failed supplier destroys its buyers' ability
    to deliver (``supply``) and upstream when a distressed buyer cuts its
    order book (``demand``). Isolating either one therefore confines the
    cascade to an analytically known graph object -- the descendants or the
    ancestors of the seed set -- which :mod:`scfsim.benchmark` computes
    without running the model, in the spirit of the reachability bounds
    used in the interbank contagion literature. The remaining two channels
    act through balance sheets rather than through the trade graph.
    """

    counterparty: bool = True     # losses on receivables from defaulted buyers
    supply: bool = True           # own supply capacity limits own deliveries
    demand: bool = True           # a distressed buyer cuts orders to suppliers
    credit_crunch: bool = True    # bank capital erosion tightens credit supply


@dataclass
class ShockConfig:
    """Exogenous shock process."""

    demand_sigma: float = 0.10        # lognormal volatility of core demand
    liquidity_shock_prob: float = 0.03  # per-firm chance of idiosyncratic drain
    liquidity_shock_size: float = 0.5   # drain as share of baseline sales
    seed_defaults: int = 1            # firms forced into default at t=seed_time
    seed_tier: int = 2                # tier from which seed defaults are drawn
    seed_time: int = 2                # period of the seed default
    #: Names of the firms to default at ``seed_time``. When non-empty this
    #: overrides the random draw, which makes a shock reproducible across
    #: relabelled or restructured networks.
    seed_firms: tuple = ()
    #: Period at which the core enterprise itself defaults, or ``None``
    #: for the default-free anchor of earlier versions. From that period
    #: the core places no orders, and its maturing payables are settled at
    #: ``receivable_recovery`` like those of any defaulted buyer. The core
    #: draws no credit, so no bank takes a direct loss; the loss arrives
    #: through its suppliers, which is the anchor-default scenario of the
    #: supply chain finance literature.
    core_default_time: Optional[int] = None


@dataclass
class SimulationConfig:
    """Top-level simulation settings."""

    n_periods: int = 30
    network: NetworkConfig = field(default_factory=NetworkConfig)
    firm: FirmConfig = field(default_factory=FirmConfig)
    bank: BankConfig = field(default_factory=BankConfig)
    scenario: ScenarioConfig = field(default_factory=ScenarioConfig)
    shock: ShockConfig = field(default_factory=ShockConfig)
    channels: ChannelConfig = field(default_factory=ChannelConfig)
    seed: Optional[int] = None
    strict: bool = False   # run the verification layers after every period
    #: Which verification layers ``strict`` enables. ``"books"`` runs the
    #: accounting identities, ``"economics"`` the economic properties.
    strict_layers: tuple = ("books", "economics")

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)

    @staticmethod
    def from_json(payload: str) -> "SimulationConfig":
        raw = json.loads(payload)
        return SimulationConfig(
            n_periods=raw.get("n_periods", 30),
            network=NetworkConfig(**{**raw.get("network", {}),
                                     "firms_per_tier": tuple(
                                         raw.get("network", {}).get(
                                             "firms_per_tier", (8, 16, 32)))}),
            firm=FirmConfig(**raw.get("firm", {})),
            bank=BankConfig(**raw.get("bank", {})),
            scenario=ScenarioConfig(**raw.get("scenario", {})),
            shock=ShockConfig(**{**raw.get("shock", {}),
                                 "seed_firms": tuple(
                                     raw.get("shock", {}).get("seed_firms", ()))}),
            channels=ChannelConfig(**raw.get("channels", {})),
            seed=raw.get("seed"),
            strict=raw.get("strict", False),
            strict_layers=tuple(raw.get("strict_layers",
                                        ("books", "economics"))),
        )
