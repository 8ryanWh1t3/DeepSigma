---
title: "DLR — Decision Log Record Specification"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
spec_id: "DLR-SPEC-001"
schema_ref: "specs/dlr.schema.json"
triad_mapping: "Truth + Reasoning"
---

# DLR — Decision Log Record

## Purpose

**What:** A DLR is the "truth receipt" for a single decision. It records which claims governed the decision, which policy (DTE) applied, what action was taken, whether verification passed, and what the outcome was.

**So What:** Without DLRs, you can log that a decision happened, but you cannot prove *what was believed to be true* at that moment or *which policy was followed*. DLRs are the bridge between Truth and Reasoning — they make decisions forensically reconstructable.

## Data Model (Required Fields)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dlrId` | string | Yes | Deterministic ID. Format: `DLR-<sha256-prefix-12+>`. |
| `episodeId` | string | Yes | The sealed DecisionEpisode this DLR was extracted from. |
| `decisionType` | string | Yes | The decision class (e.g., `AccountQuarantine`). |
| `recordedAt` | datetime | Yes | When this DLR was created. |
| `claims` | array[object] | Yes | Each: `{ claimId, role, snapshotConfidence, snapshotStatus, capturedAt }`. |
| `rationaleGraph` | array[object] | Yes | Edges: `{ from (claimId), to (claimId), rel }`. |
| `dteRef` | object | Yes | `{ decisionType, version }`. Which DTE governed this decision. |
| `outcome` | object | Yes | `{ code, verificationPassed, notes }`. |
| `seal` | object | Yes | `{ hash, algorithm, sealedAt }`. |
| `actionSummary` | object | No | What action was taken. |
| `degradeStep` | object | No | If degraded: `{ step, rationale }`. |
| `policyStamp` | object | No | `{ policyPackId, version, hash }`. |

## Validation Rules

1. `dlrId` must match `^DLR-[a-f0-9]{12,}$`.
2. 2. `claims` array must have at least one item.
   3. 3. Each claim must include `claimId`, `role`, and `capturedAt`.
      4. 4. `rationaleGraph` edges must reference `claimId` values present in `claims`.
         5. 5. `outcome.code` must be one of: `success`, `partial`, `fail`, `abstain`, `bypassed`.
            6. 6. `seal.hash` must be valid SHA-256.
              
               7. ## Minimal JSON Example
              
               8. ```json
                  {
                    "dlrId": "DLR-a1b2c3d4e5f6",
                    "episodeId": "ep-001",
                    "decisionType": "AccountQuarantine",
                    "recordedAt": "2026-02-16T10:31:00Z",
                    "claims": [
                      {
                        "claimId": "CLAIM-2026-0001",
                        "role": "primary_trigger",
                        "snapshotConfidence": 0.92,
                        "snapshotStatus": "GREEN",
                        "capturedAt": "2026-02-16T10:30:00Z"
                      }
                    ],
                    "rationaleGraph": [
                      { "from": "CLAIM-2026-0001", "to": "CLAIM-2026-0002", "rel": "supports" }
                    ],
                    "dteRef": { "decisionType": "AccountQuarantine", "version": "2.1" },
                    "outcome": {
                      "code": "success",
                      "verificationPassed": true,
                      "notes": "Account quarantined; read-after-write confirmed."
                    },
                    "seal": {
                      "hash": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
                      "algorithm": "sha256",
                      "sealedAt": "2026-02-16T10:31:01Z"
                    }
                  }
                  ```
