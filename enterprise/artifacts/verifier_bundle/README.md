# Verifier Bundle

One-command verification of any admissibility pack.

## Usage

```bash
# HMAC-signed pack
python src/tools/reconstruct/verify_pack.py --pack /path/to/pack --key "$KEY"

# Ed25519-signed pack
python src/tools/reconstruct/verify_pack.py --pack /path/to/pack --public-key "$PUB"

# Strict mode (all determinism checks)
python src/tools/reconstruct/verify_pack.py --pack /path/to/pack --key "$KEY" --strict
```

## What It Checks

1. **Replay**: Structural integrity, schema version, authority envelope, hash scope, commit hash, exclusions, merkle commitments, content hash
2. **Signature**: HMAC-SHA256 or Ed25519 cryptographic signature (auto-detected from sig file)
3. **Transparency Log**: Entry existence, entry hash integrity, artifact hash match, chain continuity
4. **Authority Ledger**: Entry existence, hash match, not revoked, scope coverage, temporal validity
5. **Determinism Audit**: hash_scope present, clock fixed, deterministic flag, exclusions, canonical JSON

## Pack Directory Layout

```
pack/
├── RUN-xxxxx_20260221T000000Z.json           # Sealed run
├── RUN-xxxxx_20260221T000000Z.manifest.json   # Manifest
├── RUN-xxxxx_20260221T000000Z.json.sig.json   # Signature
├── RUN-xxxxx_20260221T000000Z.manifest.json.sig.json
├── transparency_log.ndjson                     # Log excerpt
└── authority_ledger.ndjson                     # Authority excerpt
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed |
| 1 | One or more checks failed |
