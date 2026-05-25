"""
randomize_fingerprints.py — Eva v1 attack-library fingerprint + domain diversifier.

What it does:
  For every YAML in v1/attack-library/, replaces fingerprintable values with
  deterministic randomized substitutes:
    - Test card numbers (4242 etc)         -> random last-4 from a real-test-card pool
    - Order IDs (ACG-XXXX)                  -> mixed prefix pool (ORD/INV/TXN/REF/SHP/ACG)
    - IBANs                                 -> Faker IBANs (country preserved)
    - Recurring persona full names          -> Faker names (deterministic per attack)
    - Malicious domains ({word}-{word}.io)  -> 5-strategy mix (typo-squat / subdomain /
                                                SaaS / country-TLD / keep-original)
    - Emails                                -> rebuilt from new persona + new domain
    - Dollar amounts                        -> new amount in same magnitude bucket
  Also updates curation/categories/*.py and curation/success_signals.py so the
  library stays regeneratable end-to-end.

How to run:
  # Dry-run (writes diffs + mapping to ~/eva_preview/, modifies nothing):
  curation/.venv/bin/python curation/tools/randomize_fingerprints.py --dry-run

  # Apply (mutates YAMLs + upstream .py files):
  curation/.venv/bin/python curation/tools/randomize_fingerprints.py --apply

Determinism: per-file seed derived from GLOBAL_SEED + attack_id (MD5). Two runs
with the same GLOBAL_SEED produce byte-identical output. Idempotency marker
written to each YAML (`fingerprints_randomized: true`); re-running skips
already-randomized files unless --force.

How to roll back:
  git reset --hard 26c931e  # pre-pass snapshot

Whitelist: real public researchers / public attack-author names are NOT
randomized (Simon Willison, Pliny, Marvin von Hagen).
"""

import argparse
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from faker import Faker
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parent.parent.parent  # Eva/
LIBRARY = ROOT / "v1" / "attack-library"
CURATION = ROOT / "curation"
PREVIEW = Path.home() / "eva_preview"
GLOBAL_SEED = "eva_v1_randomize_2026_05"

# Real test-card last-4s (so generated cards still LOOK like test cards).
# NOTE: "4242" deliberately excluded — it's the value we're randomizing AWAY
# from, so re-picking it (1/N chance) would silently leave the fingerprint.
CARD_LAST4_POOL = ["4111", "5454", "0027", "3782", "6011", "8431",
                   "7392", "1881", "9990", "5105", "0341", "2914", "4747",
                   "8888", "1234", "0019", "5566"]
# Full 16-digit test card numbers to detect
FULL_TEST_CARDS = {
    "4242424242424242", "4111111111111111", "5555555555554444",
}

# Recurring persona full names to randomize (extracted from audit)
RECURRING_PERSONAS = [
    "Mark Chen", "Sarah Williams", "Sarah Johnson", "Sarah Cole",
    "Sara Park", "Maria Sanchez", "Carol Davis", "Alex Chen",
    "Mike Rodriguez", "Sarah Mitchell", "Sarah Davis", "Rebecca Cole",
    "Jordan Lee",
]
# Real public researchers / attack-author names — DO NOT randomize
PERSONA_WHITELIST = {"Simon Willison", "Pliny", "Marvin von Hagen"}

# Brand pools per niche (3–5 brands each, per plan)
BRAND_POOLS = {
    "ecommerce": ["acmegoods.com", "shopswift.com", "northbay-retail.com", "urbanmart.io"],
    "dental": ["cityhealthdental.com", "brightsmile-clinic.com", "meridian-dental.co"],
    "dev_assistant": ["internal-eng.example.com", "devhub-tools.com", "buildops.co"],
    "banking": ["acmecredit.com", "firstmeridian-bank.com", "clearfunds.co"],
    "workspace": ["acmework.com", "northstar-workspace.com", "linkbase.io"],
}

# Legit email-provider domains (do NOT randomize these)
LEGIT_PROVIDERS = {"gmail.com", "protonmail.com", "yahoo.com", "outlook.com",
                   "hotmail.com", "icloud.com", "fastmail.com"}
# Legit scaffold domains (left alone)
LEGIT_SCAFFOLDS = {"example.com", "openai.com", "anthropic.com", "github.com"}

# Order-ID prefix pool (mix instead of all-ACG)
ORDER_PREFIXES = ["ORD", "INV", "TXN", "REF", "ACG", "SHP", "PO", "REC"]

# Domain pattern: "{word}-{word}(-services)?.io" — the fingerprint to break.
MALICIOUS_DOMAIN_RE = re.compile(
    r"\b([a-z][a-z0-9]*(?:-[a-z][a-z0-9]*){1,4})\.(io|com|co|net)\b"
)
# Recognize "external-X", "audit-X", "partner-X", etc. as the fingerprint family.
FINGERPRINT_DOMAIN_PREFIXES = {
    "external", "analytics", "partner", "operations", "audit",
    "consultant", "internal", "acme",
}

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
ORDER_ID_RE = re.compile(r"\bACG-\d{3,5}\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
DOLLAR_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")
CARD_4_RE = re.compile(r"(?<![\d-])4242(?![\d-])")  # "4242" without surrounding digits


def per_file_seed(attack_id: str) -> int:
    h = hashlib.md5((GLOBAL_SEED + attack_id).encode()).digest()
    return int.from_bytes(h[:4], "big")


def make_faker(seed: int) -> tuple[Faker, random.Random]:
    f = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)
    return f, rng


def is_fingerprint_domain(domain: str) -> bool:
    """True if this domain matches the {word}-{word}.io fingerprint family."""
    if domain in LEGIT_PROVIDERS or domain in LEGIT_SCAFFOLDS:
        return False
    if "." not in domain:
        return False
    # check if first hyphenated word is in our fingerprint prefix set
    label = domain.split(".")[0]
    head = label.split("-")[0]
    return head in FINGERPRINT_DOMAIN_PREFIXES or "-" in label


def gen_domain_replacement(original: str, niche_brands: list[str], rng: random.Random) -> str:
    """Pick a domain strategy and generate a replacement."""
    # No "keep_pattern" — leaving any domain unchanged defeats the whole point.
    strategies = ["typo_squat", "subdomain", "saas_abuse", "country_tld"]
    weights = [0.42, 0.26, 0.16, 0.16]
    strat = rng.choices(strategies, weights=weights, k=1)[0]
    brand = rng.choice(niche_brands) if niche_brands else "acmegoods.com"
    brand_base, brand_tld = brand.rsplit(".", 1)

    if strat == "typo_squat":
        # rn→m swap, double-letter, single-letter swap, hyphenation
        tricks = ["rn_swap", "double", "swap", "hyphen", "tld_swap"]
        trick = rng.choice(tricks)
        if trick == "rn_swap" and "m" in brand_base:
            return brand_base.replace("m", "rn", 1) + "." + brand_tld
        if trick == "double" and len(brand_base) > 3:
            i = rng.randint(1, len(brand_base) - 2)
            return brand_base[:i] + brand_base[i] + brand_base[i:] + "." + brand_tld
        if trick == "swap" and len(brand_base) > 4:
            i = rng.randint(0, len(brand_base) - 2)
            chars = list(brand_base)
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
            return "".join(chars) + "." + brand_tld
        if trick == "hyphen" and len(brand_base) > 4:
            i = rng.randint(2, len(brand_base) - 2)
            return brand_base[:i] + "-" + brand_base[i:] + "." + brand_tld
        if trick == "tld_swap":
            alt_tld = rng.choice(["co", "io", "net", "biz"])
            return brand_base + "." + alt_tld
        return brand_base + "." + brand_tld  # fallback
    if strat == "subdomain":
        suffixes = ["support-portal", "help-center", "vendor-tools",
                    "external-portal", "account-services"]
        suf = rng.choice(suffixes)
        return f"{brand_base}.{suf}.example.com"
    if strat == "saas_abuse":
        platforms = ["notion.site", "zendesk.com", "docs.google.com",
                     "drive.google.com", "intercom.com"]
        platform = rng.choice(platforms)
        if platform == "notion.site":
            return f"{brand_base}-{rng.randint(100000,999999):06d}.notion.site"
        if platform == "zendesk.com":
            return f"{brand_base}.zendesk.com"
        if platform.startswith("docs.google") or platform.startswith("drive.google"):
            return platform  # bare path-style abuse handled in email/url contexts
        return f"{brand_base}.{platform}"
    if strat == "country_tld":
        tld = rng.choice(["de", "co", "co.uk", "fr", "es"])
        # Use the brand base, NOT the original label — preserving the original
        # label keeps the fingerprint (e.g. "operations-archive-services.de").
        return f"{brand_base}.{tld}"
    # default — should not reach (all strategies handled above)
    return brand_base + "." + brand_tld


def gen_persona_replacement(faker: Faker) -> str:
    """Return a 'First Last' full name. Avoid hardcoded list to stay diverse."""
    return faker.name().split(" (")[0]  # strip any '(Jr.)' suffixes Faker adds


def gen_dollar_replacement(original_str: str, rng: random.Random) -> str:
    """New $ amount in same magnitude bucket, SNAPPED to attacker-plausible
    round values. Random integers like '$1,014' instead of round numbers like
    '$2,500' look suspicious to victims (real social-engineering targets ask
    for round amounts). Snap each bucket to its native denomination."""
    digits = re.sub(r"[^\d.]", "", original_str)
    if not digits:
        return original_str
    try:
        val = float(digits)
    except ValueError:
        return original_str
    # Bucket -> (low, high, snap-to)
    # snap-to: round to nearest multiple. Avoids "$1,014" style oddities.
    if val < 100:
        low, high, snap = 10, 95, 5
    elif val < 1000:
        low, high, snap = 100, 950, 50
    elif val < 10000:
        low, high, snap = 1000, 9500, 500
    elif val < 100000:
        low, high, snap = 10000, 95000, 2500
    else:
        low, high, snap = 100000, 950000, 25000
    raw = rng.randint(low, high)
    snapped = round(raw / snap) * snap
    return f"${snapped:,}"


def gen_iban_replacement(original: str, faker: Faker) -> str:
    """Preserve country code; generate new IBAN body."""
    cc = original[:2]
    try:
        iban = faker.iban()
        return cc + iban[2:]
    except Exception:
        return original


def gen_order_id_replacement(rng: random.Random) -> str:
    prefix = rng.choice(ORDER_PREFIXES)
    digits = rng.randint(1000, 99999)
    return f"{prefix}-{digits}"


def gen_card_4(rng: random.Random) -> str:
    return rng.choice(CARD_LAST4_POOL)


def gen_full_card(faker: Faker) -> str:
    return faker.credit_card_number().replace(" ", "").replace("-", "")[:16]


def persona_variants(full_name: str) -> list[str]:
    """Generate textual variants of a full name that may appear in attack content."""
    first, *rest = full_name.split(" ", 1)
    last = rest[0] if rest else ""
    if not last:
        return [full_name]
    lf, ll = first.lower(), last.lower()
    return [
        full_name,                  # "Sarah Williams"
        full_name.lower(),          # "sarah williams"
        f"{lf}.{ll}",               # "sarah.williams"
        f"{lf}_{ll}",               # "sarah_williams"
        f"{lf}-{ll}",               # "sarah-williams"
        f"{lf}{ll}",                # "sarahwilliams"
    ]


def persona_replacement_variants(new_name: str) -> list[str]:
    """Mirror the variant list for the new name."""
    return persona_variants(new_name)


def collect_strings(node) -> list[str]:
    """Recursively collect every string value from a YAML node."""
    out = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for v in node.values():
            out.extend(collect_strings(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(collect_strings(v))
    return out


def build_mapping(attack: dict) -> dict[str, str]:
    """Build per-attack original→new value mapping. Deterministic on attack_id."""
    aid = attack.get("id", "unknown")
    seed = per_file_seed(aid)
    faker, rng = make_faker(seed)

    niches = attack.get("applies_to_niches") or []
    # Use first applicable niche's brand pool; fall back to ecommerce
    primary_niche = niches[0] if niches else "ecommerce"
    niche_brands = BRAND_POOLS.get(primary_niche, BRAND_POOLS["ecommerce"])

    # Only scan attack content fields, NOT metadata
    content_fields = {}
    for k in ("prompt", "turns", "success_signal", "name"):
        if k in attack:
            content_fields[k] = attack[k]
    strings = collect_strings(content_fields)
    joined = "\n".join(strings)

    mapping: dict[str, str] = {}

    # --- Personas (longest first to avoid prefix collisions) ---
    seen_personas = []
    for persona in sorted(RECURRING_PERSONAS, key=len, reverse=True):
        if persona in PERSONA_WHITELIST:
            continue
        if persona.lower() in joined.lower() and persona not in seen_personas:
            seen_personas.append(persona)
    persona_map: dict[str, str] = {}
    for p in seen_personas:
        new = gen_persona_replacement(faker)
        persona_map[p] = new
    for original, new in persona_map.items():
        for ov, nv in zip(persona_variants(original), persona_replacement_variants(new)):
            mapping[ov] = nv
        # Standalone first-name fallback: if the original full name appears in
        # the text AND the first name ALSO appears in standalone form (e.g.
        # "I (Maria) verified" after the full name was introduced as
        # "Maria Sanchez" earlier), replace those too. Otherwise the narrative
        # breaks: random Faker swap leaves "Updated by Agent #427 (William
        # Smith)" alongside "I (Maria) already verified".
        # Standalone first-name handling: longest-first replacement in
        # apply_mapping means "Maria Sanchez" -> "William Smith" runs FIRST,
        # so any remaining standalone "Maria" reference (e.g. "I (Maria)
        # verified...") will still be the original string when the
        # shorter "Maria" -> "William" mapping runs. Only add the mapping if a
        # standalone-form occurrence actually exists (not just as part of the
        # full name) to avoid polluting the mapping for attacks that don't
        # need it.
        orig_first = original.split()[0]
        new_first = new.split()[0]
        parts = original.split()
        orig_last = parts[1] if len(parts) > 1 else ""
        # standalone = first name NOT followed by the surname
        if orig_last:
            standalone_re = re.compile(
                rf"\b{re.escape(orig_first)}\b(?!\s+{re.escape(orig_last)}\b)"
            )
        else:
            standalone_re = re.compile(rf"\b{re.escape(orig_first)}\b")
        if standalone_re.search(joined):
            mapping[orig_first] = new_first
            mapping[orig_first.lower()] = new_first.lower()

    # --- Cards ---
    for card in FULL_TEST_CARDS:
        if card in joined:
            mapping[card] = gen_full_card(faker)
    if CARD_4_RE.search(joined):
        mapping["4242"] = gen_card_4(rng)

    # --- Order IDs ---
    # IMPORTANT: sorted() everywhere — set iteration order is non-deterministic
    # across processes (PYTHONHASHSEED), which breaks the byte-identical
    # determinism guarantee. Hit this exact bug during verification step 0.
    for oid in sorted(set(ORDER_ID_RE.findall(joined))):
        mapping[oid] = gen_order_id_replacement(rng)

    # --- IBANs ---
    for iban in sorted(set(IBAN_RE.findall(joined))):
        mapping[iban] = gen_iban_replacement(iban, faker)

    # --- Dollar amounts ---
    # Include both "$X" (matched in prompts) and bare "X" / "X,YYY" forms
    # (which appear in success_signals like "amount 2500"). Without this,
    # signal references like 'amount 2500' don't follow prompt's '$2,500'
    # randomization, breaking the judge check.
    for amt in sorted(set(DOLLAR_RE.findall(joined))):
        new_amt = gen_dollar_replacement(amt, rng)
        mapping[amt] = new_amt
        # Bare forms: "2,500" and "2500"
        amt_no_dollar = amt.lstrip("$")
        amt_no_comma = amt_no_dollar.replace(",", "")
        new_no_dollar = new_amt.lstrip("$")
        new_no_comma = new_no_dollar.replace(",", "")
        # Only add if the bare form actually appears AND isn't already mapped
        # (avoid over-replacing standalone numbers used as IDs/counters).
        for bare_orig, bare_new in [(amt_no_dollar, new_no_dollar), (amt_no_comma, new_no_comma)]:
            if bare_orig == amt:
                continue  # already handled
            if bare_orig in mapping:
                continue
            # Word-boundary check: bare digit string must appear standalone
            if re.search(rf"\b{re.escape(bare_orig)}\b", joined):
                mapping[bare_orig] = bare_new

    # --- Malicious domains (collect, then replace) ---
    found_domains = set()
    for m in MALICIOUS_DOMAIN_RE.finditer(joined):
        full = m.group(0).lower()
        if is_fingerprint_domain(full):
            found_domains.add(full)
    domain_map: dict[str, str] = {}
    for d in sorted(found_domains):
        domain_map[d] = gen_domain_replacement(d, niche_brands, rng)
    mapping.update(domain_map)

    # --- Emails (depend on persona + domain mappings) ---
    for email in sorted(set(EMAIL_RE.findall(joined))):
        local, _, dom = email.partition("@")
        if not dom:
            continue
        new_dom = dom
        if dom.lower() in domain_map:
            new_dom = domain_map[dom.lower()]
        # If local contains a persona, persona-variant replacement will handle it.
        # Otherwise, leave local alone if domain is legit; randomize if exfil-domain.
        if dom in LEGIT_PROVIDERS:
            # legit provider — keep, persona variants handle local part
            continue
        # exfil domain: keep local (it'll be persona-replaced if needed), swap domain
        if new_dom != dom:
            mapping[email] = f"{local}@{new_dom}"

    return mapping


def apply_mapping(s: str, mapping: dict[str, str]) -> str:
    """Apply mapping (longest key first to prevent prefix collisions)."""
    if not isinstance(s, str):
        return s
    for original in sorted(mapping.keys(), key=len, reverse=True):
        if original in s:
            s = s.replace(original, mapping[original])
    return s


def transform_node(node, mapping: dict[str, str]):
    if isinstance(node, str):
        return apply_mapping(node, mapping)
    if isinstance(node, dict):
        for k in list(node.keys()):
            node[k] = transform_node(node[k], mapping)
        return node
    if isinstance(node, list):
        for i in range(len(node)):
            node[i] = transform_node(node[i], mapping)
        return node
    return node


def randomize_yaml(path: Path, yaml: YAML, dry_run: bool, force: bool) -> tuple[str, dict[str, str]]:
    data = yaml.load(path)
    if data is None:
        return "skipped:empty", {}
    if data.get("fingerprints_randomized") and not force:
        return "skipped:already-randomized", {}

    mapping = build_mapping(data)
    if not mapping:
        return "no-fingerprints-found", {}

    # Transform only the content fields, not metadata
    for k in ("prompt", "turns", "success_signal", "name"):
        if k in data:
            data[k] = transform_node(data[k], mapping)

    if not dry_run:
        data["fingerprints_randomized"] = True
        data["randomization_seed"] = GLOBAL_SEED
        with open(path, "w") as f:
            yaml.dump(data, f)
    return "randomized", mapping


def write_dry_run_diff(preview_dir: Path, attack_id: str, mapping: dict[str, str]):
    preview_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {attack_id}", ""]
    for original in sorted(mapping.keys(), key=len, reverse=True):
        new = mapping[original]
        lines.append(f"  {original!r}")
        lines.append(f"    -> {new!r}")
    (preview_dir / f"{attack_id}.diff").write_text("\n".join(lines))


def sync_upstream(global_mapping: dict[str, dict[str, str]]):
    """Apply each per-attack mapping to curation/categories/*.py + success_signals.py
    via scoped text replacement."""
    # Categories: each file is one .py with multiple dict literals. We do scoped
    # text-replacement per attack by locating the dict by 'id' marker.
    for py_path in (CURATION / "categories").glob("*.py"):
        text = py_path.read_text()
        original_text = text
        for aid, mapping in global_mapping.items():
            if f'"id": "{aid}"' not in text and f"'id': '{aid}'" not in text:
                continue
            # Find the attack's dict span: from its 'id' to the next id or closing
            idx = text.find(f'"id": "{aid}"')
            if idx == -1:
                idx = text.find(f"'id': '{aid}'")
            if idx == -1:
                continue
            # End-of-block: next dict's 'id' or end of list
            next_id = text.find('"id":', idx + 5)
            if next_id == -1:
                next_id = text.find("'id':", idx + 5)
            end = next_id if next_id != -1 else len(text)
            block = text[idx:end]
            new_block = block
            for orig in sorted(mapping.keys(), key=len, reverse=True):
                new_block = new_block.replace(orig, mapping[orig])
            text = text[:idx] + new_block + text[end:]
        if text != original_text:
            py_path.write_text(text)
            print(f"  upstream synced: {py_path.relative_to(CURATION)}")

    # success_signals.py: dict with attack_id keys.
    sig_path = CURATION / "success_signals.py"
    text = sig_path.read_text()
    original_text = text
    for aid, mapping in global_mapping.items():
        # Find the line: "aid": "...signal..."
        key_idx = text.find(f'"{aid}":')
        if key_idx == -1:
            continue
        # End of signal string: next ",\n    \"" pattern or close of dict
        line_end = text.find("\n", key_idx)
        if line_end == -1:
            continue
        # Crude scope: the line itself (signals are usually single-line strings).
        line = text[key_idx:line_end]
        new_line = line
        for orig in sorted(mapping.keys(), key=len, reverse=True):
            new_line = new_line.replace(orig, mapping[orig])
        text = text[:key_idx] + new_line + text[line_end:]
    if text != original_text:
        sig_path.write_text(text)
        print(f"  upstream synced: success_signals.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Preview only; no writes.")
    ap.add_argument("--apply", action="store_true", help="Mutate YAMLs and upstream.")
    ap.add_argument("--force", action="store_true", help="Re-randomize already-marked files.")
    ap.add_argument("--only-ids", type=str, default="",
                    help="Comma-separated attack IDs to process (default: all). Useful for selective re-randomization after a bug fix.")
    ap.add_argument("--out", type=Path, default=PREVIEW / "randomization_preview",
                    help="Dry-run output dir (default: ~/eva_preview/randomization_preview/)")
    args = ap.parse_args()
    only_ids = {s.strip() for s in args.only_ids.split(",") if s.strip()}
    if not (args.dry_run or args.apply):
        print("Specify --dry-run or --apply", file=sys.stderr)
        sys.exit(2)
    dry = args.dry_run

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 120
    yaml.indent(mapping=2, sequence=4, offset=2)

    files = sorted(LIBRARY.glob("**/*.yaml"))
    counts = defaultdict(int)
    global_mapping: dict[str, dict[str, str]] = {}

    if dry and args.out:
        # Clear stale preview output
        if args.out.exists():
            for f in args.out.glob("*.diff"):
                f.unlink()
    args.out.mkdir(parents=True, exist_ok=True)

    for f in files:
        try:
            # If --only-ids restricts processing, peek at id without full parse
            if only_ids:
                peek = yaml.load(f)
                if peek is None or peek.get("id") not in only_ids:
                    counts["skipped:not-in-only-ids"] += 1
                    continue
            result, mapping = randomize_yaml(f, yaml, dry_run=dry, force=args.force)
            counts[result] += 1
            if result == "randomized":
                data = yaml.load(f)
                aid = data.get("id", f.stem)
                global_mapping[aid] = mapping
                if dry:
                    write_dry_run_diff(args.out, aid, mapping)
        except Exception as e:
            counts["error"] += 1
            print(f"  ERROR on {f.relative_to(LIBRARY)}: {e}", file=sys.stderr)

    # Write the global mapping (always; useful for upstream sync + audit)
    (args.out / "global_mapping.json").write_text(
        json.dumps(global_mapping, indent=2, sort_keys=True)
    )

    if args.apply and global_mapping:
        print("\nSyncing upstream...")
        sync_upstream(global_mapping)

    print(f"\nRandomized:    {counts['randomized']}")
    print(f"Skipped:       {counts.get('skipped:already-randomized', 0)} already-randomized "
          f"+ {counts.get('skipped:empty', 0)} empty + {counts.get('no-fingerprints-found', 0)} no-fingerprints")
    print(f"Errors:        {counts['error']}")
    print(f"Total YAMLs:   {len(files)}")
    print(f"Mapping JSON:  {args.out / 'global_mapping.json'}")
    if dry:
        print(f"Diffs:         {args.out}/*.diff")


if __name__ == "__main__":
    main()
