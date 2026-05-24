"""
Generic category-runner for Eva v1 attack-library curation.

Each candidate goes through a TIERED cascade:
- starter (real public template) × {gpt-4o-mini, gpt-4o, gpt-5}
- if any starter round succeeded → also run hardened (real-extracted-style) × same models

Usage:
    uv run python run_category.py tool_misuse
"""

import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import cascade_attack  # noqa: E402
from victims import VICTIM_REGISTRY  # noqa: E402
from success_signals import SIGNALS  # noqa: E402


TIER_EMOJI = {
    "frontier": "🥇",
    "strong": "🥈",
    "baseline_only": "🥉",
    "refused_everywhere": "✅",
}


def _tier_emoji(tier: str) -> str:
    return TIER_EMOJI.get(tier, "?")


def run_category(category_name: str) -> dict:
    """Run every candidate × niche through the two-tier cascade."""
    module = importlib.import_module(f"categories.{category_name}")
    candidates_attr = f"{category_name.upper()}_CANDIDATES"
    candidates = getattr(module, candidates_attr)

    results = []
    total_runs = sum(len(c["niches"]) for c in candidates)
    print(f"Running {len(candidates)} {category_name} candidates × niches = {total_runs} cascade chains")
    print(f"(each chain: starter [3 models] → if any beat, hardened [3 models])\n")

    for cand in candidates:
        print(f"[{cand['id']}] {cand['name']}")
        for niche in cand["niches"]:
            victim_fn = VICTIM_REGISTRY.get(niche)
            if not victim_fn:
                print(f"  ⚠ unknown niche: {niche}")
                continue
            try:
                cand_with_signal = {**cand, "success_signal": SIGNALS.get(cand["id"], "")}
                cascade_result = cascade_attack(cand_with_signal, victim_fn)
                record = {
                    "attack_id": cand["id"],
                    "attack_name": cand["name"],
                    "pattern": cand["pattern"],
                    "source": cand["source"],
                    "niche": niche,
                    "beats_starter": cascade_result["beats_starter"],
                    "beats_hardened": cascade_result["beats_hardened"],
                    "tier_starter": cascade_result["tier_starter"],
                    "tier_hardened": cascade_result["tier_hardened"],
                    "rounds": cascade_result["rounds"],
                }
                results.append(record)
                s_emoji = _tier_emoji(cascade_result["tier_starter"])
                h_emoji = _tier_emoji(cascade_result["tier_hardened"])
                s_beats = (
                    f"beats {', '.join(cascade_result['beats_starter'])}"
                    if cascade_result["beats_starter"]
                    else "refused"
                )
                h_beats = (
                    f"beats {', '.join(cascade_result['beats_hardened'])}"
                    if cascade_result["beats_hardened"]
                    else "—"
                )
                print(f"  {niche}: starter {s_emoji} ({s_beats}) | hardened {h_emoji} ({h_beats})")
            except Exception as e:
                print(f"  ✗ {niche}: ERROR — {e}")
                results.append({
                    "attack_id": cand["id"],
                    "niche": niche,
                    "error": str(e),
                })
        print()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    output_path = (
        Path(__file__).parent / "runs" / f"{category_name}_tiered_{timestamp}.json"
    )
    output_path.write_text(json.dumps(results, indent=2))

    starter_summary = {"frontier": 0, "strong": 0, "baseline_only": 0, "refused_everywhere": 0}
    hardened_summary = {"frontier": 0, "strong": 0, "baseline_only": 0, "refused_everywhere": 0}
    errors = 0
    for r in results:
        if "error" in r:
            errors += 1
            continue
        starter_summary[r["tier_starter"]] += 1
        hardened_summary[r["tier_hardened"]] += 1

    print(f"Full results: {output_path}")
    print(f"STARTER tier per-chain: {starter_summary}")
    print(f"HARDENED tier per-chain: {hardened_summary}")
    if errors:
        print(f"Errors: {errors}")

    # Per-attack best tier (across niches) per prompt-strength
    tier_rank = {"refused_everywhere": 0, "baseline_only": 1, "strong": 2, "frontier": 3}
    best_starter: dict[str, str] = {}
    best_hardened: dict[str, str] = {}
    for r in results:
        if "error" in r:
            continue
        aid = r["attack_id"]
        if aid not in best_starter or tier_rank[r["tier_starter"]] > tier_rank[best_starter[aid]]:
            best_starter[aid] = r["tier_starter"]
        if aid not in best_hardened or tier_rank[r["tier_hardened"]] > tier_rank[best_hardened[aid]]:
            best_hardened[aid] = r["tier_hardened"]
    pa_starter = {"frontier": 0, "strong": 0, "baseline_only": 0, "refused_everywhere": 0}
    pa_hardened = {"frontier": 0, "strong": 0, "baseline_only": 0, "refused_everywhere": 0}
    for t in best_starter.values():
        pa_starter[t] += 1
    for t in best_hardened.values():
        pa_hardened[t] += 1
    print(f"STARTER per-attack best: {pa_starter}")
    print(f"HARDENED per-attack best: {pa_hardened}")

    return {
        "starter_per_chain": starter_summary,
        "hardened_per_chain": hardened_summary,
        "starter_per_attack": pa_starter,
        "hardened_per_attack": pa_hardened,
        "results": results,
        "output_path": str(output_path),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_category.py <category_name>")
        sys.exit(1)
    run_category(sys.argv[1])
