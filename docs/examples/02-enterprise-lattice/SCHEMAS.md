---
title: "Enterprise Lattice — Schema Reference"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# Enterprise Lattice Schema Reference

> Schema structures for enterprise-scale lattice entities.

These schemas extend the [Core System Design](../../docs/credibility-engine/core_system_design.md) evidence node model for multi-domain operation.

---

## Evidence Node

The fundamental unit. Every evidence node carries these fields.

```json
{
  "element_id": "Evidence-E1",
  "status": "OK",
  "tier": 1,
  "event_time": "2026-02-19T10:00:00Z",
  "ingest_time": "2026-02-19T10:00:03Z",
  "ttl": "PT4H",
  "source_id": "Source-S001",
  "confidence": 0.92,
  "signature": "sha256:abc123...",
  "correlation_group": "internal-sensors",
  "mode": "direct",
  "domain": "alpha"
}
```

| Field | Required | Constraints |
|-------|----------|-------------|
| `element_id` | Yes | Unique across lattice |
| `status` | Yes | OK · DEGRADED · UNKNOWN · FAILED · MAINTENANCE |
| `tier` | Yes | 0–3, higher tier = higher weight |
| `event_time` | Yes | ISO 8601, must precede `ingest_time` |
| `ingest_time` | Yes | ISO 8601, set by lattice on receipt |
| `ttl` | Yes | ISO 8601 duration (no immortal evidence) |
| `source_id` | Yes | Reference to Source registry |
| `confidence` | Yes | 0.0–1.0 |
| `signature` | Yes | Cryptographic hash for integrity |
| `correlation_group` | Yes | Independence group identifier |
| `mode` | Yes | `direct` (observed) or `derived` (computed) |
| `domain` | Enterprise+ | Domain assignment for multi-domain lattices |

---

## Source Registry

Sources are the provenance root. Each source belongs to exactly one correlation group.

```json
{
  "source_id": "Source-S003",
  "name": "Cross-Domain Feed Alpha-Beta",
  "tier": 1,
  "correlation_group": "shared-infrastructure",
  "domains": ["alpha", "beta"],
  "evidence_count": 12,
  "refresh_cadence": "PT1H",
  "status": "active",
  "last_seen": "2026-02-19T13:45:00Z"
}
```

| Field | Purpose |
|-------|---------|
| `source_id` | Unique identifier |
| `tier` | Reliability tier (0 = highest) |
| `correlation_group` | Independence group — all sources in a group share a common dependency |
| `domains` | Which domains this source feeds |
| `evidence_count` | How many evidence nodes depend on this source |
| `refresh_cadence` | Expected evidence delivery interval |
| `status` | active · degraded · quarantined · offline |

---

## Correlation Group

Groups track shared dependencies. If the dependency fails, all sources in the group fail simultaneously.

```json
{
  "group_id": "shared-infrastructure",
  "description": "Sources sharing primary data center network",
  "sources": ["Source-S003", "Source-S007", "Source-S012"],
  "domains_affected": ["alpha", "beta"],
  "risk_level": "high",
  "evidence_count": 28,
  "last_reviewed": "2026-02-15"
}
```

### Enterprise Correlation Group Inventory

| Group | Sources | Domains | Evidence | Risk |
|-------|---------|---------|----------|------|
| internal-sensors | S001, S004, S008 | Alpha | 15 | Low |
| external-feeds | S002, S005, S009 | Alpha, Gamma | 12 | Medium |
| shared-infrastructure | S003, S007, S012 | Alpha, Beta | 28 | **High** |
| compliance-feeds | S006, S010 | Gamma | 10 | Low |
| beta-primary | S011, S013, S014 | Beta | 18 | Medium |
| reference-data | S015, S016 | All | 8 | Low |

**Key risk:** `shared-infrastructure` feeds 28 evidence nodes across 2 domains. This is the redundancy illusion — Alpha and Beta look independent but are not.

---

## Claim Structure

Claims decompose into subclaims. Subclaims link to evidence.

```json
{
  "claim_id": "Claim-A1",
  "domain": "alpha",
  "tier": 0,
  "title": "Primary mission readiness assertion",
  "subclaims": ["SubClaim-A1a", "SubClaim-A1b", "SubClaim-A1c", "SubClaim-A1d"],
  "quorum": {
    "n": 12,
    "k": 8,
    "min_correlation_groups": 2,
    "requires_tier_0_source": true
  },
  "status": "OK",
  "credibility_sub_index": 91
}
```

### Quorum Configuration by Tier

| Claim Tier | Minimum N | Minimum K | Min Groups | Tier 0 Required |
|------------|-----------|-----------|------------|-----------------|
| 0 | 4 | 3 | 2 | Yes |
| 1 | 3 | 2 | 2 | Recommended |
| 2 | 2 | 1 | 1 | No |

---

## Domain Sync Plane

Each domain operates its own Sync Plane with independent beacons.

```json
{
  "sync_plane_id": "sync-alpha",
  "domain": "alpha",
  "beacons": [
    {
      "beacon_id": "Beacon-A1",
      "type": "internal",
      "tier": 1,
      "status": "active",
      "last_heartbeat": "2026-02-19T13:59:30Z"
    },
    {
      "beacon_id": "Beacon-A2",
      "type": "external",
      "tier": 0,
      "status": "active",
      "last_heartbeat": "2026-02-19T13:59:28Z"
    }
  ],
  "sync_nodes": 3,
  "watermark": "2026-02-19T13:59:00Z",
  "watermark_cadence": "PT30S"
}
```

---

## Drift Signal (Enterprise)

Enterprise drift signals include domain and correlation context.

```json
{
  "ds_id": "DS-ENT-002",
  "episode_id": "EP-ENT-002",
  "category": "confidence_volatility",
  "severity": "red",
  "detected_at": "2026-02-19T18:00:00Z",
  "domains_affected": ["alpha", "beta"],
  "affected_claims": ["Claim-A1", "Claim-A2", "Claim-B1", "Claim-B2"],
  "affected_evidence_count": 12,
  "source_id": "Source-S003",
  "correlation_group": "shared-infrastructure",
  "runtime_types": ["verify", "outcome"],
  "cross_domain": true,
  "credibility_index_impact": {
    "before": 84,
    "after": 68,
    "delta": -16
  }
}
```

---

## Relationship to Existing Schemas

| Enterprise Schema | Extends |
|-------------------|---------|
| Evidence node | [Core System Design](../../docs/credibility-engine/core_system_design.md) evidence model + `domain` field |
| Drift signal | [drift.schema.json](../../specs/drift.schema.json) + institutional category + cross-domain flag |
| Claim quorum | [claim.schema.json](../../specs/claim.schema.json) + K-of-N formalism + correlation group requirement |
| Sync Plane | [dte.schema.json](../../specs/dte.schema.json) freshness gates + beacon infrastructure |
