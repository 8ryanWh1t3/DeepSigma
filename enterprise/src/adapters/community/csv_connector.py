"""Community example connector: CSV file -> canonical records -> envelopes."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from adapters.contract import RecordEnvelope


class CSVFileConnector:
    """Simple read-only ConnectorV1 example using CSV as a source."""

    source_name = "csv"

    def __init__(self, csv_path: str | Path, source_instance: str = "local") -> None:
        self.csv_path = Path(csv_path)
        self.source_instance = source_instance

    def list_records(self, **kwargs: Any) -> list[dict[str, Any]]:
        limit = int(kwargs.get("limit", 0) or 0)
        rows: list[dict[str, Any]] = []
        with self.csv_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                record_id = row.get("record_id") or row.get("id")
                if not record_id:
                    continue
                rows.append(
                    {
                        "record_id": str(record_id),
                        "record_type": row.get("record_type", "Row"),
                        "source": {"system": self.source_name},
                        "observed_at": row.get("observed_at", ""),
                        "provenance": [{"ref": f"csv://{self.csv_path.name}#{record_id}"}],
                        "raw": row,
                    }
                )
                if limit and len(rows) >= limit:
                    break
        return rows

    def get_record(self, record_id: str, **kwargs: Any) -> dict[str, Any]:
        for rec in self.list_records(**kwargs):
            if rec["record_id"] == record_id:
                return rec
        raise KeyError(f"Record not found: {record_id}")

    def to_envelopes(self, records: list[dict[str, Any]]) -> list[RecordEnvelope]:
        envs: list[RecordEnvelope] = []
        for rec in records:
            envs.append(
                RecordEnvelope(
                    source=self.source_name,
                    source_instance=self.source_instance,
                    record_id=rec["record_id"],
                    record_type=rec.get("record_type", "Row"),
                    provenance={"uri": rec.get("provenance", [{}])[0].get("ref", "")},
                    raw=rec,
                    metadata={"origin": "community_csv_connector"},
                )
            )
        return envs
