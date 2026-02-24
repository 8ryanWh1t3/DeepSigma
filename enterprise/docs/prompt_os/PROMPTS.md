# Prompt OS v2 — Canonical Prompts Reference

Canonical prompts are versioned in the repo as reusable assets.

---

## Prompt Index

| # | File | Category | When to Use |
|---|------|----------|-------------|
| 01 | [`01_unified_executive_analysis.md`](../../prompts/canonical/01_unified_executive_analysis.md) | Decision | Structured decision output — analyzing options, executive briefs, trade-offs |
| 01-json | [`01_unified_executive_analysis_json.md`](../../prompts/canonical/01_unified_executive_analysis_json.md) | Decision | JSON variant of 01 for automation pipelines |
| 02 | [`02_reality_assessment.md`](../../prompts/canonical/02_reality_assessment.md) | Perception | Perception correction — grounding in observable reality, drift check |
| 02-json | [`02_reality_assessment_json.md`](../../prompts/canonical/02_reality_assessment_json.md) | Perception | JSON variant of 02 for automation pipelines |
| 03 | [`START_SESSION_A1.md`](../../prompts/prompt_os/START_SESSION_A1.md) | Governance | Workbook control — triage LLM session, surface risks, recommend actions |
| 03-json | [`03_multi_dim_prompting_for_teams_a1_json.md`](../../prompts/canonical/03_multi_dim_prompting_for_teams_a1_json.md) | Governance | JSON variant of 03 for automation pipelines |
| 04 | [`04_decision_compression.md`](../../prompts/canonical/04_decision_compression.md) | Decision | Detect and decompress rushed decisions — compression risk scoring |

---

## Usage Notes

### 01 — Unified Executive Analysis

Use this prompt when a decision needs structured analysis. Produces a complete decision package: executive summary, recommended action with confidence/blast-radius/reversibility scoring, facts vs. interpretations, assumptions with disconfirm criteria, failure modes, options comparison, and concrete next actions.

**Maps to:** `DECISION_LOG` + `EXECUTIVE_ENGINE` tabs in the workbook.

### 02 — Reality Assessment

Use this prompt when you suspect narrative drift, emotional bias, or need to separate what is actually happening from what you're telling yourself about it. Includes a drift check for ego protection, pattern projection, scarcity narrative, urgency illusion, and external validation seeking.

**Maps to:** `REALITY_ENGINE` tab in the workbook.

### 03 — Multi-Dimensional Prompting for Teams (Workbook A1)

This is the primary workbook control prompt. Paste it into cell A1 of a START_SESSION sheet, or use it as the LLM system prompt when running a triage session. It reads all workbook tabs, identifies risks across decisions/assumptions/claims/patches, and outputs structured recommendations.

**Canonical file:** [`prompts/prompt_os/START_SESSION_A1.md`](../../prompts/prompt_os/START_SESSION_A1.md) — single source of truth. The file at `prompts/canonical/03_*` is a compatibility pointer.

### 04 — Decision Compression

Use this prompt when a decision is being rushed — under artificial urgency, without full reasoning, or with authority pressure overriding evidence. Scores compression risk (Low/Medium/High) and provides decompression steps including a 24–48 hour cooling period.

**Maps to:** `DECISION_LOG` → `CompressionRisk` field. References 01 and 02 as decompression tools.

### JSON Variants (01-json, 02-json, 03-json)

JSON variants produce identical analysis but output structured JSON instead of text. Use these for:

- Power Automate flows that need to parse LLM output
- Schema validation pipelines
- Sealed snapshot automation
- Any pipeline that needs machine-readable output

JSON output structures align with `schemas/prompt_os/prompt_os_schema_v2.json` where applicable.

> **Note:** Canonical prompts (01, 02, 04) are reusable analytical primitives. The workbook A1 prompt (03) is operational control — it references specific table names and output formatting for the Prompt OS workbook.

---

## Relationship to Workbook

```
02_reality_assessment    → REALITY_ENGINE tab (perception input)
01_executive_analysis    → EXECUTIVE_ENGINE + DECISION_LOG tabs (decision output)
04_decision_compression  → DECISION_LOG CompressionRisk field (pre-decision check)
03_team_workbook_a1      → All tabs (governance triage)
```

The prompts map to the workbook's cognitive loop: **Perception → Decision → Memory**.
