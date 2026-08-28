# Reviewer packet: financial specification of SCFSim

**For the domain reviewer. Estimated time: 70–100 minutes, of which the first 10 are spent before reading anything else.**

Every internal audit of this project has concluded that independent
review of the financial specification cannot be replaced by internal
work. Between v0.4 and v0.10 no error in the *economics* was found, only
errors in the verification machinery — a record consistent with a stable
model and equally consistent with a self-checking system that had
converged to checking itself. Since then the findings have come from
using the model in new ways rather than from checking it: the assumption
ranked second among the limitations turned out to condition the headline
result (Q2), an entire channel turned out to be outside the differential
comparison, and a user-supplied network exposed defects the synthetic
ones could never trigger. Nothing in that record says the economics is
right; it says the internal checks find what their authors imagined.
Distinguishing a stable model from a self-confirming one is what this
review is for, and it cannot be done from the inside.

**You do not need to read the code.** Everything below is answerable from
`FINANCIAL_SPEC.md` plus, where useful, one number from a simulation run.
Questions are ordered by how much a wrong answer would change the
published results.

**One caveat about this packet itself.** Questions Q1–Q7 and Q9 were
written by the maintainers from `FINANCIAL_SPEC.md`, so they inherit its
blind spots: they can only ask about what we already knew to worry about.
Q0 and Q8 exist to get around that, and Q0 only works if you answer it
*before* reading anything else of ours. Please do.

---

## How to use this packet

0. **Before reading `FINANCIAL_SPEC.md`**, answer Q0 below from your own
   knowledge of supply chain finance (about 10 minutes). Do not skip this
   or defer it: once you have read our specification, your list will be
   anchored on ours, and the one thing this review can give us that no
   internal check can is a list that is not.
1. Read `FINANCIAL_SPEC.md` (about 15 minutes).
2. Work through Q1–Q7 below. For each, record one of:
   - **OK** — the assumption is defensible for the stated purpose;
   - **QUALIFY** — defensible but the paper must state a caveat;
   - **WRONG** — the assumption misrepresents the mechanism.
3. Return to your Q0 list and complete Q8 by comparing it with what the
   specification actually contains. That comparison matters most: the
   whole point of an external review is to surface what the internal
   checks were blind to.

Optional, if you want to test a claim numerically:

```bash
pip install -e .
python examples/blockchain_switch.py            # the headline comparison
python examples/channels_and_sensitivity.py     # channel decomposition
```

---

## Q0. Your expectations, before reading ours

**Answer this first, from your own knowledge, without opening
`FINANCIAL_SPEC.md`.** There are no right answers to check against; the
value of this list lies entirely in its independence from ours.

1. A credible model of credit-risk contagion through a multi-tier supply
   chain with receivables financing must, at minimum, represent the
   following mechanisms (list three to six):

2. It must respect the following accounting or contractual conventions
   (list any that come to mind — settlement timing, collateral treatment,
   recourse, recovery, capital):

3. If a financing platform "extends verifiable payables deep into the
   chain", the effects I would expect it to have are:

4. The single assumption I would look for first, because getting it wrong
   would most change the results, is:

**Notes:**

---

## Q1. Exogenous pricing of credit

**What we do.** By default banks charge a flat per-period rate that does
not vary with borrower risk and does not enter the firm's decision;
credit is rationed by collateral eligibility and bank capital, never by
price. (`FINANCIAL_SPEC.md` §2.) An option prices new drawings against
the *lender's* capital erosion (a premium of up to forty points per
period at the steepest setting we tried); switched on, it moves the mean
default share by less than one point in either scenario, because a
borrower whose bank is impaired can draw little at any price.

**Why it matters most.** Pricing tied to the *borrower's* risk, or a
demand response to price, would make credit dearer exactly when firms
most need it in a way our option does not capture. If that effect is
first-order, our central result — that deep-tier financing reach, not
verification quality, drives the stabilisation — could weaken or reverse.

**Please assess.** Is quantity rationing without borrower-level price
adjustment a defensible representation of supply chain finance in
distress? Does the measured insensitivity to lender-based pricing tell us
anything about borrower-based pricing, or nothing?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG  Notes:

---

## Q2. Payables settled immediately, receivables delayed

**What we do.** By default variable costs are paid in the period of
production while sales are collected `payment_delay` periods later, so
every firm carries the maximum working-capital gap. (§1.) An option pays
suppliers on terms (`payables_delay`); we measured it (Table 5 of the
paper, right-hand columns), and the effect is large: with symmetric
one-period terms the traditional-SCF default share falls from 55.6% to
25.1%, credit drawn falls by five sixths, and the gap between the two
scenarios shrinks from 29 to 2 points — at every stress level we tried
(`FINANCIAL_SPEC.md` §1). Deep-tier financing still cuts the frequency of
systemic events by a third at the paper's stress level, less at milder
ones. Our headline result is therefore a statement about chains in
which suppliers are paid later than they pay.

**Please assess.** Is that the right population — is asymmetric trade
credit the condition under which SCF is offered, so that the default is
the relevant case — or should the paper lead with the symmetric case and
present the default as an upper bound? Either way, is the paper's
conditional statement of the result adequate?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG  Notes:

---

## Q3. Linear credit tightening and the capital base

**What we do.** A bank's lending multiplier falls linearly as losses erode
capital, and capital is sized as `capital_ratio × advance_rate ×
Σ(clients' receivables outstanding)`. (§3.) An earlier version scaled
capital to total chain sales instead; the resulting overstatement of about
one order of magnitude made the credit-crunch channel inert.

**Please assess.** Is the current base the right one? Would a regulatory
step function rather than a linear taper produce cliff effects that
materially change the cascade?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG  Notes:

---

## Q4. Self-liquidating lending and the second-order credit channel

**What we report.** Because receivables lending is repaid when the invoice
settles and is capped by eligible collateral, bank exposure to any one
borrower is bounded by roughly one invoice cycle. We conclude the
credit-crunch channel is *structurally* second-order in SCF — unlike
interbank contagion, where exposures are long-lived — and show its
marginal contribution rising from 0.34 firms at a capital ratio of 0.20 to
1.26 at 0.015.

**Please assess.** Is that structural claim correct, or an artefact of
modelling only invoice discounting? Revolving SCF facilities exist; we
argue tenor cannot raise peak exposure because the advance rate caps the
*stock* of debt (§5). Is that argument sound?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG  Notes:

---

## Q5. Irreversible distress

**What we do.** Defaulted firms never recover, buyers never re-source from
surviving suppliers, and lost supply capacity is never rebuilt. (§4.)

**Please assess.** We describe our cascades as upper bounds relative to a
chain with active mitigation. Is "upper bound" the right characterisation,
or does no-re-sourcing distort the *relative* comparison between the two
financing scenarios rather than just its level?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG  Notes:

---

## Q6. Share-weighted recovery instead of invoice-level tracking

**What we do.** Recovery on receivables is applied as a share-weighted
average across a firm's buyers rather than invoice by invoice. (§4.)

**Please assess.** We expect this to understate the variance of outcomes
while leaving the mean roughly right. Is that the correct intuition?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG  Notes:

---

## Q7. The blockchain scenario as three frictions

**What we do.** "Blockchain-enabled deep-tier financing" is represented as
a joint movement of exactly three parameters: financing visibility depth,
verification haircut, and expected fraud rate. (§2, and the switch in
`ScenarioConfig`.)

**Please assess.** Do these three capture what the mechanism literature
claims a blockchain SCF platform changes? What is missing — and would
including it change the finding that visibility depth dominates the other
two?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG  Notes:

---

## Q8. What did we fail to ask?

Our verification stack has five layers, and every one of them tests a
property somebody wrote down in advance. This question, together with Q0,
is the only part of the review that can reach what none of them can.

**Go back to your Q0 list.** For each item on it, record whether the
specification represents it, represents it differently from what you
expected, or does not represent it at all. Anything in the last two
categories is a finding, whether or not it appears in Q1–Q7.

| Your Q0 item | In the spec? (yes / differently / no) | Does it matter for the published comparison? |
|---|---|---|
| | | |
| | | |
| | | |

Further prompts, if useful: Is there an accounting convention we have
silently assumed? Is any parameter default implausible enough to matter?
Is there a mechanism you did *not* list in Q0 but now notice is missing?
The model now lets the core enterprise default (§4): we find that
deep-tier financing then slows the collapse and, because lending is
self-liquidating, leaves banks with *less* exposure than traditional
SCF — is that what you would expect of an anchor default under a
blockchain platform, or does it reveal a missing mechanism?

**Notes:**

---

## Q9. Sourcing gaps we know about

`FINANCIAL_SPEC.md` §7 states that our comparisons with "the conventions
of the literature" are our own reading, not a page-by-page mapping onto
published models. Only the advance rate is sourced against observable
practice (70–90%; our default is 0.80). The paper now cites three
analytical anchors — Dong, Qiu and Xu (2023) on blockchain-enabled
deep-tier financing, Kouvelis and Xu (2021) on factoring and reverse
factoring, Chod et al. (2020) on transparency and financing — and we
would value your view on whether our three frictions are a fair
reduction of the mechanisms they formalise, and what we have missed.

**If you can supply citations for any convention we assert, please note
them here — they would go directly into the paper.**

**Notes:**

---

## Returning the review

Send the completed packet to the maintainers, or open an issue. If any
answer is **WRONG**, please say whether you consider the affected result
publishable with a caveat or not publishable as it stands.
