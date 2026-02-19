---
title: "Coherence Ops Governance Table Schemas"
version: "0.6.2"
date: "2026-02-19"
---

# Coherence Ops Governance Table Schemas

> 7 named tables that form the governance layer of the Creative Director Suite workbook.
> Every dataset is an Excel Table with an exact table name. Every row has a stable ID
> and a Status field. This is **LLM-readable by design**.

---

## Why Named Tables?

Named Excel tables (`tblTimeline`, `tblDLR`, etc.) give LLMs three things
that raw cell ranges cannot:

1. **Deterministic addressing** — `tblClaims[Claim_ID="CLM-003"]` is unambiguous
2. **Schema stability** — columns are fixed; adding rows doesn't break references
3. **Cross-table joins** — IDs link tables together (e.g., `tblDLR.Assumptions_IDs` → `tblAssumptions.Assumption_ID`)

**Rule:** Every dataset must be an **Excel Table** with the exact table names below.
Every row must have a stable ID column and a Status field.

---

## Table Overview

| Named Table | Purpose | ID Column |
|-------------|---------|-----------|
| `tblTimeline` | Initiative timeline with KPI targets and assumption checks | Week |
| `tblDeliverables` | Asset delivery tracking with dependencies | Asset_ID |
| `tblClaims` | Truth claims with confidence scoring and evidence | Claim_ID |
| `tblAssumptions` | Assumptions with half-life decay and expiry tracking | Assumption_ID |
| `tblDLR` | Decision Ledger Records — sealed decisions with rationale | Decision_ID |
| `tblPatchLog` | Corrections triggered by drift detection | Patch_ID |
| `tblCanonGuardrails` | Brand/canon constraints — hard rules the LLM must enforce | Guardrail_ID |

---

## tblTimeline

**Purpose:** Each row is a campaign week with deliverables, KPI targets, assumption checks, and coherence scoring.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Week | integer | Yes | Week number |
| Start_Date | date | Yes | Week start date |
| End_Date | date | Yes | Week end date |
| Phase | text | Yes | Campaign phase (e.g., Pre-Launch, Launch, Post-Launch) |
| Key_Deliverable | text | Yes | Primary deliverable for this week |
| Primary_Lens | text | No | Dominant 6-lens perspective (PRIME/EXEC/OPS/AI-TECH/HUMAN/ICON) |
| Decision_ID | text | No | FK → tblDLR.Decision_ID |
| Assumption_Check | text | No | Assumption IDs to validate this week |
| Canon_Check | text | No | Guardrail IDs to enforce this week |
| KPI_Target | text | No | Target metric value |
| Actual_KPI | text | No | Measured metric value |
| Drift_Flag | text | No | GREEN / YELLOW / RED |
| CI_Week_Score | number | No | Coherence Index for this week (0–100) |
| CI_Week_Status | text | No | ON_TRACK / DRIFTING / CRITICAL |
| Notes | text | No | Free-form notes |

---

## tblDeliverables

**Purpose:** Each row is a specific asset with delivery status, ownership, and dependency links.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Week | integer | Yes | Delivery week |
| Asset_ID | text | Yes | Unique ID (e.g., AS-001) |
| Asset_Type | text | Yes | Video_6s / Poster / Sticker / AR_Filter / etc. |
| Channel | text | Yes | Distribution channel |
| Owner | text | Yes | Responsible person/role |
| Status | text | Yes | Draft / In_Review / Approved / Published |
| Due_Date | date | Yes | Delivery deadline |
| Dependency_Decision_ID | text | No | FK → tblDLR.Decision_ID |
| Canon_Guardrail | text | No | FK → tblCanonGuardrails.Guardrail_ID |
| Notes | text | No | Free-form notes |

---

## tblClaims

**Purpose:** Each row is a truth claim — a statement the team believes to be true, with confidence and evidence.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Claim_ID | text | Yes | Unique ID (e.g., CLM-001) |
| Claim_Text | text | Yes | The claim statement |
| Confidence_0_100 | integer | Yes | Confidence score (0–100) |
| Evidence_Summary | text | No | Summary of supporting evidence |
| Source_Ref | text | No | Source reference (URL, document, person) |
| Last_Validated_Date | date | No | When the claim was last checked |
| Owner | text | Yes | Responsible person/role |
| Status | text | Yes | ACTIVE / EXPIRED / CONTESTED / RETIRED |
| Notes | text | No | Free-form notes |

---

## tblAssumptions

**Purpose:** Each row is an assumption underlying a decision, with half-life decay tracking.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Assumption_ID | text | Yes | Unique ID (e.g., ASM-001) |
| Related_Decision_ID | text | Yes | FK → tblDLR.Decision_ID |
| Assumption_Text | text | Yes | The assumption statement |
| Confidence_Initial_0_1 | number | Yes | Initial confidence (0.0–1.0) |
| Half_Life_Days | integer | Yes | Days until confidence halves |
| Date_Validated_Last | date | No | Last validation date |
| Current_Confidence | number | No | Computed current confidence |
| Expiry_Date | date | No | When assumption becomes stale |
| Status | text | Yes | ACTIVE / EXPIRED / REFRESHED |
| Owner | text | Yes | Responsible person/role |
| Action_If_Expired | text | No | Prescribed action when expired |
| Notes | text | No | Free-form notes |

---

## tblDLR

**Purpose:** Each row is a Decision Ledger Record — a sealed decision with full rationale, alternatives, and linked assumptions.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Decision_ID | text | Yes | Unique ID (e.g., DEC-001) |
| Initiative_ID | text | Yes | FK → tblTimeline context |
| Decision_Date | date | Yes | When the decision was made |
| Context | text | Yes | Situation that prompted the decision |
| Options_Considered | text | Yes | Pipe-delimited list of options |
| Chosen_Option | text | Yes | The selected option |
| Rationale_Why | text | Yes | Why this option was chosen |
| Rejected_Alternatives_Why | text | No | Why other options were rejected |
| Assumptions_IDs | text | No | Semicolon-separated ASM-xxx references |
| Kill_Switch | text | No | Condition that would reverse this decision |
| Review_Date | date | No | Scheduled review date |
| Owner | text | Yes | Decision maker |
| Status | text | Yes | DRAFT / SEALED / PATCHED / RETIRED |
| Seal_ID | text | No | Immutable seal reference |
| Patch_Version | text | No | Current patch version |
| Notes | text | No | Free-form notes |

---

## tblPatchLog

**Purpose:** Each row is a correction triggered by drift detection — the audit trail of governance self-correction.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Patch_ID | text | Yes | Unique ID (e.g., PAT-001) |
| Week_Triggered | integer | Yes | Week when drift was detected |
| Decision_ID | text | Yes | FK → tblDLR.Decision_ID |
| Drift_Source | text | Yes | What triggered the drift (e.g., assumption expired, KPI miss) |
| Severity | text | Yes | LOW / MEDIUM / HIGH / CRITICAL |
| Root_Cause | text | Yes | Root cause analysis |
| Patch_Action | text | Yes | Corrective action taken |
| Owner | text | Yes | Person who applied the patch |
| Status | text | Yes | OPEN / IN_PROGRESS / CLOSED |
| Date_Opened | date | Yes | When the patch was opened |
| Date_Closed | date | No | When the patch was resolved |
| Impact_on_CI | text | No | Effect on Coherence Index |
| Notes | text | No | Free-form notes |

---

## tblCanonGuardrails

**Purpose:** Each row is a brand/canon constraint — a hard rule that the LLM must enforce on every output.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Guardrail_ID | text | Yes | Unique ID (e.g., GR-001) |
| Character | text | Yes | Brand character (e.g., Hello Kitty, Kuromi) |
| Dimension | text | Yes | Constraint dimension (Tone, Visual, Copy, Behavior) |
| Allowed | text | Yes | What is permitted |
| Restricted | text | No | What requires approval |
| Forbidden | text | No | What is never allowed |
| Severity | text | Yes | ADVISORY / HARD / CRITICAL |
| Detection_Method | text | No | How violations are detected |
| Auto_Flag_If | text | No | Condition for automatic flagging |
| Owner | text | Yes | Guardrail owner |
| Escalation_Path | text | No | Who to escalate violations to |
| Notes | text | No | Free-form notes |

---

## Cross-Table Relationships

```
tblTimeline.Decision_ID ──────────→ tblDLR.Decision_ID
tblTimeline.Assumption_Check ─────→ tblAssumptions.Assumption_ID
tblTimeline.Canon_Check ──────────→ tblCanonGuardrails.Guardrail_ID

tblDeliverables.Dependency_Decision_ID → tblDLR.Decision_ID
tblDeliverables.Canon_Guardrail ──────→ tblCanonGuardrails.Guardrail_ID

tblDLR.Assumptions_IDs ──────────→ tblAssumptions.Assumption_ID
tblAssumptions.Related_Decision_ID → tblDLR.Decision_ID

tblPatchLog.Decision_ID ─────────→ tblDLR.Decision_ID
```

---

## Writeback Contract

Every LLM output that modifies workbook data **must** include a
`Where to Write Back (Table/Columns)` field. Example:

```
| ID      | Recommendation           | Where to Write Back              |
|---------|--------------------------|----------------------------------|
| ASM-003 | Refresh — confidence 0.4 | tblAssumptions / Current_Confidence, Status |
| PAT-007 | New patch — KPI miss     | tblPatchLog / new row            |
```

This ensures all changes are traceable and pasteable.

---

## Mapping to Coherence Ops Primitives

| Table | Coherence Ops Artifact |
|-------|----------------------|
| tblTimeline | Decision Scaffold (DS) — timeline and structure |
| tblDLR | Decision Ledger Record (DLR) — sealed decisions |
| tblClaims | Unified Atomic Claims — truth layer |
| tblAssumptions | Assumption with half-life — drift detection input |
| tblPatchLog | Patch node in Memory Graph (MG) — correction history |
| tblCanonGuardrails | Prime Constitution — hard invariants |
| tblDeliverables | Operational layer — delivery tracking |

---

## See Also

- [Workbook Boot Protocol](WORKBOOK_BOOT_PROTOCOL.md) — how BOOT!A1 initializes the LLM
- [Multi-Dim Prompting for Teams](multi-dim-prompting-for-teams/README.md) — 6-lens prompt model
- [Template Workbook](../../templates/creative_director_suite/README.md) — ready-to-use .xlsx
