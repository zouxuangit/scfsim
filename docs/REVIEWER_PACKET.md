# Reviewer packet: financial specification of SCFSim

**For the domain reviewer.**

**Time.** The core review is Q0–Q3 plus Q9 and takes about 90 minutes.
The full packet adds Q4–Q8 and Q10 and takes about two and a half to
three hours. **If you have only 90 minutes, do the core review and
stop** — a careful core review is worth much more to us than a hurried
complete one, because we cannot tell a considered "OK" from a rushed one,
and a rushed one that reads as considered is worse than no answer.

Every internal audit of this project has concluded that independent
review of the financial specification cannot be replaced by internal
work. Between v0.4 and v0.10 no error in the *economics* was found, only
errors in the verification machinery — a record consistent with a stable
model and equally consistent with a self-checking system that had
converged to checking itself. Since then the findings have come from
using the model in new ways rather than from checking it: the assumption
we rank first among the limitations turned out to condition the headline
result (Q1), an entire channel turned out to be outside the differential
comparison, and a user-supplied network exposed defects the synthetic
ones could never trigger. Nothing in that record says the economics is
right; it says the internal checks find what their authors imagined.
Distinguishing a stable model from a self-confirming one is what this
review is for, and it cannot be done from the inside.

**You do not need to read the code.** Everything below is answerable from
`FINANCIAL_SPEC.md` plus, where useful, one number from a simulation run.
Questions are ordered by how much a wrong answer would change the
published results, following §6 of the specification.

**Two caveats about this packet itself.**

Q1–Q8 and Q10 were written by the maintainers from `FINANCIAL_SPEC.md`,
so they inherit its blind spots: they can only ask about what we already
knew to worry about. Q0 and Q9 exist to get around that, and Q0 only
works if you answer it *before* reading anything else of ours.

Several questions end with a collapsed **"What we expect, and what we
have measured"** block. It is folded away on purpose. Please form your
own view and write it down before opening it — in earlier drafts we
stated our expectation up front, which invited agreement rather than
judgement.

---

## About you

Two minutes, and it changes how we weight everything below. Approximate
answers are fine.

1. Your work is mainly: ☐ academic ☐ banking / financial institution
   ☐ SCF platform or fintech ☐ corporate treasury or procurement
   ☐ other: ______

2. The markets or programmes you know best (e.g. European reverse
   factoring, Chinese receivables-confirmation platforms, asset-based
   lending, export factoring):

3. Roughly how much of your view below comes from practice as opposed to
   the literature?

4. Anything you would want disclosed if we cite your review:

**Attribution.** We would be glad to acknowledge you in the paper, or to
keep the review confidential — your choice, and you can decide after
seeing what you wrote. There is a box for it at the end. Nothing here is
published without your say-so.

---

## How to use this packet

0. **Before reading `FINANCIAL_SPEC.md`**, answer Q0 below from your own
   knowledge of supply chain finance (about 10 minutes). Do not skip this
   or defer it: once you have read our specification, your list will be
   anchored on ours, and the one thing this review can give us that no
   internal check can is a list that is not.
1. Read `FINANCIAL_SPEC.md` (about 15 minutes).
2. Work through the questions. For each, record one of:
   - **OK** — the assumption is defensible for the stated purpose;
   - **QUALIFY** — defensible but the paper must state a caveat.
     *Please draft the caveat sentence you would want to see.* If you
     leave it to us, we will write it more gently than you would;
   - **WRONG** — the assumption misrepresents the mechanism.

   Where you are unsure, say what would settle it. "I would need to see
   X" is a useful answer and we can often produce X.
3. Return to your Q0 list and complete Q9 by comparing it with what the
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

# Core review

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

## Q1. Payables settled immediately, receivables delayed

**What we do.** By default variable costs are paid in the period of
production while sales are collected `payment_delay` periods later, so
every firm carries the maximum working-capital gap. Paying suppliers on
terms is available as an option (`firm.payables_delay`). (§1.)

**Please assess.** Is the asymmetric case the right population — is
asymmetric trade credit the condition under which SCF is offered, so that
our default is the relevant case — or should the paper lead with the
symmetric case and present the asymmetric one as an upper bound? What
would you expect symmetric terms to do to a comparison between two
financing technologies?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG

**If QUALIFY, the caveat you would want in the paper:**

**Notes:**

<details>
<summary><b>What we expect, and what we have measured</b> — open after answering</summary>

We rank this first in §6 because we measured it and the effect is large.
With symmetric one-period terms the traditional-SCF default share on the
paper's stressed network falls from 55.6% to 25.1%, credit drawn falls by
five sixths, and the gap between the two scenarios shrinks from 29 points
to 2 — at every stress level we tried (Table 5 of the paper, right-hand
columns; `FINANCIAL_SPEC.md` §1). Deep-tier financing still cuts the
frequency of systemic events by a third at the paper's stress level, less
at milder ones. Our headline result is therefore a statement about chains
in which suppliers are paid later than they pay, and the paper says so.
The open questions are whether that is the right population to publish
on, and whether our conditional statement of the result is adequate.
</details>

---

## Q2. Exogenous pricing of credit

**What we do.** By default banks charge a flat per-period rate that does
not vary with borrower risk and does not enter the firm's decision;
credit is rationed by collateral eligibility and bank capital, never by
price. An option prices new drawings against the *lender's* capital
erosion. (§2.)

**Please assess.** Is quantity rationing without borrower-level price
adjustment a defensible representation of supply chain finance in
distress? In the programmes you know, does the price of receivables
finance move with the borrower's own condition, with the anchor's, or
barely at all — and does a supplier ever decline the financing on price?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG

**If QUALIFY, the caveat you would want in the paper:**

**Notes:**

<details>
<summary><b>What we expect, and what we have measured</b> — open after answering</summary>

Lender-based pricing exists as an option (`bank.pricing_slope`); at the
steepest setting we tried — a premium of up to forty points per period —
it moves the mean default share by less than one point in either
scenario, because a borrower whose bank is impaired can draw little at
any price. We read that as quantity rationing dominating, but it is
evidence about *lender*-based pricing only.

The gap we are most worried about, and rank second in §6: pricing tied to
the *borrower's* risk, and any demand response to price, would make
credit dearer exactly when firms most need it in a way our option does
not capture. If that effect is first-order, our central result — that
deep-tier financing *reach*, not verification quality, drives the
stabilisation — could weaken or reverse. So the thing we most want to
know is whether our measured insensitivity to lender-based pricing tells
you anything about borrower-based pricing, or nothing at all.
</details>

---

## Q3. Where the loss lands: recourse, and whose credit is lent against

**What we do.** A firm borrows against its own eligible receivables and
the loan sits on that firm's books. When *that firm* defaults, its bank
writes the exposure down by `1 − loan_recovery`. The core enterprise's
credit enters only through *collateral eligibility* — how deep confirmed
payables are visible, and at what haircut — and never through where a
loss ultimately falls. Buyer non-payment reaches the supplier separately,
as a recovery rate applied to receivables. (§2, §4.)

**This question is not in `FINANCIAL_SPEC.md`.** The word "recourse" does
not appear in it. We noticed the gap while preparing this packet and have
deliberately not settled it internally first, so that your answer is not
anchored on ours.

**Please assess.**

1. Is the arrangement above best described as with-recourse or
   non-recourse, and does the distinction matter for contagion?
2. The mechanism literature on blockchain deep-tier financing generally
   describes the anchor's credit being *substituted* for the supplier's.
   In our model the anchor's credit changes how much a supplier can
   borrow but not who bears the loss when the supplier fails. Is that
   faithful, an omission, or a different product altogether?
3. If it is an omission: would representing it change the *direction* of
   the comparison between traditional and deep-tier financing, or only
   its size?
4. In the programmes you know, who actually carries the credit risk — the
   bank on the anchor, the bank on the supplier, or the supplier itself
   through a recourse clause? Does it differ with tier depth?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG

**If QUALIFY, the caveat you would want in the paper:**

**Notes:**

---

## Q9. What did we fail to ask?

*(Numbered Q9 to keep the extended questions in sequence, but it is part
of the core review — please do it even if you stop here.)*

Our verification stack has five layers, and every one of them tests a
property somebody wrote down in advance. This question, together with Q0,
is the only part of the review that can reach what none of them can.

**Go back to your Q0 list.** For each item on it, record whether the
specification represents it, represents it differently from what you
expected, or does not represent it at all. Anything in the last two
categories is a finding, whether or not it appears elsewhere in this
packet.

| Your Q0 item | In the spec? (yes / differently / no) | Does it matter for the published comparison? |
|---|---|---|
| | | |
| | | |
| | | |
| | | |

Further prompts, if useful:

- Is there an accounting convention we have silently assumed?
- Is any parameter default implausible enough to matter?
- Is there a mechanism you did *not* list in Q0 but now notice is
  missing?
- The model lets the core enterprise default (§4): we find that deep-tier
  financing then slows the collapse and, because lending is
  self-liquidating, leaves banks with *less* exposure than traditional
  SCF. Is that what you would expect of an anchor default under a
  deep-tier platform, or does it reveal a missing mechanism?

**Notes:**

---

**If you are stopping at 90 minutes, stop here** and return the packet. An
incomplete packet with four considered answers is exactly what we asked
for. The questions below are genuinely lower-stakes.

---

# Extended review

## Q4. Linear credit tightening and the capital base

**What we do.** A bank's lending multiplier falls linearly as losses erode
capital, and capital is sized as `capital_ratio × advance_rate ×
Σ(clients' receivables outstanding)`. (§3.)

**Please assess.** Is that capital base the right one for a receivables
finance book? Would a regulatory step function rather than a linear taper
produce cliff effects that materially change the cascade?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG

**If QUALIFY, the caveat you would want in the paper:**

**Notes:**

<details>
<summary><b>What we expect, and what we have measured</b> — open after answering</summary>

An earlier version scaled capital to total chain sales instead; the
resulting overstatement of about an order of magnitude made the
credit-crunch channel inert, and a regression test now re-injects that
error. We believe the current base is right and the taper shape is
second-order — but the base is a mechanism we have already got wrong
once, which is why it is in the packet at all.
</details>

---

## Q5. Self-liquidating lending and the second-order credit channel

**What we report.** Because receivables lending is repaid when the invoice
settles and is capped by eligible collateral, we argue bank exposure to
any one borrower is bounded by roughly one invoice cycle, and conclude
that the credit-crunch channel is *structurally* second-order in SCF —
unlike interbank contagion, where exposures are long-lived. (§5.)

**Please assess.** Is that structural claim correct, or an artefact of
modelling only invoice discounting? Revolving SCF facilities exist; we
argue tenor cannot raise peak exposure because the advance rate caps the
*stock* of debt. Is that argument sound?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG

**If QUALIFY, the caveat you would want in the paper:**

**Notes:**

<details>
<summary><b>What we expect, and what we have measured</b> — open after answering</summary>

We measure the channel's marginal contribution rising from 0.34 firms at
a bank capital ratio of 0.20 to 1.26 at 0.015. We present the structural
claim as a finding of the paper rather than an assumption, which is
exactly why we would like it attacked: it is the one place where we
generalise from our model to supply chain finance as such.
</details>

---

## Q6. Irreversible distress

**What we do.** Defaulted firms never recover, buyers never re-source from
surviving suppliers, and lost supply capacity is never rebuilt. (§4.)

**Please assess.** We describe our cascades as upper bounds relative to a
chain with active mitigation. Is "upper bound" the right
characterisation, or does no-re-sourcing distort the *relative*
comparison between the two financing scenarios rather than just its
level?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG

**If QUALIFY, the caveat you would want in the paper:**

**Notes:**

---

## Q7. Share-weighted recovery instead of invoice-level tracking

**What we do.** Recovery on receivables is applied as a share-weighted
average across a firm's buyers rather than invoice by invoice. (§4.)

**Please assess.** What does this cost us, and does it bear on the
published comparison or only on the dispersion of outcomes?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG

**If QUALIFY, the caveat you would want in the paper:**

**Notes:**

<details>
<summary><b>What we expect</b> — open after answering</summary>

We expect this to understate the variance of outcomes while leaving the
mean roughly right, which would make it a limitation for the
systemic-event frequency and the p95 figures but not for the mean default
share. We have not measured it: the differential reference uses a single
buyer, where the two treatments coincide, so that layer is blind to it.
</details>

---

## Q8. The blockchain scenario as three frictions

**What we do.** "Blockchain-enabled deep-tier financing" is represented as
a joint movement of exactly three parameters: financing visibility depth,
verification haircut, and expected fraud rate. (§2, and the switch in
`ScenarioConfig`.)

**Please assess.** Do these three capture what the mechanism literature
claims a blockchain SCF platform changes? What is missing — and would
including it change the finding that visibility depth dominates the other
two?

**Verdict:** ☐ OK ☐ QUALIFY ☐ WRONG

**If QUALIFY, the caveat you would want in the paper:**

**Notes:**

<details>
<summary><b>What we expect</b> — open after answering</summary>

Our friction sweep finds visibility depth dominating the other two by a
wide margin, and the paper leads on that. Candidates we are aware of and
do not model: platform fees, adoption and onboarding frictions, the legal
enforceability of a confirmed payable, and any change in the anchor's own
incentive to confirm. We do not know which of these, if any, would change
the ranking.
</details>

---

## Q10. Sourcing gaps we know about

`FINANCIAL_SPEC.md` §7 states that our comparisons with "the conventions
of the literature" are our own reading, not a page-by-page mapping onto
published models. Only the advance rate is sourced against observable
practice (70–90%; our default is 0.80). The paper cites three analytical
anchors — Dong, Qiu and Xu (2023) on blockchain-enabled deep-tier
financing, Kouvelis and Xu (2021) on factoring and reverse factoring,
Chod et al. (2020) on transparency and financing — and we would value
your view on whether our three frictions are a fair reduction of the
mechanisms they formalise, and what we have missed.

**If you can supply citations for any convention we assert, please note
them here — they would go directly into the paper.**

**Notes:**

---

## Returning the review

Send the completed packet to the maintainers, or open an issue.

- If any answer is **WRONG**, please say whether you consider the
  affected result publishable with a caveat or not publishable as it
  stands.
- **Attribution:** ☐ acknowledge me by name ☐ keep the review
  confidential ☐ ask me again once you have acted on it

Thank you. If it helps to know where this goes: every QUALIFY becomes a
caveat in the paper, every WRONG becomes either a model change or a
withdrawn claim, and the changelog entry for v1.0.0 will list each
verdict against the edit it produced.
