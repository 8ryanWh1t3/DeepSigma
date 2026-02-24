---
title: "DS — Drift Signal Specification"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
spec_id: "DS-SPEC-001"
schema_ref: "specs/drift.schema.json"
triad_mapping: "Truth (decaying)"
---

# DS — Drift Signal

## Purpose

**What:** A Drift Signal is a structured record of a detected anomaly in the decision process. It captures what drifted, how badly, what evidence triggered detection, and what corrective action is recommended.

**So What:** Without Drift Signals, degradation is invisible. The system quietly makes worse decisions as context goes stale, policies become outdated, and timing assumptions break. DS makes drift visible, typed, fingerprinted, and actionable — turning silent failure into a self-correcting loop.

## Drift Type Definitions

| Type | Trigger | Example |
|------|---------|---------|
| `time` | Decision exceeded DTE deadline | P99 spike caused 3200ms in a 2000ms envelope |
| `freshness` | Claim exceeded TTL | credit_score was 4200ms stale |
| `fallback` | System fell to lower degrade step | Ideal path unavailable; used cache_bundle |
| `bypass` | Required gate skipped | Action executed without verification |
| `verify` | Post-condition check failed | Read-after-write showed stale value |
| `outcome` | Actual outcome diverged from expected | Quarantine succeeded but alert failed |
| `fanout` | Excessive hop count | 8 hops where limit is 5 |
| `contention` | Resource contention | Lock wait exceeded 500ms |

## Data Model (Required Fields)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `driftId` | string | Yes | Unique identifier for this drift event. |
| `episodeId` | string | Yes | The sealed episode that produced this drift. |
| `driftType` | enum | Yes | `time`, `freshness`, `fallback`, `bypass`, `verify`, `outcome`, `fanout`, `contention`. |
| `severity` | enum | Yes | `green` (info), `yellow` (warning), `red` (critical). |
| `detectedAt` | datetime | Yes | When the drift was detected. |
| `evidenceRefs` | array[string] | Yes | References to triggering evidence. |
| `recommendedPatchType` | enum | Yes | `dte_change`, `ttl_change`, `cache_bundle_change`, `routing_change`, `verification_change`, `action_scope_tighten`, `manual_review`. |
| `fingerprint` | object | Yes | `{ key, version }` — stable identifier for recurrence tracking. |
| `notes` | string | No | Human-readable context. |

## Validation Rules

1. `driftType` must be one of the 8 defined enums.
2. 2. `severity` must be one of `green`, `yellow`, `red`.
   3. 3. `evidenceRefs` must have at least one entry.
      4. 4. `fingerprint.key` and `fingerprint.version` must be non-empty strings.
         5. 5. `recommendedPatchType` must be one of the 7 defined enums.
            6. 6. `detectedAt` must be a valid ISO-8601 datetime.
              
               7. ## Minimal JSON Example
              
               8. ```json
                  {
                    "driftId": "drift-007",
                    "episodeId": "ep-002",
                    "driftType": "freshness",
                    "severity": "red",
                    "detectedAt": "2026-02-16T10:31:30Z",
                    "evidenceRefs": ["feature:credit_score:capturedAt=2026-02-16T10:30:56Z"],
                    "recommendedPatchType": "ttl_change",
                    "fingerprint": {
                      "key": "freshness/ttl-breach-credit-score",
                      "version": "1"
                    },
                    "notes": "credit_score feature was 4200ms past TTL. Third occurrence in 24h window."
                  }
                  ```
