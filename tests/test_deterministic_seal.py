"""Tests for deterministic sealing — proves same inputs → same outputs."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools" / "reconstruct"))

import seal_bundle  # noqa: E402
import replay_sealed_run as replay  # noqa: E402
from canonical_json import canonical_dumps, sha256_text  # noqa: E402

GOLDEN_DIR = REPO_ROOT / "tests" / "golden"
GOLDEN_INPUTS = GOLDEN_DIR / "inputs"
GOLDEN_EXPECTED = GOLDEN_DIR / "expected"

FIXED_CLOCK = "2026-01-01T00:00:00Z"


class DeterministicTestBase(unittest.TestCase):
    """Base class that sets up a temp workspace with golden inputs."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = Path(self.tmpdir) / "artifacts" / "sample_data" / "data"
        self.data_dir.mkdir(parents=True)
        self.prompts_dir = Path(self.tmpdir) / "prompts"
        self.prompts_dir.mkdir()
        self.schemas_dir = Path(self.tmpdir) / "schemas"
        self.schemas_dir.mkdir()
        self.policy_dir = Path(self.tmpdir) / "governance"
        self.policy_dir.mkdir()

        # Copy golden inputs
        shutil.copy(GOLDEN_INPUTS / "decision_log.csv", self.data_dir / "decision_log.csv")

        prompt_sub = self.prompts_dir / "golden"
        prompt_sub.mkdir()
        shutil.copy(GOLDEN_INPUTS / "test_prompt.md", prompt_sub / "test_prompt.md")

        self.policy_baseline = self.policy_dir / "POLICY_BASELINE.md"
        shutil.copy(GOLDEN_INPUTS / "POLICY_BASELINE.md", self.policy_baseline)
        self.policy_version = self.policy_dir / "POLICY_VERSION.txt"
        shutil.copy(GOLDEN_INPUTS / "POLICY_VERSION.txt", self.policy_version)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seal(self, out_dir: Path, clock: str = FIXED_CLOCK) -> Path:
        """Run seal_bundle and return path to sealed JSON."""
        sys.argv = [
            "seal_bundle.py",
            "--decision-id", "DEC-GOLD-001",
            "--user", "GoldenTester",
            "--data-dir", str(self.data_dir),
            "--out-dir", str(out_dir),
            "--prompts-dir", str(self.prompts_dir),
            "--schemas-dir", str(self.schemas_dir),
            "--policy-baseline", str(self.policy_baseline),
            "--policy-version", str(self.policy_version),
            "--clock", clock,
            "--deterministic", "true",
        ]
        rc = seal_bundle.main()
        self.assertEqual(rc, 0, "seal_bundle should succeed")
        json_files = [
            f for f in out_dir.glob("RUN-*.json")
            if ".manifest." not in f.name
        ]
        self.assertEqual(len(json_files), 1, "Expected one sealed JSON")
        return json_files[0]


class TestDeterministicIdempotency(DeterministicTestBase):
    """Seal twice with the same clock — commit_hash must be identical."""

    def test_commit_hash_identical(self) -> None:
        out1 = Path(self.tmpdir) / "sealed1"
        out1.mkdir()
        out2 = Path(self.tmpdir) / "sealed2"
        out2.mkdir()

        sealed1_path = self._seal(out1)
        sealed2_path = self._seal(out2)

        s1 = json.loads(sealed1_path.read_text())
        s2 = json.loads(sealed2_path.read_text())

        self.assertEqual(s1["commit_hash"], s2["commit_hash"],
                         "Commit hash must be identical across runs")

    def test_run_id_identical(self) -> None:
        out1 = Path(self.tmpdir) / "sealed1"
        out1.mkdir()
        out2 = Path(self.tmpdir) / "sealed2"
        out2.mkdir()

        sealed1_path = self._seal(out1)
        sealed2_path = self._seal(out2)

        s1 = json.loads(sealed1_path.read_text())
        s2 = json.loads(sealed2_path.read_text())

        rid1 = s1["authority_envelope"]["provenance"]["run_id"]
        rid2 = s2["authority_envelope"]["provenance"]["run_id"]
        self.assertEqual(rid1, rid2, "Run ID must be identical (derived from commit hash)")

    def test_hash_scope_canonical_identical(self) -> None:
        out1 = Path(self.tmpdir) / "sealed1"
        out1.mkdir()
        out2 = Path(self.tmpdir) / "sealed2"
        out2.mkdir()

        sealed1_path = self._seal(out1)
        sealed2_path = self._seal(out2)

        s1 = json.loads(sealed1_path.read_text())
        s2 = json.loads(sealed2_path.read_text())

        canonical1 = canonical_dumps(s1["hash_scope"])
        canonical2 = canonical_dumps(s2["hash_scope"])
        self.assertEqual(canonical1, canonical2,
                         "Canonical hash scope must be byte-for-byte identical")

    def test_different_clock_different_commit_hash(self) -> None:
        out1 = Path(self.tmpdir) / "sealed1"
        out1.mkdir()
        out2 = Path(self.tmpdir) / "sealed2"
        out2.mkdir()

        sealed1_path = self._seal(out1, clock="2026-01-01T00:00:00Z")
        sealed2_path = self._seal(out2, clock="2026-06-15T12:00:00Z")

        s1 = json.loads(sealed1_path.read_text())
        s2 = json.loads(sealed2_path.read_text())

        self.assertNotEqual(s1["commit_hash"], s2["commit_hash"],
                            "Different clock → different commit hash (clock is in hash scope)")


class TestDeterministicReplay(DeterministicTestBase):
    """Deterministic sealed runs must pass replay."""

    def test_replay_passes(self) -> None:
        out = Path(self.tmpdir) / "sealed"
        out.mkdir()
        sealed_path = self._seal(out)

        result = replay.replay(sealed_path)
        self.assertTrue(result.passed,
                        f"Replay should pass. Failed: {[n for n, ok, _ in result.checks if not ok]}")
        self.assertEqual(result.exit_code, 0)

    def test_replay_detects_commit_hash_tamper(self) -> None:
        out = Path(self.tmpdir) / "sealed"
        out.mkdir()
        sealed_path = self._seal(out)

        sealed = json.loads(sealed_path.read_text())
        sealed["commit_hash"] = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
        # Don't recompute content hash — let both checks fail
        sealed_path.write_text(json.dumps(sealed))

        result = replay.replay(sealed_path)
        self.assertFalse(result.passed)
        failed_names = [n for n, ok, _ in result.checks if not ok]
        self.assertTrue(
            any("commit_hash" in n for n in failed_names),
            f"Should detect commit hash tamper. Failures: {failed_names}",
        )

    def test_replay_exit_code_3_on_hash_mismatch(self) -> None:
        out = Path(self.tmpdir) / "sealed"
        out.mkdir()
        sealed_path = self._seal(out)

        sealed = json.loads(sealed_path.read_text())
        sealed["commit_hash"] = "sha256:dead"
        sealed_path.write_text(json.dumps(sealed))

        result = replay.replay(sealed_path)
        self.assertEqual(result.exit_code, 3, "Hash mismatch should exit 3")


class TestCanonicalJson(unittest.TestCase):
    """Test the canonical serialization module."""

    def test_sorted_keys(self) -> None:
        obj = {"z": 1, "a": 2, "m": 3}
        result = canonical_dumps(obj)
        self.assertEqual(result, '{"a":2,"m":3,"z":1}')

    def test_nested_sorted_keys(self) -> None:
        obj = {"b": {"z": 1, "a": 2}, "a": 1}
        result = canonical_dumps(obj)
        self.assertEqual(result, '{"a":1,"b":{"a":2,"z":1}}')

    def test_compact_separators(self) -> None:
        obj = {"key": [1, 2, 3]}
        result = canonical_dumps(obj)
        self.assertNotIn(" ", result)

    def test_float_normalization(self) -> None:
        # 3.0 should become 3
        obj = {"val": 3.0}
        result = canonical_dumps(obj)
        self.assertEqual(result, '{"val":3}')

    def test_set_to_sorted_list(self) -> None:
        obj = {"items": {3, 1, 2}}
        result = canonical_dumps(obj)
        self.assertEqual(result, '{"items":[1,2,3]}')

    def test_datetime_normalization(self) -> None:
        obj = {"ts": "2026-02-21T00:00:00+00:00"}
        result = canonical_dumps(obj)
        self.assertIn("2026-02-21T00:00:00Z", result)

    def test_sha256_deterministic(self) -> None:
        h1 = sha256_text("hello")
        h2 = sha256_text("hello")
        self.assertEqual(h1, h2)
        self.assertTrue(h1.startswith("sha256:"))


class TestDeterministicIds(unittest.TestCase):
    """Test deterministic ID generation."""

    def test_det_id_from_hash(self) -> None:
        from deterministic_ids import det_id

        h = "sha256:abcdef0123456789"
        result = det_id("RUN", h, length=8)
        self.assertEqual(result, "RUN-abcdef01")

    def test_det_id_stable(self) -> None:
        from deterministic_ids import det_id_from_payload

        r1 = det_id_from_payload("EVT", "same input")
        r2 = det_id_from_payload("EVT", "same input")
        self.assertEqual(r1, r2)

    def test_det_id_different_inputs(self) -> None:
        from deterministic_ids import det_id_from_payload

        r1 = det_id_from_payload("EVT", "input A")
        r2 = det_id_from_payload("EVT", "input B")
        self.assertNotEqual(r1, r2)


if __name__ == "__main__":
    unittest.main()
