"""
Multi-turn attack runner for Eva v1 curation.

Real multi-turn loop (not concatenated single-shot). For each victim niche,
maintains the conversation state across turns, including tool-call responses
so the model can continue naturally between turns.

Supports both starter and hardened victim prompts via `tier` arg.
Used when an attack candidate has a `turns: [str, ...]` field instead of a
single `prompt`.
"""

import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

from victims.ecommerce import (
    SYSTEM_PROMPT_STARTER as ECOMMERCE_STARTER,
    SYSTEM_PROMPT_HARDENED as ECOMMERCE_HARDENED,
    TOOLS as ECOMMERCE_TOOLS,
)
from victims.dental import (
    SYSTEM_PROMPT_STARTER as DENTAL_STARTER,
    SYSTEM_PROMPT_HARDENED as DENTAL_HARDENED,
    TOOLS as DENTAL_TOOLS,
)
from victims.dev_assistant import (
    SYSTEM_PROMPT_STARTER as DEV_STARTER,
    SYSTEM_PROMPT_HARDENED as DEV_HARDENED,
    TOOLS as DEV_TOOLS,
)
from victims.agentdojo_victims import (
    BANKING_SYSTEM_STARTER, BANKING_SYSTEM_HARDENED, BANKING_TOOLS,
    WORKSPACE_SYSTEM_STARTER, WORKSPACE_SYSTEM_HARDENED, WORKSPACE_TOOLS,
)

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

VICTIM_CONFIGS = {
    "ecommerce":     {"starter": ECOMMERCE_STARTER, "hardened": ECOMMERCE_HARDENED, "tools": ECOMMERCE_TOOLS},
    "dental":        {"starter": DENTAL_STARTER,    "hardened": DENTAL_HARDENED,    "tools": DENTAL_TOOLS},
    "dev_assistant": {"starter": DEV_STARTER,       "hardened": DEV_HARDENED,       "tools": DEV_TOOLS},
    "banking":       {"starter": BANKING_SYSTEM_STARTER,   "hardened": BANKING_SYSTEM_HARDENED,   "tools": BANKING_TOOLS},
    "workspace":     {"starter": WORKSPACE_SYSTEM_STARTER, "hardened": WORKSPACE_SYSTEM_HARDENED, "tools": WORKSPACE_TOOLS},
}


def run_multi_turn(
    attack: dict,
    victim_name: str,
    model: str = "gpt-4o-mini",
    tier: str = "starter",
) -> dict:
    """Run a multi-turn attack — feed each turn, maintain conversation state."""
    config = VICTIM_CONFIGS[victim_name]
    system_prompt = config["hardened"] if tier == "hardened" else config["starter"]
    messages = [{"role": "system", "content": system_prompt}]
    all_texts = []
    all_tool_calls = []
    total_tokens = 0

    for turn_text in attack["turns"]:
        messages.append({"role": "user", "content": turn_text})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=config["tools"],
            tool_choice="auto",
        )
        msg = response.choices[0].message
        total_tokens += response.usage.total_tokens

        text = msg.content or ""
        all_texts.append(text)

        new_tool_calls = [
            {"name": tc.function.name, "arguments": tc.function.arguments}
            for tc in (msg.tool_calls or [])
        ]
        all_tool_calls.extend(new_tool_calls)

        # Append assistant message to messages for next turn
        if msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })
            # Synthetic tool responses so the model can continue
            for tc in msg.tool_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": '{"status": "ok"}',
                })
        else:
            messages.append({"role": "assistant", "content": text})

    return {
        "victim": victim_name,
        "tier": tier,
        "model": model,
        "response_text": "\n---TURN---\n".join(all_texts),
        "tool_calls": all_tool_calls,
        "tokens_used": total_tokens,
    }
