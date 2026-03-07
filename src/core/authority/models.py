"""AuthorityOps typed models — dataclasses and enums for authority evaluation.

All objects mirror the authorityops.schema.json definitions.
Python uses snake_case; JSON schema uses camelCase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AuthorityVerdict(str, Enum):
    """Terminal verdict of an authority evaluation."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"
    EXPIRED = "EXPIRED"
    MISSING_REASONING = "MISSING_REASONING"
    KILL_SWITCH_ACTIVE = "KILL_SWITCH_ACTIVE"


class ActorType(str, Enum):
    """Type of actor requesting authority."""

    AGENT = "agent"
    HUMAN = "human"
    SYSTEM = "system"
    SERVICE = "service"


class ConstraintType(str, Enum):
    """Types of policy constraint."""

    TIME_WINDOW = "time_window"
    BLAST_RADIUS_MAX = "blast_radius_max"
    REQUIRES_APPROVAL = "requires_approval"
    REQUIRES_DLR = "requires_dlr"
    REQUIRES_REASONING = "requires_reasoning"
    SCOPE_LIMIT = "scope_limit"
    RATE_LIMIT = "rate_limit"


class ExpiryConditionType(str, Enum):
    """Types of expiry condition."""

    TIME_ABSOLUTE = "time_absolute"
    TIME_RELATIVE = "time_relative"
    CLAIM_HALF_LIFE = "claim_half_life"
    DELEGATION_EXPIRY = "delegation_expiry"
    EXTERNAL_EVENT = "external_event"


class AuthoritySourceType(str, Enum):
    """How authority was obtained."""

    POLICY = "policy"
    DELEGATION = "delegation"
    ROLE_BINDING = "role_binding"
    EMERGENCY = "emergency"


class StepResult(str, Enum):
    """Result of a single policy evaluation step."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class BlastRadiusTier(str, Enum):
    """Blast radius tiers for action scoping."""

    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


# ── Core dataclasses ─────────────────────────────────────────────


@dataclass
class Role:
    """A role binding scoped to a domain."""

    role_id: str
    role_name: str
    scope: str
    granted_at: str = ""
    expires_at: Optional[str] = None


@dataclass
class Actor:
    """An entity requesting authority to act."""

    actor_id: str
    actor_type: str  # ActorType value
    roles: List[Role] = field(default_factory=list)
    delegated_from: Optional[str] = None
    resolved_at: str = ""


@dataclass
class PolicyConstraint:
    """A single evaluable policy constraint."""

    constraint_id: str
    constraint_type: str  # ConstraintType value
    expression: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintResult:
    """Result of evaluating a single PolicyConstraint."""

    constraint_id: str
    constraint_type: str
    passed: bool
    detail: str = ""
    verdict: str = ""


@dataclass
class AuthorityGrant:
    """A resolved authority grant for a specific scope."""

    authority_id: str
    source_type: str  # AuthoritySourceType value
    scope: str
    effective_at: str
    expires_at: Optional[str] = None
    constraints: List[PolicyConstraint] = field(default_factory=list)


@dataclass
class Delegation:
    """A delegation of authority from one actor to another."""

    delegation_id: str
    from_actor_id: str
    to_actor_id: str
    scope: str
    max_depth: int = 3
    effective_at: str = ""
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None


@dataclass
class ActionRequest:
    """An action request submitted for authority evaluation."""

    action_id: str
    action_type: str
    resource_ref: str
    blast_radius_tier: str = "small"  # BlastRadiusTier value
    idempotency_key: str = ""
    episode_id: str = ""


@dataclass
class Resource:
    """A governed resource targeted by an action."""

    resource_id: str
    resource_type: str
    owner: str = ""
    classification: str = ""
    constraints: List[PolicyConstraint] = field(default_factory=list)


@dataclass
class ReasoningRequirement:
    """Requirements for reasoning sufficiency."""

    requirement_id: str
    requires_dlr: bool = True
    minimum_claims: int = 1
    required_truth_types: List[str] = field(default_factory=list)
    minimum_confidence: float = 0.7
    max_assumption_age: str = ""  # ISO 8601 duration, e.g. PT24H


@dataclass
class ExpiryCondition:
    """A condition that can expire an authority grant."""

    condition_id: str
    condition_type: str  # ExpiryConditionType value
    expires_at: Optional[str] = None
    half_life_ref: Optional[str] = None
    is_expired: bool = False


@dataclass
class ApprovalPath:
    """An escalation/approval path for gated decisions."""

    path_id: str
    required_approvers: List[str] = field(default_factory=list)
    current_approvals: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | approved | rejected | expired
    deadline: Optional[str] = None


@dataclass
class PolicyEvaluationStep:
    """Result of a single step in the policy evaluation pipeline."""

    step_name: str
    result: str  # StepResult value
    detail: str = ""
    elapsed_ms: float = 0.0


@dataclass
class PolicyEvaluation:
    """Complete policy evaluation record."""

    evaluation_id: str
    policy_id: str
    steps: List[PolicyEvaluationStep] = field(default_factory=list)
    verdict: str = ""  # AuthorityVerdict value
    evaluated_at: str = ""


@dataclass
class DecisionGateResult:
    """Terminal result of the authority decision gate."""

    gate_id: str
    verdict: str  # AuthorityVerdict value
    evaluated_at: str
    policy_ref: str = ""
    failed_checks: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    escalation_target: Optional[str] = None


@dataclass
class RevocationEvent:
    """An event that revokes authority, delegation, or policy."""

    revocation_id: str
    target_type: str  # authority | delegation | role | policy
    target_id: str
    revoked_at: str
    revoked_by: str = ""
    reason: str = ""


@dataclass
class GovernanceArtifact:
    """A sealed governance artifact produced by AuthorityOps."""

    artifact_id: str
    artifact_type: str  # policy_evaluation | delegation_proof | approval_record | audit_trail
    created_at: str
    episode_id: str = ""
    dlr_ref: str = ""
    seal_hash: str = ""
    seal_version: int = 1


@dataclass
class CompiledPolicy:
    """A compiled, sealed policy artifact produced by the OpenPQL pipeline."""

    artifact_id: str
    source_id: str  # back-reference to PolicySource
    dlr_ref: str
    episode_id: str
    policy_pack_id: str
    rules: List[PolicyConstraint] = field(default_factory=list)
    reasoning_requirements: Optional[ReasoningRequirement] = None
    created_at: str = ""
    policy_hash: str = ""  # deterministic hash over rules + requirements
    seal_hash: str = ""
    seal_version: int = 1
    expiry_conditions: List[ExpiryCondition] = field(default_factory=list)


@dataclass
class AuditRecord:
    """An immutable audit record for an authority evaluation."""

    audit_id: str
    action_id: str
    actor_id: str
    resource_id: str
    verdict: str  # AuthorityVerdict value
    evaluated_at: str
    policy_ref: str = ""
    dlr_ref: Optional[str] = None
    assumption_snapshot: Dict[str, Any] = field(default_factory=dict)
    expiry_state: Dict[str, Any] = field(default_factory=dict)
    failed_checks: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    escalation_path: Optional[str] = None
    chain_hash: str = ""
    prev_chain_hash: Optional[str] = None
    policy_hash: str = ""
