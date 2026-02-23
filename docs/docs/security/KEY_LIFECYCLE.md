# Key Lifecycle

This document defines pilot-safe key lifecycle behavior for DISR.

## States

- `active`: usable for new encryption operations
- `disabled`: administratively disabled; no new encryption
- `expired`: TTL exceeded; no new encryption

## Required fields

Every key version record must include:

- `key_id`
- `key_version`
- `created_at`
- `expires_at` (nullable)
- `status`

## Rotation cadence (pilot)

- Normal cadence: rotate every 14 days.
- Emergency cadence: rotate immediately upon compromise signal.
- Re-encryption follows rotation when historical data must remain decryptable.

## Operational expectations

- Rotation increments `key_version` monotonically per `key_id`.
- New writes use the current active version.
- Expired keys are not silently reused.
