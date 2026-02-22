"""Credibility Engine — JSONL Persistence.

Append-only JSONL storage for claims, drift events, snapshots,
correlation clusters, and sync regions.

Supports multi-tenant isolation via tenant_id-scoped data directories.
Backward compatible: omitting tenant_id uses DEFAULT_TENANT_ID.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import warnings
from base64 import b64decode, b64encode
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from credibility_engine.constants import DEFAULT_TENANT_ID

_BASE_DATA_DIR = Path(__file__).parent.parent / "data" / "credibility"
_SAFE_TENANT_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")

_write_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_filename(filename: str) -> str:
    if not _SAFE_FILENAME_RE.fullmatch(filename):
        raise ValueError(f"Invalid filename: {filename}")
    if "/" in filename or "\\" in filename:
        raise ValueError(f"Invalid filename: {filename}")
    return filename


def _validate_tenant_id(tenant_id: str) -> str:
    if not _SAFE_TENANT_RE.fullmatch(tenant_id):
        raise ValueError("Invalid tenant_id")
    return tenant_id


def _tenant_slug(tenant_id: str) -> str:
    tid = _validate_tenant_id(tenant_id)
    return hashlib.sha256(tid.encode("utf-8")).hexdigest()[:16]


def _is_within(base: Path, candidate: Path) -> bool:
    return os.path.commonpath([str(base), str(candidate)]) == str(base)


class CredibilityStore:
    """JSONL file-backed persistence for credibility engine state.

    Tenant-aware: each tenant gets an isolated data directory under
    data/credibility/{tenant_id}/.
    """

    CLAIMS_FILE = "claims.jsonl"
    DRIFT_FILE = "drift.jsonl"
    SNAPSHOTS_FILE = "snapshots.jsonl"
    CORRELATION_FILE = "correlation.jsonl"
    SYNC_FILE = "sync.jsonl"
    PACKET_FILE = "packet_latest.json"

    def __init__(
        self,
        data_dir: str | Path | None = None,
        tenant_id: str | None = None,
        encrypt_at_rest: bool = False,
    ) -> None:
        if data_dir is not None:
            # Explicit data_dir takes precedence (backward compat / testing)
            candidate = Path(data_dir).expanduser().resolve()
            self.data_dir = candidate
        else:
            tid = _tenant_slug(tenant_id or DEFAULT_TENANT_ID)
            base = _BASE_DATA_DIR.resolve()
            candidate = (base / tid).resolve()
            if not _is_within(base, candidate):
                raise ValueError("Invalid tenant_id path")
            self.data_dir = candidate
        self.tenant_id = _validate_tenant_id(tenant_id or DEFAULT_TENANT_ID)
        self.data_dir.mkdir(parents=True, exist_ok=True)  # lgtm [py/path-injection]
        self.encrypt_at_rest = encrypt_at_rest
        self._master_key = os.environ.get("DEEPSIGMA_MASTER_KEY", "")
        self._encryption_enabled = False
        self._aesgcm: Any = None
        if self.encrypt_at_rest:
            self._initialize_encryption()

    def _initialize_encryption(self) -> None:
        if not self._master_key:
            warnings.warn(
                "encrypt_at_rest=True but DEEPSIGMA_MASTER_KEY is unset; "
                "falling back to plaintext persistence",
                RuntimeWarning,
                stacklevel=2,
            )
            return
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore
        except ImportError:
            warnings.warn(
                "encrypt_at_rest=True but cryptography is not installed; "
                "falling back to plaintext persistence",
                RuntimeWarning,
                stacklevel=2,
            )
            return
        key = self._derive_tenant_key(self._master_key)
        self._aesgcm = AESGCM(key)
        self._encryption_enabled = True

    def _derive_tenant_key(self, master_key: str) -> bytes:
        salt = f"deepsigma:{self.tenant_id}".encode("utf-8")
        return hashlib.pbkdf2_hmac(
            "sha256",
            master_key.encode("utf-8"),
            salt,
            200_000,
            dklen=32,
        )

    def _is_encrypted_envelope(self, obj: Any) -> bool:
        return (
            isinstance(obj, dict)
            and "encrypted_payload" in obj
            and "nonce" in obj
        )

    def _encrypt_record(self, record: dict[str, Any]) -> dict[str, Any]:
        if not self._encryption_enabled or self._aesgcm is None:
            return record
        plaintext = json.dumps(record, default=str, separators=(",", ":")).encode("utf-8")
        nonce = os.urandom(12)
        aad = self.tenant_id.encode("utf-8")
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, aad)
        return {
            "enc": "AES-256-GCM",
            "enc_version": 1,
            "tenant_id": self.tenant_id,
            "nonce": b64encode(nonce).decode("utf-8"),
            "encrypted_payload": b64encode(ciphertext).decode("utf-8"),
        }

    def _decrypt_record_with(
        self,
        envelope: dict[str, Any],
        aesgcm: Any,
    ) -> dict[str, Any]:
        nonce = b64decode(envelope["nonce"])
        ciphertext = b64decode(envelope["encrypted_payload"])
        aad = self.tenant_id.encode("utf-8")
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        obj = json.loads(plaintext.decode("utf-8"))
        if isinstance(obj, dict):
            obj.setdefault("tenant_id", self.tenant_id)
        return obj

    def _decode_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        if not self._is_encrypted_envelope(raw):
            raw.setdefault("tenant_id", self.tenant_id)
            return raw
        if not self._encryption_enabled or self._aesgcm is None:
            raise RuntimeError(
                "Encrypted record found but decryption is unavailable. "
                "Set DEEPSIGMA_MASTER_KEY and enable encrypt_at_rest."
            )
        return self._decrypt_record_with(raw, self._aesgcm)

    def _safe_path(self, filename: str) -> Path:
        """Resolve a validated filename under the tenant data directory."""
        safe_name = _validate_filename(filename)
        base = self.data_dir.resolve()
        candidate = (base / safe_name).resolve()
        if not _is_within(base, candidate):
            raise ValueError("Invalid file path")
        if candidate.parent != base:
            raise ValueError("Invalid file path")
        return candidate

    # -- Core operations -------------------------------------------------------

    def append_record(self, filename: str, record: dict[str, Any]) -> None:
        """Append a single JSON record as a line to a JSONL file.

        Injects tenant_id and timestamp if not already present.
        """
        enriched = dict(record)
        enriched.setdefault("tenant_id", self.tenant_id)
        enriched.setdefault("timestamp", _now_iso())
        filepath = self._safe_path(filename)
        serialized = enriched
        if filename != self.PACKET_FILE and self._encryption_enabled:
            serialized = self._encrypt_record(enriched)
        with _write_lock:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(serialized, default=str) + "\n")

    def load_latest(self, filename: str) -> dict[str, Any] | None:
        """Load the last record from a JSONL file."""
        filepath = self._safe_path(filename)
        if not filepath.exists():
            return None
        last_line = None
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if last_line:
            return self._decode_record(json.loads(last_line))
        return None

    def load_last_n(self, filename: str, n: int = 10) -> list[dict[str, Any]]:
        """Load the last N records from a JSONL file."""
        filepath = self._safe_path(filename)
        if not filepath.exists():
            return []
        lines: list[str] = []
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
        records = [self._decode_record(json.loads(line)) for line in lines[-n:]]
        return records

    def load_all(self, filename: str) -> list[dict[str, Any]]:
        """Load all records from a JSONL file."""
        filepath = self._safe_path(filename)
        if not filepath.exists():
            return []
        records = []
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(self._decode_record(json.loads(stripped)))
        return records

    def write_json(self, filename: str, data: dict[str, Any]) -> None:
        """Write a single JSON file (non-JSONL, for packets)."""
        enriched = dict(data)
        enriched.setdefault("tenant_id", self.tenant_id)
        serialized = enriched
        if filename != self.PACKET_FILE and self._encryption_enabled:
            serialized = self._encrypt_record(enriched)
        filepath = self._safe_path(filename)
        with _write_lock:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2, default=str)
                f.write("\n")

    def load_json(self, filename: str) -> dict[str, Any] | None:
        """Load a single JSON file."""
        filepath = self._safe_path(filename)
        if not filepath.exists():
            return None
        with open(filepath, encoding="utf-8") as f:
            record = json.load(f)
        if isinstance(record, dict):
            record = self._decode_record(record)
        return record

    def write_batch(self, filename: str, records: list[dict[str, Any]]) -> None:
        """Overwrite a JSONL file with a complete batch of records.

        Use for current-state data (claims, clusters, sync) where the full
        set is written at once. Injects tenant_id and timestamp if missing.
        """
        filepath = self._safe_path(filename)
        with _write_lock:
            with open(filepath, "w", encoding="utf-8") as f:
                for record in records:
                    enriched = dict(record)
                    enriched.setdefault("tenant_id", self.tenant_id)
                    enriched.setdefault("timestamp", _now_iso())
                    serialized = enriched
                    if filename != self.PACKET_FILE and self._encryption_enabled:
                        serialized = self._encrypt_record(enriched)
                    f.write(json.dumps(serialized, default=str) + "\n")

    # -- Convenience methods ---------------------------------------------------

    def save_claims(self, claim_dicts: list[dict[str, Any]]) -> None:
        """Overwrite claims file with full current state."""
        self.write_batch(self.CLAIMS_FILE, claim_dicts)

    def save_clusters(self, cluster_dicts: list[dict[str, Any]]) -> None:
        """Overwrite correlation file with full current state."""
        self.write_batch(self.CORRELATION_FILE, cluster_dicts)

    def save_sync(self, sync_dicts: list[dict[str, Any]]) -> None:
        """Overwrite sync file with full current state."""
        self.write_batch(self.SYNC_FILE, sync_dicts)

    def append_claim(self, claim_dict: dict[str, Any]) -> None:
        self.append_record(self.CLAIMS_FILE, claim_dict)

    def append_drift(self, drift_dict: dict[str, Any]) -> None:
        self.append_record(self.DRIFT_FILE, drift_dict)

    def append_snapshot(self, snapshot_dict: dict[str, Any]) -> None:
        self.append_record(self.SNAPSHOTS_FILE, snapshot_dict)

    def append_correlation(self, cluster_dict: dict[str, Any]) -> None:
        self.append_record(self.CORRELATION_FILE, cluster_dict)

    def append_sync(self, sync_dict: dict[str, Any]) -> None:
        self.append_record(self.SYNC_FILE, sync_dict)

    def save_packet(self, packet: dict[str, Any]) -> None:
        self.write_json(self.PACKET_FILE, packet)

    def latest_snapshot(self) -> dict[str, Any] | None:
        return self.load_latest(self.SNAPSHOTS_FILE)

    def latest_claims(self) -> list[dict[str, Any]]:
        """Load all current claim records."""
        return self.load_all(self.CLAIMS_FILE)

    def latest_clusters(self) -> list[dict[str, Any]]:
        """Load all current correlation clusters."""
        return self.load_all(self.CORRELATION_FILE)

    def latest_sync(self) -> list[dict[str, Any]]:
        """Load all current sync regions."""
        return self.load_all(self.SYNC_FILE)

    def drift_last_24h(self, n: int = 500) -> list[dict[str, Any]]:
        """Load recent drift events."""
        return self.load_last_n(self.DRIFT_FILE, n)

    def latest_packet(self) -> dict[str, Any] | None:
        return self.load_json(self.PACKET_FILE)

    # -- Tier file access (warm/cold) -----------------------------------------

    def _tier_path(self, filename: str, tier: str) -> Path:
        """Build path for a tiered file (e.g. claims-warm.jsonl)."""
        if tier not in {"warm", "cold"}:
            raise ValueError(f"Invalid tier: {tier}")
        safe_filename = _validate_filename(filename)
        stem = safe_filename.replace(".jsonl", "")
        return self._safe_path(f"{stem}-{tier}.jsonl")

    def load_warm(self, filename: str) -> list[dict[str, Any]]:
        """Load all records from the warm-tier file."""
        path = self._tier_path(filename, "warm")
        if not path.exists():
            return []
        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(self._decode_record(json.loads(stripped)))
        return records

    def load_cold(self, filename: str) -> list[dict[str, Any]]:
        """Load all records from the cold-tier file."""
        path = self._tier_path(filename, "cold")
        if not path.exists():
            return []
        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(self._decode_record(json.loads(stripped)))
        return records

    def write_warm(self, filename: str, records: list[dict[str, Any]]) -> None:
        """Write records to the warm-tier file."""
        path = self._tier_path(filename, "warm")
        if not records:
            if path.exists():
                path.unlink()
            return
        with _write_lock:
            with open(path, "w", encoding="utf-8") as f:
                for record in records:
                    enriched = dict(record)
                    enriched.setdefault("tenant_id", self.tenant_id)
                    serialized = enriched
                    if self._encryption_enabled:
                        serialized = self._encrypt_record(enriched)
                    f.write(json.dumps(serialized, default=str) + "\n")

    def write_cold(self, filename: str, records: list[dict[str, Any]]) -> None:
        """Write records to the cold-tier file."""
        path = self._tier_path(filename, "cold")
        if not records:
            if path.exists():
                path.unlink()
            return
        with _write_lock:
            with open(path, "w", encoding="utf-8") as f:
                for record in records:
                    enriched = dict(record)
                    enriched.setdefault("tenant_id", self.tenant_id)
                    serialized = enriched
                    if self._encryption_enabled:
                        serialized = self._encrypt_record(enriched)
                    f.write(json.dumps(serialized, default=str) + "\n")

    def rekey(self, previous_master_key: str) -> dict[str, int]:
        """Re-encrypt tenant records with the current DEEPSIGMA_MASTER_KEY.

        Sealed packet artifacts are intentionally left plaintext.
        """
        if not self.encrypt_at_rest:
            raise RuntimeError("Rekey requires encrypt_at_rest=True")
        if not self._master_key or not self._encryption_enabled:
            raise RuntimeError(
                "Rekey requires DEEPSIGMA_MASTER_KEY and cryptography support"
            )
        if not previous_master_key:
            raise RuntimeError("previous_master_key is required")

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore
        except ImportError as exc:
            raise RuntimeError("cryptography is required for rekey") from exc

        old_aes = AESGCM(self._derive_tenant_key(previous_master_key))
        stats = {"files": 0, "records": 0}
        for path in sorted(self.data_dir.glob("*")):
            if path.is_dir():
                continue
            if path.name == self.PACKET_FILE:
                continue
            if path.suffix == ".jsonl":
                lines = path.read_text(encoding="utf-8").splitlines()
                rewritten: list[str] = []
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    raw = json.loads(stripped)
                    if self._is_encrypted_envelope(raw):
                        record = self._decrypt_record_with(raw, old_aes)
                    else:
                        record = raw
                        record.setdefault("tenant_id", self.tenant_id)
                    rewritten.append(json.dumps(self._encrypt_record(record), default=str))
                    stats["records"] += 1
                with _write_lock:
                    path.write_text("\n".join(rewritten) + ("\n" if rewritten else ""), encoding="utf-8")
                stats["files"] += 1
            elif path.suffix == ".json":
                raw = json.loads(path.read_text(encoding="utf-8"))
                if self._is_encrypted_envelope(raw):
                    record = self._decrypt_record_with(raw, old_aes)
                else:
                    record = raw
                with _write_lock:
                    path.write_text(json.dumps(self._encrypt_record(record), indent=2) + "\n", encoding="utf-8")
                stats["files"] += 1
                stats["records"] += 1
        return stats
