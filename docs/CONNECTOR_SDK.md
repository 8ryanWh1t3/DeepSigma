# Connector SDK

Build a custom ConnectorV1 plugin quickly and safely.

## Quickstart (< 100 lines)

```bash
deepsigma new-connector my-api
pytest -q tests/test_my_api_connector.py
```

Generated scaffold includes:
- connector class (`src/adapters/my_api/connector.py`)
- protocol harness test (`tests/test_my_api_connector.py`)
- MCP tool stubs (`src/adapters/my_api/mcp_tools.py`)
- README (`src/adapters/my_api/README.md`)

## ConnectorV1 protocol

`adapters.contract.ConnectorV1` defines three core methods:

- `source_name: str`
  - Canonical source id (e.g., `sharepoint`, `dataverse`, `csv`)
- `list_records(**kwargs) -> list[dict]`
  - Return canonical records
- `get_record(record_id, **kwargs) -> dict`
  - Return a single canonical record
- `to_envelopes(records) -> list[RecordEnvelope]`
  - Convert canonical records to schema-validated envelopes

## Contract rules

1. Every record must include `record_id`.
2. `source_name` must be stable and non-empty.
3. `to_envelopes` must produce envelopes passing `validate_envelope`.
4. Connectors should be read-only by default and avoid writing upstream data.
5. Redaction/data-boundary behavior should follow `docs/136.md` / policy docs.

## Protocol harness

Use the reusable harness to validate any connector:

```python
from adapters.testing.harness import assert_connector_v1

assert_connector_v1(connector)
```

This verifies list/get/envelope behavior and schema validity.

## Community example connector

A reference implementation is provided:
- `src/adapters/community/csv_connector.py`
- `tests/test_connector_protocol_harness.py`

It demonstrates the minimal path from source rows to valid envelopes.
