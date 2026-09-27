# Deep Sigma Contrast

**Learn the difference that changes the outcome.**

`deepsigma-contrast` is a deterministic-first Python library for comparing decision episodes and converting
their differences into governed Deep Sigma learning signals.

It is intentionally **not** an autonomous authority engine.

The library can identify:
- comparable episodes,
- material differences,
- assumption deltas,
- outcome deltas,
- evidence deltas,
- discriminating factors,
- contrast confidence,
- CERPA review/patch handoffs.

Authority remains outside the learning engine.

## Deep Sigma flow

```text
PATHFINDER
    ↓ retrieve comparable episodes
CONTRAST ENGINE
    ↓ identify meaningful differences
RESONATOR
    ↓ explain semantic significance / gaps / contradictions
CERPA
    ↓ Claim → Event → Review → Patch → Apply
COMPOSER
    ↓ govern accepted change
AUTHORITATIVE KNOWLEDGE
```

The central question is:

> What prior episode looks most like this one — and what is materially different?

After the outcome:

> Which of those differences actually mattered?

## Installation

```bash
pip install .
```

No third-party dependency is required by the core library.

## Quick start

```python
from deepsigma_contrast import (
    ContrastEngine,
    Episode,
    Assumption,
    Outcome,
    EvidenceRef,
)

prior = Episode(
    id="EP-001",
    title="Baseline",
    claim="Sensor coverage is sufficient.",
    assumptions=[
        Assumption(id="A1", statement="Sensor A is continuously available", confidence=0.90)
    ],
    outcome=Outcome(status="SUCCESS", summary="Coverage remained stable."),
    evidence=[EvidenceRef(id="EV-1", uri="memory://ev-1")],
    tags={"C-UAS", "Fort"}
)

current = Episode(
    id="EP-002",
    title="Current",
    claim="Sensor coverage is sufficient.",
    assumptions=[
        Assumption(id="A1", statement="Sensor A is continuously available", confidence=0.45)
    ],
    outcome=Outcome(status="DEGRADED", summary="Coverage gap emerged."),
    evidence=[EvidenceRef(id="EV-2", uri="memory://ev-2")],
    tags={"C-UAS", "Fort"}
)

result = ContrastEngine().compare(current_episode=current, prior_episode=prior)

print(result.similarity)
print(result.material_differences)
print(result.discriminating_factors)
```

## Design rules

1. **Deterministic core first.**
2. **Embeddings are optional adapters, never required.**
3. **Evidence and provenance are explicit.**
4. **A contrast is advisory, not authoritative.**
5. **CERPA handoffs default to `PENDING_AUTHORITY`.**
6. **No APPLY operation occurs inside this package.**
7. **Machine output is inspectable and serializable.**
8. **DKO/DSAL hooks preserve Deep Sigma interoperability.**

## CLI

Compare two episode JSON files:

```bash
deepsigma-contrast compare examples/prior_episode.json examples/current_episode.json
```

Run the included demonstration:

```bash
deepsigma-contrast demo
```

## Package map

```text
deepsigma_contrast/
├── models.py          # Episode, assumption, outcome, evidence, contrast records
├── compare.py         # deterministic ContrastEngine
├── scorer.py          # lexical / structural / completeness scoring
├── pairs.py           # positive, negative and hard-negative pair generation
├── memory.py          # in-memory + JSONL episode stores
├── cerpa.py           # governed handoff (no autonomous APPLY)
├── dsal.py            # DKO / DSAL-compatible projections
├── embeddings.py      # optional embedding adapter protocol
├── cli.py
└── adapters/
    ├── pathfinder.py  # comparable-episode retrieval
    └── resonator.py   # semantic findings / gaps / contradictions
```

## Status

**v0.1.0** establishes the learning primitive. It is deliberately small enough to test, inspect, and later
embed inside Nano Sigma, VINCULUM, PATHFINDER, RESONATOR, COMPOSER, or other Deep Sigma runtimes.
