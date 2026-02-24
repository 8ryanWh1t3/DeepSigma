# Seal-and-Prove Pipeline

Court-grade admissibility pipeline: how a single `seal_and_prove` command
produces a verifiable, tamper-evident governance artifact bundle.

```mermaid
flowchart TD
    subgraph Inputs["Inputs"]
        DEC[Decision Log CSV]
        PROMPT[Prompt Files]
        SCHEMA[Schema Files]
        POLICY[Policy Baseline]
    end

    subgraph Seal["Step 1-3: Seal"]
        DEC --> BUILD[build_sealed_run]
        PROMPT --> BUILD
        SCHEMA --> BUILD
        POLICY --> BUILD
        BUILD --> MERKLE[Merkle Commitments<br/>4 roots: inputs, prompts,<br/>schemas, policies]
        MERKLE --> WRITE[Write Sealed JSON<br/>+ Manifest]
    end

    subgraph Sign["Step 4-5: Sign"]
        WRITE --> SIG1[Primary Signature<br/>operator / software]
        SIG1 --> WIT{Witness<br/>keys?}
        WIT -->|yes| SIG2[Append Witness Sig<br/>reviewer / auditor]
        WIT -->|no| LOG
        SIG2 --> LOG
    end

    subgraph Prove["Step 6-8: Prove"]
        LOG[Transparency Log<br/>append hash-chained entry]
        LOG --> AUDIT[Determinism Audit<br/>9 checks / strict]
        AUDIT --> REPLAY[Replay Self-Check<br/>structure + hash +<br/>sig + transparency +<br/>commitments]
    end

    subgraph Output["Output"]
        REPLAY --> PACK{Pack dir?}
        PACK -->|yes| BUNDLE[Admissibility Pack<br/>sealed + manifest +<br/>sigs + log excerpt]
        PACK -->|no| DONE[Summary Report]
        BUNDLE --> DONE
    end

    style Inputs fill:#e8f5e9,stroke:#43a047
    style Seal fill:#e3f2fd,stroke:#1e88e5
    style Sign fill:#fff3e0,stroke:#fb8c00
    style Prove fill:#fce4ec,stroke:#e53935
    style Output fill:#f3e5f5,stroke:#8e24aa
```

## Transparency Log Chain

Each log entry links to the previous via `prev_entry_hash`, forming a
tamper-evident chain.

```mermaid
flowchart LR
    E1["Entry 1<br/>prev: null<br/>hash: abc..."] --> E2["Entry 2<br/>prev: abc...<br/>hash: def..."]
    E2 --> E3["Entry 3<br/>prev: def...<br/>hash: ghi..."]
    E3 --> E4["Entry N<br/>prev: ghi...<br/>hash: ..."]

    style E1 fill:#e8f5e9,stroke:#43a047
    style E2 fill:#e3f2fd,stroke:#1e88e5
    style E3 fill:#fff3e0,stroke:#fb8c00
    style E4 fill:#fce4ec,stroke:#e53935
```

## Merkle Commitment Tree

Binary Merkle tree with SHA-256. Odd leaf count pads by duplicating
the last leaf. Four independent trees: inputs, prompts, schemas, policies.

```mermaid
flowchart TD
    L1["Leaf 1<br/>sha256:a..."] --> N1["Node<br/>sha256(a|b)"]
    L2["Leaf 2<br/>sha256:b..."] --> N1
    L3["Leaf 3<br/>sha256:c..."] --> N2["Node<br/>sha256(c|c)"]
    L3 --> N2
    N1 --> ROOT["Root<br/>sha256(ab|cc)"]
    N2 --> ROOT

    style ROOT fill:#e3f2fd,stroke:#1e88e5,stroke-width:3px
```

## Admissibility Levels

```mermaid
graph LR
    L0[L0<br/>Audit Clean] --> L1[L1<br/>Deterministic]
    L1 --> L2[L2<br/>Signed]
    L2 --> L3[L3<br/>Logged]
    L3 --> L4[L4<br/>Committed]
    L4 --> L5[L5<br/>Witnessed]
    L5 --> L6[L6<br/>Hardware-Backed]

    style L0 fill:#e8f5e9,stroke:#43a047
    style L1 fill:#c8e6c9,stroke:#43a047
    style L2 fill:#e3f2fd,stroke:#1e88e5
    style L3 fill:#bbdefb,stroke:#1e88e5
    style L4 fill:#fff3e0,stroke:#fb8c00
    style L5 fill:#ffe0b2,stroke:#fb8c00
    style L6 fill:#fce4ec,stroke:#e53935
```

## Multi-Signature Evolution

```mermaid
stateDiagram-v2
    [*] --> SingleSig: sign_artifact()
    SingleSig --> MultisigEnvelope: append_signature()
    MultisigEnvelope --> MultisigEnvelope: append_signature()
    MultisigEnvelope --> Verified: threshold met

    state SingleSig {
        sig_version: 1.0
    }
    state MultisigEnvelope {
        multisig_version: 1.0
        threshold: N
        signatures: [...]
    }
```
