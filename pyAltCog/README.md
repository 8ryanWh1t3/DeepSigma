# pyAltCog

**pyAltCog** is the executable Python layer for **Deep Sigma AltCogOps**.

It operationalizes this discovery path:

```text
FRICTION → ANOMALY → WEAK SIGNAL → CLUSTER → HYPOTHESIS → TEST → ALTCOG → MONITOR → PROMOTE
```

The design rule is strict:

> **Alternative generation is not alternative discovery.**

A model can invent another explanation. pyAltCog promotes an alternative only when observable friction, evidence, a distinct prediction, falsification criteria, mission relevance, ownership, and a revisit trigger make it operationally testable.

## What the library implements

- AC0–AC8 Alternative Cognition maturity lifecycle
- seven AltCog discovery surfaces
- deterministic friction capture and exception clustering
- ALT-F13…ALT-F18 discovery functions
- ALT-E13…ALT-E18 discovery events
- FSR / RER / ECC / ACP / DEP / DAM canonical artifacts
- candidate scoring and AC6 promotion gates
- discriminating-evidence / falsification planning
- dormant-alternative preservation and reactivation
- SHA-256 stable IDs and append-only hash-chained audit events
- ADR / RCR / WPR / TAF / DAR metrics
- JSON serialization and CLI
- dependency-free integration projections for CERPA, DSAL/DKO, RESONATOR, PATHFINDER, IntelOps, ReOps, and FranOps
- no mandatory cloud service or LLM dependency

## Install

```bash
python -m pip install -e .
```

## 30-second example

```python
from pyaltcog import AltCogEngine, DiscoverySurface, Prediction

engine = AltCogEngine()

signal = engine.capture_friction(
    stream_id="C-UAS-BLUE-01",
    surface=DiscoverySurface.OUTCOME_MISMATCH,
    statement="Expected track continuity; repeated identity resets were observed.",
    source="exercise-log",
    tags=["track", "identity", "reset"],
)

cluster = engine.cluster([signal])[0]

candidate = engine.create_candidate(
    cluster=cluster,
    dominant_model="Identity resets are random sensor noise.",
    hypothesis="Identity resets correlate with a recurring handoff condition.",
    prediction=Prediction(
        variable="reset_rate_after_handoff",
        dominant_expected="no systematic increase",
        alternative_expected="measurable increase",
    ),
    owner="BLUE-TEAM",
    revisit_trigger="next handoff event",
    mission_relevance=0.9,
)

candidate = engine.score(candidate)
candidate = engine.promote_if_ready(candidate)

print(candidate.maturity.value)  # AC6
print(candidate.score.total)
```

## CLI

```bash
pyaltcog demo
pyaltcog cluster examples/signals.json
pyaltcog score examples/candidate.json
```

## Architecture

pyAltCog deliberately keeps the core independent from other Deep Sigma runtimes.
Adapters project a canonical AltCog candidate outward; they do not let external systems silently mutate AltCog state.

```text
Reality / Logs / Reviews
        ↓
Friction Signals (FSR)
        ↓
Deterministic clustering (ECC)
        ↓
Alternative Candidate (ACP)
        ↓
Score + Discriminating Evidence Plan (DEP)
        ↓
AC6 Operational Alternative
        ├── validate → AC7 Promoted Model
        └── reject   → AC8 Archived With Trigger
                          ↓
                    Dormant Monitor (DAM)
                          ↓
                    reality changes → reactivate
```

See `docs/ARCHITECTURE.md` and `docs/SPEC_MAPPING.md`.

## Non-goals

pyAltCog does **not**:

- decide which institutional model is authoritative;
- score people;
- replace human decision authority;
- require generative AI;
- treat novelty or disagreement as evidence;
- delete rejected alternatives.

## Development

```bash
PYTHONPATH=src pytest
python -m compileall -q src
```
