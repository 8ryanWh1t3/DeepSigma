# Transparency Log

Append-only, tamper-evident log of sealed governance artifacts.

## Format

`log.ndjson` is a newline-delimited JSON (NDJSON) file. Each line is a self-contained JSON object conforming to `schemas/reconstruct/transparency_log_entry_v1.json`.

## Chaining

Each entry contains a `prev_entry_hash` field linking to the preceding entry's `entry_hash`. This creates a hash chain: modifying or deleting any entry invalidates all subsequent entries.

The first entry has `prev_entry_hash: null`.

## Verification

```bash
python src/tools/reconstruct/transparency_log_append.py \
    --log-path artifacts/transparency_log/log.ndjson \
    --verify-only
```

## Append

```bash
python src/tools/reconstruct/transparency_log_append.py \
    --log-path artifacts/transparency_log/log.ndjson \
    --run-id RUN-abc12345 \
    --commit-hash sha256:... \
    --sealed-hash sha256:...
```
