import unittest

from vinculum import BoundedState, Constraint, ConstraintStatus, Hypothesis, Quantity, VinculumEngine


class VinculumTests(unittest.TestCase):
    def setUp(self):
        self.engine = VinculumEngine()

    def test_hard_pass_accepts(self):
        h = Hypothesis("H", "ok", 0.8, {"x": 10})
        d = Constraint("D", "x", "gte", 5)
        r = self.engine.bind([h], [d]).results[0]
        self.assertEqual(r.state, BoundedState.ACCEPTED)
        self.assertEqual(r.bounded_confidence, 0.8)

    def test_hard_fail_rejects_even_high_probability(self):
        h = Hypothesis("H", "high-confidence but invalid", 0.99, {"x": 1})
        d = Constraint("D", "x", "gte", 5)
        r = self.engine.bind([h], [d]).results[0]
        self.assertEqual(r.state, BoundedState.REJECTED)
        self.assertEqual(r.bounded_confidence, 0.0)

    def test_missing_hard_field_is_unresolved(self):
        h = Hypothesis("H", "unknown", 0.8, {})
        d = Constraint("D", "x", "gte", 5)
        r = self.engine.bind([h], [d]).results[0]
        self.assertEqual(r.state, BoundedState.UNRESOLVED)
        self.assertEqual(r.evaluations[0].status, ConstraintStatus.UNKNOWN)

    def test_soft_failure_modulates_score(self):
        h = Hypothesis("H", "soft miss", 0.8, {"x": 10, "quality": 1})
        constraints = [
            Constraint("D1", "x", "gte", 5, hard=True, weight=1),
            Constraint("D2", "quality", "gte", 2, hard=False, weight=1),
        ]
        r = self.engine.bind([h], constraints).results[0]
        self.assertEqual(r.state, BoundedState.ACCEPTED)
        self.assertEqual(r.soft_compliance, 0.0)
        self.assertEqual(r.bounded_confidence, 0.8)
        self.assertEqual(r.coherence_score, 0.0)

    def test_quantity_conversion(self):
        h = Hypothesis("H", "distance", 0.7, {"distance": {"value": 984, "unit": "in"}})
        d = Constraint("D", "distance", "gte", {"value": 82, "unit": "ft"})
        r = self.engine.bind([h], [d]).results[0]
        self.assertEqual(r.state, BoundedState.ACCEPTED)

    def test_quantity_dimension_mismatch_is_unknown(self):
        h = Hypothesis("H", "mismatch", 0.7, {"x": {"value": 3, "unit": "h"}})
        d = Constraint("D", "x", "gte", {"value": 3, "unit": "ft"})
        r = self.engine.bind([h], [d]).results[0]
        self.assertEqual(r.state, BoundedState.UNRESOLVED)
        self.assertEqual(r.evaluations[0].status, ConstraintStatus.UNKNOWN)

    def test_quantity_api(self):
        self.assertAlmostEqual(Quantity(1, "ft").convert_to("in").value, 12.0)

    def test_best_supported_only_uses_accepted(self):
        h1 = Hypothesis("A", "accepted", 0.60, {"x": 10})
        h2 = Hypothesis("B", "rejected but higher P", 0.95, {"x": 1})
        d = Constraint("D", "x", "gte", 5)
        report = self.engine.bind([h1, h2], [d])
        self.assertEqual(report.best_supported_id, "A")

    def test_requires_hard_boundary_by_default(self):
        h = Hypothesis("H", "only soft", 0.8, {"x": 10})
        d = Constraint("D", "x", "gte", 5, hard=False)
        r = self.engine.bind([h], [d]).results[0]
        self.assertEqual(r.state, BoundedState.UNRESOLVED)

    def test_no_constraints_is_unresolved(self):
        h = Hypothesis("H", "unbounded", 0.8, {"x": 10})
        r = self.engine.bind([h], []).results[0]
        self.assertEqual(r.state, BoundedState.UNRESOLVED)
        self.assertEqual(r.constraint_coverage, 0.0)

    def test_receipt_is_deterministic(self):
        h = Hypothesis("H", "stable", 0.8, {"x": 10})
        d = Constraint("D", "x", "gte", 5)
        a = self.engine.bind([h], [d]).sha256()
        b = self.engine.bind([h], [d]).sha256()
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
