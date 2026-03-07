# DecisionSurface — Portable Coherence Ops Runtime

> Generic adapter layer for executing claim/event evaluation across external environments.

## Overview

DecisionSurface is a portable runtime layer that sits above domain modes. It provides a generic claim-event evaluation pipeline that can be executed in any environment through pluggable adapters. Unlike domain modes, DecisionSurface has no function IDs, no routing table entries, and no FEEDS integration — it is a standalone primitive.

**Package**: `src/core/decision_surface/` (8 modules)

## Architecture

```
Core Engine (severity, seal_and_hash, memory_graph)
        |
  DecisionSurface Runtime  (ingest / evaluate / seal)
        |
  SurfaceAdapter ABC  (8 abstract methods)
        |
   +-----------+-----------+
   |           |           |
Notebook    CLI       Vantage/Foundry
(in-memory) (+ JSON)   (stub)
```

## Modules

| Module | Purpose |
|--------|---------|
| `models.py` | ClaimStatus enum + 9 dataclasses (Claim, Event, Evidence, Assumption, DriftSignal, PatchRecommendation, DecisionArtifact, MemoryGraphUpdate, EvaluationResult) |
| `surface_adapter.py` | SurfaceAdapter ABC with 8 abstract methods |
| `claim_event_engine.py` | 7 shared evaluation functions — ALL logic lives here |
| `notebook_adapter.py` | In-memory reference adapter for notebooks and testing |
| `cli_adapter.py` | In-memory adapter with `to_json()` for CLI output |
| `vantage_adapter.py` | Honest stub — all methods raise NotImplementedError |
| `runtime.py` | DecisionSurface orchestration class with `from_surface()` factory |
| `__init__.py` | Package exports |

## SurfaceAdapter ABC

Every adapter implements 8 methods:

| Method | Purpose |
|--------|---------|
| `ingest_claims(claims)` | Store incoming claims |
| `ingest_events(events)` | Store incoming events |
| `get_claims()` | Retrieve all stored claims |
| `get_events()` | Retrieve all stored events |
| `get_evidence()` | Retrieve all evidence links |
| `store_drift_signals(signals)` | Persist drift signals |
| `store_patches(patches)` | Persist patch recommendations |
| `store_evaluation_result(result)` | Persist evaluation result |

## Claim-Event Engine

All evaluation logic lives in `claim_event_engine.py`. Adapters only handle storage/retrieval — no logic duplication.

| Function | Purpose |
|----------|---------|
| `match_events_to_claims` | Match events to claims via `claim_refs` |
| `detect_contradictions` | Find contradictory event pairs (approved/denied, confirmed/refuted, etc.) |
| `detect_expired_assumptions` | Flag claims linked to expired assumptions |
| `compute_blast_radius` | Count claims sharing evidence with a given claim |
| `build_patch_recommendation` | Map drift type to corrective action |
| `build_memory_graph_update` | Build MG nodes/edges from evaluation |
| `evaluate` | Orchestrate all above into an EvaluationResult |

## Claim Statuses

| Status | Meaning |
|--------|---------|
| `satisfied` | 1+ matching events found |
| `at_risk` | Matched but claim confidence < 0.5 |
| `drifted` | Contradiction detected or assumption expired |
| `pending` | No matching events yet |

## Drift Type to Patch Action Mapping

| Drift Type | Action |
|------------|--------|
| `contradiction` | `investigate_contradiction` |
| `expired_assumption` | `review_assumption` |
| `unsupported` | `gather_evidence` |
| (default) | `review_claim` |

## Adapters

### NotebookAdapter
In-memory reference implementation. All data stored in lists. Returns copies from get methods.

### CLIAdapter
Same as NotebookAdapter plus `to_json()` for structured JSON output with camelCase keys.

### VantageAdapter (stub)
All 8 methods raise `NotImplementedError` with a message pointing to `docs/decision_surface.md` for the integration roadmap.

## Usage

```python
from core.decision_surface import DecisionSurface, Claim, Event, Assumption

# Create via factory
ds = DecisionSurface.from_surface("notebook")  # or "cli", "vantage"

# Ingest data
ds.ingest(
    claims=[Claim(claim_id="C1", statement="System is healthy")],
    events=[Event(event_id="E1", event_type="confirmed", claim_refs=["C1"])],
)

# Evaluate
result = ds.evaluate(assumptions=[
    Assumption(assumption_id="A1", statement="No downtime",
               expires_at="2099-12-31T23:59:59Z", linked_claim_ids=["C1"]),
])
# result.satisfied == 1

# Seal
artifact = ds.seal()
# artifact.seal_hash == "sha256:..."
```

## Core Reuse

- `core.severity.compute_severity_score` — severity classification
- `core.authority.seal_and_hash.seal` — cryptographic sealing of DecisionArtifacts
- `core.memory_graph.NodeKind` / `EdgeKind` — node/edge type values (used as strings)

## Tests

- `tests/test_decision_surface_runtime.py` — 27 tests (engine + runtime + evaluation)
- `tests/test_notebook_adapter.py` — 16 tests (notebook + CLI adapters)
- `tests/test_vantage_adapter_contract.py` — 11 tests (contract + properties)

## Related Pages

- [ParadoxOps](ParadoxOps) — paradox tension detection domain
- [IntelOps](IntelOps) — claim lifecycle domain
- [Event Contracts](Event-Contracts) — routing table and event declarations
