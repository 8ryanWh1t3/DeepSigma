"""Tests for engine/policy_loader.py — Issue #3."""
import json
import pytest
from pathlib import Path
from engine.policy_loader import load_policy_pack, get_rules


@pytest.fixture
def sample_pack(tmp_path: Path) -> Path:
      """Create a minimal policy pack JSON file for testing."""
      pack = {
          "policyPackId": "test_pack",
          "version": "1.0.0",
          "policyPackHash": "abc123",
          "rules": {
              "AccountQuarantine": {
                  "dteDefaults": {
                      "decisionWindowMs": 120,
                      "ttlMs": 500,
                      "maxFeatureAgeMs": 200,
                  },
                  "degradeLadder": ["cache_bundle", "rules_only", "hitl", "abstain"],
              }
          },
      }
      p = tmp_path / "test_pack.json"
      p.write_text(json.dumps(pack), encoding="utf-8")
      return p


def test_load_policy_pack_returns_dict(sample_pack: Path):
      pack = load_policy_pack(str(sample_pack))
      assert isinstance(pack, dict)
      assert pack["policyPackId"] == "test_pack"


def test_load_policy_pack_has_rules(sample_pack: Path):
      pack = load_policy_pack(str(sample_pack))
      assert "rules" in pack
      assert "AccountQuarantine" in pack["rules"]


def test_get_rules_returns_decision_type_rules(sample_pack: Path):
      pack = load_policy_pack(str(sample_pack))
      rules = get_rules(pack, "AccountQuarantine")
      assert "dteDefaults" in rules
      assert "degradeLadder" in rules
      assert rules["dteDefaults"]["decisionWindowMs"] == 120


def test_get_rules_returns_empty_for_unknown_type(sample_pack: Path):
      pack = load_policy_pack(str(sample_pack))
      rules = get_rules(pack, "UnknownType")
      assert rules == {}


def test_load_policy_pack_file_not_found():
      with pytest.raises(FileNotFoundError):
                load_policy_pack("/nonexistent/path/pack.json")


def test_load_policy_pack_invalid_json(tmp_path: Path):
      bad = tmp_path / "bad.json"
      bad.write_text("not valid json", encoding="utf-8")
      with pytest.raises(json.JSONDecodeError):
                load_policy_pack(str(bad))
