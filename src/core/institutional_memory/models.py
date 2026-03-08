"""Institutional Memory models -- dataclasses and enums for precedent tracking.

Defines the object model for precedents, pattern fingerprints,
knowledge entries, consolidation reports, and temporal recall results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Precedent:
    """A reusable learning artifact extracted from a reflection session."""

    precedent_id: str
    source_session_id: str
    source_episode_ids: List[str]
    takeaway: str
    category: str  # degrade_pattern, drift_recurrence, outcome_anomaly
    confidence: float = 0.0
    relevance_score: float = 1.0  # Decays via knowledge_decay
    decay_half_life_days: int = 90
    created_at: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternFingerprint:
    """Structural signature of an episode or precedent pattern."""

    fingerprint_id: str
    precedent_id: str
    outcome_vector: Dict[str, float] = field(default_factory=dict)
    drift_signature: Dict[str, int] = field(default_factory=dict)
    degrade_frequency: float = 0.0
    episode_count: int = 0
    computed_at: str = ""


@dataclass
class KnowledgeEntry:
    """Consolidated knowledge from multiple related precedents."""

    entry_id: str
    title: str
    summary: str
    source_precedent_ids: List[str] = field(default_factory=list)
    relevance_score: float = 1.0
    access_count: int = 0
    created_at: str = ""
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsolidationReport:
    """Output of a precedent consolidation pass."""

    report_id: str
    entries_created: int = 0
    precedents_merged: int = 0
    total_precedents: int = 0
    created_at: str = ""


@dataclass
class TemporalRecallResult:
    """Result of a time-windowed recall query."""

    query_window_hours: int = 0
    precedents: List[Precedent] = field(default_factory=list)
    knowledge_entries: List[KnowledgeEntry] = field(default_factory=list)
    total_matches: int = 0
