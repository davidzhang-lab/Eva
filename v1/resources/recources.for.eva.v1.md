# Eva v1 — Inspiration Code & Documentation Links

Direct GitHub source files and documentation URLs for every project requested, organized for studying implementations relevant to a prompt-injection-testing AI agent eval tool for SMBs. Where a URL points to a directory tree (`/tree/`) rather than a blob (`/blob/`), browse the tree to see the full file list — GitHub's interactive listing is the most current authoritative source for filenames that change between PyRIT/inspect_ai releases.

---

## Project 1 — Inspect AI (UK AISI)

**Repo:** https://github.com/UKGovernmentBEIS/inspect_ai
**Docs:** https://inspect.aisi.org.uk

### Core architecture (source files)
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/_eval/task/task.py — The `Task` class definition (binds dataset + solver + scorer into the fundamental unit of evaluation).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/solver/_solver.py — `Solver` and `Generate` protocols, plus the `@solver` decorator implementation and the built-in `generate()` solver.
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/solver/_task_state.py — `TaskState` — the mutable state object that flows through every solver.
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/scorer/_scorer.py — `Scorer` protocol and the `@scorer` decorator.
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/dataset/_dataset.py — `Dataset`, `Sample`, and `MemoryDataset` abstractions.
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/model/_model.py — `Model` / `ModelAPI` base class and `get_model()` (the universal provider abstraction).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/log/_log.py — `EvalLog` / `EvalSample` (the eval-log schema; includes `EvalConfig` and structured per-sample results).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/log/_transcript.py — Transcript / event-stream implementation (per-step traces for the log viewer).
- https://github.com/UKGovernmentBEIS/inspect_ai/tree/main/src/inspect_ai/agent — Agent package root (agents, bridges).

### Agent Bridge (key "evaluate any external agent" primitive)
- https://github.com/UKGovernmentBEIS/inspect_ai/tree/main/src/inspect_ai/agent/_bridge — Implementations of `agent_bridge()` (in-process OpenAI-API monkey-patch) and `sandbox_agent_bridge()` (proxy server inside sandbox container).
- https://inspect.aisi.org.uk/agent-bridge.html — Agent Bridge docs (OpenAI Agents SDK / LangChain / Pydantic AI / Claude Code / Codex CLI integration patterns).

### Built-in solvers
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/solver/_solver.py — `generate()` solver (the default model-calling solver).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/solver/_prompt.py — `system_message()`, `prompt_template()`, `chain_of_thought()`.
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/solver/_multiple_choice.py — `multiple_choice()` solver (option-shuffling, answer-mapping).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/solver/_use_tools.py — `use_tools()` solver (binds tools to the next `generate()`).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/solver/_basic_agent.py — `basic_agent()` — reference ReAct-style agent loop (great starting point for Eva's agent harness).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/solver/_critique.py — `self_critique()` solver.

### Built-in scorers
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/scorer/_match.py — `match()`, `includes()`, `exact()` text-comparison scorers.
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/scorer/_model.py — `model_graded_qa()` and `model_graded_fact()` (LLM-as-judge — directly relevant for grading prompt-injection outcomes).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/scorer/_classification.py — F1 and classification scorers.
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/scorer/_metrics.py — `accuracy()`, `mean()`, `stderr()`, bootstrap metrics.

### Model providers (study OpenAI/Anthropic implementations)
- https://github.com/UKGovernmentBEIS/inspect_ai/tree/main/src/inspect_ai/model/_providers — All provider implementations.
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/model/_providers/openai.py — OpenAI provider.
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/model/_providers/anthropic.py — Anthropic provider.

### Documentation pages
- https://inspect.aisi.org.uk/tutorial.html — Tutorial (best entry point — covers the "Hello, Inspect" example end-to-end).
- https://inspect.aisi.org.uk/tasks.html — Tasks reference.
- https://inspect.aisi.org.uk/datasets.html — Datasets reference (Sample / MemoryDataset / FieldSpec).
- https://inspect.aisi.org.uk/solvers.html — Solvers reference.
- https://inspect.aisi.org.uk/scorers.html — Scorers reference.
- https://inspect.aisi.org.uk/reference/inspect_ai.scorer.html — `inspect_ai.scorer` API reference (full signatures for `match`, `includes`, `model_graded_qa`, etc.).
- https://inspect.aisi.org.uk/agent-bridge.html — Agent Bridge.
- https://inspect.aisi.org.uk/agents.html — Agents overview.
- https://inspect.aisi.org.uk/providers.html — Model Providers.
- https://inspect.aisi.org.uk/tools.html — Tools (custom + standard).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/CHANGELOG.md — Changelog (track recent agent-bridge / scorer changes).
- https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/README.md — Repo README.

---

## Project 2 — inspect_evals (UK AISI)

**Repo:** https://github.com/UKGovernmentBEIS/inspect_evals
**Eval listing site:** https://ukgovernmentbeis.github.io/inspect_evals/

### Repo-level
- https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/README.md — Main README (full eval catalog).
- https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/_registry.py — Central import registry — best file to scan to see every available eval.
- https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/pyproject.toml — Optional-dependency groups (`agentdojo`, `agentharm`, `gdm_capabilities`, etc.).

### AgentDojo eval (the most directly relevant — prompt-injection benchmark for tool-using agents)
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/agentdojo — Folder root. Browse here for the full file list; the AISI version supersedes the NIST fork as of 2025-10-23 (https://github.com/usnistgov/agentdojo-inspect now points here).
- https://ukgovernmentbeis.github.io/inspect_evals/evals/safeguards/agentdojo/ — Published eval docs page (all task parameters: `attack`, `agent`, `with_injections`, `with_sandbox_tasks`, `user_task_ids`, `injection_task_ids`).
- https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/agentdojo/agentdojo.py — Main `@task` entrypoint (exports `agentdojo` imported in `_registry.py`).
- https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/agentdojo/README.md — AgentDojo-in-Inspect README.
- https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/agentdojo/__init__.py — Module exports.
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/agentdojo/task_suites — `task_suites/` subfolder (banking, slack, travel, workspace, workspace_plus).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/agentdojo/data/suites — Data folder containing suite YAML definitions (`workspace.yaml`, `workspace_plus/terminal/...`, etc., confirmed via `.pre-commit-config.yaml` patterns).
- https://github.com/usnistgov/agentdojo-inspect — Predecessor NIST fork (archived; useful for reading the original Inspect-bridge code that the AISI version derived from).

### Other prompt-injection / safety / jailbreak evals
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/agentharm — AgentHarm (176 harmful-agent-behaviour samples + 176 benign).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/ipi_coding_agent — Indirect prompt injection in coding agents (issue descriptions, code comments, README files; scores injection resistance, task completion, and detection).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/cyberseceval_2 — Meta CybersecEval 2 (includes a `cyse2_prompt_injection` task — direct prompt-injection benchmark).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/cyberseceval_3 — CybersecEval 3 (`cyse3_visual_prompt_injection`).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/agentic_misalignment — Anthropic-style scenarios (e.g., blackmail under replacement threat).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/b3 — B3 agentic-AI security benchmark (data exfiltration, content injection, decision/behavior manipulation, DoS, content-policy bypass).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/fortress — FORTRESS (500 expert-crafted adversarial prompts with instance-based rubrics of 4–7 binary questions across 3 domains — CBRNE, Political Violence & Terrorism, and Criminal & Financial Illicit Activities — with 10 total subcategories; arXiv:2506.14922).

### Cybench (tool-using agent reference pattern)
- https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/cybench/cybench.py — Cybench task using `react()` agent with `bash()` + `python()` tools and `includes()` scorer (excellent reference for Eva's "agent + tools" pattern).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/cybench — Folder root.

### GDM dangerous-capabilities evals
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/gdm_capabilities — Root folder (covers `gdm_intercode_ctf`, `gdm_in_house_ctf`, `classifier_evasion`, `cover_your_tracks`, `oversight_pattern`, `strategic_rule_breaking`, and more).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/gdm_capabilities/intercode_ctf — InterCode CTF (100 easy picoCTF challenges covering general Linux skills, reverse engineering, cryptography, forensics, binary exploitation, and web exploitation with bash + python tools in Docker).
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/gdm_capabilities/stealth — Stealth challenges.
- https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/gdm_self_proliferation — 10 real-world–inspired self-proliferation tasks (email setup, model installation, web agent setup, wallet operations) supporting end-to-end, milestones, and expert best-of-N modes.

### HarmBench wrapper
- No first-party HarmBench *task* wrapper exists in inspect_evals at this writing; the HarmBench *dataset* is referenced by some evals. Use the HarmBench repo directly (Project 5) for behaviors/classifier.

---

## Project 3 — PyRIT (Microsoft)

**Repo:** https://github.com/microsoft/PyRIT (canonical; the legacy `Azure/PyRIT` URL still resolves).
**Docs:** https://microsoft.github.io/PyRIT/

### Architecture overview
- https://github.com/Azure/PyRIT/blob/main/doc/code/architecture.md — Architecture doc (attacks / converters / targets / scorers / memory components).
- https://github.com/microsoft/PyRIT/blob/main/.pyrit_conf_example — Example PyRIT YAML config (memory_db_type, initializers, default targets/scorers).

### Attacks / Orchestrators (Crescendo / PAIR / TAP / RedTeaming family)
> Since PyRIT 0.8 orchestrators were refactored into `pyrit.executor.attack`. Crescendo / PAIR / TAP / RedTeaming are now subclasses of `MultiTurnAttackStrategy` / `AttackStrategy`.
- https://github.com/microsoft/PyRIT/tree/main/pyrit/executor/attack — Attack package root (browse to see exact file names — they have been renamed multiple times).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/executor/attack/multi_turn/crescendo.py — `CrescendoAttack` (gradual multi-turn escalation, Russinovich et al. 2024).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/executor/attack/multi_turn/tree_of_attacks.py — `TAPAttack` / `TreeOfAttacksWithPruningAttack` (parallel-branch search with pruning).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/executor/attack/multi_turn/pair.py — `PAIRAttack` (Prompt Automatic Iterative Refinement).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/executor/attack/multi_turn/red_teaming.py — `RedTeamingAttack` (general adversarial-chat multi-turn).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/executor/attack/single_turn/prompt_sending.py — `PromptSendingAttack` (single-turn baseline — closest analog to Eva's first iteration).

### Converters (prompt transformations — Eva should mirror the stacking pattern)
- https://github.com/microsoft/PyRIT/tree/main/pyrit/prompt_converter — All 70+ converters.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_converter/prompt_converter.py — `PromptConverter` base class.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_converter/base64_converter.py — Base64 encoding.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_converter/rot13_converter.py — ROT13.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_converter/leetspeak_converter.py — Leetspeak.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_converter/translation_converter.py — LLM-powered translation converter.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_converter/role_play_converter.py — Role-play converter.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_converter/variation_converter.py — Variation converter (LLM produces N variations of a prompt).

### Targets (PromptTarget implementations)
- https://github.com/microsoft/PyRIT/tree/main/pyrit/prompt_target — All targets.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_target/openai/openai_chat_target.py — `OpenAIChatTarget` (handles Azure OpenAI, OpenAI, Ollama, Groq, OpenRouter via OpenAI-compatible API).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_target/openai/openai_response_target.py — OpenAI Responses API target.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_target/common/prompt_chat_target.py — `PromptChatTarget` base.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/prompt_target/http_target.py — Generic HTTP target — directly applicable for pointing Eva at any agent endpoint.

### Scorers
- https://github.com/microsoft/PyRIT/blob/main/pyrit/score/scorer.py — Base `Scorer` abstract class.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/score/self_ask_true_false_scorer.py — `SelfAskTrueFalseScorer` (LLM judge, binary).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/score/self_ask_likert_scorer.py — Likert-scale LLM judge.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/score/general_scorer.py — `SelfAskGeneralScorer` (flexible output format).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/score/substring_scorer.py — Simple substring scorer.

### Memory / data store
- https://github.com/microsoft/PyRIT/tree/main/pyrit/memory — Memory module.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/memory/memory_interface.py — `MemoryInterface` abstract base.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/memory/central_memory.py — `CentralMemory` (singleton accessor).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/memory/duckdb_memory.py — DuckDB implementation (default local store).
- https://github.com/microsoft/PyRIT/blob/main/pyrit/memory/azure_sql_memory.py — Azure SQL implementation.
- https://github.com/microsoft/PyRIT/blob/main/pyrit/memory/memory_models.py — ORM schema (PromptMemoryEntries, EmbeddingData, ScoreEntries).

### Attack datasets and seed prompts
- https://github.com/microsoft/PyRIT/tree/main/pyrit/datasets — Built-in seed-prompt datasets (AIRT, HarmBench, AdvBench, XSTest, many-shot — 53+ datasets).
- https://github.com/microsoft/PyRIT/tree/main/pyrit/datasets/seed_prompts — YAML seed prompts.

### Documentation pages
- https://azure.github.io/PyRIT/code/orchestrators/0_orchestrator.html — Orchestrators / Attacks overview.
- https://microsoft.github.io/PyRIT/code/executor/attack/crescendo-attack/ — Crescendo Attack walkthrough.
- https://azure.github.io/PyRIT/code/executor/attack/tap_attack.html — TAP Attack walkthrough.
- https://microsoft.github.io/PyRIT/code/converters/text-to-text-converters/ — Text-to-text converters overview.
- https://azure.github.io/PyRIT/blog/2024_12_3.html — Multi-Turn orchestrators design blog (explains the unification under `MultiTurnOrchestrator` / `AttackStrategy`).
- https://azure.github.io/PyRIT/code/targets/0_prompt_targets.html — Prompt Targets overview.
- https://azure.github.io/PyRIT/code/targets/1_openai_chat_target.html — OpenAI Chat Target docs.
- https://microsoft.github.io/PyRIT/code/targets/http-target/ — HTTP Target (testing your own agent endpoints).
- https://azure.github.io/PyRIT/code/memory/1_duck_db_memory.html — DuckDB memory + schema.
- https://microsoft.github.io/PyRIT/code/datasets/loading-datasets/ — Loading built-in datasets.

---

## Project 4 — AgentDojo (original, ETH Zurich)

**Repo:** https://github.com/ethz-spylab/agentdojo
**Paper:** arXiv:2406.13352, published at NeurIPS 2024 Datasets and Benchmarks Track (Debenedetti et al.); benchmark contains 97 realistic tasks and 629 security test cases.
**Docs site:** https://agentdojo.spylab.ai

### Repo / package
- https://github.com/ethz-spylab/agentdojo — Repo root.
- https://github.com/ethz-spylab/agentdojo/blob/main/README.md — README.
- https://github.com/ethz-spylab/agentdojo/tree/main/src/agentdojo — Package source root.

### Attacks (the canonical prompt-injection attack catalog to reproduce in Eva)
- https://github.com/ethz-spylab/agentdojo/tree/main/src/agentdojo/attacks — All attack implementations.
- https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/attacks/base_attacks.py — `BaseAttack` and `FixedJailbreakAttack` (template-substitution attack base class).
- https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/attacks/baseline_attacks.py — `IgnorePreviousAttack`, `SystemMessageAttack`, `InjecAgentAttack`, `ImportantInstructionsAttack` — the canonical baselines.
- https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/attacks/attack_registry.py — Registry mapping attack names to classes.
- https://agentdojo.spylab.ai/api/attacks/base_attacks/ — Base Attacks API doc.
- https://agentdojo.spylab.ai/api/attacks/baseline_attacks/ — Baseline Attacks API doc.

### Task definitions (user tasks & injection tasks)
- https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/base_tasks.py — `BaseUserTask` and `BaseInjectionTask` (core abstractions every concrete task subclasses).
- https://agentdojo.spylab.ai/api/base_tasks/ — Base User/Injection Tasks API doc.

### Benchmark suite (banking, slack, travel, workspace)
- https://github.com/ethz-spylab/agentdojo/tree/main/src/agentdojo/default_suites — Default suite definitions root.
- https://github.com/ethz-spylab/agentdojo/tree/main/src/agentdojo/default_suites/v1/banking — Banking suite (user tasks, injection tasks, environment, tools).
- https://github.com/ethz-spylab/agentdojo/tree/main/src/agentdojo/default_suites/v1/slack — Slack suite.
- https://github.com/ethz-spylab/agentdojo/tree/main/src/agentdojo/default_suites/v1/travel — Travel suite.
- https://github.com/ethz-spylab/agentdojo/tree/main/src/agentdojo/default_suites/v1/workspace — Workspace (email/calendar/cloud-drive) suite.
- https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/task_suite/task_suite.py — `TaskSuite` class.

### Benchmark / judge / evaluation
- https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/benchmark.py — `benchmark_suite_with_injections()` and `benchmark_suite_without_injections()` — utility/security scoring uses formal post-conditions on environment state, **not** an LLM judge (key design choice for robustness).
- https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/scripts/benchmark.py — CLI entrypoint.
- https://github.com/ethz-spylab/agentdojo/tree/main/src/agentdojo/agent_pipeline — Pipeline elements: tool-filter defense, prompt-injection-detector defense, etc.

---

## Project 5 — HarmBench (Center for AI Safety)

**Repo:** https://github.com/centerforaisafety/HarmBench

### Behaviors / prompts
- https://github.com/centerforaisafety/HarmBench/tree/main/data/behavior_datasets — Behavior dataset directory.
- https://github.com/centerforaisafety/HarmBench/blob/main/data/behavior_datasets/harmbench_behaviors_text_all.csv — All text behaviors CSV (400 prompts across 7 named semantic categories — Cybercrime & Unauthorized Intrusion, Chemical & Biological Weapons/Drugs, Copyright Violations, Misinformation & Disinformation, Harassment & Bullying, Illegal Activities, and General Harm — per Mazeika et al., arXiv:2402.04249).
- https://github.com/centerforaisafety/HarmBench/blob/main/data/behavior_datasets/harmbench_behaviors_text_test.csv — Test split (320 prompts).
- https://github.com/centerforaisafety/HarmBench/blob/main/data/behavior_datasets/harmbench_behaviors_text_val.csv — Validation split (80 prompts).
- https://github.com/centerforaisafety/HarmBench/blob/main/data/behavior_datasets/harmbench_behaviors_multimodal_all.csv — Multimodal (vision) behaviors (110 prompts).

### Classifier (judge)
- https://huggingface.co/cais/HarmBench-Llama-2-13b-cls — Finetuned Llama-2-13B classifier (Hugging Face model card; the canonical HarmBench judge).
- https://github.com/centerforaisafety/HarmBench/blob/main/evaluate_completions.py — Top-level classifier-driven evaluation script.
- https://github.com/centerforaisafety/HarmBench/tree/main/eval_utils — Eval utilities (including classifier prompt templates).
- https://github.com/centerforaisafety/HarmBench/blob/main/docs/evaluation_pipeline.md — 3-step pipeline doc (generate test cases → completions → classify).

### Attack method implementations
- https://github.com/centerforaisafety/HarmBench/tree/main/baselines — All baseline attack methods.
- https://github.com/centerforaisafety/HarmBench/blob/main/baselines/__init__.py — Method registry mapping name → class.
- https://github.com/centerforaisafety/HarmBench/blob/main/baselines/baseline.py — `RedTeamingMethod` abstract base class.
- https://github.com/centerforaisafety/HarmBench/tree/main/baselines/gcg — GCG (Greedy Coordinate Gradient) attack.
- https://github.com/centerforaisafety/HarmBench/tree/main/baselines/pair — PAIR attack.
- https://github.com/centerforaisafety/HarmBench/tree/main/baselines/tap — TAP attack.
- https://github.com/centerforaisafety/HarmBench/tree/main/baselines/autodan — AutoDAN attack.
- https://github.com/centerforaisafety/HarmBench/blob/main/baselines/human_jailbreaks/jailbreaks.py — Manual / "human" jailbreaks (DAN, etc.).
- https://github.com/centerforaisafety/HarmBench/blob/main/README.md — Main README.
- https://github.com/centerforaisafety/HarmBench/blob/main/docs/codebase_structure.md — Codebase structure doc.

---

## Project 6 — Other related

### OWASP LLM Top 10 (2025 latest)
- https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/ — Landing page for the 2025 edition.
- https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf — Full PDF of the 2025 document (LLM01 Prompt Injection, LLM02 Sensitive Info Disclosure, ..., LLM07 System Prompt Leakage, LLM08 Vector and Embedding Weaknesses, LLM09 Misinformation, LLM10 Unbounded Consumption).
- https://genai.owasp.org/llm-top-10/ — Archive of individual entry pages.

### Simon Willison — prompt injection
- https://simonwillison.net/tags/prompt-injection/ — Tag page (the canonical running index of his prompt-injection writing).
- https://simonwillison.net/series/prompt-injection/ — Long-form series page.
- https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/ — "The lethal trifecta for AI agents: private data, untrusted content, and external communication" (Jun 16, 2025) — coined "lethal trifecta," the most-cited threat model for agentic prompt injection.
- https://simonwillison.net/2025/Nov/2/new-prompt-injection-papers/ — "New prompt injection papers: Agents Rule of Two and The Attacker Moves Second" (Nov 2, 2025).
- https://simonwillison.net/2025/Apr/11/camel/ — "CaMeL offers a promising new direction for mitigating prompt injection attacks" (Apr 11, 2025).
- https://simonwillison.net/2025/Aug/26/piloting-claude-for-chrome/ — "Piloting Claude for Chrome" (Aug 26, 2025) — critique of Claude for Chrome's prompt-injection mitigations.

### Anthropic prompt-injection research
- https://www.anthropic.com/research/prompt-injection-defenses — "Mitigating the risk of prompt injections in browser use" (Nov 24, 2025) — Claude Opus 4.5 robustness, Claude for Chrome beta.
- https://www.anthropic.com/news/prompt-injection-defenses — News version of the same post.
- https://www.anthropic.com/research/trustworthy-agents — "Trustworthy agents" research post (prompt-injection risks for Claude Code, Claude Cowork, MCP).
- https://www.anthropic.com/research/teaching-claude-why — "Teaching Claude why" — discusses the agentic-misalignment evaluation (Claude Haiku 4.5+ score 0%).
- https://github.com/anthropic-experimental/agentic-misalignment — Anthropic-released open-source framework for fictional-scenario agentic-misalignment evaluations.

### OpenAI Chat Completions API reference
- https://platform.openai.com/docs/api-reference/chat — Chat Completions API reference.
- https://platform.openai.com/docs/api-reference/chat/create — `POST /v1/chat/completions` endpoint (request/response schema for the canonical model API Eva targets).

---

## Verification & Usage Notes
- A small number of URLs (specifically the individual `.py` filenames inside `src/inspect_evals/agentdojo/`, the post-refactor PyRIT `pyrit/executor/attack/multi_turn/*.py` filenames, and HarmBench `baselines/<method>/` subfolder layouts) follow conventional naming that matches all surrounding evidence (README references, import statements in `_registry.py`, the architecture doc, and the doc-site examples), but the individual blob pages are not indexed by general web search. Open each directory `/tree/` URL to confirm the exact current filenames if a `/blob/` URL 404s — directory contents change across releases.
- For PyRIT, the legacy `Azure/PyRIT` GitHub URLs all redirect to `microsoft/PyRIT` since the 2025 repo rename; either form works in browser, but for new bookmarks prefer `microsoft/PyRIT`.
- The Inspect Evals catalog evolves quickly (registration of new evals moved to a `register/` YAML system on 8 May 2026); for the most current list of prompt-injection-relevant evals, scan `src/inspect_evals/_registry.py` after each `inspect_evals` release rather than relying on a fixed list.