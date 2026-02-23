---
title: "Credibility Engine at Scale — Architecture"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# Architecture — 30,000–40,000 Nodes

> Three regions. Independent failure domains. Federated time.

---

## Regional Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Credibility Engine                        │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐       │
│  │ Region East │  │Region Central│  │ Region West  │       │
│  │  12,000     │  │   14,000     │  │   10,000     │       │
│  │  Authority:  │  │  Authority:  │  │  Authority:  │       │
│  │    33%      │  │     39%      │  │     28%      │       │
│  │             │  │              │  │              │       │
│  │  Sync Plane │  │  Sync Plane  │  │  Sync Plane  │       │
│  │  5 nodes    │  │  5 nodes     │  │  4 nodes     │       │
│  │  2 beacons  │  │  2 beacons   │  │  2 beacons   │       │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘       │
│         │                │                  │              │
│         └────────────────┼──────────────────┘              │
│                          │                                  │
│              ┌───────────┴───────────┐                     │
│              │   Beacon Federation   │                     │
│              │  Cross-Region Sync    │                     │
│              └───────────────────────┘                     │
│                          │                                  │
│              ┌───────────┴───────────┐                     │
│              │   Credibility Index   │                     │
│              │    Composite Score    │                     │
│              │       0–100          │                     │
│              └───────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Region Profiles

### Region East (12,000 nodes)

| Attribute | Value |
|-----------|-------|
| Decision domains | 4 |
| Authority share | 33% |
| Sync nodes | 5 |
| Beacons | 2 (1 internal, 1 external) |
| Hot tier | 3,000 nodes (active claims + live evidence) |
| Warm tier | 6,000 nodes (referenced in last 30 days) |
| Cold tier | 3,000 nodes (sealed archive) |
| Primary risk | Source concentration in Domain E2 |

### Region Central (14,000 nodes)

| Attribute | Value |
|-----------|-------|
| Decision domains | 5 |
| Authority share | 39% |
| Sync nodes | 5 |
| Beacons | 2 (both external) |
| Hot tier | 4,000 nodes |
| Warm tier | 7,000 nodes |
| Cold tier | 3,000 nodes |
| Primary risk | TTL pressure on high-frequency evidence |

### Region West (10,000 nodes)

| Attribute | Value |
|-----------|-------|
| Decision domains | 3 |
| Authority share | 28% |
| Sync nodes | 4 |
| Beacons | 2 (1 internal, 1 external) |
| Hot tier | 2,500 nodes |
| Warm tier | 5,000 nodes |
| Cold tier | 2,500 nodes |
| Primary risk | Thinner quorum margins (fewer sources) |

---

## Evidence Temperature

| Temperature | Contents | Access Pattern | Retention |
|-------------|----------|---------------|-----------|
| Hot | Active claims, evidence <24h, live Sync Plane | Real-time, sub-second | Always loaded |
| Warm | Claims referenced in last 30 days, evidence within TTL | Near-line, seconds | Indexed, queryable |
| Cold | Sealed archive, read-only, hash-verified | Archive, minutes | Immutable, never deleted |

Evidence migrates from Hot → Warm → Cold as it ages past its utility window. Cold evidence is the institutional memory — it is never deleted.

---

## Infrastructure Stack

### Per Region

| Component | Purpose | Scale |
|-----------|---------|-------|
| Event stream | Evidence ingestion, drift signals | Kafka/NATS cluster, partitioned by domain |
| Graph store | Claim lattice persistence | Neo4j/TerminusDB cluster, region-sharded |
| Quorum service | K-of-N tracking per claim | Stateful service, domain-partitioned |
| Drift detection | Institutional drift categories | Stream processor, 5-category detection |
| Sync Plane | Time verification | 4–5 sync nodes, 2 beacons |
| Seal service | Hash chain, immutability | Append-only store with replication |

### Cross-Region

| Component | Purpose |
|-----------|---------|
| Beacon federation | Cross-region time consistency |
| Correlation tracker | Cross-region source dependency detection |
| Index aggregator | Regional sub-indices → composite Credibility Index |
| Drift coordinator | Cross-region drift event correlation |

---

## Failure Domain Isolation

Each region operates independently:

- **Independent infrastructure** — separate compute, storage, network
- **Independent Sync Plane** — no shared clock infrastructure
- **Independent quorum** — regional claims evaluated against regional sources
- **Independent drift detection** — regional patterns detected locally

Cross-region dependencies are explicit and tracked:

- Beacon federation is the only shared timing infrastructure
- Cross-region sources are flagged in the correlation group registry
- Cross-region drift events are coordinated but not required for local operation

**If a region fails entirely, the other two regions continue operating.** Cross-region claims that depended on the failed region's evidence degrade to UNKNOWN — honestly.

---

## Authority Distribution

| Constraint | Requirement |
|-----------|-------------|
| Maximum authority per region | 40% |
| Minimum regions | 3 |
| Out-of-domain authorities | 2 minimum |

No single region can control institutional truth. Central holds 39% — the maximum. If Central fails, East (33%) and West (28%) continue with 61% combined authority, sufficient for institutional quorum.

---

## Diagrams

- [Lattice Architecture](../../archive/mermaid/38-lattice-architecture.md) — Claim → SubClaim → Evidence → Source with Sync Plane and Credibility Index
- [Institutional Drift Loop](../../archive/mermaid/39-drift-loop.md) — Detection → Response → Repair cycle
