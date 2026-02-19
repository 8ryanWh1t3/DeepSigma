---
title: "Mini Lattice — Canonical Artifacts"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# Mini Lattice Artifacts

> Every drift-patch-seal cycle produces four canonical artifacts: DLR, RS, DS, MG.

This document shows the minimal artifact set for the [mini lattice scenario](SCENARIO.md).

---

## DLR — Decision Ledger Record

The DLR records **what was decided** in response to drift.

```json
{
  "dlr_id": "DLR-MINI-001",
  "episode_id": "EP-MINI-001",
  "title": "Patch Source-S2 TTL expiration on SubClaim-A3",
  "decided_by": "drift-automation",
  "decision_date": "2026-02-19T14:11:00Z",
  "decision_type": "patch",
  "evidence_refs": ["DS-MINI-001"],
  "outcome": "SubClaim-A3 restored to OK after Source-S2 re-ingestion",
  "claims": [
    {
      "claim_id": "Claim-A",
      "status_before": "OK (degraded)",
      "status_after": "OK"
    }
  ],
  "sealed": true,
  "seal_hash": "sha256:a1b2c3..."
}
```

---

## RS — Reasoning Scaffold

The RS captures **why this decision was made** — the reasoning chain.

```json
{
  "rs_id": "RS-MINI-001",
  "episode_id": "EP-MINI-001",
  "dlr_ref": "DLR-MINI-001",
  "reasoning": {
    "trigger": "TTL expiration on Evidence-E4 and Evidence-E5",
    "root_cause": "Source-S2 feed delayed beyond 1-hour TTL",
    "options_considered": [
      {
        "option": "Extend TTL to 2 hours",
        "rejected_because": "Masks the underlying feed delay without fixing it"
      },
      {
        "option": "Re-ingest from Source-S2 with current TTL",
        "selected_because": "Addresses root cause; Source-S2 is back online"
      }
    ],
    "risk_assessment": "Low — Source-S2 confidence restored above 0.85 threshold",
    "blast_radius": ["SubClaim-A3", "Claim-A (indirect)"]
  },
  "sealed": true,
  "seal_hash": "sha256:d4e5f6..."
}
```

---

## DS — Drift Signal

The DS records **what drifted** — the structured drift detection output.

```json
{
  "ds_id": "DS-MINI-001",
  "episode_id": "EP-MINI-001",
  "category": "ttl_compression",
  "severity": "yellow",
  "detected_at": "2026-02-19T14:01:00Z",
  "affected_claims": ["SubClaim-A3"],
  "affected_evidence": ["Evidence-E4", "Evidence-E5"],
  "source_id": "Source-S2",
  "runtime_types": ["freshness", "time"],
  "description": "Evidence-E4 and E5 exceeded 1-hour TTL. SubClaim-A3 quorum broken.",
  "credibility_index_impact": {
    "before": 88,
    "after": 72,
    "delta": -16
  },
  "sealed": true,
  "seal_hash": "sha256:g7h8i9..."
}
```

---

## MG — Memory Graph Diff

The MG records **how institutional memory changed** — new nodes and edges in the knowledge graph.

```json
{
  "mg_id": "MG-MINI-001",
  "episode_id": "EP-MINI-001",
  "diff": {
    "nodes_added": [
      {
        "id": "DS-MINI-001",
        "type": "DriftSignal",
        "category": "ttl_compression",
        "severity": "yellow"
      },
      {
        "id": "PATCH-MINI-001",
        "type": "Patch",
        "action": "re-ingest",
        "target": ["Evidence-E4", "Evidence-E5"]
      }
    ],
    "edges_added": [
      {
        "from": "DS-MINI-001",
        "to": "SubClaim-A3",
        "predicate": "TRIGGERED_BY"
      },
      {
        "from": "PATCH-MINI-001",
        "to": "DS-MINI-001",
        "predicate": "RESOLVED_BY"
      },
      {
        "from": "EP-MINI-001",
        "to": "DLR-MINI-001",
        "predicate": "HAS_DLR"
      },
      {
        "from": "EP-MINI-001",
        "to": "RS-MINI-001",
        "predicate": "HAS_RS"
      },
      {
        "from": "EP-MINI-001",
        "to": "DS-MINI-001",
        "predicate": "HAS_DS"
      },
      {
        "from": "EP-MINI-001",
        "to": "MG-MINI-001",
        "predicate": "HAS_MG"
      }
    ],
    "nodes_modified": [
      {
        "id": "SubClaim-A3",
        "field": "status",
        "from": "UNKNOWN",
        "to": "OK"
      },
      {
        "id": "Evidence-E4",
        "field": "status",
        "from": "UNKNOWN",
        "to": "OK"
      },
      {
        "id": "Evidence-E5",
        "field": "status",
        "from": "UNKNOWN",
        "to": "OK"
      }
    ]
  },
  "sealed": true,
  "seal_hash": "sha256:j0k1l2..."
}
```

---

## Sealed DecisionEpisode

All four artifacts are sealed together as one immutable episode.

```json
{
  "episode_id": "EP-MINI-001",
  "version": 1,
  "sealed_at": "2026-02-19T14:12:00Z",
  "artifacts": {
    "dlr": "DLR-MINI-001",
    "rs": "RS-MINI-001",
    "ds": "DS-MINI-001",
    "mg": "MG-MINI-001"
  },
  "hash_chain": [
    "sha256:prev_seal...",
    "sha256:a1b2c3...",
    "sha256:d4e5f6...",
    "sha256:g7h8i9...",
    "sha256:j0k1l2..."
  ],
  "credibility_index": {
    "before": 88,
    "during_drift": 72,
    "after_patch": 88
  }
}
```

---

## IRIS Queries Against This Episode

```
Q: "What drifted?"
A: SubClaim-A3 — TTL expiration on Evidence-E4, E5 (Source-S2)

Q: "What was patched?"
A: Evidence-E4 and E5 re-ingested from Source-S2. SubClaim-A3 quorum restored.

Q: "Why was this decision made?"
A: Source-S2 feed delayed beyond 1-hour TTL. Re-ingestion chosen over TTL extension
   because it addresses the root cause rather than masking the delay.

Q: "What was the impact?"
A: Credibility Index dropped from 88 to 72 during drift, restored to 88 after patch.
```
