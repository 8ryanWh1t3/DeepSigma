"""CERPA — Claim -> Event -> Review -> Patch -> Apply.

The foundational adaptation loop for DeepSigma.  Every governance flow
across IntelOps, ReOps, FranOps, AuthorityOps, and ActionOps follows
the CERPA cycle.

Usage:
    from core.cerpa import Claim, Event, run_cerpa_cycle, cycle_to_dict
"""

from .engine import (
    apply_patch,
    cycle_to_dict,
    generate_patch_from_review,
    review_claim_against_event,
    run_cerpa_cycle,
)
from .models import ApplyResult, CerpaCycle, Claim, Event, Patch, Review
from .types import CerpaDomain, CerpaStatus, PatchAction, ReviewVerdict

__all__ = [
    # Models
    "Claim",
    "Event",
    "Review",
    "Patch",
    "ApplyResult",
    "CerpaCycle",
    # Enums
    "CerpaDomain",
    "CerpaStatus",
    "ReviewVerdict",
    "PatchAction",
    # Engine
    "run_cerpa_cycle",
    "review_claim_against_event",
    "generate_patch_from_review",
    "apply_patch",
    "cycle_to_dict",
]
