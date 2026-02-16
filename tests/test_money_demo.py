"""Smoke test for the v0.3 Money Demo (drift_patch_cycle).

Runs the demo end-to-end and verifies:
  - All required artifacts are written
  - Score monotonicity: baseline >= after > drift
  - memory_graph_diff.json contains patch node + resolved_by edge
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure repo root is importable
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from coherence_ops.examples.drift_patch_cycle import (  # noqa: E402
    OUTPUT_DIR,
    REQUIRED_ARTIFACTS,
    DRIFT_ID,
    PATCH_ID,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def run_demo():
    """Execute the Money Demo once for all tests in this module."""
    # Clean output dir to ensure a fresh run
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    main()  # run the cycle

    yield

    # Teardown: leave artifacts in place for manual inspection


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestArtifactsExist:
    """Verify every required artifact is written and non-empty."""

    @pytest.mark.parametrize("filename", REQUIRED_ARTIFACTS)
    def test_artifact_exists(self, filename: str):
        path = OUTPUT_DIR / filename
        assert path.exists(), f"Missing artifact: {filename}"
        assert path.stat().st_size > 0, f"Empty artifact: {filename}"


class TestScoreMonotonicity:
    """Verify the drift drops the score and the patch recovers it."""

    def _load_diff(self) -> dict:
        return json.loads((OUTPUT_DIR / "memory_graph_diff.json").read_text())

    def test_drift_below_baseline(self):
        diff = self._load_diff()
        baseline = diff["notes"]["baseline_score"]
        drift = diff["notes"]["drift_score"]
        assert drift < baseline, (
            f"drift ({drift}) must be < baseline ({baseline})"
        )

    def test_after_above_drift(self):
        diff = self._load_diff()
        drift = diff["notes"]["drift_score"]
        after = diff["notes"]["after_score"]
        assert after > drift, (
            f"after ({after}) must be > drift ({drift})"
        )


class TestMemoryGraphDiff:
    """Verify the diff contains the expected patch node and resolved_by edge."""

    def _load_diff(self) -> dict:
        return json.loads((OUTPUT_DIR / "memory_graph_diff.json").read_text())

    def test_patch_node_added(self):
        diff = self._load_diff()
        assert PATCH_ID in diff["added_nodes"], (
            f"Patch node '{PATCH_ID}' not in added_nodes: {diff['added_nodes']}"
        )

    def test_drift_node_added(self):
        diff = self._load_diff()
        assert DRIFT_ID in diff["added_nodes"], (
            f"Drift node '{DRIFT_ID}' not in added_nodes: {diff['added_nodes']}"
        )

    def test_resolved_by_edge(self):
        diff = self._load_diff()
        edges = diff["added_edges"]
        expected = [DRIFT_ID, "resolved_by", PATCH_ID]
        assert expected in edges, (
            f"Expected resolved_by edge {expected} not found in: {edges}"
        )


class TestMermaidOutput:
    """Verify the Mermaid diagram is well-formed."""

    def test_mermaid_contains_flowchart(self):
        mmd = (OUTPUT_DIR / "loop.mmd").read_text()
        assert "flowchart" in mmd, "Mermaid file missing flowchart directive"

    def test_mermaid_contains_ids(self):
        mmd = (OUTPUT_DIR / "loop.mmd").read_text()
        assert DRIFT_ID in mmd, f"Mermaid file missing {DRIFT_ID}"
        assert PATCH_ID in mmd, f"Mermaid file missing {PATCH_ID}"

    def test_mermaid_contains_resolved_by(self):
        mmd = (OUTPUT_DIR / "loop.mmd").read_text()
        assert "resolved_by" in mmd, "Mermaid file missing resolved_by label"
