"""Connector Contract v1.0 — standard interface + canonical Record Envelope.

Defines the protocol all connectors must satisfy and the RecordEnvelope
dataclass used to wrap raw source data with provenance, hashes, and metadata.

Usage::

    from adapters.contract import ConnectorV1, RecordEnvelope, validate_envelope

    # Validate an envelope dict against the schema
    errors = validate_envelope(envelope_dict)

    # Build an envelope programmatically
    env = RecordEnvelope(
        source="sharepoint",
        source_instance="contoso.sharepoint.com",
        record_id="rec-001",
        record_type="Document",
        raw={"title": "Policy v3"},
    )
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import jsonschema

# ── Schema path ──────────────────────────────────────────────────────────────

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "core"
_ENVELOPE_SCHEMA_PATH = _SCHEMA_DIR / "connector_envelope.schema.json"
_ENVELOPE_SCHEMA: Optional[Dict[str, Any]] = None


def _load_schema() -> Dict[str, Any]:
    global _ENVELOPE_SCHEMA
    if _ENVELOPE_SCHEMA is None:
        _ENVELOPE_SCHEMA = json.loads(_ENVELOPE_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _ENVELOPE_SCHEMA


# ── Protocol ─────────────────────────────────────────────────────────────────


@runtime_checkable
class ConnectorV1(Protocol):
    """Standard connector interface (v1.0).

    All source connectors should implement this protocol. Methods raise
    ``NotImplementedError`` by default so connectors can opt into the
    subset they support.
    """

    @property
    def source_name(self) -> str:
        """Canonical source identifier (e.g. ``"sharepoint"``)."""
        ...

    def list_records(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """List canonical records from the source."""
        ...

    def get_record(self, record_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Get a single canonical record by ID."""
        ...

    def to_envelopes(self, records: List[Dict[str, Any]]) -> List["RecordEnvelope"]:
        """Convert canonical records to standardized envelopes."""
        ...


# ── RecordEnvelope ───────────────────────────────────────────────────────────


@dataclass
class RecordEnvelope:
    """Standardized record envelope for all connectors.

    Wraps raw source data with provenance, hashes, and access control tags.
    """

    envelope_version: str = "1.0"
    source: str = ""
    source_instance: str = ""
    collected_at: str = ""
    record_id: str = ""
    record_type: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    hashes: Dict[str, str] = field(default_factory=dict)
    acl_tags: List[str] = field(default_factory=list)
    raw: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.collected_at:
            self.collected_at = datetime.now(timezone.utc).isoformat()
        if self.raw is not None and "raw_sha256" not in self.hashes:
            self.hashes["raw_sha256"] = compute_hash(self.raw)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict (JSON-safe)."""
        return {
            "envelope_version": self.envelope_version,
            "source": self.source,
            "source_instance": self.source_instance,
            "collected_at": self.collected_at,
            "record_id": self.record_id,
            "record_type": self.record_type,
            "provenance": self.provenance,
            "hashes": self.hashes,
            "acl_tags": self.acl_tags,
            "raw": self.raw,
            "metadata": self.metadata,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────


def compute_hash(data: Any) -> str:
    """Deterministic SHA-256 of *data*.

    Strings are encoded directly. Everything else is JSON-serialized
    with sorted keys before hashing.
    """
    if isinstance(data, str):
        return hashlib.sha256(data.encode()).hexdigest()
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def validate_envelope(envelope: Dict[str, Any]) -> List[str]:
    """Validate an envelope dict against the JSON schema.

    Returns a (possibly empty) list of human-readable error strings.
    """
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    return [e.message for e in sorted(validator.iter_errors(envelope), key=str)]


def normalize_envelope_fields(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize envelope fields to canonical form (in-place + returned).

    - Ensures ``envelope_version`` is present.
    - Computes ``hashes.raw_sha256`` if missing and ``raw`` is present.
    - Ensures ``collected_at`` is ISO-8601 UTC.
    - Coerces ``acl_tags`` to list.
    """
    envelope.setdefault("envelope_version", "1.0")
    envelope.setdefault("acl_tags", [])
    envelope.setdefault("metadata", {})
    envelope.setdefault("hashes", {})

    if isinstance(envelope.get("acl_tags"), str):
        envelope["acl_tags"] = [envelope["acl_tags"]]

    raw = envelope.get("raw")
    if raw is not None and "raw_sha256" not in envelope["hashes"]:
        envelope["hashes"]["raw_sha256"] = compute_hash(raw)

    if not envelope.get("collected_at"):
        envelope["collected_at"] = datetime.now(timezone.utc).isoformat()

    return envelope


def canonical_to_envelope(
    record: Dict[str, Any],
    *,
    source_instance: str = "",
) -> RecordEnvelope:
    """Convert an existing canonical record to a RecordEnvelope.

    This is the compatibility bridge — connectors that already produce
    canonical records can wrap them with a single call.
    """
    prov = record.get("provenance", [{}])
    first_prov = prov[0] if prov else {}

    return RecordEnvelope(
        source=record.get("source", {}).get("system", ""),
        source_instance=source_instance,
        record_id=record.get("record_id", ""),
        record_type=record.get("record_type", ""),
        provenance={
            "uri": first_prov.get("ref", ""),
            "last_modified": record.get("observed_at", ""),
            "author": record.get("source", {}).get("actor", {}).get("id", ""),
        },
        raw=record,
        metadata={
            "confidence": record.get("confidence", {}).get("score"),
            "ttl": record.get("ttl"),
            "labels": record.get("labels", {}),
        },
    )
