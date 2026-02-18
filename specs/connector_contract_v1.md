# Connector Contract v1.0

**Status:** Normative
**Version:** 1.0.0
**Since:** v0.6.0

---

## Overview

Every external data source connector in Sigma OVERWATCH must conform to this contract.
The contract defines:

1. **A standard interface** (`ConnectorV1` protocol) — consistent method signatures
2. **A canonical Record Envelope** — uniform wrapper around raw source data
3. **Pagination, retry, and error expectations** — behavioral guarantees
4. **Auth handling** — credentials via environment/config, never in fixtures

---

## Interface: ConnectorV1

```python
class ConnectorV1(Protocol):
    @property
    def source_name(self) -> str: ...

    def list_records(self, **kwargs) -> List[Dict]: ...
    def get_record(self, record_id: str, **kwargs) -> Dict: ...
    def to_envelopes(self, records: List[Dict]) -> List[RecordEnvelope]: ...
```

### Methods

| Method | Required | Description |
|--------|----------|-------------|
| `source_name` | Yes | Canonical source identifier (`"sharepoint"`, `"snowflake"`, etc.) |
| `list_records(**kwargs)` | Yes | Fetch records from the source. Returns canonical record dicts. |
| `get_record(record_id)` | Optional | Fetch a single record by ID. |
| `to_envelopes(records)` | Yes | Wrap canonical records in `RecordEnvelope` instances. |

Connectors that don't support `get_record` should raise `NotImplementedError`.

---

## Record Envelope

Every record flowing through the system is wrapped in a `RecordEnvelope`:

```json
{
  "envelope_version": "1.0",
  "source": "sharepoint",
  "source_instance": "contoso.sharepoint.com",
  "collected_at": "2026-02-18T10:00:00+00:00",
  "record_id": "5f3a7c28-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "record_type": "Document",
  "provenance": {
    "uri": "sharepoint://contoso.sharepoint.com/sites/ops/lists/Policies/1",
    "last_modified": "2026-02-15T14:30:00.000Z",
    "author": "jane.doe@contoso.com"
  },
  "hashes": {
    "raw_sha256": "a1b2c3..."
  },
  "acl_tags": ["department:ops"],
  "raw": { ... },
  "metadata": { ... }
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `envelope_version` | `"1.0"` | Schema version |
| `source` | string | Canonical source name |
| `source_instance` | string | Instance identifier (site URL, account, etc.) |
| `collected_at` | ISO-8601 | When the record was fetched |
| `record_id` | string | Unique record identifier |
| `record_type` | string | `"Document"`, `"Event"`, `"Entity"`, `"Claim"`, `"Metric"` |
| `provenance.uri` | string | Source URI with scheme |
| `hashes.raw_sha256` | hex string | SHA-256 of the `raw` field |
| `raw` | object or string | The raw source data |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `provenance.etag` | string | Source version identifier |
| `provenance.last_modified` | string | Source last-modified timestamp |
| `provenance.author` | string | Author or last modifier |
| `hashes.normalized_sha256` | hex string | SHA-256 of normalized form |
| `acl_tags` | string[] | Access control tags |
| `metadata` | object | Connector-specific metadata |

### JSON Schema

See: [`specs/connector_envelope.schema.json`](connector_envelope.schema.json)

---

## Envelope Lifecycle

```
Source API Response (raw JSON)
    │
    ▼
Connector._to_canonical(raw)          ← existing behavior (unchanged)
    │
    ▼
Canonical Record (Dict)               ← what Golden Path/pipeline uses
    │
    ▼
Connector.to_envelopes(records)       ← NEW: wraps in envelope
    │
    ▼
RecordEnvelope                        ← standardized, hashable, auditable
```

Existing code that consumes canonical records continues to work unchanged.
The envelope is an additive layer for audit, drift detection, and lineage tracking.

---

## Pagination Contract

Connectors that support pagination must:

1. Accept `cursor` or `offset`/`limit` kwargs in `list_records()`
2. Return all results when no pagination args are provided (default behavior)
3. Include `next_cursor` in response metadata when more pages exist

Pagination is optional — connectors may return all results in a single call.

---

## Retry and Backoff

Connectors should:

1. Retry transient failures (HTTP 429, 503, network timeouts) up to 3 times
2. Use exponential backoff: 1s, 2s, 4s (or honor `Retry-After` headers)
3. Raise `ConnectorError` (or subclass) for non-retryable failures

This is a behavioral expectation, not enforced in the protocol.

---

## Rate Limiting

Connectors should:

1. Respect source rate limits (HTTP 429 with `Retry-After`)
2. Expose rate-limit state in metadata when available
3. Never retry more than 3 times on rate-limit responses

---

## Error Model

| Error Type | Retryable | Description |
|-----------|-----------|-------------|
| `ConnectorAuthError` | No | Authentication/authorization failure |
| `ConnectorRateLimitError` | Yes | Rate limit exceeded |
| `ConnectorTimeoutError` | Yes | Request timed out |
| `ConnectorNotFoundError` | No | Resource not found |
| `ConnectorError` | Depends | Base error class |

---

## Auth Handling

- Credentials are provided via environment variables or constructor kwargs
- Fixture mode bypasses authentication entirely
- No secrets are ever stored in fixture files
- Each connector documents its required env vars

| Connector | Env Vars |
|-----------|----------|
| SharePoint | `SP_TENANT_ID`, `SP_CLIENT_ID`, `SP_CLIENT_SECRET`, `SP_SITE_ID` |
| Dataverse | `DV_ENVIRONMENT_URL`, `DV_CLIENT_ID`, `DV_CLIENT_SECRET`, `DV_TENANT_ID` |
| AskSage | `ASKSAGE_EMAIL`, `ASKSAGE_API_KEY` |
| Snowflake | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY_PATH` |

---

## Validation

```python
from connectors.contract import validate_envelope

errors = validate_envelope(envelope_dict)
if errors:
    print(f"Invalid envelope: {errors}")
```

Envelopes are validated against `specs/connector_envelope.schema.json`.
