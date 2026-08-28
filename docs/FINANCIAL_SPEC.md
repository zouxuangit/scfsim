# Financial specification of SCFSim

This document states every financial assumption the engine makes, why it
was made, how it compares with the conventions of the supply chain finance
and financial-contagion literature, and what would change if it were
relaxed. It exists because two successive audits of SCFSim each uncovered
a specification error that testing alone had not surfaced — a firm's own
supply capacity not constraining its own deliveries (fixed in v0.2.0), and
bank capital sized against chain sales rather than against the SCF credit
book (fixed in v0.3.0).

**This is a structured self-review, not an independent expert review.**
Maintainers should treat it as the checklist a domain reviewer would work
through, and should obtain such a review before relying on the model for
substantive conclusions.

Two kinds of mechanical enforcement are referenced below:

* **[books]** — an accounting identity enforced by `scfsim.invariants` on
  every period of every strict-mode run.
* **[reference]** — behaviour reproduced by `scfsim.reference`, a second
  implementation of a restricted version of the model written directly
  from this document. Agreement is checked period by period and firm by
  firm, on cash, loan balances, default status and bank write-offs. The
  restriction is a single linear chain without stochastic shocks; the
  whole credit layer, counterparty recovery, payables on terms and the
  anchor default are inside the comparison, multi-buyer share splitting
  is outside it. That scope is **final**, and after v0.12.0 the reference
  stands at 148 of its 150 permitted lines — the next mechanism is
  excluded from the comparison rather than added to it: extending it further would
  require the reference to reproduce the engine's network traversal and
  random-number stream, at which point it would no longer be short enough
  to verify by reading (§7). The two implementations share the
  configuration dataclasses — including the three `effective_*`
  properties that implement the blockchain switch — and nothing else;
  that surface is tested directly, because the comparison is blind to it.
* **[metamorphic]** — a relation enforced by `scfsim.metamorphic`, which
  needs no knowledge of the right answer: it transforms an input in a way
  that must not change the output and checks that the output is unchanged.
  These are the only checks in the project not derived from economics
  someone wrote down in advance.
* **[economics]** — a behavioural property enforced by `scfsim.economics`.
  These are the checks that would have caught the two historical
  specification errors, both of which left the books perfectly balanced;
  each is covered by a regression test that re-injects the original bug
  and asserts the check fires.

Where a parameter has an observable industry counterpart, the sourcing is
given in §7.

---

## 1. The firm's cash flow

| Element | Specification | Rationale and caveat |
|---|---|---|
| Revenue recognition | Sales are booked when delivered; cash arrives `payment_delay` periods later as a receivable. | Standard trade-credit timing. The receivable is the financeable asset, which is what makes SCF meaningful. |
| Variable cost | `cost_ratio × sales`, paid `payables_delay` periods after production (default 0: on delivery). | By default payables are settled immediately while receivables are delayed — the widest working-capital gap a chain can have, and the gap SCF exists to bridge. **Measured (v0.12.0–v0.13.0, Table 5 of the paper, 200 paths):** paying suppliers on the same one-period terms as customers cuts the traditional-SCF default share on the paper's stressed network from 55.6% to 25.1%, cuts credit drawn by five sixths, and shrinks the gap between the scenarios from 29 to 2 points; the frequency of systemic events still falls by a third (39.5% → 25.5%). The headline result is therefore conditional on asymmetric trade-credit terms; that is the condition under which SCF is offered at all, but it must be stated. Ranked first in §6. The collapse of the mean-share gap is robust (table below); the residual systemic-event effect is not, and is specific to the paper's stress level. |
| Fixed cost | `fixed_cost_ratio × baseline_sales`, independent of current volume. | Provides operating leverage: a firm whose orders collapse still bleeds cash. Without it, a demand shock could not by itself cause default. |
| Liquidity shock | With probability `liquidity_shock_prob`, an extra `liquidity_shock_size × baseline_sales` outflow. | A reduced-form stand-in for tax, legal, litigation or capex surprises. Not calibrated. |
| Default trigger | Cash below zero after financing has been requested. | Illiquidity, not insolvency. SCF distress is a cash-flow phenomenon, so this is the appropriate trigger, but it means a firm with a strong balance sheet and no cash still fails. |

**Robustness of the payables measurement** (100 paths, `examples/channels_and_sensitivity.py`
configuration with the listed overrides; mean default share traditional / blockchain,
then the systemic-event frequencies):

| Configuration | On delivery | On one-period terms | Systemic, on delivery | Systemic, on terms |
|---|---|---|---|---|
| Paper (cash 0.15, recovery 0.15) | 0.553 / 0.267, gap +0.286 | 0.254 / 0.233, gap +0.021 | 0.98 / 0.51 | 0.45 / 0.24 |
| Cash ratio 0.25 | 0.472 / 0.254, +0.219 | 0.245 / 0.232, +0.012 | 0.95 / 0.45 | 0.39 / 0.29 |
| Cash ratio 0.35 (package default) | 0.393 / 0.242, +0.150 | 0.236 / 0.227, +0.009 | 0.84 / 0.39 | 0.32 / 0.28 |
| Recovery 0.35 (package default) | 0.527 / 0.258, +0.269 | 0.236 / 0.225, +0.011 | 0.98 / 0.42 | 0.30 / 0.26 |
| Milder shocks (prob 0.03, σ 0.10) | 0.270 / 0.200, +0.070 | 0.199 / 0.197, +0.002 | 0.55 / 0.07 | 0.07 / 0.07 |
| Package defaults, three seeds | 0.192 / 0.186, +0.006 | 0.184 / 0.181, +0.003 | 0.05 / 0.03 | 0.03 / 0.03 |

In every configuration the mean-share gap under symmetric terms is at
most two points. Whether deep-tier financing still reduces systemic
events under symmetric terms depends on the stress level: a third at the
paper's, less or nothing at milder ones.

**[metamorphic]** Every monetary quantity is proportional to the core
enterprise's order volume, and the default trigger is expressed relative to
a firm's own baseline, so the model is dimensionally homogeneous: scaling
the economy by any positive constant leaves every outcome unchanged. The
relation is tested across twenty-one orders of magnitude (1e-9 to 1e12),
which is its declared validity band; outside it, floating-point resolution
rather than the model would decide the outcome.

**[reference]** The cash-flow arithmetic above is reproduced exactly, for
a single linear chain, by an independent implementation in
`scfsim.reference`.

**Known simplification.** There are no inventories, no equity issuance, no
dividends, and no tax. A firm's only liquidity sources are its cash
balance, its collections, and SCF credit.

---

## 2. The receivables-financing facility

| Element | Specification | Rationale and caveat |
|---|---|---|
| Eligible collateral | `receivables × visibility factor × (1 − haircut) × (1 − fraud rate)` | The three frictions are the object of study. Visibility is a step function of tier depth: full within `visibility_depth`, `deep_tier_access` beyond it. |
| Advance | `advance_rate × eligible collateral × bank credit multiplier`, less principal already outstanding. | The cap applies to the **stock** of debt, which is why `loan_maturity` cannot raise peak exposure — see §5. The default of 0.80 sits inside the 70–90% range quoted by receivables-finance providers (§7). **[economics]** A drawing is checked against this ceiling at the moment it is made — a *flow* property. Checking it as a stock property is wrong once `loan_maturity > payment_delay`, because the collateral that secured a drawing is collected while the drawing is still outstanding; the first draft of this check made that mistake and the test suite caught it. |
| Pricing | `interest_rate + pricing_slope × (1 − credit multiplier)`, fixed when the drawing is made and charged with the principal on maturity. | **Exogenous by default** (`pricing_slope = 0`): a flat rate that firms do not respond to. A positive slope prices credit against the *lender's* capital erosion, so it is dearest exactly when the chain is in distress; it is part of the credit-crunch channel and switched off with it. Measured on the paper's stressed network, a slope of 0.4 (a premium of up to forty points per period) moves the mean default share by less than one point in either scenario: the quantity rationing already present dominates, because a borrower whose bank is impaired can draw little at any price. Two gaps remain and are ranked first in §6: the premium is tied to the lender's condition rather than the borrower's, and the rate never enters the firm's decision. |
| Repayment | Principal plus interest on maturity. | Self-liquidating when `loan_maturity = payment_delay`, which is the invoice-discounting case and the default. |
| Rationing | By collateral eligibility and bank capital, never by price. | Consistent with the credit-rationing tradition; inconsistent with markets that clear on price. |

**[books]** A firm's loan ledger reconciles to its loan balance; its
outstanding principal never exceeds its cumulative drawings; interest is
booked only against principal that is owed and never above the maximum
rate; payables are never negative and are empty when costs are paid on
delivery; a defaulted firm carries no loans and owes its suppliers
nothing (its unpaid invoices die with it — the suppliers' side is the
counterparty channel, which is modelled separately).

---

### The contract layer (v0.17.0, from the external review)

Nothing in earlier versions of this document said whether the financing
was with or without recourse, or whose credit the lender ultimately
relied on. The 2026 external review (Q3, archived in
`REVIEW_2026-08.md`) judged that gap WRONG — without it the model cannot
say who risk moved from and to — and `BankConfig.instrument` now closes
it with two contracts:

* **`loan_against_receivables`** (default; the previous engine exactly).
  The firm borrows against its own receivables; the loan is on the
  firm's books and is written down when *the borrower* defaults. Full
  supplier recourse in economic substance; the primary obligor is the
  supplier. The anchor's credit enters only through collateral
  eligibility — this instrument represents *collateral widening*, not
  credit substitution.
* **`receivables_purchase`**. A true sale at
  `advance_rate × (1 − haircut) × (1 − fraud)` per unit of face value,
  pro rata across maturities; visibility gates the saleable face and
  credit tightening scales the bank's willingness to buy. The asset
  leaves the seller's books: a seller default causes no bank loss, a
  buyer default (including the core's) is the bank's loss. Non-recourse
  on buyer credit; the primary obligor is the buyer. This is the
  *credit-substitution* reading of deep-tier financing.

The distinction is not decorative. On the stressed network with the
anchor defaulting at period 10, deep-tier reach cuts bank losses by a
fifth under the loan instrument and multiplies them roughly twentyfold
under the purchase — the sign of the risk-migration result is a property
of the contract, as the review predicted. The default-share comparison
is robust to the instrument. Structures the layer still does not
represent, recorded as open: limited-recourse carve-outs (fraud, reps,
performance), payment undertakings distinct from purchase, dispute and
set-off erosion, and perfection of assignment.

## 3. The bank

| Element | Specification | Rationale and caveat |
|---|---|---|
| Capital base | `capital_ratio × advance_rate × Σ(clients' baseline receivables outstanding)` | Capital is sized against the SCF credit book the bank could plausibly hold. Sizing it against chain sales — as v0.1–v0.2 did — overstates capital by roughly an order of magnitude and renders the credit-crunch channel inert. **[economics]** A bank's capital is checked against its own potential book every period, which is the check that would have caught that error. |
| Loss on default | `exposure × (1 − loan_recovery)`, recognised immediately. | No workout period, no partial recovery over time. |
| Credit tightening | Multiplier `max(0, 1 − losses / initial capital)`, applied to all new lending. | Linear in capital erosion. A regulatory capital constraint would be a step function; the linear form is smoother and easier to interpret but has no regulatory counterpart. |
| Failure | Losses reach initial capital; the bank stops lending to every client. | Deliberately stark, and the only mechanism by which distress jumps between otherwise unconnected supply chains. |
| Funding | Unlimited and free up to the capital constraint. | No deposits, no interbank market, no liquidity risk on the bank side. |

**[reference]** Collateral eligibility, the advance-rate cap, dated
repayment with interest, write-offs on default and capital-driven credit
tightening are all re-derived independently and compared period by period.

**[books]** Recorded exposure equals the borrower's balance; every live
borrowing is recorded by exactly one bank; cumulative write-offs never
exceed cumulative lending net of recovery; the credit multiplier stays in
[0, 1]; a failed bank lends nothing; total drawings equal total supply.

---

## 4. Contagion channels

| Channel | Specification | Caveat |
|---|---|---|
| Counterparty | A defaulted buyer pays `receivable_recovery` on maturing receivables. | Applied as a share-weighted average across a firm's buyers rather than invoice by invoice, so idiosyncratic single-buyer exposure is understated. **[reference]** covered on the chain from v0.11.0; every earlier release omitted it from the reference without saying so — see §7. |
| Supply disruption | A firm's deliveries are capped by its remaining supply capacity, which falls by the input share of each failed supplier. | Capacity never recovers and buyers never re-source. Cascades are therefore upper bounds relative to a chain with active mitigation. **[economics]** Deliveries are checked against the order book scaled by capacity every period — the check that would have caught the v0.1 error, in which lost input supply reduced only what a firm ordered upstream and not what it shipped. |
| Demand contraction | A distressed buyer's reduced sales reduce what it orders upstream. | Order books adjust within the period; there is no inventory buffer or ordering lag, so upstream transmission is faster than in reality. |
| Credit crunch | Capital erosion tightens new lending and, with `pricing_slope > 0`, raises its price; bank failure halts it. | Second order in SCF by construction — see §5. |
| Anchor default | With `core_default_time` set, the core enterprise defaults at that period: it places no further orders and its maturing payables are settled at `receivable_recovery`. | The core is the chain's only customer, so its default ends the chain; the informative quantities are the speed of the collapse and the bank exposure caught on the way down, not the final default share, which is one. **[reference]** covered on the chain. **Working-capital unwind.** A firm whose orders stop also stops paying variable costs before it stops collecting, so over the first few periods a demand collapse *relieves* cash pressure; the fixed-cost bleed dominates afterwards. This is the standard working-capital unwind and not a bug, but it makes the sign of a demand shock horizon-dependent, which the tests take into account. |

---

## 5. Two structural results, not bugs

**Loan tenor cannot raise peak exposure.** The advance rate caps the
*stock* of principal against eligible collateral. Lengthening
`loan_maturity` defers repayment but simultaneously consumes headroom, so
peak exposure is unchanged; only the timing of cash outflows moves. The
parameter is therefore only economically interesting when comparing
invoice discounting (`loan_maturity = payment_delay`) with a revolving
facility whose repayment is deliberately decoupled from invoice
settlement. Users should not expect it to amplify the credit channel.

**The credit-crunch channel is second order.** Because receivables lending
is self-liquidating and collateral-capped, a bank's exposure to any one
borrower is bounded by roughly one invoice cycle. Its marginal
contribution to the cascade rises from about 0.3 firms at a capital ratio
of 0.20 to about 1.3 firms at 0.015. This contrasts with interbank
contagion models, where long-lived exposures make the bank channel first
order, and it is a property of the instrument rather than an artefact of
the implementation.

---

## 6. What a domain reviewer should attack first

`REVIEWER_PACKET.md` turns this section into a structured review form
with a verdict box per question: a 90-minute core review covering items 1
and 2 below, recourse, and the pre-registered expectations comparison,
plus an optional extended pass over the rest. Send that to the reviewer
rather than this document.

The question the packet flagged as having no counterpart here — recourse,
and whose credit is lent against — was judged WRONG by the review and is
now settled by the contract layer in §2: two instruments, two answers,
and the anchor-default result carries the opposite sign under each. Any
claim about risk migrating to banks must name the instrument it is made
under.


Ordered by how much a wrong answer would change the results:

1. **Immediate payables, delayed receivables (§1).** The default sets
   the working-capital gap at its maximum. Payables on terms are now an
   option, and the measurement is large: with symmetric one-period terms
   the two scenarios nearly converge in mean default share at every
   stress level tried (the systemic-event frequency still falls by a
   third at the paper's stress level, less at milder ones). The published comparison
   therefore describes chains in which suppliers are paid later than
   they pay — the chains SCF is offered to — and a reviewer should judge
   whether that is the right population.
2. **Pricing that firms do not respond to, and that tracks the lender
   rather than the borrower (§2).** Lender-based risk pricing is now an
   option and, measured, changes nothing; borrower-based pricing and a
   demand response to price remain the most likely omissions to change
   the sign of a comparative static.
3. **Linear credit tightening (§3).** A regulatory step function would
   produce cliff effects the current form smooths away.
4. **Irreversible distress (§4).** No recovery and no re-sourcing makes
   every cascade an upper bound.
5. **Share-weighted recovery (§4).** Invoice-level tracking would raise
   the variance of outcomes without changing the mean much.
6. **A single final customer (§4).** The core is the only source of
   demand, so its default is total; real chains have several anchors and
   spot markets.


---

## 7. Sourcing and the limits of this document

**Parameters with an observable industry counterpart.** The default
advance rate of 0.80 sits inside the 70–90% range that receivables-finance
providers quote for invoice factoring and discounting; industry sources
consistently place typical advances in that band, with 90%+ reserved for
strong debtor credit. The single-period trade-credit cycle corresponds to
the 30–90 day terms typical of the same market, compressed to one modelled
period. No other parameter is calibrated: cost ratios, cash buffers, shock
frequencies and recovery rates are illustrative values chosen to place the
system under stress, not estimates.

**What is *not* sourced.** The comparisons with "the conventions of the
literature" in §§1–4 are the maintainers' own reading, not a page-by-page
mapping onto specific published models. A reviewer who wants to challenge
a particular convention should expect to supply the citation themselves.
Closing this gap is one of the tasks listed for the domain review in §6.

**Literature anchors (v0.14.0).** Three analytical papers frame the
mechanisms this model simulates, and the manuscript now cites them:
Dong, Qiu and Xu (2023, *M&SOM* 25(6)) study deep-tier financing under
blockchain visibility in a three-tier chain, which is the mechanism the
`ScenarioConfig` switch represents; Kouvelis and Xu (2021, *Management
Science* 67(10)) give a supply chain theory of factoring and reverse
factoring, the instrument whose working-capital logic the payables
measurement of §1 turns on; Chod et al. (2020, *Management Science*
66(10)) analyse the financing benefits of transparency. None of them
models cascades over a network, which is the gap the simulator fills; a
reviewer should say whether the model's frictions (visibility depth,
haircut, fraud) are a fair reduction of the mechanisms those papers
formalise.

**Declared but untested predictions.** `bank.capital_ratio` appears in
`COMPARATIVE_STATICS` with the prediction that better-capitalised banks
weakly reduce defaults, but it is deliberately excluded from the
parameterised test: in the default parameter region its effect size sits
below Monte-Carlo sampling noise, because the credit-crunch channel is
second order (§5). Asserting it would produce a flaky test rather than a
meaningful one. The exemption is recorded here, and in the test that
verifies every other prediction is exercised, so that it cannot quietly
become a blind spot.

**What mechanical checking can and cannot do.** The checks referenced
above catch specification errors whose consequences show up in a single
period as a violated inequality. They cannot catch an error that is
internally consistent *and* produces plausible period-by-period behaviour
— for example a mis-signed elasticity, or a channel that operates through
the wrong economic mechanism while producing similar aggregates. The
comparative-statics tests in `tests/test_economics.py` extend the net to
signed predictions across runs, but they too only test predictions someone
thought to write down.

**A gap in the declared coverage of the differential layer, found in
v0.11.0.** From v0.7.0 to v0.10.1 the reference implementation contained
no counterparty recovery at all — a defaulted buyer's receivables were
collected in full — while the documentation described the comparison as
covering everything on the chain except stochastic shocks. The omission
never produced a disagreement because every differential parameterisation
seeded the deepest tier, whose default hits nobody's receivables, and in
the stressed chains every firm failed in the same period. It was found
when the anchor default was added and the first tier-1 seed was tried.
The lesson is recorded here because it is the kind the audits warned
about: every injected fault (nine at the time) was caught, yet an entire
channel was outside the comparison, because no test asked which mechanisms the
compared trajectory actually exercised. Such "actually exercised" guards
now exist for the credit layer, the counterparty channel, the pricing
premium and the anchor default.

Differential testing against `scfsim.reference` narrows the gap from a
third direction: two implementations written separately from the same
specification will rarely make the same transcription error, so a
disagreement localises a coding slip that no stated property happens to
cover. It cannot, however, detect a misconception shared by the
specification and both implementations — it is a second reading of the
same text, not a second opinion about the economics. Two boundaries of
this layer are fixed and enforced by tests. First, its *scope* stops at
the single linear chain with the full credit layer: covering multi-buyer
share splitting or stochastic shocks would require the reference to
reproduce the engine's network traversal and random-number stream,
making it a copy of the engine rather than an independent check, so a
line-count ceiling on `simulate_reference` turns any further extension
into a deliberate decision. Second, its *independence* is logical, not
physical: both implementations read parameters through the same
configuration dataclasses, including the properties that implement the
blockchain switch, so a fault there would be invisible to the
comparison. The reference is forbidden by test from importing anything
else from the package, and the shared switch is unit-tested directly.

**Where the remaining uncertainty sits.** Between v0.4 and v0.10 no
internal audit found an error in the economics of the model; every
finding was in the verification machinery, and the v0.8 audit found none
there either. Two readings fit that record equally well — the model is
stable, or the checks have converged to a fixed point at which they can
only detect the failure modes their authors imagined — and the stack was
declared complete as of v0.9.0 on the grounds that further checking
could not tell them apart. What did tell them apart, partly, was not
checking but *use*. Making the ranked assumptions switchable
(v0.11–v0.13) showed the headline result to be conditional on asymmetric
trade-credit terms, a qualification the stack could never have raised.
The first tier-1 seed in the differential tests (v0.11) showed that an
entire channel had been outside the comparison. Running the engine on a
user-supplied network (v0.15) exposed two defects that synthetic
networks can never trigger. Regenerating the documentation on a second
interpreter (v0.16) exposed a check that would have failed on its first
run. None of these was found by the five layers; each was found by doing
something the authors had not done before. That confirms the audits'
reading rather than refuting it: the stack finds what its authors
imagined, and the remaining findings come from new use. The one use not
yet made is to show the model to someone who did not build it, which is
what `REVIEWER_PACKET.md` is for — its first step asks the reviewer to
state their own expectations *before* reading this document, precisely
so that the review is not anchored on the questions we already knew to
ask.

The metamorphic relations in `scfsim.metamorphic` are the one layer that
escapes this circularity, because they assert invariance under input
transformations rather than agreement with an expected answer: rescaling
the monetary unit, permuting firm labels, or shortening the horizon must
leave the relevant outputs untouched, whatever those outputs turn out to
be. They still cannot establish that the economics is *right* — only that
the implementation contains no dimensional error, no dependence on
arbitrary labels, and no lookahead. Independent domain review remains
necessary.

---

## 8. Mapping parameters to observables

The parameters are illustrative (§7), but each corresponds to something a
user calibrating the model to a real chain could measure. No values are
asserted here; the table says where each would come from.

| Parameter | Observable counterpart | Where a user would find it |
|---|---|---|
| `firm.payment_delay` | Days sales outstanding of suppliers, in modelled periods | Receivables ageing, or the payment terms on the core's confirmed payables |
| `firm.payables_delay` | Days payables outstanding relative to DSO | Supplier payment terms; 0 reproduces "paid on delivery" |
| `firm.cost_ratio` | 1 − gross margin | Income statements of firms at each tier |
| `firm.fixed_cost_ratio` | Fixed operating cost / sales per period | Income statements (SG&A, depreciation) |
| `firm.initial_cash_ratio` | Cash and equivalents / sales per period | Balance sheets |
| `firm.input_share` | Purchased inputs / sales | Cost of goods sold split |
| `firm.receivable_recovery` | Recovery on trade receivables from insolvent buyers | Insolvency statistics, credit-insurance loss data |
| `bank.advance_rate` | Advance rate on receivables finance | Factoring and SCF platform term sheets (70–90 % is the quoted band, §7) |
| `bank.interest_rate`, `bank.pricing_slope` | Discount rate on confirmed payables and its sensitivity to lender condition | Platform pricing; `pricing_slope` has no direct observable and is a sensitivity parameter |
| `bank.capital_ratio` | Capital against the SCF book | Bank disclosures for the SCF portfolio; regulatory minimum as a floor |
| `bank.loan_recovery` | Recovery on defaulted SCF loans | Bank loss-given-default data for receivables finance |
| `bank.loan_maturity` | Facility tenor in periods | Invoice tenor (self-liquidating) or revolving-facility terms |
| `scenario.visibility_depth`, `deep_tier_access` | Tier depth at which confirmed payables remain verifiable; financeable share beyond it | Platform documentation; survey of which tiers are on-boarded |
| `scenario.haircut`, `fraud_prob` | Verification discount and share of unenforceable receivables | Platform and insurer data; fraud loss statistics |
| `shock.demand_sigma` | Volatility of the core's order volume | Order-book history |
| `shock.liquidity_shock_prob`, `liquidity_shock_size` | Frequency and size of unplanned cash outflows | Not observable directly; a stress assumption |
| `network.firms_per_tier`, `avg_buyers_per_firm` | Tier sizes and supplier multi-sourcing | Supplier maps, customs and invoice data |

