"""Deep Sigma gray-zone pattern assessment. Public v0.1 API."""

from .blast_radius import exposed_dependencies
from .cerpa import approve_patch, cerpa_packet, propose_patch, record_apply, review_hypothesis
from .drift import compare
from .engine import GrayZoneEpisode, assess
from .graph import graph_json, ntriples
from .ingest import load_events, normalize
from .lattice import LATTICE_EXAMPLE_MAP, load_lattice_jsonl
from .report import markdown, to_dict, write_excel, write_json
from .schema import (Alternative, Assessment, AssessmentConfig, Event, EventLink,
                     FieldMap, Hypothesis, SourceRef, WeakSignal)

__all__ = [
    "Alternative", "Assessment", "AssessmentConfig", "Event", "EventLink",
    "FieldMap", "GrayZoneEpisode", "Hypothesis", "SourceRef", "WeakSignal",
    "LATTICE_EXAMPLE_MAP", "approve_patch", "assess", "cerpa_packet", "compare", "exposed_dependencies",
    "graph_json", "load_events", "load_lattice_jsonl", "markdown", "normalize", "ntriples",
    "propose_patch", "record_apply", "review_hypothesis", "to_dict", "write_excel", "write_json",
]
