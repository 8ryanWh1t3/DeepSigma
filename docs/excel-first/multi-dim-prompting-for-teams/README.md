---
title: "Multi-Dimensional Prompting for Teams"
subtitle: "Excel-First Coherence Ops for SharePoint Environments"
version: "0.6.2"
date: "2026-02-19"
---

# Multi-Dimensional Prompting for Teams

> Turn a shared Excel workbook into a governed decision surface
> that any LLM can read, reason over, and audit. No code required.

---

## The Idea

Most teams already live in Excel and SharePoint. Instead of asking them
to adopt a new tool, we bring Coherence Ops governance to **where they work**.

A single workbook becomes:

- **Rows** = Use Cases (tasks, initiatives, decisions)
- **Columns** = Constraints (guardrails, assumptions, KPI targets)
- **Tabs** = Clients / Lenses / Layers
- **BOOT!A1** = Universal entry point — the LLM's system prompt

---

## The Architecture

```
┌──────────────────────────────────────────────┐
│  Excel Workbook (.xlsx)                      │
│                                              │
│  BOOT!A1 ─── System prompt for LLM          │
│                                              │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Production   │  │ Governance          │   │
│  │ Layer        │  │ Layer               │   │
│  │              │  │                     │   │
│  │ Clients      │  │ tblTimeline         │   │
│  │ Campaigns    │  │ tblDLR              │   │
│  │ Projects     │  │ tblClaims           │   │
│  │ Assets       │  │ tblAssumptions      │   │
│  │ Shots        │  │ tblPatchLog         │   │
│  │ Tasks        │  │ tblCanonGuardrails  │   │
│  │ Prompts      │  │ tblDeliverables     │   │
│  │ Approvals    │  │                     │   │
│  └─────────────┘  └─────────────────────┘   │
│                                              │
│  6_LENS_PROMPTS ─── Prompt generation layer  │
│  CI_DASHBOARD ───── Coherence Index scoring  │
└──────────────────────────────────────────────┘
         │
         ▼
   LLM reads BOOT!A1
   asks: "What Would You Like To Do Today?"
```

---

## Determinism Rules

These rules ensure the LLM can parse the workbook reliably:

1. **Table names are exact** — `tblTimeline`, not "Timeline" or "timeline_data"
2. **Every row has a stable ID** — `Decision_ID`, `Claim_ID`, `Assumption_ID`, etc.
3. **Every row has a Status field** — enables filtering (ACTIVE, EXPIRED, SEALED, etc.)
4. **Output includes a write-back contract** — `Where to Write Back (Table/Columns)`
5. **LLM uses ONLY workbook data** — no hallucinated sources, metrics, or brand rules

---

## The 6-Lens Prompt Model

Each initiative is examined through 6 lenses, each applied across 3 operations:

| Lens | IntelOps | ReOps | FranOps |
|------|----------|-------|---------|
| **PRIME** | What truth standards apply? | What governance invariants hold? | What canon precedence exists? |
| **EXEC** | Top claims + blast radius? | Decision gate + owner? | Narrative risk? |
| **OPS** | Collection gaps? | Daily loop plan? | Continuity checks? |
| **AI/TECH** | Automation for drift detection? | Drift triggers? | Safe summary rules? |
| **HUMAN** | Bias risks? | Adoption friction? | Tone guardrails? |
| **ICON** | Truth status lights? | Seal/patch markers? | SEV banners? |

These prompts live in the `6_LENS_PROMPTS` sheet of the workbook.

---

## Example Flow

### Step 1: User attaches workbook

The user uploads the `.xlsx` to their LLM app (ChatGPT, Claude, Copilot).

### Step 2: LLM reads BOOT!A1

The LLM reads the system prompt and scans all named tables.

### Step 3: LLM asks the opening question

```
What Would You Like To Do Today?

1) Build/Update Claims
2) Refresh Assumptions + Half-Life
3) Detect Drift + Root Cause
4) Propose Patch Options
5) Canon Audit
6) Weekly Exec Summary
7) Next 7 Days Asset Checklist
```

### Step 4: User selects "4" (Propose Patch Options)

### Step 5: LLM produces structured output

```
═══════════════════════════════════════════════════════════
(A) FINDINGS
═══════════════════════════════════════════════════════════

Scanned tblAssumptions: 3 assumptions expired (ASM-004, ASM-011, ASM-019).
Scanned tblTimeline: Week 3 CI_Week_Score dropped from 88 to 72 (DRIFTING).
Root cause: ASM-004 (VTR benchmark > 30%) expired 5 days ago.

═══════════════════════════════════════════════════════════
(B) RECOMMENDED ACTIONS
═══════════════════════════════════════════════════════════

| ID      | Recommendation                    | Risk   | Expected Impact | Guardrail Check | Where to Write Back           |
|---------|-----------------------------------|--------|-----------------|-----------------|-------------------------------|
| PAT-008 | Refresh ASM-004 with Q1 actuals   | LOW    | CI +8 pts       | GR-002: PASS    | tblPatchLog / new row         |
| PAT-009 | Swap TikTok → Reels for CA-003    | MEDIUM | VTR +12%        | GR-005: PASS    | tblPatchLog / new row         |
| PAT-010 | Escalate ASM-019 to Exec review   | HIGH   | Blocks Week 4   | GR-001: FLAG    | tblPatchLog / new row         |

═══════════════════════════════════════════════════════════
(C) WRITE-BACK ROWS (paste into tblPatchLog)
═══════════════════════════════════════════════════════════

| Patch_ID | Week_Triggered | Decision_ID | Drift_Source         | Severity | Root_Cause              | Patch_Action                  | Owner      | Status | Date_Opened |
|----------|---------------|-------------|----------------------|----------|-------------------------|-------------------------------|------------|--------|-------------|
| PAT-008  | 3             | DEC-004     | ASM-004 expired      | LOW      | VTR benchmark stale     | Refresh with Q1 actuals       | Ana        | OPEN   | 2026-03-01  |
| PAT-009  | 3             | DEC-006     | KPI miss CA-003      | MEDIUM   | Platform underperformance| Swap TikTok → Reels           | Kenji      | OPEN   | 2026-03-01  |
| PAT-010  | 3             | DEC-002     | ASM-019 expired      | HIGH     | Audience shift untracked | Escalate to Exec review       | Director   | OPEN   | 2026-03-01  |
```

---

## SharePoint Deployment

1. **Upload workbook** to a SharePoint document library
2. **Teams co-edit** the same workbook in real time
3. **LLM access** via file upload, Graph API, or Power Automate trigger
4. **Named tables** survive co-editing — Excel preserves table structure
5. **Version history** in SharePoint provides audit trail for all changes

---

## Quick Start

1. Download the template workbook from [`templates/creative_director_suite/`](../../../templates/creative_director_suite/)
2. Upload to SharePoint (or open locally)
3. Read `BOOT!A1` to understand the workbook structure
4. Attach workbook to your LLM app
5. Respond to: **"What Would You Like To Do Today?"**
6. Paste write-back rows into the appropriate Excel tables

---

## Connecting to DeepSigma

This Excel-first approach is a **lightweight on-ramp** to the full
Coherence Ops pipeline:

```
Workbook data  →  SharePoint connector  →  Canonical envelopes
     →  DLR sealing  →  Drift detection  →  Patch loop
     →  Memory Graph  →  IRIS queries
```

Teams start with Excel. As governance needs grow, the same table schemas
and naming conventions port directly into the DeepSigma runtime.

---

## Power App Pack (v0.6.3)

Implementation-ready specs for deploying MDPT on SharePoint + Power Platform:

| Resource | What It Provides |
|----------|-----------------|
| [PromptCapabilities Build Sheet](SHAREPOINT_LIST_BUILD_SHEET_PromptCapabilities.md) | SharePoint list schema for the 18 prompt capabilities |
| [PromptRuns Build Sheet](SHAREPOINT_LIST_BUILD_SHEET_PromptRuns.md) | Execution log list with calculated governance metrics |
| [DriftPatches Build Sheet](SHAREPOINT_LIST_BUILD_SHEET_DriftPatches.md) | Drift signal + patch lifecycle tracking list |
| [Power Automate Flows](POWER_AUTOMATE_FLOWS.md) | 4 flow recipes: drift alert, patch approval, weekly digest, workbook refresh |
| [Power Apps Screen Map](POWER_APPS_SCREEN_MAP.md) | 5-screen canvas app layout with data bindings |
| [MDPT Governance](GOVERNANCE.md) | Permission model, audit trail, compliance, escalation path |

---

## See Also

- [Workbook Boot Protocol](../WORKBOOK_BOOT_PROTOCOL.md) — how BOOT!A1 works
- [Table Schemas](../TABLE_SCHEMAS.md) — full column definitions for all 7 tables
- [Template Workbook](../../../templates/creative_director_suite/README.md) — ready-to-use .xlsx
- [Sample Dataset](../../../datasets/creative_director_suite/README.md) — 8 CSVs
