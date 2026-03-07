# Core Primitives — Architecture Overview

Four canonical, cross-cutting data types underpin all OVERWATCH governance flows.

## Design Principles

1. **Additive, not replacing** — existing domain models remain untouched
2. **Schema-first** — JSON schemas define the contract; Python dataclasses implement
3. **Never overwrite** — patches supersede; claims are retracted, not deleted
4. **Deterministic sealing** — SHA-256 hashing for tamper detection

## Primitives

### AtomicClaim

The indivisible unit of asserted truth.  Every higher-order structure
(DecisionEpisode, DriftSignal, Patch) is composed of or references claims.

- **ID pattern**: `CLAIM-YYYY-NNNN`
- **Epistemic types**: observation, inference, assumption, forecast, norm, constraint
- **Lifecycle**: active → expired | superseded | disputed | retracted
- **Confidence**: 0.00–1.00 machine-comparable score
- **Expiry**: optional `expires_at` timestamp; `is_expired()` helper

### DecisionEpisode

The orchestration container.  Captures the full decision lifecycle from goal
through outcome, referencing the claims that informed it.

- **Lifecycle**: pending → active → sealed → archived (or frozen)
- **Options**: available choices with selected/rejected tracking
- **Blast radius**: scope of potential impact
- **Kill switches**: named stops that can halt execution
- **Lineage**: parent/child decision references

### DriftSignal

Divergence between expected and observed state.  Links a DecisionEpisode to
the corrective action that follows.

- **Trigger**: what caused the drift (half_life_expiry, contradiction, etc.)
- **Severity**: green / yellow / red (traffic-light model)
- **Lifecycle**: detected → acknowledged → resolved | escalated | suppressed
- **State comparison**: `expected_state` vs `observed_state`

### Patch

Append-only correction resolving a drift signal.  Patches never overwrite
prior state — they supersede, creating an immutable lineage chain.

- **Lifecycle**: proposed → approved → applied (or rejected | superseded)
- **Supersedes**: list of prior patch IDs this one replaces
- **Lineage**: revision tracking and drift reference

## Relationships

```mermaid
graph LR
    AC[AtomicClaim] -->|used_by| DE[DecisionEpisode]
    DE -->|triggers| DS[DriftSignal]
    DS -->|resolved_by| P[Patch]
    P -->|updates| AC
    P -.->|supersedes| P2[Prior Patch]
    P -->|lineage| MG[MemoryGraph]

    style AC fill:#162447,stroke:#e94560,color:#fff
    style DE fill:#1a1a2e,stroke:#e94560,color:#fff
    style DS fill:#162447,stroke:#533483,color:#fff
    style P fill:#1a1a2e,stroke:#533483,color:#fff
    style MG fill:#0f3460,stroke:#e94560,color:#fff
    style P2 fill:#1a1a2e,stroke:#533483,color:#fff,stroke-dasharray:5
```

Patch updates lineage and does not overwrite prior state.

## Coexistence with Existing Models

These canonical primitives are reference definitions.  Existing domain-specific
models remain in place and are not replaced.

| Canonical Primitive | Existing Domain Model | Module | Relationship |
|---|---|---|---|
| AtomicClaim | `Claim` (surface layer) | `decision_surface/models.py` | Simplified evaluation view — no provenance, no expiry |
| AtomicClaim | `Claim` (JRM) | `jrm/types.py` | Extraction-focused — tied to source events |
| AtomicClaim | `claim.schema.json` | `schemas/` | Full canonical JSON — superset of AtomicClaim fields |
| DecisionEpisode | `episode.schema.json` | `schemas/` | Execution-focused — DTE, telemetry, verification |
| DecisionEpisode | `EpisodeState` | `episode_state.py` | State machine — same status values |
| DecisionEpisode | `DLREntry` / `ClaimNativeDLREntry` | `decision_log.py` | Post-seal record — derived from episodes |
| DriftSignal | `DriftSignalCollector` | `drift_signal.py` | Aggregation layer — buckets and summaries |
| DriftSignal | `DriftDetection` | `jrm/types.py` | JRM-specific — tied to pipeline fingerprints |
| DriftSignal | `drift.schema.json` | `schemas/` | Runtime drift events — episode-scoped |
| Patch | `PatchRecord` | `jrm/types.py` | JRM-specific — revision tracking, never-overwrite |
| Patch | `PatchRecommendation` | `decision_surface/models.py` | Surface layer — recommendation only |
| Patch | `TensionPatch` | `paradox_ops/models.py` | Paradox-specific — tension remediation |

## Future Integration Points

These are documented convergence points, not runtime changes.

- **Memory Graph** (`memory_graph.py`): `add_claim()`, `add_episode()`, `add_drift()`,
  `add_patch()` already accept dict payloads.  Canonical primitives can feed these
  via `to_dict()` with no adapter needed.

- **FEEDS Event Bus** (`feeds/`): canonical primitives can be wrapped in FEEDS
  envelopes using `build_envelope()`.  Topic mapping: AtomicClaim → `TRUTH_SNAPSHOT`,
  DecisionEpisode → `DECISION_LINEAGE`, DriftSignal → `DRIFT_SIGNAL`.

- **Coherence Scoring** (`scoring.py`): canonical primitives provide structured
  inputs for the CoherenceScorer pipeline (DLR + RS + DS + MG → score).

- **AuthorityOps** (`authority/`): DecisionEpisode maps naturally to authority
  decision gates.  Blast radius and kill switches align with existing policy
  evaluation.

## File Layout

| File | Purpose |
|---|---|
| `src/core/primitives.py` | Python dataclasses and enums |
| `src/core/schemas/primitives/*.schema.json` | JSON Schema contracts (4 files) |
| `src/core/fixtures/primitives/*.json` | Example payloads (4 files) |
| `tests/test_primitives.py` | Unit and lifecycle tests |
| `docs/architecture/core_primitives.md` | This document |
