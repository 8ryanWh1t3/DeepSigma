# Security

Threats RAL is designed to mitigate:
- stale context (TOCTOU)
- unsafe tool actions (missing idempotency/rollback)
- prompt/tool injection (reduce blast radius with allowlists + HITL)
- uncontrolled fanout and retry storms

Recommended:
- tool allowlists per blast radius tier
- signed policy packs (future)
- strict auth modes for high blast radius actions

## Security Proof Pack v2

The security gate (`make security-gate`) runs an integrity-chain-aware proof pack that checks four areas:

| Check | What it validates |
| --- | --- |
| **Key Lifecycle** | `enterprise/docs/security/KEY_LIFECYCLE.md` documents key generation, rotation, and revocation |
| **Crypto Proof** | `enterprise/scripts/crypto_proof.py` contains `build_proof` and `verify` functions (not placeholder) |
| **Seal Chain** | Credibility packets contain a hash-chained seal with valid chain continuity |
| **Contract Fingerprint** | Schema manifest fingerprint matches the contract fingerprint file |

Outputs:
- `release_kpis/security_proof_pack.json` — structured proof pack with per-check results
- `release_kpis/SECURITY_GATE_REPORT.md` — human-readable gate report

CI enforcement: `.github/workflows/security_gate.yml`
