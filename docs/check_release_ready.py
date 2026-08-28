"""Pre-tag check: refuse a release that would fail at Zenodo.

    python docs/check_release_ready.py

The release workflow runs the same checks; this lets the authors run them
before pushing a tag. Exit status 0 means the metadata is release-ready.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def orcid_ok(orcid: str) -> bool:
    digits = orcid.replace("-", "")
    if not re.fullmatch(r"\d{15}[\dX]", digits) or orcid == "0000-0000-0000-0000":
        return False
    total = 0
    for d in digits[:-1]:
        total = (total + int(d)) * 2
    check = (12 - total % 11) % 11
    return digits[-1] == ("X" if check == 10 else str(check))


def problems() -> list:
    bad = []
    meta = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    for c in meta.get("creators", []):
        if "REPLACE-ME" in json.dumps(c):
            bad.append(f".zenodo.json: placeholder creator {c}")
        if c.get("orcid") and not orcid_ok(c["orcid"]):
            bad.append(f".zenodo.json: invalid ORCID {c['orcid']!r}")
    for name in ("CITATION.cff", "README.md"):
        if "REPLACE-ME" in (ROOT / name).read_text(encoding="utf-8"):
            bad.append(f"{name}: REPLACE-ME left in")
    return bad


if __name__ == "__main__":
    found = problems()
    if found:
        print("not release-ready:\n  " + "\n  ".join(found))
        sys.exit(1)
    print("release-ready: no placeholders, ORCIDs valid")
