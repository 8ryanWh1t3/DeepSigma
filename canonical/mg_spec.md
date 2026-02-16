---
title: "MG — Memory Graph Specification"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
spec_id: "MG-SPEC-001"
triad_mapping: "Memory"
---

# MG — Memory Graph

## Purpose

**What:** The Memory Graph is a provenance-linked knowledge graph connecting every sealed decision, action, drift signal, and patch into queryable institutional memory. It powers "why did we do this?" retrieval.

**So What:** Without the Memory Graph, institutional knowledge is trapped in individual episode records that cannot be traversed. MG is what turns a log into a brain.

## Node Types

| Node Type | Source | Key Fields |
|-----------|--------|------------|
| `Episode` | Sealed DecisionEpisode | `episodeId`, `decisionType`, `sealedAt`, `outcome.code` |
| `Action` | Episode action block | `idempotencyKey`, `targetRefs`, `blastRadiusTier` |
| `Claim` | AtomicClaim records | `claimId`, `statement`, `confidence`, `statusLight` |
| `DriftSignal` | DS records | `driftId`, `driftType`, `severity`, `fingerprint.key` |
| `Patch` | Corrective changes | `patchId`, `patchType`, `appliedAt`, `targetArtifact` |
| `DLR` | Decision Log Records | `dlrId`, `decisionType`, `outcome.code` |
| `RS` | Reflection Sessions | `sessionId`, `learnings`, `recommendedPatches` |

## Edge Types

| Edge | From > To | Meaning |
|------|-----------|---------|
| `PRODUCED` | Episode > DLR | This episode produced this DLR |
| `TRIGGERED` | Episode > DriftSignal | This episode triggered this drift |
| `PATCHED_BY` | DriftSignal > Patch | This drift was addressed by this patch |
| `INFORMED` | Patch > Episode | This patch informed a subsequent decision |
| `GROUNDED_IN` | Episode > Claim | This decision was grounded in this claim |
| `SUPPORTS` | Claim > Claim | This claim supports another |
| `CONTRADICTS` | Claim > Claim | This claim contradicts another |
| `SUPERSEDES` | Claim > Claim | This claim replaces a previous version |
| `LEARNED_FROM` | RS > Episode | This reflection session analyzed these episodes |
| `RECOMMENDS` | RS > Patch | This reflection session recommended this patch |

## Query Interface (IRIS)

| Query Type | Question | Returns |
|------------|----------|---------|
| `WHY` | Why did we make this decision? | Provenance chain: Episode > Claims > Evidence > Policy |
| `WHAT_CHANGED` | What changed between two points? | Patches, new claims, superseded claims |
| `WHAT_DRIFTED` | What is currently drifting? | Active DS records grouped by fingerprint |
| `RECALL` | What do we know about this entity? | All related episodes, claims, drift, patches |
| `STATUS` | Current system coherence? | Coherence score + active drift summary |

## Validation Rules

1. Every node must have a unique identifier within its type.
2. 2. Every edge must reference valid source and target node IDs.
   3. 3. `Episode` nodes must have `sealedAt` — unsealed episodes are not added.
      4. 4. `Patch` nodes must reference the triggering DriftSignal or RS.
         5. 5. The graph must be acyclic for `SUPERSEDES` edges.
           
            6. ## Minimal JSON Example (Graph Export)
           
            7. ```json
               {
                 "exportedAt": "2026-02-16T11:05:00Z",
                 "nodes": [
                   { "type": "Episode", "id": "ep-001", "decisionType": "AccountQuarantine", "sealedAt": "2026-02-16T10:31:00Z", "outcome": "success" },
                   { "type": "Claim", "id": "CLAIM-2026-0001", "statement": "Account A-1042 credit score < 580", "confidence": 0.92 },
                   { "type": "DriftSignal", "id": "drift-007", "driftType": "freshness", "severity": "red" },
                   { "type": "Patch", "id": "patch-001", "patchType": "ttl_change", "appliedAt": "2026-02-16T11:00:00Z" },
                   { "type": "DLR", "id": "DLR-a1b2c3d4e5f6", "decisionType": "AccountQuarantine", "outcome": "success" }
                 ],
                 "edges": [
                   { "from": "ep-001", "to": "DLR-a1b2c3d4e5f6", "rel": "PRODUCED" },
                   { "from": "ep-001", "to": "CLAIM-2026-0001", "rel": "GROUNDED_IN" },
                   { "from": "ep-002", "to": "drift-007", "rel": "TRIGGERED" },
                   { "from": "drift-007", "to": "patch-001", "rel": "PATCHED_BY" }
                 ]
               }
               ```
