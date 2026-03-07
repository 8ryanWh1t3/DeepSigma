"""Tests for core.manifest — coherence manifest artifact coverage."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.manifest import (  # noqa: E402
    ArtifactDeclaration,
    ArtifactKind,
    ComplianceLevel,
    CoherenceManifest,
)


def _make_declaration(kind=ArtifactKind.DLR, compliance=ComplianceLevel.FULL):
    return ArtifactDeclaration(
        kind=kind,
        schema_version="1.0",
        compliance=compliance,
        source="test",
    )


def _make_full_manifest():
    m = CoherenceManifest(system_id="test-system", version="1.0")
    for kind in ArtifactKind:
        m.declare(_make_declaration(kind=kind))
    return m


class TestArtifactKind:
    def test_four_kinds(self):
        assert len(ArtifactKind) == 4

    def test_values(self):
        assert ArtifactKind.DLR.value == "dlr"
        assert ArtifactKind.RS.value == "rs"
        assert ArtifactKind.DS.value == "ds"
        assert ArtifactKind.MG.value == "mg"

    def test_str_enum(self):
        assert isinstance(ArtifactKind.DLR, str)


class TestComplianceLevel:
    def test_four_levels(self):
        assert len(ComplianceLevel) == 4

    def test_values(self):
        assert ComplianceLevel.FULL.value == "full"
        assert ComplianceLevel.PARTIAL.value == "partial"
        assert ComplianceLevel.SCAFFOLD.value == "scaffold"
        assert ComplianceLevel.MISSING.value == "missing"


class TestArtifactDeclaration:
    def test_fields(self):
        d = _make_declaration()
        assert d.kind == ArtifactKind.DLR
        assert d.schema_version == "1.0"
        assert d.compliance == ComplianceLevel.FULL
        assert d.source == "test"

    def test_optional_fields(self):
        d = _make_declaration()
        assert d.refresh_cadence_seconds is None
        assert d.description == ""
        assert d.tags == []


class TestCoherenceManifest:
    def test_declare_adds(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        m.declare(_make_declaration(kind=ArtifactKind.DLR))
        assert m.get(ArtifactKind.DLR) is not None

    def test_declare_replaces_by_kind(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        m.declare(_make_declaration(kind=ArtifactKind.DLR, compliance=ComplianceLevel.SCAFFOLD))
        m.declare(_make_declaration(kind=ArtifactKind.DLR, compliance=ComplianceLevel.FULL))
        assert m.get(ArtifactKind.DLR).compliance == ComplianceLevel.FULL
        assert len(m.artifacts) == 1

    def test_get_missing_returns_none(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        assert m.get(ArtifactKind.RS) is None

    def test_coverage_all_missing(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        cov = m.coverage()
        assert all(v == "missing" for v in cov.values())
        assert len(cov) == 4

    def test_coverage_full(self):
        m = _make_full_manifest()
        cov = m.coverage()
        assert all(v == "full" for v in cov.values())

    def test_is_complete_true(self):
        m = _make_full_manifest()
        assert m.is_complete() is True

    def test_is_complete_false_missing(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        m.declare(_make_declaration(kind=ArtifactKind.DLR))
        assert m.is_complete() is False

    def test_is_complete_false_missing_compliance(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        for kind in ArtifactKind:
            m.declare(_make_declaration(kind=kind, compliance=ComplianceLevel.MISSING))
        assert m.is_complete() is False

    def test_is_complete_partial_passes(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        for kind in ArtifactKind:
            m.declare(_make_declaration(kind=kind, compliance=ComplianceLevel.PARTIAL))
        assert m.is_complete() is True

    def test_to_dict(self):
        m = _make_full_manifest()
        d = m.to_dict()
        assert d["system_id"] == "test-system"
        assert d["version"] == "1.0"
        assert len(d["artifacts"]) == 4
        # Enum values should be strings
        assert d["artifacts"][0]["kind"] in ("dlr", "rs", "ds", "mg")

    def test_to_json_parseable(self):
        m = _make_full_manifest()
        j = m.to_json()
        data = json.loads(j)
        assert data["system_id"] == "test-system"

    def test_save_and_load_round_trip(self, tmp_path):
        m = _make_full_manifest()
        m.metadata = {"env": "test"}
        path = str(tmp_path / "manifest.json")
        m.save(path)
        loaded = CoherenceManifest.load(path)
        assert loaded.system_id == "test-system"
        assert loaded.version == "1.0"
        assert len(loaded.artifacts) == 4
        assert loaded.metadata == {"env": "test"}

    def test_created_at_iso(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        assert "T" in m.created_at

    def test_declare_returns_self(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        result = m.declare(_make_declaration())
        assert result is m
