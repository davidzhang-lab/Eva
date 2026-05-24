"""
Dedicated runner for the multi_turn_manipulation category.

Reuses the same tiered cascade logic as run_category.py but routes
through multi_turn.run_multi_turn (which maintains conversation state
across turns) instead of the single-shot victim functions.
"""

import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import judge_response, tier_from_beats, CASCADE_MODELS  # noqa: E402
from multi_turn import run_multi_turn  # noqa: E402
from success_signals import SIGNALS  # noqa: E402


def _multi_turn_run_one(attack: dict, victim_name: str, model: str, tier: str) -> dict:
    victim_response = run_multi_turn(attack, victim_name, model=model, tier=tier)
    verdict = judge_response(attack, victim_response)
    return {
        "outcome": verdict.outcome,
        "reasoning": verdict.reasoning,
        "tool_calls": victim_response["tool_calls"],
        "response_text": victim_response["response_text"],
    }


def _single_tier_multi_turn_cascade(attack: dict, victim_name: str, tier: str) -> dict:
    beats = []
    rounds = []
    for model in CASCADE_MODELS:
        result = _multi_turn_run_one(attack, victim_name, model, tier)
        rounds.append({
            "model": model,
            "prompt_tier": tier,
            "outcome": result["outcome"],
            "tool_calls": result["tool_calls"],
            "reasoning": result["reasoning"],
            "response_text": result["response_text"][:600],
        })
        if result["outcome"] == "succeeded":
            beats.append(model)
        else:
            break
    return {"beats": beats, "rounds": rounds}


def multi_turn_cascade(attack: dict, victim_name: str) -> dict:
    starter = _single_tier_multi_turn_cascade(attack, victim_name, "starter")
    if starter["beats"]:
        hardened = _single_tier_multi_turn_cascade(attack, victim_name, "hardened")
    else:
        hardened = {"beats": [], "rounds": []}
    return {
        "beats_starter": starter["beats"],
        "beats_hardened": hardened["beats"],
        "tier_starter": tier_from_beats(starter["beats"]),
        "tier_hardened": tier_from_beats(hardened["beats"]),
        "rounds": starter["rounds"] + hardened["rounds"],
    }


TIER_EMOJI = {
    "frontier": "🥇", "strong": "🥈", "baseline_only": "🥉", "refused_everywhere": "✅",
}


def main():
    module = importlib.import_module("categories.multi_turn_manipulation")
    candidates = module.MULTI_TURN_MANIPULATION_CANDIDATES

    print(f"Running {len(candidates)} multi-turn candidates...\n")
    results = []

    for cand in candidates:
        print(f"[{cand['id']}] {cand['name']}")
        for niche in cand["niches"]:
            try:
                cand_with_signal = {**cand, "success_signal": SIGNALS.get(cand["id"], "")}
                cascade_result = multi_turn_cascade(cand_with_signal, niche)
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
                s_emoji = TIER_EMOJI[cascade_result["tier_starter"]]
                h_emoji = TIER_EMOJI[cascade_result["tier_hardened"]]
                s_beats = ", ".join(cascade_result["beats_starter"]) or "refused"
                h_beats = ", ".join(cascade_result["beats_hardened"]) or "—"
                print(f"  {niche}: starter {s_emoji} ({s_beats}) | hardened {h_emoji} ({h_beats})")
            except Exception as e:
                print(f"  ✗ {niche}: ERROR — {e}")
                results.append({"attack_id": cand["id"], "niche": niche, "error": str(e)})
        print()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    output_path = Path(__file__).parent / "runs" / f"multi_turn_manipulation_tiered_{timestamp}.json"
    output_path.write_text(json.dumps(results, indent=2))
    print(f"Full results: {output_path}")


if __name__ == "__main__":
    main()
