"""Connector protocol test harness for ConnectorV1 implementations."""

from __future__ import annotations

from typing import Any

from adapters.contract import ConnectorV1, validate_envelope


class ConnectorProtocolError(AssertionError):
    """Raised when a connector violates ConnectorV1 contract expectations."""


def assert_connector_v1(
    connector: ConnectorV1,
    *,
    list_kwargs: dict[str, Any] | None = None,
    get_kwargs: dict[str, Any] | None = None,
) -> None:
    """Validate a connector instance against core ConnectorV1 contract rules."""
    if not getattr(connector, "source_name", ""):
        raise ConnectorProtocolError("connector.source_name must be non-empty")

    list_kwargs = list_kwargs or {}
    records = connector.list_records(**list_kwargs)
    if not isinstance(records, list):
        raise ConnectorProtocolError("list_records() must return a list")
    if not records:
        raise ConnectorProtocolError("list_records() returned no records for protocol test")

    first = records[0]
    if not isinstance(first, dict):
        raise ConnectorProtocolError("list_records() items must be dicts")
    if "record_id" not in first:
        raise ConnectorProtocolError("record missing required key: record_id")

    rid = first["record_id"]
    fetched = connector.get_record(rid, **(get_kwargs or {}))
    if not isinstance(fetched, dict):
        raise ConnectorProtocolError("get_record() must return a dict")
    if fetched.get("record_id") != rid:
        raise ConnectorProtocolError("get_record() returned mismatched record_id")

    envelopes = connector.to_envelopes([fetched])
    if not isinstance(envelopes, list) or not envelopes:
        raise ConnectorProtocolError("to_envelopes() must return a non-empty list")

    envelope = envelopes[0]
    payload = envelope.to_dict() if hasattr(envelope, "to_dict") else envelope
    if not isinstance(payload, dict):
        raise ConnectorProtocolError("envelope must be dict-like")

    errors = validate_envelope(payload)
    if errors:
        raise ConnectorProtocolError(f"envelope schema validation failed: {errors}")
