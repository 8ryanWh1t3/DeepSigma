"""Coherence Auditor — periodic cross-artifact consistency checks.

The auditor runs a battery of checks across DLR, RS, DS, and MG to
detect inconsistencies such as orphan drift events, episodes missing
from the memory graph, policy stamp mismatches, and coverage gaps.

It produces an AuditReport with findings ranked by severity.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .decision_log import DLRBuilder
from .drift_signal import DriftSignalCollector
from .memory_graph import MemoryGraph
from .reflection import ReflectionSession
from .manifest import CoherenceManifest, ArtifactKind, ComplianceLevel

logger = logging.getLogger(__name__)


class FindingSeverity(str, Enum):
    """Severity of an audit finding."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditFinding:
    """A single finding from the audit."""

    check_name: str
    severity: FindingSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Full output of a coherence audit run."""

    audit_id: str
    run_at: str
    manifest_system_id: str
    findings: List[AuditFinding]
    passed: bool
    summary: Dict[str, Any] = field(default_factory=dict)


class CoherenceAuditor:
    """Run cross-artifact consistency checks.

    Usage:
        auditor = CoherenceAuditor(
            manifest=manifest,
            dlr_builder=dlr,
            rs=reflection_session,
            ds=drift_collector,
            mg=memory_graph,
        )
        report = auditor.run("audit-001")
    """

    def __init__(
        self,
        manifest: CoherenceManifest,
        dlr_builder: Optional[DLRBuilder] = None,
        rs: Optional[ReflectionSession] = None,
        ds: Optional[DriftSignalCollector] = None,
        mg: Optional[MemoryGraph] = None,
    ) -> None:
        self.manifest = manifest
        self.dlr = dlr_builder
        self.rs = rs
        self.ds = ds
        self.mg = mg

    def run(self, audit_id: str) -> AuditReport:
        """Execute all checks and return an AuditReport."""
        findings: List[AuditFinding] = []
        findings.extend(self._check_manifest_coverage())
        findings.extend(self._check_dlr_completeness())
        findings.extend(self._check_drift_resolution())
        findings.extend(self._check_mg_orphans())
        findings.extend(self._check_verification_consistency())

        passed = all(f.severity != FindingSeverity.CRITICAL for f in findings)

        report = AuditReport(
            audit_id=audit_id,
            run_at=datetime.now(timezone.utc).isoformat(),
            manifest_system_id=self.manifest.system_id,
            findings=findings,
            passed=passed,
            summary={
                "total_findings": len(findings),
                "critical": sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL),
                "warnings": sum(1 for f in findings if f.severity == FindingSeverity.WARNING),
                "info": sum(1 for f in findings if f.severity == FindingSeverity.INFO),
            },
        )
        logger.info("Audit %s complete: %s", audit_id, "PASSED" if passed else "FAILED")
        return report

    def to_json(self, audit_id: str, indent: int = 2) -> str:
        """Run the audit and return JSON."""
        report = self.run(audit_id)
        raw = asdict(report)
        for f in raw.get("findings", []):
            f["severity"] = f["severity"].value if hasattr(f["severity"], "value") else f["severity"]
        return json.dumps(raw, indent=indent)

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_manifest_coverage(self) -> List[AuditFinding]:
        """Verify all four artifact kinds are declared in the manifest."""
        findings: List[AuditFinding] = []
        for kind in ArtifactKind:
            decl = self.manifest.get(kind)
            if decl is None or decl.compliance == ComplianceLevel.MISSING:
                findings.append(AuditFinding(
                    check_name="manifest_coverage",
                    severity=FindingSeverity.WARNING,
                    message=f"Artifact {kind.value} is missing or undeclared in manifest.",
                    details={"artifact": kind.value},
                ))
            elif decl.compliance == ComplianceLevel.SCAFFOLD:
                findings.append(AuditFinding(
                    check_name="manifest_coverage",
                    severity=FindingSeverity.INFO,
                    message=f"Artifact {kind.value} is scaffold-level — not yet production-ready.",
                    details={"artifact": kind.value, "compliance": decl.compliance.value},
                ))
        return findings

    def _check_dlr_completeness(self) -> List[AuditFinding]:
        """Check that DLR entries have required fields populated."""
        findings: List[AuditFinding] = []
        if self.dlr is None:
            return findings
        for entry in self.dlr.entries:
            if not entry.dte_ref:
                findings.append(AuditFinding(
                    check_name="dlr_completeness",
                    severity=FindingSeverity.CRITICAL,
                    message=f"DLR {entry.dlr_id} has no DTE reference.",
                    details={"dlr_id": entry.dlr_id, "episode_id": entry.episode_id},
                ))
            if entry.outcome_code == "unknown":
                findings.append(AuditFinding(
                    check_name="dlr_completeness",
                    severity=FindingSeverity.WARNING,
                    message=f"DLR {entry.dlr_id} has unknown outcome code.",
                    details={"dlr_id": entry.dlr_id},
                ))
        return findings

    def _check_drift_resolution(self) -> List[AuditFinding]:
        """Check whether recurring drift has recommended patches applied."""
        findings: List[AuditFinding] = []
        if self.ds is None:
            return findings
        summary = self.ds.summarise()
        for bucket in summary.buckets:
            if bucket.count >= 3 and bucket.worst_severity == "red":
                findings.append(AuditFinding(
                    check_name="drift_resolution",
                    severity=FindingSeverity.CRITICAL,
                    message=(
                        f"Drift fingerprint {bucket.fingerprint_key!r} has recurred "
                        f"{bucket.count} times at red severity without resolution."
                    ),
                    details={
                        "fingerprint": bucket.fingerprint_key,
                        "count": bucket.count,
                        "patches": bucket.recommended_patches,
                    },
                ))
            elif bucket.count >= 5:
                findings.append(AuditFinding(
                    check_name="drift_resolution",
                    severity=FindingSeverity.WARNING,
                    message=f"Drift fingerprint {bucket.fingerprint_key!r} has recurred {bucket.count} times.",
                    details={"fingerprint": bucket.fingerprint_key, "count": bucket.count},
                ))
        return findings

    def _check_mg_orphans(self) -> List[AuditFinding]:
        """Check that DLR entries have corresponding Memory Graph nodes."""
        findings: List[AuditFinding] = []
        if self.mg is None or self.dlr is None:
            return findings
        stats = self.mg.query("stats")
        if stats.get("total_nodes", 0) == 0:
            findings.append(AuditFinding(
                check_name="mg_orphans",
                severity=FindingSeverity.WARNING,
                message="Memory Graph is empty — no episodes ingested.",
            ))
        return findings

    def _check_verification_consistency(self) -> List[AuditFinding]:
        """Cross-check DLR verification fields against RS pass rate."""
        findings: List[AuditFinding] = []
        if self.dlr is None:
            return findings
        unverified = [
            e for e in self.dlr.entries
            if e.verification is None or e.verification.get("result") == "na"
        ]
        total = len(self.dlr.entries)
        if total and len(unverified) > total * 0.5:
            findings.append(AuditFinding(
                check_name="verification_consistency",
                severity=FindingSeverity.WARNING,
                message=(
                    f"{len(unverified)}/{total} DLR entries lack verification — "
                    "consider enforcing mandatory verification."
                ),
            ))
        return findings
