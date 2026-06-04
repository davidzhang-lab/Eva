"""
test_judge_calibration.py — verify the runtime judge in v1/eva/judge.py agrees
with the curation judge (curation/pipeline.py) on the actual rounds we ran
during the 14-winners hardening pass.

Pass threshold: ≥90% agreement on the outcome field.

Data sources:
  - curation/runs/*_tiered_*.json: per-round responses (response_text + tool_calls)
    AND the curation judge's verdict (outcome + reasoning) for each round.
  - v1/attack-library/**/*.yaml: attack metadata (success_signal, technique, prompt).

What we re-judge: ONLY rounds belonging to the 14 winners. Other attacks weren't
re-tested in the hardening pass, so their stored verdicts predate the latest
methodology and aren't reliable as ground truth.

Run:
  curation/.venv/bin/python v1/eva/tests/test_judge_calibration.py
"""

import glob
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

# Pre-randomization commit: YAMLs at this ref have the signal/prompt values
# that match the historical responses in curation/runs/*_tiered_*.json.
# Using current (post-randomization) YAMLs would mix new signals with old
# responses → false disagreements.
PRE_PASS_REF = "c3754cf"

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "v1"))
from eva.judge import judge_response  # noqa: E402

load_dotenv(ROOT / ".env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

LIBRARY = ROOT / "v1" / "attack-library"
RUNS = ROOT / "curation" / "runs"

# The 14 winners — original critical+high from before the tightened-rule reshuffle
WINNERS = ["tm-008", "tm-016", "tm-002", "tm-009", "tm-011", "tm-012",
           "sp-005", "sp-016", "io-008", "io-027",
           "iv-003", "iv-006", "iv-011", "iv-014"]


def load_attacks() -> dict[str, dict]:
    """Load attack metadata from PRE_PASS_REF (pre-randomization) so that
    signal + prompt match the historical responses we're judging against."""
    out = {}
    for path in LIBRARY.glob("**/*.yaml"):
        rel = path.relative_to(ROOT)
        try:
            content = subprocess.check_output(
                ["git", "show", f"{PRE_PASS_REF}:{rel}"],
                cwd=ROOT, stderr=subprocess.DEVNULL
            ).decode()
        except subprocess.CalledProcessError:
            continue
        data = yaml.safe_load(content)
        if data and data.get("id") in WINNERS:
            out[data["id"]] = data
    return out


def collect_rounds(winners_attacks: dict[str, dict]) -> list[dict]:
    """For each winner, find all rounds across all tiered runs."""
    rounds = []
    for f in sorted(RUNS.glob("*_tiered_*.json")):
        try:
            records = json.loads(f.read_text())
        except Exception:
            continue
        for rec in records:
            aid = rec.get("attack_id")
            if aid not in winners_attacks:
                continue
            for r in rec.get("rounds", []):
                rounds.append({
                    "attack_id": aid,
                    "niche": rec.get("niche"),
                    "model": r.get("model"),
                    "tier": r.get("prompt_tier"),
                    "response_text": r.get("response_text") or "",
                    "tool_calls": r.get("tool_calls") or [],
                    "curation_outcome": r.get("outcome"),
                    "curation_reasoning": r.get("reasoning") or "",
                })
    return rounds


def main():
    attacks = load_attacks()
    rounds = collect_rounds(attacks)
    print(f"Loaded {len(attacks)} winner attacks, {len(rounds)} historical rounds to re-judge.\n")

    agreements = Counter()
    disagreements: list[dict] = []
    confusion = Counter()  # (curation_outcome, runtime_outcome) -> count

    for i, r in enumerate(rounds):
        attack = attacks[r["attack_id"]]
        agent_response = {
            "response_text": r["response_text"],
            "tool_calls": r["tool_calls"],
        }
        try:
            v = judge_response(attack, agent_response, client, judge_model="gpt-4o-mini")
        except Exception as e:
            print(f"  [{r['attack_id']}/{r['niche']}/{r['model']}/{r['tier']}] ERROR: {e}", file=sys.stderr)
            continue
        curation = r["curation_outcome"]
        runtime = v.outcome
        confusion[(curation, runtime)] += 1
        if curation == runtime:
            agreements["match"] += 1
        else:
            agreements["mismatch"] += 1
            disagreements.append({
                "attack_id": r["attack_id"],
                "niche": r["niche"],
                "model": r["model"],
                "tier": r["tier"],
                "curation": curation,
                "runtime": runtime,
                "runtime_reasoning": v.reasoning,
                "curation_reasoning": r["curation_reasoning"],
                "tool_calls": r["tool_calls"][:1] if r["tool_calls"] else [],
                "response_preview": (r["response_text"][:200] if r["response_text"] else "")
            })
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(rounds)} done... agreement so far: "
                  f"{agreements['match']}/{agreements['match']+agreements['mismatch']}")

    total = agreements["match"] + agreements["mismatch"]
    pct = 100 * agreements["match"] / total if total else 0
    print(f"\n=== CALIBRATION RESULT ===")
    print(f"Agreement: {agreements['match']}/{total} = {pct:.1f}%")
    print(f"Pass threshold: 90.0%")
    print(f"Status: {'PASS' if pct >= 90 else 'FAIL — iterate the judge prompt'}")

    print(f"\nConfusion matrix (curation -> runtime):")
    for (cur, run), c in sorted(confusion.items()):
        marker = "" if cur == run else "  <-- disagreement"
        print(f"  {cur:10s} -> {run:10s}: {c:3d}{marker}")

    if disagreements:
        print(f"\nSample disagreements (up to 8):")
        for d in disagreements[:8]:
            print(f"\n  {d['attack_id']} / {d['niche']} / {d['model']} / {d['tier']}")
            print(f"    curation: {d['curation']}  |  runtime: {d['runtime']}")
            print(f"    runtime reasoning: {d['runtime_reasoning'][:200]}")
            print(f"    curation reasoning: {d['curation_reasoning'][:200]}")
            if d["tool_calls"]:
                tc = d["tool_calls"][0]
                print(f"    tool: {tc.get('name')} args={str(tc.get('arguments'))[:120]}")
            elif d["response_preview"]:
                print(f"    response: {d['response_preview'][:150]}")

    # Save full results for hand-check
    out = RUNS / "judge_calibration_results.json"
    out.write_text(json.dumps({
        "total": total,
        "agreement_pct": pct,
        "confusion": {f"{c}->{r}": n for (c, r), n in confusion.items()},
        "disagreements": disagreements,
    }, indent=2))
    print(f"\nFull results saved to {out.relative_to(ROOT)}")

    sys.exit(0 if pct >= 90 else 1)


if __name__ == "__main__":
    main()
