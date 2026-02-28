"""Encryption-at-rest for sealed episodes and audit logs.

Provides file-level encryption using Fernet (AES-128-CBC + HMAC-SHA256)
from the ``cryptography`` library. Falls back to a no-op wrapper when
the library is not installed, logging a warning on first use.

Key management:
    - Key is read from DEEPSIGMA_ENCRYPTION_KEY env var (base64-encoded Fernet key)
    - Or loaded from a key file via DEEPSIGMA_ENCRYPTION_KEY_FILE
    - generate_key() produces a new Fernet key for bootstrapping

Usage:
    from governance.encryption import FileEncryptor

    enc = FileEncryptor()
    enc.encrypt_file(Path("data/audit/tenant-alpha/audit.jsonl"))
    # Produces data/audit/tenant-alpha/audit.jsonl.enc

    plaintext = enc.decrypt_file(Path("data/audit/tenant-alpha/audit.jsonl.enc"))
"""
from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def generate_key() -> str:
    """Generate a new Fernet key (base64-encoded)."""
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography package required: pip install cryptography")
    return Fernet.generate_key().decode("ascii")


class FileEncryptor:
    """Encrypt and decrypt files at rest using Fernet symmetric encryption.

    Reads the encryption key from environment or an explicit argument.
    When no key is available, operations are no-ops with a warning.
    """

    def __init__(self, key: Optional[str] = None) -> None:
        self._fernet = None
        resolved_key = key or self._load_key_from_env()
        if resolved_key and HAS_CRYPTO:
            self._fernet = Fernet(resolved_key.encode("ascii") if isinstance(resolved_key, str) else resolved_key)
        elif not HAS_CRYPTO:
            logger.warning("cryptography package not installed; encryption disabled")
        elif not resolved_key:
            logger.warning("No encryption key configured; encryption disabled")

    @staticmethod
    def _load_key_from_env() -> Optional[str]:
        key = os.environ.get("DEEPSIGMA_ENCRYPTION_KEY")
        if key:
            return key
        key_file = os.environ.get("DEEPSIGMA_ENCRYPTION_KEY_FILE")
        if key_file:
            p = Path(key_file)
            if p.is_file():
                return p.read_text().strip()
        return None

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt_file(self, path: Path, out_path: Optional[Path] = None) -> Path:
        """Encrypt a file, writing to ``<path>.enc`` by default.

        Returns the path to the encrypted file.
        """
        target = out_path or path.with_suffix(path.suffix + ".enc")
        if not self._fernet:
            logger.warning("Encryption disabled; copying %s unencrypted", path.name)
            target.write_bytes(path.read_bytes())
            return target

        plaintext = path.read_bytes()
        ciphertext = self._fernet.encrypt(plaintext)
        target.write_bytes(ciphertext)
        logger.info("Encrypted %s → %s (%d bytes)", path.name, target.name, len(ciphertext))
        return target

    def decrypt_file(self, path: Path) -> bytes:
        """Decrypt a ``.enc`` file and return the plaintext bytes."""
        if not self._fernet:
            logger.warning("Encryption disabled; reading %s as plaintext", path.name)
            return path.read_bytes()

        ciphertext = path.read_bytes()
        return self._fernet.decrypt(ciphertext)

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt raw bytes. Returns ciphertext (or passthrough if disabled)."""
        if not self._fernet:
            return data
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        """Decrypt raw bytes. Returns plaintext (or passthrough if disabled)."""
        if not self._fernet:
            return data
        return self._fernet.decrypt(data)
