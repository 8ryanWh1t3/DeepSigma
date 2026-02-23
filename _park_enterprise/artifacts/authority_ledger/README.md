# Authority Ledger

Append-only, tamper-evident ledger of authority grants, delegations, and revocations.

## Format

`ledger.ndjson` is a newline-delimited JSON (NDJSON) file. Each line is a self-contained JSON object conforming to `schemas/reconstruct/authority_ledger_entry_v1.json`.

## Chaining

Each entry contains a `prev_entry_hash` field linking to the preceding entry's `entry_hash`. This creates a hash chain: modifying or deleting any entry invalidates all subsequent entries.

The first entry has `prev_entry_hash: null`.

## Revocation

Revocations are appended as new entries with `grant_type: "revocation"` and `revoked_at` set. The original grant entry is never modified.

## Verification

```bash
python src/tools/reconstruct/authority_ledger_verify.py \
    --ledger-path artifacts/authority_ledger/ledger.ndjson
```

## Append

```bash
python src/tools/reconstruct/authority_ledger_append.py \
    --ledger-path artifacts/authority_ledger/ledger.ndjson \
    --authority-id GOV-2.1 \
    --actor-id alice \
    --actor-role Operator \
    --grant-type direct \
    --scope '{"decisions":["*"],"claims":[],"patches":[],"prompts":[],"datasets":[]}' \
    --policy-version GOV-2.0.2 \
    --policy-hash sha256:... \
    --effective-at 2026-02-21T00:00:00Z
```
