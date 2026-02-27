"""Tests for FEEDS canon — store, claim validator, memory graph writer."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from core.feeds.canon import CanonStore, ClaimValidator, MGWriter
from core.feeds import build_envelope, FeedTopic


# ── Helpers ───────────────────────────────────────────────────────

def _make_canon_entry(canon_id="CANON-2026-0001", version="1.0.0",
                      domain="security-operations", supersedes=None):
    entry = {
        "canonId": canon_id,
        "title": "Standard operating procedure for quarantine decisions",
        "claimIds": ["CLAIM-2026-0001", "CLAIM-2026-0002"],
        "blessedBy": "governance-engine",
        "blessedAt": "2026-02-27T09:00:00Z",
        "scope": {"domain": domain},
        "version": version,
        "seal": {"hash": "sha256:canon", "sealedAt": "2026-02-27T09:00:01Z", "version": 1},
    }
    if supersedes:
        entry["supersedes"] = supersedes
    return entry


def _make_claim(claim_id="CLAIM-001", half_life=None, created=None,
                confidence=None, status_light=None, contradicts=None):
    claim = {"claimId": claim_id}
    if half_life is not None:
        claim["halfLife"] = half_life
    if created is not None:
        claim["timestampCreated"] = created
    if confidence is not None:
        claim["confidence"] = {"score": confidence}
    if status_light is not None:
        claim["statusLight"] = status_light
    if contradicts is not None:
        claim["graph"] = {"contradicts": contradicts}
    return claim


def _make_events(packet_id="CP-2026-02-27-0001"):
    """Build a set of FEEDS events for graph testing."""
    ts_payload = {
        "snapshotId": "TS-graph-001",
        "capturedAt": "2026-02-27T10:00:00Z",
        "claims": [{"claimId": "CLAIM-2026-0001"}],
        "evidenceSummary": "Graph test evidence.",
        "coherenceScore": 85,
        "seal": {"hash": "sha256:ts", "sealedAt": "2026-02-27T10:00:01Z", "version": 1},
    }
    ds_payload = {
        "driftId": "DS-graph-001",
        "driftType": "freshness",
        "severity": "yellow",
        "detectedAt": "2026-02-27T11:00:00Z",
        "evidenceRefs": ["ref-001", "ref-002"],
        "recommendedPatchType": "ttl_change",
        "fingerprint": {"key": "graph:test", "version": "1"},
    }
    als_payload = {
        "sliceId": "ALS-graph-001",
        "authoritySource": "governance-engine",
        "authorityRole": "policy-owner",
        "scope": "security-operations",
        "claimsBlessed": ["CLAIM-2026-0001", "CLAIM-2026-0002"],
        "effectiveAt": "2026-02-27T09:00:00Z",
        "seal": {"hash": "sha256:als", "sealedAt": "2026-02-27T09:00:01Z", "version": 1},
    }
    ce_payload = _make_canon_entry()

    events = []
    for topic, payload in [
        (FeedTopic.TRUTH_SNAPSHOT, ts_payload),
        (FeedTopic.DRIFT_SIGNAL, ds_payload),
        (FeedTopic.AUTHORITY_SLICE, als_payload),
        (FeedTopic.CANON_ENTRY, ce_payload),
    ]:
        events.append(build_envelope(
            topic=topic, payload=payload, packet_id=packet_id,
            producer="test-graph", sequence=len(events),
        ))
    return events


# ── Canon Store Tests ─────────────────────────────────────────────

class TestCanonStore:
    def test_add_and_get(self, tmp_path):
        store = CanonStore(tmp_path / "canon.db")
        entry = _make_canon_entry()
        cid = store.add(entry)
        assert cid == "CANON-2026-0001"

        result = store.get(cid)
        assert result is not None
        assert result["canonId"] == "CANON-2026-0001"
        assert result["data"]["title"] == entry["title"]
        store.close()

    def test_list_entries(self, tmp_path):
        store = CanonStore(tmp_path / "canon.db")
        store.add(_make_canon_entry("CANON-2026-0001"))
        store.add(_make_canon_entry("CANON-2026-0002", domain="financial-ops"))

        all_entries = store.list_entries()
        assert len(all_entries) == 2

        filtered = store.list_entries(domain="financial-ops")
        assert len(filtered) == 1
        assert filtered[0]["canonId"] == "CANON-2026-0002"
        store.close()

    def test_supersedes_chain(self, tmp_path):
        store = CanonStore(tmp_path / "canon.db")
        store.add(_make_canon_entry("CANON-2026-0001", version="1.0.0"))
        store.add(_make_canon_entry("CANON-2026-0002", version="2.0.0",
                                    supersedes="CANON-2026-0001"))
        store.add(_make_canon_entry("CANON-2026-0003", version="3.0.0",
                                    supersedes="CANON-2026-0002"))

        # Verify superseded_by pointer was set
        v1 = store.get("CANON-2026-0001")
        assert v1["supersededBy"] == "CANON-2026-0002"

        v2 = store.get("CANON-2026-0002")
        assert v2["supersededBy"] == "CANON-2026-0003"

        # Version chain from v3 backward
        chain = store.get_version_chain("CANON-2026-0003")
        assert len(chain) == 3
        assert chain[0]["canonId"] == "CANON-2026-0003"
        assert chain[2]["canonId"] == "CANON-2026-0001"
        store.close()

    def test_cache_invalidation_event(self, tmp_topics_root, tmp_path):
        store = CanonStore(
            tmp_path / "canon.db",
            topics_root=tmp_topics_root,
        )
        store.add(_make_canon_entry())
        store.close()

        ce_inbox = tmp_topics_root / "canon_entry" / "inbox"
        assert len(list(ce_inbox.glob("*.json"))) == 1

    def test_persistence(self, tmp_path):
        db = tmp_path / "persist.db"
        s1 = CanonStore(db)
        s1.add(_make_canon_entry())
        s1.close()

        s2 = CanonStore(db)
        assert s2.get("CANON-2026-0001") is not None
        s2.close()


# ── Claim Validator Tests ─────────────────────────────────────────

class TestClaimValidator:
    def test_contradiction_detected(self):
        canon_claims = [{"claimId": "CANON-C1"}]
        validator = ClaimValidator(canon_claims=canon_claims)
        claim = _make_claim("NEW-C1", contradicts=["CANON-C1"])
        issues = validator.validate_claim(claim)

        assert len(issues) == 1
        assert issues[0]["type"] == "contradiction"
        assert "CANON-C1" in issues[0]["detail"]

    def test_no_contradiction(self):
        canon_claims = [{"claimId": "CANON-C1"}]
        validator = ClaimValidator(canon_claims=canon_claims)
        claim = _make_claim("NEW-C2", contradicts=["UNRELATED-C99"])
        issues = validator.validate_claim(claim)

        assert len(issues) == 0

    def test_ttl_expired(self):
        validator = ClaimValidator()
        old_time = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        claim = _make_claim(
            "STALE-C1",
            half_life={"value": 2, "unit": "hours"},
            created=old_time,
        )
        issues = validator.validate_claim(claim)

        assert len(issues) == 1
        assert issues[0]["type"] == "expired"

    def test_ttl_fresh(self):
        validator = ClaimValidator()
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        claim = _make_claim(
            "FRESH-C1",
            half_life={"value": 24, "unit": "hours"},
            created=recent,
        )
        issues = validator.validate_claim(claim)

        assert len(issues) == 0

    def test_confidence_inconsistency_high_red(self):
        validator = ClaimValidator()
        claim = _make_claim("INC-C1", confidence=0.95, status_light="red")
        issues = validator.validate_claim(claim)

        assert len(issues) == 1
        assert issues[0]["type"] == "inconsistent"

    def test_confidence_inconsistency_low_green(self):
        validator = ClaimValidator()
        claim = _make_claim("INC-C2", confidence=0.1, status_light="green")
        issues = validator.validate_claim(claim)

        assert len(issues) == 1
        assert issues[0]["type"] == "inconsistent"

    def test_consistent_claim_no_issues(self):
        validator = ClaimValidator()
        claim = _make_claim("OK-C1", confidence=0.9, status_light="green")
        issues = validator.validate_claim(claim)

        assert len(issues) == 0

    def test_build_drift_signal(self):
        validator = ClaimValidator()
        issue = {
            "type": "contradiction",
            "claimId": "CLAIM-001",
            "detail": "Test contradiction",
            "severity": "red",
        }
        ds = validator.build_drift_signal(issue, packet_id="CP-2026-02-27-0001")

        assert "driftId" in ds
        assert ds["driftType"] == "authority_mismatch"
        assert ds["severity"] == "red"
        assert "fingerprint" in ds


# ── MG Writer Tests ───────────────────────────────────────────────

class TestMGWriter:
    def test_graph_structure(self):
        writer = MGWriter()
        events = _make_events()
        graph = writer.build_graph("CP-2026-02-27-0001", events)

        assert graph["packetId"] == "CP-2026-02-27-0001"
        assert len(graph["nodes"]) >= 5  # packet + 4 events
        assert len(graph["edges"]) >= 4  # at least 4 packet_contains

    def test_packet_contains_edges(self):
        writer = MGWriter()
        events = _make_events()
        graph = writer.build_graph("CP-2026-02-27-0001", events)

        pc_edges = [e for e in graph["edges"] if e["kind"] == "packet_contains"]
        assert len(pc_edges) == len(events)

    def test_ds_detected_from_edges(self):
        writer = MGWriter()
        events = _make_events()
        graph = writer.build_graph("CP-2026-02-27-0001", events)

        ds_edges = [e for e in graph["edges"] if e["kind"] == "ds_detected_from"]
        assert len(ds_edges) == 2  # 2 evidence refs in DS payload

    def test_ce_resolves_edges(self):
        writer = MGWriter()
        events = _make_events()
        graph = writer.build_graph("CP-2026-02-27-0001", events)

        ce_edges = [e for e in graph["edges"] if e["kind"] == "ce_resolves"]
        assert len(ce_edges) == 2  # 2 claim IDs in CE payload

    def test_als_authorizes_edges(self):
        writer = MGWriter()
        events = _make_events()
        graph = writer.build_graph("CP-2026-02-27-0001", events)

        als_edges = [e for e in graph["edges"] if e["kind"] == "als_authorizes"]
        assert len(als_edges) == 2  # 2 blessed claims in ALS payload

    def test_file_creation(self, tmp_path):
        writer = MGWriter()
        events = _make_events()
        path = writer.write_graph("CP-2026-02-27-0001", events, tmp_path)

        assert path.exists()
        assert path.name == "CP-2026-02-27-0001_graph.json"

        data = json.loads(path.read_text())
        assert data["packetId"] == "CP-2026-02-27-0001"

    def test_valid_json(self, tmp_path):
        writer = MGWriter()
        events = _make_events()
        path = writer.write_graph("CP-2026-02-27-0001", events, tmp_path)

        data = json.loads(path.read_text())
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_idempotent(self, tmp_path):
        writer = MGWriter()
        events = _make_events()

        path1 = writer.write_graph("CP-2026-02-27-0001", events, tmp_path)
        content1 = path1.read_text()

        path2 = writer.write_graph("CP-2026-02-27-0001", events, tmp_path)
        content2 = path2.read_text()

        assert content1 == content2
