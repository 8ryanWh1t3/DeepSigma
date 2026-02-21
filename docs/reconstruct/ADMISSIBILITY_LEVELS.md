# Admissibility Levels

**Version:** 1.0

Defines tiers of admissibility assurance for sealed governance artifacts. Each level builds on the previous — a higher level implies all lower requirements are met.

---

## Levels

| Level | Name | Requirements | Threat Model |
|-------|------|-------------|--------------|
| **L0** | Audit Clean | Sealed run passes structural replay (all required keys present, schema valid) | Accidental corruption, incomplete records |
| **L1** | Deterministic Replay | L0 + deterministic commit hash verified (same inputs + clock = same hash) | Unintentional data drift, non-reproducible outputs |
| **L2** | Signed Artifacts | L1 + cryptographic signature (HMAC-SHA256 or Ed25519) on sealed run and manifest | Unauthorized modification, impersonation |
| **L3** | Transparency Log | L2 + artifact registered in tamper-evident transparency log with chained entry hashes | Post-hoc deletion, silent replacement of artifacts |
| **L4** | Witness / Multi-Signature | L3 + threshold multi-signature (e.g. 2-of-3) with distinct roles (operator, witness) | Single-actor fraud, collusion below threshold |
| **L5** | Selective Disclosure | L4 + Merkle commitment roots embedded in sealed run (prove inclusion without revealing full dataset) | Forced full disclosure, privacy violations |
| **L6** | Hardware-Backed Keys | L5 + signing keys stored in hardware (YubiKey, HSM, KMS) with attestation | Key extraction, software-level key compromise |

---

## Verification Commands by Level

| Level | Verification |
|-------|-------------|
| L0 | `python src/tools/reconstruct/replay_sealed_run.py --sealed <path>` |
| L1 | L0 command (commit hash verified automatically when `hash_scope` present) |
| L2 | `replay_sealed_run.py --sealed <path> --verify-signature true --key <key>` |
| L3 | L2 + `--verify-transparency true --transparency-log <log_path>` |
| L4 | L3 + `--require-multisig 2` |
| L5 | L4 (commitment roots verified automatically when `inputs_commitments` present) |
| L6 | L5 with hardware-backed key (signature block shows `signer_type: hardware`) |

---

## Component Mapping

| Component | Introduced At | Schema | Tool |
|-----------|--------------|--------|------|
| Sealed Run | L0 | `sealed_run_v1.json` | `seal_bundle.py` |
| Authority Envelope | L0 | `authority_envelope_v1.json` | `seal_bundle.py` |
| Hash Scope + Commit Hash | L1 | `hash_scope_v1.json` | `seal_bundle.py` |
| Signature Block | L2 | `signature_block_v1.json` | `sign_artifact.py` |
| Transparency Log Entry | L3 | `transparency_log_entry_v1.json` | `transparency_log_append.py` |
| Multi-Signature Block | L4 | `multisig_block_v1.json` | `verify_multisig.py` |
| Merkle Commitments | L5 | `merkle_commitment_v1.json` | `build_commitments.py` |
| Hardware Key Attestation | L6 | (extension of `signature_block_v1.json`) | `sign_artifact.py --external-signer-cmd` |

---

## Admissibility Pack Contents by Level

| File | L0 | L1 | L2 | L3 | L4 | L5 | L6 |
|------|----|----|----|----|----|----|-----|
| Sealed run JSON | X | X | X | X | X | X | X |
| Manifest JSON | X | X | X | X | X | X | X |
| Signature `.sig.json` | | | X | X | X | X | X |
| Transparency log entry | | | | X | X | X | X |
| Multi-sig envelope | | | | | X | X | X |
| Commitment roots | | | | | | X | X |
| Replay instructions | X | X | X | X | X | X | X |

---

## Related

- [ADMISSIBILITY_PACK.md](ADMISSIBILITY_PACK.md) — Third-party verification procedure
- [DETERMINISM_DOCTRINE.md](DETERMINISM_DOCTRINE.md) — Hash scope and determinism rules
- [KEY_MANAGEMENT.md](KEY_MANAGEMENT.md) — Key storage and rotation
