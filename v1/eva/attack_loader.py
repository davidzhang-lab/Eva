"""
attack_loader.py — walk v1/attack-library/ and yield attack dicts.

Reads YAMLs produced by the 2026-05-24 hardening pass. Schema fields used:
  id, name, category, technique, observed_tier, success_signal,
  applies_to_niches, prompt OR turns.

Supports filtering by category (direct/indirect), technique (tool_misuse etc),
observed_tier (high/medium/low/refused-by-tested-models), and niche.
"""

from pathlib import Path
from typing import Iterator, Optional

import yaml

# Repo root: this file is at v1/eva/attack_loader.py -> parents[2] == Eva root
ROOT = Path(__file__).resolve().parents[2]
LIBRARY_DEFAULT = ROOT / "v1" / "attack-library"


def load_attacks(
    library_dir: Path = LIBRARY_DEFAULT,
    category: Optional[str] = None,
    technique: Optional[str] = None,
    observed_tier: Optional[str] = None,
    niche: Optional[str] = None,
    max_attacks: Optional[int] = None,
) -> list[dict]:
    """Load attacks from the library, optionally filtered.

    Filters are AND-combined. niche check matches if niche appears in
    attack['applies_to_niches']. Returns a sorted (by id) list.
    """
    attacks: list[dict] = []
    for path in sorted(library_dir.glob("**/*.yaml")):
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            continue
        if category and data.get("category") != category:
            continue
        if technique and data.get("technique") != technique:
            continue
        if observed_tier and data.get("observed_tier") != observed_tier:
            continue
        if niche and niche not in (data.get("applies_to_niches") or []):
            continue
        attacks.append(data)
    attacks.sort(key=lambda a: a.get("id", ""))
    if max_attacks is not None:
        attacks = attacks[:max_attacks]
    return attacks
