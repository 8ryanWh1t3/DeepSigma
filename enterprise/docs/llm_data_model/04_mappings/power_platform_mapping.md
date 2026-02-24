# Power Platform → LLM Data Model Mapping

## Overview

Microsoft Power Platform (Dataverse, Power Automate, Power Apps) records map into canonical records.  This document covers ingestion from Dataverse tables via the Web API and Power Automate flow outputs.

## Table/entity mapping

| Dataverse Table | Envelope record_type | Notes |
|---|---|---|
| Account / Contact | `Entity` | CRM entities — customers, vendors, partners |
| Case / Incident | `Event` | Support cases, incidents with lifecycle timestamps |
| Note / Annotation | `Document` | Attachments, comments, notes |
| Custom Table (analytical) | `Claim` or `Metric` | Computed/derived data → Claim; measured values → Metric |
| Power Automate Run | `Event` | Flow execution records |

## Field mapping

| Dataverse field | Envelope field | Transform |
|---|---|---|
| `activityid` / `<entity>id` | `record_id` | `'rec_' + guid` — reuse Dataverse GUID with prefix |
| `createdon` | `created_at` | ISO-8601 conversion |
| `modifiedon` | `observed_at` | ISO-8601 — last modification |
| `_ownerid_value` | `source.actor.id` | Resolve lookup to user principal name |
| `_ownerid_type` | `source.actor.type` | `systemuser` → `human`, `team` → `system` |
| `statecode` | `labels.tags[]` | Map state (Active/Inactive/Resolved) to tag |
| `statuscode` | `labels.tags[]` | Map status reason to tag |
| All other columns | `content` | Flatten into content object; resolve lookups |

## Power Automate integration

Power Automate flows can push records directly to the canonical store:

1. **Trigger** — Dataverse row created/updated, or scheduled recurrence.
2. **Transform step** — HTTP action calls the ingest API with the mapped record.
3. **Validation** — the ingest API validates against `canonical_record.schema.json` and rejects invalid records.
4. **Seal** — the ingest API computes the seal hash and returns the `record_id`.

## Provenance

- `provenance.chain[0]`: `{type: "source", ref: "dataverse://<environment>/<table>/<id>"}`
- For Power Automate-derived records: add `{type: "evidence", ref: "flow://<flow_id>/run/<run_id>", method: "power_automate_transform"}`

## Confidence scoring

- System-of-record tables (Account, Contact): `confidence.score = 0.95`
- User-entered data (Cases, Notes): `confidence.score = 0.75`
- Flow-computed data: `confidence.score = 0.70`

## TTL defaults

| Content type | TTL (ms) | Rationale |
|---|---|---|
| Account / Contact | `86400000` (24h) | Refreshed daily; may change |
| Active Case | `3600000` (1h) | In-flight cases update frequently |
| Resolved Case | `0` (perpetual) | Historical record — immutable once resolved |
| Note / Attachment | `0` (perpetual) | Authored content doesn't expire |
| Flow Run | `604800000` (7d) | Operational data; useful for recent analysis |

## Permissions

Requires an Azure AD app registration with Dataverse `user_impersonation` or application-level `Environment.Read` scope.  For Power Automate, use a service account with Environment Maker role.
