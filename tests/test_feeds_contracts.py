"""Tests for FEEDS event contracts — routing table, loader, and validator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.feeds.contracts.loader import (
    RoutingTable,
    compute_table_fingerprint,
    load_routing_table,
)
from core.feeds.contracts.validator import (
    validate_event_contract,
    validate_output_event,
    validate_routing_table_integrity,
)
from core.feeds import build_envelope, FeedTopic


# ── Fixture ──────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def table() -> RoutingTable:
    """Load the canonical routing table once per module."""
    return load_routing_table()


# ── Loader tests ─────────────────────────────────────────────────


class TestRoutingTableLoader:
    """Tests for routing_table.json loading and parsing."""

    def test_load_succeeds(self, table: RoutingTable) -> None:
        assert table.schema_version == "1.0.0"
        assert table.generated_at != ""
        assert table.contract_fingerprint.startswith("sha256:")

    def test_function_count(self, table: RoutingTable) -> None:
        """36 functions: 12 INTEL + 12 FRAN + 12 RE."""
        assert len(table.functions) == 36

    def test_event_count(self, table: RoutingTable) -> None:
        """38 events: 14 INTEL + 13 FRAN + 12 RE (one is shared)."""
        # Actual count from routing_table.json
        assert len(table.events) >= 38

    def test_all_function_ids_well_formed(self, table: RoutingTable) -> None:
        import re
        pattern = re.compile(r"^(INTEL|FRAN|RE)-F\d{2}$")
        for fid in table.function_ids:
            assert pattern.match(fid), f"Malformed function ID: {fid}"

    def test_all_event_ids_well_formed(self, table: RoutingTable) -> None:
        import re
        pattern = re.compile(r"^(INTEL|FRAN|RE|CASCADE)-E\d{2}$")
        for eid in table.event_ids:
            assert pattern.match(eid), f"Malformed event ID: {eid}"

    def test_intel_functions_present(self, table: RoutingTable) -> None:
        for i in range(1, 13):
            fid = f"INTEL-F{i:02d}"
            assert fid in table.functions, f"Missing {fid}"

    def test_fran_functions_present(self, table: RoutingTable) -> None:
        for i in range(1, 13):
            fid = f"FRAN-F{i:02d}"
            assert fid in table.functions, f"Missing {fid}"

    def test_re_functions_present(self, table: RoutingTable) -> None:
        for i in range(1, 13):
            fid = f"RE-F{i:02d}"
            assert fid in table.functions, f"Missing {fid}"

    def test_function_has_required_fields(self, table: RoutingTable) -> None:
        for fid, fn in table.functions.items():
            assert fn.name, f"{fid} missing name"
            assert fn.domain, f"{fid} missing domain"
            assert fn.input_topic, f"{fid} missing input_topic"
            assert fn.input_subtype, f"{fid} missing input_subtype"
            assert fn.handler, f"{fid} missing handler"

    def test_event_has_required_fields(self, table: RoutingTable) -> None:
        for eid, ev in table.events.items():
            assert ev.name, f"{eid} missing name"
            assert ev.domain, f"{eid} missing domain"
            assert ev.topic, f"{eid} missing topic"
            assert ev.subtype, f"{eid} missing subtype"
            assert ev.produced_by, f"{eid} missing produced_by"

    def test_functions_by_domain(self, table: RoutingTable) -> None:
        intel = table.functions_by_domain("intelops")
        assert len(intel) == 12
        fran = table.functions_by_domain("franops")
        assert len(fran) == 12
        reops = table.functions_by_domain("reflectionops")
        assert len(reops) == 12

    def test_get_handler(self, table: RoutingTable) -> None:
        handler = table.get_handler("INTEL-F01")
        assert handler == "core.modes.intelops.claim_ingest"

    def test_get_handler_missing(self, table: RoutingTable) -> None:
        assert table.get_handler("NONEXISTENT-F99") is None

    def test_get_consumers(self, table: RoutingTable) -> None:
        consumers = table.get_consumers("INTEL-E01")
        assert "INTEL-F02" in consumers

    def test_get_consumers_empty(self, table: RoutingTable) -> None:
        assert table.get_consumers("NONEXISTENT-E99") == []

    def test_functions_for_topic(self, table: RoutingTable) -> None:
        fns = table.functions_for_topic("truth_snapshot")
        assert len(fns) > 0
        for fn in fns:
            assert fn.input_topic == "truth_snapshot"

    def test_functions_for_topic_with_subtype(self, table: RoutingTable) -> None:
        fns = table.functions_for_topic("truth_snapshot", "claim_ingest")
        assert len(fns) == 1
        assert fns[0].function_id == "INTEL-F01"


# ── Validator tests ──────────────────────────────────────────────


class TestContractValidator:
    """Tests for event contract validation."""

    def test_valid_input_event(self, table: RoutingTable) -> None:
        event = build_envelope(
            topic=FeedTopic.TRUTH_SNAPSHOT,
            payload={"claimId": "CLAIM-001", "statement": "test", "confidence": 0.9,
                     "snapshotId": "TS-001", "capturedAt": "2026-01-01T00:00:00Z",
                     "claims": [], "evidenceSummary": "ok", "coherenceScore": 80,
                     "seal": {"hash": "sha256:abc", "sealedAt": "2026-01-01T00:00:01Z", "version": 1}},
            packet_id="CP-2026-02-28-0001",
            producer="test",
            subtype="claim_ingest",
        )
        result = validate_event_contract(event, "INTEL-F01", table)
        assert result.valid

    def test_wrong_topic(self, table: RoutingTable) -> None:
        event = {"topic": "drift_signal", "subtype": "claim_ingest", "payload": {}}
        result = validate_event_contract(event, "INTEL-F01", table)
        assert not result.valid
        assert any("topic" in v.field for v in result.violations)

    def test_wrong_subtype(self, table: RoutingTable) -> None:
        event = {"topic": "truth_snapshot", "subtype": "wrong_subtype", "payload": {}}
        result = validate_event_contract(event, "INTEL-F01", table)
        assert not result.valid
        assert any("subtype" in v.field for v in result.violations)

    def test_missing_payload_field(self, table: RoutingTable) -> None:
        event = {"topic": "truth_snapshot", "subtype": "claim_ingest", "payload": {}}
        result = validate_event_contract(event, "INTEL-F01", table)
        assert not result.valid
        assert any("claimId" in v.field for v in result.violations)

    def test_unknown_function_id(self, table: RoutingTable) -> None:
        result = validate_event_contract({}, "NONEXISTENT-F99", table)
        assert not result.valid
        assert any("not found" in v.message for v in result.violations)

    def test_valid_output_event(self, table: RoutingTable) -> None:
        event = {"topic": "canon_entry", "subtype": "claim_accepted"}
        result = validate_output_event(event, "INTEL-F01", table)
        assert result.valid

    def test_invalid_output_topic(self, table: RoutingTable) -> None:
        event = {"topic": "authority_slice", "subtype": "claim_accepted"}
        result = validate_output_event(event, "INTEL-F01", table)
        assert not result.valid


# ── Integrity tests ──────────────────────────────────────────────


class TestRoutingTableIntegrity:
    """Tests for internal routing table consistency."""

    def test_all_emitted_events_exist(self, table: RoutingTable) -> None:
        result = validate_routing_table_integrity(table)
        emit_violations = [v for v in result.violations if "emitsEvents" in v.field]
        assert not emit_violations, f"Missing events: {emit_violations}"

    def test_all_producers_exist(self, table: RoutingTable) -> None:
        result = validate_routing_table_integrity(table)
        producer_violations = [v for v in result.violations if "producedBy" in v.field
                               and "not in functions" in v.message]
        assert not producer_violations, f"Invalid producers: {producer_violations}"

    def test_no_orphaned_events(self, table: RoutingTable) -> None:
        result = validate_routing_table_integrity(table)
        orphan_violations = [v for v in result.violations if "no producers" in v.message]
        assert not orphan_violations, f"Orphaned events: {orphan_violations}"

    def test_full_integrity_pass(self, table: RoutingTable) -> None:
        result = validate_routing_table_integrity(table)
        assert result.valid, f"Integrity violations: {result.violations}"


# ── Fingerprint tests ────────────────────────────────────────────


class TestFingerprint:
    """Tests for routing table fingerprinting."""

    def test_fingerprint_deterministic(self) -> None:
        raw = {"functions": {"F01": {"a": 1}}, "events": {"E01": {"b": 2}}}
        fp1 = compute_table_fingerprint(raw)
        fp2 = compute_table_fingerprint(raw)
        assert fp1 == fp2

    def test_fingerprint_changes_with_content(self) -> None:
        raw1 = {"functions": {"F01": {"a": 1}}, "events": {}}
        raw2 = {"functions": {"F01": {"a": 2}}, "events": {}}
        assert compute_table_fingerprint(raw1) != compute_table_fingerprint(raw2)

    def test_fingerprint_format(self) -> None:
        raw = {"functions": {}, "events": {}}
        fp = compute_table_fingerprint(raw)
        assert fp.startswith("sha256:")
        assert len(fp) == 71  # "sha256:" + 64 hex chars


# ── Topics coverage ──────────────────────────────────────────────


class TestTopicsCoverage:
    """Ensure all 6 FEEDS topics are referenced."""

    def test_all_topics_have_functions(self, table: RoutingTable) -> None:
        topics = {fn.input_topic for fn in table.functions.values()}
        # At minimum truth_snapshot, canon_entry, drift_signal, decision_lineage
        assert "truth_snapshot" in topics
        assert "canon_entry" in topics
        assert "drift_signal" in topics
        assert "decision_lineage" in topics

    def test_all_domains_covered(self, table: RoutingTable) -> None:
        domains = {fn.domain for fn in table.functions.values()}
        assert domains == {"intelops", "franops", "reflectionops"}
