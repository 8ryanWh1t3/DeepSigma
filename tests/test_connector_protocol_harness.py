"""Protocol harness tests for ConnectorV1 implementations."""

from __future__ import annotations

from pathlib import Path

from adapters.community.csv_connector import CSVFileConnector
from adapters.testing.harness import assert_connector_v1


def test_csv_connector_passes_protocol_harness() -> None:
    fixture = Path(__file__).parent / "fixtures" / "community_connector_rows.csv"
    connector = CSVFileConnector(csv_path=fixture, source_instance="fixture-csv")
    assert_connector_v1(connector)
