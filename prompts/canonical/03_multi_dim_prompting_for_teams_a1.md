# Multi-Dimensional Prompting for Teams — Workbook A1 Prompt

**Category:** Governance
**Version:** 1.0
**Usage:** Workbook control / triage / governance output — intended for Excel cell A1 in START_SESSION. Use when running an LLM session against the Coherence Prompt OS v2 workbook.

---

```text
You are reading a structured cognition workbook.

Follow these steps:

1) Read all tabs.
2) Identify:
   - Active decisions
   - Expired assumptions
   - Low credibility claims (<60)
   - High blast radius decisions (≥4)
   - Major drift prompts
   - Open RED severity patches
3) Surface the 3 highest priority risks.
4) Suggest 3 high-leverage actions.
5) Identify any structural weaknesses in the system.
6) Recommend one governance improvement.

OUTPUT FORMAT:

TOP RISKS:
- Risk 1
- Risk 2
- Risk 3

TOP ACTIONS:
1)
2)
3)

SYSTEM OBSERVATIONS:
- Structural issue
- Drift signal
- Governance gap

Seal this run with:
- Summary Confidence (%)
- What should be reviewed next
- Suggested Review Date

Then ask:
"What would you like to do today?"
```
