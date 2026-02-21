# Sealed Run Export Specification

**Version:** 1.0
**Source table:** `LLM_OUTPUT` (`LLMOutputTable`)
**Key field:** `RunID`

---

## Overview

A sealed run is an immutable JSON snapshot of a single LLM session output. Each export captures the structured results produced during a triage session, along with provenance metadata and a content hash for audit integrity.

Sealed runs follow the core governance rule: **seal → version → patch**. Once exported, a sealed run file is never overwritten. Corrections are recorded as new patches in the `PATCH_LOG`.

---

## Target JSON Structure

```json
{
  "schema_version": "1.0",
  "meta": {
    "run_id": "RUN-001",
    "session_date": "2026-02-15",
    "operator": "J. Rivera",
    "model": "gpt-4o",
    "workbook_version": "v2",
    "export_timestamp": "2026-02-15T18:30:00Z"
  },
  "top_risks": [
    "Budget reversal",
    "Legacy API consumer discovered",
    "Assumption staleness"
  ],
  "top_actions": [
    "Validate ERP vendor SSO",
    "Re-check hiring freeze",
    "Test v2 parity"
  ],
  "system_observations": [],
  "suggested_updates": [
    "Update CLM-003 confidence",
    "Flag ASM-002 for re-review"
  ],
  "kpis": {
    "summary_confidence_pct": 78,
    "next_review_date": "2026-02-22"
  },
  "hash": "sha256:a1b2c3d4e5f6..."
}
```

### Field Reference

| Field | Source | Required |
|-------|--------|----------|
| `meta.run_id` | `LLMOutputTable.RunID` | Yes |
| `meta.session_date` | `LLMOutputTable.SessionDate` | Yes |
| `meta.operator` | `LLMOutputTable.Operator` | Yes |
| `meta.model` | `LLMOutputTable.Model` | Yes |
| `meta.workbook_version` | Hardcoded `"v2"` | Yes |
| `meta.export_timestamp` | Generated at export time (ISO 8601 UTC) | Yes |
| `top_risks[]` | Parsed from `LLMOutputTable.TopRisks` (semicolon-delimited) | Yes |
| `top_actions[]` | Parsed from `LLMOutputTable.TopActions` (semicolon-delimited) | Yes |
| `system_observations[]` | Reserved for future use | No (default `[]`) |
| `suggested_updates[]` | Parsed from `LLMOutputTable.SuggestedUpdates` (semicolon-delimited) | No |
| `kpis.summary_confidence_pct` | `LLMOutputTable.SummaryConfidence_pct` | Yes |
| `kpis.next_review_date` | `LLMOutputTable.NextReviewDate` | Yes |
| `hash` | SHA-256 of canonical JSON (excluding the `hash` field itself) | Yes |

---

## Filename Convention

```
artifacts/sealed_runs/<RunID>_<YYYYMMDDTHHMMSSZ>.json
```

Examples:
- `artifacts/sealed_runs/RUN-001_20260215T183000Z.json`
- `artifacts/sealed_runs/RUN-015_20260221T120000Z.json`

---

## Governance Rules

1. **No overwrite** — Once a sealed run file is written, it must not be modified or replaced.
2. **Seal → Version → Patch** — If a sealed run's conclusions are later found incorrect, create a patch in `PATCH_LOG` referencing the `RunID`. Do not edit the sealed file.
3. **Provenance fields** — All `meta` fields must be populated, even if the value is an empty string. This ensures traceability.
4. **Hash integrity** — The `hash` field is computed from the JSON content (with `hash` set to `""`) using SHA-256. Consumers can verify integrity by recomputing the hash.

---

## Export Tool

**Script:** `src/tools/prompt_os/export_sealed_run.py`

MVP behavior (CSV-based):
- Reads `artifacts/sample_data/prompt_os_v2/llm_output.csv`
- Exports a single run by `--run-id`
- Writes JSON to `artifacts/sealed_runs/`

```bash
python src/tools/prompt_os/export_sealed_run.py --run-id RUN-001
python src/tools/prompt_os/export_sealed_run.py --run-id RUN-001 --out artifacts/sealed_runs/RUN-001_custom.json
```

Future: workbook-based extraction via openpyxl (reads directly from `LLM_OUTPUT` tab).

---

## Reconstructability Requirements

Sealed runs produced by `seal_bundle.py` (v1+) must satisfy these additional requirements beyond the base schema:

1. **Authority envelope required.** Every sealed run must embed a complete `authority_envelope` binding actor, role, scope, policy snapshot, refusal state, and enforcement state.

2. **Policy/prompt/schema hashes required.** The `policy_snapshot` must include:
   - `policy_version` — read from `docs/governance/POLICY_VERSION.txt`
   - `policy_hash` — SHA-256 of `docs/governance/POLICY_BASELINE.md`
   - `prompt_hashes` — SHA-256 of each prompt file used
   - `schema_version` — version of the governing schema

3. **Refusal checks must be recorded.** The `refusal.checks_performed` array must list all checks evaluated, even if none triggered. An empty array is inadmissible.

4. **Enforcement must emit admissible artifacts.** `enforcement.enforcement_emitted` must be `true` and all `gate_outcomes` must have `result: "pass"` for the run to be admissible.

5. **Replay script must succeed without live system.** The sealed run must be reconstructable using only the exported bundle:
   ```bash
   python src/tools/reconstruct/replay_sealed_run.py --sealed <path>
   ```
   A non-zero exit code means the sealed run is **inadmissible**.

See:
- [schemas/reconstruct/sealed_run_v1.json](../../schemas/reconstruct/sealed_run_v1.json) — Full schema
- [schemas/reconstruct/authority_envelope_v1.json](../../schemas/reconstruct/authority_envelope_v1.json) — Authority envelope schema
- [docs/reconstruct/ADVERSARIAL_REPLAY_GUIDE.md](../reconstruct/ADVERSARIAL_REPLAY_GUIDE.md) — Third-party replay guide

---

## Related Docs

- [GOVERNANCE.md](GOVERNANCE.md) — Seal policy and retention rules
- [TABS_AND_SCHEMA.md](TABS_AND_SCHEMA.md) — LLM_OUTPUT column reference
- [TELEMETRY.md](TELEMETRY.md) — Prompt health and usage tracking
