# ABP v1 Specification

> Authority Boundary Primitive — a stack-independent, pre-runtime governance declaration that any enforcement engine can read to know the boundaries without needing DeepSigma's runtime.

## Table of Contents

- [Overview](#overview)
- [ABP Lifecycle](#abp-lifecycle)
- [Deterministic ID](#deterministic-id)
- [Content Hash](#content-hash)
- [Canonical JSON](#canonical-json)
- [Sections Reference](#sections-reference)
- [Objectives](#objectives)
- [Tools](#tools)
- [Composition](#composition)
- [Current ABP](#current-abp)

---

## Overview

The ABP is a JSON document that declares:

- **What** an AI system is allowed to do (objectives, tools)
- **Where** it operates (scope — contract, program, modules)
- **With what authority** (binding to authority ledger entry)
- **Under what constraints** (data permissions, approvals, escalation paths)
- **Producing what proof** (runtime validators, proof requirements)
- **With what reassessment** (delegation review triggers)

The ABP is **pre-runtime** — it exists before any agent executes. At decision time, the agent's Authority Envelope references the ABP. After execution, the Sealed Run contains both.

```mermaid
graph LR
    subgraph PreRuntime["Pre-Runtime"]
        ABP["ABP v1\nWhat's allowed / denied / required\nPortable: any engine reads it"]
    end

    subgraph AtDecision["At Decision Time"]
        ENV["Authority Envelope\nWhat actor had what authority\nGate outcomes + refusal state\nBound to sealed run"]
    end

    subgraph PostExecution["Post-Execution"]
        SEAL["Sealed Run\nHash-chained proof\nImmutable evidence"]
    end

    ABP -->|"specifies boundaries"| ENV
    ENV -->|"captures state"| SEAL

    style PreRuntime fill:#e7f5ff,stroke:#1c7ed6
    style AtDecision fill:#fff3bf,stroke:#f59f00
    style PostExecution fill:#d3f9d8,stroke:#37b24d
```

## ABP Lifecycle

```mermaid
flowchart TD
    subgraph Declare["1. Declare Boundaries"]
        D1["Scope\n(contract, program, modules)"]
        D2["Authority Ref\n(ledger entry binding)"]
        D3["Objectives\n(allowed / denied)"]
        D4["Tools\n(allow / deny)"]
        D5["Data + Approvals + Escalation"]
        D6["Runtime + Proof"]
        D7["Delegation Review\n(optional triggers)"]
    end

    subgraph Build["2. Build ABP"]
        B1["Canonical JSON\n(sorted keys, compact)"]
        B2["ABP ID\nABP- + sha256[:8]"]
        B3["Content Hash\nsha256:canonical"]
        B4["Contradiction Check"]
    end

    subgraph Embed["3. Embed + Gate"]
        E1["Stamp EDGE HTML\nscript id=ds-abp-v1"]
        E2["gate_abp.py\n10 checks per file"]
    end

    subgraph Verify["4. Verify"]
        V1["verify_abp.py\n8 checks"]
        V2["verify_pack.py\n--require-abp"]
    end

    subgraph Reassess["5. Reassess"]
        R1["Drift Triggers\nDRT-001 to DRT-004"]
        R2["Delegation Review\nReviewer approval"]
        R3["ABP Patch\nUpdated boundaries"]
    end

    D1 & D2 & D3 & D4 & D5 & D6 & D7 --> B1
    B1 --> B2 & B3 & B4
    B4 -->|pass| E1
    B4 -->|fail| REJECT["ValueError"]
    E1 --> E2
    E2 -->|pass| V1
    E2 -->|pass| V2
    V1 & V2 -->|verified| R1
    R1 -->|threshold met| R2
    R2 --> R3
    R3 -->|rebuild| B1

    style Declare fill:#e7f5ff,stroke:#1c7ed6
    style Build fill:#fff3bf,stroke:#f59f00
    style Embed fill:#e8f5e9,stroke:#43a047
    style Verify fill:#e3f2fd,stroke:#1e88e5
    style Reassess fill:#fce4ec,stroke:#e53935
    style REJECT fill:#ff6b6b,color:#fff
```

## Deterministic ID

The ABP ID is deterministic — same inputs always produce the same ID:

```
abp_id = "ABP-" + sha256(canonical_json({
    "scope": scope,
    "authority_ref": authority_ref,
    "created_at": created_at
}))[:8]
```

- Only scope, authority_ref, and created_at determine the ID
- Adding/changing objectives, tools, delegation_review, etc. does **not** change the ID
- Adding delegation_review **does** change the hash (different canonical JSON)

**Current:** `ABP-bf0afe15`

## Content Hash

The content hash covers the entire ABP:

```
hash = sha256(canonical_json(abp_with_hash_set_to_empty_string))
```

1. Copy the ABP object
2. Set `copy["hash"] = ""`
3. Serialize to canonical JSON
4. Compute SHA-256
5. Prefix with `"sha256:"`

Any change to any field (except `hash` itself) changes the content hash. This is how tamper detection works.

**Current:** `sha256:c01f3565f11678598e098083ab01d7fc429d985525756300f932f44eea722789`

## Canonical JSON

All hashes in the system are computed over canonical JSON serialization only:

| Rule | Example |
|------|---------|
| Dict keys sorted alphabetically | `{"a":1,"b":2}` not `{"b":2,"a":1}` |
| Compact separators (no spaces) | `{"a":1}` not `{ "a": 1 }` |
| Floats normalized to 15-digit precision | `1.000000000000000` |
| Datetime strings normalized to UTC Z | `2026-02-25T00:00:00Z` |
| Newlines normalized to `\n` | No `\r\n` |

**Implementation:** `enterprise/src/tools/reconstruct/canonical_json.py`

Key functions:

- `canonical_dumps(obj)` — canonical JSON string
- `sha256_text(s)` — SHA-256 of UTF-8 string, prefixed with `"sha256:"`
- `sha256_canonical(obj)` — hash of canonical JSON

## Sections Reference

| Section | Type | Required | Description |
|---------|------|----------|-------------|
| `abp_version` | string | Yes | Schema version: `"1.0"` |
| `abp_id` | string | Yes | Deterministic ID: `"ABP-xxxxxxxx"` |
| `scope` | object | Yes | `contract_id`, `program`, `modules[]` |
| `authority_ref` | object | Yes | `authority_entry_id`, `authority_entry_hash`, `authority_ledger_path` |
| `objectives` | object | Yes | `allowed[]` (id + description), `denied[]` (id + description + reason) |
| `tools` | object | Yes | `allow[]` (name + scope), `deny[]` (name + reason) |
| `data` | object | Yes | `permissions[]` (resource, operations, roles, sensitivity) |
| `approvals` | object | Yes | `required[]` (action, approver_role, threshold, timeout_ms) |
| `escalation` | object | Yes | `paths[]` (trigger, destination, severity, auto) |
| `runtime` | object | Yes | `validators[]` (name, when, fail_action, config) |
| `proof` | object | Yes | `required[]` array of proof types |
| `composition` | object | Yes | `parent_abp_id`, `parent_abp_hash`, `children[]` |
| `effective_at` | string | Yes | ISO 8601 effective date |
| `expires_at` | string/null | Yes | ISO 8601 expiry (null = no expiry) |
| `created_at` | string | Yes | ISO 8601 creation timestamp |
| `hash` | string | Yes | Self-authenticating content hash |
| `delegation_review` | object | No | Optional: `triggers[]`, `review_policy{}` |

## Objectives

### Allowed Objectives

| ID | Description |
|----|-------------|
| OBJ-001 | Evaluate bid/no-bid for opportunity DEC-001 |
| OBJ-002 | Assess staffing readiness for contract execution |
| OBJ-003 | Map compliance requirements to deliverables |
| OBJ-004 | Generate basis-of-estimate pricing models |
| OBJ-005 | Estimate award staffing allocation and costs |
| OBJ-006 | Monitor claim coherence and drift signals |
| OBJ-007 | Present read-only unified decision surface |
| OBJ-008 | Export verifiable evidence packs from any module |

### Denied Objectives

| ID | Description | Reason |
|----|-------------|--------|
| OBJ-D01 | Modify sealed decisions | Sealed artifacts are immutable per governance policy |
| OBJ-D02 | Bypass ABP verification on export | All EDGE exports must carry verified ABP |
| OBJ-D03 | Alter coherence scores without re-evaluation | Coherence values are derived from evidence chains |

## Tools

### Allowed Tools

| Name | Scope |
|------|-------|
| `seal_bundle` | DEC-001 |
| `sign_artifact` | DEC-001 |
| `replay_sealed_run` | (any) |
| `verify_pack` | (any) |
| `verify_abp` | (any) |
| `gate_abp` | (any) |
| `export_evidence_pack` | SEQUOIA |

### Denied Tools

| Name | Reason |
|------|--------|
| `authority_ledger_revoke` | Only reviewers may revoke authority grants |
| `transparency_log_delete` | Append-only log cannot be truncated |

## Composition

ABPs can form hierarchies via the `composition` section:

```mermaid
graph TD
    PARENT["Program ABP\n(parent)\nABP-aabb1122"]

    CHILD1["Hiring Module\nABP-cc334455"]
    CHILD2["Compliance Module\nABP-dd556677"]
    CHILD3["BOE Module\nABP-ee778899"]

    PARENT -->|"children[0]"| CHILD1
    PARENT -->|"children[1]"| CHILD2
    PARENT -->|"children[2]"| CHILD3

    style PARENT fill:#e7f5ff,stroke:#1c7ed6
    style CHILD1 fill:#fff3bf,stroke:#f59f00
    style CHILD2 fill:#fff3bf,stroke:#f59f00
    style CHILD3 fill:#fff3bf,stroke:#f59f00
```

`compose_abps()` merges child ABPs into a parent:

- Concatenates `objectives.allowed` + `objectives.denied`
- Concatenates `tools.allow` + `tools.deny`
- Concatenates `data.permissions`, `approvals.required`, `escalation.paths`, `runtime.validators`
- Unions `proof.required`
- Deduplicates `delegation_review.triggers` by ID
- Takes tightest `review_policy.timeout_ms` from children
- Records each child's `abp_id` + `hash` in `composition.children`

## Current ABP

| Field | Value |
|-------|-------|
| `abp_id` | `ABP-bf0afe15` |
| `hash` | `sha256:c01f3565f11678598e098083ab01d7fc429d985525756300f932f44eea722789` |
| `scope.contract_id` | `CTR-DEMO-001` |
| `scope.program` | `SEQUOIA` |
| `scope.modules` | hiring, bid, compliance, boe, award_staffing, coherence, suite_readonly, unified |
| `authority_ref.entry_id` | `AUTH-033059a5` |
| `created_at` | `2026-02-25T00:00:00Z` |
| `effective_at` | `2026-02-25T00:00:00Z` |
| `expires_at` | null (no expiry) |

**File:** `edge/abp_v1.json`
**Schema:** `enterprise/schemas/reconstruct/abp_v1.json`
