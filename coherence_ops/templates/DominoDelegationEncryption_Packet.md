# Domino Delegation Encryption — Packet Template

## TS (Truth Snapshot)

| Field | Value |
|---|---|
| **What** | _[What is being protected or unlocked — e.g., "Quarterly authority rotation credentials"]_ |
| **When** | _[Ceremony date/time]_ |
| **Who** | _[List of 7 participants by role]_ |
| **Scope** | _[Program, contract, or decision domain]_ |
| **Session ID** | _[From ceremony JSON: `session_id`]_ |
| **TTL** | _[1 hour from `created_at`; expires at `expires_at`]_ |
| **Chain Fingerprint** | _[From ceremony JSON: `chain_fingerprint`]_ |
| **Domino Name** | _[From ceremony JSON: `domino_fingerprint`]_ |

## ALS (Authority Ledger Slice)

| Field | Value |
|---|---|
| **Threshold** | 4-of-7 (SSS_GF256) |
| **Participant Roles** | _[Role 1, Role 2, ..., Role 7 — from ceremony JSON `participants` array]_ |
| **Keyword Fingerprints** | |
| Keyword 1 | _[`keyword_fingerprints["1"]`]_ |
| Keyword 2 | _[`keyword_fingerprints["2"]`]_ |
| Keyword 3 | _[`keyword_fingerprints["3"]`]_ |
| Keyword 4 | _[`keyword_fingerprints["4"]`]_ |
| Keyword 5 | _[`keyword_fingerprints["5"]`]_ |
| Keyword 6 | _[`keyword_fingerprints["6"]`]_ |
| Keyword 7 | _[`keyword_fingerprints["7"]`]_ |
| **Chain Seal (SHA-256)** | _[`chain_hash`]_ |

## DLR Linkage (Decision Ledger Record)

| Field | Value |
|---|---|
| **Decision Episode ID** | _[DLR episode ID that authorized this delegation ceremony]_ |
| **Reason** | _[Why delegation was needed — e.g., "Key rotation per quarterly governance policy"]_ |
| **Authorizing Entry** | _[Authority ledger entry ID, e.g., AUTH-xxxxxxxx]_ |

## CE (Canon Entry)

| Field | Value |
|---|---|
| **Canon Entry Pointer** | _[CE record ID for the ceremony JSON artifact]_ |
| **Artifact Hash** | _[SHA-256 of the ceremony JSON file]_ |
| **Storage** | _[Where the ceremony JSON is archived — e.g., "evidence pack /ceremonies/2026-03-01/"]_ |

## Justification (Reasoning)

_[1-3 sentences: Why was this ceremony conducted? What decision or authority action required threshold encryption? What is the intended use of the encrypted payload?]_

## Drift Hook

**On TTL expiry:**
- Create a Drift Signal (DS) recording that the ceremony window has closed
- If unlock was not completed before expiry, the delegation is void
- A new ceremony must be conducted to re-establish authority

**Event:** `reops.delegation.ttl_expired`
**Required action:** Log DS, notify ceremony coordinator, archive ceremony JSON as expired
