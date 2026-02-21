# Multi-Dimensional Prompting for Teams — JSON Output Variant

**Category:** Governance
**Version:** 1.0
**Usage:** Machine-readable workbook triage output for automation pipelines (Power Automate, sealed snapshot export, schema validation).

> **Note:** This is the JSON variant of [`prompts/prompt_os/START_SESSION_A1.md`](../prompt_os/START_SESSION_A1.md).

---

```text
You are reading a structured cognition workbook (Coherence Prompt OS v2).

Follow these steps:

1) Read all tabs in the workbook.
2) Identify:
   - Active decisions (DECISION_LOG where Status = "Active")
   - Expired assumptions (ASSUMPTIONS where ExpiryRisk = "RED")
   - Low credibility claims (ATOMIC_CLAIMS where CredibilityScore < 60)
   - High blast radius decisions (DECISION_LOG where BlastRadius >= 4)
   - Major drift prompts (PROMPT_LIBRARY where DriftFlag = "Major")
   - Open RED severity patches (PATCH_LOG where Severity_GYR = "RED" and Status = "Open")
3) Surface the 3 highest priority risks.
4) Suggest 3 high-leverage actions.
5) Identify any structural weaknesses in the system.
6) Recommend one governance improvement.

OUTPUT: Respond ONLY with valid JSON matching this schema:

{
  "top_risks": [
    {
      "description": "string",
      "source_table": "string",
      "source_id": "string"
    }
  ],
  "top_actions": [
    {
      "action": "string",
      "expected_impact": "string"
    }
  ],
  "suggested_updates": [
    {
      "table": "string",
      "row_id": "string",
      "change": "string"
    }
  ],
  "system_observations": {
    "structural_issue": "string",
    "drift_signal": "string",
    "governance_gap": "string"
  },
  "seal": {
    "summary_confidence_pct": 0,
    "seal_hash": "placeholder",
    "next_review_date": "YYYY-MM-DD",
    "review_next": "string"
  }
}

Be precise. No commentary outside the JSON object.
```
