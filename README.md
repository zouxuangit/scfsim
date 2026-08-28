# SCFSim

**Agent-based simulation of credit risk propagation in supply chain finance (SCF) networks.**

SCFSim generates (or ingests) a multi-tier supply network — one core enterprise, tiered
suppliers, and financial institutions — and simulates trade-credit settlement,
receivables financing, and default contagion through four coupled channels:
counterparty losses, supply disruption, demand contraction, and bank credit crunch.
A single scenario switch turns on **blockchain-enabled deep-tier financing** (extended
receivable visibility, lower verification haircut, suppressed fraud), letting
researchers quantify how financing technology reshapes systemic risk in supply chains.
Three further switches, off by default, relax the assumptions the paper ranks as its
main limitations: suppliers can be paid on terms rather than on delivery
(`firm.payables_delay`), banks can price credit against their own capital erosion
(`bank.pricing_slope`), and the core enterprise itself can default
(`shock.core_default_time`). The first matters: with symmetric trade-credit terms the
two scenarios nearly converge in mean default share at every stress level tried, so
the headline comparison is a statement about chains in which suppliers are paid later
than they pay — the right-hand half of Table 5 in the paper says so.

> Version 0.16.3 · MIT License · Python ≥ 3.9 · depends only on numpy, networkx, matplotlib

## Install

```bash
pip install -e .            # from the repository root
pip install -e .[dev]       # with pytest
```

## Quick start (60 seconds)

```python
from scfsim import SimulationConfig, ScenarioConfig, run_batch, batch_summary

cfg = SimulationConfig(n_periods=30)
cfg.shock.seed_defaults = 2                      # two seed defaults in tier 2
cfg.scenario = ScenarioConfig(blockchain=True)   # the deep-tier financing switch

results = run_batch(cfg, n_runs=100, base_seed=1)
print(batch_summary(results))
```

> **If you modify the model, run it with `SimulationConfig(..., strict=True)`.**
> Strict mode verifies the accounting identities *and* the economic properties
> after every period, and costs about a quarter of runtime. Both specification errors
> in this project's history would have been caught immediately by it. Set
> `strict_layers=("books",)` or `("economics",)` to enable one layer only.

Worked examples:

```bash
python examples/blockchain_switch.py          # scenario comparison + figure
python examples/channels_and_sensitivity.py           # ablation + sensitivity
python examples/channels_and_sensitivity.py --quick   # ... in seconds
python examples/custom_network.py             # a mapped chain from an edge list
```

## What is in the box

| Module | Purpose |
|---|---|
| `scfsim.config` | Declarative, JSON-serialisable scenario configuration, incl. `ChannelConfig` |
| `scfsim.network` | Layered SCF network generator; `network_from_edges` and `validate_network` for user-supplied graphs |
| `scfsim.agents` | Firm and bank state containers |
| `scfsim.simulation` | Discrete-time engine: settlement → orders → production → financing → default resolution; Monte-Carlo batch runner |
| `scfsim.metrics` | Per-run time series, cascade summaries, batch aggregation |
| `scfsim.benchmark` | Analytical reachability bounds and ablation designs used to verify the engine |
| `scfsim.invariants` | Accounting identities and domain bounds, checked every period in strict mode |
| `scfsim.economics` | Economic properties and signed comparative-statics predictions |
| `scfsim.metamorphic` | Input transformations whose outputs must not change |
| `scfsim.reference` | Independent implementation of a restricted model, for differential testing |
| `scfsim.sweep` | Parameter sweeps (1-D and grid), ablations, channel decomposition |
| `scfsim.viz` | Scenario comparison, sensitivity and channel-contribution figures |

## Model in one paragraph

Each period, receivables booked one trade-credit cycle earlier are settled (defaulted
buyers pay only a recovery rate), the core enterprise draws stochastic demand which
cascades upstream through input shares, and firms deliver against their order book up
to their remaining supply capacity and pay production costs. A firm short of cash
requests receivables financing from its house bank; eligible collateral depends on how
deep the *financing visibility* of confirmed core payables reaches — tier 1 in
traditional SCF, effectively unbounded on a blockchain platform — minus a verification
haircut and an expected-fraud discount. Banks accumulate losses from defaulted
borrowers and tighten credit as capital erodes (and, optionally, price it dearer); a
failed bank stops lending to all of its clients. The core enterprise can be made to
default at a chosen period, after which it orders nothing and pays its maturing
payables at the recovery rate. Firms that remain illiquid default, hitting their buyers (supply
disruption), their suppliers (demand contraction and counterparty losses) and their
bank (credit crunch).

## Validation

The engine is checked against quantities computed *without* simulating:

* **Reachability bounds.** With only the supply channel live, contagion can travel
  supplier→buyer only, so the attributable cascade must lie inside the *descendants*
  of the seed set; with only the demand channel live it must lie inside the
  *ancestors*. `scfsim.benchmark` computes both, and `attributable_defaults()`
  isolates seed-induced defaults from ordinary operating failures using a matched
  control run.
* **Ablation.** `isolated_channel_configs()` measures each channel acting alone and
  `leave_one_out_configs()` measures each channel removed from the coupled model.
  Second-order channels — notably the credit crunch, which only binds once other
  channels have eroded bank capital — need the second design to show up at all.
  `channel_decomposition()` reports both together with the interaction term.
* **Randomised property tests.** Both bounds are re-checked over 30 randomly drawn
  topologies and parameterisations per direction, so validity does not rest on one
  hand-picked configuration.
* **Economic properties.** Accounting checks verify that the books balance; they
  cannot detect a specification that balances perfectly and means the wrong thing.
  Both specification errors in this project's history were of that kind, so
  `scfsim.economics` states the economic content they violated — deliveries are
  bounded by the order book scaled by supply capacity, a bank's capital is scaled
  to its own potential credit book, a drawing is supported by collateral at the
  moment it is made — and `tests/test_economics.py` re-injects each historical bug
  and asserts the check fires. A guard that cannot catch the bug it was written
  for is not a guard. Eleven signed comparative-statics predictions (more cash
  cannot raise defaults, a larger haircut cannot lower them, and so on) are
  checked across matched seeds.
* **Differential testing.** `scfsim.reference` re-implements a restricted version
  of the model — a single linear chain, no stochastic shocks — directly from
  `docs/FINANCIAL_SPEC.md`, short enough to verify by reading. The engine must
  reproduce its cash, loan balances, default status and bank write-offs to within
  1e-9 every period for every firm. The whole credit layer is inside the
  comparison (collateral eligibility, the advance-rate cap, dated repayment with
  interest fixed at drawing, risk-based pricing, write-offs, capital-driven
  tightening, and the blockchain switch), as are counterparty recovery, payables on
  terms and the anchor default; multi-buyer share splitting and stochastic shocks are outside it,
  and that boundary is final — covering them would make the reference a copy of the
  engine, so a line-count ceiling on `simulate_reference` turns any extension
  into a deliberate decision. The two implementations share only the
  configuration dataclasses, which a test forbids the reference from exceeding
  and which are unit-tested directly because the comparison is blind to them.
  Ten injected faults — among them collateral overstated by 2%, interest half
  a point too high, recovery on receivables overstated, and sales inflated by one
  part in ten thousand — must each break agreement. A word on the counterparty
  channel: from v0.7.0 to v0.10.1 the reference silently omitted it, and no
  parameterisation seeded a firm whose default hits anyone's receivables, so the
  omission never surfaced. v0.11.0 closes it and adds guards that check each
  mechanism in scope is actually exercised by the compared trajectory
  (`docs/FINANCIAL_SPEC.md` §7).
* **Metamorphic relations.** Every check above needs someone to know the right
  answer in advance, and so is blind to a failure nobody anticipated. Metamorphic
  testing asks instead: if the input is transformed in a way that *must not*
  change the output, does it? Three relations hold by construction — rescaling the
  monetary unit (dimensional homogeneity), permuting firm labels (anonymity), and
  shortening the horizon (no lookahead). Each is tested twice: on the real engine,
  where it must hold, and against a deliberately faulted engine, where it must
  fail.
* **Accounting identities.** `SimulationConfig(strict=True)` verifies after every
  period that the ledgers reconcile — a bank's recorded exposure equals the
  borrower's balance, write-offs never exceed lending net of recovery, a defaulted
  firm carries no loans, total drawings equal total supply, and so on. Eleven mutation
  tests deliberately corrupt the ledgers and assert that the checker catches each,
  so the checker's own sensitivity is tested. Strict mode costs about a quarter of
  runtime (measured: 25% on the paper's network, with the interest and payables
  ledgers now checked as well) and is off by default.

### On the credit-crunch channel

Receivables lending is self-liquidating and capped by eligible collateral, so a
bank's exposure to any one firm is bounded by roughly one invoice cycle. The
credit-crunch channel is therefore genuinely second-order in SCF, unlike in
interbank networks where exposures are long-lived: at a bank capital ratio of 0.20
it adds about 0.3 firms to the mean cascade, rising to about 1.3 firms at 0.015.
Lengthening `bank.loan_maturity` does not by itself activate it, because the advance
rate caps the *stock* of principal, so a longer facility defers repayment while
consuming headroom and leaves peak exposure unchanged. The parameter is therefore
only economically interesting when contrasting invoice discounting
(`loan_maturity = payment_delay`, the default) with a revolving facility whose
repayment is decoupled from invoice settlement. `docs/FINANCIAL_SPEC.md` documents
this and every other financial assumption, ranked by how much a wrong answer would
change the results.

```bash
MPLBACKEND=Agg pytest tests/ -q                 # 163 tests, 97% statement coverage
MPLBACKEND=Agg pytest tests/ -q -m "not slow"   # fast layer only (~7 s)
```

### What the stack cannot tell you

Between v0.4 and v0.10 no internal audit found an error in the *economics*
of the model; every finding was in the verification machinery, and the
audit of v0.8.0 found none there either — a record consistent with a stable
model and equally consistent with checks that had converged to detecting
only the failure modes their authors imagined. The stack was declared
complete at v0.9.0 on those grounds. What has been found since came from
*using* the model in ways it had not been used, not from checking it: the
switchable assumptions (v0.11–v0.13) showed the headline result to be
conditional on asymmetric trade-credit terms; a tier-1 seed showed a whole
channel outside the differential comparison; a user-supplied network
exposed two engine defects; a second interpreter exposed a broken
documentation check. None of these was caught by the five layers. The one
use not yet made is to show the model to someone who did not build it,
which is why the section *For domain reviewers* below exists.

### Reproducing the manuscript

The numbers quoted in the paper are pinned by `tests/test_manuscript.py`,
which imports the scenarios from the two example scripts (not a re-typed
copy) and asserts Table 5 and the channel decomposition at the printed
precision. It runs in the slow layer (about 50 s). `docs/REPRODUCTION.md`
maps every remaining figure in the paper — the friction sweeps and the
capitalisation panel, which take minutes — to the console line of the
script that produces it.

## Limitations

Version 0.16.3 makes the following simplifications, which users should weigh before
drawing substantive conclusions:

* **No calibration.** All parameters are illustrative. The model reproduces
  qualitative mechanisms; it has not been fitted to real receivables or
  balance-sheet data, and absolute magnitudes should not be read as forecasts.
* **Irreversible distress.** Defaulted firms never recover, buyers do not re-source
  from surviving suppliers, and lost supply capacity is not rebuilt. Cascades are
  therefore upper bounds relative to a chain with active mitigation.
* **The core enterprise's cash is not tracked**; unless `core_default_time` is set it
  is the risk-free anchor of the chain.
* **Settlement is approximate.** Recovery on receivables is applied as a
  share-weighted average over a firm's buyers rather than by tracking each invoice,
  so idiosyncratic invoice-level exposure is not represented.
* **Immediate payables by default.** Suppliers are paid on delivery while their own
  customers pay on terms — the widest working-capital gap. `firm.payables_delay`
  closes it; doing so cuts the traditional-SCF default share on the paper's network
  from 55.6% to 25.1% and the gap between scenarios from 29 to 2 points (systemic
  events still fall by a third at that stress level). Ranked first among the
  limitations.
* **Financing terms do not enter the firm's decision.** By default banks charge a
  flat rate; with `bank.pricing_slope > 0` the rate rises with the lending bank's
  capital erosion, which on the paper's stressed network changes the results by less
  than one point — quantity rationing dominates. Pricing tied to the *borrower's*
  risk, and any demand response to price, are not modelled.
* **The core enterprise is the only final customer.** Its default
  (`shock.core_default_time`) therefore ends the chain; the feature is for studying
  how fast the collapse travels and how much bank exposure it catches, not the size
  of the cascade, which is total.
* **Single-period trade-credit cycle** by default, and no inventories.

## Performance

The engine is a pure-Python agent loop, so runtime scales linearly in
firms × periods × Monte-Carlo runs — measured at roughly 20 µs per firm-period on one
commodity x86-64 core, from 56 firms (0.05 s per 40-period path) to 1,960 firms
(1.7 s per path, so 100 paths in about 3 min). The 56-firm, 40-period
`blockchain_switch.py` example (800 paths, both halves of Table 5) takes
about 30 s; the ablation and
sensitivity example takes about 5 min. Monte-Carlo paths are independent, so
`run_batch(..., n_jobs=N)` (and the same argument on `sweep`, `grid_sweep` and
`ablation`) runs them in a process pool with results identical to the serial run;
`channels_and_sensitivity.py --jobs 0` uses every core. Networks of several thousand
firms are practical with fewer paths or more cores — the per-path loop is not vectorised.

## Bringing your own network

A mapped supply chain enters as an edge list — one row per supplier–buyer
relationship with the share of the buyer's purchases it represents — and runs
through the same batch, sweep and ablation drivers as the generated networks, with
the topology fixed and only the shocks varying between paths:

```python
from scfsim import SimulationConfig, ScenarioConfig, network_from_edges, run_batch, batch_summary

edges = [("Alpha Castings", "Acme Motors", 0.6), ("Beta Electronics", "Acme Motors", 0.4),
         ("Delta Steel", "Alpha Castings", 1.0), ("Zeta Chips", "Beta Electronics", 1.0)]
g = network_from_edges(edges, core="Acme Motors", banks=2)   # tiers inferred, validated

cfg = SimulationConfig(n_periods=40)
cfg.shock.seed_firms = ("Delta Steel",)                       # a named failure
cfg.scenario = ScenarioConfig(blockchain=True)
print(batch_summary(run_batch(cfg, n_runs=100, base_seed=1, network=g)))
```

`network_from_edges` infers each firm's tier as the longest path to the core, so a
supplier that sells into two depths is placed above the deeper buyer; it refuses
shares that do not sum to one per buyer rather than normalising them, so mapping
errors surface. `validate_network` accepts any `networkx.DiGraph` built by other means
that follows the convention (`kind`, `tier`, `bank` on nodes, `share` on edges, trade
edges pointing to a strictly lower tier). The core enterprise is identified by
`kind == "core"` and may be called anything; banks are created for every id a firm
names. `examples/custom_network.py` runs a fourteen-firm mapped chain through the
scenario comparison and reports which firms fail most often — a question the
synthetic networks cannot ask.

## Reuse beyond SCF

Any layered exposure network — interbank lending tiers, reinsurance chains, even
SIR-type diffusion on trade networks — can be studied by re-interpreting the financing
layer, which is what makes the framework a general tool for **risk propagation on
layered networks with an endogenous liquidity backstop**.

## For domain reviewers

The financial specification has not been reviewed by an independent supply chain
finance expert, and every internal audit of this project has concluded that such
a review cannot be substituted for. `docs/REVIEWER_PACKET.md` is a structured
review form of about 70–100 minutes: it opens with a ten-minute question to be
answered *before* reading our specification, so that the reviewer's list of
required mechanisms is not anchored on ours, followed by nine questions ordered
by how much a wrong answer would change the published results, each with a
verdict box, answerable from `docs/FINANCIAL_SPEC.md` without reading the code.
The closing question compares the two lists; that comparison is the review's
primary output.

## Contributing

Bug reports and feature requests are welcome via the GitHub issue templates. CI runs
the test suite on Linux, macOS and Windows for Python 3.9–3.12, and once more on
Python 3.9 with every dependency pinned to the floor of its declared range
(numpy 1.22.4, networkx 2.8, matplotlib 3.5.3), where the paper's headline numbers
are asserted to reproduce bit-for-bit. Pushing a version
tag runs the release workflow, which builds the distributions and publishes a
GitHub release (`docs/RELEASE.md`); `tests/test_release_metadata.py` keeps the
version string consistent across every file that records it. `docs/gen_api.py`
and `docs/gen_fig1.py` regenerate the API reference and the architecture figure.

## Citing

See `CITATION.cff`. The blockchain scenario design follows the mechanisms discussed
in Du et al., *IEEE Trans. Eng. Manage.* 67(4), 2020, and the transaction-security
frictions analysed in Li et al., *IEEE Trans. Eng. Manage.*, 2024. The analytical
literature the simulator complements — deep-tier financing under blockchain visibility
(Dong, Qiu and Xu, *M&SOM* 25(6), 2023), factoring and reverse factoring (Kouvelis and
Xu, *Management Science* 67(10), 2021), and the financing benefits of transparency
(Chod et al., *Management Science* 66(10), 2020) — is cited in the paper.

## Support

Questions and bug reports: open a GitHub issue or email `scfsim@REPLACE-ME.org`.
