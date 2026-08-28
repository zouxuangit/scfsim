"""SCFSim: agent-based simulation of credit risk propagation in supply
chain finance networks.

Public API
----------
- :class:`scfsim.SimulationConfig` (+ nested configs) -- declarative scenarios
- :func:`scfsim.generate_network` -- layered SCF network generator
- :class:`scfsim.Simulation` / :func:`scfsim.run_batch` -- engine
- :func:`scfsim.batch_summary` -- Monte-Carlo aggregation
- :func:`scfsim.sweep` / :func:`scfsim.ablation` -- sensitivity analysis
- :func:`scfsim.supply_reachable_set` -- analytical cascade bound
- plotting helpers in :mod:`scfsim.viz`
"""
from .benchmark import (attributable_defaults, demand_reachable_set,
                        isolated_channel_configs, leave_one_out_configs,
                        supply_reachable_set)
from .config import (BankConfig, ChannelConfig, FirmConfig, NetworkConfig,
                     ScenarioConfig, ShockConfig, SimulationConfig)
from .economics import (COMPARATIVE_STATICS, EconomicViolation,
                        check_drawing, check_economics,
                        comparative_statics)
from .invariants import (InvariantViolation, check_invariants,
                         network_invariants)
from .metamorphic import (outcome_signature, relabelled, scaled,
                          truncated)
from .metrics import RunResult, batch_summary
from .reference import (ReferenceTrace, linear_chain, restricted_config,
                        simulate_reference)
from .network import (CORE, core_node, generate_network, network_from_edges,
                      validate_network)
from .simulation import Simulation, run_batch
from .sweep import (ablation, channel_decomposition, grid_sweep,
                    set_by_path, sweep)
from .viz import (plot_channel_ablation, plot_channel_contributions,
                  plot_scenario_comparison, plot_sensitivity)

__version__ = "0.16.3"
__all__ = [
    "BankConfig", "ChannelConfig", "FirmConfig", "NetworkConfig",
    "ScenarioConfig", "ShockConfig", "SimulationConfig",
    "RunResult", "batch_summary", "CORE", "generate_network",
    "check_invariants", "network_invariants", "InvariantViolation",
    "scaled", "relabelled", "truncated", "outcome_signature",
    "simulate_reference", "linear_chain", "restricted_config",
    "ReferenceTrace",
    "check_economics", "check_drawing", "comparative_statics",
    "COMPARATIVE_STATICS",
    "EconomicViolation",
    "validate_network", "network_from_edges", "core_node", "Simulation",
    "run_batch",
    "sweep", "grid_sweep", "ablation", "channel_decomposition",
    "set_by_path",
    "supply_reachable_set", "demand_reachable_set", "attributable_defaults",
    "isolated_channel_configs", "leave_one_out_configs",
    "plot_scenario_comparison", "plot_sensitivity", "plot_channel_ablation",
    "plot_channel_contributions",
    "__version__",
]
