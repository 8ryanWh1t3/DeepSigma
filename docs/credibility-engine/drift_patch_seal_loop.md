---
title: "Drift-Patch-Seal Loop — Institutional Scale"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-19"
---

# Drift → Patch → Seal

> Drift is maintenance fuel.

At runtime, individual episodes produce drift signals of 8 types: time, freshness, fallback, bypass, verify, outcome, fanout, contention. These are the existing [drift event types](../../specs/drift.schema.json) that power the Coherence Ops Drift→Patch loop.

At institutional scale, these runtime signals combine into **5 higher-level categories** that represent structural patterns across the claim lattice. These institutional drift categories are the escalation and response framework for the Credibility Engine.

---

## Institutional Drift Categories

### 1. Timing Entropy

Evidence arrival times become unpredictable. Ingestion lag variance exceeds tolerance.

| Aspect | Detail |
|--------|--------|
| Root cause | Infrastructure degradation, network partition, source overload |
| Detection | Variance in `ingest_time - event_time` across evidence streams |
| Primary runtime types | time, contention |
| Secondary | fanout |

### 2. Correlation Drift

Claims that should be independent begin drifting simultaneously because they share a source dependency.

| Aspect | Detail |
|--------|--------|
| Root cause | Source failure, source compromise, shared infrastructure dependency |
| Detection | Multiple claims drift at the same time from the same correlation group |
| Primary runtime types | freshness, outcome |
| Secondary | fallback |

### 3. Confidence Volatility

Claim confidence scores fluctuate beyond expected bands without a clear external cause.

| Aspect | Detail |
|--------|--------|
| Root cause | Source quality degradation, model drift, changing environmental conditions |
| Detection | Standard deviation of confidence scores across a domain exceeds threshold |
| Primary runtime types | verify, outcome |
| Secondary | freshness |

### 4. TTL Compression

Evidence TTLs are being shortened by operational pressure faster than sources can refresh.

| Aspect | Detail |
|--------|--------|
| Root cause | Operational tightening of TTLs without increasing source refresh rates |
| Detection | Ratio of TTL to refresh interval drops below 2:1 |
| Primary runtime types | freshness |
| Secondary | time |

### 5. External Mismatch

Internal evidence contradicts external beacons or reference data from the Sync Plane.

| Aspect | Detail |
|--------|--------|
| Root cause | Internal data corruption, clock skew, external reference change |
| Detection | Sync Plane beacon divergence exceeds tolerance |
| Primary runtime types | bypass, verify |
| Secondary | outcome |

---

## Mapping: Institutional Categories → Runtime Types

| Institutional Category | Primary Runtime Types | Secondary |
|-----------------------|----------------------|-----------|
| Timing Entropy | time, contention | fanout |
| Correlation Drift | freshness, outcome | fallback |
| Confidence Volatility | verify, outcome | freshness |
| TTL Compression | freshness | time |
| External Mismatch | bypass, verify | outcome |

The 8 runtime types remain the detection mechanism. The 5 institutional categories provide the escalation and response framework.

---

## The Loop

For each detected institutional drift:

```
1. Generate DS artifact
   └─ Structured Drift Signal with category, severity, evidence refs

2. Root cause analysis
   └─ Determine which sources, correlation groups, or sync nodes are involved

3. Create Patch object
   └─ Proposed correction with rollback plan and blast radius assessment

4. Update Memory Graph
   └─ New DriftSignal and Patch nodes, TRIGGERED and RESOLVED_BY edges

5. Seal affected claims
   └─ New version, extended hash chain, updated patch_log

6. Recalculate Credibility Index
   └─ Score reflects post-patch state
```

Each step produces an immutable artifact. The entire sequence is a DecisionEpisode that gets sealed.

---

## Automation Requirements by Scale

| Scale | Automation Level |
|-------|-----------------|
| Mini (12 nodes) | Manual review acceptable. Loop runs on-demand. |
| Enterprise (~500 nodes) | Semi-automated. Drift detection runs on 15-minute cycle. Patches require human approval above severity threshold. |
| Production (30,000+ nodes) | Fully automated for green/yellow drift. Red drift and Tier 0 flips escalate to human DRI. Loop runs continuously. |

At production scale, manual-only drift management is itself a risk. The volume of drift signals (100–400/day at steady state) requires automated triage.

---

## Relationship to Existing Drift→Patch

This loop extends the existing lifecycle documented in:

- [Drift to Patch diagram](../mermaid/05-drift-to-patch.md) — runtime-level flowchart
- [Drift event schema](../../specs/drift.schema.json) — 8 runtime drift types
- [Drift-Patch Model](../../ontology/drift_patch_model.md) — conceptual framework

The existing runtime types remain unchanged. The institutional categories are a higher-order abstraction that composes from them.
