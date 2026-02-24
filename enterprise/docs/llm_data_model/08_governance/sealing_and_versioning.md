# Sealing and Versioning

How records are sealed, how versions are tracked, and how patches work.

## Seal lifecycle

1. **Record created** — all fields populated, `seal.version = 1`.
2. **Hash computed** — SHA-256 of the canonical JSON (fields sorted alphabetically, no whitespace).  Stored as `seal.hash = "sha256:<hex>"`.
3. **Timestamp applied** — `seal.sealed_at` set to current UTC time.
4. **Record sealed** — after this point, the `content`, `provenance`, `confidence`, `labels`, `links`, and `source` fields are immutable.

## What can change after sealing

Only the `seal.patch_log` array can be appended.  A patch does not modify the original record — it adds a correction or annotation.

| Field | Mutable after seal? | Notes |
|---|---|---|
| `record_id` | No | Permanent identity |
| `record_type` | No | Fixed at creation |
| `created_at` | No | Historical fact |
| `observed_at` | No | Historical fact |
| `source` | No | Origin is immutable |
| `provenance` | No | Evidence chain is sealed |
| `confidence` | No | Original assessment preserved |
| `ttl` | No | Original TTL preserved (patches can note revised TTL) |
| `labels` | No | Classification is sealed |
| `links` | No | Graph edges are sealed (new edges create new records) |
| `content` | No | Payload is sealed |
| `seal.hash` | Updated on patch | New hash reflects the patched state |
| `seal.sealed_at` | No | Original seal time preserved |
| `seal.version` | Incremented on patch | Monotonically increasing |
| `seal.patch_log` | Append-only | New patches are added to the array |

## Patch structure

Each patch entry records:

```json
{
  "patched_at": "2026-02-13T09:00:00Z",
  "author": "auditor-jane",
  "reason": "Corrected confidence after manual review",
  "new_hash": "sha256:a1b2c3d4..."
}
```

The `new_hash` is computed over the original record plus all patches up to and including this one.  This creates a hash chain: each patch depends on all previous patches.

## Version numbering

- `seal.version` starts at 1 when the record is first sealed.
- Each patch increments the version by 1.
- Consumers should check `seal.version` to detect whether a record has been patched.
- Version is monotonically increasing — gaps are not allowed.

## Hash verification

To verify a record's integrity:

1. Serialize the record (excluding `seal.hash`, `seal.patch_log`, and `seal.version`) to canonical JSON.
2. Compute SHA-256 of the serialized string.
3. Compare against `seal.hash` (for version 1) or the last `patch_log[].new_hash`.

## Supersedes vs. Patches

| Mechanism | When to use | Result |
|---|---|---|
| **Patch** (append to `seal.patch_log`) | Minor correction to an existing record (confidence adjustment, metadata fix) | Same record_id, incremented version |
| **Supersede** (new record with `supersedes` link) | Major revision — new version of a policy, updated entity snapshot | New record_id, `links: [{rel: "supersedes", target: "<old_record_id>"}]` |

## Immutability guarantee

Once sealed, no system component may modify the original fields.  The ingestion API enforces this at the write layer.  Any attempt to update a sealed record (other than appending to `patch_log`) returns HTTP 409 Conflict.
