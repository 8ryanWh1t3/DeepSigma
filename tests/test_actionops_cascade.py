"""Tests for ActionOps cascade rules."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.modes.cascade_rules import RULES, get_rules_for_event


# ── Rule Registration ─────────────────────────────────────────────


class TestActionOpsCascadeRules:
    def test_four_actionops_rules_registered(self):
        action_rules = [r for r in RULES if r.target_domain == "actionops" or r.source_domain == "actionops"]
        assert len(action_rules) == 4

    def test_r14_authority_to_actionops(self):
        rules = get_rules_for_event("authorityops", "authority_approved")
        assert any(r.rule_id == "CASCADE-R14" for r in rules)
        r14 = next(r for r in rules if r.rule_id == "CASCADE-R14")
        assert r14.target_domain == "actionops"
        assert r14.target_function_id == "ACTION-F01"

    def test_r15_actionops_to_reflectionops(self):
        rules = get_rules_for_event("actionops", "commitment_breached")
        assert any(r.rule_id == "CASCADE-R15" for r in rules)
        r15 = next(r for r in rules if r.rule_id == "CASCADE-R15")
        assert r15.target_domain == "reflectionops"
        assert r15.target_function_id == "RE-F08"

    def test_r16_actionops_to_intelops(self):
        rules = get_rules_for_event("actionops", "commitment_completed")
        assert any(r.rule_id == "CASCADE-R16" for r in rules)
        r16 = next(r for r in rules if r.rule_id == "CASCADE-R16")
        assert r16.target_domain == "intelops"
        assert r16.target_function_id == "INTEL-F12"

    def test_r17_actionops_to_franops(self):
        rules = get_rules_for_event("actionops", "commitment_escalated")
        assert any(r.rule_id == "CASCADE-R17" for r in rules)
        r17 = next(r for r in rules if r.rule_id == "CASCADE-R17")
        assert r17.target_domain == "franops"
        assert r17.target_function_id == "FRAN-F03"

    def test_total_rule_count(self):
        assert len(RULES) == 17

    def test_rule_ids_unique(self):
        ids = [r.rule_id for r in RULES]
        assert len(ids) == len(set(ids))

    def test_red_drift_still_catches_actionops(self):
        """CASCADE-R07 wildcard rule catches red-severity ActionOps events."""
        rules = get_rules_for_event("actionops", "commitment_breached", severity="red")
        r07 = [r for r in rules if r.rule_id == "CASCADE-R07"]
        assert len(r07) == 1
