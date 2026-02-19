---
title: "Credibility Engine — Multi-Tenant Specification"
version: "0.8.0"
status: "Stage 3"
last_updated: "2026-02-19"
---

# Multi-Tenant Credibility Engine Specification

---

## Tenant Entity

Each tenant represents an isolated institutional credibility boundary.

| Field | Type | Description |
|-------|------|-------------|
| `tenant_id` | string (slug) | Unique identifier, e.g. `tenant-alpha` |
| `display_name` | string | Human-readable name |
| `status` | string | `ACTIVE` |
| `profile` | string | Credibility profile description |
| `created_at` | ISO 8601 | Creation timestamp |

Registry stored at `data/tenants.json`.

---

## Tenant Isolation

- Each tenant gets an isolated data directory: `data/credibility/{tenant_id}/`
- No cross-tenant data access at the store or engine level
- Engine instances are cached per-tenant in the API layer
- All persisted records include `tenant_id` field

---

## Roles & Permission Matrix

Header-based RBAC via `X-Role` and `X-User` headers.

| Role | Snapshot | Claims | Drift | Correlation | Sync | Generate Packet | Seal Packet |
|------|----------|--------|-------|-------------|------|-----------------|-------------|
| `exec` | Read | Read | Read | Read | Read | Yes | **No** |
| `truth_owner` | Read | Read | Read | Read | Read | Yes | **No** |
| `dri` | Read | Read | Read | Read | Read | Yes | **No** |
| `coherence_steward` | Read | Read | Read | Read | Read | Yes | **Yes** |

- Default role (no header): `exec`
- Invalid role values fall back to `exec`
- Seal requires `coherence_steward` — returns HTTP 403 for all other roles

---

## Tenant ID Propagation Rule

Every record written to persistence MUST include:
- `tenant_id` — the owning tenant
- `timestamp` — write time (auto-injected if missing)

Records read from persistence that lack `tenant_id` are enriched with the store's tenant_id on load (backward compatibility with pre-0.8.0 data).

---

## Canonical Record Schemas

### Claim

```json
{
  "tenant_id": "tenant-alpha",
  "id": "CLM-T0-001",
  "title": "Primary institutional readiness assertion",
  "state": "VERIFIED",
  "confidence": 0.94,
  "k_required": 3,
  "n_total": 5,
  "margin": 2,
  "ttl_remaining": 185,
  "correlation_group": "CG-001",
  "region": "East",
  "domain": "E1",
  "last_verified": "2026-02-19T18:30:00Z"
}
```

### Drift Event

```json
{
  "tenant_id": "tenant-alpha",
  "id": "DRF-001",
  "severity": "medium",
  "fingerprint": "",
  "timestamp": "2026-02-19T18:30:00Z",
  "tier_impact": 0,
  "category": "timing_entropy",
  "region": "East",
  "auto_resolved": false
}
```

### Correlation Cluster

```json
{
  "tenant_id": "tenant-alpha",
  "id": "CG-002",
  "label": "Shared Infrastructure (East + Central)",
  "coefficient": 0.78,
  "status": "REVIEW",
  "sources": ["S-003", "S-007", "S-012"],
  "claims_affected": 28,
  "domains": ["E2", "C1", "C2"],
  "regions": ["East", "Central"]
}
```

### Sync Region

```json
{
  "tenant_id": "tenant-alpha",
  "id": "Central",
  "time_skew_ms": 18,
  "watermark_lag_s": 1.2,
  "replay_flags": 0,
  "status": "OK",
  "sync_nodes": 5,
  "sync_nodes_healthy": 5,
  "beacons": 2,
  "beacons_healthy": 2,
  "watermark_advancing": true,
  "last_watermark": "2026-02-19T18:30:00Z"
}
```

### Snapshot

```json
{
  "tenant_id": "tenant-alpha",
  "credibility_index": 97,
  "band": "Stable",
  "timestamp": "2026-02-19T18:30:00Z",
  "summary": "CI=97 (Stable) — 2 drift events"
}
```

### Credibility Packet

```json
{
  "tenant_id": "tenant-alpha",
  "packet_id": "CP-2026-02-19-1830",
  "generated_at": "2026-02-19T18:30:00Z",
  "generated_by": "demo",
  "credibility_index": { "score": 97, "band": "Stable", "components": {} },
  "dlr_summary": { ... },
  "rs_summary": { ... },
  "ds_summary": { ... },
  "mg_summary": { ... },
  "seal": {
    "sealed": true,
    "seal_hash": "sha256:abc123...",
    "sealed_at": "2026-02-19T18:31:00Z",
    "sealed_by": "demo",
    "role": "Coherence Steward",
    "hash_chain_length": 158
  },
  "guardrails": { "abstract_model": true, "domain_specific": false }
}
```

---

## Guardrails

- Abstract institutional credibility architecture only
- No real-world weapon modeling
- No operational defense content
- All tenant data is synthetic
- No cross-tenant data bleed
