# Power Platform Connector

Microsoft Dataverse Web API connector for canonical record ingestion.

The `DataverseConnector` queries Dataverse tables (accounts, contacts, incidents, etc.), transforms rows to canonical record envelopes using the field mapping defined in `llm_data_model/04_mappings/power_platform_mapping.md`, and supports OData filtering. Includes webhook integration via the dashboard API for Power Automate flows.

**Source:** `adapters/powerplatform/connector.py`

---

## Setup

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `DV_ENVIRONMENT_URL` | Yes | Dataverse environment URL, e.g. `https://org.crm.dynamics.com` |
| `DV_CLIENT_ID` | Yes | Azure AD app registration client ID |
| `DV_CLIENT_SECRET` | Yes | App registration client secret |
| `DV_TENANT_ID` | Yes | Azure AD tenant ID |
| `PA_WEBHOOK_SECRET` | No | HMAC secret for Power Automate webhook verification |

```bash
export DV_ENVIRONMENT_URL="https://myorg.crm.dynamics.com"
export DV_CLIENT_ID="your-client-id"
export DV_CLIENT_SECRET="your-client-secret"
export DV_TENANT_ID="your-tenant-id"
```

---

## Usage

### List all records from a table

```python
from adapters.powerplatform.connector import DataverseConnector

connector = DataverseConnector()
records = connector.list_records("accounts")
for rec in records:
    print(rec["record_id"], rec["record_type"])
```

### Get a single record

```python
record = connector.get_record("contacts", "00000000-0000-0000-0000-000000000001")
```

### Query with OData filter

```python
active_cases = connector.query("incidents", "$filter=statecode eq 0")
```

---

## API Reference

### `DataverseConnector`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `environment_url` | `str` | `DV_ENVIRONMENT_URL` env | Dataverse environment URL. |
| `client_id` | `str` | `DV_CLIENT_ID` env | Azure AD client ID. |
| `client_secret` | `str` | `DV_CLIENT_SECRET` env | Azure AD client secret. |
| `tenant_id` | `str` | `DV_TENANT_ID` env | Azure AD tenant ID. |

### Methods

| Method | Returns | Description |
|---|---|---|
| `list_records(table_name)` | `list[dict]` | Fetch all records as canonical records. |
| `get_record(table_name, record_id)` | `dict` | Fetch one record by Dataverse GUID. |
| `query(table_name, filter_expr)` | `list[dict]` | Query with OData `$filter` expression. |

---

## Field mapping

### Table to record type

| Dataverse table | Canonical `record_type` | Confidence | TTL |
|---|---|---|---|
| `accounts` | Entity | 0.95 | 24h |
| `contacts` | Entity | 0.95 | 24h |
| `incidents` | Event | 0.75 | 1h (active) |
| `cases` | Event | 0.75 | 1h (active) |
| `annotations` | Document | 0.75 | perpetual |
| `notes` | Document | 0.75 | perpetual |
| `tasks` | Event | 0.70 | 7d |
| `emails` | Event | 0.70 | 7d |

Resolved/inactive records (`statecode != 0`) get TTL `0` (perpetual) and boosted confidence.

### Row to canonical envelope

| Dataverse field | Canonical field | Notes |
|---|---|---|
| `{singular}id` (e.g. `accountid`) | `record_id` | Prefixed with `rec_` |
| `createdon` | `created_at` | ISO 8601 |
| `modifiedon` | `observed_at` | ISO 8601 |
| `_ownerid_value` | `source.actor.id` | |
| `_ownerid_type` | `source.actor.type` | `systemuser` -> `human`, else `system` |
| `statecode` | `labels.tags` | As `state:Active/Inactive/Resolved` |
| `statuscode` | `labels.tags` | As `status:{code}` |
| *(remaining fields)* | `content` | Excluding metadata prefixes `@`, `_` |

---

## Webhook (Power Automate)

Power Automate flows can push records to `POST /api/webhooks/powerautomate`:

- **Canonical records:** Send `{record_id, record_type, ...}` -- passed through directly.
- **Raw Dataverse records:** Send the Dataverse row JSON -- auto-transformed via `_to_canonical()`.
- **HMAC:** When `PA_WEBHOOK_SECRET` is set, include `X-PowerAutomate-Signature` header.

---

## MCP Tools

| Tool | Description |
|---|---|
| `dataverse_list_records` | List records from a Dataverse table |
| `dataverse_get_record` | Get a single record by table and GUID |
| `dataverse_query` | Query with OData filter expression |

---

## Files

| File | Path |
|---|---|
| Source | `adapters/powerplatform/connector.py` |
| Auth helper | `adapters/_azure_auth.py` |
| Field mapping spec | `llm_data_model/04_mappings/power_platform_mapping.md` |
| Webhook handler | `dashboard/api_server.py` |
| This doc | `docs/27-power-platform-connector.md` |
