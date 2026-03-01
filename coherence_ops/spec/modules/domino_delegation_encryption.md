# Module Spec: Domino Delegation Encryption

## Purpose

Provides a verifiable, threshold-based encryption ceremony for high-stakes custody decisions. Seven participants coordinate via physical domino tiles (co-presence proof), receive Shamir keyword shares, and can later reconstruct the encryption key with a 4-of-7 quorum.

**Core concept: Public Record / Private Power.** The ceremony JSON is a fully auditable public record (chain, seal, fingerprints, TTL, session identity). The encryption capability (keywords + passphrase) remains distributed across participants and is never recorded.

## Threat Model Summary

| Threat | Mitigation |
|---|---|
| Single point of compromise | 4-of-7 threshold — no single keyword reveals information |
| Remote impersonation | Physical domino chain proves sequential co-presence |
| Stale credentials | 1-hour TTL auto-expires keywords |
| Offline brute force | HKDF key derivation with strong passphrase requirement |
| Data exfiltration | EDGE hardening: no network, no persistence, no external deps |
| Ceremony forgery | SHA-256 chain seal + keyword fingerprints for independent verification |

## Triad Mapping

### Truth
- **Chain seal** (SHA-256 of tile sequence) is the atomic truth unit
- **Ceremony JSON** captures the complete verifiable state
- **Keyword fingerprints** prove keyword-to-ceremony binding without revealing secrets

### Reasoning
- **Threshold selection** (4-of-7) balances availability vs security
- **Passphrase + keywords** dual-factor ensures no single vector unlocks
- **TTL enforcement** bounds the decision window

### Memory
- **Ceremony JSON** is the persistent memory artifact (archivable, verifiable)
- **Keywords are ephemeral** — exist only in human memory or physical custody
- **Session ID** links the ceremony to downstream decisions

## Events Mapping

### ReOps (Reconnaissance Operations)
| Event | Trigger | Payload |
|---|---|---|
| `reops.delegation.ceremony_initiated` | Self-test passes, chain sealed | `{session_id, chain_fingerprint, participant_count, timestamp}` |
| `reops.delegation.keywords_generated` | Keywords created | `{session_id, n, t, ttl_ms, created_at, expires_at}` |
| `reops.delegation.ttl_expired` | TTL countdown reaches zero | `{session_id, expired_at}` |

### FranOps (Framework Operations)
| Event | Trigger | Payload |
|---|---|---|
| `franops.delegation.quorum_reached` | 4+ valid keywords entered | `{session_id, valid_count, threshold}` |
| `franops.delegation.message_locked` | Plaintext encrypted | `{session_id, ciphertext_length}` |
| `franops.delegation.message_unlocked` | Ciphertext decrypted | `{session_id, plaintext_length}` |

### IntelOps (Intelligence Operations)
| Event | Trigger | Payload |
|---|---|---|
| `intelops.delegation.ceremony_verified` | Verifier confirms record | `{session_id, chain_fingerprint, all_checks_passed}` |
| `intelops.delegation.fingerprint_mismatch` | Keyword fails fingerprint check | `{session_id, slot_index, expected_fp}` |
| `intelops.delegation.seal_tampered` | Chain hash mismatch on verification | `{session_id, expected_hash, computed_hash}` |

## Artifact Links

| Artifact | Location | Links To |
|---|---|---|
| Ceremony JSON | Exported from EDGE tool | DLR (decision context), CE (canon record) |
| Keyword fingerprints (in JSON) | `keyword_fingerprints` field | ALS (authority participant proof) |
| Session ID | `session_id` field | DLR episode linkage |
| Chain seal | `chain_hash` field | CE integrity anchor |
| TTL window | `created_at` / `expires_at` | DLR time-bounded authority |

## EDGE Artifacts

| Edition | File | Capabilities |
|---|---|---|
| Enterprise | `enterprise/edge/EDGE_Domino_Delegation_Encryption.html` | Full ceremony + encrypt/decrypt |
| Core | `core/edge/EDGE_Domino_Delegation_Encryption_Verifier.html` | Verification only (read-only) |
