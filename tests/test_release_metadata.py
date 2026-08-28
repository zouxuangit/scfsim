"""The version number is recorded in one place per file format and must
agree everywhere.

Version bumps have been done by hand for nine releases, each time
touching pyproject.toml, the package, CITATION.cff, the README badge line,
the changelog and the submission checklist. The release workflow refuses
a tag that disagrees with the package; this test makes the remaining
files disagree loudly rather than quietly. It runs in the fast layer and
in the release workflow.
"""
import json
import pathlib
import re

import scfsim

ROOT = pathlib.Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_pyproject_matches_the_package():
    m = re.search(r'^version\s*=\s*"([^"]+)"', read("pyproject.toml"), re.M)
    assert m and m.group(1) == scfsim.__version__


def test_citation_file_matches_the_package():
    m = re.search(r"^version:\s*(\S+)", read("CITATION.cff"), re.M)
    assert m and m.group(1) == scfsim.__version__


def test_zenodo_metadata_matches_the_package():
    meta = json.loads(read(".zenodo.json"))
    assert meta["version"] == scfsim.__version__


def test_changelog_leads_with_the_current_version():
    m = re.search(r"^## \[([^\]]+)\]", read("CHANGELOG.md"), re.M)
    assert m and m.group(1) == scfsim.__version__, (
        "the first changelog entry must be the current version")


def test_readme_states_the_current_version():
    assert f"> Version {scfsim.__version__} ·" in read("README.md")


def test_submission_checklist_tags_the_current_version():
    assert f"v{scfsim.__version__}" in read("docs/SUBMISSION_CHECKLIST.md")


def test_version_is_a_release_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+", scfsim.__version__), (
        "no pre-release suffixes: the tag, Zenodo and the manuscript all "
        "quote this string")


def test_api_reference_is_in_sync_and_deterministic():
    """CI fails if ``docs/API.md`` differs from a fresh regeneration, so the
    generator must be deterministic. Until v0.16.0 it rendered dataclass
    fields without a plain default as ``<dataclasses._MISSING_TYPE object
    at 0x...>`` — a memory address that changed on every run — so the check
    would have failed on the first CI run and on every run after it."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen_api", ROOT / "docs" / "gen_api.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    text = gen.render()
    assert " at 0x" not in text, "the API reference contains a memory address"
    assert "_MISSING_TYPE" not in text
    assert text == read("docs/API.md"), (
        "docs/API.md is stale: run 'python docs/gen_api.py' and commit it")
