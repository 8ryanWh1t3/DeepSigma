# Excel-First Governance

The Excel-first governance model brings Coherence Ops to teams who already live in Excel and SharePoint. Instead of CLI commands, JSON artifacts, and Python scripts, governance happens through named tables, structured prompts, and write-back rows — all inside a shared workbook.

---

## BOOT Protocol

Cell `BOOT!A1` acts as a system prompt. When the workbook is attached to an LLM, this cell initializes the entire governance context.

**Structure:**

```
YOU ARE: Creative Ops Copilot (Coherence Ops: Truth · Reasoning · Memory)
OPENING MOVE: Read tables, then ask "What Would You Like To Do Today?"
MENU:
  1. Build Claims from Deliverables
  2. Refresh Assumptions
  3. Detect Drift
  4. Propose Patch Options
  5. Canon Audit
  6. Exec Summary
  7. Asset Checklist
RULES: Use ONLY workbook data. Cite TableName + Row_IDs. Enforce Canon Guardrails.
OUTPUT: Findings → Recommended Actions → Write-back rows for Excel
```

**Why it works:** LLMs parse structured text in A1 as system instructions. Named tables give deterministic cell references. The menu constrains the interaction to governed operations.

Full spec: `docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md`

---

## Table Schemas

Seven named Excel tables map directly to Coherence Ops primitives:

### tblTimeline

Milestone tracking with drift and patch status.

| Column | Type | Description |
|--------|------|-------------|
| Milestone_ID | Text | Unique identifier |
| Milestone_Name | Text | Short descriptive name |
| Owner | Text | Responsible person |
| Due_Date | Date | Target completion date |
| Status | Text | On Track / At Risk / Blocked / Complete |
| Drift_Flag | Boolean | TRUE if drift detected |
| Patch_Ref | Text | Link to tblPatchLog row if patched |

### tblDeliverables

Asset-level deliverable tracking.

| Column | Type | Description |
|--------|------|-------------|
| Deliverable_ID | Text | Unique identifier |
| Deliverable_Name | Text | Asset or output name |
| Milestone_ID | Text | FK → tblTimeline |
| Format | Text | File type or medium |
| Status | Text | Draft / In Review / Approved / Delivered |
| Assignee | Text | Responsible person |
| Due_Date | Date | Target delivery date |

### tblDLR

Decision Ledger Records — formal decision capture.

| Column | Type | Description |
|--------|------|-------------|
| DLR_ID | Text | Unique identifier |
| Decision_Title | Text | Short decision name |
| Decision_Date | Date | When the decision was made |
| Decision_Owner | Text | Who made the decision |
| Rationale | Text | Why this choice was made |
| Evidence_Refs | Text | Supporting data or sources |
| Status | Text | Active / Superseded / Revoked |

### tblClaims

Verifiable claims tied to decisions.

| Column | Type | Description |
|--------|------|-------------|
| Claim_ID | Text | Unique identifier |
| Claim_Text | Text | The verifiable assertion |
| DLR_Ref | Text | FK → tblDLR |
| Confidence | Number | 0.0–1.0 confidence score |
| Evidence | Text | Supporting evidence |
| Status | Text | Active / Challenged / Refuted |
| Last_Verified | Date | Most recent verification date |

### tblAssumptions

Assumptions with confidence scores and time-to-live.

| Column | Type | Description |
|--------|------|-------------|
| Assumption_ID | Text | Unique identifier |
| Assumption_Text | Text | The assumption statement |
| Owner | Text | Who holds this assumption |
| Confidence | Number | 0.0–1.0 confidence score |
| TTL_Days | Number | Days before review required |
| Last_Reviewed | Date | Most recent review date |
| Status | Text | Active / Expired / Replaced |

### tblPatchLog

Drift → Patch correction log.

| Column | Type | Description |
|--------|------|-------------|
| Patch_ID | Text | Unique identifier |
| Drift_Source | Text | What triggered the drift |
| Drift_Type | Text | time / freshness / bypass / verify / outcome |
| Severity | Text | low / medium / high / critical |
| Patch_Action | Text | Corrective action taken |
| Applied_Date | Date | When the patch was applied |
| Applied_By | Text | Who applied the patch |

### tblCanonGuardrails

Blessed rules and constraints — the workbook's constitution.

| Column | Type | Description |
|--------|------|-------------|
| Canon_ID | Text | Unique identifier |
| Rule_Text | Text | The guardrail statement |
| Category | Text | Brand / Legal / Process / Quality |
| Severity | Text | Must / Should / May |
| Source | Text | Where the rule comes from |
| Last_Updated | Date | Most recent update |
| Status | Text | Active / Deprecated |

Full column specs: `docs/excel-first/TABLE_SCHEMAS.md`

---

## Writeback Contract

Every LLM response must include:

1. **Findings** — what was discovered (citing TableName + Row_IDs)
2. **Recommended Actions** — what should change
3. **Write-back rows** — paste-ready rows for Excel tables, specifying target table and columns

This ensures every LLM output is traceable and actionable within the workbook.

---

## 6-Lens Prompt Model

Six perspectives for multi-dimensional governance:

| Lens | Focus | Example Question |
|------|-------|-----------------|
| **PRIME** | Constitutional compliance | "Does this decision violate any Canon Guardrails?" |
| **EXEC** | Strategic alignment | "How does this impact the campaign timeline?" |
| **OPS** | Operational readiness | "Are all deliverables on track for the milestone?" |
| **AI-TECH** | Technical feasibility | "Can the asset pipeline handle this volume?" |
| **HUMAN** | Team and stakeholder impact | "Who needs to approve this change?" |
| **ICON** | Brand and creative integrity | "Does this maintain brand consistency?" |

Each lens crosses with three operations:

| Operation | What it does |
|-----------|-------------|
| **IntelOps** | Gather intelligence — scan tables for signals |
| **ReOps** | Re-evaluate — challenge assumptions and claims |
| **FranOps** | Franchise governance — enforce canon and brand rules |

**6 lenses × 3 operations = 18 prompt patterns** — all available from the BOOT menu.

Full guide: `docs/excel-first/multi-dim-prompting-for-teams/README.md`

---

## Mapping to Coherence Ops

| Excel Table | Coherence Ops Primitive | Artifact |
|-------------|------------------------|----------|
| tblTimeline | Decision Scaffold | DS |
| tblDeliverables | Decision Scaffold | DS |
| tblDLR | Decision Ledger Record | DLR |
| tblClaims | Atomic Claims | Claim |
| tblAssumptions | Reasoning Scaffold | RS |
| tblPatchLog | Patch Packets | Patch |
| tblCanonGuardrails | Canon | Canon |

The same Truth · Reasoning · Memory loop runs in Excel as in the Python runtime — just with a human-readable interface.

---

## See Also

- [Creative Director Suite](Creative-Director-Suite) — Dataset, workbook, quickstart
- [Coherence Ops Mapping](Coherence-Ops-Mapping) — DLR / RS / DS / MG governance artifacts
- [Unified Atomic Claims](Unified-Atomic-Claims) — Claim primitive specification
- [Canon](Canon) — Blessed claim memory and canon entry lifecycle
