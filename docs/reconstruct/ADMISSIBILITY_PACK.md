# Admissibility Pack

**Version:** 1.0

What a third party needs to verify a sealed governance artifact without live system access.

---

## Required Files

| File | Purpose |
|------|---------|
| `<run_id>_<timestamp>.json` | The sealed run (immutable artifact) |
| `<run_id>_<timestamp>.manifest.json` | Manifest with commit hash, hash scope, row counts |
| `<run_id>_<timestamp>.json.sig.json` | Cryptographic signature of the sealed run |
| `<run_id>_<timestamp>.manifest.json.sig.json` | Cryptographic signature of the manifest |
| Public key (ed25519) or verification key procedure (hmac) | Needed to verify signatures |
| `schemas/reconstruct/sealed_run_v1.json` | Schema for structural validation |
| `schemas/reconstruct/signature_block_v1.json` | Schema for signature validation |

---

## Verification Procedure

### Step 1: Verify Signature

```bash
# Ed25519 (public key)
python src/tools/reconstruct/verify_signature.py \
    --file <sealed_run>.json \
    --public-key <base64-public-key>

# HMAC (shared key)
python src/tools/reconstruct/verify_signature.py \
    --file <sealed_run>.json \
    --key <base64-shared-key>
```

**Expected:** `RESULT: SIGNATURE VALID`

### Step 2: Replay Sealed Run

```bash
python src/tools/reconstruct/replay_sealed_run.py \
    --sealed <sealed_run>.json \
    --verify-signature true \
    --key <key>
```

**Expected:** `RESULT: REPLAY PASS`

### Step 3: Interpret Results

| Result | Meaning |
|--------|---------|
| `REPLAY PASS` + `SIGNATURE VALID` | Artifact is **admissible** — structurally valid, deterministically reproducible, and cryptographically signed |
| `REPLAY PASS` + no signature | Artifact is structurally valid but **unsigned** — integrity verified, authenticity not confirmed |
| `INADMISSIBLE` | Artifact fails structural or hash verification — **reject** |
| `SIGNATURE INVALID` | Signature does not match artifact — artifact may have been **tampered** |

---

## What the Replay Tool Checks

1. **Structural integrity** — All required keys present in sealed run and authority envelope
2. **Schema version** — Matches expected version
3. **Authority envelope** — Actor, authority type, scope, policy, refusal, enforcement, provenance all valid
4. **Hash scope** — Deterministic hash scope manifest present and correctly structured
5. **Commit hash** — Recomputed from embedded hash_scope, must match recorded value
6. **Provenance match** — Commit hash matches `provenance.deterministic_inputs_hash`
7. **Exclusion rules** — `observed_at` correctly excluded from hash scope
8. **Content hash** — Full artifact hash verified via canonical serialization
9. **Signature** (if requested) — Cryptographic signature verified against artifact bytes

---

## What the Signature Verifier Checks

1. **Payload bytes hash** — SHA-256 of canonical JSON bytes matches recorded value
2. **Commit hash match** — Commit hash in signature matches commit hash in artifact
3. **Cryptographic signature** — HMAC-SHA256 or Ed25519 signature verified

---

## Failure Conditions

| Code | Meaning |
|------|---------|
| Exit 0 | ADMISSIBLE — all checks passed |
| Exit 1 | INADMISSIBLE — structural or logical failure |
| Exit 2 | Schema failure — missing required keys |
| Exit 3 | Hash mismatch — commit hash or content hash tampered |
| Exit 4 | Missing file — referenced input file not found (strict mode) |

---

## Algorithm Guidance

| Use Case | Recommended Algorithm |
|----------|----------------------|
| Third-party audit | Ed25519 (public-key verification) |
| Internal CI/CD | HMAC-SHA256 (simpler key management) |
| Production signing | Ed25519 with key rotation |
| Development/testing | HMAC-SHA256 with ephemeral keys |

---

## Related

- [docs/reconstruct/KEY_MANAGEMENT.md](KEY_MANAGEMENT.md) — Key storage and rotation
- [docs/reconstruct/DETERMINISM_DOCTRINE.md](DETERMINISM_DOCTRINE.md) — Hash scope and determinism rules
- [docs/reconstruct/ADVERSARIAL_REPLAY_GUIDE.md](ADVERSARIAL_REPLAY_GUIDE.md) — Full replay procedure
- [schemas/reconstruct/signature_block_v1.json](../../schemas/reconstruct/signature_block_v1.json) — Signature schema
- [schemas/reconstruct/sealed_run_v1.json](../../schemas/reconstruct/sealed_run_v1.json) — Sealed run schema
