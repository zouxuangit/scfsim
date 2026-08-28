# Integrating the domain review: verdict-to-edit map

`REVIEWER_PACKET.md` lowers the cost of *obtaining* an independent review.
This document lowers the cost of *acting on it*. For every question in the
packet it records, in advance, exactly what a QUALIFY or a WRONG touches —
the specification section, the code, the sentences in the manuscript, the
tests, and the page budget — so that incorporating the review is a
sequence of known edits rather than a fresh analysis. It was written before
any review existed and contains no verdicts; the verdict ledger at the end
is empty on purpose.

Two constraints apply to every edit below.

- **The page budget.** As of v0.16.1 the body ends on page 6 with a
  realistic five-line author block in place and about two lines of
  headroom in the draft layout. Three of the four contingency cuts have
  been spent (six-line code listing, Table 5's last row folded into the
  prose, the former headline figure dropped — Table 5 carries its
  numbers). A caveat sentence costs one line unless it replaces existing
  words; the only cut left is to merge the two examples by dropping the
  friction sweep, Fig. 2(b)–(c), and stating its result in one sentence
  (about a third of a page). Never cut the ranked limitations in
  Section 5. Since v0.13.0 Table 5 has four numeric columns (payables on
  delivery / on terms) and Section 3 ends with a paragraph on the three
  switchable assumptions; several of the edits below now land there.
- **The differential layer's scope is final** (`scfsim.reference`,
  module docstring). A model change that fits inside a single linear chain
  without stochastic shocks — pricing, payables timing, tightening shape,
  recovery rules on a chain — must be mirrored in the reference, which
  stays under its 150-line tripwire. A change that needs the network
  (re-sourcing, per-buyer ledgers) is switched **off** in
  `restricted_config()` and added to the "not covered" clause of Table 4;
  the reference is not extended to reach it.

Every model change, whatever its source, ends with the same four steps:
`MPLBACKEND=Agg pytest tests/ -q` (the slow layer re-asserts the paper's
numbers and will fail), re-run both example scripts in full, update the
numbers in Section 3, Table 5, `tests/test_manuscript.py` and
`docs/REPRODUCTION.md` together, and add a *behaviour-changing* entry to
`CHANGELOG.md`.

---
## Q1 — Payables settled immediately, receivables delayed

| | |
|---|---|
| Spec | §1 *Variable cost*, §6 item 1 |
| Code | `_produce_and_finance`: `firm.cash -= cost` in the period of production; receivables booked at `t + payment_delay` |
| Manuscript | §2.1 phase (3) "pay variable costs on delivery or, optionally, on terms"; Table 5 right-hand columns; §3 closing paragraph "Paying suppliers on the same one-period terms as their customers closes the working-capital gap …"; §5 limitation 1 "immediate payables by default" |
| Tests | reference (cost timing is one line of the reference arithmetic); `test_invariants.py` drawings-equal-supply |

**QUALIFY.** §3 already states the result conditionally and §5 lists
the assumption first. If the reviewer wants it in the abstract, add
"under asymmetric trade-credit terms" after "reshapes that propagation"
(five words, no line cost on page 1).

**WRONG (v0.12.0 update).** `FirmConfig.payables_delay` now exists,
mirrored in the reference, and the measurement is in §3 of the paper:
symmetric terms collapse the mean-share gap to 2 points. A WRONG here
therefore means one of two things. *The default population is wrong*:
change the default to `payables_delay = 1`, re-run everything, and
rewrite the headline around the systemic-event frequency (which still
halves) rather than the mean share — every number in Section 3 and
Table 5 changes. *A defaulted buyer's unpaid payables should hit its
suppliers*: that is a second counterparty channel; the suppliers' side is
already `receivable_recovery`, so the change is to make the two
consistent, ~10 lines and a spec §4 rewrite.

---

## Q2 — Exogenous pricing of credit

| | |
|---|---|
| Spec | §2 *Pricing*, §6 item 2 |
| Code | `BankConfig.interest_rate` (flat); charged in `Simulation._settle`; never read in `_request_financing`, so price does not enter the draw decision |
| Manuscript | §2.1 phase (4) "and, optionally, priced against that erosion"; §3 "In this configuration the reach of deep-tier financing, not the quality of verification, is what makes the blockchain scenario stabilising" and, in the closing paragraph, "Pricing credit against the lender's capital erosion … moves the mean default share by less than one point in either scenario"; §5 limitation 2 "credit priced on the lender rather than the borrower and never refused by firms" |
| Tests | `test_economics.py` comparative statics (no prediction involves the rate); `test_reference.py` "costly credit" parameterisation |

**QUALIFY.** §5 already carries the limitation and §3 reports the
measured insensitivity to lender-based pricing. Strengthen the §3 claim
in place, at zero line cost: "In this configuration, and under the
quantity rationing the model assumes, the reach of deep-tier financing,
not the quality of verification, is what makes the blockchain scenario
stabilising." Add the reviewer's reasoning to spec §2 *Pricing* caveat.

**WRONG.** Lender-based pricing already exists (`BankConfig.pricing_slope`,
v0.11.0, mirrored in the reference, comparative static `+1`, fault
"pricing premium ignored") and is measured to change nothing, so a WRONG
here means one of two things. *Borrower-based pricing*: a premium on the
borrower's own condition — the natural observable is the shortfall being
financed relative to baseline sales — added as `FirmConfig`/`BankConfig`
fields, ~6 lines in `_request_financing`, ~4 in the reference. *Demand
response to price*: `FirmConfig.max_rate`, above which a firm does not
draw and defaults instead; ~3 lines each side. Either changes numbers;
the second is the one that can reverse the headline, because it removes
the backstop exactly where it binds. Section 3's conclusion must then be
re-derived, not re-worded.

---

## Q3 — Where the loss lands: recourse and the anchor's credit

| | |
|---|---|
| Spec | **not addressed** — the word "recourse" does not appear in `FINANCIAL_SPEC.md`. A QUALIFY or WRONG here creates a new §2 subsection and a new §6 item |
| Code | `_request_financing` books the drawing on the borrowing firm (`firm.loans`); `_resolve_default` writes the exposure down against the *borrower's* default (`bank.register_loss(exposure * (1 - loan_recovery))`); the anchor's credit enters only through `_eligible_receivables`, never through loss allocation. Buyer non-payment reaches suppliers separately via `receivable_recovery` in `_settle` |
| Manuscript | §2.1 phase (4); the framing of deep-tier financing in §1, which describes the anchor's confirmed payables as what makes a deep-tier supplier bankable |
| Tests | `test_reference.py` mirrors the write-off rule, so a change is inside the differential scope; `test_invariants.py` write-offs-never-exceed-lending |

**OK.** Add a sentence to spec §2 recording that the arrangement is a
borrowing-base facility with the credit risk on the borrower, and that a
reviewer judged this the right representation. No manuscript change; this
is a gap in the *specification*, not in the model, and closing it costs
nothing.

**QUALIFY.** The model represents one product and the paper implies a
wider class. Add to §5, replacing the lowest-ranked limitation: "credit
risk is carried by the borrowing supplier rather than transferred to the
anchor" (one line). Spec gains a §2 subsection and a §6 entry at the rank
the reviewer's answer implies.

**WRONG — the anchor's credit should bear the loss.** This is the largest
change any verdict in this packet can produce, because it moves the
anchor from a *collateral* mechanism to a *loss-allocation* mechanism and
the two scenarios differ precisely in how deep the anchor's credit
reaches. Loss on a deep-tier drawing would fall on the core enterprise
(or on the bank's exposure *to* the core) rather than on the failed
supplier's bank, which changes: who writes off what in `_resolve_default`
(~10 lines), the capital base in §3 (a bank's receivables-finance book is
then concentrated on one name), the credit-crunch channel's magnitude,
and — most importantly — the direction of the deep-tier comparison, since
deeper reach would now concentrate rather than distribute bank losses.
The anchor-default result in §3 ("leaves banks with a sixth of the
losses") must be re-derived, not re-worded; it may reverse. Mirror in
`scfsim.reference` (the single chain can express it) and re-run
everything. Budget a full iteration and treat the headline as unproven
until it is done.

---

## Q4 — Linear credit tightening and the capital base

| | |
|---|---|
| Spec | §3 *Capital base*, *Credit tightening*; §6 item 3 |
| Code | capital sized in `_init_states` (advance rate × clients' baseline receivables outstanding); multiplier `BankState.tightening()` applied in `_request_financing` |
| Manuscript | §2.1 phase (4) "multiplied by the bank's capital-driven credit tightening"; §2.1 "bank capital is sized against the credit book a bank could plausibly hold"; Table 4 economics row "bank capital is scaled to its own credit book"; §3 panel (d) paragraph |
| Tests | `test_economics.py` capital-base regression (re-injects the v0.2 error); `test_reference.py` "thin bank capital" |

**QUALIFY.** Panel (d) paragraph: "It binds through capitalisation
instead, **under the linear taper the model assumes**: its marginal
contribution rises…" (zero to one line). Spec §3 caveat already says a
step function has a regulatory counterpart; add the reviewer's view on
which is realistic.

**WRONG on the taper.** `BankConfig.tightening = "linear" | "step"` with
`step_threshold`; ~4 lines in `BankState.tightening()`, ~3 in the
reference (which is at 148 of 150 lines — pay for them by simplifying
elsewhere in it, or exclude the step form from the comparison and say so
in Table 4). Only the credit-crunch channel changes, and it is second
order: Fig. 2(d) and its two quoted numbers change; Table 5 moves little.
**WRONG on the base.** Re-derive the base with the reviewer; this is the
mechanism the v0.3.0 fix got wrong once already, so re-run the capital
regression test *first* and expect it to need a new expected value.

---

## Q5 — Self-liquidating lending and the second-order credit channel

| | |
|---|---|
| Spec | §5 both structural results; §2 *Advance* (stock cap) |
| Code | `headroom = advance_rate × eligible × tight − firm.loans` in `_request_financing`; `BankConfig.loan_maturity` |
| Manuscript | §3 panel (d) paragraph in full ("Panel (d) answers a question the framework raised. The credit-crunch channel is second order … a contrast with interbank models [5, 6]"); README *On the credit-crunch channel*; Highlights bullet 2 mentions the channel but not its order |
| Tests | `test_economics.py` flow-vs-stock advance-rate check; `test_reference.py` "long facility" |

**QUALIFY.** Replace "The credit-crunch channel is second order in supply
chain finance because…" with "The credit-crunch channel is second order
**for invoice-tenor lending** because…" and delete "since tenor is not the
binding constraint" if the reviewer disputes the tenor argument (net
negative line cost). Spec §5 first paragraph gains the qualification.

**WRONG.** The stock-cap argument is unsound → the advance rate must cap
*new drawings against new collateral* (a flow) and exposure can then
accumulate with tenor. That changes `_request_financing`, the economics
check (which currently asserts the flow property at drawing time and
would now be the model rather than the check), the reference, and the
interpretation of panel (d), which may reverse. Treat as a re-run of the
v0.3.0 investigation; budget a full iteration.

---

## Q6 — Irreversible distress

| | |
|---|---|
| Spec | §4 *Supply disruption* caveat; §6 item 4 |
| Code | `_resolve_default`: `supply_capacity = 0`, buyers' capacity reduced by the share, never restored; no re-sourcing anywhere |
| Manuscript | §2.1 phase (5); §5 limitation 3 "irreversible distress" |
| Tests | reachability bounds (`test_benchmark.py`) are computed on the fixed trade graph: re-sourcing would add edges and invalidate the descendants/ancestors bound |

**QUALIFY.** §5 already lists it. If the reviewer says the *relative*
comparison is distorted, add to the paragraph below Table 5: "Both
scenarios share the no-recovery assumption, so the comparison is between
upper bounds." (one line, from the two-line headroom).

**WRONG.** Re-sourcing and capacity recovery need the network and
therefore fall **outside the reference scope**: implement as
`FirmConfig.recovery_periods` / `NetworkConfig.resourcing`, default off,
forced off in `restricted_config()`, listed in Table 4 as not covered.
The reachability bounds are invalid once re-sourcing rewires the graph
— the layer's docstring must say so and the tests must run it with
re-sourcing off.
Numbers change substantially; the bound tests are the first to fail.

---

## Q7 — Share-weighted recovery instead of invoice-level tracking

| | |
|---|---|
| Spec | §4 *Counterparty* caveat; §6 item 5 |
| Code | `_collection_rate`: share-weighted average over out-edges; `FirmState.receivables_due` is dated but not per buyer |
| Manuscript | not stated; README *Limitations* "Settlement is approximate" |
| Tests | reference (single buyer, so the two treatments coincide — the reference cannot detect a change here); `test_invariants.py` |

**QUALIFY.** The manuscript does not mention it; if the reviewer thinks
it matters for the published comparison, append to §5: "…and
share-weighted rather than invoice-level recovery" (one line). Otherwise
the README limitation suffices.

**WRONG.** Per-buyer dated ledgers in `FirmState` and `_settle`; the
network-dependent part is outside the reference scope but the single-buyer
case still coincides, so Table 4 wording is unchanged. Means move little,
p95 numbers and the systemic-event frequency move; Table 5 rows 1–3 and
Fig. 2's right panel change.

---

## Q8 — The blockchain scenario as three frictions

| | |
|---|---|
| Spec | §2 *Eligible collateral*; the switch in `ScenarioConfig` |
| Code | `ScenarioConfig.effective_*`; `_eligible_receivables` |
| Manuscript | Abstract; Highlights bullet 3; §1 para 3 "The blockchain switch is precisely a joint movement of these three frictions"; §3 friction sweep and Fig. 2(b)–(c); references [14] and [16] now frame the mechanism |
| Tests | `test_reference.py::test_the_shared_blockchain_switch_is_checked_directly` and the "blockchain switch on" parameterisation; `test_scfsim.py` round-trip |

**QUALIFY.** Add the missing mechanism to §5 as a limitation ("platform
fees and adoption are not modelled", one line) and to spec §2 caveat. §1
para 3 keeps "precisely" only if the reviewer accepts the three as the
*modelled* content of the switch; otherwise "represented as a joint
movement of three frictions".

**WRONG (a fourth friction).** New `ScenarioConfig` field pair
(`x`, `bc_x`) and `effective_x`; enters `_eligible_receivables` or the
cost side; extend the direct switch test to four assertions; add a sweep
to `channels_and_sensitivity.py`; a fifth panel would shrink Fig. 2
below legibility, so report the fourth friction in the text of §3 (two
lines, which exhausts the headroom) or replace panel (b) with a
combined friction panel. Highlights bullet 3 is at 76 characters and
can absorb one more word.

---

## Q9 — What we failed to ask

Work the Q0/Q8 comparison table row by row:

- **"yes"** — no action; note the confirmation in the ledger.
- **"differently"** — treat as a QUALIFY on whichever of Q1–Q7 is
  closest, or as a new spec caveat if none is; manuscript only if it
  bears on the published comparison.
- **"no"** — a mechanism the model lacks. Add it to spec §6 at the rank
  the reviewer's "does it matter" column implies (§6 now has six items,
  led by immediate payables). If it is above item 3, it goes into §5 of
  the manuscript in place of the lowest-ranked limitation currently
  listed ("a single final customer"), keeping the sentence to one line.
  The reviewer packet's Q9 also asks about the anchor-default result
  (§3, "deep-tier financing slows the collapse … leaves banks with a
  sixth of the losses"); a "differently" there is a QUALIFY on that
  sentence. If the
  reviewer marks it as changing the sign of the comparison, it is a WRONG
  with no pre-drafted edit: stop and redesign.

---

## Q10 — Sourcing

Every citation supplied goes into spec §7 next to the convention it
supports, and into the manuscript's reference list only where a §1 or §2
sentence asserts the convention (a reference costs about two lines in
the back matter, outside the body budget; check whether the target
template counts references toward the six pages). The list has room: 16
of the 25 allowed, [14]–[16] being the analytical anchors added in
v0.14.0. If the reviewer disputes that the three frictions are a fair
reduction of the mechanisms in [14] and [16], that is a QUALIFY on §1
para 3, not a sourcing gap.

---


## Producing v1.0.0 from the review

1. Fill the ledger below from the returned packet.
2. Apply all QUALIFY edits (spec first, then manuscript); re-render and
   confirm the body still ends on page 6 with the author block in place.
3. A WRONG on Q3 (recourse) is handled before any other WRONG: it can
   change the direction of the headline comparison, and the edits below
   assume that direction.
4. Apply WRONG edits one at a time, each with its reference mirror or its
   Table 4 exclusion, and run the full suite after each.
5. Re-run both examples in full (`--jobs 0` is identical and faster);
   update Section 3, Table 5, `tests/test_manuscript.py`,
   `docs/REPRODUCTION.md` together; regenerate figures;
   `python docs/gen_api.py`; `python docs/gen_fig1.py` if the package
   layout changed; `python docs/check_release_ready.py` before tagging.
6. Write the `1.0.0` changelog entry: list every verdict and the edit it
   produced, and mark the release as the first with an external review of
   the economics. Bump the version in the seven places
   `tests/test_release_metadata.py` checks; tag; follow `RELEASE.md`.
7. Acknowledge the reviewer in the manuscript if they agreed to it.

## Verdict ledger (empty until the review returns)

| Q | Verdict | Reviewer's reason (one line) | Edit applied | Numbers changed? |
|---|---|---|---|---|
| Q1 | | | | |
| Q2 | | | | |
| Q3 | | | | |
| Q4 | | | | |
| Q5 | | | | |
| Q6 | | | | |
| Q7 | | | | |
| Q8 | | | | |
| Q9 | | | | |
| Q10 | | | | |
