---
title: "Creative Director Suite — Sample Dataset"
version: "0.6.2"
date: "2026-02-19"
---

# Creative Director Suite — Sample Dataset

> 8 CSVs, 25 rows each. A complete creative-production data layer
> for demonstrating Coherence Ops governance over multi-platform campaigns.

## What This Dataset Represents

A fictional Sanrio-themed creative production pipeline — from client
onboarding through campaign planning, project execution, asset creation,
shot-level breakdown, task management, prompt automation, and approval workflow.

This is the **"what we are making"** layer. The governance layer
(**"how we govern what we are making"**) lives in the Excel workbook
template — see [docs/excel-first/TABLE_SCHEMAS.md](../../docs/excel-first/TABLE_SCHEMAS.md).

## Files

| File | Rows | Description |
|------|------|-------------|
| `Sample_Clients.csv` | 25 | Client organizations with brand lines and priority tiers |
| `Sample_Campaigns.csv` | 25 | Multi-platform campaigns with KPI targets |
| `Sample_Projects.csv` | 25 | Work packages within campaigns |
| `Sample_Assets.csv` | 25 | Deliverable artifacts (video, poster, sticker, AR filter, etc.) |
| `Sample_Shots.csv` | 25 | Shot-level breakdown with timecodes |
| `Sample_Tasks.csv` | 25 | Task assignments with dependencies |
| `Sample_Prompts.csv` | 25 | LLM prompt definitions for workbook automation |
| `Sample_Approvals.csv` | 25 | Review decisions with round tracking |

Also included: `Creative_Director_Suite_Sample_Records_CSV.zip` (original archive).

## Schema Summary

### Sample_Clients.csv

| Column | Description |
|--------|-------------|
| client_id | Unique ID (CL-xxx) |
| client_name | Organization name |
| brand_line | Product/brand line |
| contact_role | Primary contact role |
| contact_email | Contact email |
| priority_tier | A / B / C |
| notes | Free-form notes |

### Sample_Campaigns.csv

| Column | Description |
|--------|-------------|
| campaign_id | Unique ID (CA-xxx) |
| client_id | FK → Clients |
| campaign_name | Campaign title |
| platforms | Pipe-delimited platform list |
| start_date | Campaign start |
| end_date | Campaign end |
| status | In_Production / Planning / Complete |
| kpi_target | Target KPI (e.g., VTR_35%) |

### Sample_Projects.csv

| Column | Description |
|--------|-------------|
| project_id | Unique ID (PRJ-xxx) |
| campaign_id | FK → Campaigns |
| project_name | Project title |
| workstream | Short-Form / Long-Form / Static / etc. |
| owner_role | Responsible role |
| priority | P1 / P2 / P3 |
| due_date | Delivery date |
| status | Active / Planning / Complete |
| risk_flag | Green / Yellow / Red |

### Sample_Assets.csv

| Column | Description |
|--------|-------------|
| asset_id | Unique ID (AS-xxx) |
| project_id | FK → Projects |
| asset_type | Video_6s / Poster / Sticker / AR_Filter / etc. |
| format | Aspect ratio (1:1, 16:9, 9:16, etc.) |
| resolution | Pixel dimensions |
| language | ISO language code |
| version | Version string |
| approval_state | Internal_Review / Client_Review / Approved / Rejected |
| storage_uri | SharePoint URI |

### Sample_Shots.csv

| Column | Description |
|--------|-------------|
| shot_id | Unique ID (SH-xxx) |
| asset_id | FK → Assets |
| shot_name | Shot identifier |
| timecode_in | Start timecode |
| timecode_out | End timecode |
| description | Shot description |
| status | Planned / In_Progress / Final |

### Sample_Tasks.csv

| Column | Description |
|--------|-------------|
| task_id | Unique ID (TSK-xxx) |
| project_id | FK → Projects |
| task_name | Task title |
| assignee | Person name |
| status | To_Do / In_Progress / Done |
| start_date | Task start |
| due_date | Task deadline |
| deps | Dependency task IDs |
| notes | Free-form notes |

### Sample_Prompts.csv

| Column | Description |
|--------|-------------|
| prompt_id | Unique ID (PMP-xxx) |
| prompt_name | Prompt title |
| scope | Workbook / Sheet / Cell |
| autoexec_cell | Cell that triggers execution |
| input_tabs | Pipe-delimited input sheets |
| output_tab | Target output sheet |
| tooling_note | Execution notes |

### Sample_Approvals.csv

| Column | Description |
|--------|-------------|
| approval_id | Unique ID (APR-xxx) |
| asset_id | FK → Assets |
| reviewer_role | Reviewer's role |
| review_round | Round number |
| decision | Approve / Revise / Reject |
| decision_date | Decision date |
| top_issue | Primary concern |
| notes | Free-form notes |

## Relationship Graph

```
Clients ──→ Campaigns ──→ Projects ──→ Assets ──→ Shots
                                   └──→ Tasks
                          Assets ──→ Approvals
```

## How This Connects to Coherence Ops

The CSVs are the **production data** — what the creative team is building.
The governance tables in the Excel workbook (tblTimeline, tblDLR, tblClaims,
tblAssumptions, tblPatchLog, tblCanonGuardrails) are the **governance layer** —
how decisions about that work are recorded, audited, and corrected.

Together they demonstrate **multi-dimensional prompting** over structured
creative data. See:

- [Workbook Boot Protocol](../../docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md)
- [Table Schemas](../../docs/excel-first/TABLE_SCHEMAS.md)
- [Multi-Dim Prompting for Teams](../../docs/excel-first/multi-dim-prompting-for-teams/README.md)
- [Template Workbook](../../templates/creative_director_suite/README.md)
