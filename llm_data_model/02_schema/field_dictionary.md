# Field Dictionary

Every field in the Canonical Record Envelope, documented with type, constraints, and examples.

## Envelope fields

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `record_id` | string | yes | Stable UUID prefixed with `rec_`. Never reused, never recycled. | `rec_a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `record_type` | enum | yes | One of: `Claim`, `DecisionEpisode`, `Event`, `Document`, `Entity`, `Metric` | `Claim` |
| `created_at` | date-time | yes | ISO-8601 timestamp of when the record was created in the system. | `2026-02-12T15:00:00Z` |
| `observed_at` | date-time | yes | ISO-8601 timestamp of when the underlying fact was observed. May differ from `created_at` if data is ingested with delay. | `2026-02-12T14:58:30Z` |

## Source block

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `source.system` | string | yes | The system, service, or API that produced this record. | `fraud-detection-agent-v3` |
| `source.actor.type` | enum | no | `agent`, `human`, or `system` | `agent` |
| `source.actor.id` | string | no | Identifier of the producing actor. | `agent-fd-003` |
| `source.environment` | enum | no | `production`, `staging`, `development`, or `test` | `production` |

## Provenance block

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `provenance.chain` | array | yes | Ordered list of provenance steps from claim to source. Min 1 entry. | See below |
| `provenance.chain[].type` | enum | yes | `claim`, `evidence`, or `source` | `claim` |
| `provenance.chain[].statement` | string | no | Human-readable assertion (for `claim` type). | `Account ACC-9921 shows anomalous transfer pattern` |
| `provenance.chain[].ref` | string | no | Reference to supporting record or external source (for `evidence`/`source`). | `rec_evt_transfer_burst_2026-02-12` |
| `provenance.chain[].method` | string | no | How the evidence was gathered. | `statistical_anomaly_detection` |
| `provenance.chain[].captured_at` | date-time | no | When the source data was captured. | `2026-02-12T14:58:00Z` |

## Confidence block

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `confidence.score` | number | yes | 0.0–1.0.  0 = no confidence / unscored.  1 = absolute certainty. | `0.87` |
| `confidence.explanation` | string | yes | Human-readable reason for the score.  Must be meaningful for audit. | `3-sigma deviation in 15-min transfer volume` |

## Freshness fields

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `ttl` | integer | yes | Time-to-live in milliseconds.  `0` = perpetual (e.g., immutable policies). After expiry, record must be re-validated. | `300000` (5 minutes) |
| `assumption_half_life` | integer | no | Half-life of the assumption in ms.  After one half-life, confidence should be halved. | `600000` (10 minutes) |

## Labels block

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `labels.domain` | string | yes | Business domain this record belongs to. | `fraud` |
| `labels.sensitivity` | enum | no | `public`, `internal`, `confidential`, `restricted`, `high` | `high` |
| `labels.project` | string | no | Project or workstream identifier. | `account-protection` |
| `labels.tags` | array[string] | no | Free-form tags for search and filtering. | `["anomaly", "transfer"]` |

## Links array

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `links[].rel` | enum | yes | Relationship type: `supports`, `contradicts`, `derived_from`, `supersedes`, `part_of`, `caused_by`, `verified_by` | `derived_from` |
| `links[].target` | string | yes | `record_id` of the linked record. | `rec_evt_transfer_burst_2026-02-12` |

## Content block

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `content` | object | yes | Type-specific payload.  Structure varies by `record_type`.  No fixed schema — each record type defines its own content shape. | `{ "account_id": "ACC-9921", ... }` |

## Seal block

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `seal.hash` | string | yes | SHA-256 of record content at seal time, prefixed with `sha256:`. | `sha256:e3b0c44...` |
| `seal.sealed_at` | date-time | yes | When the seal was applied. | `2026-02-12T15:00:01Z` |
| `seal.version` | integer | yes | Monotonically increasing.  Starts at 1. | `1` |
| `seal.patch_log` | array | no | Ordered list of patches.  Only field allowed to be appended after sealing. | See below |
| `seal.patch_log[].patched_at` | date-time | yes | When the patch was applied. | `2026-02-13T09:00:00Z` |
| `seal.patch_log[].author` | string | yes | Who applied the patch. | `auditor-jane` |
| `seal.patch_log[].reason` | string | yes | Why the patch was needed. | `Corrected confidence after manual review` |
| `seal.patch_log[].new_hash` | string | yes | New SHA-256 hash after patch. | `sha256:a1b2c3...` |
