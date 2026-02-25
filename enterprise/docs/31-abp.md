# 31 — Authority Boundary Primitive (ABP)

## What It Is

The Authority Boundary Primitive (ABP) is a **stack-independent, pre-runtime governance declaration**. It declares what is allowed, denied, and required before any enforcement engine executes.

Unlike the authority envelope (which captures runtime state at decision time), the ABP defines boundaries *before* runtime begins. Any enforcement engine can read an ABP to know the boundaries without needing DeepSigma's runtime. Authority becomes infrastructure; tooling becomes replaceable; governance stays stable.

## Why It Exists

DeepSigma's runtime proof layer (sealed runs, authority envelopes, DLR/RS/DS seals, transparency logs) provides enforcement **evidence** — proof that governance operated. The ABP provides the **specification** — what governance *should* enforce.

| Layer | What | When | Example |
| --- | --- | --- | --- |
| ABP | Declaration | Pre-runtime | "Operators may seal decisions but cannot revoke authority" |
| Authority Envelope | State capture | At decision time | "Operator X had direct authority, 5 gates checked, 0 failed" |
| Sealed Run | Evidence | Post-execution | Hash-chained proof that all of the above happened |

## Schema

`enterprise/schemas/reconstruct/abp_v1.json`

### Required Fields

| Field | Type | Description |
| --- | --- | --- |
| `abp_version` | `"1.0"` | Schema version |
| `abp_id` | `ABP-<hex8>` | Deterministic ID from `sha256(canonical(scope + authority_ref + created_at))` |
| `scope` | object | Contract, program, and modules this ABP covers |
| `authority_ref` | object | Binding to an authority ledger entry |
| `objectives` | object | Allowed and denied objectives with reasons |
| `tools` | object | Allowed and denied tools with scope/reason |
| `data` | object | Data permissions by resource, operation, role, sensitivity |
| `approvals` | object | Required approval workflows |
| `escalation` | object | Escalation paths with triggers and severity |
| `runtime` | object | Validators to run pre/post/periodic |
| `proof` | object | Required proof artifacts (seal, manifest, etc.) |
| `composition` | object | Parent/child ABP references for hierarchical composition |
| `effective_at` | ISO 8601 | When ABP becomes effective |
| `expires_at` | ISO 8601 or null | Expiry (null = no expiry) |
| `created_at` | ISO 8601 | Creation timestamp |
| `hash` | `sha256:...` | Self-authenticating content hash |

### ABP ID

Deterministic: `ABP-` + first 8 hex chars of `sha256(canonical(scope + authority_ref + created_at))`. Same inputs always produce the same ID.

### Hash

Self-authenticating: `sha256(canonical(abp with hash=""))`. Same pattern used by sealed runs and authority ledger entries.

### Authority Ref

Binds to an existing authority ledger entry by `entry_id` and `entry_hash`. Does not duplicate authority data — references it.

## Lifecycle

```
1. Create ABP       build_abp() or build_abp.py CLI
2. Bind to authority authority_ref points to ledger entry
3. Attach to pack   seal_and_prove.py --auto-abp (or --abp-path)
4. Verify            verify_abp.py or verify_pack.py (auto-discovers abp_v1.json)
```

## Composition

Program-level ABPs can compose module-level ABPs:

```
Program ABP (parent)
  ├── Hiring Module ABP (child)
  ├── Compliance Module ABP (child)
  └── BOE Module ABP (child)
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

## Verification Checks

`verify_abp.py` performs 7 checks:

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

Pack verification automatically discovers and verifies `abp_v1.json`:

```bash
python enterprise/src/tools/reconstruct/verify_pack.py --pack /tmp/pack --key "$KEY"
```

## Files

| File | Purpose |
| --- | --- |
| `enterprise/schemas/reconstruct/abp_v1.json` | JSON Schema |
| `enterprise/src/tools/reconstruct/build_abp.py` | Builder + CLI |
| `enterprise/src/tools/reconstruct/verify_abp.py` | Standalone verifier |
| `enterprise/artifacts/public_demo_pack/abp_v1.json` | Reference artifact |
| `enterprise/tests/test_build_abp.py` | 22 unit tests |
