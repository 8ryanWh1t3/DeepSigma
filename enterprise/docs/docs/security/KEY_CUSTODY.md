# Signature Key Custody

Key custody lifecycle for `DEEPSIGMA_SIGNING_KEY` used by the authority ledger.

## Generation

```bash
openssl rand -hex 32
```

Produces a 32-byte (256-bit) hex-encoded key. Set as environment variable:

```bash
export DEEPSIGMA_SIGNING_KEY="<generated-hex>"
```

## Storage

| Environment | Mechanism |
|---|---|
| Local dev | Environment variable (`DEEPSIGMA_SIGNING_KEY`) |
| CI (GitHub Actions) | Repository secret `secrets.DEEPSIGMA_SIGNING_KEY` |
| Production (planned) | HSM or YubiKey via PKCS#11 bridge |

The key MUST NOT be committed to source control or logged in CI output.

## Rotation

- **Schedule:** Quarterly (90-day cycle).
- **Dual-read period:** During transition, both the old and new keys are accepted for signature verification. Writers emit signatures using the new key only.
- **Process:**
  1. Generate a new key (`openssl rand -hex 32`).
  2. Deploy the new key alongside the old key (dual-read).
  3. After confirmation that all new entries use the new key, revoke the old key.
  4. Record the rotation in the authority ledger with the new `signing_key_id`.

## Revocation

Record key retirement in the authority ledger:

- Set `signing_key_id` on the ledger entry to identify which key was active.
- Append an `AUTHORIZED_KEY_ROTATION` entry referencing the retired key.
- Remove the old key from all secret stores (env, CI secrets, HSM slots).

## Verification

```bash
python verify_authority_signature.py --key $KEY --message $MSG --signature $SIG
```

Verification re-computes `HMAC-SHA256(canonical_json(message), key)` and compares against the stored signature using constant-time comparison.

## CI Integration

GitHub Actions workflow references the signing key via:

```yaml
env:
  DEEPSIGMA_SIGNING_KEY: ${{ secrets.DEEPSIGMA_SIGNING_KEY }}
```

Set the secret in **Repository Settings > Secrets and variables > Actions**.
