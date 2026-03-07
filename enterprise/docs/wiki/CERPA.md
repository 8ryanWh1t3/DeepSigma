# CERPA -- The Foundational Adaptation Loop

**Claim -> Event -> Review -> Patch -> Apply**

CERPA is the minimal governance primitive for DeepSigma. Every supervision flow -- across all five operational domains -- follows this cycle.

## The Loop

```
  +-------+     +---------+     +--------+
  | Claim |---->|  Event  |---->| Review |
  +-------+     +---------+     +--------+
                                   |
                        +----------+----------+
                        |                     |
                    [aligned]            [mismatch]
                        |                     |
                   Continue              +-------+     +-------+
                   Monitoring            | Patch |---->| Apply |
                                         +-------+     +-------+
                                                           |
                                                    (feeds back to
                                                     next Claim)
```

## Primitives

### Claim

An asserted truth or commitment to be monitored.

- **id** -- unique identifier
- **text** -- the assertion in natural language
- **domain** -- operational domain (intelops, reops, franops, authorityops, actionops)
- **source** -- where the claim originates
- **assumptions** -- conditions the claim depends on

### Event

An observable occurrence that may affect a Claim.

- **id** -- unique identifier
- **text** -- description of what was observed
- **observed_state** -- structured state data

### Review

Evaluation of a Claim against an Event. Produces a verdict.

- **verdict** -- aligned, mismatch, violation, or expired
- **drift_detected** -- boolean flag
- **severity** -- green, yellow, or red (when drift detected)

### Patch

Corrective action generated when a Review detects drift.

- **action** -- adjust, escalate, redefine, strengthen, or expire
- **target** -- the claim or system being corrected

### ApplyResult

Outcome of executing a Patch.

- **success** -- whether the patch was applied
- **new_state** -- the resulting system state
- **updated_claims** -- claims affected by the patch

## CERPA Across Domains

Every operational domain runs the same CERPA cycle with domain-specific claims, events, and review logic.

| Domain | Example Claim | Example Event |
|--------|--------------|---------------|
| IntelOps | Latency p99 under 200ms | Latency spike to 280ms |
| ReOps | Service uptime >= 99.9% | Uptime dropped to 99.5% |
| FranOps | Canon entry is blessed | Canon entry contradicted |
| AuthorityOps | Agent must not emit restricted content | Agent emitted restricted content |
| ActionOps | Contractor delivers artifact by deadline | Artifact not delivered |

## Mapping to Existing Architecture

CERPA does not replace existing structures. It names the cycle they already implement.

| CERPA Step | Existing Structure | Module |
|------------|-------------------|--------|
| Claim | `AtomicClaim` (canonical) | `core/primitives.py` |
| Claim | `Claim` (surface) | `core/decision_surface/models.py` |
| Event | `Event` (surface) | `core/decision_surface/models.py` |
| Review | `evaluate()` | `core/decision_surface/claim_event_engine.py` |
| Review | `DriftSignalCollector.ingest()` | `core/drift_signal.py` |
| Patch | `Patch` (canonical) | `core/primitives.py` |
| Patch | `PatchRecommendation` | `core/decision_surface/models.py` |
| Apply | `build_memory_graph_update()` | `core/decision_surface/claim_event_engine.py` |
| Apply | `MemoryGraph.add_patch()` | `core/memory_graph.py` |

## Demos

```bash
python -m src.core.examples.cerpa_contract_demo
python -m src.core.examples.cerpa_agent_supervision_demo
```

## Source Code

| File | Purpose |
|------|---------|
| `src/core/cerpa/__init__.py` | Package init and re-exports |
| `src/core/cerpa/types.py` | Enums: CerpaDomain, CerpaStatus, ReviewVerdict, PatchAction |
| `src/core/cerpa/models.py` | Dataclasses: Claim, Event, Review, Patch, ApplyResult, CerpaCycle |
| `src/core/cerpa/engine.py` | Orchestrator: `run_cerpa_cycle()` and step functions |
| `src/core/cerpa/mappers.py` | Adapters to AtomicClaim, DriftSignal, DLR, etc. |

## Related Pages

- [Drift to Patch](Drift-to-Patch) -- how drift signals become structured Patch Packets
- [Coherence Ops Mapping](Coherence-Ops-Mapping) -- DLR / RS / DS / MG governance artifacts
- [Unified Atomic Claims](Unified-Atomic-Claims) -- the unit of institutional memory
- [Architecture](Architecture) -- system diagram and component map
