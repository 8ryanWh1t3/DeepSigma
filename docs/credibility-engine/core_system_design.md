---
title: "Core System Design — Evidence Nodes, Events, TTL, Quorum"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-19"
---

# Core System Design

The Credibility Engine operates on three foundational principles:

1. Status is a time-bound assertion
2. History is immutable; current state is derived
3. Truth requires independent confirmation

---

## Status Is a Time-Bound Assertion

Every evidence node in the claim lattice must include:

| Field | Type | Purpose |
|-------|------|---------|
| `element_id` | string | Unique node identifier |
| `status` | enum | OK · DEGRADED · UNKNOWN · FAILED · MAINTENANCE |
| `tier` | integer (0–3) | Source reliability tier |
| `event_time` | timestamp | When the observation occurred at the source |
| `ingest_time` | timestamp | When the lattice received and recorded it |
| `ttl` | duration | Time-to-live before evidence is considered stale |
| `source_id` | string | Provenance: which source produced this evidence |
| `confidence` | float (0.0–1.0) | Assessed reliability of this evidence |
| `signature` | string | Cryptographic integrity seal |
| `correlation_group` | string | Which independence group this source belongs to |
| `mode` | enum | direct · derived |

> No TTL = no truth.

An evidence node without a TTL is an assertion without an expiration date. In the Credibility Engine, that is not allowed. Every claim about reality must have a shelf life.

---

## Event Model (Append-Only)

Events are never overwritten:

| Event | When It Fires |
|-------|--------------|
| `EvidenceReported` | New evidence ingested into the lattice |
| `SignalLoss` | Expected evidence fails to arrive within TTL |
| `DriftDetected` | Institutional drift category triggered |
| `PatchApplied` | Corrective action recorded |
| `ClaimFlip` | Claim status changes (e.g., OK → UNKNOWN) |
| `SealCreated` | Decision episode sealed with hash chain |

Current state is derived from history.

History is immutable.

This mirrors the existing Coherence Ops [sealing and versioning model](../../llm_data_model/08_governance/sealing_and_versioning.md) — records are sealed, patches are appended, and each patch extends the hash chain.

---

## TTL Discipline

| Tier | TTL Range | Example |
|------|-----------|---------|
| Tier 0 | Minutes–Hours | Primary sensor / authoritative beacon |
| Tier 1 | Hours–1 Day | Direct observation or near-real-time feed |
| Tier 2 | 1–7 Days | Aggregated or batch-processed evidence |
| Tier 3 | 1–30 Days | Contextual, historical, or reference data |

Assumptions must expire. No immortal claims allowed.

When evidence exceeds its TTL:

1. The evidence node status shifts toward UNKNOWN
2. Dependent claims lose a quorum vote
3. The [Credibility Index](credibility_index.md) TTL expiration penalty increases
4. If quorum breaks, the claim flips to UNKNOWN automatically

---

## Quorum & Independence

Critical claims require independent confirmation:

| Requirement | Description |
|-------------|-------------|
| N evidence streams | Multiple sources observe the same claim |
| K-of-N agreement | At least K sources must agree for the claim to hold |
| Minimum 2 correlation groups | Sources must come from at least 2 independent groups |
| At least 1 Tier 0 source | One out-of-band, high-reliability source required |

### When Quorum Breaks

If the number of agreeing sources drops below K:

1. The claim flips to **UNKNOWN** automatically
2. A `ClaimFlip` event is emitted
3. All dependent subclaims are re-evaluated
4. The Credibility Index quorum margin penalty activates

**UNKNOWN is honest.**

A claim marked UNKNOWN is not a failure — it is an admission that the institution does not currently have sufficient evidence to assert truth. This is infinitely better than a stale OK.

### Correlation Groups

Sources within the same correlation group share a common dependency. If that dependency fails, all sources in the group fail simultaneously.

The Credibility Engine requires a minimum of 2 correlation groups per critical claim. This ensures that no single infrastructure failure can silently compromise a claim.

---

## Relationship to Existing Primitives

| Credibility Engine Concept | Existing Coherence Ops Primitive |
|---------------------------|--------------------------------|
| Evidence node | [AtomicClaim](../../specs/claim.schema.json) sources and evidence arrays |
| Seal | [Sealing and versioning](../../llm_data_model/08_governance/sealing_and_versioning.md) hash chain |
| TTL discipline | [DTE freshness gates](../../specs/dte.schema.json) defaultTtlMs and per-feature overrides |
| Quorum | Extends claim [status light derivation](../../docs/19-claim-primitive.md) with K-of-N formalism |
| Event model | Extends existing [drift events](../../specs/drift.schema.json) with institutional-scale event types |
