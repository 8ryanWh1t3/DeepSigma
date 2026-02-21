# Prompt OS v2 — Canonical Prompts Reference

Three canonical prompts are versioned in the repo as reusable assets.

---

## Prompt Index

| # | File | Category | When to Use |
|---|------|----------|-------------|
| 01 | [`prompts/canonical/01_unified_executive_analysis.md`](../../prompts/canonical/01_unified_executive_analysis.md) | Decision | Structured decision output — analyzing options, preparing executive briefs, evaluating trade-offs |
| 02 | [`prompts/canonical/02_reality_assessment.md`](../../prompts/canonical/02_reality_assessment.md) | Perception | Perception correction — grounding situations in observable reality, checking for narrative drift and emotional bias |
| 03 | [`prompts/prompt_os/START_SESSION_A1.md`](../../prompts/prompt_os/START_SESSION_A1.md) | Governance | Workbook control — triage LLM session against Prompt OS v2 workbook, surface risks, recommend actions |

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

> **Note:** Canonical prompts (01, 02) are reusable analytical primitives. The workbook A1 prompt is operational control — it references specific table names and output formatting for the Prompt OS workbook.

---

## Relationship to Workbook

```
02_reality_assessment → REALITY_ENGINE tab (perception input)
01_executive_analysis → EXECUTIVE_ENGINE + DECISION_LOG tabs (decision output)
03_team_workbook_a1  → All tabs (governance triage)
```

The three prompts map to the workbook's cognitive loop: **Perception → Decision → Memory**.
