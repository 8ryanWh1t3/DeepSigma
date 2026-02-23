# DISR Security Model

DISR stands for **Breakable -> Detectable -> Rotatable -> Recoverable**.

The intent is practical: assume keys can be compromised, then make compromise
visible, reversible, and measurable under pilot conditions.

## Core controls

- **Breakable:** Keys are treated as disposable. No key is permanent.
- **Detectable:** Misuse signals are machine-detectable and gateable in CI.
- **Rotatable:** Rotation is a first-class operation, not an emergency-only script.
- **Recoverable:** Re-encryption and rollback are rehearsed with deterministic drills.

## Artifacts

- Key lifecycle policy: `docs/docs/security/KEY_LIFECYCLE.md`
- Recovery runbook: `docs/docs/security/RECOVERY_RUNBOOK.md`
- Crypto envelope schema: `schemas/core/crypto_envelope.schema.json`
- Keyring model: `src/deepsigma/security/keyring.py`

## Pilot implementation notes

- Key versions are modeled explicitly (`key_id`, `key_version`, `expires_at`, `status`).
- Envelope metadata must include `key_id`, `key_version`, `alg`, `nonce`, and `aad`.
- Expiry and disable transitions are represented as status changes, not silent mutation.
