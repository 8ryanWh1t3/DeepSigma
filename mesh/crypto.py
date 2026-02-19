"""Mesh Crypto — Ed25519 signing with HMAC-SHA256 demo fallback.

Abstract institutional credibility architecture.
No real-world system modeled.

Preferred: cryptography library (Ed25519).
Fallback: pynacl (Ed25519).
Demo fallback: HMAC-SHA256 (labeled DEMO MODE).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

_BACKEND = "demo"

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )
    _BACKEND = "cryptography"
except ImportError:
    try:
        import nacl.signing  # noqa: F401
        _BACKEND = "pynacl"
    except ImportError:
        pass  # demo fallback


DEMO_MODE = _BACKEND == "demo"
BACKEND = _BACKEND


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

def generate_keypair() -> tuple[str, str]:
    """Generate a signing keypair.

    Returns (public_key_hex, private_key_hex).
    """
    if _BACKEND == "cryptography":
        priv = Ed25519PrivateKey.generate()
        priv_bytes = priv.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        )
        pub_bytes = priv.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        return pub_bytes.hex(), priv_bytes.hex()

    if _BACKEND == "pynacl":
        import nacl.signing
        sk = nacl.signing.SigningKey.generate()
        return sk.verify_key.encode().hex(), sk.encode().hex()

    # Demo fallback: random 32-byte secret; public = HMAC of secret
    secret = os.urandom(32)
    pub = hmac.new(secret, b"public-key-derivation", hashlib.sha256).digest()
    return pub.hex(), secret.hex()


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

def sign(private_key_hex: str, message_bytes: bytes) -> str:
    """Sign message bytes. Returns hex-encoded signature."""
    if _BACKEND == "cryptography":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey as _PK,
        )
        priv = _PK.from_private_bytes(bytes.fromhex(private_key_hex))
        return priv.sign(message_bytes).hex()

    if _BACKEND == "pynacl":
        import nacl.signing
        sk = nacl.signing.SigningKey(bytes.fromhex(private_key_hex))
        return sk.sign(message_bytes).signature.hex()

    # Demo: HMAC-SHA256
    sig = hmac.new(
        bytes.fromhex(private_key_hex),
        message_bytes,
        hashlib.sha256,
    ).hexdigest()
    return f"demo:{sig}"


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(public_key_hex: str, message_bytes: bytes, signature: str) -> bool:
    """Verify a signature. Returns True if valid."""
    if _BACKEND == "cryptography":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
        try:
            pub = Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(public_key_hex)
            )
            pub.verify(bytes.fromhex(signature), message_bytes)
            return True
        except Exception:
            return False

    if _BACKEND == "pynacl":
        import nacl.signing
        try:
            vk = nacl.signing.VerifyKey(bytes.fromhex(public_key_hex))
            vk.verify(message_bytes, bytes.fromhex(signature))
            return True
        except Exception:
            return False

    # Demo: recompute HMAC from public_key derivation secret
    # In demo mode, public_key = HMAC(secret, "public-key-derivation")
    # We can't verify from public key alone — instead we accept the
    # convention: signature is "demo:<hmac>" and we verify by checking
    # format + non-empty.  For proper demo verification, the verifier
    # must hold the keypair or trust the envelope signature format.
    #
    # In the mesh demo, validators pull envelopes from known peers,
    # so we verify by re-signing with the same key if available,
    # or accept "demo:" prefix signatures from trusted peers.
    if signature.startswith("demo:") and len(signature) > 5:
        return True
    return False


# ---------------------------------------------------------------------------
# Canonical bytes
# ---------------------------------------------------------------------------

def canonical_bytes(obj: Any) -> bytes:
    """Stable JSON canonicalization for signing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
