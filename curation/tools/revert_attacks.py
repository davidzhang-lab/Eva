"""
revert_attacks.py — Surgically revert specific attack IDs to a prior git
commit's state. Used during the hardening pass to roll back individual
attacks (e.g. after a randomizer bug fix) without touching the rest of the
library.

What it does:
  For each given attack ID:
  1. Revert the attack's YAML file to <ref> via `git checkout <ref> -- <path>`
  2. In each upstream file (curation/categories/*.py + curation/success_signals.py),
     locate the attack's dict block (by `"id": "<aid>"` marker) and replace
     it with the version from <ref>.

How to run:
  curation/.venv/bin/python curation/tools/revert_attacks.py \\
      --ref c3754cf --ids tm-016,iv-003

After revert, re-run the randomizer with --only-ids to re-randomize cleanly:
  curation/.venv/bin/python curation/tools/randomize_fingerprints.py \\
      --apply --only-ids tm-016,iv-003
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CURATION = ROOT / "curation"
LIBRARY = ROOT / "v1" / "attack-library"


def find_yaml(aid: str) -> Path | None:
    for f in LIBRARY.glob("**/*.yaml"):
        if f.name.startswith(f"{aid}-"):
            return f
    return None


def git_show(ref: str, path: Path) -> str:
    rel = path.relative_to(ROOT)
    return subprocess.check_output(["git", "show", f"{ref}:{rel}"], cwd=ROOT).decode()


def extract_attack_block(text: str, aid: str) -> str | None:
    """Find the dict block for the given attack id and return it as a substring.
    Spans from the line containing `"id": "<aid>"` (or `'id': '<aid>'`) back to
    the opening `{` of that dict, and forward to the matching `}` (paren-balanced)."""
    needle1 = f'"id": "{aid}"'
    needle2 = f"'id': '{aid}'"
    idx = text.find(needle1)
    if idx == -1:
        idx = text.find(needle2)
    if idx == -1:
        return None
    # Walk back to find the opening {
    open_idx = text.rfind("{", 0, idx)
    if open_idx == -1:
        return None
    # Walk forward, counting nested {}
    depth = 0
    i = open_idx
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx:i + 1]
        i += 1
    return None


def revert_in_upstream(ref: str, aid: str, py_path: Path) -> bool:
    if not py_path.exists():
        return False
    old_text = git_show(ref, py_path)
    old_block = extract_attack_block(old_text, aid)
    if old_block is None:
        return False
    cur_text = py_path.read_text()
    cur_block = extract_attack_block(cur_text, aid)
    if cur_block is None:
        return False
    if cur_block == old_block:
        return False
    new_text = cur_text.replace(cur_block, old_block, 1)
    py_path.write_text(new_text)
    return True


def revert_in_signals(ref: str, aid: str) -> bool:
    sig_path = CURATION / "success_signals.py"
    if not sig_path.exists():
        return False
    old_text = git_show(ref, sig_path)
    cur_text = sig_path.read_text()
    needle = f'"{aid}":'
    cur_idx = cur_text.find(needle)
    old_idx = old_text.find(needle)
    if cur_idx == -1 or old_idx == -1:
        return False
    # Each signal is one line: extract from key marker to end-of-line
    cur_eol = cur_text.find("\n", cur_idx)
    old_eol = old_text.find("\n", old_idx)
    if cur_eol == -1 or old_eol == -1:
        return False
    cur_line = cur_text[cur_idx:cur_eol]
    old_line = old_text[old_idx:old_eol]
    if cur_line == old_line:
        return False
    new_text = cur_text[:cur_idx] + old_line + cur_text[cur_eol:]
    sig_path.write_text(new_text)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="Git ref to revert to (e.g. c3754cf)")
    ap.add_argument("--ids", required=True, help="Comma-separated attack IDs")
    args = ap.parse_args()
    ids = [s.strip() for s in args.ids.split(",") if s.strip()]

    for aid in ids:
        print(f"\n--- Reverting {aid} to {args.ref} ---")
        # 1. YAML
        yaml_path = find_yaml(aid)
        if yaml_path:
            rel = yaml_path.relative_to(ROOT)
            subprocess.check_call(["git", "checkout", args.ref, "--", str(rel)], cwd=ROOT)
            print(f"  YAML: {rel} reverted")
        else:
            print(f"  YAML: no match found for {aid}", file=sys.stderr)
        # 2. categories/*.py
        for py_path in (CURATION / "categories").glob("*.py"):
            if py_path.name == "__init__.py":
                continue
            if revert_in_upstream(args.ref, aid, py_path):
                print(f"  upstream: {py_path.relative_to(CURATION)} block reverted")
        # 3. success_signals.py
        if revert_in_signals(args.ref, aid):
            print(f"  upstream: success_signals.py line reverted")


if __name__ == "__main__":
    main()
