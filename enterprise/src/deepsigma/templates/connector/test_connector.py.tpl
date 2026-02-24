"""Tests for {{ connector_class }} scaffold."""

from __future__ import annotations

from {{ import_path }} import {{ connector_class }}
from adapters.testing.harness import assert_connector_v1


class _{{ connector_class }}ForTest({{ connector_class }}):
    def list_records(self, **kwargs):
        return [
            {
                "record_id": "sample-001",
                "record_type": "Sample",
                "source": {"system": self.source_name},
                "provenance": [{"ref": "sample://1"}],
                "raw": {"x": 1},
            }
        ]

    def get_record(self, record_id: str, **kwargs):
        return self.list_records()[0]


def test_protocol_harness_passes():
    assert_connector_v1(_{{ connector_class }}ForTest())
