import unittest

from vinculum import (
    MeaningRegistry,
    MeaningRule,
    ObjectType,
    ScoreMode,
    VinculumEngine,
    ingest_mapping,
    ingest_text,
    ingest_ttl,
)


class SecondOrderTests(unittest.TestCase):
    def setUp(self):
        self.engine = VinculumEngine()

    def math(self, text):
        return self.engine.score(
            ingest_text(text, object_type=ObjectType.MATH, mode=ScoreMode.MATH, decompose=False)
        )

    def test_exact_math_has_full_defense(self):
        r = self.math("2 + 2 = 4")
        self.assertAlmostEqual(r.deterministic_defense_strength, 1.0)
        self.assertAlmostEqual(r.probabilistic_contamination, 0.0)
        self.assertAlmostEqual(r.raw_deterministic_strength, r.defended_deterministic_strength)

    def test_approximation_weakens_math_defense(self):
        exact = self.math("x = 4")
        approx = self.math("x ≈ 4")
        self.assertLess(approx.deterministic_defense_strength, exact.deterministic_defense_strength)
        self.assertGreater(approx.probabilistic_contamination, exact.probabilistic_contamination)
        self.assertLess(approx.defended_deterministic_strength, approx.raw_deterministic_strength)

    def test_explicit_55_percent_reliability_sets_defense(self):
        r = self.math("x = 4 with reliability 55%")
        self.assertAlmostEqual(r.deterministic_defense_strength, 0.55)
        self.assertAlmostEqual(r.probabilistic_contamination, 0.45)
        self.assertAlmostEqual(r.defended_deterministic_strength, r.raw_deterministic_strength * 0.55)

    def test_postfix_80_percent_confidence_sets_defense(self):
        r = self.math("x ≈ 4 ± 0.5 with 80% confidence")
        self.assertAlmostEqual(r.deterministic_defense_strength, 0.80)
        self.assertAlmostEqual(r.probabilistic_contamination, 0.20)

    def test_structured_record_confidence_reduces_collision(self):
        def run(confidence):
            ep = {
                "claims": ["The order is a baker's dozen."],
                "receipt": {"item": "Baker's Dozen Cookies", "quantity": 12, "confidence": confidence},
            }
            return self.engine.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id=f"EP-{confidence}"))

        strong = run(0.99)
        weak = run(0.42)
        self.assertAlmostEqual(strong.deterministic_defense_strength, 0.99)
        self.assertAlmostEqual(weak.deterministic_defense_strength, 0.42)
        self.assertGreater(strong.semantic_record_tension, weak.semantic_record_tension)
        self.assertLess(weak.defended_deterministic_strength, weak.raw_deterministic_strength)

    def test_percentage_record_confidence_normalizes(self):
        ep = {
            "claims": ["The order is a baker's dozen."],
            "receipt": {"item": "Baker's Dozen Cookies", "quantity": 12, "sensor_confidence": "42%"},
        }
        r = self.engine.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="EP-PCT"))
        self.assertAlmostEqual(r.deterministic_defense_strength, 0.42)
        self.assertAlmostEqual(r.reconciliation["comparisons"][0]["probabilistic_contamination"], 0.58)

    def test_cuas_same_collision_changes_with_sensor_confidence(self):
        rule = MeaningRule.compile(
            id="SEM_AIRSPACE_CLEAR",
            label="airspace clear",
            pattern=r"\bairspace\s+(?:is\s+)?clear\b",
            dimension="count",
            operator="eq",
            value=0,
            unit="count",
            confidence=0.95,
            priority=5,
        )
        engine = VinculumEngine(meaning_registry=MeaningRegistry.default().with_rule(rule))

        def run(confidence):
            ep = {
                "claims": ["Airspace clear."],
                "observations": [
                    {"label": "active threat tracks", "count": 1, "sensor_confidence": confidence}
                ],
            }
            return engine.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id=f"CUAS-{confidence}"))

        strong = run(0.99)
        weak = run(0.42)
        self.assertEqual(strong.reconciliation_status, "CONFLICT")
        self.assertEqual(weak.reconciliation_status, "CONFLICT")
        self.assertGreater(strong.semantic_record_tension, weak.semantic_record_tension)
        self.assertAlmostEqual(strong.reconciliation["comparisons"][0]["semantic_determinization_strength"], 0.95)
        self.assertAlmostEqual(weak.reconciliation["comparisons"][0]["deterministic_defense_strength"], 0.42)

    def test_ttl_same_subject_confidence_weakens_record_defense(self):
        ttl = '''
        @prefix ex: <https://example.org/> .
        ex:order ex:label "baker's dozen" ;
                 ex:quantity 12 ;
                 ex:sensorConfidence 0.40 .
        '''
        r = self.engine.score(ingest_ttl(ttl, object_id="G"))
        self.assertEqual(r.reconciliation_status, "CONFLICT")
        self.assertAlmostEqual(r.deterministic_defense_strength, 0.40)
        self.assertAlmostEqual(r.probabilistic_contamination, 0.60)

    def test_structured_record_uncertainty_modifies_d_not_first_order_p(self):
        def run(confidence):
            ep = {
                "claims": ["The order is a baker's dozen."],
                "receipt": {"item": "Baker's Dozen Cookies", "quantity": 12, "sensor_confidence": confidence},
            }
            return self.engine.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id=f"SEP-{confidence}"))

        strong = run(0.99)
        weak = run(0.42)
        self.assertAlmostEqual(strong.probabilistic_pressure, weak.probabilistic_pressure)
        self.assertGreater(strong.defended_deterministic_strength, weak.defended_deterministic_strength)

    def test_collision_aliases_match_reconciliation(self):
        ep = {
            "claims": ["The order is a baker's dozen."],
            "receipt": {"item": "Baker's Dozen Cookies", "quantity": 12, "confidence": 0.8},
        }
        r = self.engine.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="ALIAS"))
        self.assertEqual(r.collision_status, r.reconciliation_status)
        self.assertAlmostEqual(r.collision_strength, r.semantic_record_tension)
        self.assertAlmostEqual(r.collision_coverage, r.comparison_coverage)
        self.assertIsNotNone(r.primary_collision)
        out = r.to_dict()
        self.assertIn("collision_model", out)
        self.assertAlmostEqual(out["collision_model"]["collision_strength"], r.collision_strength)


if __name__ == "__main__":
    unittest.main()
