"""FEEDS envelope builder — construct and hash event envelopes."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .types import Classification, FeedTopic, RecordType, TOPIC_TO_RECORD


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Canonical JSON + SHA-256 hash of a payload dict.

    Returns:
        String in format ``"sha256:<64hex>"``.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_envelope(
    topic: FeedTopic | str,
    payload: Dict[str, Any],
    packet_id: str,
    producer: str,
    classification: Classification | str = Classification.LEVEL_0,
    sequence: int = 0,
    *,
    event_id: Optional[str] = None,
    uid: Optional[str] = None,
    human_id: Optional[str] = None,
    subtype: Optional[str] = None,
    schema_version: str = "1.0.0",
    created_at: Optional[str] = None,
    record_type: Optional[RecordType | str] = None,
) -> Dict[str, Any]:
    """Build a complete FEEDS event envelope.

    Auto-generates ``event_id``, ``uid``, ``created_at``, and ``payload_hash``
    when not explicitly provided.
    """
    topic_enum = FeedTopic(topic) if isinstance(topic, str) else topic

    if record_type is None:
        record_type = TOPIC_TO_RECORD[topic_enum]
    rt_value = record_type.value if isinstance(record_type, RecordType) else record_type

    cls_value = (
        classification.value
        if isinstance(classification, Classification)
        else classification
    )

    eid = event_id or str(uuid.uuid4())
    uid_val = uid or eid
    ts = created_at or datetime.now(timezone.utc).isoformat()

    envelope: Dict[str, Any] = {
        "eventId": eid,
        "packetId": packet_id,
        "topic": topic_enum.value,
        "recordType": rt_value,
        "uid": uid_val,
        "sequence": sequence,
        "createdAt": ts,
        "producer": producer,
        "classification": cls_value,
        "payload": payload,
        "payloadHash": compute_payload_hash(payload),
        "schemaVersion": schema_version,
    }

    if human_id is not None:
        envelope["humanId"] = human_id
    if subtype is not None:
        envelope["subtype"] = subtype

    return envelope
