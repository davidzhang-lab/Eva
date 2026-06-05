"""
connector.py — sends one message to a target agent over an OpenAI-compatible
endpoint. Captures the response (text + any tool calls the agent tried to
make). Capture-only — does NOT execute tool calls.

Special case: target_endpoint == "demo" routes the call in-process to
examples.demo_agent instead of over HTTP. Avoids needing to spin up a local
server for the bundled demo.

This file is stateless. Multi-turn conversation state is managed by the
runner, which passes a growing `conversation_history` on each call.
"""

import json
import time
from typing import Optional

from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError


def _build_messages(
    attack_prompt: str,
    conversation_history: Optional[list[dict]],
) -> list[dict]:
    """Append the attack prompt as a user message onto any existing history."""
    if conversation_history:
        return list(conversation_history) + [{"role": "user", "content": attack_prompt}]
    return [{"role": "user", "content": attack_prompt}]


def _normalize_tool_calls(raw_tool_calls) -> list[dict]:
    """Flatten OpenAI's tool_calls objects into [{name, arguments, id}] dicts.
    Always emits arguments as a string (JSON-encoded if dict)."""
    out: list[dict] = []
    for tc in raw_tool_calls or []:
        # New-style: tc has .function.name + .function.arguments + .id
        name = getattr(getattr(tc, "function", None), "name", None) or tc.get("name", "")
        args = getattr(getattr(tc, "function", None), "arguments", None)
        if args is None:
            args = tc.get("arguments", "{}")
        if not isinstance(args, str):
            try:
                args = json.dumps(args)
            except Exception:
                args = "{}"
        tc_id = getattr(tc, "id", None) or tc.get("id")
        out.append({"name": name, "arguments": args, "id": tc_id})
    return out


def send_attack(
    target_endpoint: str,
    target_api_key: str,
    target_model: str,
    attack_prompt: str,
    conversation_history: Optional[list[dict]] = None,
    tools: Optional[list[dict]] = None,
    timeout_seconds: int = 30,
    max_retries: int = 3,
) -> dict:
    """Send one attack and capture the agent's response. Stateless.

    Returns AgentResponse-shaped dict:
      {
        "response_text": str,
        "tool_calls": [{"name": str, "arguments": str, "id": str}, ...],
        "latency_ms": int,
        "tokens_used": int,
        "error": Optional[str],
      }
    """
    # In-process route for the bundled demo
    if target_endpoint == "demo":
        from .examples.demo_agent import call_demo
        return call_demo(attack_prompt, conversation_history=conversation_history)

    messages = _build_messages(attack_prompt, conversation_history)
    client = OpenAI(
        api_key=target_api_key,
        base_url=target_endpoint if target_endpoint.startswith("http") else None,
        timeout=timeout_seconds,
    )

    last_err = None
    for attempt in range(max_retries):
        start = time.time()
        try:
            kwargs = {"model": target_model, "messages": messages}
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            response = client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
            return {
                "response_text": msg.content or "",
                "tool_calls": _normalize_tool_calls(getattr(msg, "tool_calls", None)),
                "latency_ms": int((time.time() - start) * 1000),
                "tokens_used": getattr(getattr(response, "usage", None), "total_tokens", 0) or 0,
                "error": None,
            }
        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            last_err = e
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
        except APIError as e:
            # Non-retryable API errors (auth, malformed request) — fail fast
            return {
                "response_text": "",
                "tool_calls": [],
                "latency_ms": int((time.time() - start) * 1000),
                "tokens_used": 0,
                "error": f"{type(e).__name__}: {e}",
            }
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)

    return {
        "response_text": "",
        "tool_calls": [],
        "latency_ms": 0,
        "tokens_used": 0,
        "error": f"max retries exhausted: {type(last_err).__name__}: {last_err}" if last_err else "unknown error",
    }
