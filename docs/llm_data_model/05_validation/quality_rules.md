# Quality Rules

Validation rules that every canonical record must pass before it enters the system.  These rules go beyond JSON Schema structural validation — they enforce semantic quality.

## Required field rules

| Rule ID | Field | Condition | Severity |
|---|---|---|---|
| QR-001 | `record_id` | Must match pattern `rec_[a-f0-9\-]{36}` | REJECT |
| QR-002 | `record_type` | Must be one of: Claim, DecisionEpisode, Event, Document, Entity, Metric | REJECT |
| QR-003 | `created_at` | Must be valid ISO-8601 datetime, not in the future (tolerance: +60s) | REJECT |
| QR-004 | `observed_at` | Must be valid ISO-8601 datetime, must be ≤ `created_at` (tolerance: +60s) | WARN |
| QR-005 | `source.system` | Must be non-empty string | REJECT |
| QR-006 | `provenance.chain` | Must have ≥ 1 entry | REJECT |
| QR-007 | `confidence.score` | Must be 0.0–1.0 inclusive | REJECT |
| QR-008 | `confidence.explanation` | Must be non-empty string, min 10 characters | WARN |
| QR-009 | `ttl` | Must be ≥ 0 integer | REJECT |
| QR-010 | `labels.domain` | Must be non-empty string | REJECT |
| QR-011 | `seal.hash` | Must start with `sha256:` | REJECT |
| QR-012 | `seal.version` | Must be ≥ 1 integer | REJECT |

## TTL rules

| Rule ID | Condition | Severity |
|---|---|---|
| QR-020 | If `ttl = 0`, record is perpetual — only allowed for `Document` and sealed `DecisionEpisode` types | WARN |
| QR-021 | If `ttl > 0`, `observed_at + ttl` must be in the future at ingestion time (record is not already expired) | WARN |
| QR-022 | If `assumption_half_life` is set, it must be ≥ `ttl` | WARN |
| QR-023 | `Claim` records should have `ttl ≤ 86400000` (24h) unless explicitly overridden | WARN |

## Provenance rules

| Rule ID | Condition | Severity |
|---|---|---|
| QR-030 | `provenance.chain` should include at least one `source` type entry | WARN |
| QR-031 | If `confidence.score = 0.0`, `confidence.explanation` must contain "unscored" | WARN |
| QR-032 | `evidence` entries should have a non-empty `ref` field | WARN |
| QR-033 | `source` entries should have a non-empty `ref` and `captured_at` | WARN |

## Seal rules

| Rule ID | Condition | Severity |
|---|---|---|
| QR-040 | `seal.hash` must be 71 characters (sha256: prefix + 64 hex chars) | REJECT |
| QR-041 | `seal.sealed_at` must be ≥ `created_at` | WARN |
| QR-042 | If `seal.patch_log` is non-empty, last entry's `new_hash` must match `seal.hash` | REJECT |
| QR-043 | `seal.patch_log` entries must be ordered by `patched_at` ascending | WARN |

## Link rules

| Rule ID | Condition | Severity |
|---|---|---|
| QR-050 | `links[].rel` must be a known edge type | WARN |
| QR-051 | `links[].target` must match `rec_` prefix pattern | REJECT |
| QR-052 | A record should not link to itself | WARN |

## Severity levels

- **REJECT** — record is rejected and not ingested.  The submitting system receives an error.
- **WARN** — record is ingested but flagged for review.  A warning is logged and surfaced in the Coherence Ops audit.
