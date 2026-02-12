# Access Control

Component-level need-to-know access for canonical records.

## Sensitivity tiers

Every record carries a `labels.sensitivity` field that gates access:

| Tier | Who can read | Who can write | Example |
|---|---|---|---|
| `public` | All agents, all humans | Authorized systems | Published policies, public documentation |
| `internal` | All authenticated agents and humans within the organization | Authorized systems | Operational metrics, internal DTEs |
| `confidential` | Named roles + specific agent identities | Authorized systems with elevated grants | Customer data, financial records |
| `restricted` | Explicit per-record ACL | Dedicated ingestion pipelines only | PII, legal holds, sealed investigation records |
| `high` | Same as `restricted` with additional audit logging | Same as `restricted` | Active fraud investigations, security incidents |

## Component access matrix

| Component | public | internal | confidential | restricted / high |
|---|---|---|---|---|
| Agent (runtime context) | read | read | read (if agent is authorized for domain) | denied |
| Supervisor | read | read | read | read (audit-logged) |
| Drift detector | read | read | metadata only (no content) | denied |
| Auditor | read | read | read | read (audit-logged, approval required) |
| Coherence Ops scorer | read | read | metadata only | metadata only |
| External API | read | denied | denied | denied |

## Agent authorization

Agents are authorized by a combination of:

1. **Agent identity** — `source.actor.id` must match a registered agent in the agent registry.
2. **Domain grant** — the agent must have a grant for the record's `labels.domain`.
3. **Sensitivity ceiling** — each agent has a maximum sensitivity tier it can access.

## Record-level ACL

For `restricted` and `high` sensitivity records, an explicit ACL can be attached:

```json
{
  "acl": {
    "readers": ["agent-fd-003", "auditor-jane", "supervisor-main"],
    "writers": ["ingest-pipeline-fraud"],
    "admin": ["security-admin"]
  }
}
```

The ACL is stored outside the sealed envelope (in the access control layer) to avoid re-sealing when permissions change.

## Audit logging

All access to `confidential`, `restricted`, and `high` records is logged:

| Log field | Value |
|---|---|
| `accessor` | Identity of the reader/writer |
| `record_id` | The record accessed |
| `action` | `read`, `write`, `patch`, `graph_traverse` |
| `timestamp` | ISO-8601 |
| `justification` | Required for `restricted`/`high` access |

## Redaction

When a component lacks access to a record's `content`, the system returns a **redacted envelope** containing only: `record_id`, `record_type`, `labels` (without tags), `created_at`, `observed_at`.  The `content`, `provenance`, `confidence`, and `seal` fields are omitted.
