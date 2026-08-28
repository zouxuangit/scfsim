# Release runbook

The steps that turn a commit into the archived, citable artefact the
manuscript points to. Everything mechanical is automated; the steps that
need a human are the ones that need an account.

## Before tagging

1. Bump the version in `scfsim/__init__.py`, `pyproject.toml`,
   `CITATION.cff` (also `date-released`), `.zenodo.json`, the README
   badge line, and the tag in `docs/SUBMISSION_CHECKLIST.md`; add the
   changelog entry at the top of `CHANGELOG.md`.
   `pytest tests/test_release_metadata.py` fails until every file agrees.
2. Run the full suite once: `MPLBACKEND=Agg pytest tests/ -q`. The slow
   layer includes `tests/test_manuscript.py`, so a pass means the numbers
   in the paper still reproduce.
3. If the package layout changed, regenerate the API reference and the
   architecture figure: `python docs/gen_api.py && python docs/gen_fig1.py`.
4. Run `python docs/check_release_ready.py`. It refuses if a `REPLACE-ME`
   placeholder or an invalid ORCID is still in `.zenodo.json`,
   `CITATION.cff` or the README; the release workflow runs the same
   check and stops before publishing, because a Zenodo archive that
   fails *after* the GitHub release exists is awkward to repair.
5. Commit and push `main`; wait for CI to pass on all four jobs.

## Tag and release

```bash
git tag -a v0.17.0 -m "SCFSim v0.17.0"
git push origin v0.17.0
```

The `Release` workflow then checks that the tag matches
`scfsim.__version__`, re-runs the fast suite on the tagged commit, builds
the sdist and wheel, verifies the wheel installs into a clean environment,
and creates a GitHub release with both files attached.

## Zenodo (needs the repository owner's account)

1. Log in to Zenodo with GitHub, open *GitHub* under the account menu,
   and switch the toggle for this repository on. Do this **before** the
   first release you want archived; Zenodo only archives releases
   published after the toggle.
2. `.zenodo.json` supplies title, description, keywords, licence and
   creators. Replace the `REPLACE-ME` creator entry with real names,
   affiliations and ORCID iDs before tagging, or the archive will carry
   the placeholder.
3. Publishing the GitHub release triggers the archive. Within a few
   minutes Zenodo shows a version DOI (for this release) and a concept
   DOI (for all versions). Use the **version** DOI in the manuscript's
   code metadata (C2), since the paper describes this version; use the
   concept DOI in `CITATION.cff` if you want citations to follow future
   releases, otherwise the version DOI there too.

## After the DOI exists

- `CITATION.cff`: fill `doi` and `repository-code`.
- Manuscript: fill C2 with the repository URL plus the tag, and the DOI;
  fill C9 and S8 with the support address; update S2 if a wheel is
  attached to the release ("wheel and source distribution attached to
  the GitHub release" is accurate once the workflow has run).
- `README.md`: replace `scfsim@REPLACE-ME.org`.

Nothing else in the repository references the DOI, so no further edits
are needed for a re-release.
