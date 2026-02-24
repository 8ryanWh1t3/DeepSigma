# RFC 3161 Timestamping

**Version:** 1.0 (Interface Spec)
**Status:** Not yet implemented — defines the integration interface for future TSA support.

---

## Overview

RFC 3161 defines a protocol for trusted timestamping via a Time-Stamp Authority (TSA). A client sends a hash of a document; the TSA returns a signed timestamp token proving the document existed at that time.

DeepSigma will support RFC 3161 as an optional timestamping layer above the built-in transparency log.

---

## Protocol Flow

```
1. Client computes SHA-256 of sealed artifact
2. Client sends TimeStampReq to TSA URL
3. TSA returns signed TimeStampResp
4. Client stores base64(TimeStampResp) in timestamp_block.tsa_response_b64
5. Client records TSA URL in timestamp_block.tsa_url
```

---

## CLI Interface (Future)

```bash
# During seal_and_prove:
python src/tools/reconstruct/seal_and_prove.py \
    --decision-id DEC-001 \
    --clock 2026-02-21T00:00:00Z \
    --sign-algo hmac --sign-key-id ds-dev --sign-key "$KEY" \
    --tsa-url https://freetsa.org/tsr

# Standalone timestamp:
python src/tools/reconstruct/transparency_log_append.py \
    --log-path artifacts/transparency_log/log.ndjson \
    --tsa-url https://freetsa.org/tsr \
    <other args>
```

---

## Storage Format

TSA responses are stored alongside the transparency log entry:

```
artifacts/transparency_log/
├── log.ndjson                          # Transparency log
└── timestamps/
    └── <entry_id>.tsa.json             # RFC 3161 response
```

Each `.tsa.json` file:

```json
{
  "tsa_version": "1.0",
  "tsa_url": "https://freetsa.org/tsr",
  "tsa_response_b64": "<base64-encoded TimeStampResp>",
  "payload_bytes_sha256": "sha256:...",
  "requested_at": "2026-02-21T00:00:00Z"
}
```

---

## Recommended Providers

| Provider | URL | Cost | Notes |
|----------|-----|------|-------|
| FreeTSA | `https://freetsa.org/tsr` | Free | Good for dev/testing |
| DigiCert | Commercial | Paid | Production-grade, high availability |
| Sectigo | Commercial | Paid | Production-grade, widely trusted |
| GlobalSign | Commercial | Paid | eIDAS-qualified timestamps |

---

## Verification

To verify an RFC 3161 timestamp:

1. Decode the `tsa_response_b64` field
2. Extract the `MessageImprint` hash from the TimeStampToken
3. Compare against `payload_bytes_sha256`
4. Verify the TSA's signature chain against a trusted root

```bash
# Using openssl (future CLI integration):
openssl ts -verify -in response.tsr -data sealed_run.json -CAfile tsa_chain.pem
```

---

## Three-Tier Timestamping Strategy

| Tier | Method | Trust Level | Implementation |
|------|--------|-------------|----------------|
| **Baseline** | Transparency log | Self-asserted, tamper-evident | Built-in (v2.0.2+) |
| **Stronger** | RFC 3161 TSA | Third-party witnessed | Interface defined, not yet implemented |
| **Strongest** | Public chain anchor | Globally witnessed, immutable | Future (OP_RETURN or equivalent) |

Each tier builds on the previous. The transparency log provides ordering and tamper evidence; TSA adds independent time witness; public anchoring makes backdating computationally infeasible.

---

## Related

- [TRUSTED_TIMESTAMPING.md](TRUSTED_TIMESTAMPING.md) — Timestamp strategy overview
- [ADMISSIBILITY_LEVELS.md](ADMISSIBILITY_LEVELS.md) — L3 requires transparency log
- [timestamp_block_v1.json](../../schemas/reconstruct/timestamp_block_v1.json) — Schema
