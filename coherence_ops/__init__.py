"""Coherence Ops — governance framework for agentic AI.

Implements the four canonical artifacts (DLR / RS / DS / MG),
the coherence audit loop that connects RAL / Sigma OVERWATCH
runtime exhaust to structured governance, learning, and memory,
and the Unified Atomic Claims layer, and the Money Demo (v0.3.0).

Public API
----------
CoherenceManifest  — system-level declaration of artifact coverage
DLRBuilder         — build Decision Log Records from sealed episodes
ClaimNativeDLRBuilder — claim-native DLR builder (atomic claims as first-class)
ReflectionSession  — aggregate episodes into learning summaries
DriftSignalCollector — collect and structure runtime drift signals
MemoryGraph        — build provenance / recall graph (claim-aware)
NodeKind / EdgeKind — typed graph vocabulary enums
CoherenceAuditor   — periodic cross-artifact consistency checks
CoherenceScorer    — compute unified coherence score
Reconciler         — detect and resolve cross-artifact inconsistencies
IRISEngine         — operator query resolution engine
IRISQuery          — structured query input for IRIS
IRISResponse       — structured response with provenance chain
QueryType          — WHY | WHAT_CHANGED | WHAT_DRIFTED | RECALL | STATUS
IRISConfig         — configuration for the IRIS engine
ResolutionStatus   — OK | PARTIAL | NOT_FOUND | ERROR
"""
from __future__ import annotations

__version__ = "0.6.2"

from coherence_ops.manifest import CoherenceManifest
from coherence_ops.dlr import (
    DLRBuilder,
    ClaimNativeDLRBuilder,
    ClaimNativeDLREntry,
    ClaimRef,
    RationaleEdge,
)
from coherence_ops.rs import ReflectionSession
from coherence_ops.ds import DriftSignalCollector
from coherence_ops.mg import MemoryGraph, NodeKind, EdgeKind
from coherence_ops.audit import CoherenceAuditor
from coherence_ops.scoring import CoherenceScorer
from coherence_ops.reconciler import Reconciler
from coherence_ops.iris import (
    IRISEngine,
    IRISQuery,
    IRISResponse,
    QueryType,
    IRISConfig,
    ResolutionStatus,
)
from coherence_ops.prime import (
    PRIMEGate,
    PRIMEConfig,
    PRIMEContext,
    PRIMEVerdict,
    TruthInvariant,
    ReasoningInvariant,
    MemoryInvariant,
    Verdict,
    ConfidenceBand,
)
__all__ = [
    "CoherenceManifest",
    "DLRBuilder",
    "ClaimNativeDLRBuilder",
    "ClaimNativeDLREntry",
    "ClaimRef",
    "RationaleEdge",
    "ReflectionSession",
    "DriftSignalCollector",
    "MemoryGraph",
    "NodeKind",
    "EdgeKind",
    "CoherenceAuditor",
    "CoherenceScorer",
    "Reconciler",
    "IRISEngine",
    "IRISQuery",
    "IRISResponse",
    "QueryType",
    "PRIMEGate",
    "PRIMEConfig",
    "PRIMEContext",
    "PRIMEVerdict",
    "TruthInvariant",
    "ReasoningInvariant",
    "MemoryInvariant",
    "Verdict",
    "ConfidenceBand",
    "IRISConfig",
    "ResolutionStatus",
]
