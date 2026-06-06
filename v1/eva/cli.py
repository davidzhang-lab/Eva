"""
cli.py — `eva run ...` entry point.

Single subcommand for v1 (`run`). Wires together attack_loader -> runner ->
results.write_results -> reporter.write_report.

Usage:
  python -m eva run --target demo
  python -m eva run --target https://api.example.com/v1 --target-model gpt-4o \\
      --target-api-key $TARGET_KEY --output ./results/
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .results import compute_summary, format_summary, write_results
from .runner import RunConfig, run
from .judge import JUDGE_PROMPT_VERSION
from .reporter import write_report


def _add_run_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--target", required=True,
                   help="Target endpoint URL, or 'demo' for the bundled demo agent")
    p.add_argument("--target-model", default="gpt-4o-mini",
                   help="Target model identifier (default: gpt-4o-mini)")
    p.add_argument("--target-api-key", default="",
                   help="API key for the target endpoint (or use TARGET_API_KEY env var). "
                        "Demo target doesn't need one.")
    p.add_argument("--judge-model", default="gpt-4o-mini",
                   help="Judge model (default: gpt-4o-mini)")
    p.add_argument("--judge-endpoint", default="",
                   help="Optional separate endpoint for the judge LLM")
    p.add_argument("--judge-api-key", default="",
                   help="Optional separate key for the judge LLM (defaults to OPENAI_API_KEY)")
    p.add_argument("--output", default="./results",
                   help="Output directory (default: ./results/)")
    p.add_argument("--max-attacks", type=int, default=None,
                   help="Cap attacks for smoke testing. Default: run all 151.")
    p.add_argument("--category", default=None, choices=["direct", "indirect"],
                   help="Filter to one category")
    p.add_argument("--technique", default=None,
                   help="Filter to one technique (e.g. tool_misuse)")
    p.add_argument("--observed-tier", default=None,
                   help="Filter to one tier (e.g. high)")
    p.add_argument("--niche", default=None,
                   help="Filter to one niche (e.g. ecommerce)")
    p.add_argument("--no-report", action="store_true",
                   help="Skip the report.md render step")


def _cmd_run(args: argparse.Namespace) -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    target_api_key = args.target_api_key or os.environ.get("TARGET_API_KEY", "")
    if args.target != "demo" and not target_api_key:
        print("error: --target-api-key (or TARGET_API_KEY env var) is required for non-demo targets",
              file=sys.stderr)
        return 2

    config = RunConfig(
        target_endpoint=args.target,
        target_api_key=target_api_key,
        target_model=args.target_model,
        judge_endpoint=args.judge_endpoint,
        judge_api_key=args.judge_api_key,
        judge_model=args.judge_model,
        category=args.category,
        technique=args.technique,
        observed_tier=args.observed_tier,
        niche=args.niche,
        max_attacks=args.max_attacks,
    )

    def progress(i, n, attack, outcome):
        print(f"  [{i}/{n}] {attack['id']:8s} {outcome}", flush=True)

    print(f"Running Eva v1 — target: {args.target}, model: {args.target_model}")
    if args.max_attacks:
        print(f"  (limited to {args.max_attacks} attacks)")
    print()

    records = run(config, on_progress=progress)
    if not records:
        print("No attacks matched the filters.", file=sys.stderr)
        return 1

    summary = compute_summary(records)
    print(format_summary(summary, args.target))

    out_path = write_results(
        records, out_dir=args.output,
        target_endpoint=args.target, target_model=args.target_model,
        judge_model=args.judge_model, judge_prompt_version=JUDGE_PROMPT_VERSION,
        niche=args.niche,
    )
    print(f"\nResults JSON:  {out_path}")

    if not args.no_report:
        report_path = write_report(out_path)
        print(f"Report:        {report_path}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="eva", description="Eva v1 — prompt-injection evaluator")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="Run the attack library against a target")
    _add_run_args(run_p)
    run_p.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
