---
title: "Release Notes — v0.6.2 Creative Director Suite"
version: "0.6.2"
codename: "Creative Director Suite"
date: "2026-02-19"
---

# v0.6.2 — Creative Director Suite

**Release date:** 2026-02-19

> From code-first governance to Excel-first governance — Coherence Ops
> meets teams where they already work.

---

## What "Creative Director Suite" Means

Before v0.6.2, Coherence Ops required Python, CLI commands, and JSON
artifacts. The Creative Director Suite proves that the same governance
primitives — claims, assumptions, decisions, drift, patches — work
inside a shared Excel workbook that any team can edit in SharePoint.
No code required. Same rigor.

---

## What's New

### Tier 1 — Dataset & Workbook

- **Creative Director Suite dataset** (`datasets/creative_director_suite/`):
  8 CSVs, 25 rows each — clients, campaigns, projects, assets, shots,
  tasks, prompts, approvals. Sanrio-themed creative production data.
- **Excel workbook generator** (`tools/generate_cds_workbook.py`):
  Produces a governed workbook with BOOT sheet, 7 named tables,
  25 sample rows each, and a CI_DASHBOARD.
- **Template workbook** (`templates/creative_director_suite/`):
  Ready-to-use .xlsx with plug-and-play governance tables.

### Tier 2 — Excel-First Documentation

- **Workbook Boot Protocol** (`docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md`):
  How BOOT!A1 initializes LLM context for the entire workbook.
- **Table Schemas** (`docs/excel-first/TABLE_SCHEMAS.md`):
  7 governance table schemas with full column definitions, types, and
  cross-table relationships.
- **Multi-Dimensional Prompting for Teams**
  (`docs/excel-first/multi-dim-prompting-for-teams/README.md`):
  6-lens prompt model (PRIME/EXEC/OPS/AI-TECH/HUMAN/ICON) with
  SharePoint-first architecture and worked example.

### Tier 3 — Integration

- **Root README update**: New Creative Director Suite section with quickstart.
- **NAV.md update**: Excel-First Governance section with 6 resource links.
- **CHANGELOG update**: [0.6.2] entry with full changeset.
- **Version bump**: pyproject.toml 0.6.1 → 0.6.2, coherence_ops/__init__.py 0.5.0 → 0.6.2.
- **Optional dependency**: `[excel]` group added to pyproject.toml (openpyxl).

---

## By the Numbers

| Metric | Value |
|--------|-------|
| New files | 17 |
| Modified files | 5 |
| CSVs committed | 8 (200 total rows) |
| Named Excel tables | 7 |
| Sample rows per table | 25 |
| 6-Lens prompt dimensions | 6 lenses x 3 ops = 18 prompts |
| Governance tables | 7 (tblTimeline, tblDeliverables, tblDLR, tblClaims, tblAssumptions, tblPatchLog, tblCanonGuardrails) |
| Workbook sheets | 12 |

---

## Quick Start

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -e ".[excel]"

# Generate the workbook
python tools/generate_cds_workbook.py
# Output: templates/creative_director_suite/Creative_Director_Suite_CoherenceOps_v2.xlsx

# Or just explore the CSVs
ls datasets/creative_director_suite/samples/
```

---

## Verify

```bash
# Version check
python -c "import coherence_ops; print(coherence_ops.__version__)"
# Expected: 0.6.2

# Workbook exists
ls templates/creative_director_suite/Creative_Director_Suite_CoherenceOps_v2.xlsx

# Workbook structure
python -c "
import openpyxl
wb = openpyxl.load_workbook('templates/creative_director_suite/Creative_Director_Suite_CoherenceOps_v2.xlsx')
print('Sheets:', wb.sheetnames)
print('BOOT!A1 starts with:', wb['BOOT']['A1'].value[:60])
for ws in wb.worksheets:
    for t in ws.tables.values():
        print(f'  Table: {t.displayName} in {ws.title}')
"
```

---

## Key Links

| Resource | Path |
|----------|------|
| Dataset README | [`datasets/creative_director_suite/README.md`](../datasets/creative_director_suite/README.md) |
| Boot Protocol | [`docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md`](../docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md) |
| Table Schemas | [`docs/excel-first/TABLE_SCHEMAS.md`](../docs/excel-first/TABLE_SCHEMAS.md) |
| Prompting Guide | [`docs/excel-first/multi-dim-prompting-for-teams/README.md`](../docs/excel-first/multi-dim-prompting-for-teams/README.md) |
| Template | [`templates/creative_director_suite/`](../templates/creative_director_suite/) |
| Generator Script | [`tools/generate_cds_workbook.py`](../tools/generate_cds_workbook.py) |
| Changelog | [`CHANGELOG.md`](../CHANGELOG.md) |

---

**Σ OVERWATCH** — *Every decision governed. Even in Excel.*
