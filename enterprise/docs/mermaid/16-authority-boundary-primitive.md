# Authority Boundary Primitive (ABP)

Pre-runtime governance declaration lifecycle: declare boundaries, build deterministic ABP, attach to admissibility pack, verify integrity.

## ABP Lifecycle

```mermaid
flowchart TD
    subgraph Declare["1. Declare Boundaries"]
        D1["Scope\n(contract, program, modules)"]
        D2["Authority Ref\n(ledger entry binding)"]
        D3["Objectives\n(allowed / denied)"]
        D4["Tools\n(allow / deny)"]
        D5["Data Permissions\n(resource, ops, roles, sensitivity)"]
        D6["Approvals + Escalation"]
        D7["Runtime Validators"]
        D8["Proof Requirements"]
    end

    subgraph Build["2. Build ABP"]
        B1["Canonical JSON\n(deterministic serialization)"]
        B2["ABP ID\nsha256(scope + auth_ref + created_at)[:8]"]
        B3["Content Hash\nsha256(canonical(abp with hash=''))"]
        B4["Contradiction Check\n(no tool/objective in both allow+deny)"]
    end

    subgraph Attach["3. Attach to Pack"]
        A1["seal_and_prove.py\n--auto-abp"]
        A2["abp_v1.json\n(in admissibility pack)"]
    end

    subgraph Verify["4. Verify"]
        V1["schema_valid"]
        V2["hash_integrity"]
        V3["id_deterministic"]
        V4["authority_ref_valid"]
        V5["authority_not_expired"]
        V6["composition_valid"]
        V7["no_contradictions"]
    end

    D1 --> B1
    D2 --> B1
    D3 --> B1
    D4 --> B1
    D5 --> B1
    D6 --> B1
    D7 --> B1
    D8 --> B1

    B1 --> B2
    B1 --> B3
    B1 --> B4
    B4 -->|pass| A1
    B4 -->|fail| REJECT["ValueError:\ncontradiction detected"]

    A1 --> A2
    A2 --> V1
    V1 --> V2
    V2 --> V3
    V3 --> V4
    V4 --> V5
    V5 --> V6
    V6 --> V7
    V7 -->|all pass| VERIFIED["ABP Verified"]
    V7 -->|any fail| FAILED["Verification Failed"]

    style REJECT fill:#ff6b6b,color:#fff
    style VERIFIED fill:#51cf66,color:#fff
    style FAILED fill:#ff6b6b,color:#fff
```

## ABP vs Authority Envelope

```mermaid
graph LR
    subgraph PreRuntime["Pre-Runtime (ABP)"]
        ABP["Authority Boundary Primitive\n- What's allowed/denied/required\n- Tool lists + data permissions\n- Escalation paths\n- Portable: any engine reads it"]
    end

    subgraph AtDecision["At Decision Time (Envelope)"]
        ENV["Authority Envelope\n- What actor had what authority\n- Gate outcomes + refusal state\n- Policy snapshot\n- Bound to sealed run"]
    end

    subgraph PostExecution["Post-Execution (Sealed Run)"]
        SEAL["Sealed Run\n- Hash-chained proof\n- All of the above happened\n- Immutable evidence"]
    end

    ABP -->|"specifies boundaries"| ENV
    ENV -->|"captures state"| SEAL

    style PreRuntime fill:#e7f5ff,stroke:#1c7ed6
    style AtDecision fill:#fff3bf,stroke:#f59f00
    style PostExecution fill:#d3f9d8,stroke:#37b24d
```

## ABP Composition

```mermaid
graph TD
    PARENT["Program ABP\n(parent)\nABP-aabb1122"]

    CHILD1["Hiring Module ABP\n(child)\nABP-cc334455"]
    CHILD2["Compliance Module ABP\n(child)\nABP-dd556677"]
    CHILD3["BOE Module ABP\n(child)\nABP-ee778899"]

    PARENT -->|"composition.children[0]"| CHILD1
    PARENT -->|"composition.children[1]"| CHILD2
    PARENT -->|"composition.children[2]"| CHILD3

    CHILD1 -->|"abp_id + hash preserved"| PARENT
    CHILD2 -->|"abp_id + hash preserved"| PARENT
    CHILD3 -->|"abp_id + hash preserved"| PARENT

    style PARENT fill:#e7f5ff,stroke:#1c7ed6
    style CHILD1 fill:#fff3bf,stroke:#f59f00
    style CHILD2 fill:#fff3bf,stroke:#f59f00
    style CHILD3 fill:#fff3bf,stroke:#f59f00
```

Boundaries from children are merged into the parent. `compose_abps()` concatenates allowed/denied objectives, tool allow/deny lists, data permissions, and records each child's `abp_id` and `hash` in `composition.children`.
