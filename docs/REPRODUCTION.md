# Reproduction log for the manuscript numbers

Every number quoted in the SoftwareX manuscript, the script and console
line that produces it, and the value obtained on the release build. The
authors must re-run this in their own environment before submission
(`docs/SUBMISSION_CHECKLIST.md`, *Verification by the authors*); this
file records what they should expect to see. v0.11.0 and v0.12.0 added three
optional mechanisms and closed a gap in the reference implementation;
every number from earlier versions reproduces bit-for-bit, and the block
near the end records the numbers the paper quotes for the relaxed
assumptions.

The first two blocks and the last are also asserted by
`tests/test_manuscript.py` at the printed precision, from scenarios
imported from the example scripts. The friction-sweep and capitalisation
blocks come from the full run of `examples/channels_and_sensitivity.py`,
which takes several minutes and is therefore checked here rather than in
the test suite.

**Release build:** CPython 3.12.3, numpy 2.4.4, networkx 3.6.1,
matplotlib 3.10.8, Linux x86-64, 2026-08-26 (re-run on v0.13.0). Both scripts were run in
full with `MPLBACKEND=Agg` from the repository root.

## Table 5 and Section 3, first example

`python examples/blockchain_switch.py` — 200 matched paths per scenario,
`BASE_SEED = 42`; the script runs both halves of Table 5 (about 30 s).

| Manuscript | Console field | Traditional | Blockchain | Reproduced |
|---|---|---|---|---|
| Mean final default share 55.6% / 26.5% | `mean_default_share` | 0.5555 | 0.2654 | yes |
| Mean cascade beyond the seeds 28.1 / 11.9 | `mean_cascade_size` | 28.1100 | 11.8600 | yes |
| Frequency of systemic events 98.0% / 47.5% | `systemic_event_freq` | 0.9800 | 0.4750 | yes |
| Prose: credit extended "9.7 to 24.8" | `mean_credit_extended` | 9.7434 | 24.7507 | yes |
| Prose: cumulative bank losses "2.29 to 2.59" | `mean_bank_losses` | 2.2916 | 2.5881 | yes |

Right-hand columns of Table 5 (`payables on one-period terms` blocks of the
same script, `firm.payables_delay = 1`, same 200 seeds):

| Manuscript | Console field | Traditional | Blockchain | Reproduced |
|---|---|---|---|---|
| Mean final default share 25.1% / 23.5% | `mean_default_share` | 0.2509 | 0.2349 | yes |
| Mean cascade 11.1 / 10.2 | `mean_cascade_size` | 11.0500 | 10.1550 | yes |
| Frequency of systemic events 39.5% / 25.5% | `systemic_event_freq` | 0.3950 | 0.2550 | yes |
| Prose: "credit drawn falls by five sixths" | `mean_credit_extended` | 1.5934 (from 9.7434: ratio 0.16) | 7.4365 | yes |
| Prose: "gap shrinks from 29 to 2 points" | — | 29.0 → 1.6 | | yes |
| Prose: "cuts the frequency of systemic events by a third" | — | 1 − 0.255/0.395 = 0.35 | | yes |

The last two figures moved from Table 5 into the sentence below it in
v0.10.1 (page budget; see the checklist). Prose: "more than halves the
mean cascade and the frequency of systemic events" (11.86 < 14.06; 0.475
< 0.49); "credit extended rises two and a half times" (24.75 / 9.74 =
2.54). Figure: `example_output.pdf` / `.png` (no longer in the manuscript since v0.11.0; kept in the repository).

## Fig. 2(a) and Section 3, channel decomposition

`python examples/channels_and_sensitivity.py`, block *Channel ablation*
— 100 paths per variant.

| Manuscript | Console line | Value | Reproduced |
|---|---|---|---|
| Counterparty alone 11.9 | `counterparty  alone` | +11.90 | yes |
| Demand alone 7.8 | `demand  alone` | +7.84 | yes |
| Supply alone 1.9 | `supply  alone` | +1.91 | yes |
| Credit crunch alone "essentially nothing" | `credit_crunch  alone` | +0.01 | yes |
| Supply marginal 8.2 (largest) | `supply  marginal` | +8.21 | yes |
| Counterparty marginal 6.2 | `counterparty  marginal` | +6.24 | yes |
| Demand marginal 3.6 | `demand  marginal` | +3.60 | yes |
| Coupled effect 20.6 | `effect of the coupled model` | +20.60 | yes |
| 1.1 firms smaller than the sum of first-order effects | `interaction term` | −1.06 | yes |

## Fig. 2(b)–(c) and Section 3, friction sweeps

Same script, block *Friction sensitivity* — 100 paths per grid point.

| Manuscript | Console line | Value | Reproduced |
|---|---|---|---|
| Traditional baseline "0.55" | `traditional-SCF baseline` | 0.553 | yes |
| Haircut from zero to 0.65: "about 0.27 to roughly 0.46" | `haircut: 0.0->… 0.65->…` | 0.266 → 0.456 | yes |
| Fraud from zero to 0.65: "about 0.27 to roughly 0.46" | `fraud: 0.0->… 0.65->…` | 0.266 → 0.463 | yes |
| Visibility three tiers to one: "raises it to 0.53" | `depth: 1->… 3->…` | 3 → 0.267, 1 → 0.526 | yes |

Full sweep values, for the record:

- haircut: 0.0→0.266, 0.05→0.267, 0.1→0.270, 0.2→0.291, 0.35→0.324, 0.5→0.350, 0.65→0.456
- fraud: 0.0→0.266, 0.05→0.270, 0.1→0.267, 0.2→0.296, 0.35→0.330, 0.5→0.361, 0.65→0.463
- depth: 1→0.526, 2→0.372, 3→0.267

## Fig. 2(d) and Section 3, credit-crunch binding

Same script, block *When does the credit-crunch channel bind?* — 100
paths per point, two variants per capital ratio.

| Manuscript | Console line | Value | Reproduced |
|---|---|---|---|
| "0.34 firms at a capital ratio of 0.20" | `bank capital ratio 0.2` | +0.34 | yes |
| "1.26 at 0.015" | `bank capital ratio 0.015` | +1.26 | yes |

Full series: 0.20→+0.34, 0.12→+0.36, 0.06→+0.43, 0.03→+0.82,
0.015→+1.26. The README's rounded statement ("about 0.3 firms … rising to
about 1.3") and `docs/FINANCIAL_SPEC.md` §5 refer to the same series.

## Section 3, last paragraph: the three relaxed assumptions

Same script, block *Relaxing the default configuration's assumptions* —
100 paths per point; the anchor case replaces the three tier-2 seeds
with a core-enterprise default at the same period (t = 2).

| Manuscript | Console line | Value | Reproduced |
|---|---|---|---|
| Payables on one-period terms: "default share falls from 0.55 to 0.25" | `payables delay 0` vs `1`, traditional | 0.553 → 0.254 | yes |
| "credit drawn falls by four fifths" | same rows, `credit drawn` | 8.8 → 1.8 (ratio 0.20) | yes |
| "the gap between the scenarios shrinks from 29 to 2 points" | `gap` column | +0.286 → +0.021 | yes |
| "still halves the frequency of systemic events (0.45 against 0.24)" | `systemic events`, delay 1 | 0.45 / 0.24 | yes |
| Pricing slope 0.4 "moves the mean default share by less than one point in either scenario" | `pricing slope 0.0` vs `0.4` | traditional 0.553 → 0.553; blockchain 0.267 → 0.269 | yes |
| "0.18 of the chain defaulted by period 10 against 0.33" | `default share ... at t=10` | traditional 0.33; blockchain 0.18 | yes |
| "a sixth of the losses (0.12 against 0.74)" | `bank losses` | traditional 0.74; blockchain 0.12 | yes |
| "ends the chain in both scenarios" | `... at the end` | 1.00 and 1.00 | yes |

Full payables series (traditional / blockchain, mean default share):
0 → 0.553 / 0.267, 1 → 0.254 / 0.233, 2 → 0.233 / 0.223; credit drawn
8.8 / 22.9, 1.8 / 8.2, 1.1 / 5.8; systemic events 0.98 / 0.51,
0.45 / 0.24, 0.31 / 0.26. Full pricing series: 0.0 → 0.553 / 0.267,
0.1 → 0.553 / 0.266, 0.2 → 0.553 / 0.268, 0.4 → 0.553 / 0.269. Credit
extended under the anchor default: 4.6 / 8.8.

## Performance claims in the README

Measured on the release build (best of three, one core): strict mode
costs 25% on the paper's network (0.74 s → 0.92 s per 20 paths); a
40-period path takes 0.05 s at 56 firms, 0.24 s at 280, 0.87 s at 1,000
and 1.74 s at 1,960 — about 20 µs per firm-period, linear in network
size. The README quoted "about 10%" for strict mode from v0.4.0 to
v0.16.0; the checkers have grown since (interest and payables ledgers,
economics layer), and the figure was never re-measured.

## Across Python and dependency versions

Table 5 (both halves), the quick-mode channel decomposition and the
three example scripts were re-run on **Python 3.9.25 with numpy 1.22.4,
networkx 2.8 and matplotlib 3.5.3** — the floor of every version range
declared in `pyproject.toml` — and produced the same numbers as the
release build on Python 3.12 with numpy 2.4, networkx 3.6 and matplotlib
3.10. The `floor` CI job repeats the Table 5 assertion at those versions
on every push. The API reference generator is asserted to produce
byte-identical output on both interpreters.

## Runtime

On the release build, `blockchain_switch.py` took about 30 s (15 s before the
symmetric-terms half was added) and
`channels_and_sensitivity.py` 255 s in full on one core with the test
suite running concurrently (v0.12.0 build; about 4 min before the
relaxed-assumptions block was added), consistent with the manuscript's
"about 30 s and 5 min on one commodity x86-64 core". With
`--jobs 0` on a four-core machine the same run takes under two minutes
and produces the same numbers.

## If a number does not reproduce

The engine is deterministic given the seed, so a mismatch means one of
three things: the scenario in the example script changed (compare
`stressed_base()` with the description in Section 3 of the manuscript);
the model changed (check `CHANGELOG.md` for a *behaviour-changing* entry
and update the paper); or the numerical environment differs in a way
that affects floating-point summation order, which has not been observed
across the CI matrix but should be reported as an issue if it occurs.
