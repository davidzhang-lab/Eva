# Eva — Mission

## The one-liner

Eva is an evaluator for AI agents. Each version of Eva tackles one way agents fail (v1: prompt injection, v2: hallucinations, v3: TBD). After ~3 versions I synthesize them into "Eva" and publish.

## Who it's for

**Eventually:** founders shipping their own AI agent in production — the people who need to know what their own agent breaks on before customers find out. Auditors and labs come later. Never first.

**Right now (v1, v2, v3):** me. Each version is a personal R&D iteration. I'm learning by building. YouTube audience watches.

## Why now

Two stories, both true.

**The bet.** AI is in a bubble. OpenAI loses money on every API call, big labs prop each other up, real-world freelance jobs fail at 96% under AI. After every tech bubble, the same pattern:

- post-.com → cybersecurity testing became mandatory
- post-2008 → financial stress tests became mandatory
- post-AI correction → AI evaluation/auditing follows the same pattern

Technology survives. Trust collapses. Proving AI works becomes infrastructure. Eva is built for that moment.

**The path.** I'm 17 and I have deep theory but no hands-on judgment yet. So I build it the only way that actually works: one problem at a time, in public. Each version teaches me one part of the eval landscape by building it.

## What Eva is — and isn't

**Eva v1:**
- Fires direct + indirect prompt injection attacks at an AI agent and analyzes which ones got through.
- Detects and analyzes — does NOT fix. The builder fixes their own agent. ("Deal with, not solve" — prompt injection is hard enough by itself.)
- Evaluates one agent against one model. No model comparison in v1.
- For me, not customers yet.

**Published Eva (eventually) WILL be:**
- Multiple eval dimensions stitched together (injection + hallucination + more)
- Production logs / observability — yes, in scope
- Feedback to builders (suggested defenses) — eventually

**Published Eva will NEVER be:**
- An academic benchmark optimized for citations.
- A general dev observability tool fighting Datadog/Sentry. Audit-grade eval is the bet.

## How I work with Friday

Friday is the coder. I'm the architect.

- **Design decisions** (what to build, scope): Friday asks until ~95% sure, then writes code. I review.
- **Implementation**: Friday writes piece by piece, narrating what + why. Pair-style. I can interrupt anywhere.
- **Small reversible choices** (pytest vs custom runner, library X vs Y): Friday decides, briefly explains, moves on. I push back if I disagree.
- **Big choices with real downstream consequences** (architecture, scope creep): Friday stops and asks first.
- **Knowledge drops** (Inspect notes now, PyRIT later): I drop them into `Eva/inbox/`. Friday reads carefully, asks pointed questions, doesn't pretend to understand silently. Decisions affecting Eva graduate from inbox into MISSION.md or memory.

## Where I am right now

(2026-05-05)

- Phase 1 (theory) done. ~38 pages of handwritten notes absorbed into Friday's memory.
- Folder reset. Eva-v.1 prototype scrapped. Master plan deleted. Fresh slate.
- Currently studying Inspect AI hands-on. PyRIT is next.
- About to build Eva v1 (prompt injection eval) once Inspect ingestion is done.

## Open questions

(Unresolved decisions live here so they don't get lost between sessions.)

- Distribution and output format for v1 (CLI? library? terminal? HTML? JSON?) — set aside until after Inspect ingestion.
- v3's specific focus (after injection and hallucinations).
- Publish trigger: committed to ~3 versions, but is that a fixed count or "when it feels ready"?
- Whether Eva should ever run injection-resistance comparison across models (skipped for v1; may revisit at v2 or at synthesis).
