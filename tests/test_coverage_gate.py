"""CI gate: verify every function ID has a test and every handler exists."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


def _load_matrix() -> dict:
    p = _REPO_ROOT / "tests" / "coverage_matrix.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _load_routing_table() -> dict:
    p = _REPO_ROOT / "src" / "core" / "feeds" / "contracts" / "routing_table.json"
    return json.loads(p.read_text(encoding="utf-8"))


class TestCoverageGate:
    """Fail CI if any function lacks handler or test coverage."""

    def test_all_routing_functions_in_matrix(self):
        """Every function in routing_table.json must appear in coverage_matrix.json."""
        rt = _load_routing_table()
        matrix = _load_matrix()
        rt_functions = set(rt["functions"].keys())
        matrix_functions = set(matrix["functions"].keys())
        missing = rt_functions - matrix_functions
        assert not missing, f"Functions in routing table but not in coverage matrix: {missing}"

    def test_all_matrix_functions_in_routing(self):
        """Every function in coverage_matrix.json must appear in routing_table.json."""
        rt = _load_routing_table()
        matrix = _load_matrix()
        rt_functions = set(rt["functions"].keys())
        matrix_functions = set(matrix["functions"].keys())
        extra = matrix_functions - rt_functions
        assert not extra, f"Functions in coverage matrix but not in routing table: {extra}"

    def test_all_test_files_exist(self):
        """Every test file referenced in the matrix must exist."""
        matrix = _load_matrix()
        for fid, entry in matrix["functions"].items():
            tf = _REPO_ROOT / entry["testFile"]
            assert tf.exists(), f"Test file for {fid} missing: {entry['testFile']}"

    def test_all_handlers_registered(self):
        """Every function ID must be handled by its domain mode."""
        from core.modes.intelops import IntelOps
        from core.modes.franops import FranOps
        from core.modes.reflectionops import ReflectionOps

        modes = {
            "intelops": IntelOps(),
            "franops": FranOps(),
            "reflectionops": ReflectionOps(),
        }

        rt = _load_routing_table()
        for fid, contract in rt["functions"].items():
            domain = contract["domain"]
            mode = modes.get(domain)
            assert mode is not None, f"No mode for domain '{domain}' (function {fid})"
            assert mode.has_handler(fid), f"Handler missing for {fid} in {domain}"

    def test_36_functions_covered(self):
        """Exactly 36 functions must be covered."""
        matrix = _load_matrix()
        assert len(matrix["functions"]) == 36

    def test_4_integration_suites(self):
        """Must have integration suites for all 3 domains + cascade."""
        matrix = _load_matrix()
        assert len(matrix["integration"]) == 4
        for key in ("intelops", "franops", "reflectionops", "cascade"):
            assert key in matrix["integration"]


class TestDeterminism:
    """Per-function replay determinism: same input -> same hash."""

    def _make_context(self) -> dict:
        from core.memory_graph import MemoryGraph
        from core.drift_signal import DriftSignalCollector
        from core.episode_state import EpisodeTracker
        from core.feeds.canon.workflow import CanonWorkflow
        from core.audit_log import AuditLog
        from datetime import datetime, timezone

        return {
            "memory_graph": None,
            "drift_collector": None,
            "canon_store": None,
            "canon_claims": [],
            "claims": {},
            "all_claims": [],
            "all_canon_entries": [],
            "workflow": None,
            "episode_tracker": None,
            "audit_log": None,
            "gates": [],
            "blessed_claims": set(),
            "now": datetime(2026, 2, 28, tzinfo=timezone.utc),
        }

    @pytest.mark.parametrize("function_id,domain", [
        ("INTEL-F01", "intelops"),
        ("INTEL-F04", "intelops"),
        ("INTEL-F09", "intelops"),
        ("FRAN-F01", "franops"),
        ("FRAN-F07", "franops"),
        ("FRAN-F10", "franops"),
        ("RE-F01", "reflectionops"),
        ("RE-F05", "reflectionops"),
        ("RE-F08", "reflectionops"),
        ("RE-F10", "reflectionops"),
    ])
    def test_replay_deterministic(self, function_id, domain):
        """Same inputs produce same replay hash."""
        from core.modes.intelops import IntelOps
        from core.modes.franops import FranOps
        from core.modes.reflectionops import ReflectionOps

        modes = {
            "intelops": IntelOps(),
            "franops": FranOps(),
            "reflectionops": ReflectionOps(),
        }
        mode = modes[domain]

        # Build minimal event based on domain
        events = {
            "INTEL-F01": {"payload": {"claimId": "C-DET", "statement": "test", "confidence": {"score": 0.5}}},
            "INTEL-F04": {"payload": {"driftType": "freshness", "fingerprint": {"key": "det", "version": "1"}}},
            "INTEL-F09": {"payload": {"severity": "yellow", "driftType": "process_gap"}},
            "FRAN-F01": {"payload": {"canonId": "CANON-DET", "title": "det", "claimIds": []}},
            "FRAN-F07": {"payload": {"domain": "det", "claimCount": 5}},
            "FRAN-F10": {"payload": {"canonId": "C-DET", "scope": {"domain": "intelops"}}},
            "RE-F01": {"payload": {"episodeId": "EP-DET", "decisionType": "test"}},
            "RE-F05": {"payload": {"episodeId": "EP-DET", "degradeStep": "none"}},
            "RE-F08": {"payload": {"driftType": "process_gap", "severity": "yellow"}},
            "RE-F10": {"payload": {"episodeId": "EP-DET"}},
        }

        event = events[function_id]
        ctx = self._make_context()

        r1 = mode.handle(function_id, event, ctx)
        r2 = mode.handle(function_id, event, ctx)

        assert r1.replay_hash == r2.replay_hash
        assert r1.replay_hash.startswith("sha256:")
