# Admissibility Pack V1

**Version:** 1.3 (Court-Grade)

Complete verification bundle for third-party audit without live system access. Extends the [base pack](ADMISSIBILITY_PACK.md) with transparency log, multi-signature witness, merkle commitments, and determinism audit.

---

## Pack Contents

| File | Purpose | Level |
|------|---------|-------|
| `<run_id>_<ts>.json` | Sealed run (immutable artifact) | L0 |
| `<run_id>_<ts>.manifest.json` | Manifest with hash scope and row counts | L0 |
| `<run_id>_<ts>.json.sig.json` | Signature (single or multisig envelope) | L2 |
| `<run_id>_<ts>.manifest.json.sig.json` | Manifest signature | L2 |
| `transparency_log.ndjson` | Append-only transparency log excerpt | L3 |
| Public key or shared key procedure | For signature verification | L2 |

### Referenced Schemas

| Schema | Purpose |
|--------|---------|
| `schemas/reconstruct/sealed_run_v1.json` | Sealed run structure |
| `schemas/reconstruct/signature_block_v1.json` | Signature block format |
| `schemas/reconstruct/multisig_block_v1.json` | Multi-signature envelope |
| `schemas/reconstruct/merkle_commitment_v1.json` | Merkle commitment roots |
| `schemas/reconstruct/transparency_log_entry_v1.json` | Log entry format |

---

## Verification Procedure

### Step 1: Replay (Structural + Hash Integrity)

```bash
python src/tools/reconstruct/replay_sealed_run.py \
    --sealed <sealed_run>.json
```

Checks: structure, schema version, authority envelope, hash scope, commit hash, exclusions, merkle commitments (auto-detected), content hash.

### Step 2: Verify Signature

```bash
# Single signature (HMAC)
python src/tools/reconstruct/replay_sealed_run.py \
    --sealed <sealed_run>.json \
    --verify-signature true \
    --key <base64-shared-key>

# Multi-signature (threshold=2)
python src/tools/reconstruct/replay_sealed_run.py \
    --sealed <sealed_run>.json \
    --verify-signature true \
    --key <base64-shared-key> \
    --require-multisig 2
```

### Step 3: Verify Transparency Log

```bash
python src/tools/reconstruct/replay_sealed_run.py \
    --sealed <sealed_run>.json \
    --verify-transparency true \
    --transparency-log transparency_log.ndjson
```

Checks: entry exists for commit_hash, entry hash integrity, artifact bytes hash matches, chain link integrity.

### Step 4: Verify Log Chain Integrity

```bash
python src/tools/reconstruct/transparency_log_append.py \
    --log-path transparency_log.ndjson \
    --verify-only
```

### Step 5: Determinism Audit

```bash
python src/tools/reconstruct/determinism_audit.py \
    --sealed <sealed_run>.json \
    --strict
```

Checks: hash_scope present, clock fixed, deterministic flag, exclusions, run_id deterministic, no UUIDs, committed_at matches clock, merkle commitments present, canonical JSON valid.

### Step 6: Full Pipeline Verification (All-in-One)

```bash
python src/tools/reconstruct/replay_sealed_run.py \
    --sealed <sealed_run>.json \
    --verify-signature true \
    --key <key> \
    --verify-transparency true \
    --transparency-log transparency_log.ndjson \
    --require-multisig 2
```

---

## Admissibility Level Mapping

| Level | Name | What It Proves | Required Artifacts |
|-------|------|----------------|-------------------|
| L0 | Audit Clean | Structural integrity | Sealed run, manifest |
| L1 | Deterministic | Reproducible output | + hash_scope, commit_hash |
| L2 | Signed | Authenticity | + signature files |
| L3 | Logged | Tamper-evident record | + transparency log |
| L4 | Committed | Merkle-bound | + inputs_commitments |
| L5 | Witnessed | Multi-party attestation | + multisig envelope |
| L6 | Hardware-Backed | Key attestation | + signer_type: hardware |

See [ADMISSIBILITY_LEVELS.md](ADMISSIBILITY_LEVELS.md) for full definitions.

---

## Generating a Pack

```bash
python src/tools/reconstruct/seal_and_prove.py \
    --decision-id DEC-001 \
    --clock 2026-02-21T00:00:00Z \
    --sign-algo hmac \
    --sign-key-id ds-dev-2026-02 \
    --sign-key "$DEEPSIGMA_SIGNING_KEY" \
    --pack-dir /path/to/admissibility-pack
```

---

## Related

- [ADMISSIBILITY_PACK.md](ADMISSIBILITY_PACK.md) — Base pack spec (v1.0-v1.2)
- [ADMISSIBILITY_LEVELS.md](ADMISSIBILITY_LEVELS.md) — Level definitions
- [TRUSTED_TIMESTAMPING.md](TRUSTED_TIMESTAMPING.md) — Transparency log details
- [HARDWARE_BACKED_KEYS.md](HARDWARE_BACKED_KEYS.md) — Hardware key support
- [DETERMINISM_PROFILE.md](DETERMINISM_PROFILE.md) — Determinism rules
