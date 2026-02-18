"""Tests for the Connector Fixture Library — deterministic golden envelope comparison."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from connectors.contract import validate_envelope

FIXTURE_BASE = Path(__file__).parent.parent / "fixtures" / "connectors"

# Use the same fixed timestamp as the generator
_COLLECTED_AT = "2026-02-18T12:00:00+00:00"


def _load_expected(connector_name: str) -> list[dict]:
    """Load expected_envelopes.jsonl for a connector."""
    path = FIXTURE_BASE / connector_name / "expected_envelopes.jsonl"
    assert path.exists(), f"Missing: {path}"
    return [json.loads(line) for line in path.read_text().strip().splitlines()]


# ── SharePoint Fixtures ──────────────────────────────────────────────────────


class TestSharePointFixtures:
    CONNECTOR = "sharepoint_small"

    def _produce(self):
        from unittest.mock import MagicMock, patch as mock_patch
        from adapters.sharepoint.connector import SharePointConnector
        from connectors.contract import canonical_to_envelope

        raw = json.loads((FIXTURE_BASE / self.CONNECTOR / "baseline_raw.json").read_text())
        with mock_patch.object(SharePointConnector, "__init__", lambda self, **kw: None):
            c = SharePointConnector.__new__(SharePointConnector)
            c._site_id = "fixture-site"
            c._delta_tokens = {}
            c._auth = MagicMock()
            c._tenant_id = "t"
            c._client_id = "c"
            c._client_secret = "s"

        records = [c._to_canonical(item, "fixture-list") for item in raw]
        envs = []
        for rec in records:
            env = canonical_to_envelope(rec, source_instance="fixture-site")
            env.collected_at = _COLLECTED_AT
            envs.append(env.to_dict())
        return envs

    def test_count_matches(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        assert len(produced) == len(expected)

    def test_envelopes_match_golden(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        for i, (exp, prod) in enumerate(zip(expected, produced)):
            # Compare stable fields (not collected_at which may drift)
            prod_sorted = json.dumps(prod, sort_keys=True)
            exp_sorted = json.dumps(exp, sort_keys=True)
            assert prod_sorted == exp_sorted, f"Mismatch at index {i}"

    def test_all_validate(self):
        expected = _load_expected(self.CONNECTOR)
        for i, env in enumerate(expected):
            errors = validate_envelope(env)
            assert errors == [], f"Validation errors at [{i}]: {errors}"

    def test_hashes_stable(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        for exp, prod in zip(expected, produced):
            assert exp["hashes"]["raw_sha256"] == prod["hashes"]["raw_sha256"]

    def test_source_correct(self):
        expected = _load_expected(self.CONNECTOR)
        for env in expected:
            assert env["source"] == "sharepoint"


# ── Dataverse Fixtures ───────────────────────────────────────────────────────


class TestDataverseFixtures:
    CONNECTOR = "dataverse_small"

    def _produce(self):
        from unittest.mock import MagicMock, patch as mock_patch
        from adapters.powerplatform.connector import DataverseConnector
        from connectors.contract import canonical_to_envelope

        raw = json.loads((FIXTURE_BASE / self.CONNECTOR / "baseline_raw.json").read_text())
        with mock_patch.object(DataverseConnector, "__init__", lambda self, **kw: None):
            c = DataverseConnector.__new__(DataverseConnector)
            c._env_url = "https://fixture.crm.dynamics.com"
            c._auth = MagicMock()
            c._client_id = "c"
            c._client_secret = "s"
            c._tenant_id = "t"

        envs = []
        for row in raw:
            table = _infer_dv_table(row)
            rec = c._to_canonical(row, table)
            env = canonical_to_envelope(rec, source_instance="fixture")
            env.collected_at = _COLLECTED_AT
            envs.append(env.to_dict())
        return envs

    def test_count_matches(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        assert len(produced) == len(expected)

    def test_envelopes_match_golden(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        for i, (exp, prod) in enumerate(zip(expected, produced)):
            assert json.dumps(prod, sort_keys=True) == json.dumps(exp, sort_keys=True), \
                f"Mismatch at index {i}"

    def test_all_validate(self):
        expected = _load_expected(self.CONNECTOR)
        for i, env in enumerate(expected):
            errors = validate_envelope(env)
            assert errors == [], f"Validation errors at [{i}]: {errors}"

    def test_hashes_stable(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        for exp, prod in zip(expected, produced):
            assert exp["hashes"]["raw_sha256"] == prod["hashes"]["raw_sha256"]

    def test_source_correct(self):
        expected = _load_expected(self.CONNECTOR)
        for env in expected:
            assert env["source"] == "dataverse"


# ── Snowflake Fixtures ───────────────────────────────────────────────────────


class TestSnowflakeFixtures:
    CONNECTOR = "snowflake_small"

    def _produce(self):
        from unittest.mock import MagicMock, patch as mock_patch
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        from connectors.contract import canonical_to_envelope

        raw = json.loads((FIXTURE_BASE / self.CONNECTOR / "baseline_raw.json").read_text())
        with mock_patch.object(SnowflakeWarehouseConnector, "__init__", lambda self, **kw: None):
            c = SnowflakeWarehouseConnector.__new__(SnowflakeWarehouseConnector)
            c._auth = MagicMock()
            c._auth.account = "fixture-account"
            c._database = "FIXTURE_DB"
            c._schema = "PUBLIC"
            c._warehouse = "FIXTURE_WH"

        records = c.to_canonical(raw, "fixture_table")
        envs = []
        for rec in records:
            env = canonical_to_envelope(rec, source_instance="fixture-account")
            env.collected_at = _COLLECTED_AT
            envs.append(env.to_dict())
        return envs

    def test_count_matches(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        assert len(produced) == len(expected)

    def test_envelopes_match_golden(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        for i, (exp, prod) in enumerate(zip(expected, produced)):
            assert json.dumps(prod, sort_keys=True) == json.dumps(exp, sort_keys=True), \
                f"Mismatch at index {i}"

    def test_all_validate(self):
        expected = _load_expected(self.CONNECTOR)
        for i, env in enumerate(expected):
            errors = validate_envelope(env)
            assert errors == [], f"Validation errors at [{i}]: {errors}"

    def test_hashes_stable(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        for exp, prod in zip(expected, produced):
            assert exp["hashes"]["raw_sha256"] == prod["hashes"]["raw_sha256"]

    def test_source_correct(self):
        expected = _load_expected(self.CONNECTOR)
        for env in expected:
            assert env["source"] == "snowflake"


# ── AskSage Fixtures ────────────────────────────────────────────────────────


class TestAskSageFixtures:
    CONNECTOR = "asksage_small"

    def _produce(self):
        from connectors.contract import canonical_to_envelope

        raw = json.loads((FIXTURE_BASE / self.CONNECTOR / "baseline_raw.json").read_text())
        envs = []
        for rec in raw:
            env = canonical_to_envelope(rec, source_instance="https://api.asksage.ai")
            env.collected_at = _COLLECTED_AT
            envs.append(env.to_dict())
        return envs

    def test_count_matches(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        assert len(produced) == len(expected)

    def test_envelopes_match_golden(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        for i, (exp, prod) in enumerate(zip(expected, produced)):
            assert json.dumps(prod, sort_keys=True) == json.dumps(exp, sort_keys=True), \
                f"Mismatch at index {i}"

    def test_all_validate(self):
        expected = _load_expected(self.CONNECTOR)
        for i, env in enumerate(expected):
            errors = validate_envelope(env)
            assert errors == [], f"Validation errors at [{i}]: {errors}"

    def test_hashes_stable(self):
        expected = _load_expected(self.CONNECTOR)
        produced = self._produce()
        for exp, prod in zip(expected, produced):
            assert exp["hashes"]["raw_sha256"] == prod["hashes"]["raw_sha256"]

    def test_source_correct(self):
        expected = _load_expected(self.CONNECTOR)
        for env in expected:
            assert env["source"] == "asksage"


# ── Cross-connector Tests ───────────────────────────────────────────────────


class TestCrossConnector:
    CONNECTORS = ["sharepoint_small", "dataverse_small", "snowflake_small", "asksage_small"]

    def test_all_fixtures_exist(self):
        for name in self.CONNECTORS:
            assert (FIXTURE_BASE / name / "baseline_raw.json").exists(), f"Missing baseline: {name}"
            assert (FIXTURE_BASE / name / "delta_raw.json").exists(), f"Missing delta: {name}"
            assert (FIXTURE_BASE / name / "expected_envelopes.jsonl").exists(), f"Missing expected: {name}"

    def test_all_envelopes_have_version(self):
        for name in self.CONNECTORS:
            for env in _load_expected(name):
                assert env["envelope_version"] == "1.0"

    def test_no_empty_record_ids(self):
        for name in self.CONNECTORS:
            for env in _load_expected(name):
                assert env["record_id"], f"Empty record_id in {name}"

    def test_all_have_raw_hash(self):
        for name in self.CONNECTORS:
            for env in _load_expected(name):
                assert len(env["hashes"]["raw_sha256"]) == 64


# ── Helpers ──────────────────────────────────────────────────────────────────

def _infer_dv_table(row: dict) -> str:
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
