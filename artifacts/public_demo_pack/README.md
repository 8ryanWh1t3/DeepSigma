# Public Demo Pack

This pack was generated with a **publicly-known demo key** to demonstrate
the full admissibility verification pipeline. The key is intentionally
public — it proves pipeline correctness, not secrecy.

**Demo Key (base64):** `ZGVlcHNpZ21hLXB1YmxpYy1kZW1vLWtleS0yMDI2IQ==`

**Fixed Clock:** `2026-02-21T00:00:00Z`

**Decision:** `DEC-001`

## Verify

```bash
python src/tools/reconstruct/verify_pack.py --pack artifacts/public_demo_pack --key "ZGVlcHNpZ21hLXB1YmxpYy1kZW1vLWtleS0yMDI2IQ=="
```
