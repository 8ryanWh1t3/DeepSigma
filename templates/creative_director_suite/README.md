---
title: "Creative Director Suite — Workbook Template"
version: "0.6.2"
date: "2026-02-19"
---

# Creative Director Suite — Workbook Template

> A plug-and-play Excel workbook with BOOT sheet, 7 named governance tables,
> sample data, and a Coherence Index dashboard.

---

## Files in This Directory

| File | Description |
|------|-------------|
| `Creative_Director_Suite_CoherenceOps_v2.xlsx` | Generated workbook — ready to use |
| `README.md` | This file |

---

## Workbook Structure

| Sheet | Named Table | Purpose |
|-------|-------------|---------|
| BOOT | — | System prompt for LLM initialization (`A1`) |
| QUICK_START | — | Step-by-step guide (7 rows) |
| DATA_DICTIONARY | — | Lookup lists for dropdowns |
| BRIEF_MATRIX | tblTimeline | Initiative tracking with assumption half-life |
| BRIEF_MATRIX | tblDeliverables | Deliverable tracking with dependencies |
| 6_LENS_PROMPTS | — | Multi-dimensional prompt generation |
| DLR_CAPTURE | tblDLR | Decision Ledger Records |
| CANON_SYNC | tblCanonGuardrails | Canonical statement registry |
| ASSUMPTIONS | tblAssumptions | Assumption tracking with decay |
| CLAIMS | tblClaims | Truth claims with confidence |
| PATCH_LOG | tblPatchLog | Correction audit trail |
| CI_DASHBOARD | — | Coherence Index scorecard |

---

## Quick Start

1. **Download** `Creative_Director_Suite_CoherenceOps_v2.xlsx`
2. **Open** in Excel (desktop or web)
3. **Read** the `BOOT` sheet — cell `A1` contains the LLM system prompt
4. **Attach** the workbook to your LLM app (ChatGPT, Claude, Copilot)
5. **Respond** to: "What Would You Like To Do Today?"
6. **Paste** write-back rows into the appropriate Excel tables

---

## Paste-Ready BOOT!A1 Block

If creating a workbook from scratch, paste this into `BOOT!A1`:

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

## Regenerating the Workbook

```bash
pip install openpyxl  # or: pip install -e ".[excel]"
python tools/generate_cds_workbook.py
```

Output: `templates/creative_director_suite/Creative_Director_Suite_CoherenceOps_v2.xlsx`

---

## Creating a Workbook from Scratch

If you prefer to build manually:

1. Create a new Excel workbook
2. Add sheets: `BOOT`, `QUICK_START`, `DATA_DICTIONARY`, `BRIEF_MATRIX`, `6_LENS_PROMPTS`, `DLR_CAPTURE`, `CANON_SYNC`, `ASSUMPTIONS`, `CLAIMS`, `PATCH_LOG`, `CI_DASHBOARD`
3. Paste the BOOT!A1 text above into cell `A1` of the `BOOT` sheet
4. For each governance sheet, add column headers from [TABLE_SCHEMAS.md](../../docs/excel-first/TABLE_SCHEMAS.md)
5. Select each header row + data → Insert → Table → Name the table (`tblTimeline`, etc.)
6. Add sample data or your own initiative data

---

## Template Checklist

| Step | Done? |
|------|-------|
| BOOT sheet exists with A1 system prompt | |
| All 7 named tables created with exact names | |
| Column headers match TABLE_SCHEMAS.md exactly | |
| Every row has a stable ID and Status field | |
| DATA_DICTIONARY populated with lookup values | |
| CI_DASHBOARD has weighted dimensions | |
| Workbook saved as .xlsx (not .xls) | |

---

## See Also

- [Workbook Boot Protocol](../../docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md) — BOOT!A1 specification
- [Table Schemas](../../docs/excel-first/TABLE_SCHEMAS.md) — full column definitions
- [Multi-Dim Prompting for Teams](../../docs/excel-first/multi-dim-prompting-for-teams/README.md) — 6-lens model
- [Sample Dataset](../../datasets/creative_director_suite/README.md) — 8 CSVs with 25 rows each
