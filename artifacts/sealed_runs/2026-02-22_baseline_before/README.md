# Coherence Ops GitHub-Native Pilot

## What this pilot proves

This pilot demonstrates three release-gate capabilities using only repository artifacts and automation:

1. Drift -> Patch loop is real and traceable.
2. Coherence Index (CI) is computed deterministically from repo state.
3. WHY retrieval can be <= 60 seconds using linked markdown records and repo search.

All records in this pilot are fictional and safe.

## Run CI locally

From repo root:

```bash
python3 scripts/compute_ci.py
```

Outputs are written to:

- `pilot/reports/ci_report.json`
- `pilot/reports/ci_report.md`

## Create a decision

1. Copy `schemas/DLR_TEMPLATE.md` to `pilot/decisions/<decision-id>.md`.
2. Fill intent, decision, assumptions, owner, and seal sections.
3. Link related assumptions by ID (for example, `A-2026-001`).

## File drift

1. Copy `schemas/DRIFT_SIGNAL_TEMPLATE.md` to `pilot/drift/DRIFT-<year>-<id>.md`.
2. Set severity, trigger, evidence, linked decision, owner, and status.
3. Open a GitHub issue using the Drift Signal template.

## Patch drift

1. Copy `schemas/PATCH_TEMPLATE.md` to `pilot/patches/PATCH-<year>-<id>.md`.
2. Link drift signal and changed files.
3. Update related decision/assumption records.
4. Re-run `python3 scripts/compute_ci.py`.

## Target KPI

- Median WHY retrieval <= 60 seconds

## Demo path (click in order)

1. `pilot/decisions/2026-001-demo-threat-model.md`
2. `pilot/assumptions/A-2026-001.md`
3. `pilot/drift/DRIFT-2026-001.md`
4. `pilot/patches/PATCH-2026-001.md`
5. `pilot/reports/ci_report.md`

Use `rg "2026-001|A-2026-001|DRIFT-2026-001|PATCH-2026-001" pilot/` to retrieve WHY links quickly.

## Pilot Drills

- PASS->FAIL->PASS: `make pilot-in-a-box`
- WHY-60s challenge: `make why-60s`

## Governance

- Scope: `docs/pilot/PILOT_SCOPE.md`
- DRI model: `docs/pilot/DRI_MODEL.md`
- Branch protection: `docs/pilot/BRANCH_PROTECTION.md`
- Contract: `docs/pilot/PILOT_CONTRACT_ONEPAGER.md`

## Pilot Drills

- PASS→FAIL→PASS: `make pilot-in-a-box`
- WHY-60s: `make why-60s`

## Pilot Governance

- Scope: `docs/docs/pilot/PILOT_SCOPE.md`
- DRI model: `docs/docs/pilot/DRI_MODEL.md`
- Branch protection: `docs/docs/pilot/BRANCH_PROTECTION.md`
- Contract: `docs/docs/pilot/PILOT_CONTRACT_ONEPAGER.md`

## Release Notes

- `docs/docs/release/RELEASE_NOTES_v2.0.2.md`
