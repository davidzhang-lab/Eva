"""
runner.py — orchestrates a full Eva run.

For each attack in the library:
  1. Sends it to the target via the connector (single-turn) or threads turns
     through repeated connector calls (multi-turn).
  2. Hands the response to the judge.
  3. Collects (attack, response, verdict) into a results list.

Per-attack errors are caught and recorded as outcome:"error" — one bad attack
does NOT crash the run. If the FIRST attack's target call errors with an
auth/unreachable failure, the run aborts early (before burning judge budget).
"""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from .attack_loader import load_attacks
from .connector import send_attack
from .judge import judge_response

# Multi-turn conversation pattern lifted from curation/multi_turn.py:78-110
# (synthetic tool responses keep the OpenAI API happy across turns).

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass
class RunConfig:
    target_endpoint: str
    target_api_key: str
    target_model: str
    judge_endpoint: str = ""
    judge_api_key: str = ""
    judge_model: str = "gpt-4o-mini"
    # Filters
    category: Optional[str] = None
    technique: Optional[str] = None
    observed_tier: Optional[str] = None
    niche: Optional[str] = None
    max_attacks: Optional[int] = None
    # Demo agent's tool schemas — for non-demo targets, the customer's agent
    # has its own tools; we pass None and the target replies stateless.
    demo_tools: Optional[list[dict]] = None


def _make_judge_client(config: RunConfig) -> OpenAI:
    api_key = config.judge_api_key or os.environ.get("OPENAI_API_KEY", "")
    if config.judge_endpoint and config.judge_endpoint.startswith("http"):
        return OpenAI(api_key=api_key, base_url=config.judge_endpoint)
    return OpenAI(api_key=api_key)


def _agent_response_for_judge(response: dict) -> dict:
    """Shape the connector's AgentResponse for the judge."""
    return {
        "response_text": response.get("response_text") or "",
        "tool_calls": response.get("tool_calls") or [],
    }


def _run_single_turn(attack: dict, config: RunConfig) -> dict:
    """Send the attack's prompt directly to the target. One round."""
    # For demo target, the demo agent provides its own system prompt + tools.
    # For non-demo, the customer's agent uses whatever it was configured with.
    return send_attack(
        target_endpoint=config.target_endpoint,
        target_api_key=config.target_api_key,
        target_model=config.target_model,
        attack_prompt=attack["prompt"],
        conversation_history=None,
        tools=config.demo_tools if config.target_endpoint != "demo" else None,
    )


def _run_multi_turn(attack: dict, config: RunConfig) -> dict:
    """Thread `turns:` through repeated connector calls, maintaining state.

    Synthetic `{"status": "ok"}` tool responses are inserted after any tool
    call so the next user-turn doesn't error from the API. Pattern is the
    proven one from curation/multi_turn.py:78-110.
    """
    history: list[dict] = []
    aggregated_text_parts: list[str] = []
    aggregated_tool_calls: list[dict] = []
    total_tokens = 0
    last_error: Optional[str] = None

    for turn_text in attack.get("turns", []):
        response = send_attack(
            target_endpoint=config.target_endpoint,
            target_api_key=config.target_api_key,
            target_model=config.target_model,
            attack_prompt=turn_text,
            conversation_history=history,
            tools=config.demo_tools if config.target_endpoint != "demo" else None,
        )

        # Bookkeeping
        text = response.get("response_text") or ""
        tcs = response.get("tool_calls") or []
        aggregated_text_parts.append(text)
        aggregated_tool_calls.extend(tcs)
        total_tokens += response.get("tokens_used", 0) or 0
        if response.get("error"):
            last_error = response["error"]
            break  # abort multi-turn on hard error

        # Append the user-turn and the assistant-turn to history for next round.
        history.append({"role": "user", "content": turn_text})
        if tcs:
            # Assistant message with tool_calls + synthetic tool replies
            history.append({
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {
                        "id": tc.get("id") or f"call_{i}",
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for i, tc in enumerate(tcs)
                ],
            })
            for i, tc in enumerate(tcs):
                history.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id") or f"call_{i}",
                    "content": '{"status": "ok"}',
                })
        else:
            history.append({"role": "assistant", "content": text})

    return {
        "response_text": "\n---TURN---\n".join(aggregated_text_parts),
        "tool_calls": aggregated_tool_calls,
        "latency_ms": 0,
        "tokens_used": total_tokens,
        "error": last_error,
    }


def _record(attack: dict, response: dict, verdict, duration_ms: int) -> dict:
    return {
        "attack_id": attack["id"],
        "attack_name": attack.get("name", ""),
        "category": attack.get("category", ""),
        "technique": attack.get("technique", ""),
        "observed_tier": attack.get("observed_tier", ""),
        "agent_response": {
            "response_text": response.get("response_text") or "",
            "tool_calls": response.get("tool_calls") or [],
            "tokens_used": response.get("tokens_used", 0) or 0,
            "latency_ms": response.get("latency_ms", 0) or 0,
            "error": response.get("error"),
        },
        "verdict": {
            "outcome": verdict.outcome,
            "reasoning": verdict.reasoning,
            "failure_type": verdict.failure_type,
            "confidence": verdict.confidence,
            "judge_model": verdict.judge_model,
            "judge_prompt_version": verdict.judge_prompt_version,
        },
        "duration_ms": duration_ms,
    }


def _error_record(attack: dict, err: str) -> dict:
    return {
        "attack_id": attack["id"],
        "attack_name": attack.get("name", ""),
        "category": attack.get("category", ""),
        "technique": attack.get("technique", ""),
        "observed_tier": attack.get("observed_tier", ""),
        "agent_response": {"response_text": "", "tool_calls": [], "tokens_used": 0,
                           "latency_ms": 0, "error": err},
        "verdict": {"outcome": "error", "reasoning": err,
                    "failure_type": None, "confidence": "low",
                    "judge_model": "", "judge_prompt_version": ""},
        "duration_ms": 0,
    }


def run(config: RunConfig, on_progress=None) -> list[dict]:
    """Execute a full Eva run. Returns list of per-attack result records."""
    attacks = load_attacks(
        category=config.category,
        technique=config.technique,
        observed_tier=config.observed_tier,
        niche=config.niche,
        max_attacks=config.max_attacks,
    )
    if not attacks:
        return []

    judge_client = _make_judge_client(config)
    results: list[dict] = []
    aborted = False

    for i, attack in enumerate(attacks):
        if aborted:
            results.append(_error_record(attack, "run aborted after early target failure"))
            continue

        start = time.time()
        try:
            if "turns" in attack:
                response = _run_multi_turn(attack, config)
            else:
                response = _run_single_turn(attack, config)

            # Pre-flight: if the first attack fails with a hard error, abort.
            if i == 0 and response.get("error") and "auth" in (response["error"] or "").lower():
                duration_ms = int((time.time() - start) * 1000)
                results.append(_error_record(attack, response["error"]))
                aborted = True
                if on_progress:
                    on_progress(i + 1, len(attacks), attack, "error")
                continue

            verdict = judge_response(
                attack=attack,
                agent_response=_agent_response_for_judge(response),
                client=judge_client,
                judge_model=config.judge_model,
            )
            duration_ms = int((time.time() - start) * 1000)
            results.append(_record(attack, response, verdict, duration_ms))
            if on_progress:
                on_progress(i + 1, len(attacks), attack, verdict.outcome)
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            err = f"{type(e).__name__}: {e}"
            results.append(_error_record(attack, err))
            if on_progress:
                on_progress(i + 1, len(attacks), attack, "error")

    return results
