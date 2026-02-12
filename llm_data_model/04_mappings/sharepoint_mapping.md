# SharePoint → LLM Data Model Mapping

## Overview

SharePoint lists, libraries, and pages map into canonical records.  This document covers the ingestion strategy for the most common SharePoint content types.

## Content type mapping

| SharePoint Content Type | Envelope record_type | Notes |
|---|---|---|
| Document Library Item | `Document` | Files, PDFs, policies, procedures |
| Custom List Item | `Entity` or `Claim` | Depends on list purpose — structured data → Entity, assertions → Claim |
| Page | `Document` | Wiki pages, news posts |
| Calendar Event | `Event` | Meeting records, deadlines |
| Task | `Event` | Action items with timestamps |

## Field mapping

| SharePoint field | Envelope field | Transform |
|---|---|---|
| `ListItemId` | `record_id` | `uuid_from_hash('sp', ListItemId)` |
| `Created` | `created_at` | ISO-8601 conversion |
| `Modified` | `observed_at` | ISO-8601 — last modification = latest observation |
| `Author` | `source.actor.id` | Extract email address |
| `Editor` | `seal.patch_log[-1].author` | Last editor goes into patch log |
| `ContentType` | `record_type` | See content type mapping table above |
| `Title` | `content.title` | Passthrough |
| `Body` / `FileLeafRef` | `content.body` / `content.filename` | Strip HTML for body; preserve filename |
| `_ModerationStatus` | `labels.tags[]` | Map approval status to tag |
| n/a | `provenance` | Auto-generate: `[{type:"source", ref:"sharepoint://<site>/<list>/<id>"}]` |
| n/a | `confidence.score` | Default `0.8` for authored docs, `0.5` for auto-generated |
| n/a | `ttl` | Policy docs: `0` (perpetual). Working docs: `604800000` (7 days). |

## Ingestion strategy

1. **Graph API subscription** — register a webhook on target lists/libraries for real-time change notifications.
2. **Delta query** — on startup and periodic sync, use `/delta` endpoint to fetch only changed items.
3. **Transform** — apply field mapping, generate UUID, compute seal hash.
4. **Validate** — run against `canonical_record.schema.json`.
5. **Ingest** — write to canonical store.

## Permissions

The connector requires `Sites.Read.All` (application permission) or `Sites.ReadWrite.All` if the connector needs to update SharePoint metadata with record_id cross-references.

## Limitations

- SharePoint versioning is separate from envelope versioning.  The envelope `seal.version` tracks changes to the canonical record, not the SharePoint version history.
- Rich text / HTML in SharePoint Body fields is stripped to plain text during ingestion.  Original HTML is preserved in `content.raw_html` if needed for downstream processing.
