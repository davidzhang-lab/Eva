# Inspect AI — notes from public sources

Source 1: [Neural Creators review](https://neurlcreators.substack.com/p/inspect-ai-evaluation-framework-review) (Sept 2025, v0.3.130)
Source 2: [AISI 2025 year-in-review](https://www.aisi.gov.uk/blog/our-2025-year-in-review)

These are Friday's notes from open-web research, distinct from David's curated notes (still pending).

---

## What Inspect AI is, in one sentence

An open-source Python framework from the UK AI Security Institute for building reproducible agent evaluations — installed via `pip install inspect-ai`, MIT-licensed, Python ≥3.10.

## Architecture (the pipeline)

```
Dataset → Task → Solver → Scorer
```

- **Task** = the bundle (declarative). Decorated with `@task`.
- **Dataset** = JSON / CSV / Hugging Face / custom, fed as `Sample` objects.
- **Solver** = how the model produces the answer. Chain-of-thought, ReAct agents, multi-turn, self-critique, multi-agent composition. Built-in tool support (bash, Python, text-edit, web_search, web_browser, computer). MCP support.
- **Scorer** = how the answer is graded. Exact match, F1, pass@k, model-graded, bootstrap confidence intervals, custom regex/logic.

**Hello-world example from the review:**

```python
from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import generate
from inspect_ai.scorer import exact

@task
def hello_world():
    return Task(
        dataset=[Sample(input="Just reply with Hello World",
                       target="Hello World")],
        solver=[generate()],
        scorer=exact(),
    )
```

Run: `inspect eval hello.py --model openai/gpt-4o`

## What Inspect ships that's relevant to Eva

- **15+ model providers** through one interface (OpenAI, Anthropic, Google, xAI, Bedrock, Azure, vLLM/Ollama, etc.) — Eva can reuse this instead of writing its own.
- **Inspect View** — a live web GUI for browsing trace logs (prompts, responses, tokens, cost, scorer heatmaps).
- **VS Code extension** `ukaisi.inspect-ai` for running/debugging.
- **Sandboxing tiers:** Docker (built-in), Kubernetes (per-sample pods with allowlists), Proxmox VM (community).
- **Policy enforcement:** token limits, CPU-time / clock-time budgets, message count caps.
- **Agent bridges** for AutoGen and LangChain (so an existing agent can be evaluated without porting it).
- **CLI ergonomics:** `--limit`, `--seed`, retry/resume, batch mode, eval-set slicing, caching.

## Where Inspect explicitly is not strong (per the review)

- **Lightweight static benchmarks** — too heavy, learning curve.
- **Simple text-in/text-out evals** without tools — overhead unjustified.
- **No-Docker environments** — sandboxing assumes container infra.
- **Imperative code preference** — Inspect is declarative/DSL.
- vs PromptFoo: PromptFoo is faster/lighter for one-off static comparisons.

## What AISI did with Inspect in 2025

- Tested **30+ frontier models** with it.
- Found **62,000 vulnerabilities** in an agent red-team competition with Grey Swan.
- Found **"dozens of universal jailbreak paths"** in biosecurity red-teaming with OpenAI + Anthropic.
- Released sister tools: **InspectSandbox**, **InspectCyber**, **ControlArena** (newest).
- Adopted by METR, Apollo Research, frontier labs.

## Evidence for Eva's bubble/post-correction thesis

The AISI year-in-review is essentially a real-world case study of David's thesis:
- Government safety institute built audit-grade infra (Inspect) → frontier labs (Anthropic, OpenAI, DeepMind) actively partner with them on red-team work.
- 62K vulnerabilities in one agent competition = the gap is huge.
- "Sandbagging detection" is a new technique they're developing (models hiding their capabilities) — this is post-correction territory.

This isn't proof of the bubble narrative, but it's strong evidence the **audit infrastructure layer is materializing** — exactly where Eva positions itself.

---

## Friday's design questions for David (the big ones)

### 1. Build *on top of* Inspect, or build *standalone*?

This is THE architectural fork for Eva v1. Two clean options:

**Option A — Eva v1 is an Inspect plugin.** Eva v1 = a curated set of injection-specific solvers, scorers, and tasks distributed as an `inspect-eva` Python package. Users install Inspect and Eva, run `inspect eval eva-injection.py`. Reuses Inspect's sandbox, multi-vendor models, view, VS Code extension.
- *Pro:* You ship v1 fast (weeks not months). Riding government-backed infra means audit-grade trail comes for free. Fits "v1 is a learning project" — you learn injection deeply without rebuilding eval infrastructure.
- *Con:* Eva is dependent on Inspect for its lifetime. If Inspect makes a breaking change you don't like, you're stuck. The "proxy-connector" design in your memory doesn't quite fit — Inspect's model is task-runner, not proxy.

**Option B — Eva v1 standalone.** Eva ships its own runner, scorer, model abstraction. Inspect is studied, not depended on.
- *Pro:* Eva owns its architecture. The proxy-connector design from your memory works cleanly. Free to diverge later.
- *Con:* Months to build what Inspect already gives. Risk of v1 drowning in plumbing instead of injection research.

**Option C — Hybrid.** Eva v1 uses Inspect's *primitives* (model abstraction, scorer, task) but adds its own injection-specific orchestration layer (the proxy-connector lives outside, intercepts traffic, then formats results into Inspect Tasks for grading).
- *Pro:* Best of both. Some divergence, some reuse.
- *Con:* More integration thinking. Need to be careful about what's "ours" vs "borrowed."

### 2. Output format — could you just use Inspect View?

Open question in MISSION.md is "what does Eva v1 output." If you go with Option A or C above, **Eva v1's output is just Inspect log files, viewed in Inspect View.** You don't build your own UI. That decision drops out for free.

### 3. Sandboxing — do you need it for v1?

For injection evaluation, the agent-under-test is doing things based on injected prompts. If the agent has tools (bash, web), sandboxing matters a lot. For v1, do you assume the agent-under-test has no tools (just text-in/text-out)? Or do you need Docker isolation from day 1?

### 4. Injection corpus — where do attacks come from?

Eva v1 needs injection prompts to fire at agents. Options:
- HarmBench (you already studied it) — broad harm, includes some injection.
- The Grey Swan / AISI 62K vulnerability set — most likely not public.
- Tensor Trust / Gandalf — public direct injection datasets.
- Synthesize via LLM — you generate injections programmatically.

You'll need to choose. Probably mix.
