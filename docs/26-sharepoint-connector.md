# SharePoint Connector

Microsoft Graph API connector for SharePoint list and library ingestion.

The `SharePointConnector` fetches items from SharePoint lists, transforms them to canonical record envelopes using the field mapping defined in `llm_data_model/04_mappings/sharepoint_mapping.md`, and supports incremental delta sync and Graph API webhook subscriptions.

**Source:** `adapters/sharepoint/connector.py`

---

## Setup

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `SP_TENANT_ID` | Yes | Azure AD tenant ID |
| `SP_CLIENT_ID` | Yes | App registration client ID |
| `SP_CLIENT_SECRET` | Yes | App registration client secret |
| `SP_SITE_ID` | Yes | SharePoint site ID (format: `{hostname},{site-collection-id},{web-id}`) |
| `SP_WEBHOOK_SECRET` | No | HMAC secret for webhook signature verification |

### Azure AD app registration

The app registration requires these Graph API application permissions:
- `Sites.Read.All` (list items)
- `Sites.ReadWrite.All` (subscriptions)

```bash
export SP_TENANT_ID="your-tenant-id"
export SP_CLIENT_ID="your-client-id"
export SP_CLIENT_SECRET="your-client-secret"
export SP_SITE_ID="contoso.sharepoint.com,site-guid,web-guid"
```

---

## Usage

### Fetch all items from a list

```python
from adapters.sharepoint.connector import SharePointConnector

connector = SharePointConnector()
records = connector.list_items("my-list-id")
for rec in records:
    print(rec["record_id"], rec["content"]["title"])
```

### Fetch a single item

```python
record = connector.get_item("my-list-id", "42")
```

### Incremental delta sync

```python
result = connector.delta_sync("my-list-id")
print(f"Created: {result['created']}, Updated: {result['updated']}")
for rec in result["records"]:
    ingest(rec)
```

Delta tokens are cached per list. Subsequent calls return only changes.

### Webhook subscription

```python
sub = connector.subscribe(
    list_id="my-list-id",
    webhook_url="https://my-app.example.com/api/webhooks/sharepoint",
    expiry_hours=48,
)
print(sub["id"])  # subscription ID
```

---

## API Reference

### `SharePointConnector`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `tenant_id` | `str` | `SP_TENANT_ID` env | Azure AD tenant. |
| `client_id` | `str` | `SP_CLIENT_ID` env | App registration client ID. |
| `client_secret` | `str` | `SP_CLIENT_SECRET` env | App registration secret. |
| `site_id` | `str` | `SP_SITE_ID` env | SharePoint site ID. |

### Methods

| Method | Returns | Description |
|---|---|---|
| `list_items(list_id)` | `list[dict]` | Fetch all items as canonical records. |
| `get_item(list_id, item_id)` | `dict` | Fetch one item as a canonical record. |
| `delta_sync(list_id)` | `dict` | Incremental sync. Returns `{synced, created, updated, records}`. |
| `subscribe(list_id, webhook_url, expiry_hours=48)` | `dict` | Create Graph API webhook subscription. |

---

## Field mapping

SharePoint fields are mapped to canonical record envelopes:

| SharePoint field | Canonical field | Notes |
|---|---|---|
| `id` | `record_id` | Hashed with `sp` prefix via `uuid_from_hash` |
| `ContentType.Name` | `record_type` | Mapped: Document/Wiki Page -> Document, Item -> Entity, Event/Task -> Event |
| `Created` / `createdDateTime` | `created_at` | ISO 8601 |
| `Modified` / `lastModifiedDateTime` | `observed_at` | ISO 8601 |
| `Author` / `createdBy.user.email` | `source.actor.id` | Actor type: `human` |
| `Title` | `content.title` | |
| `Body` | `content.body` | HTML stripped |
| `FileLeafRef` | `content.filename` | |
| `_ModerationStatus` | `labels.tags` | As `approval:{status}` |

### Confidence and TTL

- **Authored content:** confidence `0.8`
- **System-generated:** confidence `0.5`
- **Documents:** TTL `0` (permanent)
- **Working items:** TTL `604800000` (7 days)

---

## MCP Tools

When registered as MCP tools, the connector exposes:

| Tool | Description |
|---|---|
| `sharepoint_list_items` | List items from a SharePoint list |
| `sharepoint_get_item` | Get a single item by list and item ID |
| `sharepoint_delta_sync` | Incremental sync for a list |

---

## Files

| File | Path |
|---|---|
| Source | `adapters/sharepoint/connector.py` |
| Auth helper | `adapters/_azure_auth.py` |
| Field mapping spec | `llm_data_model/04_mappings/sharepoint_mapping.md` |
| This doc | `docs/26-sharepoint-connector.md` |
