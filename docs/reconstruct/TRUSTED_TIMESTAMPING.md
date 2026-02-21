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

## Log Head Anchoring

A daily or per-session `LOG_HEAD.json` captures the current state of the transparency log:

```json
{
  "head_version": "1.0",
  "entry_count": 42,
  "latest_entry_id": "LOG-abc12345",
  "latest_entry_hash": "sha256:...",
  "chain_head_hash": "sha256:...",
  "generated_at": "2026-02-21T00:00:00Z"
}
```

The `chain_head_hash` is the SHA-256 of the full log content. By recording this periodically (or anchoring it externally), you can prove the log state at a given point in time.

Generate with:
```bash
python src/tools/reconstruct/transparency_log_head.py \
    --log-path artifacts/transparency_log/log.ndjson
```

---

## Three-Tier Timestamping Strategy

| Tier | Method | Trust Level | Implementation |
|------|--------|-------------|----------------|
| **Baseline** | Transparency log | Self-asserted, tamper-evident | Built-in (v2.0.2+) |
| **Stronger** | RFC 3161 TSA | Third-party witnessed | Interface defined (see [RFC3161_TIMESTAMPING.md](RFC3161_TIMESTAMPING.md)) |
| **Strongest** | Public chain anchor | Globally witnessed, immutable | Future (OP_RETURN or equivalent) |

Each tier builds on the previous. The transparency log provides ordering and tamper evidence; TSA adds independent time witness; public anchoring makes backdating computationally infeasible.

---

## RFC 3161 Timestamping (Interface Defined)

For third-party timestamp verification, DeepSigma defines an RFC 3161 TSA integration interface:

1. The signing tool sends a hash of the sealed artifact to an external TSA.
2. The TSA returns a signed timestamp token.
3. The token is stored in `tsa_response_b64` and referenced from the transparency log entry.

See [RFC3161_TIMESTAMPING.md](RFC3161_TIMESTAMPING.md) for the full interface specification, recommended providers, and verification procedure.

Integration path: add `--tsa-url` to `transparency_log_append.py` and `seal_and_prove.py`.

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
