# Recovery Runbook (Pilot)

This runbook describes recovery steps after key compromise in a DISR posture.

## Objective

Recover encrypted evidence integrity with auditable steps and bounded downtime.

## Procedure

1. Freeze writes for affected scope.
2. Disable compromised key version.
3. Create and activate a new key version.
4. Re-encrypt evidence from old key -> new key (dry-run first).
5. Validate readability and integrity.
6. Resume writes.

## Outputs

- Rotation event with key lineage
- Re-encryption summary (records processed, failures, retries)
- Recovery timestamp and owner attribution

## Rollback

If re-encryption validation fails:

1. Halt processing.
2. Restore from the latest verified checkpoint.
3. Re-run with reduced batch size and diagnostics enabled.
