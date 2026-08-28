# Cover note for the domain reviewer

A ready-to-send message to accompany `REVIEWER_PACKET.md`. The one
instruction that matters is the order of work — Q0 before the
specification — and the note is written to make that order hard to miss.
Adapt the salutation and the closing; do not soften the ordering.

---

Subject: 70–100 minutes of your expertise on a supply chain finance model — one unusual request first

Dear [Name],

We are preparing a short software paper for *SoftwareX* on SCFSim, an
open-source simulator of credit-risk contagion through multi-tier supply
chains with receivables financing. The software has been through sixteen
internal rounds, and they reached the same conclusion from two
directions: the internal checks only ever found what their authors
already knew to worry about, and the things found later came from using
the model in new ways — one of which showed our headline result to be
conditional on an assumption we had ranked second. The model's economics
has never been reviewed by someone who works in supply chain finance.
We would like that someone to be you.

The attached packet is a structured review form, estimated at 70–100
minutes, answerable from a specification of about fifteen pages without reading any
code. Nine of its questions ask you to judge specific assumptions and
record a verdict — fine, needs a caveat, or wrong.

**The unusual request is about the first ten minutes.** Before you open
the specification or read the nine questions, the packet asks you (Q0) to
write down, from your own knowledge, which mechanisms and conventions a
credible model of this kind must have. Once you have read our document,
your list will inevitably be shaped by ours, and the one thing your review
can give us that no internal check can is a list that is not. The final
question then asks you to compare the two. We regard that comparison as
the primary output of the review — an item on your list that our
specification does not represent is a finding even if you mark every
other question "fine".

Practically:

- Attached: `REVIEWER_PACKET.md` (the form) and `FINANCIAL_SPEC.md` (the
  specification). Please open the packet first and complete Q0 before
  opening the specification.
- If you want to test a claim numerically, the repository installs with
  `pip install -e .` and two scripts reproduce every number in the paper;
  the packet shows how. This is optional.
- Return the completed packet by [date] if you can. We will add a caveat to
  the paper for every "needs a caveat", revise the model for every "wrong",
  and cite any literature you point us to for conventions we currently
  assert without a source.

We would be glad to acknowledge your review in the paper, or to keep it
confidential, as you prefer.

With thanks,

[Names, affiliation, contact]
