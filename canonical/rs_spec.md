---
title: "RS — Reflection Session Specification"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
spec_id: "RS-SPEC-001"
triad_mapping: "Reasoning + Memory"
---

# RS — Reflection Session

## Purpose

**What:** A Reflection Session aggregates one or more sealed DecisionEpisodes into a structured learning summary. It captures what happened, what degraded, what diverged from expectation, and what the institution should learn.

**So What:** Individual episodes are forensic records. RS is the "after-action review" — it converts raw experience into institutional learning. Without RS, the system makes the same mistakes repeatedly because there is no structured feedback path from outcomes to policy.

## Data Model (Required Fields)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sessionId` | string | Yes | Unique identifier. Format: `RS-<uuid>` or `RS-<sequential>`. |
| `createdAt` | datetime | Yes | When this session was generated. |
| `episodeIds` | array[string] | Yes | Which sealed episodes were analyzed. |
| `summary` | string | Yes | Human-readable summary of what happened. |
| `degradations` | array[object] | Yes | Each: `{ episodeId, fromStep, toStep, reason }`. |
| `divergences` | array[object] | Yes | Each: `{ episodeId, expected, actual, severity }`. |
| `learnings` | array[string] | Yes | Actionable insights extracted from this batch. |
| `recommendedPatches` | array[object] | No | Each: `{ targetArtifact, patchType, description }`. |
| `coherenceScore` | object | No | `{ overall, truth, reasoning, memory }`. |
| `seal` | object | No | Tamper-evident seal of this RS record. |

## Validation Rules

1. `episodeIds` must have at least one entry.
2. 2. `degradations[].fromStep` and `toStep` must be valid degrade ladder steps.
   3. 3. `divergences[].severity` must be one of: `low`, `medium`, `high`, `critical`.
      4. 4. `learnings` must have at least one entry.
        
         5. ## Minimal JSON Example
        
         6. ```json
            {
              "sessionId": "RS-001",
              "createdAt": "2026-02-16T11:00:00Z",
              "episodeIds": ["ep-001", "ep-002", "ep-003"],
              "summary": "3 AccountQuarantine decisions processed. 1 required freshness degradation. 2 completed on ideal path. Verification passed on all 3.",
              "degradations": [
                {
                  "episodeId": "ep-002",
                  "fromStep": "ideal",
                  "toStep": "cache_bundle",
                  "reason": "credit_score feature exceeded TTL (stale by 4200ms)"
                }
              ],
              "divergences": [
                {
                  "episodeId": "ep-002",
                  "expected": "ideal_path_completion",
                  "actual": "cache_bundle_fallback",
                  "severity": "medium"
                }
              ],
              "learnings": [
                "credit_score TTL of 30s is too aggressive for batch windows; consider 60s",
                "All 3 verifications passed — current postcondition checks are effective"
              ],
              "recommendedPatches": [
                {
                  "targetArtifact": "DTE:AccountQuarantine",
                  "patchType": "ttl_change",
                  "description": "Increase credit_score TTL from 30000ms to 60000ms for batch context"
                }
              ]
            }
            ```
