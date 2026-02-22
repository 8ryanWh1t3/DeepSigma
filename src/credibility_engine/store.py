"""Credibility Engine — JSONL Persistence.

Append-only JSONL storage for claims, drift events, snapshots,
correlation clusters, and sync regions.

Supports multi-tenant isolation via tenant_id-scoped data directories.
Backward compatible: omitting tenant_id uses DEFAULT_TENANT_ID.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import json
import re
import threading
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
    ) -> None:
        if data_dir is not None:
            # Explicit data_dir takes precedence (backward compat / testing)
            candidate = Path(data_dir).expanduser().resolve()
            self.data_dir = candidate
        else:
            tid = _validate_tenant_id(tenant_id or DEFAULT_TENANT_ID)
            self.data_dir = _BASE_DATA_DIR / tid
        self.tenant_id = _validate_tenant_id(tenant_id or DEFAULT_TENANT_ID)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # -- Core operations -------------------------------------------------------

    def append_record(self, filename: str, record: dict[str, Any]) -> None:
        """Append a single JSON record as a line to a JSONL file.

        Injects tenant_id and timestamp if not already present.
        """
        enriched = dict(record)
        enriched.setdefault("tenant_id", self.tenant_id)
        enriched.setdefault("timestamp", _now_iso())
        filepath = self.data_dir / _validate_filename(filename)
        with _write_lock:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(enriched, default=str) + "\n")

    def load_latest(self, filename: str) -> dict[str, Any] | None:
        """Load the last record from a JSONL file."""
        filepath = self.data_dir / _validate_filename(filename)
        if not filepath.exists():
            return None
        last_line = None
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if last_line:
            record = json.loads(last_line)
            record.setdefault("tenant_id", self.tenant_id)
            return record
        return None

    def load_last_n(self, filename: str, n: int = 10) -> list[dict[str, Any]]:
        """Load the last N records from a JSONL file."""
        filepath = self.data_dir / _validate_filename(filename)
        if not filepath.exists():
            return []
        lines: list[str] = []
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
        records = [json.loads(line) for line in lines[-n:]]
        for r in records:
            r.setdefault("tenant_id", self.tenant_id)
        return records

    def load_all(self, filename: str) -> list[dict[str, Any]]:
        """Load all records from a JSONL file."""
        filepath = self.data_dir / _validate_filename(filename)
        if not filepath.exists():
            return []
        records = []
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    record = json.loads(stripped)
                    record.setdefault("tenant_id", self.tenant_id)
                    records.append(record)
        return records

    def write_json(self, filename: str, data: dict[str, Any]) -> None:
        """Write a single JSON file (non-JSONL, for packets)."""
        enriched = dict(data)
        enriched.setdefault("tenant_id", self.tenant_id)
        filepath = self.data_dir / _validate_filename(filename)
        with _write_lock:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(enriched, f, indent=2, default=str)
                f.write("\n")

    def load_json(self, filename: str) -> dict[str, Any] | None:
        """Load a single JSON file."""
        filepath = self.data_dir / _validate_filename(filename)
        if not filepath.exists():
            return None
        with open(filepath, encoding="utf-8") as f:
            record = json.load(f)
        if isinstance(record, dict):
            record.setdefault("tenant_id", self.tenant_id)
        return record

    def write_batch(self, filename: str, records: list[dict[str, Any]]) -> None:
        """Overwrite a JSONL file with a complete batch of records.

        Use for current-state data (claims, clusters, sync) where the full
        set is written at once. Injects tenant_id and timestamp if missing.
        """
        filepath = self.data_dir / _validate_filename(filename)
        with _write_lock:
            with open(filepath, "w", encoding="utf-8") as f:
                for record in records:
                    enriched = dict(record)
                    enriched.setdefault("tenant_id", self.tenant_id)
                    enriched.setdefault("timestamp", _now_iso())
                    f.write(json.dumps(enriched, default=str) + "\n")

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
        safe_filename = _validate_filename(filename)
        stem = safe_filename.replace(".jsonl", "")
        return self.data_dir / f"{stem}-{tier}.jsonl"

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
                    record = json.loads(stripped)
                    record.setdefault("tenant_id", self.tenant_id)
                    records.append(record)
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
                    record = json.loads(stripped)
                    record.setdefault("tenant_id", self.tenant_id)
                    records.append(record)
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
                    f.write(json.dumps(enriched, default=str) + "\n")

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
                    f.write(json.dumps(enriched, default=str) + "\n")
