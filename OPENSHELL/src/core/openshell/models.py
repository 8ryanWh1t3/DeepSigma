"""Typed models for the Deep Sigma ↔ NVIDIA OpenShell integration.

The objects in this module intentionally keep Deep Sigma mission/authority
semantics separate from OpenShell's enforcement syntax.  The compiler is the
one-way boundary that projects a governed mission contract into an OpenShell
policy.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ContractValidationError(ValueError):
    """Raised when a mission contract cannot be projected safely."""


class AccessMode(str, Enum):
    """OpenShell endpoint access presets used by the compiler."""

    READ_ONLY = "read-only"
    READ_WRITE = "read-write"
    FULL = "full"


class PlanStatus(str, Enum):
    """Lifecycle state for a governed OpenShell plan."""

    BLOCKED = "blocked"
    PENDING_APPROVAL = "pending_approval"
    READY = "ready"
    APPLIED = "applied"
    REQUIRES_RECREATE = "requires_recreate"


@dataclass(frozen=True)
class L7Rule:
    """Fine-grained HTTP rule for an inspected REST endpoint."""

    method: str
    path: str
    allow: bool = True

    def validate(self) -> None:
        if not self.method or not self.path:
            raise ContractValidationError("L7 rules require method and path")
        if not self.path.startswith("/"):
            raise ContractValidationError("L7 rule path must begin with '/'")


@dataclass(frozen=True)
class EndpointPermission:
    """A network destination an agent may reach from an OpenShell sandbox."""

    name: str
    host: str
    port: int = 443
    protocol: Optional[str] = "rest"
    enforcement: Optional[str] = "enforce"
    tls: Optional[str] = "terminate"
    access: Optional[str] = AccessMode.READ_ONLY.value
    binaries: List[str] = field(default_factory=list)
    rules: List[L7Rule] = field(default_factory=list)
    credential_bound: bool = False
    description: str = ""

    def validate(self) -> None:
        if not self.name.strip():
            raise ContractValidationError("endpoint permission requires a name")
        if not self.host.strip():
            raise ContractValidationError("endpoint permission requires a host")
        if not 1 <= int(self.port) <= 65535:
            raise ContractValidationError(f"invalid endpoint port: {self.port}")
        if self.access not in {
            None,
            AccessMode.READ_ONLY.value,
            AccessMode.READ_WRITE.value,
            AccessMode.FULL.value,
        }:
            raise ContractValidationError(f"unsupported access preset: {self.access}")
        # NVIDIA explicitly recommends exact hostnames because wildcard DNS names
        # increase exfiltration surface.  Make that mandatory when credentials bind.
        if self.credential_bound and ("*" in self.host or "?" in self.host):
            raise ContractValidationError(
                "credential-bound endpoints must use an exact hostname"
            )
        for rule in self.rules:
            rule.validate()
        if self.rules and self.protocol not in {"rest", "sql", "graphql", "jsonrpc", "mcp"}:
            raise ContractValidationError(
                "L7 rules require an inspectable application protocol"
            )


@dataclass
class AgentMissionContract:
    """Deep Sigma mission contract projected into OpenShell enforcement.

    This is the DKO/DSAL-facing boundary.  It records *why* access exists before
    the compiler translates it into the lower-level OpenShell policy that says
    *what* can be touched.
    """

    contract_id: str
    episode_id: str
    mission: str
    objective: str
    agent_id: str
    actor_id: str
    command: List[str]
    authority_scope: str
    role: str = "agent"
    blast_radius_tier: str = "small"
    read_only_paths: List[str] = field(default_factory=list)
    read_write_paths: List[str] = field(default_factory=list)
    endpoints: List[EndpointPermission] = field(default_factory=list)
    include_workdir: bool = True
    process_user: Optional[str] = None
    process_group: Optional[str] = None
    assumptions: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    kill_conditions: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)
    human_approval_required: bool = False
    sandbox_image: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        required = {
            "contract_id": self.contract_id,
            "episode_id": self.episode_id,
            "mission": self.mission,
            "objective": self.objective,
            "agent_id": self.agent_id,
            "actor_id": self.actor_id,
            "authority_scope": self.authority_scope,
        }
        missing = [k for k, v in required.items() if not str(v).strip()]
        if missing:
            raise ContractValidationError(
                "missing required mission contract fields: " + ", ".join(missing)
            )
        if not self.command or not all(str(x).strip() for x in self.command):
            raise ContractValidationError("command must contain at least one non-empty token")
        if self.blast_radius_tier not in {"tiny", "small", "medium", "large"}:
            raise ContractValidationError(
                f"unsupported blast radius tier: {self.blast_radius_tier}"
            )
        ro = set(self.read_only_paths)
        rw = set(self.read_write_paths)
        overlap = sorted(ro & rw)
        if overlap:
            raise ContractValidationError(
                "paths cannot be both read-only and read-write: " + ", ".join(overlap)
            )
        for path in ro | rw:
            if not path.startswith("/"):
                raise ContractValidationError(
                    f"filesystem policy paths must be absolute: {path}"
                )
        endpoint_names: set[str] = set()
        for endpoint in self.endpoints:
            endpoint.validate()
            key = _safe_key(endpoint.name)
            if key in endpoint_names:
                raise ContractValidationError(
                    f"duplicate endpoint permission name after normalization: {endpoint.name}"
                )
            endpoint_names.add(key)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data

    def canonical_hash(self) -> str:
        payload = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dko(self) -> Dict[str, Any]:
        """Project the contract into a portable DKO-shaped object.

        This does not claim to be the final DSAL grammar.  It preserves the
        semantic fields required for a later lossless DSAL encoding.
        """
        return {
            "kind": "AgentMissionContract",
            "id": self.contract_id,
            "episode": self.episode_id,
            "mission": {
                "name": self.mission,
                "objective": self.objective,
                "expected_outputs": list(self.expected_outputs),
            },
            "agent": {
                "id": self.agent_id,
                "actor_id": self.actor_id,
                "role": self.role,
                "command": list(self.command),
            },
            "authority": {
                "scope": self.authority_scope,
                "blast_radius_tier": self.blast_radius_tier,
                "human_approval_required": self.human_approval_required,
            },
            "evidence": list(self.evidence_refs),
            "assumptions": list(self.assumptions),
            "kill_conditions": list(self.kill_conditions),
            "openshell_projection": {
                "read_only_paths": list(self.read_only_paths),
                "read_write_paths": list(self.read_write_paths),
                "endpoints": [asdict(e) for e in self.endpoints],
            },
            "contract_hash": self.canonical_hash(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class PolicyProjection:
    contract_id: str
    contract_hash: str
    policy: Dict[str, Any]
    yaml_text: str
    policy_hash: str
    static_hash: str
    dynamic_hash: str


@dataclass(frozen=True)
class PolicyDelta:
    static_changed: bool
    dynamic_changed: bool
    expands_access: bool
    reasons: List[str] = field(default_factory=list)

    @property
    def requires_recreate(self) -> bool:
        return self.static_changed


@dataclass(frozen=True)
class SemanticFinding:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class SemanticAssessment:
    passed: bool
    findings: List[SemanticFinding] = field(default_factory=list)


@dataclass(frozen=True)
class AuthorityDecision:
    verdict: str
    gate_id: str = ""
    reason: str = ""
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    escalation_target: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.verdict == "ALLOW"


@dataclass
class GovernedPlan:
    plan_id: str
    sandbox_name: str
    contract: AgentMissionContract
    projection: PolicyProjection
    semantic: SemanticAssessment
    authority: AuthorityDecision
    delta: PolicyDelta
    status: str
    requires_human_approval: bool
    created_at: str
    reasons: List[str] = field(default_factory=list)
    applied_at: Optional[str] = None
    approved_by: Optional[str] = None
    runtime_receipt: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OpenShellAuditEvent:
    event_id: str
    timestamp: str
    sandbox_name: str
    decision: str
    action: str
    binary: str = ""
    host: str = ""
    port: Optional[int] = None
    method: str = ""
    path: str = ""
    rule: str = ""
    reason: str = ""
    source: str = "openshell"
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def denied(self) -> bool:
        return self.decision.upper() in {"DENY", "DENIED", "BLOCK", "BLOCKED"}


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_key(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "rule"


__all__ = [
    "AccessMode",
    "AgentMissionContract",
    "AuthorityDecision",
    "ContractValidationError",
    "EndpointPermission",
    "GovernedPlan",
    "L7Rule",
    "OpenShellAuditEvent",
    "PlanStatus",
    "PolicyDelta",
    "PolicyProjection",
    "SemanticAssessment",
    "SemanticFinding",
    "canonical_hash",
    "_safe_key",
]
