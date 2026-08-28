# Changelog

All notable changes to SCFSim are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.17.0] — 2026-08-28

The first release shaped by the external domain review (archived in
`docs/REVIEW_2026-08.md`). This release answers the review's Q3 — the
one finding its author asked to have settled before the core financial
claims — and re-derives the results that depended on it. The remaining
review items (obligor-based pricing and a demand response, Q2;
functional-form robustness of credit tightening, Q4; invoice-level
recovery measurement, Q7; a global friction design, Q8) are scheduled
for 1.0.0 and recorded in `docs/REVIEW_INTEGRATION.md`.

### Added — the contract layer (review Q3)
- `BankConfig.instrument`: `"loan_against_receivables"` (default; the
  previous engine, bit-for-bit — asserted by a parity test) or
  `"receivables_purchase"` — a true sale, non-recourse on buyer credit.
  Derived read-only properties `recourse_mode` and `primary_obligor`
  document who the funder can pursue and whose credit is relied on.
- Under the purchase instrument a firm *sells* face value pro rata
  across maturities at `advance_rate × (1 − haircut) × (1 − fraud)` per
  unit; the sold face moves to the bank's purchased ledger
  (`BankState.purchased`), a seller default causes **no** write-off, and
  a buyer default — including the core enterprise's — is the bank's
  loss.
- An independent reference implementation of the purchase regime,
  `simulate_reference_purchase`, deliberately separate from
  `simulate_reference` so each stays under the readability ceiling; the
  engine reproduces it to 1e-9 across six parameterisations, and two
  injected faults (retained sold assets, a mispriced purchase) are each
  caught by the stack (`tests/test_contract.py`, 17 tests).
- Mode-aware invariants: no loans may exist under a purchase instrument,
  loss ceilings switch from lending-net-of-recovery to total purchase
  consideration, and purchased face must be non-negative.

### Changed — results conditional on the instrument
- The anchor-default finding reverses sign with the contract, exactly as
  the review predicted: with `core_default_time=10` on the stressed
  network (200 matched paths), deep-tier reach *reduces* bank losses
  under the loan instrument (ratio ≈ 0.8) and *multiplies* them under
  the non-recourse purchase (ratio ≈ 23), because the funder then owns
  claims on the anchor itself. The claim "deep-tier financing leaves
  banks with less exposure" is therefore an artefact of the
  loan-against-receivables contract and is no longer stated
  unconditionally anywhere in the documentation.
- The headline default-share comparison is robust to the instrument
  (traditional vs deep-tier: 55.6% → 26.5% under the loan, 58.5% →
  30.6% under the purchase, same seeds), so it is a statement about
  liquidity, not about where credit risk ends up.
- `check_drawing` accepts `proceeds=` and verifies sale proceeds against
  the pre-sale eligible value; `credit_outstanding` now includes the
  bank's purchased cost outstanding, so the funds-employed series is
  comparable across instruments.

## [0.16.3] - 2026-08-26

Patch: the project's own account of its verification record was stale.
No code changed.

### Fixed
- `docs/FINANCIAL_SPEC.md` §7, the README and the reviewer packet still
  told the reader that "since v0.4 no internal audit has found an error
  in the economics; every finding has been in the verification
  machinery" and that the stack was "complete as of v0.9.0". Written at
  v0.9.0, that was accurate; seven releases later it under-reported what
  had been found since: the headline result's dependence on asymmetric
  trade-credit terms (v0.12–v0.13), a channel entirely outside the
  differential comparison (v0.11), two engine defects on user-supplied
  networks (v0.15) and a documentation check that would have failed on
  its first run (v0.16). All three passages now give the record through
  v0.16 and draw the same conclusion from it as the audits drew from the
  earlier record: none of the later findings came from the verification
  stack; each came from using the model in a way it had not been used
  before, and the one use not yet made is an independent review.
- `docs/REVIEWER_INVITATION.md`: "nine internal verification rounds" is
  now sixteen, with the same one-sentence account.

## [0.16.2] - 2026-08-26

Patch: the recipe for producing v1.0.0 had drifted from the manuscript
it edits. No code changed.

### Fixed
- `docs/REVIEW_INTEGRATION.md` was written against the v0.10.1
  manuscript and quotes the sentences each verdict would touch. Six
  manuscript versions later, eight of its fourteen quoted anchors pointed
  at text that no longer existed (a limitation reworded in v0.11.0, a
  sentence deleted in v0.11.0, a phase description changed in v0.12.0),
  its page budget still said four lines of headroom and listed a cut that
  had already been spent, and it numbered figures as Fig. 3 after the
  renumbering. Every anchor is now checked against the v0.16.1 text; the
  budget, the remaining cut, the figure numbers, the reference count and
  the reference implementation's remaining line budget are current, and
  Q1, Q2, Q7 and Q8 account for the mechanisms that have since become
  switches. The checklist tells the authors to re-check the anchors
  before acting on the review, since the manuscript is not in the
  repository and no test can do it for them.
- `docs/SUBMISSION_CHECKLIST.md`: one figure number and the headroom.

## [0.16.1] - 2026-08-26

Patch: two measured corrections to the README and a guard on the release
mechanics. No code in the package changed except a docstring.

### Fixed
- The README, the quick-start note and `scfsim.invariants` said strict
  mode "costs about 10% of runtime". Measured on the paper's network it
  costs 25% (0.74 s → 0.92 s per 20 paths): the checkers have grown since
  the figure was first written in v0.4.0 and it was never re-measured.
  All three places now say "about a quarter".
- The README's scaling note ("beyond a few thousand firms … practical
  only with fewer paths") is replaced by measurements: about 20 µs per
  firm-period on one core, linear from 56 to 1,960 firms (0.05 s to
  1.74 s per 40-period path). Both measurements are in
  `docs/REPRODUCTION.md`.

### Added
- `docs/check_release_ready.py` and a matching step in the release
  workflow: refuse to publish while `.zenodo.json`, `CITATION.cff` or the
  README still carry a `REPLACE-ME` placeholder, or while an ORCID fails
  its checksum. Zenodo mints the DOI from `.zenodo.json` after the GitHub
  release is published, so a bad creator entry fails the archive after
  the release already exists; the guard fails before anything is
  published. The workflow also validates `CITATION.cff` with
  `cffconvert` (the current file validates).

## [0.16.0] - 2026-08-26

Verifies the environment claims in the paper's metadata tables, which
had never been tested: development ran only on Python 3.12 with the
latest dependencies, and CI had never executed. No modelling behaviour
changed.

### Fixed
- **The API-reference CI check would have failed on every run.**
  `docs/gen_api.py` rendered dataclass fields with a `default_factory`
  or no default as `<dataclasses._MISSING_TYPE object at 0x…>` — a
  memory address, different in every process — so the committed
  `docs/API.md` could never match a fresh regeneration and the
  docs-and-examples job's `git diff --exit-code` would have failed on
  the first push. Such fields now render as `NetworkConfig()`, `dict()`
  or `required`. A test regenerates the reference in-process and asserts
  it is byte-identical to the committed file and free of addresses; the
  output is identical on Python 3.9 and 3.12.

### Verified
- On Python 3.9.25 with numpy 1.22.4, networkx 2.8 and matplotlib 3.5.3
  — the floor of every range in `pyproject.toml` and the versions the
  paper's S6 declares — the fast suite passes, Table 5 reproduces
  bit-for-bit (both halves), the quick channel decomposition matches,
  and all three example scripts, the figure generator and the API
  generator run. Recorded in `docs/REPRODUCTION.md`.
- `generate_network` does draw input shares from a flat Dirichlet, as
  §2.1 states (checked while auditing the claims).

### Added
- A `floor` CI job: Python 3.9 with the pinned minimum dependency
  versions, running the fast suite and the Table 5 assertion, so the
  paper's S6/C7 claim is checked on every push rather than assumed.
- `docs/gen_api.py` exposes `render()` for the test above.

### Changed
- The test suite grew from 162 to 163 tests; statement coverage is 97%.
  The submission checklist's first-CI-run item lists four jobs.

### Note
Every number reported for v0.3.0 onwards reproduces exactly and is
asserted to by the slow test layer — now on two interpreters.

## [0.15.0] - 2026-08-26

Makes the paper's reuse claim true in practice. Section 2.1 calls
`validate_network` "the extension point for empirically mapped supply
networks" and Section 4 says the engine transfers to any layered
exposure network, but a user who built a graph to the documented
convention would have hit two latent faults and one missing capability.
No published number changed.

### Fixed
- **The engine identified the core enterprise by the name `core-0`**
  (`Simulation` and `RunResult` both hard-coded it), so a user network
  whose anchor had any other name failed with a `KeyError` or counted
  the core among the firms. The core is now located by `kind == "core"`
  and may be called anything; renaming it is asserted to leave every
  outcome unchanged — the anonymity relation extended to the anchor.
- **Banks were created from `network.n_banks`, not from the ids the
  network names**, so a mapped network with bank ids outside that range
  raised a `KeyError` at initialisation. A bank is now created for every
  id a firm names (plus the configured range, so generated networks keep
  their client-less banks and reproduce bit-for-bit).

### Added
- `run_batch(..., network=)`, and the same argument on `sweep`,
  `grid_sweep` and `ablation`: a Monte-Carlo batch on a fixed topology,
  in which only the shocks vary between paths. Previously a batch always
  drew a new synthetic network per seed, so there was no supported way
  to run the paper's experiments on a mapped chain.
- `network_from_edges(edges, core, banks)`: a validated network from
  `(supplier, buyer, share)` triples — the form a supplier map, invoice
  data or customs records take. Tiers are inferred as the longest path
  to the core, so a supplier selling into two depths sits above the
  deeper buyer, which tier-by-tier order propagation requires; shares
  that do not sum to one per buyer are reported, not normalised.
- `validate_network` now enforces the parts of the convention the engine
  silently relied on: the core at tier 0, firms at tier >= 1, every trade
  edge pointing to a strictly lower tier, incoming shares summing to one,
  every firm selling to somebody.
- `examples/custom_network.py`: a fourteen-firm mapped chain from an edge
  list, its reachability sets, and the scenario comparison on the fixed
  topology with per-firm default frequencies (about 2 s). Run in CI.
  README section *Bringing your own network*.
- `tests/test_custom_network.py`, eight tests.

### Changed
- Manuscript: S7 and Table 3 (F1) mention `network_from_edges` and the
  third example script; nothing else. The test suite grew from 154 to
  162 tests; statement coverage is 97%.

### Note
Every number reported for v0.3.0 onwards reproduces exactly and is
asserted to by the slow test layer.

## [0.14.0] - 2026-08-26

Consistency and literature release. No code in the package changed; the
manuscript's claims about the verification stack are brought back into
line with the stack, and the mechanisms the model simulates are anchored
to the analytical literature that formalises them.

### Fixed
- Table 4 of the manuscript still said "six mutation tests" and "nine
  signed comparative statics"; the suite has had eleven of each since
  v0.12.0. The README carried the same two stale counts. A count in
  `docs/FINANCIAL_SPEC.md` §7 that was correct as history ("nine
  injected faults") is now marked as such.

### Added
- Three references, each verified against the publisher's page and two
  independent indexes for journal, volume, issue, pages and DOI:
  Dong, Qiu and Xu (2023), *Blockchain-enabled deep-tier supply chain
  finance*, M&SOM 25(6) 2021–2037 — the analytical model of the
  mechanism the scenario switch represents, and a paper any reviewer in
  this area would expect to see cited; Kouvelis and Xu (2021), *A supply
  chain theory of factoring and reverse factoring*, Management Science
  67(10) 6071–6088 — the working-capital logic that the payables
  measurement turns on; Chod et al. (2020), *On the financing benefits of
  supply chain transparency and blockchain adoption*, Management Science
  66(10) 4378–4396. Cited in §1 (deep-tier reach; the analytical
  literature as a fifth category of related work that solves for
  contracts in two- or three-tier chains rather than cascades), §3 (the
  payables result) and §4. Sixteen references of the twenty-five allowed.
- `docs/FINANCIAL_SPEC.md` §7 gains a *Literature anchors* paragraph and
  the reviewer packet's Q9 asks whether the three frictions are a fair
  reduction of the mechanisms those papers formalise.

### Changed
- Manuscript: the "Fourth" category of related work in §1 is rewritten
  to include the analytical models; the body still ends on page 6 with
  the author block in place. The three new references push the
  reference list onto a seventh back-matter page; whether the target
  template counts references toward the page limit is on the checklist.

### Note
Every number reported for v0.3.0 onwards reproduces exactly and is
asserted to by the slow test layer.

## [0.13.0] - 2026-08-26

Puts the v0.12.0 finding where it belongs. The conditionality of the
headline result on asymmetric trade-credit terms was a sentence at the
end of Section 3; it is now the right-hand half of Table 5, computed on
the same 200 matched paths as the left-hand half, and its robustness
across stress levels is recorded. No modelling behaviour changed.

### Added
- `examples/blockchain_switch.py` runs the headline comparison twice:
  with suppliers paid on delivery (the paper's default) and on the same
  one-period terms as their customers. `scenario_configs(payables_delay)`
  exposes both. About 30 s.
- Table 5 of the manuscript gains two columns. On terms: mean default
  share 25.1% / 23.5% (from 55.6% / 26.5%), mean cascade 11.1 / 10.2,
  systemic events 39.5% / 25.5%; credit drawn falls by five sixths.
  `tests/test_manuscript.py` asserts all six numbers and the three
  phrases built on them.
- Robustness of the measurement across six configurations (cash
  buffers, recovery, shock intensity, package defaults), in
  `docs/FINANCIAL_SPEC.md` §1: the mean-share gap under symmetric terms
  is at most two points in every one. The residual reduction in
  systemic events is not robust — a third at the paper's stress level,
  little or nothing at milder ones — and the paper now says "by a
  third" rather than "halves".

### Changed
- Manuscript: abstract mentions the three switches; Highlight 5 does
  too; Section 3 quotes Table 5's 200-path numbers and states the
  robustness; four sentences elsewhere tightened to pay for the wider
  table (§1, §2.1, §2.3, §3). The body still ends on page 6, author
  block included, with about two lines to spare.
- Reviewer packet Q2 and the README quote the same numbers and the
  robustness caveat.

### Note
Every number reported for v0.3.0 onwards reproduces exactly and is
asserted to by the slow test layer.

## [0.12.0] - 2026-08-26

Continues v0.11.0: the assumption ranked second among the model's
limitations — suppliers paid on delivery while paying their own suppliers
on terms — becomes a switch, and the measurement changes how the headline
result must be stated. Off by default; every published number reproduces
bit-for-bit.

### Added
- **Payables on terms**, `FirmConfig.payables_delay` (default 0).
  Variable costs are booked to a dated payables ledger and paid that many
  periods after production; fixed costs and liquidity shocks are still
  paid at once. Unpaid invoices die with a defaulted firm (the suppliers'
  side is the counterparty channel, modelled separately). Comparative
  static `firm.payables_delay: −1`; identities on the ledger with two
  mutation tests; mirrored in the reference; an "actually exercised"
  guard and a tenth injected fault (payables settled a period early).
- **The measurement.** With symmetric one-period terms on the paper's
  stressed network the traditional-SCF default share falls from 0.55 to
  0.25, credit drawn falls by four fifths, and the gap between the
  scenarios shrinks from 29 to 2 points; deep-tier financing still
  halves the frequency of systemic events (0.45 → 0.24). The headline
  effect is therefore conditional on asymmetric trade-credit terms — the
  condition under which SCF is offered, but a condition. Section 3 of
  the manuscript now says so; the assumption moves to first place in
  `docs/FINANCIAL_SPEC.md` §6 and the reviewer packet's Q2 asks whether
  that population is the right one.
- **Parallel Monte-Carlo**, `run_batch(..., n_jobs=N)`, threaded through
  `sweep`, `grid_sweep` and `ablation`, and `--jobs N` on the sensitivity
  example. Paths are independent and carry their own seeds, so the result
  is identical to the serial run in the same order; a test asserts it.
  `n_jobs=0` uses every core.
- `docs/FINANCIAL_SPEC.md` §8: every parameter mapped to the observable
  it corresponds to and where a user calibrating to a real chain would
  find it. No values are asserted.
- A payables block in `relaxed_limitations()`; `tests/test_manuscript.py`
  pins the six numbers the paper quotes for it.

### Changed
- Manuscript: §2.1 phase (3) and Table 3 (F1) mention payables on terms;
  the §3 paragraph on relaxed assumptions now leads with the payables
  result and states the headline conditionally; §5 lists immediate
  payables first among the limitations. The body still ends on page 6
  with the author block in place.
- `simulate_reference` is 148 of its 150 permitted lines. The next
  mechanism is excluded from the differential comparison and listed in
  Table 4 as not covered, or paid for by simplification inside the
  reference; the ceiling is not raised.
- The test suite grew from 142 to 154 tests; statement coverage is 97%.
  The full sensitivity example takes about 5 minutes on one core (4.3 min measured on the release build under load).

### Note
Every number reported for v0.3.0 onwards reproduces exactly and is
asserted to by the slow test layer.

## [0.11.0] - 2026-08-26

The audits since v0.7.0 limited the *verification* stack, not the model.
This release turns the first- and last-ranked limitations in the paper
into switchable mechanisms — off by default, so every published number
reproduces bit-for-bit — and, in doing so, found and closed a gap in the
declared coverage of the differential layer.

### Added
- **Risk-based pricing**, `BankConfig.pricing_slope` (default 0). The
  rate on a new drawing is `interest_rate + pricing_slope × (1 − credit
  multiplier)`, fixed when the drawing is made and booked in a new
  interest ledger on `FirmState`; it is part of the credit-crunch
  channel and switched off with it. On the paper's stressed network a
  slope of 0.4 — a premium of up to forty points per period — moves the
  mean default share by less than one point in either scenario: quantity
  rationing already dominates, because a borrower whose bank is impaired
  can draw little at any price. Comparative static `bank.pricing_slope:
  +1`; two accounting identities on the interest ledger with mutation
  tests; mirrored in the reference implementation.
- **Anchor default**, `ShockConfig.core_default_time` (default `None`).
  From that period the core enterprise places no orders and its maturing
  payables settle at `receivable_recovery`. Because the core is the
  chain's only customer, its default ends the chain in every scenario;
  what differs is the speed of the collapse and the bank exposure caught
  on the way down. With the anchor default in place of the tier-2 seeds,
  deep-tier financing slows the collapse (0.18 of the chain defaulted by
  period 10 against 0.33) and, because the lending is self-liquidating,
  leaves banks with a sixth of the losses (0.12 against 0.74) — the risk
  transfer of Table 5 does not occur when the anchor itself fails.
  Mirrored in the reference. The working-capital unwind — a firm whose
  orders stop also stops paying variable costs before it stops
  collecting, so a demand collapse briefly *relieves* cash pressure — is
  documented in `docs/FINANCIAL_SPEC.md` §4 and taken into account by
  the tests.
- A fourth block in `examples/channels_and_sensitivity.py` runs both
  experiments (`relaxed_limitations()`); `tests/test_manuscript.py`
  pins the numbers the paper quotes for them.
- "Actually exercised" guards in `tests/test_reference.py`: the compared
  trajectory must actually settle a receivable at the recovery rate,
  charge a pricing premium, and stop the core's orders, or the
  corresponding parameterisation is vacuous. Two further injected
  faults (recovery on receivables overstated; pricing premium ignored)
  bring the total to nine.

### Fixed
- **The reference implementation had no counterparty channel.** From
  v0.7.0 to v0.10.1 a defaulted buyer's receivables were collected in
  full in `scfsim.reference`, while the documentation described the
  comparison as covering everything on the chain except stochastic
  shocks. No disagreement ever surfaced because every differential
  parameterisation seeded the deepest tier, whose default hits nobody's
  receivables, and in the stressed chains every firm failed in the same
  period. Found when the first tier-1 seed was tried while adding the
  anchor default. The channel is now in the reference, two
  parameterisations seed tiers 1 and 2, and Table 4 of the manuscript
  lists counterparty recovery among the covered mechanisms. Recorded in
  `docs/FINANCIAL_SPEC.md` §7 as the kind of gap the audits warned
  about: nine injected faults were all caught while an entire channel
  was outside the comparison, because no test asked which mechanisms the
  compared trajectory actually exercised.
- `simulate_reference` grew to 151 lines with the additions and tripped
  its 150-line readability ceiling; the two duplicated default-resolution
  blocks were merged into one local function, bringing it to 140 lines.
  The ceiling was not raised.

### Changed
- Manuscript: abstract, §2.1, Table 3 (F1), Table 4 (differential row),
  §3 (a paragraph on the two relaxed limitations) and §5 (the ranked
  limitations, now: credit priced on the lender rather than the
  borrower and never refused by firms; uncalibrated parameters;
  irreversible distress; a single final customer). To pay for the new
  paragraph the checklist's next contingency cut was applied: the
  headline figure (former Fig. 2) was dropped and Table 5 kept; the
  former Fig. 3 is now Fig. 2. The body ends on page 6 with about three
  lines to spare, author block included.
- `docs/REVIEWER_PACKET.md` Q1 reports the measured insensitivity to
  lender-based pricing and asks specifically about borrower-based
  pricing and a demand response to price; Q8 asks whether the anchor
  result matches the reviewer's expectations.
- The test suite grew from 124 to 142 tests; statement coverage is 97%.

### Note
Every number reported for v0.3.0 onwards reproduces exactly and is
asserted to by the slow test layer. The full sensitivity example now
takes about 5 minutes.

## [0.10.1] - 2026-08-26

Patch release: no code in the package changed. It prepares the
integration of the external inputs that v1.0.0 depends on, and fixes a
page-budget error that every earlier page check had shared.

### Added
- `docs/REVIEW_INTEGRATION.md`: for each of the nine questions in the
  reviewer packet, the specification section, code, manuscript
  sentences, tests and page cost that a QUALIFY or a WRONG would touch,
  with the caveat sentence for each QUALIFY pre-drafted against the page
  budget and the modelling change for each WRONG scoped — including
  whether it must be mirrored in the reference implementation or
  excluded from it, since that layer's scope is final. Ends with an
  empty verdict ledger and the step list for producing v1.0.0. Written
  before any review exists; it contains no verdicts.

### Changed
- Manuscript: the one-line author placeholder had hidden about five
  lines of page-1 content. A realistic block (three authors, two
  affiliations, corresponding e-mail, ORCIDs) pushed the entire
  Conclusions section onto page 7, so every "ends on page 6" check
  since v0.7 had been made against an understated budget. The
  placeholder is now a five-line block of realistic length, and the
  first two contingency cuts from the checklist pay for it: the code
  listing is six lines (still runnable; the JSON round-trip form), and
  Table 5's last row (credit extended / cumulative bank losses) is
  folded into the sentence below it, where both pairs of numbers still
  appear. The body ends on page 6 with about four lines to spare with
  the author block in place. Every number is unchanged;
  `tests/test_manuscript.py` asserts them where they now sit.
- `docs/SUBMISSION_CHECKLIST.md` records the author-block finding and
  the two remaining contingency cuts; `docs/REPRODUCTION.md` maps the
  two moved numbers to the prose.

### Note
No modelling behaviour changed. This release contains no further
internal work to do; v1.0.0 requires the domain review, the author
details and the archive DOI, and `docs/REVIEW_INTEGRATION.md` is the
recipe for producing it from them.

## [0.10.0] - 2026-08-26

Release-readiness version. The v0.9.0 change summary listed seven
remaining steps, all of them actions only the authors can take; this
release does the parts of those steps that do not require an author's
identity, so that each one becomes a short, mechanical task. No
verification layer was added and no modelling behaviour changed.

### Added
- `.github/workflows/release.yml`: pushing a `v*` tag checks that the
  tag matches `scfsim.__version__`, re-runs the fast suite on the tagged
  commit, builds the sdist and wheel, verifies the wheel installs into a
  clean environment, and publishes a GitHub release with both attached.
  Publishing the release is what triggers the Zenodo archive.
  `docs/RELEASE.md` is the runbook for the remaining human steps: the
  Zenodo toggle, which DOI goes where, and what to back-fill.
- `tests/test_release_metadata.py`: the version string must agree across
  `pyproject.toml`, the package, `CITATION.cff`, `.zenodo.json`, the
  changelog, the README and the submission checklist. Version bumps had
  been done by hand for nine releases; this makes a missed file fail the
  fast suite and the release workflow.
- `docs/gen_fig1.py` regenerates Fig. 1 from the repository. The figure
  had been a hand-made artefact that predated the verification modules,
  so it showed eight modules while the package has twelve and the README
  lists twelve; the manuscript text repeated "eight". All three now
  agree, and the figure can be regenerated when the layout changes.
- `docs/REVIEWER_INVITATION.md`: the cover note to send with the reviewer
  packet, written so that the Q0-before-specification ordering cannot be
  missed.
- `.gitignore`; `.zenodo.json` records the version.

### Changed
- Manuscript: language and typography pass — en dashes for ranges and
  parenthetical dashes, superscript tolerance, a handful of sentences
  tightened; Section 2.1 names all twelve modules; Fig. 1 replaced by
  the regenerated version at the same size. Every number is unchanged
  and `tests/test_manuscript.py` still passes. The body still ends on
  page 6.
- References checked against their sources where that could be done
  without a subscription: [3] and [12] confirmed in full (journal,
  volume, pages, DOI); [2] confirmed to exist in IEEE Transactions on
  Engineering Management (2024) but its DOI could not be cross-checked
  and is flagged in the checklist for the authors. [1], [4]–[11] and
  [13] are long-established citations and were checked for internal
  consistency only.
- `docs/SUBMISSION_CHECKLIST.md` records the reference verification and
  points each remaining item at the runbook or note that executes it.
- The test suite grew from 117 to 124 tests; statement coverage is 97%.

### Note
No modelling behaviour changed: every number reported for v0.3.0 onwards
reproduces exactly, and is asserted to by the slow test layer. This is
the last release with internal work in it; the next should be v1.0.0,
after the independent domain review has been incorporated.

## [0.9.0] - 2026-08-26

The audit of v0.8.0 concluded that the internal verification stack had
reached the point at which further self-checking could no longer
distinguish a stable model from a self-confirming one, and recommended
against another iteration built around internal checks. This release
follows that recommendation. It adds no verification layer and widens no
existing one; it fixes the boundaries of the stack in code so they cannot
drift, and it lowers the cost of the external actions that remain.

### Added
- `tests/test_manuscript.py`: the numbers quoted in the paper — Table 5
  and the channel decomposition of Fig. 3(a) — are asserted at their
  printed precision from scenarios imported from the example scripts,
  so the manuscript and the code cannot drift apart unnoticed. Runs in
  the slow layer. `docs/REPRODUCTION.md` maps the remaining figures in
  the paper (the friction sweeps and the capitalisation panel, which take
  minutes) to the console output that produces them, with the values
  obtained on the release build.
- Two tests guarding the *design* of the differential layer rather than
  the engine: the reference implementation may import only the
  configuration modules from the package, and `simulate_reference` may
  not exceed 150 lines. The first pins the only surface the two
  implementations share; the second turns the scope ceiling the v0.8.0
  audit recorded into a tripwire, so an extension has to be argued for.
- The shared surface — the three `effective_*` properties that implement
  the blockchain switch, and their JSON round-trip — is unit-tested
  directly, because the differential comparison is blind to anything
  both sides read from the same code. One differential parameterisation
  now runs with the switch on.
- `docs/REVIEWER_PACKET.md` gains a pre-registration step: Q0 asks the
  reviewer to list the mechanisms and conventions they would require
  *before* reading our specification, and Q8 becomes a structured
  comparison of that list against what the specification contains. The
  v0.8.0 audit noted that the packet's questions inherit the blind spots
  of the document they were written from; the ordering is what makes the
  review independent rather than a check of our own list.

### Changed
- The example scripts expose their configuration as functions
  (`stressed_base()`, `scenario_configs()`, `decompose_channels()`) and
  run under `if __name__ == "__main__"`, so tests can import the exact
  scenarios the paper describes. Console output and figures are
  unchanged.
- `docs/FINANCIAL_SPEC.md` §7 and `scfsim.reference` document the two
  boundaries above and state where the remaining uncertainty sits.
  `README.md` says what the verification stack cannot tell a user.
- `docs/SUBMISSION_CHECKLIST.md` records that the manuscript body has no
  headroom and gives an ordered list of cuts for the template migration,
  and it treats the Q0/Q8 comparison as the primary output of the
  domain review. A stale statement of a third of a page of headroom, and
  a stale version number in the README limitations section, are fixed.
- Manuscript: Table 4 states that the reference shares only the
  configuration classes with the engine; the test count and version are
  updated; the data-availability statement records that the reported
  numbers are pinned by the test suite. No other text changed and the
  body still ends on page 6.
- The test suite grew from 111 to 117 tests; statement coverage is 97%.

### Note
No modelling behaviour changed: every number reported for v0.3.0 onwards
reproduces exactly, and is now asserted to.

## [0.8.0] - 2026-08-20

The audit of v0.7.0 recommended treating the number of verification layers
as having reached its limit — the manuscript had run out of space to
describe another — and deepening the existing layers instead. This release
follows that recommendation: no sixth layer, wider coverage for the fifth.

### Added
- The reference implementation now covers the **entire credit layer**:
  collateral eligibility (visibility depth, haircut, expected fraud), the
  advance-rate cap on the stock of debt, dated repayment with interest,
  write-offs on default, and capital-driven credit tightening. v0.7.0
  forced `advance_rate = 0`, which left all of it outside the differential
  comparison.
- The comparison now checks loan balances and cumulative bank write-offs
  alongside cash and default status; three further faults are injected
  (collateral overstated by 2%, interest half a point too high, recovery
  on defaulted loans overstated by ten points) and must each break
  agreement, bringing the total to seven.
- `docs/REVIEWER_PACKET.md`: a structured 60–90 minute review form for an
  independent supply chain finance expert — nine questions ordered by how
  much a wrong answer would change the published results, each with a
  verdict box, answerable without reading the code. Every audit of this
  project has identified domain review as the one step internal work
  cannot replace; this lowers its cost.
- `--sample-parameterisations` thins the heavily parameterised
  differential and metamorphic cases for a fast pass on a constrained
  runner.

### Changed
- `restricted_config()` no longer disables financing; it constrains the
  network to one bank so that credit tightening is unambiguous.
- Manuscript: the ranked limitation list cut from Section 5 in v0.7.0 is
  restored, paid for by consolidating the functionality table from six
  rows to four. Table 4 now states what the differential layer does and
  does not cover.
- The test suite grew from 100 to 111 tests; statement coverage is 97%,
  with `scfsim.reference` at 100%.

### Note
No modelling behaviour changed: every number reported for v0.3.0 onwards
reproduces exactly.

## [0.7.0] - 2026-08-20

Release focused on the residual circularity identified by the audit of
v0.6.0: metamorphic relations escape the need to know the right answer,
but they still require someone to write down the right *invariance*.

### Added
- `scfsim.reference`: an independent implementation of a restricted model
  — a single linear chain, no stochastic shocks, financing disabled —
  re-derived directly from `docs/FINANCIAL_SPEC.md` and short enough to
  verify by reading. `tests/test_reference.py` asserts that the engine
  reproduces its cash trajectory to within 1e-9 for every firm in every
  period, across four parameterisations and four chain lengths, and
  injects four faults that must each break agreement. Differential testing
  catches implementation slips that violate no property anyone thought to
  state.
- `linear_chain()` and `restricted_config()` build the regime the
  reference covers; the reference honours `ShockConfig.seed_firms` so the
  supply cascade is exercised rather than left dormant.
- Anonymity is now shown to hold on the **default** randomly-seeded code
  path as well as for explicitly named seeds, closing the coverage gap the
  previous audit recorded, plus a test documenting that the relation is
  invariance to *renaming* and not to *reordering* — the draw selects a
  position, so a differently ordered node list is a different input.
- Dimensional homogeneity is tested across twenty-one orders of magnitude
  (1e-9 to 1e12), which is now its declared validity band.

### Changed
- `restricted_config()` no longer clears `seed_firms`; only the random
  draw is disabled.
- The test suite grew from 80 to 100 tests; statement coverage is 97%.

### Note
No modelling behaviour changed: every number reported for v0.3.0 onwards
reproduces exactly.

## [0.6.0] - 2026-08-20

Release focused on the circularity identified by the audit of v0.5.0:
every verification layer up to that point required someone to know the
right answer in advance, and so was blind to any failure mode nobody had
anticipated.

### Added
- `scfsim.metamorphic`: verification that needs no oracle. Three relations
  transform an input in a way that must not change the output —
  **dimensional homogeneity** (rescaling the monetary unit),
  **anonymity** (permuting firm labels within tiers), and **no lookahead**
  (a short run reproduces the prefix of a long one). Each is tested on the
  real engine, where it must hold, and against a deliberately faulted
  engine, where it must fail.
- `FirmConfig.core_demand` makes the monetary unit an explicit parameter,
  which is what allows dimensional homogeneity to be tested.
- `ShockConfig.seed_firms` names the firms to default instead of drawing
  them, so a shock is reproducible across relabelled networks.
- `SimulationConfig.strict_layers` selects which verification layers
  `strict` enables (`"books"`, `"economics"`, or both).
- `--statics-runs` pytest option tunes the cost of the comparative-statics
  layer without editing test code.

### Changed
- **The default trigger is now relative.** A firm defaults when cash falls
  below `-default_tolerance × baseline_sales` rather than below an absolute
  constant, and the core enterprise's cash endowment scales with
  `core_demand`. Absolute constants in a model whose quantities are all
  ratios break dimensional homogeneity; these were found by writing the
  relation down rather than by observing a wrong result.
- `docs/FINANCIAL_SPEC.md` records the one declared-but-untested
  comparative-statics prediction (`bank.capital_ratio`, whose effect size
  sits below sampling noise) so the exemption cannot become a blind spot,
  and states which layer escapes the oracle problem and which does not.
- The test suite grew from 66 to 80 tests; statement coverage is 97%.

### Note
No modelling behaviour changed: every number reported for v0.3.0 onwards
reproduces exactly.

## [0.5.0] - 2026-08-20

Release focused on the limitation identified by the audit of v0.4.0: the
accounting identities added in v0.4.0 verify that the books balance, and
therefore could not have detected either of the two specification errors in
this project's history, both of which balanced perfectly and simply meant
the wrong thing.

### Added
- `scfsim.economics`: economic properties, as distinct from accounting
  identities. Deliveries are bounded by the order book scaled by supply
  capacity; a bank's capital is scaled to its own potential SCF credit
  book; a drawing is supported by eligible collateral at the moment it is
  made. Checked alongside the accounting identities under `strict=True`.
- **Regression tests for both historical specification errors.** Each bug
  is re-injected into the engine and the corresponding check is asserted
  to fire, so the guards are demonstrated to catch the failures they were
  written for rather than merely asserted to.
- `COMPARATIVE_STATICS`: nine signed predictions about the direction in
  which the default share must move as each parameter rises, checked
  across matched Monte-Carlo seeds.
- Ten further tests covering the previously unexercised error branches of
  both checkers; the suite has no skipped tests.

### Changed
- The advance-rate ceiling is now checked as a **flow** property at the
  moment of drawing rather than as a stock property every period. The
  first draft checked the stock, which is wrong once
  `loan_maturity > payment_delay` because the collateral securing a
  drawing is collected while the drawing is still outstanding; the test
  suite caught this before release and a test now pins the distinction.
- `examples/channels_and_sensitivity.py` runs in strict mode, and the
  README quick start tells users to enable it whenever they modify the
  model.
- `docs/FINANCIAL_SPEC.md` distinguishes **[books]** from **[economics]**
  enforcement, sources the advance rate against industry practice
  (70–90% is the range quoted by receivables-finance providers; the
  default of 0.80 sits inside it), and adds a section stating plainly what
  mechanical checking cannot do.
- The test suite grew from 42 to 66 tests; statement coverage is 97%.

### Note
No modelling behaviour changed in this release; every number reported for
v0.3.0 and v0.4.0 reproduces exactly.

## [0.4.0] - 2026-08-20

Release focused on making the financial specification self-checking, in
response to the audit of v0.3.0, which noted that two successive audits had
each found a specification error that testing alone had not surfaced.

### Added
- `scfsim.invariants`: accounting identities and domain bounds — a bank's
  recorded exposure equals the borrower's balance, a firm's dated loan
  ledger reconciles to its balance, write-offs never exceed lending net of
  recovery, defaulted firms carry no loans, aggregate drawings equal
  aggregate supply, and structural checks on network input shares.
  `SimulationConfig(strict=True)` runs them after every period at a cost of
  roughly 10% of runtime; off by default.
- Seventeen invariant tests, including six **mutation tests** that corrupt
  the ledgers in six different ways and assert the checker catches each —
  the checker's own sensitivity is tested rather than assumed.
- `docs/FINANCIAL_SPEC.md`: every financial assumption, its rationale, how
  it compares with the literature's conventions, what would change if it
  were relaxed, and a ranked list of what an independent domain reviewer
  should attack first. Explicitly labelled a structured self-review rather
  than a substitute for expert review.
- `grid_sweep()` now refuses to start a sweep larger than
  `max_simulations` (default 20 000 simulations) and accepts
  `progress=True`.
- Pytest `slow` marker separating the randomised property tests and large
  ablations from the fast layer, which now runs in about 7 seconds.

### Changed
- CI is split into three jobs: the fast suite across the nine-entry
  platform matrix, the slow suite once, and a documentation-and-examples
  job that fails if `docs/API.md` differs from a fresh regeneration
  (previously CI only checked that generation succeeded).
- README documents why `bank.loan_maturity` cannot raise peak exposure:
  the advance rate caps the stock of principal, so a longer facility defers
  repayment while consuming headroom.

### Note
No modelling behaviour changed in this release; every number reported for
v0.3.0 reproduces exactly.

## [0.3.0] - 2026-08-20

Release focused on the open questions raised by the audit of v0.2.0: the
apparent inertness of the credit-crunch channel, the unexplained
sub-additivity of the channel decomposition, and the narrow parameter
support of the validation suite.

### Added
- `BankConfig.loan_maturity`: drawings are now booked to a dated loan
  ledger and repaid on maturity, so revolving facilities can be modelled
  alongside invoice-tenor (self-liquidating) receivables lending.
- `sweep.grid_sweep()`: joint sweeps over the Cartesian product of several
  configuration paths, for studying interactions between frictions.
- `sweep.channel_decomposition()`: reports each channel's first-order and
  marginal effect together with the interaction term, i.e. the gap between
  the coupled effect and the sum of the first-order effects.
- Randomised property tests: the reachability bounds are now checked over
  30 randomly drawn network topologies and parameterisations per direction,
  rather than at a single configuration.
- A fourth panel in the sensitivity example locating the bank
  capitalisation at which the credit-crunch channel starts to bind, and a
  `--quick` flag that runs the whole experiment in seconds.
- `docs/gen_api.py` and the generated `docs/API.md`; `.zenodo.json` and
  `docs/SUBMISSION_CHECKLIST.md`.

### Changed
- **Specification fix (behaviour-changing).** Bank capital is now sized
  against the SCF credit book each bank could plausibly hold (advance rate
  applied to its clients' receivables outstanding) rather than against
  total chain sales. `capital_ratio` is therefore an interpretable capital
  ratio against SCF exposure; under the previous base it was roughly an
  order of magnitude too generous, which is why the credit-crunch channel
  appeared inert.
- The test suite grew from 18 to 25 tests; statement coverage is 97%.

### Fixed
- `BankState.outstanding` is now decremented on partial repayment instead
  of being cleared wholesale, which was only correct for single-period
  loans.

## [0.2.0] - 2026-08-20

Release focused on model validity, verifiability and reproducibility, in
response to an internal audit of v0.1.0.

### Added
- `ChannelConfig`: the contagion channels can now be switched on and off
  independently, which makes ablation experiments possible.
- `scfsim.benchmark`: analytical reference quantities computed without
  running the model — `supply_reachable_set` (descendants bound),
  `demand_reachable_set` (ancestors bound), `attributable_defaults`
  (treated-minus-control attribution), plus `isolated_channel_configs` and
  `leave_one_out_configs` for the two ablation designs.
- `scfsim.sweep`: `sweep()` for one-dimensional sensitivity analysis over
  any dotted configuration path, `ablation()` for named config variants,
  and `set_by_path()` with validation of unknown fields.
- `viz.plot_sensitivity`, `viz.plot_channel_ablation` and
  `viz.plot_channel_contributions`; all plotting helpers now accept an
  existing `ax` so figures can be composed.
- `examples/channels_and_sensitivity.py`: channel decomposition and
  sensitivity to the three financing frictions.
- Eleven new tests (`tests/test_benchmark.py` validation suite and
  `tests/test_viz.py` plotting smoke tests), taking the suite from 7 to 18
  tests and statement coverage to 96%. Continuous
  integration across three operating systems and four Python versions, a
  Limitations section in the README, issue templates and this changelog.

### Changed
- **Model fix (behaviour-changing).** A firm's realised sales are now
  scaled by its own remaining supply capacity. In v0.1.0 the loss of an
  input supplier reduced only what the firm ordered from its *other*
  suppliers and left its own deliveries untouched, so supply disruption
  propagated upstream but never downstream. Cascade sizes under the
  stressed example are correspondingly larger than in v0.1.0.
- The upstream (demand-contraction) and downstream (supply-disruption)
  directions are now separate, separately switchable channels; the model
  therefore has four channels rather than three.
- `run_batch()` clones configurations with `copy.deepcopy` instead of a
  JSON round-trip, so non-serialisable fields cannot silently break a batch.
- `scfsim.viz` no longer calls `matplotlib.use("Agg")`, which previously
  overrode the backend of any interactive session that imported SCFSim.
- Figures are exported in vector (PDF) as well as raster format.

### Fixed
- `RunResult` now records the names of defaulted and seeded firms, which
  the reachability benchmarks require.

## [0.1.0] - 2026-08-20

Initial release: layered SCF network generation, five-phase discrete-time
engine, receivables financing with a blockchain scenario switch,
Monte-Carlo batches, summary metrics and a comparison figure.
