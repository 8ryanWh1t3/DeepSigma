"""Primitive Envelope — canonical wrapper for the five primitive types.

Every CLAIM, EVENT, REVIEW, PATCH, or APPLY flowing through the system
is wrapped in a PrimitiveEnvelope before entering the coherence loop,
Memory Graph, or FEEDS bus.  Envelopes are append-only and versioned;
superseding creates a new envelope linked to its parent.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .primitives import ALLOWED_PRIMITIVE_TYPES, PrimitiveType


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _envelope_id() -> str:
    return f"ENV-{uuid.uuid4().hex[:12]}"


# ── Envelope dataclass ─────────────────────────────────────────


@dataclass
class PrimitiveEnvelope:
    """Canonical wrapper for any of the five primitive types."""

    envelope_id: str
    primitive_type: PrimitiveType
    version: int
    payload: Dict[str, Any]
    created_at: str
    source: str
    parent_envelope_id: Optional[str] = None
    sealed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict."""
        d: Dict[str, Any] = {
            "envelopeId": self.envelope_id,
            "primitiveType": self.primitive_type.value if isinstance(self.primitive_type, PrimitiveType) else self.primitive_type,
            "version": self.version,
            "payload": self.payload,
            "createdAt": self.created_at,
            "source": self.source,
            "sealed": self.sealed,
        }
        if self.parent_envelope_id is not None:
            d["parentEnvelopeId"] = self.parent_envelope_id
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    def seal(self) -> PrimitiveEnvelope:
        """Return a sealed copy (idempotent)."""
        self.sealed = True
        return self


# ── Factory / validation ───────────────────────────────────────


def wrap_primitive(
    primitive_type: str,
    payload: Dict[str, Any],
    source: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    parent_envelope_id: Optional[str] = None,
    version: int = 1,
) -> PrimitiveEnvelope:
    """Create a new PrimitiveEnvelope.

    Raises ``ValueError`` if *primitive_type* is not one of the five
    allowed types.
    """
    if primitive_type not in ALLOWED_PRIMITIVE_TYPES:
        raise ValueError(
            f"Unknown primitive type {primitive_type!r}. "
            f"Allowed: {sorted(ALLOWED_PRIMITIVE_TYPES)}"
        )
    return PrimitiveEnvelope(
        envelope_id=_envelope_id(),
        primitive_type=PrimitiveType(primitive_type),
        version=version,
        payload=payload,
        created_at=_now_iso(),
        source=source,
        parent_envelope_id=parent_envelope_id,
        metadata=metadata or {},
    )


def validate_envelope(envelope: PrimitiveEnvelope) -> None:
    """Raise ``ValueError`` if the envelope's type is not allowed."""
    ptype = (
        envelope.primitive_type.value
        if isinstance(envelope.primitive_type, PrimitiveType)
        else envelope.primitive_type
    )
    if ptype not in ALLOWED_PRIMITIVE_TYPES:
        raise ValueError(
            f"Invalid primitive type {ptype!r}. "
            f"Allowed: {sorted(ALLOWED_PRIMITIVE_TYPES)}"
        )


def wrap_record(
    record: Any,
    source: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    parent_envelope_id: Optional[str] = None,
    version: int = 1,
) -> PrimitiveEnvelope:
    """Wrap a typed record (ClaimRecord, EventRecord, etc.) in an envelope.

    The record must have a ``PRIMITIVE_TYPE`` attribute and a ``to_dict()``
    method.
    """
    return wrap_primitive(
        record.PRIMITIVE_TYPE.value,
        record.to_dict(),
        source,
        metadata=metadata,
        parent_envelope_id=parent_envelope_id,
        version=version,
    )


def supersede_envelope(
    old: PrimitiveEnvelope,
    new_payload: Dict[str, Any],
    source: Optional[str] = None,
) -> PrimitiveEnvelope:
    """Create a new envelope that supersedes *old*.

    Increments version and links back via *parent_envelope_id*.
    """
    return PrimitiveEnvelope(
        envelope_id=_envelope_id(),
        primitive_type=old.primitive_type,
        version=old.version + 1,
        payload=new_payload,
        created_at=_now_iso(),
        source=source or old.source,
        parent_envelope_id=old.envelope_id,
        metadata=old.metadata.copy(),
    )
