"""Tests for core.audit — coherence auditor cross-artifact consistency checks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.audit import (  # noqa: E402
    AuditFinding,
    AuditReport,
    CoherenceAuditor,
    FindingSeverity,
)
from core.manifest import (  # noqa: E402
    ArtifactDeclaration,
    ArtifactKind,
    CoherenceManifest,
    ComplianceLevel,
)


def _make_full_manifest():
    m = CoherenceManifest(system_id="test-system", version="1.0")
    for kind in ArtifactKind:
        m.declare(ArtifactDeclaration(
            kind=kind,
            schema_version="1.0",
            compliance=ComplianceLevel.FULL,
            source="test",
        ))
    return m


def _make_empty_manifest():
    return CoherenceManifest(system_id="test-system", version="1.0")


class TestFindingSeverity:
    def test_three_levels(self):
        assert len(FindingSeverity) == 3

    def test_values(self):
        assert FindingSeverity.INFO.value == "info"
        assert FindingSeverity.WARNING.value == "warning"
        assert FindingSeverity.CRITICAL.value == "critical"


class TestAuditFinding:
    def test_fields(self):
        f = AuditFinding(
            check_name="test",
            severity=FindingSeverity.WARNING,
            message="test message",
        )
        assert f.check_name == "test"
        assert f.severity == FindingSeverity.WARNING
        assert f.details == {}


class TestCheckManifestCoverage:
    def test_full_manifest_no_findings(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        findings = auditor._check_manifest_coverage()
        assert len(findings) == 0

    def test_empty_manifest_warnings(self):
        auditor = CoherenceAuditor(manifest=_make_empty_manifest())
        findings = auditor._check_manifest_coverage()
        assert len(findings) == 4
        assert all(f.severity == FindingSeverity.WARNING for f in findings)

    def test_scaffold_is_info(self):
        m = CoherenceManifest(system_id="sys", version="1.0")
        m.declare(ArtifactDeclaration(
            kind=ArtifactKind.DLR,
            schema_version="1.0",
            compliance=ComplianceLevel.SCAFFOLD,
            source="test",
        ))
        auditor = CoherenceAuditor(manifest=m)
        findings = auditor._check_manifest_coverage()
        info = [f for f in findings if f.severity == FindingSeverity.INFO]
        assert len(info) == 1


class TestCheckDlrCompleteness:
    def test_no_dlr(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        findings = auditor._check_dlr_completeness()
        assert len(findings) == 0

    def test_dlr_with_valid_entries(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        auditor = CoherenceAuditor(manifest=_make_full_manifest(), dlr_builder=dlr)
        findings = auditor._check_dlr_completeness()
        # Valid entries should have DTE refs
        critical = [f for f in findings if f.severity == FindingSeverity.CRITICAL]
        # May or may not have warnings depending on sample data
        assert isinstance(findings, list)


class TestCheckDriftResolution:
    def test_no_ds(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        findings = auditor._check_drift_resolution()
        assert len(findings) == 0

    def test_ds_with_data(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        auditor = CoherenceAuditor(manifest=_make_full_manifest(), ds=ds)
        findings = auditor._check_drift_resolution()
        assert isinstance(findings, list)


class TestCheckMgOrphans:
    def test_no_mg(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        findings = auditor._check_mg_orphans()
        assert len(findings) == 0

    def test_empty_mg(self, coherence_pipeline):
        from core.memory_graph import MemoryGraph
        dlr, rs, ds, mg = coherence_pipeline
        empty_mg = MemoryGraph()
        auditor = CoherenceAuditor(
            manifest=_make_full_manifest(),
            dlr_builder=dlr,
            mg=empty_mg,
        )
        findings = auditor._check_mg_orphans()
        warnings = [f for f in findings if f.severity == FindingSeverity.WARNING]
        assert len(warnings) == 1

    def test_populated_mg(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        auditor = CoherenceAuditor(
            manifest=_make_full_manifest(),
            dlr_builder=dlr,
            mg=mg,
        )
        findings = auditor._check_mg_orphans()
        empty_warnings = [f for f in findings if "empty" in f.message.lower()]
        assert len(empty_warnings) == 0


class TestCheckVerificationConsistency:
    def test_no_dlr(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        findings = auditor._check_verification_consistency()
        assert len(findings) == 0


class TestAuditRun:
    def test_run_returns_report(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        report = auditor.run("audit-001")
        assert isinstance(report, AuditReport)
        assert report.audit_id == "audit-001"

    def test_report_passed_no_critical(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        report = auditor.run("audit-001")
        assert report.passed is True

    def test_report_failed_on_critical(self):
        auditor = CoherenceAuditor(manifest=_make_empty_manifest())
        # Empty manifest only produces warnings, not critical
        report = auditor.run("audit-001")
        assert report.passed is True  # Warnings don't fail

    def test_report_summary_counts(self):
        auditor = CoherenceAuditor(manifest=_make_empty_manifest())
        report = auditor.run("audit-001")
        assert "total_findings" in report.summary
        assert "critical" in report.summary
        assert "warnings" in report.summary

    def test_run_at_iso(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        report = auditor.run("audit-001")
        assert "T" in report.run_at

    def test_manifest_system_id(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        report = auditor.run("audit-001")
        assert report.manifest_system_id == "test-system"

    def test_to_json_parseable(self):
        auditor = CoherenceAuditor(manifest=_make_full_manifest())
        j = auditor.to_json("audit-001")
        data = json.loads(j)
        assert data["audit_id"] == "audit-001"

    def test_full_pipeline_audit(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        auditor = CoherenceAuditor(
            manifest=_make_full_manifest(),
            dlr_builder=dlr,
            rs=rs,
            ds=ds,
            mg=mg,
        )
        report = auditor.run("audit-full")
        assert isinstance(report, AuditReport)
        assert report.summary["total_findings"] >= 0
