# Retention and Redaction

Rules for how long records are kept, when they are archived, and how PII or sensitive content is redacted.

## Retention tiers

| Tier | Records | Hot storage | Warm storage | Cold/archive | Total retention |
|---|---|---|---|---|---|
| **Perpetual** | Sealed DecisionEpisodes, Policy Documents (`ttl = 0`) | Indefinite | n/a | n/a | Forever — these are audit evidence |
| **Standard** | Claims, Events, Metrics, Entities with `ttl > 0` | While TTL is valid | 30 days after expiry | 1 year after expiry | ~1 year post-expiry |
| **Operational** | Power Automate flow runs, sync logs | 7 days | 30 days | 90 days | ~90 days |
| **Ephemeral** | Intermediate computation records, cache entries | TTL only | Not stored | Not stored | TTL duration only |

## Lifecycle stages

1. **Active** — record is in hot storage, fully indexed (vector + keyword + graph), queryable by all authorized components.
2. **Expired** — TTL has lapsed.  Record is marked `stale` in indexes.  Excluded from default queries.  Still queryable with `include_stale=true`.
3. **Warm** — record has been expired for > 7 days.  Moved to warm storage (cheaper, higher latency).  Removed from vector index.  Keyword and graph indexes retained.
4. **Archived** — record has been expired for > 30 days.  Moved to cold storage (object store/glacier).  Removed from all hot indexes.  Queryable only via archive API.
5. **Purged** — record has exceeded its total retention period.  Permanently deleted.  Only a tombstone record_id is retained.

## Redaction

Redaction removes sensitive content from a record while preserving the envelope for audit purposes.

### When to redact

- **Legal hold release** — when a legal hold is lifted and the underlying data must be expunged.
- **PII removal request** — data subject access request (DSAR) requires removal of personal data.
- **Classification change** — a record is reclassified and some content must be removed from lower-sensitivity views.

### Redaction process

1. **Identify fields** — determine which fields in `content` contain sensitive data.
2. **Create redaction patch** — add a patch_log entry with `reason: "redacted:DSAR-2026-001"`.
3. **Replace content** — sensitive fields are replaced with `"[REDACTED]"`.
4. **Recompute hash** — new seal.hash reflects the redacted state.
5. **Preserve links** — graph edges are preserved (the record's position in the graph remains intact).

### Redacted record example

```json
{
  "content": {
    "entity_type": "Customer",
    "entity_id": "[REDACTED]",
    "display_name": "[REDACTED]",
    "status": "active",
    "tier": "enterprise",
    "region": "[REDACTED]"
  }
}
```

## Legal holds

When a legal hold is placed on a set of records:

- Records are flagged with `labels.tags[] += "legal_hold"`.
- Retention timers are paused — no archival or purging while hold is active.
- Access is restricted to `restricted` sensitivity level.
- All access is audit-logged with hold reference.

## Compliance mapping

| Regulation | Relevant rules | Implementation |
|---|---|---|
| GDPR Art. 17 (Right to erasure) | Redaction process | Replace PII in content with [REDACTED], preserve envelope |
| GDPR Art. 30 (Records of processing) | Perpetual retention of DecisionEpisodes | Sealed episodes are retained indefinitely as processing records |
| SOX | Seal immutability | Hash-chain integrity prevents tampering with financial decisions |
| HIPAA | Sensitivity tiers | Health-related records use `restricted` sensitivity with explicit ACLs |
