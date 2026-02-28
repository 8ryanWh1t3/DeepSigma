# Governance Hardening Layer — v0.9.0

> Board-grade governance without bloat.

Abstract institutional credibility architecture.
No real-world system modeled.

---

## Overview

v0.9.0 adds five governance capabilities to the multi-tenant credibility engine:

1. **Per-Tenant Policy Engine** — Policies become data, not hardcoded constants
2. **Seal Chaining** — Every seal is chained to the prior seal for tamper-evident continuity
3. **Immutable Audit Trail** — Sensitive operations emit append-only audit events
4. **Drift Recurrence Weighting** — Repeated drift fingerprints drive severity escalation
5. **Quotas + SLO Telemetry** — Per-tenant rate limits and operational metrics

---

## 1. Per-Tenant Policy Engine

### Location

- **Module:** `tenancy/policies.py`
- **Data:** `data/policies/{tenant_id}.json`

### Policy Schema

```json
{
  "tenant_id": "tenant-alpha",
  "updated_at": "ISO8601",
  "ttl_policy": {
    "tier0_seconds": 900,
    "tier1_seconds": 3600,
    "tier2_seconds": 21600
  },
  "quorum_policy": {
    "tier0": {
      "k_required": 3,
      "n_total": 5,
      "min_correlation_groups": 2,
      "out_of_band_required": true
    },
    "tier1": {
      "k_required": 2,
      "n_total": 4,
      "min_correlation_groups": 2,
      "out_of_band_required": false
    }
  },
  "correlation_policy": {
    "review_threshold": 0.7,
    "invalid_threshold": 0.9
  },
  "silence_policy": {
    "healthy_pct": 0.1,
    "elevated_pct": 1.0,
    "degraded_pct": 2.0
  },
  "slo_policy": {
    "why_retrieval_target_seconds": 60,
    "packet_generate_target_ms": 500
  },
  "quota_policy": {
    "packets_per_hour": 120,
    "exports_per_day": 500
  }
}
```

### Functions

| Function | Description |
|----------|-------------|
| `load_policy(tenant_id)` | Load policy; creates default if missing |
| `save_policy(tenant_id, dict, actor)` | Persist updated policy |
| `evaluate_policy(tenant_id, state)` | Evaluate policy against current engine state |
| `get_policy_hash(dict)` | SHA-256 of canonical policy content (excludes metadata) |

### Policy Evaluation

`evaluate_policy()` checks:
- **TTL violations** — claims with expired TTL
- **Correlation violations** — clusters exceeding review/invalid thresholds
- **Quorum violations** — claims in UNKNOWN state (broken quorum)
- **Silence violations** — silent node percentage exceeding thresholds

Returns: `violations` list, `policy_hash`, `applied_thresholds`.

### API

- `GET /api/{tenant_id}/policy` — Read current policy
- `POST /api/{tenant_id}/policy` — Update policy (requires `truth_owner` or `coherence_steward`)

---

## 2. Seal Chaining

### How It Works

Each sealed packet includes:

| Field | Source |
|-------|--------|
| `seal_hash` | SHA-256 of `prev_seal_hash + policy_hash + snapshot_hash + canonical_packet` |
| `prev_seal_hash` | Previous seal's hash, or `"GENESIS"` for the first seal |
| `policy_hash` | SHA-256 of current tenant policy |
| `snapshot_hash` | SHA-256 of latest credibility snapshot |

### Verification

To verify tamper evidence:

1. Load `seal_chain.jsonl` for the tenant
2. For each entry, verify `seal_hash` derives from the declared inputs
3. Confirm `prev_seal_hash` matches the previous entry's `seal_hash`
4. Confirm `policy_hash` matches the policy file at the declared time
5. First entry must have `prev_seal_hash = "GENESIS"`

### Storage

- Seal chain: `data/credibility/{tenant_id}/seal_chain.jsonl` (append-only)
- Latest packet: `data/credibility/{tenant_id}/packet_latest.json`

---

## 3. Immutable Audit Trail

### Location

- **Module:** `governance/audit.py`
- **Data:** `data/audit/{tenant_id}/audit.jsonl`

### Audit Event Schema

```json
{
  "audit_id": "AUD-xxxxxxxxxxxx",
  "tenant_id": "tenant-alpha",
  "timestamp": "ISO8601",
  "actor_user": "demo",
  "actor_role": "coherence_steward",
  "action": "PACKET_SEAL",
  "target_type": "PACKET",
  "target_id": "CP-2026-02-19-1200",
  "outcome": "SUCCESS",
  "metadata": {}
}
```

### Audited Actions

| Action | When |
|--------|------|
| `PACKET_GENERATE` | Packet generated |
| `PACKET_SEAL` | Packet sealed (SUCCESS or DENIED) |
| `SNAPSHOT_WRITE` | Snapshot persisted |
| `POLICY_UPDATE` | Policy modified |

**Denied attempts are always audited** (e.g., seal denied due to wrong role, quota exceeded).

### API

- `GET /api/{tenant_id}/audit/recent?limit=50` — Read-only, most recent events

---

## 4. Drift Recurrence Weighting

### Location

- **Module:** `governance/drift_registry.py`
- **Data:** `data/drift_registry/{tenant_id}.json`

### Weighting Rules

| 24h Recurrence | Severity Multiplier |
|----------------|-------------------|
| > 50 | 3.0x |
| > 25 | 2.0x |
| > 10 | 1.5x |
| <= 10 | 1.0x |

### How It Works

1. Drift events are grouped by fingerprint (or category if no fingerprint)
2. 24h and 7d counts are maintained per fingerprint
3. Severity weight is computed from 24h recurrence
4. Registry is updated when snapshots are generated

### Functions

| Function | Description |
|----------|-------------|
| `update_drift_registry(tenant_id, events)` | Update fingerprint counts |
| `get_weighted_drift_summary(tenant_id, events)` | Return weighted severity summary |

---

## 5. Quotas + SLO Telemetry

### Location

- **Module:** `governance/telemetry.py`
- **Data:** `data/telemetry/{tenant_id}/telemetry.jsonl`

### Quota Enforcement

Quotas are defined in tenant policy:

| Quota | Default |
|-------|---------|
| `packets_per_hour` | 120 |
| `exports_per_day` | 500 |

When exceeded: HTTP 429 response + audit event with outcome `DENIED`.

### Tracked Metrics

| Metric | Unit |
|--------|------|
| `packet_generate_latency_ms` | ms |
| `packet_seal_latency_ms` | ms |

### Functions

| Function | Description |
|----------|-------------|
| `record_metric(tenant_id, name, value, actor)` | Persist a metric |
| `check_quota(tenant_id, action, policy)` | Returns True if allowed |

---

## Seeded Tenant Policy Differences

| Setting | Alpha | Bravo | Charlie |
|---------|-------|-------|---------|
| Tier 0 TTL (s) | 900 | 600 | 900 |
| Quorum K (Tier 0) | 3/5 | 4/6 | 3/5 |
| Correlation invalid | 0.9 | 0.9 | 0.85 |
| Packets/hour | 120 | 60 | 120 |
| WHY retrieval (s) | 60 | 45 | 60 |

Bravo has stricter quorum and lower quotas. Charlie has a lower correlation invalid threshold.

---

## Guardrails

- Abstract institutional credibility model
- Non-domain: no real-world system modeled
- Audit log is append-only; no mutation or deletion via code paths
- Policy changes are audited with actor identity
- Seal chaining is tamper-evident, not tamper-proof (demo/development context)

---

## File Inventory

### New Files

| File | Purpose |
|------|---------|
| `governance/__init__.py` | Package init |
| `governance/audit.py` | Immutable audit trail |
| `governance/drift_registry.py` | Drift recurrence weighting |
| `governance/telemetry.py` | Quotas + SLO telemetry |
| `tenancy/policies.py` | Per-tenant policy engine |
| `data/policies/tenant-alpha.json` | Alpha policy (default) |
| `data/policies/tenant-bravo.json` | Bravo policy (stricter quorum) |
| `data/policies/tenant-charlie.json` | Charlie policy (lower correlation threshold) |
| `docs/credibility-engine/GOVERNANCE_V0_9.md` | This document |

### Modified Files

| File | Changes |
|------|---------|
| `pyproject.toml` | Version 0.8.0 -> 0.9.0, added `governance*` to packages |
| `credibility_engine/__init__.py` | Version bump |
| `credibility_engine/packet.py` | Seal chaining, audit events, policy hash |
| `credibility_engine/engine.py` | Policy evaluation in snapshots, drift registry |
| `credibility_engine/api.py` | Policy/audit endpoints, quota enforcement |
| `tenancy/__init__.py` | Export policy functions |
| `dashboard/credibility-engine-demo/app.js` | Policy hash + seal chain display |
| `dashboard/credibility-engine-demo/index.html` | Policy hash element |
| `CHANGELOG.md` | v0.9.0 entry |
