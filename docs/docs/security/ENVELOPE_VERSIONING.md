# Envelope Versioning Plan

This document defines the migration path for cryptographic envelope schema versions.

## Current state

- `envelope_version_current`: `1.0`
- `envelope_versions_supported`: `["1.0"]`
- Source of truth: `governance/security_crypto_policy.json`

## Migration strategy to v2

- Strategy: **dual-read, single-write**
- Writers must emit `envelope_version_current`.
- Readers may accept any value in `envelope_versions_supported`.

## v2 rollout sequence

1. Add `2.0` to `envelope_versions_supported` while keeping current at `1.0`.
2. Ship readers that can decode both `1.0` and `2.0`.
3. Flip `envelope_version_current` to `2.0` for new writes.
4. Retire `1.0` from supported versions after re-encryption and validation.

## CI and runtime enforcement

- `scripts/crypto_misuse_scan.py` fails on unsupported envelope versions.
- Runtime write path rejects envelope metadata that violates provider/algorithm/version policy.
