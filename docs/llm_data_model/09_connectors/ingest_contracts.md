# Ingest Contracts

How external systems submit records to the canonical store.

## API endpoint

```
POST /api/v1/records
Content-Type: application/json
Authorization: Bearer <service-token>
```

## Request body

A complete canonical record envelope (see `02_schema/canonical_record.json`).

The ingesting system is responsible for:

1. Generating a unique `record_id` (prefixed with `rec_`).
2. Populating all required fields including `source`, `provenance`, `confidence`.
3. Computing `seal.hash` over the record content.
4. Setting `seal.version = 1` and `seal.sealed_at` to current time.

## Response

| Status | Meaning |
|---|---|
| `201 Created` | Record accepted, validated, and stored |
| `400 Bad Request` | Schema validation failed — response body contains error details |
| `409 Conflict` | `record_id` already exists (duplicate submission) |
| `422 Unprocessable` | Quality rules failed (see `05_validation/quality_rules.md`) — response body contains rule violations |
| `401 Unauthorized` | Missing or invalid service token |
| `403 Forbidden` | Service token lacks permission for the record's `labels.domain` |

## Batch ingestion

```
POST /api/v1/records/batch
Content-Type: application/json
```

Request body: `{ "records": [ ... ] }` — array of canonical records.

- Maximum batch size: 100 records.
- Atomic: either all records pass validation and are stored, or none are.
- Response includes per-record status for debugging.

## Webhook ingestion

For event-driven sources, register a webhook:

```
POST /api/v1/webhooks
{
  "url": "https://canonical-store.internal/api/v1/records",
  "source_system": "core-banking-api",
  "events": ["record.created", "record.patched"],
  "secret": "<hmac-secret>"
}
```

The webhook payload is a canonical record envelope.  The store verifies the HMAC signature before processing.

## Connector responsibilities

Every connector (SharePoint, Palantir, Power Platform, etc.) must:

1. **Map fields** according to the mapping documentation in `04_mappings/`.
2. **Generate deterministic record_ids** using `uuid_from_hash(source_name, source_id)` so re-ingestion doesn't create duplicates.
3. **Set provenance** with at least one `source` entry pointing back to the origin system.
4. **Set confidence** — if the source system has no confidence concept, use `0.0` with `explanation: "unscored"`.
5. **Set TTL** according to the defaults in the mapping documentation.
6. **Compute seal** before submission.
7. **Handle retries** — the API is idempotent on `record_id`, so retries are safe.

## Rate limits

| Tier | Requests/second | Batch size | Notes |
|---|---|---|---|
| Standard connector | 50 | 100 | Most integrations |
| High-volume connector | 500 | 100 | Real-time event streams |
| Bulk migration | 1000 | 100 | One-time historical loads (temporary grant) |
