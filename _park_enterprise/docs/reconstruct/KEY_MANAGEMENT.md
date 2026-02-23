# Key Management

**Version:** 1.0
**Applies to:** All signing operations on sealed governance artifacts.

---

## Core Rule: Never Commit Private Keys

Private keys, shared secrets, and signing credentials must **never** appear in the repository. This is enforced by `.gitignore` entries and CI checks.

---

## Key Storage

| Method | Use Case | How |
|--------|----------|-----|
| Environment variable | CI/CD pipelines | `DEEPSIGMA_SIGNING_KEY` |
| Local `.env` file | Developer workstation | `.env` is gitignored |
| OS keychain | Production systems | macOS Keychain, Linux secret-tool, etc. |
| GitHub Actions secret | Automated signing | Settings > Secrets > `DEEPSIGMA_SIGNING_KEY` |

---

## Key ID Format

Key IDs identify which key was used without revealing the key itself:

```
ds-<environment>-<year>-<month>
```

Examples:
- `ds-dev-2026-01` — Development key, January 2026
- `ds-prod-2026-02` — Production key, February 2026
- `ds-ci-2026-01` — CI pipeline key, January 2026

---

## Algorithm Selection

| Algorithm | Type | When to Use |
|-----------|------|-------------|
| **ed25519** | Public-key | Third-party verification, production signing |
| **hmac-sha256** | Shared key | Internal verification, CI, dev environments |

Ed25519 is preferred because it allows verification with only the public key. HMAC requires the shared secret on both sides.

---

## Key Generation

### Ed25519

```bash
# Requires: pip install pynacl  (or  pip install cryptography)
python -c "
from nacl.signing import SigningKey
import base64
sk = SigningKey.generate()
print('Private:', base64.b64encode(sk.encode()).decode())
print('Public:', base64.b64encode(sk.verify_key.encode()).decode())
"
```

### HMAC-SHA256

```bash
python -c "
import secrets, base64
key = secrets.token_bytes(32)
print('Key:', base64.b64encode(key).decode())
"
```

Store the output in your chosen key storage, never in a file tracked by git.

---

## Key Rotation

| Trigger | Action |
|---------|--------|
| Quarterly schedule | Generate new key, update `signing_key_id`, sign new artifacts with new key |
| Key compromise | Immediately rotate, invalidate old key ID, re-sign any artifacts signed during window |
| Personnel change | Rotate if departing member had access to signing keys |

Old signatures remain valid for historical verification. New artifacts must use the current key.

---

## Verification Without the Private Key

For ed25519-signed artifacts:

```bash
python src/tools/reconstruct/verify_signature.py \
    --file artifacts/sealed_runs/<run>.json \
    --sig artifacts/sealed_runs/<run>.sig.json \
    --public-key <base64-public-key>
```

For hmac-signed artifacts (requires shared key):

```bash
python src/tools/reconstruct/verify_signature.py \
    --file artifacts/sealed_runs/<run>.json \
    --sig artifacts/sealed_runs/<run>.sig.json \
    --key <base64-shared-key>
```

---

## Related

- [docs/reconstruct/ADMISSIBILITY_PACK.md](ADMISSIBILITY_PACK.md) — What a third party needs
- [docs/reconstruct/DETERMINISM_DOCTRINE.md](DETERMINISM_DOCTRINE.md) — Hash scope and determinism rules
- [schemas/reconstruct/signature_block_v1.json](../../schemas/reconstruct/signature_block_v1.json) — Signature schema
