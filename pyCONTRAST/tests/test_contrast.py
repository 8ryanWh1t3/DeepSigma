import unittest

from deepsigma_contrast import (
    Assumption,
    ContrastEngine,
    Episode,
    EvidenceRef,
    Outcome,
    contrast_to_dsal,
    generate_pairs,
    to_cerpa_handoff,
)


def prior_episode():
    return Episode(
        id="EP-1",
        title="Stable coverage",
        claim="Coverage is sufficient",
        decision="Maintain posture",
        rationale="Telemetry met threshold",
        assumptions=[Assumption("A1", "Sensor is available", 0.9)],
        outcome=Outcome("SUCCESS", "Stable", {"coverage": 0.95}),
        evidence=[EvidenceRef("E1", "mem://e1", 0.9)],
        tags={"C-UAS", "coverage"},
        entities=["sensor-a"],
        metadata={"weather": "clear"},
    )


def current_episode():
    return Episode(
        id="EP-2",
        title="Coverage degradation",
        claim="Coverage is sufficient",
        decision="Maintain posture",
        rationale="Telemetry historically met threshold",
        assumptions=[Assumption("A1", "Sensor is available", 0.4)],
        outcome=Outcome("DEGRADED", "Gap", {"coverage": 0.60}),
        evidence=[EvidenceRef("E2", "mem://e2", 1.0)],
        tags={"C-UAS", "coverage"},
        entities=["sensor-a"],
        metadata={"weather": "heavy-rain"},
    )


class ContrastTests(unittest.TestCase):
    def setUp(self):
        self.engine = ContrastEngine()
        self.prior = prior_episode()
        self.current = current_episode()
        self.result = self.engine.compare(current_episode=self.current, prior_episode=self.prior)

    def test_similarity_range(self):
        self.assertGreaterEqual(self.result.similarity, 0.0)
        self.assertLessEqual(self.result.similarity, 1.0)

    def test_outcome_delta_detected(self):
        self.assertTrue(any(d.kind == "OUTCOME_STATUS_CHANGED" for d in self.result.outcome_deltas))

    def test_assumption_confidence_delta_detected(self):
        self.assertTrue(any(d.kind == "ASSUMPTION_CONFIDENCE_CHANGED" for d in self.result.assumption_deltas))

    def test_context_delta_detected(self):
        self.assertTrue(any(d.key == "weather" for d in self.result.metadata_deltas))

    def test_discriminating_factors_created(self):
        self.assertGreater(len(self.result.discriminating_factors), 0)

    def test_advisory_only(self):
        self.assertTrue(self.result.advisory_only)

    def test_cerpa_never_auto_applies(self):
        h = to_cerpa_handoff(self.result)
        self.assertEqual(h.apply_status, "PENDING_AUTHORITY")
        self.assertFalse(h.authoritative)
        self.assertTrue(h.patch["requires_authority"])

    def test_dsal_blocks_apply(self):
        dsal = contrast_to_dsal(self.result)
        self.assertFalse(dsal["governance"]["applyPermitted"])
        self.assertTrue(dsal["governance"]["authorityRequiredForPatch"])

    def test_pair_generation_hard_negative(self):
        pairs = generate_pairs([self.prior, self.current], hard_negative_threshold=0.25)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].relation, "HARD_NEGATIVE")

    def test_evidence_delta_detected(self):
        self.assertGreaterEqual(len(self.result.evidence_deltas), 2)


if __name__ == "__main__":
    unittest.main()
