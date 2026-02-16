---
title: "Sealing Protocol"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# Sealing Protocol

## What is Sealing?

Sealing computes a cryptographic hash over a completed DecisionEpisode, marking it as immutable. Once sealed, the episode cannot be modified — only superseded via a versioned patch.

## When to Seal

An episode is sealed when all four phases complete: Gather (claims collected), Reason (degrade step chosen), Act (action dispatched or abstain recorded), Verify (post-condition checked).

## Seal Computation

Input: canonical JSON of the episode (excluding the seal object itself). Method: SHA-256 hash of UTF-8 encoded canonical JSON. Output: 64-character hex string.

Canonical JSON rules for deterministic hashing:
1. Keys sorted alphabetically at every nesting level
2. 2. No whitespace (compact representation)
   3. 3. Unicode normalized (NFC)
      4. 4. Null values excluded
         5. 5. The seal field itself is excluded from the hash input
           
            6. ## Seal Object
           
            7. ```json
               {
                 "hash": "<sha256-hex-64-chars>",
                 "algorithm": "sha256",
                 "sealedAt": "<ISO-8601 datetime>",
                 "sealedBy": "<system/version>",
                 "version": 1
               }
               ```

               ## Versioning via Patch

               Sealed episodes are immutable. To record a correction:

               1. Create a new version with version: N+1
               2. 2. Add a patch_log entry with patchedAt, patchedBy, reason, patchId, fieldsChanged
                  3. 3. Recompute the seal hash over the updated episode
                     4. 4. Old version remains in MG with SUPERSEDED_BY edge to new version
                       
                        5. ## Tamper Detection
                       
                        6. If the computed hash does not match seal.hash, the episode is tampered or corrupted. A verify drift signal is emitted automatically and the episode is flagged in MG with integrity: compromised.
