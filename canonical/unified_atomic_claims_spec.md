---
title: "Unified Atomic Claims Specification"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
spec_id: "CLAIM-SPEC-001"
schema_ref: "specs/claim.schema.json"
---

# Unified Atomic Claims Specification

## Purpose

**What:** The `AtomicClaim` is the indivisible unit of asserted truth. Every higher-order structure (DLR, Canon, Drift, Retcon, Patch) is composed of Claims.

**So What:** Without a universal claim primitive, truth is scattered across untyped strings, unversioned assertions, and unlinked evidence. Claims give every assertion an identity, a confidence score, an expiration, evidence links, and a tamper-evident seal.

## Data Model (Required Fields)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `claimId` | string | Yes | Stable identifier. Format: `CLAIM-YYYY-NNNN`. Never reused. |
| `statement` | string | Yes | The human-readable assertion. |
| `scope` | enum | Yes | Domain: `intel`, `recon`, `franchise`, `cross-domain`. |
| `truthType` | enum | Yes | `empirical`, `derived`, `asserted`, `policy`, `inferred`. |
| `confidence` | number | Yes | 0.0-1.0. How much the system trusts this claim. |
| `statusLight` | enum | Yes | `GREEN` (valid), `AMBER` (degrading), `RED` (expired/contradicted). |
| `sources` | array[string] | Yes | URIs or identifiers of originating systems. |
| `evidence` | array[object] | Yes | Each: `{ evidenceId, type, ref, capturedAt, confidence }`. |
| `owner` | string | Yes | Accountable entity (team, agent, system). |
| `timestampCreated` | datetime | Yes | When the claim was first asserted. |
| `version` | integer | Yes | Monotonically increasing. Starts at 1. |
| `halfLife` | object | Yes | `{ value (ms), basis }` — how quickly this claim decays. |
| `seal` | object | Yes | `{ hash (SHA-256), algorithm, sealedAt, sealedBy }`. |
| `tags` | array[string] | No | Free-form labels for filtering. |
| `supersedes` | string | No | `claimId` of the claim this replaces. |
| `links` | array[object] | No | `{ rel, targetId }` — supports, contradicts, derived_from. |

## Validation Rules

1. `claimId` must match pattern `^CLAIM-[0-9]{4}-[0-9]{4,}$`.
2. 2. `confidence` must be in range `[0.0, 1.0]`.
   3. 3. `statusLight` must be one of `GREEN`, `AMBER`, `RED`.
      4. 4. `evidence` array must have at least one item.
         5. 5. `seal.hash` must be a valid SHA-256 hex string (64 characters).
            6. 6. `version` must be >= 1.
               7. 7. `halfLife.value` must be > 0.
                 
                  8. ## Minimal JSON Example
                 
                  9. ```json
                     {
                       "claimId": "CLAIM-2026-0001",
                       "statement": "Account A-1042 has a credit score below 580.",
                       "scope": "franchise",
                       "truthType": "empirical",
                       "confidence": 0.92,
                       "statusLight": "GREEN",
                       "sources": ["credit-bureau-api/v3"],
                       "evidence": [
                         {
                           "evidenceId": "EV-001",
                           "type": "api_response",
                           "ref": "credit-bureau-api/v3/accounts/A-1042",
                           "capturedAt": "2026-02-16T10:30:00Z",
                           "confidence": 0.95
                         }
                       ],
                       "owner": "risk-ops-team",
                       "timestampCreated": "2026-02-16T10:30:05Z",
                       "version": 1,
                       "halfLife": { "value": 86400000, "basis": "credit scores refresh daily" },
                       "seal": {
                         "hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                         "algorithm": "sha256",
                         "sealedAt": "2026-02-16T10:30:06Z",
                         "sealedBy": "coherence-ops/v0.2.0"
                       },
                       "tags": ["credit", "risk", "account-quarantine"],
                       "links": [
                         { "rel": "supports", "targetId": "CLAIM-2026-0002" }
                       ]
                     }
                     ```
