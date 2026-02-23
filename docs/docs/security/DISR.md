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
- 10-minute demo: `docs/docs/security/DEMO_10_MIN.md`
- Crypto envelope schema: `schemas/core/crypto_envelope.schema.json`
- Keyring model: `src/deepsigma/security/keyring.py`

## Pilot implementation notes

- Key versions are modeled explicitly (`key_id`, `key_version`, `expires_at`, `status`).
- Default provider is `local-keystore` (file-backed) with deterministic storage at `local_keystore.json`.
- Envelope v1 metadata includes `key_id`, `key_version`, `provider`, `alg`, `nonce`, `aad`, `created_at`, and `expires_at`.
- Expiry and disable transitions are represented as status changes, not silent mutation.

## Optional cloud provider stubs

Cloud KMS providers are registered as stubs only:

- `aws-kms`
- `gcp-kms`
- `azure-kv`

These stubs intentionally fail closed until you implement deployment-specific adapters.
Do not commit credentials or cloud client configs in repo. Inject runtime auth through your
deployment environment and replace stub internals in private integration layers.
