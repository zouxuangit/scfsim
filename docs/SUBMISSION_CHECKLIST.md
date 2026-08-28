# SoftwareX submission checklist

Items the maintainers must complete before submitting; each replaces a
`REPLACE-ME` placeholder somewhere in the repository or the manuscript.
The internal work is complete as of v0.16.3: every item below is either
an action only the authors can take, or one that depends on the outcome
of the independent domain review. Where a runbook or a ready-made
document exists for an item, it is named.

## Repository and archiving

- [ ] Create the public GitHub repository and push `main`; confirm the
      first CI run passes.
- [x] Fill the real author name, affiliation and ORCID in `.zenodo.json`
      **before** tagging, and switch the Zenodo–GitHub toggle on for the
      repository (`docs/RELEASE.md`, *Zenodo*). `python docs/check_release_ready.py`
      confirms no placeholder is left and every ORCID checksum is valid;
      the release workflow refuses to publish otherwise. Name and affiliation
      are filled; **the ORCID field is currently omitted** because none was
      supplied. The checker passes without it, but register an iD and add
      it before tagging if you want the archive to carry one.
- [ ] Tag the release: `git tag -a v0.16.3 -m "SCFSim v0.16.3" && git push origin v0.16.3`.
      The `Release` workflow builds and publishes the GitHub release;
      Zenodo mints the DOI from it.
- [ ] Back-fill the DOI: `repository-code` and `doi` in `CITATION.cff`,
      C2 in the manuscript (`docs/RELEASE.md`, *After the DOI exists*).
- [x] Replace the support address `scfsim@REPLACE-ME.org` in `README.md`.
- [ ] Confirm the first CI run passes on all four jobs — the fast suite
      on all nine matrix entries (especially Windows), the floor job
      (Python 3.9 with the minimum dependency versions, verified locally
      in v0.16.0), the slow suite, and the docs-and-examples job (whose
      API-reference check would have failed on every run before v0.16.0;
      it is now covered by a local test).

## Manuscript

- [ ] Migrate the full text into the current official SoftwareX OSP
      template; do not submit the draft layout.
- [ ] Re-check the page count after migration. **The body has no
      headroom, and the author block is part of the budget.** v0.10.1
      found that the one-line author placeholder used in every earlier
      page check hid about five lines: a realistic block (three authors,
      two affiliations, corresponding e-mail, ORCIDs) pushed the whole
      Conclusions section onto page 7. The manuscript now carries a
      placeholder block of that length, and the first two contingency
      cuts have been applied to pay for it (the code listing is six
      lines; Table 5 has three rows, its last row folded into the
      sentence below it). With those in place the body ends on page 6
      with about two lines to spare in the draft layout. If the
      template is less economical, or the author block is longer than
      five lines, one cut remains: merge the two examples into one by
      cutting the friction sweep (Fig. 2b–c) and keeping the channel
      decomposition and the capitalisation panel; the sweep result is
      then stated in one sentence with the repository as its source.
      (v0.11.0 used the previous cut — the headline figure was dropped
      and Table 5 kept — to pay for the paragraph on the two relaxed
      limitations; the figure remains in the repository as
      `example_output.pdf`.)
      Do not cut the ranked limitations in Section 5; they were restored
      in v0.8.0 at a reviewer-visible cost and are the honest
      counterweight to the Impact section. Each QUALIFY caveat from the
      domain review costs up to one further line; `docs/REVIEW_INTEGRATION.md`
      pre-drafts each one against this budget.
- [ ] If a reviewer reports that the four-row functionality table is hard
      to scan, split F1 and F2 back into two rows each; the six-row
      version exists in the v0.7.0 manuscript.
- [ ] Check whether the SoftwareX template counts the reference list
      toward the page limit. The body ends on page 6; since v0.14.0 the
      sixteen references run onto a seventh back-matter page in the
      draft layout. If references count, the three references added in
      v0.14.0 ([14]–[16]) are the ones to shorten (drop the DOI URLs
      first, which the template's reference style may not require).
- [ ] Fill code metadata C2 and C9 and software metadata S8 with the real
      repository URL, DOI and support email.
- [ ] Fill the CRediT statement per author; add author names,
      affiliations, ORCID iDs and acknowledgements.
- [ ] Replace the raster figures with the vector versions already present:
      `docs/fig1_architecture.pdf` and `channels_and_sensitivity.pdf`.
- [ ] Reference [2] (Li et al., IEEE TEM 2024): the article exists
      (IEEE Xplore document 10432773) but its DOI, volume and pages could
      not be cross-checked without a subscription in v0.10.0. Confirm
      the DOI `10.1109/TEM.2024.3364832` and add volume and pages if the
      article has been assigned to an issue. References [3] and [12]
      were confirmed in full; [14], [15] and [16] (added in v0.14.0)
      were confirmed against the publisher's pages and indexes (journal,
      volume, issue, pages, DOI); [1], [4]–[11] and [13] are
      long-established and were checked for internal consistency only —
      spot-check one or two against the publisher's page.
- [ ] Native-speaker proofread. A language and typography pass was done
      in v0.10.0 (dashes, superscripts, tightened sentences); what
      remains is a native speaker's read for idiom.

## Independent domain review

- [ ] Send `docs/REVIEWER_PACKET.md` and `docs/FINANCIAL_SPEC.md` to a
      supply chain finance researcher or practitioner, using
      `docs/REVIEWER_INVITATION.md` as the cover note. Every internal
      audit of this project has listed this as the one step internal work
      cannot replace, and the last two concluded that the internal
      verification stack has reached the point at which it can no longer
      tell a stable model from a self-confirming one. The cover note asks
      the reviewer to complete Q0 before reading anything else; that
      ordering is what makes the review independent.
- [ ] Before acting on the review, re-read the quoted manuscript anchors
      in `docs/REVIEW_INTEGRATION.md` against the manuscript you are
      about to edit. They were last synchronised with the v0.16.1 text;
      six manuscript versions between v0.10.1 and v0.16.1 had left eight
      of its fourteen quoted anchors pointing at sentences that no longer
      existed, which a later reader would not have noticed.
- [ ] Record the verdicts in the ledger at the end of
      `docs/REVIEW_INTEGRATION.md`, which maps every question to the
      specification section, code, manuscript sentences, tests and page
      cost it touches and pre-drafts the caveat for each QUALIFY. Add the
      caveat for every QUALIFY and revise the model for every WRONG. Any
      model revision must keep `tests/test_manuscript.py` passing or be
      accompanied by the corresponding edits to Section 3 and Table 5.
- [ ] Fold any citations the reviewer supplies into
      `docs/FINANCIAL_SPEC.md` §7, which currently sources only the
      advance rate against observable practice.
- [ ] Treat the Q0/Q8 comparison as the primary output of the review: an
      item on the reviewer's own list that the specification does not
      represent is a finding even if every verdict in Q1–Q7 is OK.

## Verification by the authors

- [ ] Run `pip install -e .[dev] && MPLBACKEND=Agg pytest tests/ -q` and
      confirm all tests pass in your own environment. The slow layer
      includes `tests/test_manuscript.py`, which re-runs the headline
      comparison and the channel decomposition and asserts every number
      quoted in Section 3 and Table 5 at the printed precision; a pass
      there is the reproducibility check the previous checklists asked
      you to perform by hand.
- [ ] Run both scripts in `examples/` once in full and confirm the
      figures regenerate; the friction-sweep and capitalisation numbers
      of Fig. 2(b)–(d) are printed to the console and are checked against
      the manuscript in `docs/REPRODUCTION.md`, not by the test suite,
      because the full sweep takes several minutes.
- [ ] Regenerate the API reference: `python docs/gen_api.py`.
- [ ] Read and take responsibility for the generative-AI declaration: this
      software and the manuscript draft were produced with AI assistance,
      and the authors are accountable for their correctness.
