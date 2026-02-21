# Determinism Doctrine

**Version:** 1.1
**Applies to:** All sealed governance artifacts produced by `seal_bundle.py`

---

## Core Principle

Same inputs + same clock = same commit hash. Always.

A sealed run must be **reconstructable** by any third party using only the exported bundle and the replay tool. No live system access. No "trust me" narratives. No repair after the fact.

---

## What Is in Hash Scope

The **commit hash** is computed over the canonical JSON serialization of the `hash_scope` object. This object includes:

| Category | Contents |
|----------|----------|
| **Inputs** | All CSV files in the data directory (path + SHA-256 each) |
| **Prompts** | All prompt files (path + SHA-256 each) |
| **Policies** | Policy baseline file (path + SHA-256 + version) |
| **Schemas** | All JSON Schema files (path + SHA-256 each) |
| **Parameters** | Fixed clock value, deterministic mode flag |

---

## What Is Excluded from Hash Scope

| Field | Why Excluded |
|-------|-------------|
| `observed_at` | Wall-clock timestamp varies between runs. Not semantically meaningful for reconstruction. |
| `artifacts_emitted` | Output file paths contain temp directories or absolute paths that vary. |

These exclusions are declared explicitly in the `hash_scope.exclusions` array so they are machine-verifiable.

---

## Why Clock Is Required

Without a fixed clock, the `committed_at` timestamp (and thus the hash scope parameters) would differ between runs on the same data. This would break determinism:

```
Run 1 at 14:00 → commit_hash: sha256:abc...
Run 2 at 14:01 → commit_hash: sha256:def...  (same data, different hash!)
```

Passing `--clock` binds the time-of-commit to a specific value. This is required for:
- CI determinism gates
- Golden test vectors
- Adversarial replay verification

**Rule:** Deterministic builds must pass `--clock`.

---

## No Repair After the Fact

Once a sealed run is written, its commit hash is fixed. If the conclusion is wrong:

1. **Do not edit the sealed file.** (Immutability violated.)
2. **Do not re-seal with corrected data.** (Provenance chain broken.)
3. **Create a patch** in the `PATCH_LOG` referencing the original `run_id`.

This is the "seal → version → patch" rule. Corrections are additive, never destructive.

---

## Canonical Serialization

All hashes are computed over **canonical JSON** produced by `canonical_json.py`:

- Dict keys sorted recursively
- Compact separators: `(",", ":")`
- No trailing whitespace
- Floats normalized (3.0 → 3)
- Sets/tuples converted to sorted lists
- Datetime strings normalized to UTC ISO8601 with `Z` suffix
- Newlines normalized to `\n`

This ensures the same Python object always produces the same bytes.

---

## Deterministic IDs

IDs in sealed artifacts are **derived from content**, not from random number generation:

| ID Type | Derivation |
|---------|-----------|
| `RUN-<hash8>` | First 8 hex chars of commit hash |
| `EVT-<hash8>` | First 8 hex chars of SHA-256(event_type + run_id + payload canonical) |
| `PX-<hash8>` | First 8 hex chars of SHA-256(patch content canonical) |

**Rule:** No `random.choice`, `uuid4()`, or wall-clock-derived IDs appear in sealed artifacts.

---

## Replay Procedure for Third Party

```bash
# 1. Obtain the sealed run bundle
#    (sealed JSON + manifest + input files)

# 2. Validate structural integrity
python src/tools/reconstruct/replay_sealed_run.py --sealed <path>

# 3. The tool will:
#    - Verify all required keys present
#    - Recompute commit_hash from embedded hash_scope
#    - Verify commit_hash matches provenance.deterministic_inputs_hash
#    - Verify exclusion rules honored
#    - Verify content hash integrity

# 4. Exit codes:
#    0 = REPLAY PASS (admissible)
#    1 = INADMISSIBLE (structural/logical failure)
#    2 = Schema failure (missing required keys)
#    3 = Hash mismatch (commit_hash or content hash tampered)
#    4 = Missing referenced file (--strict-files true only)
```

---

## Failure Modes

| Failure | Exit Code | Cause |
|---------|-----------|-------|
| Missing required keys | 2 | Sealed run was produced by incompatible version |
| Commit hash mismatch | 3 | hash_scope was modified after sealing |
| Content hash mismatch | 3 | Any field was modified after sealing |
| Provenance hash mismatch | 3 | commit_hash doesn't match provenance record |
| Missing exclusion declaration | 1 | observed_at not declared in exclusions |
| Missing input file | 4 | Referenced file not present (strict mode) |

---

## CI Enforcement

The `determinism_gate.yml` workflow:

1. Runs all unit tests
2. Seals the same decision twice with the same `--clock`
3. Asserts commit hashes are **identical**
4. Runs replay on both sealed outputs
5. Fails the build if any mismatch is detected

---

## Related

- [schemas/reconstruct/hash_scope_v1.json](../../schemas/reconstruct/hash_scope_v1.json) — Hash scope schema
- [schemas/reconstruct/sealed_run_v1.json](../../schemas/reconstruct/sealed_run_v1.json) — Sealed run schema
- [docs/reconstruct/ADVERSARIAL_REPLAY_GUIDE.md](ADVERSARIAL_REPLAY_GUIDE.md) — Third-party replay guide
- [docs/governance/POLICY_BASELINE.md](../governance/POLICY_BASELINE.md) — Governance policy baseline
