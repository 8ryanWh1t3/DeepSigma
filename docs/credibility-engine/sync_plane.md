---
title: "Sync Plane — Evidence Synchronization Infrastructure"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-19"
---

# Sync Plane

> Sync nodes are evidence about evidence.

At institutional scale, the assumption that timestamps are trustworthy is itself a claim that must be verified. The Sync Plane is the infrastructure that provides this verification.

---

## Why a Sync Plane

At scale:

- Events arrive late
- Events arrive out of order
- Clocks drift
- Replays occur

Without a Sync Plane, evidence ordering is assertion-based rather than verification-based. The institution trusts that Source A's timestamp is accurate because Source A says so. That is not credibility — that is faith.

---

## Core Concepts

### Event Time vs. Ingest Time

Every evidence node carries two timestamps:

| Timestamp | What It Represents |
|-----------|-------------------|
| `event_time` | When the observation occurred at the source |
| `ingest_time` | When the lattice received and recorded it |

The delta between them is **ingestion lag**. Small, consistent deltas are normal. Large or variable deltas are suspicious and may indicate infrastructure degradation, network partition, or intentional manipulation.

### Monotonic Source Sequence Enforcement

Each source must produce evidence with monotonically increasing sequence numbers. If evidence arrives with a sequence number less than or equal to the last recorded sequence from that source:

1. A sync drift signal fires
2. The evidence is quarantined (not rejected — held for investigation)
3. The source's reliability tier may be temporarily downgraded

This prevents replay attacks and stale injection.

### Independent Time Beacons

External, independent time references that the Sync Plane checks against. Beacons are themselves Sources in the lattice — they have a tier, a provenance chain, and a TTL.

If internal timestamps diverge from beacons beyond tolerance, a sync drift signal fires. The beacon's evidence outranks the source's self-reported timestamp.

### Watermark Logic

Each Sync Plane maintains a **high-water mark**: the latest confirmed `event_time` for which all prior events are accounted for.

| Condition | Meaning |
|-----------|---------|
| Evidence arrives with `event_time` below watermark | Late arrival — investigate |
| Evidence arrives with `event_time` far above watermark | Clock skew — investigate |
| Watermark advances smoothly | Healthy sync |
| Watermark stalls | Source silence — trigger `SignalLoss` |

### Replay and Backfill Detection

When evidence arrives below the watermark, the Sync Plane must distinguish between:

| Scenario | Detection Method |
|----------|-----------------|
| Legitimate late arrival | Small delta, unique sequence, source authenticated |
| Replay attack | Duplicate sequence number, hash matches existing sealed evidence |
| Backfill | Flagged by source as historical load, bulk sequence range |

Detection heuristics: sequence number overlap, hash comparison against sealed evidence, source authentication token validation.

---

## Sync Plane Minimum (Production)

| Requirement | Minimum |
|-------------|---------|
| Regions | 3 |
| Sync nodes per region | 3–5 |
| Out-of-domain authorities | 2 |
| Maximum authority per region | 40% |

Detect:

- Replay
- Clock skew
- Ordering manipulation

---

## Scale Progression

| Scale | Sync Plane Configuration |
|-------|-------------------------|
| Mini (12 nodes) | Single Sync Plane, 1 beacon, manual watermark review |
| Enterprise (~500 nodes) | Per-domain Sync Planes, 2+ beacons per domain, regional validators, automated watermarks |
| Production (30,000+ nodes) | Per-region Sync Planes, 3–5 nodes/region, cross-region beacon federation, continuous watermark, automated drift response |

---

## Relationship to Existing Infrastructure

The Sync Plane extends the existing [DTE (Decision Timing Envelope)](../../specs/dte.schema.json) freshness gates:

| Dimension | DTE | Sync Plane |
|-----------|-----|-----------|
| Question | Is this data fresh enough? | Is this timestamp trustworthy? |
| Scope | Per-decision | Per-evidence-stream |
| Mechanism | TTL comparison | Independent beacon verification |
| Failure mode | Stale data used | Forged or skewed timestamp accepted |

They are complementary. DTE ensures freshness. The Sync Plane ensures the freshness claim itself is credible.
