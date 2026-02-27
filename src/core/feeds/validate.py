"""Two-phase FEEDS event validation.

Phase 1: validate envelope against ``feeds_event_envelope`` schema.
Phase 2: validate payload against topic-specific schema.
"""

from __future__ import annotations

from typing import Any, Dict

from core.schema_validator import ValidationResult, validate as schema_validate

from .envelope import compute_payload_hash
from .types import FeedTopic

# Map topic enum values to their payload schema names (without .schema.json)
_TOPIC_SCHEMA: Dict[str, str] = {
    FeedTopic.TRUTH_SNAPSHOT.value: "truth_snapshot",
    FeedTopic.AUTHORITY_SLICE.value: "authority_slice",
    FeedTopic.DECISION_LINEAGE.value: "decision_lineage",
    FeedTopic.DRIFT_SIGNAL.value: "drift_signal",
    FeedTopic.CANON_ENTRY.value: "canon_entry",
    FeedTopic.PACKET_INDEX.value: "packet_index",
}


def validate_feed_event(event: Dict[str, Any]) -> ValidationResult:
    """Validate a FEEDS event in two phases.

    Phase 1 — Envelope schema (``feeds_event_envelope``).
    Phase 2 — Topic-specific payload schema + payload hash verification.

    Returns the first failing :class:`ValidationResult`, or a passing result
    if both phases succeed.
    """
    # Phase 1: envelope schema
    result = schema_validate(event, "feeds_event_envelope")
    if not result.valid:
        return result

    # Phase 2: payload schema by topic
    topic = event.get("topic", "")
    payload_schema = _TOPIC_SCHEMA.get(topic)
    if payload_schema is not None:
        payload = event.get("payload", {})
        payload_result = schema_validate(payload, payload_schema)
        if not payload_result.valid:
            return payload_result

    # Phase 2b: verify payload hash
    declared_hash = event.get("payloadHash", "")
    computed_hash = compute_payload_hash(event.get("payload", {}))
    if declared_hash != computed_hash:
        from core.schema_validator import SchemaError

        return ValidationResult(
            valid=False,
            errors=[
                SchemaError(
                    path="payloadHash",
                    message=f"Payload hash mismatch: declared={declared_hash}, computed={computed_hash}",
                    schema_path="",
                )
            ],
            schema_name="feeds_event_envelope",
        )

    return ValidationResult(valid=True, schema_name="feeds_event_envelope")
