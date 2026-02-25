# Authority Boundary Primitive (ABP)

The Authority Boundary Primitive is a **stack-independent, pre-runtime governance declaration**. It declares what is allowed, denied, and required before any enforcement engine executes.

Unlike the authority envelope (which captures runtime state at decision time), the ABP defines boundaries *before* runtime begins. Any enforcement engine can read an ABP to know the boundaries without needing DeepSigma's runtime.

## What It Contains

| Section | Purpose |
| --- | --- |
| `scope` | Contract, program, and modules this ABP covers |
| `authority_ref` | Binding to an authority ledger entry (entry_id + entry_hash) |
| `objectives` | Allowed and denied objectives with reasons |
| `tools` | Allowed and denied tools with scope/reason |
| `data` | Data permissions by resource, operation, role, sensitivity |
| `approvals` | Required approval workflows (action, approver, threshold) |
| `escalation` | Escalation paths with triggers, destinations, severity |
| `runtime` | Validators to run pre/post/periodic with fail actions |
| `proof` | Required proof artifacts (seal, manifest, pack_hash, etc.) |
| `composition` | Parent/child ABP references for hierarchical composition |

## Deterministic Properties

- **ABP ID**: `ABP-` + first 8 hex chars of `sha256(canonical(scope + authority_ref + created_at))`. Same inputs always produce the same ID.
- **Hash**: `sha256(canonical(abp with hash=""))`. Same self-authenticating pattern used by sealed runs.
- **Authority Ref**: Binds to an existing authority ledger entry by `entry_id` and `entry_hash`. Does not duplicate authority data.

## Lifecycle

```text
1. Create ABP       build_abp() or build_abp.py CLI
2. Bind to authority authority_ref points to ledger entry
3. Attach to pack   seal_and_prove.py --auto-abp (or --abp-path)
4. Verify            verify_abp.py or verify_pack.py (auto-discovers abp_v1.json)
```

## Composition

Program-level ABPs compose module-level ABPs:

```text
Program ABP (parent)
  +-- Hiring Module ABP (child)
  +-- Compliance Module ABP (child)
  +-- BOE Module ABP (child)
```

The `compose_abps()` function merges boundaries from children and records child references in `composition.children`. Each child's `abp_id` and `hash` are preserved.

## ABP vs Authority Envelope

| Aspect | ABP | Authority Envelope |
| --- | --- | --- |
| **When** | Pre-runtime | At decision time |
| **Declares** | What's allowed/denied/required | What actor had what authority |
| **Contains** | Tool lists, data permissions, escalation paths | Gate outcomes, refusal state, policy snapshot |
| **Portable** | Yes — any engine can read it | Bound to DeepSigma sealed run |
| **Verifiable** | Hash + ID + authority ref | Embedded in sealed run hash chain |

## Verification (7 Checks)

`verify_abp.py` performs:

1. **abp.schema_valid** — validates against JSON schema
2. **abp.hash_integrity** — recomputes content hash
3. **abp.id_deterministic** — recomputes ABP ID from inputs
4. **abp.authority_ref_valid** — entry exists in ledger, not revoked
5. **abp.authority_not_expired** — ABP created_at within authority window
6. **abp.composition_valid** — parent/child refs consistent, no duplicates
7. **abp.no_contradictions** — no tool/objective in both allow and deny

## CLI Usage

### Build

```bash
python enterprise/src/tools/reconstruct/build_abp.py \
    --scope '{"contract_id":"CTR-001","program":"SEQUOIA","modules":["hiring","bid"]}' \
    --authority-entry-id AUTH-033059a5 \
    --authority-ledger enterprise/artifacts/authority_ledger/ledger.ndjson \
    --config abp_config.json \
    --clock 2026-02-24T00:00:00Z \
    --out-dir artifacts/abp
```

### Verify

```bash
python enterprise/src/tools/reconstruct/verify_abp.py \
    --abp artifacts/abp/abp_v1.json \
    --ledger enterprise/artifacts/authority_ledger/ledger.ndjson
```

### Pipeline Integration

```bash
python enterprise/src/tools/reconstruct/seal_and_prove.py \
    --decision-id DEC-001 \
    --clock 2026-02-21T00:00:00Z \
    --sign-algo hmac --sign-key-id ds-dev --sign-key "$KEY" \
    --auto-authority --auto-abp \
    --pack-dir /tmp/pack
```

## Files

| File | Purpose |
| --- | --- |
| `enterprise/schemas/reconstruct/abp_v1.json` | JSON Schema |
| `enterprise/src/tools/reconstruct/build_abp.py` | Builder + CLI |
| `enterprise/src/tools/reconstruct/verify_abp.py` | Standalone verifier |
| `enterprise/artifacts/public_demo_pack/abp_v1.json` | Reference artifact |
| `enterprise/tests/test_build_abp.py` | 22 unit tests |
| `enterprise/docs/31-abp.md` | Spec document |

## See Also

- [Architecture](Architecture) — System diagram with ABP mermaid link
- [Contracts](Contracts) — Runtime action contracts (ABP operates before these)
- [Sealing & Episodes](Sealing-and-Episodes) — How sealed runs reference ABP
