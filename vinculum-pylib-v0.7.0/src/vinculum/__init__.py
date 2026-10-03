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

from .version import __version__

# Canonical v0.6 cross-order API; the original v0.5.2 API above is retained.
from .core import (Side, PairStatus, CheckState, PDProfile, SupportFactor, SupportProfile,
                   NumericRange, TimeWindow, Scope, Representation, PairSpec, HingeCheck, PairResult, HingeOrderState)
from .hinge import HingeEvaluator, HingePolicy
from .matrix import PairGraph, ObjectGroup, EvaluationReport, CrossOrderEngine
from .lang import SemanticRegistry, NumericMeaningRule, Resolution, measurement
from .math import UnitRegistry, UnitDefinition, beta_calibration
from .codec import CodecEvaluator, CodecReport, Transformation
from .context import NarrativeContext
from .monitor import PairingMonitor, PairProposal
from .serialization import Scenario, load_scenario, save_scenario, scenario_from_dict

__all__ += [
    'Side', 'PairStatus', 'CheckState', 'PDProfile', 'SupportFactor', 'SupportProfile',
    'NumericRange', 'TimeWindow', 'Scope', 'Representation', 'PairSpec', 'HingeCheck', 'PairResult', 'HingeOrderState',
    'HingeEvaluator', 'HingePolicy', 'PairGraph', 'ObjectGroup', 'EvaluationReport', 'CrossOrderEngine',
    'SemanticRegistry', 'NumericMeaningRule', 'Resolution', 'measurement', 'UnitRegistry',
    'UnitDefinition', 'beta_calibration', 'CodecEvaluator', 'CodecReport', 'Transformation',
    'NarrativeContext', 'PairingMonitor', 'PairProposal', 'Scenario', 'load_scenario',
    'save_scenario', 'scenario_from_dict',
]

# v0.7 orchestration; optional file/API/report runtimes remain lazy imports.
from .pipeline import VinculumPipeline, PipelineResult
from .pairing import PairPlanner, PairingPlan, PairCandidate, PairingAudit
from .ontology import OntologyRegistry, TermResolution
from .evidence import EvidenceRegistry, EvidenceSource
from .higher_order import HigherOrderPolicy, assess_factors, pair_order_diagnostics, freshness_index
from .represent import FieldMapping, ExtractionTrace
from .io import LoadLimits, SourceBatch, load_source
__all__ += ['VinculumPipeline','PipelineResult','PairPlanner','PairingPlan','PairCandidate','PairingAudit',
            'OntologyRegistry','TermResolution','EvidenceRegistry','EvidenceSource','HigherOrderPolicy',
            'assess_factors','pair_order_diagnostics','freshness_index','FieldMapping','ExtractionTrace',
            'LoadLimits','SourceBatch','load_source']

from .symbolic import interval_calculate
__all__ += ["interval_calculate"]
