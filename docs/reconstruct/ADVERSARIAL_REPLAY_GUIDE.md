---
title: "Adversarial Replay Guide"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-21"
---

# Adversarial Replay Guide

How a third party reconstructs and validates a sealed decision — without live system access.

---

## What Files Must Be Present

A complete replay bundle requires:

| File | Purpose |
|------|---------|
| `artifacts/sealed_runs/<RUN_ID>_<timestamp>.json` | The sealed run (authority envelope + decision state + hashes) |
| `artifacts/sealed_runs/<RUN_ID>_<timestamp>.manifest.json` | Manifest linking sealed run to inputs |
| `artifacts/sample_data/prompt_os_v2/*.csv` | Input CSVs (decision_log, patch_log, etc.) |
| `docs/governance/POLICY_BASELINE.md` | Policy document (hashable) |
| `docs/governance/POLICY_VERSION.txt` | Policy version string |
| `prompts/**/*.md` | Prompt files (hashed in policy snapshot) |
| `schemas/reconstruct/*.json` | Schemas for structural validation |

---

## How a Third Party Replays

### Step 1: Obtain the bundle

The reviewing party receives the sealed run JSON and its associated artifacts. No live system access is required.

### Step 2: Run the replay tool

```bash
python src/tools/reconstruct/replay_sealed_run.py \
  --sealed artifacts/sealed_runs/<RUN_ID>_<timestamp>.json
```

### Step 3: Read the reconstruction report

The replay tool checks every structural requirement:

- **Authority:** Who held authority, what type, when effective/expired
- **Scope:** What decisions, claims, patches, prompts, datasets were bound
- **Policy:** Which policy version governed, with SHA-256 hash
- **Refusal:** Whether refusal was structurally possible, what checks ran
- **Enforcement:** Which gates were checked, outcomes, whether artifacts emitted
- **Provenance:** Run ID, creation timestamp, deterministic inputs hash
- **Integrity:** SHA-256 content hash verification

### Step 4: Interpret results

- **ADMISSIBLE** — All checks pass. The sealed run is structurally complete and internally consistent.
- **INADMISSIBLE** — One or more checks fail. The report identifies exactly which checks failed and why.

---

## What Constitutes Failure

A sealed run is **inadmissible** if any of the following are true:

1. **Missing structure** — Required fields absent from sealed run JSON
2. **No authority** — Actor or authority block missing or malformed
3. **Unbound scope** — No decisions bound to the sealed run
4. **No policy snapshot** — Policy version or hash missing
5. **Refusal not available** — `refusal_available` is false (system could not refuse)
6. **No refusal checks** — `checks_performed` is empty (refusal was not evaluated)
7. **Enforcement not emitted** — `enforcement_emitted` is false
8. **Failed gates** — Any enforcement gate has `result: "fail"`
9. **No provenance** — Run ID or inputs hash missing
10. **Hash mismatch** — Content hash does not match recomputed hash (tampering indicator)

---

## What Constitutes Admissibility

A sealed run is **admissible** when:

1. All required structural fields are present and well-typed
2. Authority was held by a named actor with a valid role
3. Scope was explicitly bound to at least one decision
4. Policy version and hash are recorded
5. Refusal was structurally possible and checks were evaluated
6. All enforcement gates passed and enforcement was emitted
7. Provenance includes run ID and deterministic inputs hash
8. Content hash verifies (no post-seal modification)

---

## Related

- [schemas/reconstruct/sealed_run_v1.json](../../schemas/reconstruct/sealed_run_v1.json) — Sealed run schema
- [schemas/reconstruct/authority_envelope_v1.json](../../schemas/reconstruct/authority_envelope_v1.json) — Authority envelope schema
- [schemas/reconstruct/refusal_codes_v1.json](../../schemas/reconstruct/refusal_codes_v1.json) — Refusal code definitions
- [docs/governance/POLICY_BASELINE.md](../governance/POLICY_BASELINE.md) — Governance policy baseline
