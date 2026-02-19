---
title: "Workbook Boot Protocol"
version: "0.6.2"
date: "2026-02-19"
---

# Workbook Boot Protocol

> How a single cell — `BOOT!A1` — initializes the entire Creative Director Suite
> workbook for any LLM.

---

## The Idea

When a user attaches an Excel workbook to an LLM app (ChatGPT, Claude, Copilot),
the LLM needs to understand what the workbook contains and how to operate on it.

The **BOOT sheet** solves this. Cell `A1` contains a structured text block —
effectively a system prompt embedded in the workbook itself. The LLM reads
`BOOT!A1` first, then knows:

1. What role to adopt
2. What tables exist and what they contain
3. What menu to offer the user
4. What rules to follow
5. How to format output
6. Where to write results back

---

## Exact BOOT!A1 Content

This is the canonical text that goes into cell `BOOT!A1`. Copy it exactly.

```text
YOU ARE: Creative Ops Copilot (Coherence Ops: Truth · Reasoning · Memory)

OPENING MOVE:
1) Read this workbook's tables (tblTimeline, tblDeliverables, tblClaims, tblAssumptions, tblDLR, tblPatchLog, tblCanonGuardrails).
2) Then ask the user: "What Would You Like To Do Today?" and show the menu below.

MENU (reply with a number):
1) Build/Update Claims
2) Refresh Assumptions + Half-Life
3) Detect Drift + Root Cause
4) Propose Patch Options
5) Canon Audit
6) Weekly Exec Summary
7) Next 7 Days Asset Checklist

RULES:
- Use ONLY information found in this workbook. If data is missing, ask 1 clarifying question and list the missing fields.
- Do NOT invent sources, metrics, or brand rules.
- Enforce Canon Guardrails (tblCanonGuardrails) as hard constraints.
- Always reference: TableName + Row_ID(s) (e.g., tblTimeline Week=4, Decision_ID=DEC-004).
- Output in tables with these columns when applicable: ID | Recommendation | Risk | Expected Impact | Guardrail Check | Where to Write Back (Table/Columns).

DEFAULT OUTPUT FORMAT:
- Start with: "What Would You Like To Do Today?"
- After selection: produce (A) Findings, (B) Recommended Actions, (C) Write-back rows for Excel (ready to paste).
```

---

## How LLMs Process the BOOT Sheet

```
1. User attaches workbook to LLM app
2. LLM opens workbook → reads BOOT!A1
3. LLM parses role declaration → adopts "Creative Ops Copilot"
4. LLM reads named tables → builds internal schema map
5. LLM presents menu → "What Would You Like To Do Today?"
6. User selects option (e.g., "4")
7. LLM scans relevant tables → produces structured output
8. Output includes write-back rows → user pastes into Excel
```

---

## Why BOOT Matters

### For Teams
- **Zero onboarding** — the workbook teaches the LLM how to use itself
- **Consistent behavior** — every team member gets the same copilot experience
- **SharePoint-native** — workbook lives in a document library, teams co-edit

### For Coherence Ops
- **Deterministic parsing** — named tables + stable IDs = no ambiguity
- **Governance enforcement** — Canon Guardrails checked on every output
- **Audit trail** — every action references TableName + Row_ID
- **Write-back contract** — LLM always tells you where to paste results

### For Adoption
- **Excel-template-like** — feels like a normal workbook with a smart assistant
- **No code required** — attach, ask, paste
- **Works everywhere** — ChatGPT Advanced Data Analysis, Claude, Copilot in Excel

---

## Table Registry

The BOOT sheet references these named tables. See [TABLE_SCHEMAS.md](TABLE_SCHEMAS.md) for full column definitions.

| Named Table | Sheet | Purpose |
|-------------|-------|---------|
| `tblTimeline` | BRIEF_MATRIX | Initiative timeline with assumption half-life |
| `tblDeliverables` | BRIEF_MATRIX | Deliverable tracking (alias of tblTimeline scope) |
| `tblClaims` | CLAIMS | Truth claims with confidence and evidence |
| `tblAssumptions` | ASSUMPTIONS | Assumptions with half-life decay tracking |
| `tblDLR` | DLR_CAPTURE | Decision Ledger Records — every decision sealed here |
| `tblPatchLog` | PATCH_LOG | Corrections triggered by drift detection |
| `tblCanonGuardrails` | CANON_SYNC | Canonical statements — the truth registry |

---

## Compatibility

| Platform | How It Works |
|----------|-------------|
| ChatGPT (Advanced Data Analysis) | Upload .xlsx → GPT reads BOOT!A1 → menu appears |
| Claude | Upload .xlsx as attachment → Claude reads BOOT!A1 |
| Copilot in Excel | Named tables accessible → BOOT!A1 as custom prompt |
| SharePoint + Power Automate | Upload to document library → trigger flow on edit |
| Power Platform / Dataverse | Use Dataverse connector to read named ranges |

---

## Validation Gate

The BOOT contract is enforced in CI. To validate a workbook locally:

```bash
python tools/validate_workbook_boot.py templates/creative_director_suite/Creative_Director_Suite_CoherenceOps_v2.xlsx
```

Rules checked:

1. Sheet "BOOT" exists
2. Cell A1 begins with `BOOT!` prefix
3. Required metadata keys present: `version:`, `ttl_hours_default:`, `risk_lane_default:`, `schema_ref:`, `owner:`
4. 7 named governance tables present (pass `--boot-only` for minimal validation)

Exit code 0 = pass, 1 = fail with readable errors.

---

## See Also

- [Table Schemas](TABLE_SCHEMAS.md) — full column definitions for all 7 tables
- [Multi-Dim Prompting for Teams](multi-dim-prompting-for-teams/README.md) — 6-lens prompt model
- [Template Workbook](../../templates/creative_director_suite/README.md) — ready-to-use .xlsx
- [Sample Dataset](../../datasets/creative_director_suite/README.md) — 8 CSVs with 25 rows each
