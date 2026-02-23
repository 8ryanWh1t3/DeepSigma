---
title: "Artifact Relationships — How DLR/RS/DS/MG Connect"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# Artifact Relationships

## The Flow

```
DecisionEpisode (sealed)
    |
    |-- extracts --> DLR (truth receipt)
    |                 contains claim snapshots + policy ref + outcome
    |
    |-- feeds -----> RS (reflection session, batched)
    |                 aggregates episodes into learnings + recommended patches
    |
    |-- emits -----> DS (drift signal, if anomaly detected)
    |                 typed, fingerprinted, severity-graded
    |                 triggers Patch workflow
    |
    +-- stored in -> MG (memory graph)
                      provenance edges linking all of the above
```

## Relationship Matrix

| From | To | Relationship | Cardinality |
|------|----|-------------|-------------|
| Episode | DLR | 1 episode produces 1 DLR | 1:1 |
| Episode | DS | 1 episode may emit 0..N drift signals | 1:N |
| Episode | MG | Every sealed episode becomes a node in MG | 1:1 |
| DS | Patch | 1 drift signal may trigger 0..1 patches | 1:0..1 |
| Patch | MG | Every applied patch becomes a node in MG | 1:1 |
| RS | Episode | 1 RS analyzes 1..N episodes | 1:N |
| RS | Patch | 1 RS may recommend 0..N patches | 1:N |
| MG | IRIS | IRIS queries MG to resolve operator questions | query interface |
| Claim | DLR | Claims are snapshotted inside DLR records | N:1 |
| Claim | Claim | Claims link via supports/contradicts/supersedes | N:N |

## Lifecycle

1. **Episode created** — claims gathered, reasoning applied, action taken, verified, sealed
2. 2. **DLR extracted** — truth receipt frozen
   3. 3. **DS emitted** (if drift) — fingerprinted, severity assigned
      4. 4. **MG updated** — episode + DLR + DS nodes and edges added
         5. 5. **RS generated** (periodic/batch) — learning extracted, patches recommended
            6. 6. **Patch applied** (if triggered) — policy updated, MG records provenance
               7. 7. **Next episode** — benefits from updated policy and enriched memory
