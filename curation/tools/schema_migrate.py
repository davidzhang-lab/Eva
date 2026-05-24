"""
schema_migrate.py — Eva v1 attack-library schema migration (hardening pass 2026-05-24).

What it does:
  1. Renames `severity:` → `observed_tier:` in every YAML.
  2. Renames the bucket value `baseline-guardrail` → `refused-by-tested-models`.
  3. Parses freeform "mirrors X" text out of the `source:` string into a structured
     `mirrors: [<id>, ...]` list field.
  4. Adds `test_results.niches_tested:` field, backfilled from curation/runs/*.json
     (the actual niches a given attack was run against, regardless of outcome).
     Falls back to `applies_to_niches` with `niches_tested_source: inferred` when
     no run record exists.

How to run:
  /Users/davidzhang/Desktop/Eva/curation/.venv/bin/python \\
    /Users/davidzhang/Desktop/Eva/curation/tools/schema_migrate.py

  Idempotent: re-running on already-migrated YAMLs is a no-op (detected via the
  presence of `observed_tier:` instead of `severity:`).

How to roll back:
  git reset --hard 26c931e  # or whichever commit is the pre-pass snapshot

Mutates: all 151 YAMLs under v1/attack-library/ + curation/save_yaml.py.
"""

import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parent.parent.parent  # Eva/
LIBRARY = ROOT / "v1" / "attack-library"
RUNS = ROOT / "curation" / "runs"

OLD_BUCKET = "baseline-guardrail"
NEW_BUCKET = "refused-by-tested-models"

MIRRORS_RE = re.compile(r"mirrors\s+([a-z]{2}-\d+(?:\s*(?:,|/|and|\&)\s*[a-z]{2}-\d+)*)", re.IGNORECASE)
ID_RE = re.compile(r"[a-z]{2}-\d+", re.IGNORECASE)


def build_tested_map() -> dict[str, set[str]]:
    """attack_id -> set of niches it was run against (from latest tiered runs)."""
    tested: dict[str, set[str]] = defaultdict(set)
    # Group run files by category, pick the latest tiered_*.json per category
    by_cat: dict[str, list[Path]] = defaultdict(list)
    for f in RUNS.glob("*.json"):
        name = f.name
        # data_exfiltration_tiered_2026-...json -> category = "data_exfiltration"
        m = re.match(r"(.+?)_(tiered|cascade)_", name)
        if not m:
            continue
        by_cat[m.group(1)].append(f)
    for cat, files in by_cat.items():
        # Prefer tiered runs; among them, latest by name (timestamp sorts)
        tiered = sorted([f for f in files if "_tiered_" in f.name])
        chosen = tiered[-1] if tiered else sorted(files)[-1]
        try:
            records = json.loads(chosen.read_text())
        except Exception as e:
            print(f"  ! skip {chosen.name}: {e}", file=sys.stderr)
            continue
        for r in records:
            if "attack_id" in r and "niche" in r:
                tested[r["attack_id"]].add(r["niche"])
    return tested


def parse_mirrors(source: str) -> tuple[str, list[str]]:
    """Return (cleaned_source, mirrors_list)."""
    if not source or "mirrors" not in source.lower():
        return source, []
    ids: list[str] = []
    # Extract every attack id after the word "mirrors"
    for m in MIRRORS_RE.finditer(source):
        ids.extend(i.lower() for i in ID_RE.findall(m.group(0)))
    # Strip the mirrors clause from source
    # Strip "mirrors XX-NN [more ids] [trailing descriptors]" greedily up to next
    # punctuation boundary (comma/semicolon) or end of string.
    # Stop greedy match at `,`, `;`, or `)` so we don't eat a closing paren that
    # belongs to outer text (e.g. "Eva-original (hybrid, mirrors X)").
    cleaned = re.sub(
        r"[,;]?\s*mirrors\s+[a-z]{2}-\d+(?:[\s,/&]+(?:and\s+)?[a-z]{2}-\d+)*[^,;)]*",
        "",
        source,
        flags=re.IGNORECASE,
    ).strip(" ,;")
    if not cleaned:
        cleaned = "Eva-original"
    return cleaned, sorted(set(ids))


def migrate_yaml(path: Path, tested_map: dict[str, set[str]], yaml: YAML) -> str:
    """Returns 'migrated', 'skipped', or error msg."""
    data = yaml.load(path)
    if data is None:
        return "skipped:empty"

    # Idempotency check
    if "observed_tier" in data and "severity" not in data:
        return "skipped:already-migrated"

    # 1+2: severity -> observed_tier (with bucket rename)
    if "severity" in data:
        old = data["severity"]
        new = NEW_BUCKET if old == OLD_BUCKET else old
        # Rebuild dict to control key order: replace `severity` in-place
        new_data = {}
        for k, v in data.items():
            if k == "severity":
                new_data["observed_tier"] = new
            else:
                new_data[k] = v
        data = new_data

    # 3: mirrors extraction
    src = data.get("source", "")
    cleaned_src, mirrors = parse_mirrors(src)
    if cleaned_src != src:
        data["source"] = cleaned_src
    if mirrors and "mirrors" not in data:
        # Insert mirrors right after source for readability
        new_data = {}
        for k, v in data.items():
            new_data[k] = v
            if k == "source":
                new_data["mirrors"] = mirrors
        data = new_data

    # 4: niches_tested backfill
    aid = data.get("id")
    tr = data.get("test_results") or {}
    if "niches_tested" not in tr:
        if aid in tested_map and tested_map[aid]:
            tr_new = {"niches_tested": sorted(tested_map[aid])}
        else:
            # Fallback: assume applies_to_niches was the intent
            applies = data.get("applies_to_niches") or []
            tr_new = {
                "niches_tested": list(applies),
                "niches_tested_source": "inferred",
            }
        # Preserve existing keys (niches_succeeded, beats_*) after niches_tested
        for k, v in tr.items():
            if k not in tr_new:
                tr_new[k] = v
        data["test_results"] = tr_new

    # Write back
    with open(path, "w") as f:
        yaml.dump(data, f)
    return "migrated"


def main():
    print(f"Building tested-niches map from {RUNS}...")
    tested_map = build_tested_map()
    print(f"  -> {len(tested_map)} attack_ids found in run records\n")

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 120
    yaml.indent(mapping=2, sequence=4, offset=2)

    counts = defaultdict(int)
    fallbacks: list[str] = []
    files = sorted(LIBRARY.glob("**/*.yaml"))
    for f in files:
        try:
            result = migrate_yaml(f, tested_map, yaml)
            counts[result] += 1
            if result == "migrated":
                # Note attacks that fell back to applies_to_niches
                data = yaml.load(f)
                tr = data.get("test_results") or {}
                if tr.get("niches_tested_source") == "inferred":
                    fallbacks.append(data.get("id", f.name))
        except Exception as e:
            counts["error"] += 1
            print(f"  ERROR on {f.relative_to(LIBRARY)}: {e}", file=sys.stderr)

    print(f"Migrated:  {counts['migrated']}")
    print(f"Skipped:   {counts.get('skipped:already-migrated', 0)} (already migrated) "
          f"+ {counts.get('skipped:empty', 0)} (empty)")
    print(f"Errors:    {counts['error']}")
    print(f"Fallback-to-applies (niches_tested_source=inferred): {len(fallbacks)}")
    if fallbacks[:5]:
        print(f"  examples: {', '.join(fallbacks[:5])}")
    print(f"\nTotal YAMLs touched: {len(files)}")


if __name__ == "__main__":
    main()
