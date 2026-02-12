"""Coherence Ops — governance framework for agentic AI.

Implements the four canonical artifacts (DLR / RS / DS / MG) and the
coherence audit loop that connects RAL / Sigma OVERWATCH runtime exhaust
to structured governance, learning, and memory.

Public API:
    CoherenceManifest   — system-level declaration of artifact coverage
    DLRBuilder          — build Decision Log Records from sealed episodes
    ReflectionSession   — aggregate episodes into learning summaries
    DriftSignalCollector — collect and structure runtime drift signals
    MemoryGraph          — build provenance / recall graph
    CoherenceAuditor    — periodic cross-artifact consistency checks
    CoherenceScorer     — compute unified coherence score
    Reconciler          — detect and resolve cross-artifact inconsistencies
"""

from __future__ import annotations

__version__ = "0.1.0"

from coherence_ops.manifest import CoherenceManifest
from coherence_ops.dlr import DLRBuilder
from coherence_ops.rs import ReflectionSession
from coherence_ops.ds import DriftSignalCollector
from coherence_ops.mg import MemoryGraph
from coherence_ops.audit import CoherenceAuditor
from coherence_ops.scoring import CoherenceScorer
from coherence_ops.reconciler import Reconciler

__all__ = [
    "CoherenceManifest",
    "DLRBuilder",
    "ReflectionSession",
    "DriftSignalCollector",
    "MemoryGraph",
    "CoherenceAuditor",
    "CoherenceScorer",
    "Reconciler",
]
