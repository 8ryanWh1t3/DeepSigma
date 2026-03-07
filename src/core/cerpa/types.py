"""CERPA type definitions — enums for the adaptation loop.

Claim -> Event -> Review -> Patch -> Apply
"""

from __future__ import annotations

from enum import Enum


class CerpaDomain(str, Enum):
    """Operational domains that run CERPA cycles."""

    INTELOPS = "intelops"
    REOPS = "reops"
    FRANOPS = "franops"
    AUTHORITYOPS = "authorityops"
    ACTIONOPS = "actionops"


class CerpaStatus(str, Enum):
    """Overall status of a CERPA cycle."""

    ALIGNED = "aligned"
    MISMATCHED = "mismatched"
    PATCHED = "patched"
    APPLIED = "applied"
    ESCALATED = "escalated"


class ReviewVerdict(str, Enum):
    """Outcome of comparing a Claim against an Event."""

    ALIGNED = "aligned"
    MISMATCH = "mismatch"
    VIOLATION = "violation"
    EXPIRED = "expired"


class PatchAction(str, Enum):
    """Corrective action type for a Patch."""

    ADJUST = "adjust"
    ESCALATE = "escalate"
    REDEFINE = "redefine"
    STRENGTHEN = "strengthen"
    EXPIRE = "expire"
