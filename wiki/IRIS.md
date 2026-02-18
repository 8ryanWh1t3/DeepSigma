# IRIS

**Interface for Resolution, Insight, and Status** — the operator-facing query layer for [Coherence Ops](Coherence-Ops-Mapping).

IRIS sits on top of [PRIME](Glossary) and queries against the four canonical artifacts ([DLR](Glossary) / [RS](Glossary) / [DS](Glossary) / [MG](Glossary)) to answer operator questions with full provenance chains and sub-60-second resolution targets.

---

## Position in the Stack

```text
Operator  →  IRIS (read path / query resolution)
                 ↓
             PRIME (write path / governance gate)
                 ↓
             DLR  │  RS  │  DS  │  MG
```

IRIS is read-only — it never mutates artifact state. PRIME governs the write path (sealing episodes, stamping policies). IRIS reconstructs what PRIME produced.

See [Glossary](Glossary) for definitions: PRIME = "LLM proposes. PRIME disposes." IRIS = "the terminal through which operators interact with PRIME."

---

## Query Types

| Type | Question | Primary Artifact | Requires `episode_id` |
|------|----------|-----------------|----------------------|
| **WHY** | "Why did we decide X?" | MG + DLR | Yes |
| **WHAT_CHANGED** | "What changed?" | DLR + MG + DS | No |
| **WHAT_DRIFTED** | "What's drifting?" | DS + MG | No |
| **RECALL** | "What do we know about X?" | MG + DLR | Yes |
| **STATUS** | "How healthy are we?" | All four (via CoherenceScorer) | No |

### WHY

Queries MG for the episode's provenance node (evidence refs, actions, linked drift), then enriches with DLR policy context (decision type, outcome, policy stamp, degrade step). RS provides broader context when available.

### WHAT_CHANGED

Analyses DLR entries: outcome distribution, degraded episodes, missing policy stamps. MG enriches with patch counts. DS enriches with drift signal totals and severity breakdown.

### WHAT_DRIFTED

Pulls DS summary: total signals, severity breakdown (red/yellow/green), top fingerprint buckets, recurring patterns. MG cross-references drift nodes vs. patch nodes to compute a resolution ratio.

### RECALL

Full MG graph traversal for an episode: provenance node, evidence refs, actions, drift events, patches. DLR enriches with decision type and outcome. Deepest single-episode query.

### STATUS

Runs CoherenceScorer across all four artifacts. Returns overall score (0–100), letter grade, and per-dimension breakdown: Policy Adherence (DLR, 30%), Outcome Health (RS, 25%), Drift Control (DS, 25%), Memory Completeness (MG, 20%). Includes MG stats and drift headline.

---

## Response Format

Every response includes:

- **query_id** — deterministic hash: `iris-{sha256[:12]}`
- **query_type** — WHY | WHAT_CHANGED | WHAT_DRIFTED | RECALL | STATUS
- **status** — RESOLVED | PARTIAL | NOT_FOUND | ERROR
- **summary** — human-readable explanation
- **data** — query-type-specific structured data
- **provenance_chain** — ordered list of `ProvenanceLink` objects
- **confidence** — 0.0–1.0 (additive per artifact, capped at 1.0)
- **resolved_at** — ISO-8601 timestamp
- **elapsed_ms** — wall-clock time
- **warnings** — performance or data quality alerts

### Provenance Chain

Each link in the chain identifies:

- **artifact** — DLR, MG, DS, RS, or PRIME
- **ref_id** — specific record identifier
- **role** — `source` (primary), `evidence` (supporting), or `context` (enriching)
- **detail** — human-readable description

### Resolution Status

| Status | Condition |
|--------|-----------|
| RESOLVED | confidence >= 0.5 |
| PARTIAL | 0 < confidence < 0.5 |
| NOT_FOUND | required data missing |
| ERROR | exception during resolution |

---

## Interfaces

### Python

```python
from coherence_ops.iris import IRISEngine, IRISQuery, QueryType

engine = IRISEngine(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
response = engine.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
```

### CLI

```bash
coherence iris query --type WHY --target ep-001
coherence iris query --type STATUS
coherence iris query --type WHAT_DRIFTED --json
```

### Dashboard

View 4 (keyboard shortcut `4`) in the Σ OVERWATCH dashboard. Natural language input with query type selector, structured response with provenance chain visualization.

### JSON Schema

`specs/iris_query.schema.json` — JSON Schema draft 2020-12, `$id: https://deepsigma.dev/schemas/iris_query.schema.json`.

---

## Usage Patterns

| Pattern | Query Type | When |
|---------|-----------|------|
| Post-incident review | WHY | After an unexpected outcome — trace provenance + policy context |
| Drift triage | WHAT_DRIFTED | Routine monitoring — severity breakdown + resolution ratio |
| Health check | STATUS | Pre-deployment — coherence score + dimension breakdown |
| Institutional memory | RECALL | Onboarding / knowledge transfer — full graph context for an episode |
| Change audit | WHAT_CHANGED | Pre-policy-update — baseline outcome distribution + patch count |

---

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `response_time_target_ms` | 60,000 | Performance warning threshold |
| `max_provenance_depth` | 50 | Max provenance links per response |
| `default_time_window_seconds` | 3,600 | Time window for WHAT_CHANGED |
| `default_limit` | 20 | Result count limit |
| `include_raw_artifacts` | false | Include raw data in response |

---

## Design Principles

- **Read-only** — queries but never writes. Mutation flows through PRIME.
- **Provenance-first** — no answer without lineage. Every response traces back to artifact records.
- **Sub-60-second** — matches MG's institutional memory promise.
- **Structured output** — machine-parseable (JSON) and human-readable.
- **Graceful degradation** — returns PARTIAL/NOT_FOUND instead of failing when artifacts are unavailable.

---

## Files

| File | Description |
|------|-------------|
| `coherence_ops/iris.py` | Engine implementation |
| `specs/iris_query.schema.json` | JSON Schema contract |
| `coherence_ops/cli.py` | CLI `coherence iris query` |
| `dashboard/src/IrisPanel.tsx` | Dashboard panel component |
| `dashboard/src/mockData.ts` | Mock resolver for dev mode |

---

## Glossary Terms

See [Glossary](Glossary) and [GLOSSARY.md](../GLOSSARY.md):

- **IRIS** — operator-facing interface layer; query resolution with sub-60s targets
- **PRIME** — governance threshold gate; LLM output → decision-grade action
- **DLR** — Decision Lineage Record; truth constitution for a decision class
- **RS** — Reasoning Summary; outcome aggregation and learning
- **DS** — Drift Scan; structured drift signals by type/severity/fingerprint
- **MG** — Memory Graph; provenance + recall graph
- **Claim–Evidence–Source** — the truth chain enforced by PRIME, reconstructed by IRIS
- **Coherence Score** — 0–100 composite from all four artifacts
- **Seal** — immutable, tamper-evident record

See also: [Language Map](../docs/01-language-map.md) for LinkedIn-to-Code mappings (IRIS = Phase 2).

---

Full documentation: `docs/18-iris.md`
