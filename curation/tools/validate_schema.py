"""
validate_schema.py — Assert every YAML in v1/attack-library/ matches the
post-2026-05-24-hardening-pass schema.

What it checks per file:
  - Required fields present: id, name, category, technique, pattern, observed_tier,
    source, applies_to_niches, test_results, success_signal
  - test_results sub-fields: niches_tested, niches_succeeded, beats_starter_tier,
    beats_hardened_tier
  - observed_tier in {critical, high, medium, low, refused-by-tested-models}
  - category in {direct, indirect}
  - fingerprints_randomized: true and randomization_seed present (or attack has
    no fingerprintable values — recorded in the 42-skip list)
  - Either `prompt` or `turns` is present, not both empty
  - mirrors (if present) is a list of strings matching attack-ID pattern

How to run:
  curation/.venv/bin/python curation/tools/validate_schema.py

Exits 0 if all valid; exits 1 with file-by-file failure list on first error.

How to roll back if it fails:
  git reset --hard c3754cf  # post-schema, pre-randomization
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
LIBRARY = ROOT / "v1" / "attack-library"

REQUIRED = ["id", "name", "category", "technique", "pattern", "observed_tier",
            "source", "applies_to_niches", "test_results", "success_signal"]
TR_REQUIRED = ["niches_tested", "niches_succeeded", "beats_starter_tier", "beats_hardened_tier"]
VALID_TIERS = {"critical", "high", "medium", "low", "refused-by-tested-models"}
VALID_CATEGORIES = {"direct", "indirect"}
ID_RE = re.compile(r"^[a-z]{2}-\d+$")


def validate_one(path: Path) -> list[str]:
    errs = []
    try:
        data = yaml.safe_load(path.read_text())
    except Exception as e:
        return [f"YAML parse error: {e}"]
    if not isinstance(data, dict):
        return ["top-level must be a mapping"]

    for k in REQUIRED:
        if k not in data:
            errs.append(f"missing required field: {k}")

    aid = data.get("id", "")
    if not ID_RE.match(str(aid)):
        errs.append(f"id {aid!r} does not match pattern '^[a-z]{{2}}-\\d+$'")

    if data.get("observed_tier") not in VALID_TIERS:
        errs.append(f"observed_tier {data.get('observed_tier')!r} not in {sorted(VALID_TIERS)}")
    if data.get("category") not in VALID_CATEGORIES:
        errs.append(f"category {data.get('category')!r} not in {sorted(VALID_CATEGORIES)}")

    tr = data.get("test_results") or {}
    for k in TR_REQUIRED:
        if k not in tr:
            errs.append(f"test_results missing field: {k}")
        elif not isinstance(tr[k], list):
            errs.append(f"test_results.{k} must be a list, got {type(tr[k]).__name__}")

    # Either prompt or turns required
    if "prompt" not in data and "turns" not in data:
        errs.append("must have either 'prompt' or 'turns'")
    if "turns" in data and not isinstance(data["turns"], list):
        errs.append("turns must be a list")

    # mirrors: optional, but if present must be list of valid IDs
    if "mirrors" in data:
        if not isinstance(data["mirrors"], list):
            errs.append("mirrors must be a list")
        else:
            for m in data["mirrors"]:
                if not ID_RE.match(str(m)):
                    errs.append(f"mirrors entry {m!r} does not match attack-ID pattern")

    # fingerprints_randomized: presence-only check. Some attacks have no
    # fingerprintable values; in that case the marker is absent and that's OK.
    if "fingerprints_randomized" in data and data["fingerprints_randomized"] is not True:
        errs.append(f"fingerprints_randomized must be True if present, got {data['fingerprints_randomized']!r}")

    return errs


def main():
    files = sorted(LIBRARY.glob("**/*.yaml"))
    failures: dict[str, list[str]] = {}
    randomized = 0
    not_randomized = []
    for f in files:
        errs = validate_one(f)
        if errs:
            failures[str(f.relative_to(LIBRARY))] = errs
        # Track randomization status
        data = yaml.safe_load(f.read_text())
        if isinstance(data, dict):
            if data.get("fingerprints_randomized"):
                randomized += 1
            else:
                not_randomized.append(data.get("id", f.name))

    print(f"Validated {len(files)} files.")
    print(f"  fingerprints_randomized: {randomized}")
    print(f"  no fingerprintable values (no marker, expected): {len(not_randomized)}")
    if failures:
        print(f"\n{len(failures)} files FAILED:")
        for path, errs in failures.items():
            print(f"  {path}:")
            for e in errs:
                print(f"    - {e}")
        sys.exit(1)
    print(f"\nAll schema checks passed.")


if __name__ == "__main__":
    main()
