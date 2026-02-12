"""Coherence Manifest — system-level declaration of artifact coverage.

A CoherenceManifest declares which of the four canonical artifacts
(DLR, RS, DS, MG) a system produces, their schema versions, data
sources, refresh cadences, and compliance status.  It serves as the
"bill of materials" for governance and enables the audit loop to
know what to check.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ArtifactKind(str, Enum):
    """The four canonical Coherence Ops artifacts."""

    DLR = "dlr"
    RS = "rs"
    DS = "ds"
    MG = "mg"


class ComplianceLevel(str, Enum):
    """How fully an artifact meets the specification."""

    FULL = "full"
    PARTIAL = "partial"
    SCAFFOLD = "scaffold"
    MISSING = "missing"


@dataclass
class ArtifactDeclaration:
    """One entry in the manifest — describes a single artifact."""

    kind: ArtifactKind
    schema_version: str
    compliance: ComplianceLevel
    source: str
    refresh_cadence_seconds: Optional[int] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class CoherenceManifest:
    """Top-level manifest for a Coherence Ops deployment.

    Attributes:
        system_id: Unique identifier for the system.
        version: Manifest version string.
        created_at: ISO-8601 timestamp of creation.
        artifacts: Declarations for each artifact the system produces.
        metadata: Free-form metadata dict.
    """

    system_id: str
    version: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    artifacts: List[ArtifactDeclaration] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Builder helpers
    # ------------------------------------------------------------------

    def declare(self, declaration: ArtifactDeclaration) -> CoherenceManifest:
        """Add or replace an artifact declaration (by kind)."""
        self.artifacts = [
            a for a in self.artifacts if a.kind != declaration.kind
        ]
        self.artifacts.append(declaration)
        return self

    def get(self, kind: ArtifactKind) -> Optional[ArtifactDeclaration]:
        """Return the declaration for *kind*, or ``None``."""
        for a in self.artifacts:
            if a.kind == kind:
                return a
        return None

    def coverage(self) -> Dict[str, str]:
        """Return ``{artifact_kind: compliance_level}`` for all four artifacts."""
        result: Dict[str, str] = {}
        for kind in ArtifactKind:
            decl = self.get(kind)
            result[kind.value] = (
                decl.compliance.value if decl else ComplianceLevel.MISSING.value
            )
        return result

    def is_complete(self) -> bool:
        """Return ``True`` if every artifact is at least PARTIAL."""
        for kind in ArtifactKind:
            decl = self.get(kind)
            if decl is None or decl.compliance == ComplianceLevel.MISSING:
                return False
        return True

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict (JSON-ready)."""
        raw = asdict(self)
        # Enum values → strings
        for art in raw.get("artifacts", []):
            art["kind"] = art["kind"].value if hasattr(art["kind"], "value") else art["kind"]
            art["compliance"] = (
                art["compliance"].value
                if hasattr(art["compliance"], "value")
                else art["compliance"]
            )
        return raw

    def to_json(self, indent: int = 2) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: str) -> None:
        """Write manifest JSON to *path*."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding="utf-8")
        logger.info("Manifest saved to %s", path)

    @classmethod
    def load(cls, path: str) -> CoherenceManifest:
        """Load a manifest from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        artifacts = [
            ArtifactDeclaration(
                kind=ArtifactKind(a["kind"]),
                schema_version=a["schema_version"],
                compliance=ComplianceLevel(a["compliance"]),
                source=a["source"],
                refresh_cadence_seconds=a.get("refresh_cadence_seconds"),
                description=a.get("description", ""),
                tags=a.get("tags", []),
            )
            for a in data.get("artifacts", [])
        ]
        return cls(
            system_id=data["system_id"],
            version=data["version"],
            created_at=data.get("created_at", ""),
            artifacts=artifacts,
            metadata=data.get("metadata", {}),
        )
