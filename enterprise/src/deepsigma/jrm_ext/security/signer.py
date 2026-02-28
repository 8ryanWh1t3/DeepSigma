"""JRM Packet Signer — HMAC-SHA256 manifest signing (pluggable)."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict


class PacketSigner:
    """Sign JRM-X packet manifests using HMAC-SHA256.

    Pluggable: subclass and override ``sign`` for KMS-backed signatures.
    """

    def __init__(self, key: str | bytes) -> None:
        self._key = key.encode("utf-8") if isinstance(key, str) else key

    def sign(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Sign a manifest dict.  Returns signature object."""
        canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        sig = hmac.new(self._key, canonical, hashlib.sha256).hexdigest()
        return {
            "algorithm": "hmac-sha256",
            "value": sig,
            "signerId": "local",
        }

    def verify(self, manifest: Dict[str, Any], signature: Dict[str, Any]) -> bool:
        """Verify a manifest signature."""
        expected = self.sign(manifest)
        return hmac.compare_digest(expected["value"], signature.get("value", ""))
