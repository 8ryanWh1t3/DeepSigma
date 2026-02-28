"""JRM Packet Validator — verify packet signatures."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict

from .signer import PacketSigner


class PacketValidator:
    """Validate JRM-X packet signatures."""

    def __init__(self, key: str | bytes) -> None:
        self._signer = PacketSigner(key)

    def validate(self, packet_path: str | Path) -> bool:
        """Validate packet manifest signature."""
        packet_path = Path(packet_path)
        try:
            with zipfile.ZipFile(packet_path, "r") as zf:
                manifest = json.loads(zf.read("manifest.json"))
                signature = manifest.get("signature")
                if not signature:
                    return False
                # Remove signature before verifying
                manifest_copy = {k: v for k, v in manifest.items() if k != "signature"}
                return self._signer.verify(manifest_copy, signature)
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError):
            return False
