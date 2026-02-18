#!/usr/bin/env python3
"""Generate expected envelope files for connector fixture data.

Reads baseline_raw.json from each connector fixture directory, transforms
through the appropriate connector, wraps in RecordEnvelopes, and writes
expected_envelopes.jsonl for deterministic golden-file testing.

Usage::

    python tools/generate_connector_fixtures.py
    python tools/generate_connector_fixtures.py --connector sharepoint_small
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from connectors.contract import canonical_to_envelope, validate_envelope  # noqa: E402

FIXTURE_BASE = _REPO_ROOT / "fixtures" / "connectors"

# ── Connector-specific transformers ──────────────────────────────────────────

_COLLECTED_AT = "2026-02-18T12:00:00+00:00"  # Fixed for determinism


def _sharepoint_transform(raw_items: List[Dict]) -> List[Dict[str, Any]]:
    """Transform raw SharePoint Graph API items → canonical → envelopes."""
    from adapters.sharepoint.connector import SharePointConnector

    with patch.object(SharePointConnector, "__init__", lambda self, **kw: None):
        c = SharePointConnector.__new__(SharePointConnector)
        c._site_id = "fixture-site"
        c._delta_tokens = {}
        c._auth = MagicMock()
        c._tenant_id = "t"
        c._client_id = "c"
        c._client_secret = "s"

    records = [c._to_canonical(item, "fixture-list") for item in raw_items]
    envelopes = []
    for rec in records:
        env = canonical_to_envelope(rec, source_instance="fixture-site")
        env.collected_at = _COLLECTED_AT
        envelopes.append(env.to_dict())
    return envelopes


def _dataverse_transform(raw_rows: List[Dict]) -> List[Dict[str, Any]]:
    """Transform raw Dataverse rows → canonical → envelopes."""
    from adapters.powerplatform.connector import DataverseConnector

    with patch.object(DataverseConnector, "__init__", lambda self, **kw: None):
        c = DataverseConnector.__new__(DataverseConnector)
        c._env_url = "https://fixture.crm.dynamics.com"
        c._auth = MagicMock()
        c._client_id = "c"
        c._client_secret = "s"
        c._tenant_id = "t"

    envelopes = []
    for row in raw_rows:
        # Infer table name from the key pattern
        table = _infer_dv_table(row)
        rec = c._to_canonical(row, table)
        env = canonical_to_envelope(rec, source_instance="fixture")
        env.collected_at = _COLLECTED_AT
        envelopes.append(env.to_dict())
    return envelopes


def _infer_dv_table(row: Dict) -> str:
    """Infer Dataverse table name from row keys."""
    if "accountid" in row:
        return "accounts"
    if "contactid" in row:
        return "contacts"
    if "incidentid" in row:
        return "incidents"
    if "annotationid" in row:
        return "annotations"
    if "taskid" in row:
        return "tasks"
    return "unknown"


def _snowflake_transform(raw_rows: List[Dict]) -> List[Dict[str, Any]]:
    """Transform raw Snowflake rows → canonical → envelopes."""
    from adapters.snowflake.warehouse import SnowflakeWarehouseConnector

    with patch.object(SnowflakeWarehouseConnector, "__init__", lambda self, **kw: None):
        c = SnowflakeWarehouseConnector.__new__(SnowflakeWarehouseConnector)
        c._auth = MagicMock()
        c._auth.account = "fixture-account"
        c._database = "FIXTURE_DB"
        c._schema = "PUBLIC"
        c._warehouse = "FIXTURE_WH"

    records = c.to_canonical(raw_rows, "fixture_table")
    envelopes = []
    for rec in records:
        env = canonical_to_envelope(rec, source_instance="fixture-account")
        env.collected_at = _COLLECTED_AT
        envelopes.append(env.to_dict())
    return envelopes


def _asksage_transform(raw_records: List[Dict]) -> List[Dict[str, Any]]:
    """AskSage fixtures are already canonical — just wrap in envelopes."""
    envelopes = []
    for rec in raw_records:
        env = canonical_to_envelope(rec, source_instance="https://api.asksage.ai")
        env.collected_at = _COLLECTED_AT
        envelopes.append(env.to_dict())
    return envelopes


_TRANSFORMERS = {
    "sharepoint_small": _sharepoint_transform,
    "dataverse_small": _dataverse_transform,
    "snowflake_small": _snowflake_transform,
    "asksage_small": _asksage_transform,
}


# ── Main ─────────────────────────────────────────────────────────────────────


def generate(connector_name: str) -> int:
    """Generate expected_envelopes.jsonl for a single connector fixture."""
    fixture_dir = FIXTURE_BASE / connector_name
    baseline_path = fixture_dir / "baseline_raw.json"

    if not baseline_path.exists():
        print(f"SKIP {connector_name}: no baseline_raw.json", file=sys.stderr)
        return 1

    transformer = _TRANSFORMERS.get(connector_name)
    if transformer is None:
        print(f"SKIP {connector_name}: no transformer registered", file=sys.stderr)
        return 1

    raw_data = json.loads(baseline_path.read_text())
    envelopes = transformer(raw_data)

    # Validate all envelopes
    for i, env in enumerate(envelopes):
        errors = validate_envelope(env)
        if errors:
            print(f"FAIL {connector_name} envelope[{i}]: {errors}", file=sys.stderr)
            return 1

    # Write as JSONL (one envelope per line, stable ordering)
    out_path = fixture_dir / "expected_envelopes.jsonl"
    with open(out_path, "w") as f:
        for env in envelopes:
            f.write(json.dumps(env, sort_keys=True) + "\n")

    print(f"OK   {connector_name}: {len(envelopes)} envelopes → {out_path.relative_to(_REPO_ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate expected connector envelope fixtures",
    )
    parser.add_argument(
        "--connector",
        default=None,
        help="Generate for a single connector (e.g. sharepoint_small)",
    )
    args = parser.parse_args(argv)

    if args.connector:
        return generate(args.connector)

    # Generate all
    failed = 0
    for name in sorted(_TRANSFORMERS):
        failed += generate(name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
