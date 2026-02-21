# Coherence Ops

Governance framework for agentic AI — implements the four canonical artifacts (**DLR / RS / DS / MG**) and the coherence audit loop that connects RAL / Σ OVERWATCH runtime exhaust to structured governance, learning, and memory.

## Architecture

```
Sealed Episodes + Drift Events (from RAL)
          │
          ▼
┌───────────────────────────────────────────┐
│              coherence_ops                │
│                                           │
│  ┌─────────┐  ┌────────┐  ┌────────────┐ │
│  │   DLR   │  │   RS   │  │     DS     │ │
│  │ Builder │  │Session │  │ Collector  │ │
│  └────┬────┘  └───┬────┘  └─────┬──────┘ │
│       │           │             │         │
│       ▼           ▼             ▼         │
│  ┌─────────────────────────────────────┐  │
│  │         Memory Graph (MG)          │  │
│  │ episodes · actions · drift · patches│  │
│  └─────────────────────────────────────┘  │
│       │           │             │         │
│       ▼           ▼             ▼         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Auditor  │ │ Scorer   │ │Reconciler│  │
│  └──────────┘ └──────────┘ └──────────┘  │
│                    │                      │
│                    ▼                      │
│  ┌─────────────────────────────────────┐  │
│  │        IRIS (Query Resolution)      │  │
│  │  WHY · WHAT_CHANGED · WHAT_DRIFTED  │  │
│  │  RECALL · STATUS                    │  │
│  │  Provenance chains · sub-60s target │  │
│  └─────────────────────────────────────┘  │
└───────────────────────────────────────────┘
```

## Modules

| Module | Class | Purpose |
|---|---|---|
| `manifest.py` | `CoherenceManifest` | System-level declaration of artifact coverage |
| `dlr.py` | `DLRBuilder` | Build Decision Log Records from sealed episodes |
| `rs.py` | `ReflectionSession` | Aggregate episodes into learning summaries |
| `ds.py` | `DriftSignalCollector` | Collect and bucket drift signals by fingerprint |
| `mg.py` | `MemoryGraph` | Provenance graph for "why did we do this?" queries |
| `audit.py` | `CoherenceAuditor` | Cross-artifact consistency checks |
| `scoring.py` | `CoherenceScorer` | Unified 0–100 coherence score (A/B/C/D/F) |
| `reconciler.py` | `Reconciler` | Detect and propose repairs for inconsistencies |
| `iris.py` | `IRISEngine` | Operator query resolution engine — WHY / WHAT_CHANGED / WHAT_DRIFTED / RECALL / STATUS |
| `cli.py` | — | CLI entrypoint: `audit`, `score`, `mg export`, `iris query`, `demo` |

## The Four Canonical Artifacts

| Artifact | Full Name | Question It Answers |
|---|---|---|
| **DLR** | Decision Log Record | What policy governed this decision, and was it followed? |
| **RS** | Reflection Session | What happened, what degraded, what should we learn? |
| **DS** | Drift Signal | What is breaking, how often, and how badly? |
| **MG** | Memory Graph | What happened before, why, and what changed as a result? |

## CLI

```bash
# Run from the repo root

# Coherence audit
python -m coherence_ops audit ./coherence_ops/examples/sample_episodes.json

# Coherence score
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json

# Memory Graph export
python -m coherence_ops mg export ./coherence_ops/examples/ --format=json
python -m coherence_ops mg export ./coherence_ops/examples/ --format=graphml
python -m coherence_ops mg export ./coherence_ops/examples/ --format=neo4j-csv

# IRIS query — operator question resolution
python -m coherence_ops iris query --type WHY --target ep-001
python -m coherence_ops iris query --type STATUS
python -m coherence_ops iris query --type WHAT_DRIFTED --json
python -m coherence_ops iris query --type RECALL --target ep-042 --limit 10
python -m coherence_ops iris query --type WHAT_CHANGED

# Ship-it demo (the Stark/Jobs moment)
python -m coherence_ops demo
```

The `demo` command prints:
1. **Coherence score** with per-dimension breakdown
2. 2. **Top 3 drift fingerprints** with severity and recommended patches
   3. 3. **"Why did we do this?"** query result from the Memory Graph
     
      4. Every output includes **seal / version / patch** metadata (stub hash today, real hash when sealed).
     
      5. ## Quick Start
     
      6. ```python
         from coherence_ops import (
             CoherenceManifest,
             DLRBuilder,
             ReflectionSession,
             DriftSignalCollector,
             MemoryGraph,
             CoherenceScorer,
             IRISEngine,
             IRISQuery,
             QueryType,
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

         # 6. Query with IRIS
         engine = IRISEngine(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
         response = engine.resolve(IRISQuery(
             query_type=QueryType.WHY,
             episode_id="ep-001",
         ))
         print(response.summary)
         for link in response.provenance_chain:
             print(f"  [{link.artifact}] {link.ref_id} ({link.role})")
         ```

         ## Examples

         End-to-end examples live in `examples/`:

         | File | Description |
         |---|---|
         | `sample_episodes.json` | 3 sealed DecisionEpisodes (deploy, scale, rollback) |
         | `sample_drift.json` | 5 drift events (green/yellow/red) |
         | `e2e_seal_to_report.py` | Full pipeline: sealed episode → CoherenceReport JSON |

         Run the end-to-end examples:

         ```bash
         python -m coherence_ops.examples.e2e_seal_to_report
         ```

         ## Schemas

         - `schemas/coherence_manifest.schema.json` — manifest structure
         - - `schemas/coherence_report.schema.json` — audit report structure
           - - `../schemas/core/iris_query.schema.json` — IRIS query/response contract
            
             - ## Related Resources
            
             - > **IRIS Documentation** — Full interface contract, query types, provenance chains:
               > > [`docs/18-iris.md`](../docs/18-iris.md) | [`wiki/IRIS.md`](../wiki/IRIS.md)
               > >
               > > > **Mermaid Diagrams** — Visual architecture of the coherence pipeline:
               > > > > [`mermaid/coherence_ops_pipeline.mmd`](../mermaid/coherence_ops_pipeline.mmd) |
               > > > > > [`mermaid/coherence_ops_data_flow.mmd`](../mermaid/coherence_ops_data_flow.mmd) |
               > > > > > > [`mermaid/coherence_ops_scoring.mmd`](../mermaid/coherence_ops_scoring.mmd)
               > > > > > >
               > > > > > > > **Wiki** — Full mapping between RAL runtime artifacts and Coherence Ops:
               > > > > > > > > [Coherence Ops Integration](https://github.com/8ryanWh1t3/DeepSigma/wiki/Coherence-Ops-Integration) |
               > > > > > > > > > [Coherence Ops Architecture](https://github.com/8ryanWh1t3/DeepSigma/wiki/Coherence-Ops-Architecture) |
               > > > > > > > > > > [DLR / RS / DS / MG Deep Dive](https://github.com/8ryanWh1t3/DeepSigma/wiki/DLR-RS-DS-MG-Artifacts)
               > > > > > > > > > >
               > > > > > > > > > > > **Integration Guide** — `docs/10-coherence-ops-integration.md`
