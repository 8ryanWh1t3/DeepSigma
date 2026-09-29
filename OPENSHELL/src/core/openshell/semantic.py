"""Deterministic semantic checks before an OpenShell policy reaches runtime.

This is intentionally a conservative RESONATOR-facing adapter, not a claim that
it replaces the full RESONATOR engine.  It generates machine-readable findings
that RESONATOR can ingest or supersede later.
"""

from __future__ import annotations

from .models import (
    AccessMode,
    AgentMissionContract,
    PolicyProjection,
    SemanticAssessment,
    SemanticFinding,
)


class OpenShellSemanticValidator:
    """Check mission intent for risky or incoherent permission patterns."""

    def assess(
        self,
        contract: AgentMissionContract,
        projection: PolicyProjection,
    ) -> SemanticAssessment:
        findings: list[SemanticFinding] = []

        # Mission contract validation is first and deterministic.
        try:
            contract.validate()
        except ValueError as exc:
            findings.append(
                SemanticFinding("CONTRACT_INVALID", "critical", str(exc))
            )
            return SemanticAssessment(False, findings)

        if not contract.evidence_refs:
            findings.append(
                SemanticFinding(
                    "EVIDENCE_GAP",
                    "warning",
                    "Mission contract has no evidence_refs; provenance is weak.",
                )
            )

        if not contract.kill_conditions:
            findings.append(
                SemanticFinding(
                    "KILL_CONDITION_GAP",
                    "warning",
                    "No explicit kill condition is attached to the agent mission.",
                )
            )

        if contract.blast_radius_tier in {"medium", "large"} and not contract.human_approval_required:
            findings.append(
                SemanticFinding(
                    "HUMAN_GATE_REQUIRED",
                    "critical",
                    "Medium/large blast-radius contracts must require human approval.",
                )
            )

        for endpoint in contract.endpoints:
            if endpoint.access in {AccessMode.READ_WRITE.value, AccessMode.FULL.value}:
                if not endpoint.rules:
                    findings.append(
                        SemanticFinding(
                            "BROAD_NETWORK_WRITE",
                            "warning",
                            f"{endpoint.name} grants {endpoint.access} without path-scoped L7 rules.",
                        )
                    )
            if "*" in endpoint.host or "?" in endpoint.host:
                findings.append(
                    SemanticFinding(
                        "WILDCARD_NETWORK_SCOPE",
                        "warning",
                        f"{endpoint.name} uses wildcard host {endpoint.host!r}.",
                    )
                )
            if endpoint.credential_bound and endpoint.protocol != "rest":
                findings.append(
                    SemanticFinding(
                        "CREDENTIAL_BOUNDARY_WEAK",
                        "critical",
                        f"{endpoint.name} is credential-bound without REST inspection.",
                    )
                )

        if set(contract.read_write_paths) & set(contract.read_only_paths):
            findings.append(
                SemanticFinding(
                    "FILESYSTEM_CONTRADICTION",
                    "critical",
                    "A filesystem path appears in both read-only and read-write sets.",
                )
            )

        critical = [f for f in findings if f.severity == "critical"]
        return SemanticAssessment(passed=not critical, findings=findings)


__all__ = ["OpenShellSemanticValidator"]
