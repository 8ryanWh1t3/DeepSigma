"""Configuration and result types for the Golden Path pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GoldenPathConfig:
    """Configuration for a Golden Path run."""

    source: str  # "sharepoint" | "snowflake" | "dataverse" | "asksage"
    fixture_path: Optional[str] = None  # Path to fixture dir (None = live API)
    episode_id: str = "gp-demo"
    decision_type: str = "ingest"
    supervised: bool = False  # If True, pause before patch step
    output_dir: str = "./golden_path_output"
    # Source-specific (from env vars or CLI args):
    list_id: str = ""  # SharePoint
    site_id: str = ""  # SharePoint
    table_name: str = ""  # Dataverse
    sql: str = ""  # Snowflake
    prompt: str = ""  # AskSage


@dataclass
class GoldenPathResult:
    """Summary of a completed Golden Path run."""

    steps_completed: List[str]
    canonical_records: int
    claims_extracted: int
    episode_id: str
    baseline_score: float
    baseline_grade: str
    drift_events: int
    patch_applied: bool
    patched_score: float
    patched_grade: str
    iris_queries: Dict[str, str] = field(default_factory=dict)
    output_dir: str = ""
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps_completed": self.steps_completed,
            "canonical_records": self.canonical_records,
            "claims_extracted": self.claims_extracted,
            "episode_id": self.episode_id,
            "baseline_score": self.baseline_score,
            "baseline_grade": self.baseline_grade,
            "drift_events": self.drift_events,
            "patch_applied": self.patch_applied,
            "patched_score": self.patched_score,
            "patched_grade": self.patched_grade,
            "iris_queries": self.iris_queries,
            "output_dir": self.output_dir,
            "elapsed_ms": self.elapsed_ms,
        }
