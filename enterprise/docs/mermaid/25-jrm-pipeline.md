# 25 — JRM Pipeline & Federation

Log-agnostic Judgment Refinement Module: 3 adapters, 5-stage coherence pipeline, JRM-X packet builder, and enterprise cross-environment federation.

```mermaid
graph TB
    subgraph "Log Sources"
        SURI[Suricata EVE<br/>JSON lines]
        SNRT[Snort fast.log<br/>GID:SID:REV]
        CPLT[Copilot Agent<br/>JSONL]
    end

    subgraph "Adapters (lossless)"
        A1[JRM-A01<br/>suricata_eve]
        A2[JRM-A02<br/>snort_fastlog]
        A3[JRM-A03<br/>copilot_agent]
    end

    SURI --> A1
    SNRT --> A2
    CPLT --> A3

    A1 --> NORM[JRMEvent stream<br/>sha256 evidence hash]
    A2 --> NORM
    A3 --> NORM

    subgraph "5-Stage Pipeline"
        direction TB
        S1[JRM-S01 Truth<br/>Cluster → Claims]
        S2[JRM-S02 Reasoning<br/>Decision Lanes]
        S3[JRM-S03 Drift<br/>FP_SPIKE / STALE_LOGIC /<br/>MISSING_MAPPING / ASSUMPTION_EXPIRED]
        S4[JRM-S04 Patch<br/>rev++ with lineage]
        S5[JRM-S05 Memory Graph<br/>nodes + edges + canon]
    end

    NORM --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5

    S5 --> PKT[Rolling Packet Builder<br/>50k events OR 25MB]

    subgraph "JRM-X Packet (zip)"
        TS[truth_snapshot.json]
        ALS[authority_slice.json]
        DLR[decision_lineage.jsonl]
        DS[drift_signal.jsonl]
        MG[memory_graph.json]
        CE[canon_entry.json]
        MAN[manifest.json<br/>SHA-256 per file]
    end

    PKT --> TS
    PKT --> ALS
    PKT --> DLR
    PKT --> DS
    PKT --> MG
    PKT --> CE
    PKT --> MAN

    subgraph "Enterprise Federation"
        GATE[JRM Gate<br/>validate + scope + redact]
        HUB[JRM Hub<br/>multi-env ingest]
        DETECT[Cross-Env Drift<br/>VERSION_SKEW /<br/>POSTURE_DIVERGENCE]
        ADV[Advisory Engine<br/>publish / accept / decline]
        SIGN[Packet Signer<br/>HMAC-SHA256]
    end

    MAN --> SIGN
    SIGN --> GATE
    GATE --> HUB
    HUB --> DETECT
    DETECT --> ADV

    style S1 fill:#e8f5e9
    style S2 fill:#e3f2fd
    style S3 fill:#fff3e0
    style S4 fill:#fce4ec
    style S5 fill:#f3e5f5
    style GATE fill:#e0f2f1
    style HUB fill:#e0f2f1
    style ADV fill:#e0f2f1
```

## CLI Commands

| Command | Stage |
|---------|-------|
| `coherence jrm ingest` | Adapter → NDJSON |
| `coherence jrm run` | Pipeline → Packets |
| `coherence jrm validate` | Packet verification |
| `coherence jrm adapters` | List adapters |
| `deepsigma jrm federate` | Cross-env federation |
| `deepsigma jrm gate validate` | Gate validation |
| `deepsigma jrm hub replay` | Hub replay |
| `deepsigma jrm advisory publish` | Advisory workflow |

## Support Modules

| Module | Purpose | File |
|--------|---------|------|
| Adapter base | `parse_line()` + `parse_stream()` + `hash_raw()` | `src/core/jrm/adapters/base.py` |
| Adapter registry | `register_adapter()` + `get_adapter()` | `src/core/jrm/adapters/registry.py` |
| Pipeline runner | Chain 5 stages with error tolerance | `src/core/jrm/pipeline/runner.py` |
| Packet naming | `JRM_X_PACKET_<ENV>_<start>_<end>_partNN` | `src/core/jrm/packet/naming.py` |
| Manifest builder | SHA-256 per file + metadata | `src/core/jrm/packet/manifest.py` |
| Rolling builder | Hybrid threshold auto-flush | `src/core/jrm/packet/builder.py` |
| Extension hooks | Drift detectors, validators, connectors, CLI | `src/core/jrm/hooks/registry.py` |
| Federation gate | Integrity + scope + redaction | `enterprise/src/deepsigma/jrm_ext/federation/gate.py` |
| Federation hub | Multi-env ingest + drift detect | `enterprise/src/deepsigma/jrm_ext/federation/hub.py` |
| Advisory engine | Publish/accept/decline lifecycle | `enterprise/src/deepsigma/jrm_ext/federation/advisory.py` |
| Packet signer | HMAC-SHA256 canonical JSON | `enterprise/src/deepsigma/jrm_ext/security/signer.py` |
