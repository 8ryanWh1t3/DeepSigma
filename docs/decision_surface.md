# DecisionSurface — Portable Coherence Ops Runtime

## Architecture

```
Core Engine (scoring, seal_and_hash, memory_graph, severity)
        |
  DecisionSurface Runtime  (orchestration: ingest / evaluate / seal)
        |
  SurfaceAdapter ABC  (8 abstract methods)
        |
   +-----------+-----------+
   |           |           |
Notebook    CLI       Vantage/Foundry
(in-memory) (in-memory  (stub —
             + JSON)    NotImplementedError)
```

The DecisionSurface is NOT a DomainMode. It has no function IDs, no routing table entries, and no coverage matrix entries. It is a portable runtime layer that sits above domain modes and provides a generic claim/event evaluation pipeline.

## Quick Start

```python
from core.decision_surface import DecisionSurface, Claim, Event

ds = DecisionSurface.from_surface("notebook")

ds.ingest(
    claims=[Claim(claim_id="C1", statement="System is healthy")],
    events=[Event(event_id="E1", event_type="confirmed", claim_refs=["C1"])],
)

result = ds.evaluate()
# result.satisfied == 1, result.pending == 0

artifact = ds.seal()
# artifact.seal_hash == "sha256:..."
```

## Adapters

### NotebookAdapter (MVP reference)
In-memory storage. Use in Jupyter notebooks, tests, and interactive sessions.

### CLIAdapter
In-memory storage with `to_json()` for structured CLI output.

### VantageAdapter (stub)
All 8 methods raise `NotImplementedError`. Requires Foundry SDK integration.

### Writing a Custom Adapter

Subclass `SurfaceAdapter` and implement all 8 abstract methods:

```python
from core.decision_surface import SurfaceAdapter

class MyAdapter(SurfaceAdapter):
    surface_name = "my_surface"

    def ingest_claims(self, claims): ...
    def ingest_events(self, events): ...
    def get_claims(self): ...
    def get_events(self): ...
    def get_evidence(self): ...
    def store_drift_signals(self, signals): ...
    def store_patches(self, patches): ...
    def store_evaluation_result(self, result): ...
```

Then use it:
```python
ds = DecisionSurface(MyAdapter())
```

## Evaluation Engine

All evaluation logic lives in `claim_event_engine.py`. Adapters never contain evaluation logic.

| Function | Purpose |
|----------|---------|
| `match_events_to_claims` | Match events to claims via `claim_refs` |
| `detect_contradictions` | Find contradictory event pairs (approved/denied, etc.) |
| `detect_expired_assumptions` | Flag claims linked to expired assumptions |
| `compute_blast_radius` | Count claims sharing evidence with a given claim |
| `build_patch_recommendation` | Map drift type to corrective action |
| `build_memory_graph_update` | Build MG nodes/edges from evaluation |
| `evaluate` | Orchestrate all above into an `EvaluationResult` |

## Claim Statuses

| Status | Meaning |
|--------|---------|
| `satisfied` | 1+ matching events found |
| `at_risk` | Matched but claim confidence < 0.5 |
| `drifted` | Contradiction detected or assumption expired |
| `pending` | No matching events yet |

## Core Reuse

- `core.severity.compute_severity_score` — severity classification
- `core.authority.seal_and_hash.seal` — cryptographic sealing of DecisionArtifacts
- `core.memory_graph.NodeKind` / `EdgeKind` — node/edge type values (used as strings)
