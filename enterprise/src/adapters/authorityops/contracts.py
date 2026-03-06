"""AuthorityOps enterprise contracts — Protocol interfaces for external systems.

These interfaces define stable extension points for integrating enterprise
identity providers, policy stores, approval systems, audit sinks, and
kill-switch providers into the AuthorityOps evaluation pipeline.

No full implementations here — only contracts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class IdentityProviderV1(Protocol):
    """Interface for enterprise identity providers (Entra ID, Okta, etc.).

    Resolves actor identity, roles, and group membership for use in
    AuthorityOps actor resolution (AUTH-F02).
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...

    def resolve_actor(self, actor_id: str) -> Dict[str, Any]:
        """Resolve an actor's identity and attributes.

        Returns dict with: actorId, actorType, displayName, email, etc.
        """
        ...

    def resolve_roles(self, actor_id: str) -> List[Dict[str, Any]]:
        """Resolve roles assigned to an actor.

        Returns list of role dicts with: roleId, roleName, scope, grantedAt, expiresAt.
        """
        ...

    def check_group_membership(self, actor_id: str, group: str) -> bool:
        """Check if an actor belongs to a specific group."""
        ...


@runtime_checkable
class PolicyStoreV1(Protocol):
    """Interface for external policy storage backends.

    Manages policy packs that define constraints, reasoning requirements,
    and blast radius thresholds for AuthorityOps evaluation (AUTH-F04).
    """

    @property
    def store_name(self) -> str:
        """Human-readable store name."""
        ...

    def load_policy(self, policy_id: str) -> Dict[str, Any]:
        """Load a policy pack by ID.

        Returns policy dict with: policyPackId, version, constraints,
        requiresDlr, maxBlastRadius, minimumConfidence.
        """
        ...

    def list_policies(self, scope: str) -> List[Dict[str, Any]]:
        """List all policies applicable to a given scope."""
        ...


@runtime_checkable
class ApprovalSystemV1(Protocol):
    """Interface for approval workflow systems (Jira, ServiceNow, etc.).

    Handles escalation paths when AuthorityOps verdict is ESCALATE (AUTH-F10).
    """

    @property
    def system_name(self) -> str:
        """Human-readable system name."""
        ...

    def create_approval(self, request: Dict[str, Any]) -> str:
        """Create an approval request.

        Args:
            request: Dict with actionId, actorId, resourceId, reason, etc.

        Returns:
            Approval ID for tracking.
        """
        ...

    def check_approval_status(self, approval_id: str) -> str:
        """Check approval status.

        Returns: "pending", "approved", "rejected", or "expired".
        """
        ...


@runtime_checkable
class AuditSinkV1(Protocol):
    """Interface for audit event sinks (SIEM, log aggregators, etc.).

    Receives audit records from AuthorityOps (AUTH-F11) for external
    storage and compliance.
    """

    @property
    def sink_name(self) -> str:
        """Human-readable sink name."""
        ...

    def emit_audit_record(self, record: Dict[str, Any]) -> bool:
        """Emit an audit record to the external sink.

        Returns True if accepted, False if rejected.
        """
        ...


@runtime_checkable
class KillSwitchProviderV1(Protocol):
    """Interface for external kill-switch state providers.

    Provides kill-switch state for AuthorityOps evaluation (AUTH-F09).
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...

    def is_active(self) -> bool:
        """Check if the kill-switch is currently active."""
        ...

    def activate(self, reason: str, authorized_by: str) -> Dict[str, Any]:
        """Activate the kill-switch.

        Returns dict with: activated_at, reason, authorized_by, confirmation_id.
        """
        ...

    def deactivate(self, authorized_by: str) -> Dict[str, Any]:
        """Deactivate the kill-switch.

        Returns dict with: deactivated_at, authorized_by, confirmation_id.
        """
        ...
