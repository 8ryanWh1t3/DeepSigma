# Hardware-Backed Keys

> Admissibility Level L6 — hardware-backed key attestation.

## Overview

DeepSigma's signing infrastructure supports three key storage models:

| Type | `signer_type` | Key Storage | Example |
|------|---------------|-------------|---------|
| Software | `software` | In-memory / env var | HMAC shared secret, Ed25519 seed |
| Hardware | `hardware` | HSM, YubiKey, TPM | PKCS#11 slot, PIV applet |
| External | `external` | Remote KMS or CLI tool | AWS KMS, GCP Cloud HSM, custom CLI |

## External Signer Protocol

When `--external-signer-cmd` is provided, `sign_artifact.py` delegates signing to an external process:

1. **Input**: The canonical JSON bytes SHA-256 hash is written to a temp file.
2. **Invocation**: The command is called with the temp file path as the sole argument.
3. **Output**: The command prints the base64-encoded signature to stdout (single line).
4. **Exit code**: 0 = success, non-zero = failure.

### Example: YubiKey PIV

```bash
python src/tools/reconstruct/sign_artifact.py \
    --file artifacts/sealed_runs/RUN-abc12345_20260221T000000Z.json \
    --algo ed25519 \
    --key-id ds-hw-2026-02 \
    --external-signer-cmd "yubico-piv-tool -a verify-pin -a sign --algorithm ECCP256" \
    --witness "operator-1" \
    --role operator
```

### Example: AWS KMS

```bash
# Wrapper script: sign_with_kms.sh
#!/bin/bash
HASH_FILE="$1"
HASH=$(cat "$HASH_FILE")
aws kms sign \
    --key-id alias/deepsigma-signing \
    --message "$HASH" \
    --message-type RAW \
    --signing-algorithm ECDSA_SHA_256 \
    --output text --query Signature

# Usage:
python src/tools/reconstruct/sign_artifact.py \
    --file artifacts/sealed_runs/RUN-abc12345_20260221T000000Z.json \
    --algo ed25519 \
    --key-id ds-kms-2026-02 \
    --external-signer-cmd "./sign_with_kms.sh" \
    --witness "kms-signer" \
    --role operator
```

### Example: Custom HSM CLI

```bash
python src/tools/reconstruct/sign_artifact.py \
    --file artifacts/sealed_runs/RUN-abc12345_20260221T000000Z.json \
    --algo ed25519 \
    --key-id ds-hsm-2026-02 \
    --external-signer-cmd "/usr/local/bin/hsm-sign --slot 1" \
    --witness "hsm-operator" \
    --role operator
```

## External Signer Contract

The external command MUST:

1. Accept a single argument: path to a temp file containing the hex-encoded SHA-256 hash of the canonical JSON bytes.
2. Print exactly one line to stdout: the base64-encoded signature.
3. Exit with code 0 on success, non-zero on failure.
4. Print any error messages to stderr (not stdout).

The external command SHOULD:

1. Not modify any files in the sealed run directory.
2. Complete within 30 seconds.
3. Support idempotent re-invocation (same input → same output for deterministic signers).

## Key Attestation (Future)

Hardware key attestation provides cryptographic proof that a signing key lives in tamper-resistant hardware. This is planned for a future version:

- **YubiKey**: PIV attestation certificate chain
- **TPM 2.0**: `tpm2_certify` output
- **Cloud HSM**: KMS key metadata + audit log

Attestation will be stored as an optional `key_attestation` field in the signature block.

## Signature Block Fields

When using hardware or external signers, the signature block includes:

```json
{
  "signer_type": "hardware",
  "signing_key_id": "ds-hw-2026-02",
  "signer_id": "operator-1",
  "role": "operator",
  "algorithm": "ed25519"
}
```

The `signer_type` field distinguishes software-only keys from hardware-backed keys, enabling auditors to verify the security level of each signature in a multi-signature envelope.

## Integration with Admissibility Levels

| Level | Requirement |
|-------|-------------|
| L0-L4 | Software keys sufficient |
| L5 | At least one witness signature recommended |
| L6 | At least one `signer_type: "hardware"` or `"external"` signature required |

See [ADMISSIBILITY_LEVELS.md](ADMISSIBILITY_LEVELS.md) for full tier definitions.
