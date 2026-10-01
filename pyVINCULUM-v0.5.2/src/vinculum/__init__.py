from .config import ScoringConfig, SignalRule
from .engine import VinculumEngine
from .formulas import DerivedVector, derive_vector
from .ingest import ingest_file, ingest_mapping, ingest_text, ingest_ttl, stable_id
from .models import DominantState, ObjectType, ScoreMode, Signal, VinculumObject, VinculumResult
from .semantics import (ComparisonResult, MeaningRegistry, MeaningRule, ReconciliationStatus, ReconciliationSummary, SemanticFact, reconcile_object)

__all__ = [
    "DerivedVector",
    "DominantState",
    "ObjectType",
    "ScoreMode",
    "ScoringConfig",
    "Signal",
    "SignalRule",
    "VinculumEngine",
    "VinculumObject",
    "VinculumResult",
    "derive_vector",
    "ingest_file",
    "ingest_mapping",
    "ingest_text",
    "ingest_ttl",
    "stable_id",
    "ComparisonResult",
    "MeaningRegistry",
    "MeaningRule",
    "ReconciliationStatus",
    "ReconciliationSummary",
    "SemanticFact",
    "reconcile_object",
]

__version__ = "0.5.2"
