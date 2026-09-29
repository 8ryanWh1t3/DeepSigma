"""Deep Sigma ↔ NVIDIA OpenShell governed runtime bridge.

OpenShell contains the agent. Deep Sigma contains the consequences.
"""

from .audit import normalize_ocsf_event, normalize_ocsf_stream, to_cerpa_event, to_vinculum_event
from .authority import AllowAuthorityAdapter, DeepSigmaAuthorityAdapter
from .cerpa_bridge import contract_claim, policy_plan_event, run_plan_cycle, run_runtime_event_cycle
from .compiler import OpenShellPolicyCompiler, diff_policies
from .controller import GovernanceError, GovernedOpenShellController
from .loader import contract_from_dict, load_contract
from .models import (
    AccessMode,
    AgentMissionContract,
    AuthorityDecision,
    ContractValidationError,
    EndpointPermission,
    GovernedPlan,
    L7Rule,
    OpenShellAuditEvent,
    PlanStatus,
    PolicyDelta,
    PolicyProjection,
    SemanticAssessment,
    SemanticFinding,
)
from .runtime import OpenShellCliRuntime, OpenShellRuntimeError, OpenShellSdkProbe
from .semantic import OpenShellSemanticValidator

__version__ = "0.1.0"

__all__ = [
    "AccessMode",
    "AgentMissionContract",
    "AllowAuthorityAdapter",
    "AuthorityDecision",
    "ContractValidationError",
    "DeepSigmaAuthorityAdapter",
    "EndpointPermission",
    "GovernanceError",
    "GovernedOpenShellController",
    "GovernedPlan",
    "L7Rule",
    "OpenShellAuditEvent",
    "OpenShellCliRuntime",
    "OpenShellPolicyCompiler",
    "OpenShellRuntimeError",
    "OpenShellSdkProbe",
    "OpenShellSemanticValidator",
    "PlanStatus",
    "PolicyDelta",
    "PolicyProjection",
    "SemanticAssessment",
    "SemanticFinding",
    "contract_claim",
    "contract_from_dict",
    "diff_policies",
    "load_contract",
    "normalize_ocsf_event",
    "normalize_ocsf_stream",
    "policy_plan_event",
    "run_plan_cycle",
    "run_runtime_event_cycle",
    "to_cerpa_event",
    "to_vinculum_event",
]
