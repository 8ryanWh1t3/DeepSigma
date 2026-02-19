# Σ OVERWATCH — Stability Contract

**Version:** v1.0.0
**Status:** Beta — core architecture stable, experimental modules clearly marked
**See also:** [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) · [CHANGELOG.md](CHANGELOG.md)

---

## Summary

DeepSigma v1.0.0 is a stable core with clearly delineated stable and experimental surfaces. The artifact schemas, credibility engine, governance layer, mesh infrastructure, and CLI entry points are production-grade and covered by this contract. Adapters and dashboard remain experimental.

If you depend on this project, pin to a tagged release.

---

## What Is Stable (v1.0.0)

These interfaces are stable — breaking changes require a major version bump and a CHANGELOG entry.

### 1. Artifact Schemas (JSON)

| Artifact | Schema File | Stability |
|----------|-------------|-----------|
| DecisionEpisode | `specs/episode.schema.json` | **Stable** |
| Decision Ledger Record (DLR) | `specs/dlr.schema.json` | **Stable** |
| Drift Event | `specs/drift.schema.json` | **Stable** |
| Decision Timing Envelope (DTE) | `specs/dte.schema.json` | **Stable** |
| Claim | `specs/claim.schema.json` | **Stable** |

Sealed episodes and credibility packets written by v1.0.0 will remain readable by future versions.

### 2. Credibility Engine

| Interface | Stability |
|-----------|-----------|
| `credibility_engine.CredibilityEngine` | **Stable** — public API frozen |
| `credibility_engine.CredibilityStore` | **Stable** — JSONL persistence format frozen |
| Credibility Index (6-component, 5-band) | **Stable** — bands and component names frozen |
| Credibility Packet (DLR/RS/DS/MG) | **Stable** — packet schema frozen |
| Seal chaining (`prev_seal_hash \| policy_hash \| snapshot_hash`) | **Stable** — chain format frozen |

### 3. Tenancy & Governance

| Interface | Stability |
|-----------|-----------|
| Tenant registry (`data/tenants.json`) | **Stable** |
| Per-tenant policy schema | **Stable** — keys frozen, values configurable |
| Audit trail format (`audit.jsonl`) | **Stable** — append-only, schema frozen |
| RBAC headers (`X-Role`, `X-User`) | **Stable** |
| Quota enforcement (HTTP 429) | **Stable** |

### 4. Mesh Infrastructure

| Interface | Stability |
|-----------|-----------|
| Evidence Envelope schema | **Stable** |
| Validation Record schema | **Stable** |
| Aggregation Record schema | **Stable** |
| Seal chain mirror format | **Stable** |
| Node roles (edge/validator/aggregator/seal-authority) | **Stable** |
| Federated quorum rules | **Stable** — policy-driven thresholds |
| Append-only JSONL log format | **Stable** |
| Mesh CLI (`python -m mesh.cli`) | **Stable** |

Crypto backend selection (Ed25519 → pynacl → HMAC-SHA256 demo) is stable. Demo mode is clearly labeled and acceptable for non-production use.

### 5. API Endpoints

| Endpoint Pattern | Stability |
|-----------------|-----------|
| `GET /api/tenants` | **Stable** |
| `/api/{tenant_id}/credibility/*` | **Stable** |
| `/api/{tenant_id}/policy` | **Stable** |
| `/api/{tenant_id}/audit/recent` | **Stable** |
| `/api/credibility/*` (alias routes) | **Stable** |
| `/mesh/{tenant_id}/*` | **Stable** |

### 6. CLI Entry Points

```bash
coherence score <path>
coherence audit <path>
coherence mg export <path>
coherence iris query --type <TYPE>
coherence demo <path>
python -m mesh.cli init --tenant <id>
python -m mesh.cli run --tenant <id> --scenario <phase>
python -m mesh.cli scenario --tenant <id> --mode day3
python -m mesh.cli verify --tenant <id>
```

### 7. Money Demo Contract

The `drift_patch_cycle` demo must always produce:
- BASELINE grade A
- DRIFT grade B (or lower)
- PATCH grade A (restored)

Enforced in `tests/test_money_demo.py`. Regression = release blocker.

---

## What Is Experimental (v1.0.0)

These may change between minor releases without a major version bump:

### Internal Python Classes

| Module | Status |
|--------|--------|
| `coherence_ops.dlr.DLRBuilder` | Internal — constructor kwargs may change |
| `coherence_ops.rs.ReflectionSession` | Internal — session API may evolve |
| `coherence_ops.scoring.CoherenceScorer` | Internal — dimension weights not frozen |
| `coherence_ops.iris.IRISEngine` | Internal — query resolution evolving |
| `engine.*` | Internal — compression/degrade/supervisor logic |

**Safe to use:** `CoherenceScorer.score()` return type (grade, overall, dimensions) is stable.

### Adapters

| Adapter | Status |
|---------|--------|
| `adapters/mcp/` | **Scaffold** — not a full MCP implementation |
| `adapters/openclaw/` | **Experimental** — contract check logic stable, API may evolve |
| `adapters/otel/` | **Experimental** — span names and attributes may change |

### Dashboard

The React dashboard (`dashboard/`) and its server API (`dashboard/api_server.py`) are demonstration UIs. Not stable interfaces.

### Coherence Scores

Exact numeric coherence scores are not frozen — scorer weight tuning between releases may shift scores. Grade thresholds (A/B/C/D/F) are stable.

---

## Versioning Policy (Post-1.0)

DeepSigma follows [Semantic Versioning](https://semver.org/):

| Change Type | Version Bump |
|-------------|-------------|
| New feature, backward compatible | **minor** (1.0.0 → 1.1.0) |
| Bug fix, no interface change | **patch** (1.0.0 → 1.0.1) |
| Breaking change to stable interface | **major** (1.0.0 → 2.0.0) |
| Breaking change to experimental interface | **minor** (with CHANGELOG note) |

### How Breaking Changes Are Communicated

1. Entry in [CHANGELOG.md](CHANGELOG.md) under `BREAKING` heading
2. Note in relevant canonical spec or doc
3. Migration path described if feasible

---

*See also: [CHANGELOG.md](CHANGELOG.md) · [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) · [roadmap/README.md](roadmap/README.md)*
