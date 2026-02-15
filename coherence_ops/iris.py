from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


# NOTE: This module must remain import-safe because coherence_ops/__init__.py exports
# QueryType, IRISQuery, IRISResponse, IRISConfig, and IRISEngine.


class QueryType(str, Enum):
    """Supported IRIS query types."""

    WHY = "WHY"
    WHAT_CHANGED = "WHAT_CHANGED"
    WHAT_DRIFTED = "WHAT_DRIFTED"
    RECALL = "RECALL"
    STATUS = "STATUS"


class ResolutionStatus(str, Enum):
    """Resolution status returned by IRIS."""

    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


@dataclass
class ProvenanceLink:
    artifact: str
    ref_id: str
    role: str
    detail: str = ""


@dataclass
class IRISQuery:
    query_type: QueryType
    text: str = ""
    episode_id: str = ""
    decision_type: str = ""
    time_window_seconds: float = 3600.0
    limit: int = 20
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IRISResponse:
    query_id: str
    query_type: QueryType
    status: ResolutionStatus
    summary: str
    data: Dict[str, Any] = field(default_factory=dict)
    provenance_chain: List[ProvenanceLink] = field(default_factory=list)
    confidence: float = 0.0
    resolved_at: str = ""
    elapsed_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class IRISConfig:
    response_time_target_ms: float = 60_000

    def validate(self) -> List[str]:
        issues: List[str] = []
        if self.response_time_target_ms <= 0:
            issues.append("response_time_target_ms must be positive")
        return issues


class IRISEngine:
    """Minimal operator query resolution engine (stub)."""

    def __init__(
        self,
        dlr_builder: object | None = None,
        rs: object | None = None,
        ds: object | None = None,
        mg: object | None = None,
        config: IRISConfig | None = None,
    ) -> None:
        self.dlr = dlr_builder
        self.rs = rs
        self.ds = ds
        self.mg = mg
        self.config = config or IRISConfig()

        issues = self.config.validate()
        if issues:
            raise ValueError(f"Invalid IRISConfig: {'; '.join(issues)}")

    def resolve(self, query: IRISQuery) -> IRISResponse:
        """Return a stub response to keep module import-safe."""

        return IRISResponse(
            query_id="stub",
            query_type=query.query_type,
            status=ResolutionStatus.NOT_FOUND,
            summary="IRIS stub resolver (no artefacts wired)",
            warnings=["IRIS engine is not wired to DLR/RS/DS/MG"],
        )
