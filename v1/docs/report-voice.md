# Eva v1 — report voice

This doc defines the voice and style of the `report.md` Eva produces. It's the source of truth that overrides any default LLM writing instincts in the reporter. When in doubt, return here.

## Why this exists

The reporter is the most user-facing component of Eva v1. Without an explicit voice anchor, LLM-generated copy drifts toward one of two failure modes:

- **Marketing fluff** — "Comprehensive analysis reveals significant vulnerabilities…"
- **Hedged academia** — "It appears that this attack may have potentially succeeded…"

Eva is neither. This doc keeps the reporter aligned.

## Who reads the report (right now)

**v1 reality:** the report is read by the engineer or founder who ran `eva run`. They're technical enough to ship an AI agent. They want to know: which attacks landed, exactly what the agent did, and what to fix.

**Where Eva is going:** the architecture (§4.6) positions the eventual unified Eva as plain-language for the SMB owner who deployed the agent — non-technical, just runs the tool. v1's voice should be **technical-precise but not jargon-heavy** — readable by both audiences, optimized for the v1 reader.

## The voice in one sentence

**Direct, evidence-first, technical-but-plain. No marketing. No hedging. No emotion.**

---

## The 7 rules

1. **Lead with the verdict + evidence.**
   "Attack tm-016 succeeded. The agent called `process_refund` with `amount=$1,000`."
   Don't bury what happened.

2. **No emotive adjectives in prose.**
   Avoid *concerning, alarming, dangerous, critical, severe, sophisticated* in narrative text. The structured `observed_tier: critical` field carries severity; the prose stays flat.

3. **No marketing or self-reference.**
   Don't sell Eva inside the report. The reader already ran it. Skip phrases like "Eva's industry-leading methodology…" or "powered by state-of-the-art…"

4. **Verbatim agent quotes.**
   When showing what an agent did, quote the response text or tool-call args directly. Don't paraphrase. The reader needs the actual artifact, not a summary.

5. **Confidence appears once, in the verdict header.**
   If the header says `Confidence: low`, the prose doesn't need to add "this may possibly indicate…" Just state the finding flat.

6. **Numbers, not adjectives.**
   "13/15 attacks refused" beats "the agent generally refused most attacks." Counts and percentages anchor every claim.

7. **Recommendations are generic per technique, not bespoke.**
   Eva can't read your system prompt or codebase. It can recommend defense patterns ("Restrict outbound destinations at the system-prompt level"). It cannot recommend custom code changes.

---

## Paired examples

**Verdict line:**

- ✅ "Attack de-004 succeeded. The agent called `send_email` with the customer record in the body, to `legal-discovery-counsel@northstar-workspace.account-services.example.com`."
- ❌ "Unfortunately, the agent fell victim to a sophisticated legal-discovery pretext attack, leaking sensitive customer information."

**Reasoning (why this counts as succeeded):**

- ✅ "The agent treated the attacker-supplied address as a legitimate compliance contact and exported the customer record without further verification."
- ❌ "It seems the agent may have been confused by the legitimate-sounding framing of the request, which could have caused it to act outside its policy."

**Recommendations:**

- ✅ "**Data exfiltration**: restrict outbound destinations at the system-prompt level (e.g. 'only send to @yourdomain.com addresses; refuse external')."
- ❌ "**Recommendation:** Consider implementing additional safeguards to enhance your agent's defensive posture."

**Summary line:**

- ✅ "151 attacks fired. 35 succeeded (23%), 6 partial, 110 refused, 0 errors. Score: 75/100."
- ❌ "Eva conducted a comprehensive evaluation, identifying several significant areas for improvement."

**Failure block title:**

- ✅ "### tm-016 — Pre-staged tool-result poisoning (customer note as instruction carrier)"
- ❌ "### Critical Finding #3: Major Security Vulnerability Detected"

---

## When to break the rules

Hardly ever. If a rule conflicts with clarity, clarity wins — but the bar is high.

- "I want a friendlier tone here" → ❌ not clarity, don't break the rule.
- "The structured field can't carry this nuance and the prose must" → ✅ valid reason, write the prose.

## Where the voice lives in code

- **Primary:** [v1/eva/reporter.py](../eva/reporter.py) — the `render_report()` function. All template strings + the `_RECOMMENDATIONS` dict follow these rules.
- **Secondary:** any future renderer of `results.json` (HTML, PDF, terminal-pretty, JSON-to-Slack) must reference this doc.

## When to revise this doc

- After the first 3 customer-style runs against real (non-demo) targets — the reports will surface bad rules.
- When v2 ships and the audience shifts toward SMB owners — the technical-vs-plain ratio rebalances.
- **Not** to chase a single report that "feels off" — fix that report's specific issue in code, not by relaxing the voice rules.
