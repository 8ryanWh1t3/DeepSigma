# Creative Director Suite

**v0.6.2** — Excel-first Coherence Ops for creative production teams.

> From code-first governance to Excel-first governance — Coherence Ops meets teams where they already work.

The Creative Director Suite proves that the same governance primitives — claims, assumptions, decisions, drift, patches — work inside a shared Excel workbook that any team can edit in SharePoint. No code required. Same rigor.

---

## Quick Start

```bash
# Generate the governed workbook
pip install -e ".[excel]"
python tools/generate_cds_workbook.py

# Or explore the sample dataset
ls datasets/creative_director_suite/samples/
```

**Five-step workflow:**

1. Download the template workbook from `templates/creative_director_suite/`
2. Fill `BOOT!A1` (or use the pre-filled template)
3. Attach workbook to your LLM app (ChatGPT, Claude, Copilot)
4. Respond to: **"What Would You Like To Do Today?"**
5. Paste write-back rows into Excel tables

---

## Workbook Structure

The generated workbook contains 12 sheets:

| Sheet | Purpose |
|-------|---------|
| **BOOT** | LLM system prompt in A1 — initializes context for the entire workbook |
| QUICK_START | One-page setup guide for new users |
| DATA_DICTIONARY | Column definitions across all tables |
| 6_LENS_PROMPTS | PRIME / EXEC / OPS / AI-TECH / HUMAN / ICON prompt templates |
| BRIEF_MATRIX | Client × Campaign brief cross-reference |
| DELIVERABLES | Governance table — tblDeliverables |
| DLR_CAPTURE | Governance table — tblDLR (Decision Ledger Records) |
| CLAIMS | Governance table — tblClaims |
| ASSUMPTIONS | Governance table — tblAssumptions |
| PATCH_LOG | Governance table — tblPatchLog |
| CANON_SYNC | Governance table — tblCanonGuardrails |
| CI_DASHBOARD | Coherence Index dashboard with live metrics |

---

## Governance Tables

Seven named Excel tables provide deterministic addressing for LLM parsing:

| Table | Maps To | Purpose |
|-------|---------|---------|
| tblTimeline | Decision Scaffold (DS) | Milestone tracking with drift/patch status |
| tblDeliverables | Decision Scaffold (DS) | Asset-level deliverable tracking |
| tblDLR | Decision Ledger Record (DLR) | Formal decision capture with rationale |
| tblClaims | Atomic Claims | Verifiable claims tied to decisions |
| tblAssumptions | Reasoning Scaffold (RS) | Assumptions with confidence and TTL |
| tblPatchLog | Patch Packets | Drift → Patch correction log |
| tblCanonGuardrails | Canon | Blessed rules and constraints |

Each table has 25 sample rows of Sanrio-themed creative production data.

---

## Dataset

Eight CSVs in `datasets/creative_director_suite/samples/`:

| CSV | Rows | Description |
|-----|------|-------------|
| Sample_Clients.csv | 25 | Client organizations |
| Sample_Campaigns.csv | 25 | Campaign definitions |
| Sample_Projects.csv | 25 | Production projects |
| Sample_Assets.csv | 25 | Creative assets |
| Sample_Shots.csv | 25 | Shot-level production data |
| Sample_Tasks.csv | 25 | Task assignments |
| Sample_Prompts.csv | 25 | LLM prompt records |
| Sample_Approvals.csv | 25 | Approval workflows |

**Relationships:** Clients → Campaigns → Projects → Assets → Shots → Tasks → Prompts → Approvals

---

## BOOT Protocol

The `BOOT` sheet cell A1 contains a structured system prompt that tells the LLM:

- **WHO** — Creative Ops Copilot (Coherence Ops: Truth · Reasoning · Memory)
- **OPENING MOVE** — Read all tables, then ask "What Would You Like To Do Today?"
- **MENU** — 7 options (Build Claims, Refresh Assumptions, Detect Drift, Propose Patch, Canon Audit, Exec Summary, Asset Checklist)
- **RULES** — Use ONLY workbook data, cite TableName + Row_IDs, enforce Canon Guardrails
- **OUTPUT** — Findings → Recommended Actions → Write-back rows for Excel

See [Excel-First Governance](Excel-First-Governance) for the full BOOT!A1 spec, table schemas, and 6-lens prompting model.

---

## LLM Compatibility

| Platform | Attachment Method |
|----------|------------------|
| ChatGPT (Plus/Team/Enterprise) | Upload .xlsx via file attachment |
| Claude (Pro/Team) | Upload .xlsx via file attachment |
| Microsoft Copilot | SharePoint-connected workbook |
| Any LLM with file support | Upload or paste BOOT!A1 + table contents |

---

## Key Files

| Resource | Path |
|----------|------|
| Template workbook | `templates/creative_director_suite/Creative_Director_Suite_CoherenceOps_v2.xlsx` |
| Generator script | `tools/generate_cds_workbook.py` |
| Sample CSVs | `datasets/creative_director_suite/samples/` |
| Boot Protocol spec | `docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md` |
| Table Schemas | `docs/excel-first/TABLE_SCHEMAS.md` |
| 6-Lens Prompting | `docs/excel-first/multi-dim-prompting-for-teams/README.md` |
| Release Notes | [RELEASE_NOTES_v0.6.2.md](https://github.com/8ryanWh1t3/DeepSigma/blob/main/_park_enterprise/docs/release/RELEASE_NOTES_v0.6.2.md) |

---

## See Also

- [Excel-First Governance](Excel-First-Governance) — BOOT protocol, table schemas, 6-lens prompting model
- [Coherence Ops Mapping](Coherence-Ops-Mapping) — DLR / RS / DS / MG governance artifacts
- [Drift → Patch](Drift-to-Patch) — How drift signals become structured Patch Packets
