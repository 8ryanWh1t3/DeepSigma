---
title: "Credibility Engine — API Reference v0.8.0"
version: "0.8.0"
status: "Stage 3"
last_updated: "2026-02-19"
---

# Credibility Engine API Reference (v0.8.0)

---

## Base URL

```
http://localhost:8000
```

Start the server:

```bash
uvicorn dashboard.api_server:app --reload
```

---

## Authentication (Demo)

Header-based RBAC for demo/development:

| Header | Description | Default |
|--------|-------------|---------|
| `X-Role` | Caller role | `exec` |
| `X-User` | Caller identity | `anonymous` |

Valid roles: `exec`, `truth_owner`, `dri`, `coherence_steward`

---

## Tenant Registry

### GET /api/tenants

Returns all registered tenants.

**Response:**

```json
[
  {
    "tenant_id": "tenant-alpha",
    "display_name": "Tenant Alpha",
    "status": "ACTIVE",
    "profile": "Stable baseline",
    "created_at": "2026-02-19T18:30:00Z"
  }
]
```

---

## Tenant-Scoped Endpoints

All endpoints follow the pattern: `/api/{tenant_id}/credibility/*`

### GET /api/{tenant_id}/credibility/snapshot

Returns current Credibility Index, band, trend, and components.

### GET /api/{tenant_id}/credibility/claims/tier0

Returns current Tier 0 claim state.

### GET /api/{tenant_id}/credibility/drift/24h

Returns drift events for the last 24 hours by severity, category, and region.

### GET /api/{tenant_id}/credibility/correlation

Returns correlation cluster map with coefficients and risk levels.

### GET /api/{tenant_id}/credibility/sync

Returns sync plane integrity with per-region metrics and federation health.

### POST /api/{tenant_id}/credibility/packet/generate

Generates a credibility packet (DLR/RS/DS/MG summaries). Unsealed.

All roles can generate packets.

### POST /api/{tenant_id}/credibility/packet/seal

Seals the latest credibility packet with SHA-256 hash chain.

**Requires role:** `coherence_steward`

**403 Response (wrong role):**

```json
{
  "detail": "Role 'exec' is not authorized for this action. Required: coherence_steward"
}
```

---

## Backward-Compatible Alias Routes

These serve `tenant-alpha` (the default tenant) for backward compatibility with v0.7.0:

| Alias Route | Maps To |
|-------------|---------|
| `GET /api/credibility/snapshot` | `/api/tenant-alpha/credibility/snapshot` |
| `GET /api/credibility/claims/tier0` | `/api/tenant-alpha/credibility/claims/tier0` |
| `GET /api/credibility/drift/24h` | `/api/tenant-alpha/credibility/drift/24h` |
| `GET /api/credibility/correlation` | `/api/tenant-alpha/credibility/correlation` |
| `GET /api/credibility/sync` | `/api/tenant-alpha/credibility/sync` |
| `GET /api/credibility/packet` | `/api/tenant-alpha/credibility/packet/generate` |

---

## Response Notes

All responses include `tenant_id` at the top level for tenant identification.

---

## Guardrails

- Abstract institutional credibility architecture only
- No real-world system modeled
- All data is synthetic
- Demo authentication only — not for production use
