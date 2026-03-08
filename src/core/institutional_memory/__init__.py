"""Institutional Memory -- precedent tracking and knowledge consolidation.

Persists learning from ReflectionOps sessions as searchable precedents,
computes pattern fingerprints, and consolidates knowledge over time.
"""

from __future__ import annotations

from .consolidation import merge_precedents
from .fingerprinting import compute_fingerprint, similarity_score
from .models import (
    ConsolidationReport,
    KnowledgeEntry,
    PatternFingerprint,
    Precedent,
    TemporalRecallResult,
)
from .registry import PrecedentRegistry
from .temporal import apply_decay, filter_by_window
from .validators import validate_knowledge_entry, validate_precedent

__all__ = [
    "ConsolidationReport",
    "KnowledgeEntry",
    "PatternFingerprint",
    "Precedent",
    "PrecedentRegistry",
    "TemporalRecallResult",
    "apply_decay",
    "compute_fingerprint",
    "filter_by_window",
    "merge_precedents",
    "similarity_score",
    "validate_knowledge_entry",
    "validate_precedent",
]
