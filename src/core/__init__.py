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

from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("deepsigma")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

from core.manifest import CoherenceManifest
from core.dlr import (
    DLRBuilder,
    ClaimNativeDLRBuilder,
    ClaimNativeDLREntry,
    ClaimRef,
    RationaleEdge,
)
from core.rs import ReflectionSession
from core.ds import DriftSignalCollector
from core.mg import MemoryGraph, NodeKind, EdgeKind
from core.audit import CoherenceAuditor
from core.scoring import CoherenceScorer
from core.reconciler import Reconciler
from core.iris import (
    IRISEngine,
    IRISQuery,
    IRISResponse,
    QueryType,
    IRISConfig,
    ResolutionStatus,
)
from core.normalize import normalize_keys
from core.coherence_gate import CoherenceGate, GateConfig, GateResult, Signal
from core.prime import (
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
    "normalize_keys",
    "CoherenceGate",
    "GateConfig",
    "GateResult",
    "Signal",
]
