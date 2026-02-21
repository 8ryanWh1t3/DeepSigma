# Decision Compression Prompt

**Category:** Decision
**Version:** 1.0
**Usage:** Use when a decision is being made too fast, under artificial urgency, or without full reasoning. Detects compression and provides decompression steps.

---

```text
A decision is being made. Before it proceeds, check for compression.

Decision compression occurs when urgency, authority, or cognitive overload
forces a decision through without adequate reasoning, evidence, or
assumption-checking.

INPUT:
Decision Title:
Current Timeline:
Who is pushing for this?
What reasoning has been documented?
What alternatives have been considered?

COMPRESSION DETECTION:

1) Time Pressure
   - Is the deadline real or manufactured?
   - What happens if the decision is delayed 48 hours?
   - Who benefits from urgency?

2) Evidence Gap
   - How many supporting claims exist? (target: ≥ 3)
   - Have counter-claims been considered?
   - Is the evidence fresh (< 30 days)?

3) Assumption Load
   - How many assumptions underpin this decision?
   - Have any been tested or validated?
   - What is the combined confidence level?

4) Authority Pressure
   - Is someone senior driving this without evidence?
   - Has dissent been invited or suppressed?
   - Would the decision change if the most senior person left the room?

5) Reversibility Check
   - Reversibility score (1–5)?
   - If irreversible, has a failure mode analysis been done?
   - Is there a rollback plan?

COMPRESSION RISK SCORE:
- Count the number of "yes" flags above
- 0–1: LOW — proceed with normal review
- 2–3: MEDIUM — schedule 24-hour cooling period + evidence review
- 4+: HIGH — halt and decompress before deciding

DECOMPRESSION STEPS (if MEDIUM or HIGH):

1) Document the decision in DECISION_LOG with all available evidence
2) Add at least 3 claims to ATOMIC_CLAIMS with source attribution
3) Register key assumptions in ASSUMPTIONS with half-life estimates
4) Run Reality Assessment (02_reality_assessment.md) on the situation
5) Run Executive Analysis (01_unified_executive_analysis.md) for structured options
6) Wait 24–48 hours before finalizing
7) Re-score CompressionRisk in DECISION_LOG

OUTPUT:
- Compression Risk: Low / Medium / High
- Flags triggered (list)
- Recommended action
- What to document before proceeding
- Suggested review date

No decision is so urgent it can't survive 24 hours of structured reasoning.
```
