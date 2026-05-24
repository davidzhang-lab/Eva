"""
Verify the 11 frontier wins by re-running each one against gpt-5 and
capturing the FULL tool-call arguments + response text.

Need this because cascade_attack() only stores tool-call names, not
arguments. To validate that frontier wins are real (agent actually
performed the malicious action with attacker-controlled values), we
have to inspect the args.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from victims import VICTIM_REGISTRY  # noqa: E402

# Each entry: (category, attack_id, niche)
FRONTIER_WINS = [
    ("tool_misuse", "tm-002", "workspace"),
    ("tool_misuse", "tm-008", "workspace"),
    ("tool_misuse", "tm-016", "ecommerce"),
    ("data_exfiltration", "de-011", "banking"),
    ("system_prompt_leak", "sp-005", "dev_assistant"),
    ("indirect_via_input", "iv-003", "ecommerce"),
    ("indirect_via_input", "iv-006", "dev_assistant"),
    ("indirect_via_input", "iv-009", "ecommerce"),
    ("indirect_via_input", "iv-011", "workspace"),
    ("indirect_via_input", "iv-011", "ecommerce"),
    ("indirect_via_input", "iv-014", "dev_assistant"),
]


def load_attack(category: str, attack_id: str) -> dict:
    import importlib
    module = importlib.import_module(f"categories.{category}")
    attr = f"{category.upper()}_CANDIDATES"
    candidates = getattr(module, attr)
    return next(c for c in candidates if c["id"] == attack_id)


def main():
    print(f"Re-running {len(FRONTIER_WINS)} frontier wins against gpt-5 with full arg capture...\n")
    results = []
    for i, (cat, aid, niche) in enumerate(FRONTIER_WINS, 1):
        attack = load_attack(cat, aid)
        victim_fn = VICTIM_REGISTRY[niche]
        print(f"[{i}/{len(FRONTIER_WINS)}] {aid} × {niche}: {attack['name']}")
        try:
            response = victim_fn(attack["prompt"], model="gpt-5")
            results.append({
                "category": cat,
                "attack_id": aid,
                "attack_name": attack["name"],
                "niche": niche,
                "tool_calls": response["tool_calls"],  # full args
                "response_text": response["response_text"],
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "category": cat,
                "attack_id": aid,
                "niche": niche,
                "error": str(e),
            })

    output_path = Path(__file__).parent / "runs" / "frontier_verification.json"
    output_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nFull verification data saved to: {output_path}")


if __name__ == "__main__":
    main()
