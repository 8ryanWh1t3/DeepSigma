# Coherence Ops

Governance framework for agentic AI — implements the four canonical
artifacts (**DLR / RS / DS / MG**) and the coherence audit loop that
connects RAL / Σ OVERWATCH runtime exhaust to structured governance,
learning, and memory.

## Architecture

```
Sealed Episodes + Drift Events (from RAL)
            │
            ▼
┌───────────────────────────────────────────┐
│          coherence_ops                     │
│                                            │
│  ┌─────────┐  ┌────────┐  ┌────────────┐  │
│  │  DLR    │  │   RS   │  │     DS     │  │
│  │ Builder │  │Session │  │ Collector  │  │
│  └────┬────┘  └───┬────┘  └─────┬──────┘  │
│       │           │             │          │
│       ▼           ▼             ▼          │
│  ┌─────────────────────────────────────┐   │
│  │         Memory Graph (MG)           │   │
│  │  episodes · actions · drift · patches│   │
│  └─────────────────────────────────────┘   │
│       │           │             │          │
│       ▼           ▼             ▼          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Auditor  │  │  Scorer  │  │Reconciler│ │
│  └──────────┘  └──────────┘  └──────────┘ │
└───────────────────────────────────────────┘
```

## Modules

| Module | Class | Purpose |
|--------|-------|---------|
| `manifest.py` | `CoherenceManifest` | System-level declaration of artifact coverage |
| `dlr.py` | `DLRBuilder` | Build Decision Log Records from sealed episodes |
| `rs.py` | `ReflectionSession` | Aggregate episodes into learning summaries |
| `ds.py` | `DriftSignalCollector` | Collect and bucket drift signals by fingerprint |
| `mg.py` | `MemoryGraph` | Provenance graph for "why did we do this?" queries |
| `audit.py` | `CoherenceAuditor` | Cross-artifact consistency checks |
| `scoring.py` | `CoherenceScorer` | Unified 0–100 coherence score (A/B/C/D/F) |
| `reconciler.py` | `Reconciler` | Detect and propose repairs for inconsistencies |

## The Four Canonical Artifacts

| Artifact | Full Name | Question It Answers |
|----------|-----------|-------------------|
| **DLR** | Decision Log Record | What policy governed this decision, and was it followed? |
| **RS** | Reflection Session | What happened, what degraded, what should we learn? |
| **DS** | Drift Signal | What is breaking, how often, and how badly? |
| **MG** | Memory Graph | What happened before, why, and what changed as a result? |

## Quick Start

```python
from coherence_ops import (
    CoherenceManifest, DLRBuilder, ReflectionSession,
    DriftSignalCollector, MemoryGraph, CoherenceScorer,
)

# 1. Build DLR from sealed episodes
dlr = DLRBuilder()
dlr.from_episodes(sealed_episodes)

# 2. Run a reflection session
rs = ReflectionSession("rs-001")
rs.ingest(sealed_episodes)
summary = rs.summarise()

# 3. Collect drift signals
ds = DriftSignalCollector()
ds.ingest(drift_events)

# 4. Build the memory graph
mg = MemoryGraph()
for ep in sealed_episodes:
    mg.add_episode(ep)
for d in drift_events:
    mg.add_drift(d)

# 5. Score coherence
scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
report = scorer.score()
print(f"Coherence: {report.overall_score}/100 ({report.grade})")
```

## Schemas

- `schemas/coherence_manifest.schema.json` — manifest structure
- `schemas/coherence_report.schema.json` — audit report structure

## Integration with RAL

See `docs/10-coherence-ops-integration.md` for the full mapping between
RAL runtime artifacts and Coherence Ops canonical artifacts.
