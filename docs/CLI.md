---
title: "DeepSigma CLI Reference"
version: "0.6.4"
date: "2026-02-19"
---

# DeepSigma CLI Reference

> Unified product CLI for Institutional Decision Infrastructure.

---

## Installation

```bash
pip install -e ".[dev,excel]"
```

---

## Commands

### `deepsigma init`

Scaffold a starter project with sample claims, drift scenario, IRIS queries, and a Trust Scorecard path.

```bash
deepsigma init my-project
cd my-project
make demo
```

Produces a runnable starter workspace with `data/`, `queries/`, `scenarios/`, and `out/` artifacts.

---

### `deepsigma doctor`

Environment health check — verifies Python version, dependencies, repo structure, and key paths.

```bash
deepsigma doctor          # Human-readable checklist
deepsigma doctor --json   # Machine-readable JSON
```

Exit code: 0 = healthy, 1 = issues detected.

---

### `deepsigma demo excel`

Run the Excel-first Money Demo — deterministic Drift→Patch proof (no LLM, no network).

```bash
deepsigma demo excel                          # Default: out/excel_money_demo
deepsigma demo excel --out /tmp/my_demo       # Custom output dir
```

Produces: `workbook.xlsx`, `run_record.json`, `drift_signal.json`, `patch_stub.json`, `coherence_delta.txt`.

---

### `deepsigma validate boot`

Validate a workbook's BOOT contract (BOOT!A1 metadata keys + 7 named tables).

```bash
deepsigma validate boot templates/creative_director_suite/Creative_Director_Suite_CoherenceOps_v2.xlsx
deepsigma validate boot myworkbook.xlsx --boot-only   # Skip table checks
```

Exit code: 0 = PASS, 1 = FAIL.

---

### `deepsigma mdpt index`

Generate a validated MDPT Prompt Index from a PromptCapabilities SharePoint list export (CSV).

```bash
deepsigma mdpt index --csv prompt_export.csv --out out/mdpt
deepsigma mdpt index --csv prompt_export.csv --out out/mdpt --include-nonapproved
```

Produces: `prompt_index.json` (schema-validated) + `prompt_index_summary.md`.

---

### `deepsigma golden-path`

Run the 7-step Golden Path decision governance loop (Connect → Normalize → Extract → Seal → Drift → Patch → Recall).

```bash
deepsigma golden-path sharepoint \
  --fixture src/demos/golden_path/fixtures/sharepoint_small --clean

deepsigma golden-path sharepoint \
  --fixture src/demos/golden_path/fixtures/sharepoint_small --json
```

---

## Version

```bash
deepsigma --version
```

---

## See Also

- [MDPT Overview](../mdpt/README.md)
- [Money Demo](excel-first/MONEY_DEMO.md)
- [BOOT Protocol](excel-first/WORKBOOK_BOOT_PROTOCOL.md)
- [Golden Path](../demos/golden_path/README.md)
