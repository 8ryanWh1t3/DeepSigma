"""Tests: validate JSON examples against their JSON Schema specs.

Requires: pip install jsonschema
"""

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_json(rel_path: str) -> dict:
      """Load a JSON file relative to repo root."""
      return json.loads((ROOT / rel_path).read_text(encoding="utf-8"))


# ── Claim Primitive ──────────────────────────────────────────────

class TestClaimSchema:
      """Validate claim_primitive_example.json against claim.schema.json."""

    @pytest.fixture(autouse=True)
    def _load(self):
              jsonschema = pytest.importorskip("jsonschema")
              self.schema = _load_json("specs/claim.schema.json")
              self.example = _load_json(
                  "llm_data_model/03_examples/claim_primitive_example.json"
              )
              self.validate = jsonschema.validate

    def test_example_validates(self):
              """The shipped example must conform to the schema."""
              self.validate(instance=self.example, schema=self.schema)

    def test_claim_id_pattern(self):
              """claimId must match CLAIM-YYYY-NNNN."""
              assert self.example["claimId"].startswith("CLAIM-")

    def test_confidence_range(self):
              """confidence.score must be 0.00–1.00."""
              score = self.example["confidence"]["score"]
              assert 0.0 <= score <= 1.0

    def test_status_light_enum(self):
              """statusLight must be green, yellow, or red."""
              assert self.example["statusLight"] in ("green", "yellow", "red")

    def test_truth_type_enum(self):
              """truthType must be one of the 6 allowed values."""
              allowed = {"observation", "inference", "assumption", "forecast", "norm", "constraint"}
              assert self.example["truthType"] in allowed

    def test_sources_min_one(self):
              """At least one source is required."""
              assert len(self.example["sources"]) >= 1

    def test_seal_present(self):
              """Seal must have hash, sealedAt, version."""
              seal = self.example["seal"]
              assert "hash" in seal
              assert "sealedAt" in seal
              assert "version" in seal

    def test_half_life_present(self):
              """halfLife must have value and unit."""
              hl = self.example["halfLife"]
              assert "value" in hl
              assert "unit" in hl

    def test_missing_claim_id_fails(self):
              """Removing claimId should cause validation failure."""
              jsonschema = pytest.importorskip("jsonschema")
              bad = {k: v for k, v in self.example.items() if k != "claimId"}
              with pytest.raises(jsonschema.ValidationError):
                            self.validate(instance=bad, schema=self.schema)


# ── DLR Claim-Native ─────────────────────────────────────────────

class TestDLRSchema:
      """Validate dlr_claim_native_example.json against dlr.schema.json."""

    @pytest.fixture(autouse=True)
    def _load(self):
              jsonschema = pytest.importorskip("jsonschema")
              self.schema = _load_json("specs/dlr.schema.json")
              self.example = _load_json(
                  "llm_data_model/03_examples/dlr_claim_native_example.json"
              )
              self.validate = jsonschema.validate

    def test_example_validates(self):
              """The shipped example must conform to the schema."""
              self.validate(instance=self.example, schema=self.schema)

    def test_dlr_id_present(self):
              """dlrId must be present."""
              assert "dlrId" in self.example

    def test_claim_refs_not_empty(self):
              """claimRefs must have at least one entry."""
              assert len(self.example.get("claimRefs", [])) >= 1


# ── Canon Schema ─────────────────────────────────────────────────

class TestCanonSchema:
      """Structural tests for canon.schema.json."""

    @pytest.fixture(autouse=True)
    def _load(self):
              pytest.importorskip("jsonschema")
              self.schema = _load_json("specs/canon.schema.json")

    def test_schema_loads(self):
              """Schema must parse as valid JSON."""
              assert self.schema["title"].startswith("Canon")

    def test_required_fields(self):
              """Required fields include canonId, claimIds, seal."""
              required = self.schema["required"]
              assert "canonId" in required
              assert "claimIds" in required
              assert "seal" in required


# ── Retcon Schema ────────────────────────────────────────────────

class TestRetconSchema:
      """Structural tests for retcon.schema.json."""

    @pytest.fixture(autouse=True)
    def _load(self):
              pytest.importorskip("jsonschema")
              self.schema = _load_json("specs/retcon.schema.json")

    def test_schema_loads(self):
              """Schema must parse as valid JSON."""
              assert self.schema["title"].startswith("Retcon")

    def test_required_fields(self):
              """Required fields include retconId, originalClaimId, newClaimId."""
              required = self.schema["required"]
              assert "retconId" in required
              assert "originalClaimId" in required
              assert "newClaimId" in required
