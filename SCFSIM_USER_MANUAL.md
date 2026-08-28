# SCFSim User Manual

**Version 0.16.3** · Agent-based simulation of credit risk propagation in supply chain finance networks

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation](#3-installation)
4. [Functional Modules](#4-functional-modules)
5. [API Reference](#5-api-reference)
6. [Operation Guide](#6-operation-guide)
7. [Example Scripts](#7-example-scripts)
8. [Verification and Accuracy](#8-verification-and-accuracy)
9. [Troubleshooting](#9-troubleshooting)
10. [Support and Version Information](#10-support-and-version-information)
11. [Appendix](#11-appendix)

---

## 1. Introduction

### 1.1 Overview

SCFSim answers four questions you should be able to answer before you draw a conclusion about credit risk in a multi-tier supply chain:

- **How far does a default travel?** — a seeded failure deep in the chain propagates through trade credit; SCFSim reports the cascade beyond the seeds, the final default share, and the frequency of systemic events.
- **Through which channel?** — counterparty losses, supply disruption, demand contraction and bank credit crunch are separately switchable, and two ablation designs decompose the coupled outcome into first-order effects, marginal effects and the interaction term.
- **What does financing technology change?** — a single scenario switch models blockchain-enabled deep-tier financing as three interpretable frictions (receivable visibility depth, verification haircut, fraud rate), so the technology is an experimental variable rather than an assumption.
- **How much does the answer depend on the defaults?** — switches for payables terms, risk-based pricing and an anchor default test whether a result survives when the model's strongest assumptions are relaxed.

The distinctive design commitment is that **no result is trusted on the engine's say-so**. The engine is checked against quantities computed *without* simulating — graph reachability bounds, accounting identities, signed comparative statics, an independently written reference implementation, and metamorphic relations — and every check is itself demonstrated to work by re-injecting a failure it must catch. The second commitment is stated scope: the headline comparison between traditional and deep-tier financing is conditional on asymmetric trade-credit terms, and the switch that closes the gap ships in the box (`firm.payables_delay`); the documentation says so rather than leaving it to be discovered.

### 1.2 Key Features

- **Layered SCF topology** — one core enterprise, tiered supplier layers with Dirichlet-distributed input shares, house-bank assignments; or bring your own network as an edge list.
- **Five-phase engine** — settlement → orders → production → financing → default resolution, with dated receivable, payable and loan ledgers, warm-start initialisation, and both invoice-tenor (self-liquidating) and revolving facilities.
- **Four coupled contagion channels** — each independently switchable, so ablation is a configuration change, not a code change.
- **The blockchain switch** — one boolean moves visibility depth, haircut and fraud rate jointly; each friction is also sweepable on its own.
- **Assumption switches** — payables on terms, lender-based risk pricing, and a scheduled default of the core enterprise itself.
- **Matched Monte Carlo** — `run_batch` replays a scenario over independent seeds with matched network draws; sweeps and ablations reuse the same seeds so differences are treatment effects, not sampling noise.
- **Strict mode** — `SimulationConfig(strict=True)` verifies the accounting identities and the economic properties after every period, at about 25% runtime cost.
- **Reproducibility** — every configuration round-trips through JSON; the paper's numbers are asserted by the test suite at the printed precision.

### 1.3 Technical Architecture

| Layer | Technology |
|---|---|
| Language | Python ≥ 3.9 |
| Numerical core | NumPy |
| Graphs | NetworkX |
| Figures | Matplotlib (use the Agg backend for headless runs) |
| Interface | Python API (no CLI); three runnable example scripts |
| Configuration | JSON-serialisable dataclasses |
| Packaging | setuptools / PEP 621 (`pyproject.toml`) |
| Continuous integration | GitHub Actions — Linux, macOS, Windows × Python 3.9–3.12, plus a floor-pinned job (numpy 1.22.4, networkx 2.8, matplotlib 3.5.3) on which the paper's headline numbers reproduce bit-for-bit |
| Tests | 163 tests, 97% statement coverage |
| License | MIT |

No GPU and no network access are required; all computation is local and deterministic given a seed.

### 1.4 Two Ways to Run an Experiment

|  | Intended for | How to run |
|---|---|---|
| **Example scripts** | Reproducing the paper; a template to edit | `python examples/blockchain_switch.py` |
| **Python API** | Your own scenarios, networks and sweeps | `from scfsim import SimulationConfig, run_batch` |

Both use the same engine. Run the examples first to confirm the installation and to see the standard experimental designs; then copy the pattern into your own scripts.

---

## 2. System Requirements

| Item | Minimum | Recommended |
|---|---|---|
| Python | 3.9 | 3.12 |
| Operating system | Linux, macOS, Windows | any of the three (all CI-tested) |
| Memory | 1 GB | 4 GB |
| Disk | 100 MB | 250 MB including figures |

**Required dependencies** (installed automatically):

| Package | Minimum version |
|---|---|
| numpy | 1.22 |
| networkx | 2.8 |
| matplotlib | 3.5 |

**Optional dependency group:**

| Group | Packages | Needed for |
|---|---|---|
| `dev` | pytest ≥ 7 | running the test suite |

Runtime scales linearly in firms × periods × Monte-Carlo paths, at roughly 20 µs per firm-period on one commodity x86-64 core. The 56-firm, 40-period headline experiment (800 paths) takes about 30 s; Monte-Carlo paths are independent, so `n_jobs=N` runs them in a process pool with results identical to the serial run.

---

## 3. Installation

### 3.1 From Source

SCFSim is not on PyPI; install from the repository:

```bash
git clone https://github.com/zouxuangit/scfsim
cd scfsim
pip install -e .            # engine only
pip install -e ".[dev]"     # with pytest
```

Or install the archived release directly from the DOI landing page (https://doi.org/10.5281/zenodo.22141706), which carries the exact v0.16.3 source.

### 3.2 Verify the Installation

```bash
python -c "import scfsim; print(scfsim.__version__)"
# 0.16.3

MPLBACKEND=Agg pytest tests/ -q -m "not slow"   # fast layer, ~7 s
MPLBACKEND=Agg pytest tests/ -q                 # full suite incl. paper numbers, ~2 min
```

Then run one bundled experiment end to end:

```bash
python examples/blockchain_switch.py
```

If the console prints two scenario summaries and `example_output.png` appears, the installation is complete.

### 3.3 Headless Note

The plotting helpers use Matplotlib. On servers without a display, set `MPLBACKEND=Agg` (as the commands above do) and pass `save="figure.png"` to the plot functions instead of relying on an interactive window.

---

## 4. Functional Modules

| Module | Purpose |
|---|---|
| `scfsim.config` | Declarative, JSON-serialisable configuration dataclasses, incl. `ChannelConfig` |
| `scfsim.network` | Layered SCF network generator; `network_from_edges` and `validate_network` for user graphs |
| `scfsim.agents` | `FirmState` and `BankState` containers with dated ledgers |
| `scfsim.simulation` | Discrete-time engine and the Monte-Carlo runner `run_batch` |
| `scfsim.metrics` | `RunResult` time series and `batch_summary` aggregation |
| `scfsim.sweep` | 1-D and grid sweeps, named ablations, channel decomposition |
| `scfsim.viz` | Scenario comparison, sensitivity and channel-contribution figures |
| `scfsim.benchmark` | Analytical reachability bounds and the two ablation designs |
| `scfsim.invariants` | Accounting identities, checked every period in strict mode |
| `scfsim.economics` | Economic properties and signed comparative-statics predictions |
| `scfsim.metamorphic` | Input transformations whose outputs must not change |
| `scfsim.reference` | Independent restricted-model implementation for differential testing |

### 4.1 `scfsim.config` — Configuration

Seven dataclasses, aggregated in `SimulationConfig`; every field has a default, and the whole object round-trips through JSON (`to_json` / `from_json`), so a complete experiment is a plain-text file.

- **`NetworkConfig`** — `n_tiers` (3), `firms_per_tier` ((8, 16, 32)), `n_banks` (3), `avg_buyers_per_firm` (1.6), `seed`.
- **`FirmConfig`** — cost and balance-sheet parameters: `cost_ratio` (0.72), `input_share` (0.55), `fixed_cost_ratio` (0.06), `initial_cash_ratio` (0.35), `payment_delay` (1), **`payables_delay` (0 — suppliers paid on delivery; set 1 for symmetric terms)**, `receivable_recovery` (0.35), `core_demand` (100.0).
- **`BankConfig`** — `advance_rate` (0.80), `interest_rate` (0.02), `capital_ratio` (0.12), `loan_recovery` (0.40), `loan_maturity` (1 — invoice discounting; larger for a revolving facility), **`pricing_slope` (0.0 — set > 0 to price credit against the lender's capital erosion)**.
- **`ScenarioConfig`** — the blockchain switch and its frictions: `blockchain` (False), `visibility_depth` (1) vs `bc_visibility_depth` (99), `haircut` (0.25) vs `bc_haircut` (0.05), `fraud_prob` (0.06) vs `bc_fraud_prob` (0.005), `deep_tier_access` (0.15 — residual eligibility beyond the visible depth).
- **`ChannelConfig`** — four booleans: `counterparty`, `supply`, `demand`, `credit_crunch`, all True.
- **`ShockConfig`** — `demand_sigma` (0.1), `liquidity_shock_prob` (0.03), `liquidity_shock_size` (0.5), seeding by count (`seed_defaults`, `seed_tier`, `seed_time`) or by name (`seed_firms`), and **`core_default_time` (None — set to a period to default the core enterprise itself)**.
- **`SimulationConfig`** — `n_periods` (30), the six sub-configs, `seed`, `strict` (False), `strict_layers` (("books", "economics")).

### 4.2 `scfsim.network` — Topology

- **`generate_network(cfg, rng=None)`** — random layered SCF network: one core, tiered suppliers, Dirichlet input shares, house banks.
- **`network_from_edges(edges, core, banks=1)`** — build a compliant graph from `(supplier, buyer, share)` triples; tiers are inferred as the longest path to the core, and shares that do not sum to one per buyer are **refused rather than normalised**, so mapping errors surface.
- **`validate_network(g, tol=1e-06)`** — admit any `networkx.DiGraph` that follows the attribute convention (`kind`, `tier`, `bank` on nodes, `share` on edges, trade edges pointing to a strictly lower tier); raises `ValueError` otherwise.
- **`core_node(g)`** — the single `kind == "core"` node; the core may be called anything.

### 4.3 `scfsim.simulation` — Engine

Each period runs five phases: (1) settlement of receivables booked one trade-credit cycle earlier, with defaulted buyers paying only the recovery rate and maturing loans repaid with interest; (2) stochastic core demand cascading upstream through input shares, deliveries capped by remaining supply capacity; (3) production costs and idiosyncratic liquidity shocks; (4) receivables financing from the house bank, up to `advance_rate × eligible collateral × credit tightening`, where eligibility applies the scenario's visibility depth, haircut and fraud discount; (5) default resolution — the bank writes the exposure down, buyers lose the input share, suppliers lose the demand.

- **`Simulation(config, network=None).run() -> RunResult`** — one path.
- **`run_batch(config, n_runs=100, base_seed=0, n_jobs=1, network=None)`** — independent seeds, matched network draws; `n_jobs=N` parallelises with identical results.

### 4.4 `scfsim.metrics` — Results

- **`RunResult`** — per-period `default_share`, `credit_outstanding`, `bank_losses`; the sets `defaulted_firms` and `seeded_firms`; and a `summary` dict (see Appendix B).
- **`batch_summary(results)`** — means, 95th percentiles and `systemic_event_freq`, the fraction of paths whose final default share exceeds 0.25.

### 4.5 `scfsim.sweep` — Experiments

- **`sweep(config, path, values, ...)`** — one matched batch per value of a dotted configuration path such as `"scenario.bc_haircut"` or `"firm.initial_cash_ratio"`.
- **`grid_sweep(config, grid, ...)`** — several paths jointly over their Cartesian product, capped by `max_simulations`.
- **`ablation(configs, ...)`** — a matched batch per named variant.
- **`channel_decomposition(isolated, loo, metric=...)`** — first-order effects, marginal effects and the interaction term from the two ablation designs.
- **`set_by_path(cfg, path, value)`** — the dotted-path setter the sweeps use.

### 4.6 `scfsim.benchmark` — Analytical Benchmarks

- **`supply_reachable_set(g, seeds)`** / **`demand_reachable_set(g, seeds)`** — descendants / ancestors of the seed set along trade edges; with only the corresponding channel live, the attributable cascade must lie inside them.
- **`attributable_defaults(treated, control)`** — seed-induced defaults isolated with a matched control run.
- **`isolated_channel_configs(base)`** / **`leave_one_out_configs(base)`** — the two ablation designs. Second-order channels — notably the credit crunch — only show up in the second.

### 4.7 `scfsim.viz` — Figures

`plot_scenario_comparison`, `plot_sensitivity`, `plot_channel_ablation`, `plot_channel_contributions`. Every helper accepts an existing `ax` so panels can be composed, and `save="file.png"` for headless use.

### 4.8 Verification modules

`scfsim.invariants` (accounting identities, `check_invariants`), `scfsim.economics` (`check_economics`, `check_drawing`, `comparative_statics`), `scfsim.metamorphic` (`scaled`, `relabelled`, `truncated`, `outcome_signature`) and `scfsim.reference` (`simulate_reference`, `linear_chain`, `restricted_config`) are described in Section 8; they are public so you can run the same checks against your own modifications.

---

## 5. API Reference

### 5.1 Configuration (the usual entry point)

```python
SimulationConfig(n_periods=30, network=NetworkConfig(), firm=FirmConfig(),
                 bank=BankConfig(), scenario=ScenarioConfig(), shock=ShockConfig(),
                 channels=ChannelConfig(), seed=None,
                 strict=False, strict_layers=("books", "economics"))

SimulationConfig.to_json() -> str
SimulationConfig.from_json(s) -> SimulationConfig
```

### 5.2 Networks

```python
generate_network(cfg: NetworkConfig, rng=None) -> nx.DiGraph
network_from_edges(edges, core: str, banks=1) -> nx.DiGraph   # (supplier, buyer, share)
validate_network(g: nx.DiGraph, tol=1e-06) -> None            # raises ValueError
core_node(g: nx.DiGraph) -> str
```

### 5.3 Simulation and Results

```python
Simulation(config, network=None).run() -> RunResult
run_batch(config, n_runs=100, base_seed=0, n_jobs=1, network=None) -> list[RunResult]
batch_summary(results: list[RunResult]) -> dict[str, float]
```

### 5.4 Sweeps and Ablation

```python
sweep(config, path, values, n_runs=50, base_seed=0, n_jobs=1, network=None) -> list[dict]
grid_sweep(config, grid, n_runs=50, base_seed=0, max_simulations=20000,
           progress=False, n_jobs=1, network=None) -> list[dict]
ablation(configs: dict[str, SimulationConfig], n_runs=50, base_seed=0,
         n_jobs=1, network=None) -> dict[str, dict]
channel_decomposition(isolated, loo, metric="mean_cascade_size",
                      channels=("counterparty", "supply", "demand", "credit_crunch")) -> dict
set_by_path(cfg, path: str, value) -> None
```

### 5.5 Benchmarks

```python
supply_reachable_set(g, seeds) -> set[str]
demand_reachable_set(g, seeds) -> set[str]
attributable_defaults(treated: RunResult, control: RunResult) -> set[str]
isolated_channel_configs(base) -> dict[str, SimulationConfig]
leave_one_out_configs(base) -> dict[str, SimulationConfig]
```

### 5.6 Verification

```python
check_invariants(firms, banks, cfg, t=-1, core_name="core-0") -> None   # raises InvariantViolation
check_economics(firms, banks, cfg, orders=None, books=None, t=-1,
                core_name="core-0") -> None                             # raises EconomicViolation
check_drawing(firm, eligible, tightening, cfg) -> None
comparative_statics() -> dict[str, int]        # signed predictions by config path

scaled(cfg, factor) -> SimulationConfig        # monetary unit rescaled
relabelled(g, rng) -> (nx.DiGraph, dict)       # names permuted within tiers
truncated(cfg, n_periods) -> SimulationConfig  # horizon shortened
outcome_signature(result, places=9) -> tuple

simulate_reference(cfg, n_tiers=None) -> ReferenceTrace
linear_chain(n_tiers=3, n_banks=1) -> nx.DiGraph
restricted_config(cfg) -> SimulationConfig
```

### 5.7 Plotting

```python
plot_scenario_comparison(batches: dict[str, list[RunResult]], save=None)
plot_sensitivity(sweeps, xlabel, metric="mean_default_share", baseline=None, ax=None, save=None)
plot_channel_ablation(ablation, metric="mean_cascade_size", order=None, ax=None, save=None)
plot_channel_contributions(isolated, loo, metric="mean_cascade_size",
                           channels=None, ax=None, save=None)
```

---

## 6. Operation Guide

### 6.1 Run a Scenario (the short path)

```python
from scfsim import SimulationConfig, ScenarioConfig, run_batch, batch_summary

cfg = SimulationConfig(n_periods=30)
cfg.shock.seed_defaults = 2                      # two seed defaults in tier 2
cfg.scenario = ScenarioConfig(blockchain=True)   # the deep-tier financing switch

results = run_batch(cfg, n_runs=100, base_seed=1)
print(batch_summary(results))
```

### 6.2 Compare Traditional and Deep-Tier Financing on Matched Paths

```python
from scfsim import ScenarioConfig, SimulationConfig, run_batch, batch_summary

base = SimulationConfig(n_periods=40); base.firm.initial_cash_ratio = 0.15
base.shock.seed_defaults = 3                         # scenario A: traditional SCF

cfg_b = SimulationConfig.from_json(base.to_json())   # scenario B: blockchain on
cfg_b.scenario = ScenarioConfig(blockchain=True)

for cfg in (base, cfg_b):
    print(batch_summary(run_batch(cfg, n_runs=200, base_seed=42)))
```

The JSON round-trip is the recommended way to copy a configuration: both scenarios then differ in exactly one switch, and `base_seed` matching makes the difference a treatment effect.

### 6.3 Relax the Default Assumptions

```python
cfg.firm.payables_delay = 1        # suppliers paid on terms, not on delivery
cfg.bank.pricing_slope = 0.4       # credit priced against the lender's capital erosion
cfg.shock.core_default_time = 5    # the core enterprise itself defaults at period 5
```

The first matters most: with symmetric one-period terms the two scenarios nearly converge in mean default share (the systemic-event frequency still falls by a third at the paper's stress level). Any conclusion you draw should be checked against these switches before it is published.

### 6.4 Bring Your Own Network

```python
from scfsim import SimulationConfig, ScenarioConfig, network_from_edges, run_batch, batch_summary

edges = [("Alpha Castings", "Acme Motors", 0.6), ("Beta Electronics", "Acme Motors", 0.4),
         ("Delta Steel", "Alpha Castings", 1.0), ("Zeta Chips", "Beta Electronics", 1.0)]
g = network_from_edges(edges, core="Acme Motors", banks=2)   # tiers inferred, validated

cfg = SimulationConfig(n_periods=40)
cfg.shock.seed_firms = ("Delta Steel",)                      # a named failure
cfg.scenario = ScenarioConfig(blockchain=True)
print(batch_summary(run_batch(cfg, n_runs=100, base_seed=1, network=g)))
```

The topology stays fixed across paths; only the shocks vary. Any `networkx.DiGraph` following the attribute convention passes `validate_network` and can be supplied the same way.

### 6.5 Sweep a Friction

```python
from scfsim import sweep

rows = sweep(cfg_b, "scenario.bc_haircut", [0.0, 0.15, 0.30, 0.45, 0.65],
             n_runs=50, base_seed=1)
for r in rows:
    print(r["value"], r["mean_default_share"])
```

Any dotted configuration path works (`"firm.initial_cash_ratio"`, `"bank.capital_ratio"`, `"scenario.bc_visibility_depth"`, …); `grid_sweep` crosses several.

### 6.6 Decompose the Channels

```python
from scfsim import (isolated_channel_configs, leave_one_out_configs,
                    ablation, channel_decomposition)

iso = ablation(isolated_channel_configs(base), n_runs=50, base_seed=1)
loo = ablation(leave_one_out_configs(base), n_runs=50, base_seed=1)
print(channel_decomposition(iso, loo))
```

Read both designs together: a channel that amplifies failures generated by the others (supply disruption) is invisible one-at-a-time and dominant leave-one-out, and the interaction term quantifies the overlap.

### 6.7 Verify a Modified Model

```python
cfg = SimulationConfig(n_periods=40, strict=True)          # both layers
cfg = SimulationConfig(strict=True, strict_layers=("books",))      # accounting only
```

**If you modify the engine, run with `strict=True`.** It verifies the accounting identities and the economic properties after every period at about 25% runtime cost; both specification errors in this project's history would have been caught immediately by it. The metamorphic transformations (`scaled`, `relabelled`, `truncated`) and the reference comparison (`simulate_reference` on `restricted_config(cfg)`) are public for the same reason.

### 6.8 Plot

```python
from scfsim import plot_scenario_comparison
plot_scenario_comparison({"traditional": run_batch(base, 200, 42),
                          "blockchain": run_batch(cfg_b, 200, 42)},
                         save="comparison.png")
```

### 6.9 Parallelise

`run_batch(..., n_jobs=8)` — and the same argument on `sweep`, `grid_sweep` and `ablation` — runs Monte-Carlo paths in a process pool with results identical to the serial run. `n_jobs=0` in the example scripts means "use every core".

---

## 7. Example Scripts

Three scripts in `examples/` are both the reproduction of the paper and the templates to copy:

| Script | What it does | Runtime |
|---|---|---|
| `blockchain_switch.py` | The headline comparison: traditional vs deep-tier financing, payables on delivery and on terms (both halves of the paper's Table 5), 800 matched paths, one figure | ~30 s |
| `channels_and_sensitivity.py` | Channel ablation under both designs, friction sweeps, credit-crunch capitalisation panel (the paper's Fig. 2); `--quick` runs a reduced version in seconds; `--jobs 0` uses every core | ~5 min |
| `custom_network.py` | A fourteen-firm mapped chain through the scenario comparison, reporting which named firms fail most often | seconds |

```bash
python examples/blockchain_switch.py
python examples/channels_and_sensitivity.py --quick
python examples/custom_network.py
```

`docs/REPRODUCTION.md` maps every figure and number in the paper to the console line of the script that produces it, and `tests/test_manuscript.py` asserts Table 5 and the channel decomposition at the printed precision — the paper's numbers are recomputed by CI, not quoted.

---

## 8. Verification and Accuracy

### 8.1 The Five Layers

A simulator of this kind has no reference output to compare against, so SCFSim verifies itself in five layers, each demonstrated to work by re-injecting a failure it must catch:

| Layer | What it asserts | How its effectiveness is shown |
|---|---|---|
| Reachability bounds | With one trade-graph channel active, the attributable cascade lies inside the descendants (supply) or ancestors (demand) of the seed set — computed without simulating | Re-checked over thirty random topologies and parameterisations per direction |
| Accounting identities | Exposure equals the borrower's principal; write-offs never exceed lending net of recovery; drawings equal supply | Eleven mutation tests corrupt the ledgers; each corruption must be caught |
| Economic properties | Deliveries bounded by the order book × supply capacity; bank capital scaled to its own credit book; a drawing collateralised when made | Both historical specification errors are re-injected; each must fire its check. Eleven signed comparative statics verified across matched seeds |
| Metamorphic relations | Rescaling the monetary unit, permuting firm labels and shortening the horizon leave outcomes unchanged | Each relation also run against a deliberately faulted engine, where it must fail |
| Differential testing | On a single linear chain the engine reproduces an independently written reference implementation to within 1e-9 — cash, loans, defaults, write-offs, period by period | Ten injected faults (collateral overstated by 2%, sales inflated by one part in ten thousand, …) must each break agreement; a guard checks every covered mechanism actually fires |

### 8.2 What the Stack Cannot Tell You

Every layer tests a property somebody wrote down in advance. The defects found since v0.9 did **not** come from the stack — each came from using the model in a way it had not been used (switching an assumption, seeding tier 1, supplying a real network). Treat the stack as necessary, not sufficient: it establishes that the model is self-consistent and matches its own specification, not that the specification is economically right. An independent domain review form ships in `docs/REVIEWER_PACKET.md` for exactly that gap.

### 8.3 Scope and Limitations

- **No calibration.** All parameters are illustrative; the model reproduces qualitative mechanisms and its absolute magnitudes are not forecasts.
- **The headline is conditional.** With symmetric trade-credit terms (`firm.payables_delay = 1`) the traditional-SCF default share on the paper's network falls from 55.6% to 25.1% and the gap between scenarios from 29 to 2 points. The published comparison describes chains in which suppliers are paid later than they pay.
- **Irreversible distress.** Defaulted firms never recover and buyers never re-source, so cascades are upper bounds relative to a chain with active mitigation.
- **The core enterprise's cash is not tracked**; unless `core_default_time` is set it is the risk-free anchor.
- **Settlement is share-weighted**, not invoice-level, so idiosyncratic invoice exposure is not represented.
- **Financing terms do not enter the firm's decision**; pricing tied to the borrower's own risk, and any demand response to price, are not modelled.
- **The core is the only final customer**, so its default ends the chain by construction.

`docs/FINANCIAL_SPEC.md` documents every financial assumption, ranked by how much a wrong answer would change the results.

---

## 9. Troubleshooting

### 9.1 No Figure Appears / Matplotlib Backend Errors on a Server

**Cause:** no display.

**Fix:** `export MPLBACKEND=Agg` and pass `save="figure.png"` to the plot helpers.

### 9.2 `network_from_edges` Raises "shares … do not sum to one"

**Expected.** Shares are refused rather than normalised so mapping errors surface. Check the edge list for a buyer whose incoming `share` values do not total 1.0; fix the data, do not rescale blindly.

### 9.3 `seed_firms` Raises "not a firm in this network"

**Cause:** a name in `shock.seed_firms` does not exist in the supplied network.

**Fix:** names are exact strings, including case; print `list(g.nodes)` to see what the network actually calls the firm.

### 9.4 The Credit-Crunch Channel Shows Almost No Effect

**Expected** at ordinary capitalisation. Receivables lending is self-liquidating and capped by collateral, so the channel is second order: about 0.3 extra firms in the mean cascade at `capital_ratio = 0.20`, rising to about 1.3 at 0.015. Lengthening `loan_maturity` does not activate it, because the advance rate caps the stock of principal. Sweep `"bank.capital_ratio"` downwards to see it bind, and use `leave_one_out_configs` — one-at-a-time ablation cannot see second-order channels at all.

### 9.5 The Two Scenarios Give Nearly Identical Results

**Check `firm.payables_delay`.** With payables on terms the working-capital gap that receivables financing bridges is largely closed and the scenarios converge by design (Section 8.3). This is a property of the economics, not a bug.

### 9.6 Strict Mode Makes Runs Noticeably Slower

**Expected:** about 25% on the paper's network. Use `strict_layers=("books",)` for the cheaper accounting layer only, or reserve `strict=True` for runs after you have modified the model — which is when it earns its cost.

### 9.7 Results Differ Between My Machine and CI

**Cause:** almost always an unpinned seed or a changed configuration, not the platform — CI reproduces the paper's numbers bit-for-bit on three operating systems and on floor-pinned dependencies.

**Fix:** set `base_seed` (and `NetworkConfig.seed` if the topology must be fixed), and diff your `cfg.to_json()` against the intended scenario.

### 9.8 The Full Test Suite Is Slow

**Expected:** the slow layer re-runs the paper's experiments (~2 min total). Day-to-day, run the fast layer: `pytest tests/ -q -m "not slow"` (~7 s).

---

## 10. Support and Version Information

### 10.1 Contact

- **Repository:** https://github.com/zouxuangit/scfsim
- **Support and bug reports:** open an issue at https://github.com/zouxuangit/scfsim/issues (issue templates are provided)

### 10.2 Version

- **Current version:** 0.16.3
- **Released:** 2026-08-26
- **License:** MIT

### 10.3 Author

| Name | Affiliation |
|---|---|
| Xuan Zou | Business School, Hunan Agricultural University |

### 10.4 Citation

If you use SCFSim in published work, please cite the archived release:

> Zou, X. (2026). *SCFSim: A Python framework for agent-based simulation of credit risk propagation in supply chain finance networks* (v0.16.3). Zenodo. https://doi.org/10.5281/zenodo.22141706

DOI: 10.5281/zenodo.22141706. Machine-readable metadata is in `CITATION.cff`.

### 10.5 Testing

```bash
MPLBACKEND=Agg pytest tests/ -q                 # 163 tests, 97% statement coverage
MPLBACKEND=Agg pytest tests/ -q -m "not slow"   # fast layer only (~7 s)
```

Continuous integration runs the suite on Linux, macOS and Windows across Python 3.9–3.12, once more with every dependency pinned to the floor of its declared range (numpy 1.22.4, networkx 2.8, matplotlib 3.5.3) on which the paper's headline numbers are asserted to reproduce bit-for-bit, and checks that the generated API reference and the example scripts are in sync with the source.

---

## 11. Appendix

### A. Complete Public API

**Configuration:** `SimulationConfig`, `NetworkConfig`, `FirmConfig`, `BankConfig`, `ScenarioConfig`, `ShockConfig`, `ChannelConfig`

**Networks:** `generate_network`, `network_from_edges`, `validate_network`, `core_node`, `CORE`

**Engine and results:** `Simulation`, `run_batch`, `RunResult`, `batch_summary`

**Sweeps:** `sweep`, `grid_sweep`, `ablation`, `channel_decomposition`, `set_by_path`

**Benchmarks:** `supply_reachable_set`, `demand_reachable_set`, `attributable_defaults`, `isolated_channel_configs`, `leave_one_out_configs`

**Invariants:** `check_invariants`, `network_invariants`, `InvariantViolation`

**Economics:** `check_economics`, `check_drawing`, `comparative_statics`, `COMPARATIVE_STATICS`, `EconomicViolation`

**Metamorphic:** `scaled`, `relabelled`, `truncated`, `outcome_signature`

**Reference:** `simulate_reference`, `linear_chain`, `restricted_config`, `ReferenceTrace`

**Plotting:** `plot_scenario_comparison`, `plot_sensitivity`, `plot_channel_ablation`, `plot_channel_contributions`

### B. Output Field Glossary

`RunResult.summary` (one path):

| Field | Meaning |
|---|---|
| `n_firms` | Firms in the network (core excluded from the default share denominator's seeds) |
| `final_default_share` | Share of firms defaulted at the end of the run |
| `cascade_size` | Defaults beyond the seeded ones, `max(0, total − seeds)` |
| `default_share_by_tier` | `{tier: share}` breakdown |
| `total_credit_extended` | Cumulative receivables financing drawn |
| `total_bank_losses` | Cumulative bank write-offs net of recovery |
| `banks_failed` | Number of failed banks |

`batch_summary` (across a batch):

| Field | Meaning |
|---|---|
| `runs` | Number of Monte-Carlo paths |
| `mean_default_share`, `p95_default_share` | Mean / 95th percentile of the final default share |
| `mean_cascade_size`, `p95_cascade_size` | Mean / 95th percentile of the cascade beyond the seeds |
| `mean_credit_extended` | Mean cumulative credit drawn |
| `mean_bank_losses` | Mean cumulative bank losses |
| `systemic_event_freq` | Fraction of paths whose final default share exceeds 0.25 |

`RunResult` time series: `default_share`, `credit_outstanding`, `bank_losses` (one value per period), plus the sets `defaulted_firms` and `seeded_firms`.

### C. Default Scenario at a Glance

| Group | Key defaults |
|---|---|
| Network | 3 tiers of 8/16/32 firms, 3 banks, ~1.6 buyers per firm |
| Firm | cost ratio 0.72, initial cash 0.35× baseline sales, receivables collected after 1 period, payables on delivery, recovery 0.35 |
| Bank | advance rate 0.80, interest 2%/period, capital ratio 0.12, loan recovery 0.40, invoice-tenor maturity, flat pricing |
| Traditional scenario | visibility depth 1, haircut 25%, fraud 6%, deep-tier access 0.15 |
| Blockchain scenario | visibility depth 99, haircut 5%, fraud 0.5% |
| Shocks | demand σ 0.1, liquidity shock 3%/period at 0.5× cash, one seed default in tier 2 at period 2 |
| Channels | all four on |

### D. Repository Layout

```
scfsim/
├── scfsim/                      # package source
│   ├── __init__.py              # public API
│   ├── config.py                # configuration dataclasses
│   ├── network.py               # topology generation + user networks
│   ├── agents.py                # FirmState / BankState
│   ├── simulation.py            # five-phase engine + run_batch
│   ├── metrics.py               # RunResult + batch_summary
│   ├── sweep.py                 # sweeps, ablation, decomposition
│   ├── viz.py                   # figures
│   ├── benchmark.py             # reachability bounds, ablation designs
│   ├── invariants.py            # accounting identities (strict mode)
│   ├── economics.py             # economic properties + comparative statics
│   ├── metamorphic.py           # invariance transformations
│   └── reference.py             # independent restricted-model implementation
├── examples/                    # blockchain_switch / channels_and_sensitivity / custom_network
├── docs/
│   ├── API.md                   # generated API reference
│   ├── FINANCIAL_SPEC.md        # every financial assumption, ranked by impact
│   ├── REPRODUCTION.md          # paper figure → script line map
│   ├── REVIEWER_PACKET.md       # structured domain-review form
│   └── RELEASE.md               # release runbook
├── tests/                       # pytest suite (163 tests)
├── .github/workflows/           # ci.yml + release.yml
├── pyproject.toml
├── CITATION.cff                 # incl. DOI
├── SCFSIM_USER_MANUAL.md        # this manual
├── LICENSE                      # MIT
└── README.md
```

---

*SCFSim 0.16.3 · MIT License · Copyright © 2026 Xuan Zou*
