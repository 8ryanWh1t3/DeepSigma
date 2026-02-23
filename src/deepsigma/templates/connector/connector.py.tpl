"""{{ connector_class }} — generated connector scaffold."""

from __future__ import annotations

from typing import Any

from adapters.contract import RecordEnvelope


class {{ connector_class }}:
    """ConnectorV1-compatible scaffold."""

    source_name = "{{ connector_slug }}"

    def list_records(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Return canonical records from the source."""
        return []

    def get_record(self, record_id: str, **kwargs: Any) -> dict[str, Any]:
        """Return a single canonical record by record_id."""
        raise KeyError(f"Record not found: {record_id}")

    def to_envelopes(self, records: list[dict[str, Any]]) -> list[RecordEnvelope]:
        """Convert canonical records into RecordEnvelope objects."""
        envelopes: list[RecordEnvelope] = []
        for rec in records:
            envelopes.append(
                RecordEnvelope(
                    source=self.source_name,
                    source_instance="generated",
                    record_id=rec.get("record_id", ""),
                    record_type=rec.get("record_type", "Record"),
                    provenance={"uri": rec.get("uri", "")},
                    raw=rec,
                )
            )
        return envelopes
