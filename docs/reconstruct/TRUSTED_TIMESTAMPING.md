# Trusted Timestamping

**Version:** 1.0

How DeepSigma proves *when* a governance artifact was created, not just *what* it contains.

---

## Local Transparency Log (Built-in)

The default timestamping method is a repo-committed, append-only NDJSON log at `artifacts/transparency_log/log.ndjson`. Each entry chains to its predecessor via `prev_entry_hash`, making the log tamper-evident.

### How It Works

1. After sealing and signing, the tool appends an entry containing the commit hash, artifact bytes hash, and signing key ID.
2. The entry's `entry_hash` is computed over all fields (with `entry_hash` set to `""` during computation).
3. The `prev_entry_hash` links to the preceding entry, forming an immutable chain.

### Guarantees

- **Ordering:** Entries are strictly ordered by append time.
- **Tamper evidence:** Modifying any entry invalidates its hash and breaks the chain for all successors.
- **No deletion:** Removing an entry creates a gap in the chain that `verify_chain()` detects.

### Limitations

- **Trust anchor:** The log's integrity depends on the git repository. An actor with force-push access could rewrite history.
- **No third-party witness:** The timestamp is self-asserted, not externally verified.

---

## RFC 3161 Timestamping (Future)

For third-party timestamp verification, DeepSigma supports an RFC 3161 TSA hook (not yet implemented):

1. The signing tool sends a hash of the sealed artifact to an external TSA.
2. The TSA returns a signed timestamp token.
3. The token is embedded in the `timestamp_block` of the transparency log entry.

### Recommended TSAs

| Provider | URL | Notes |
|----------|-----|-------|
| FreeTSA | `https://freetsa.org/tsr` | Free, suitable for development |
| DigiCert | (commercial) | Production-grade |
| Sectigo | (commercial) | Production-grade |

Integration path: add `--tsa-url` to `transparency_log_append.py`.

---

## Public Chain Anchor (Future)

For maximum non-repudiation, the commit hash can be anchored to a public blockchain:

1. Compute SHA-256 of the sealed artifact.
2. Submit as an `OP_RETURN` transaction or equivalent.
3. Record the transaction ID in `anchor_tx`.

This provides a timestamp that cannot be backdated by any single party.

---

## Related

- [ADMISSIBILITY_LEVELS.md](ADMISSIBILITY_LEVELS.md) — L3 requires transparency log
- [DETERMINISM_DOCTRINE.md](DETERMINISM_DOCTRINE.md) — Hash scope rules
- [KEY_MANAGEMENT.md](KEY_MANAGEMENT.md) — Signing key management
