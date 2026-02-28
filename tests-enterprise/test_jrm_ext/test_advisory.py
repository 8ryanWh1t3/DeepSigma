"""Tests for JRM Advisory Engine."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "enterprise" / "src"))

from deepsigma.jrm_ext.federation.advisory import AdvisoryEngine
from deepsigma.jrm_ext.types import CrossEnvDrift, CrossEnvDriftType


class TestAdvisoryEngine:
    def test_publish(self):
        drift = CrossEnvDrift(
            drift_id="XDS-001",
            drift_type=CrossEnvDriftType.VERSION_SKEW,
            severity="medium",
            environments=["SOC_EAST", "SOC_WEST"],
            signature_id="sig:2010935",
            detail="Revisions differ",
        )
        engine = AdvisoryEngine()
        advisories = engine.publish([drift])
        assert len(advisories) == 1
        assert advisories[0].status == "published"
        assert advisories[0].drift_type == "VERSION_SKEW"
        assert "SOC_EAST" == advisories[0].source_env
        assert "SOC_WEST" in advisories[0].target_envs

    def test_accept_decline(self):
        drift = CrossEnvDrift(
            drift_id="XDS-002",
            drift_type=CrossEnvDriftType.POSTURE_DIVERGENCE,
            severity="high",
            environments=["A", "B"],
        )
        engine = AdvisoryEngine()
        advisories = engine.publish([drift])
        adv_id = advisories[0].advisory_id

        assert engine.accept(adv_id) is True
        assert engine.list_advisories()[0].status == "accepted"

    def test_decline(self):
        drift = CrossEnvDrift(
            drift_id="XDS-003",
            drift_type=CrossEnvDriftType.REFINEMENT_CONFLICT,
            severity="high",
            environments=["A", "B"],
        )
        engine = AdvisoryEngine()
        advisories = engine.publish([drift])
        adv_id = advisories[0].advisory_id

        assert engine.decline(adv_id) is True
        assert engine.list_advisories()[0].status == "declined"

    def test_unknown_advisory(self):
        engine = AdvisoryEngine()
        assert engine.accept("nonexistent") is False
        assert engine.decline("nonexistent") is False
