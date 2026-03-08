"""Context Envelope — the ambient field surrounding CERPA.

Context is NOT a sixth primitive. It is the envelope that carries
identity, timing, constraints, scope, and rationale through every
operation in the system.
"""

from .models import ContextDiff, ContextEnvelope, ContextSnapshot
from .builder import ContextEnvelopeBuilder
from .propagation import (
    compute_context_diff,
    fork_context,
    inherit_context,
    merge_context,
    snapshot_context,
)
from .validators import validate_context_envelope

__all__ = [
    "ContextDiff",
    "ContextEnvelope",
    "ContextEnvelopeBuilder",
    "ContextSnapshot",
    "compute_context_diff",
    "fork_context",
    "inherit_context",
    "merge_context",
    "snapshot_context",
    "validate_context_envelope",
]
