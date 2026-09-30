"""pyDOGE — work-system diagnostics before workforce optimization."""

from .core import WorkSystem
from .cerpa import CERPALedger
from .models import Mission, Authority, Policy, WorkItem, SystemAsset, RoleCapacity, OutcomeObservation

__all__ = [
    "WorkSystem",
    "CERPALedger",
    "Mission",
    "Authority",
    "Policy",
    "WorkItem",
    "SystemAsset",
    "RoleCapacity",
    "OutcomeObservation",
]

__version__ = "0.1.0"
