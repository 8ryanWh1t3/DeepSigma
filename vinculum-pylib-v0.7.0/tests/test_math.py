import unittest
from vinculum import VinculumEngine, ObjectType, ScoreMode, ingest_text

class MathTests(unittest.TestCase):
    def setUp(self): self.e = VinculumEngine()
    def score(self, text): return self.e.score(ingest_text(text, object_type=ObjectType.MATH, mode=ScoreMode.MATH, decompose=False))

    def test_exact_equation_d_dominant(self):
        r = self.score("2 + 2 = 4")
        self.assertGreater(r.deterministic_strength, r.probabilistic_pressure)
        self.assertGreater(r.vinculum_score, 75)

    def test_approximation_raises_p(self):
        exact = self.score("x = 4")
        approx = self.score("x ≈ 4")
        self.assertGreater(approx.probabilistic_pressure, exact.probabilistic_pressure)

    def test_plus_minus_raises_p(self):
        r = self.score("x = 4 ± 0.5")
        self.assertTrue(any(s.id == "P_PLUS_MINUS" for s in r.drivers_p))

    def test_confidence_creates_tension(self):
        r = self.score("x ≈ 4 ± 0.5 with 80% confidence")
        self.assertGreater(r.tension_index, 0.25)

    def test_empty_math_unmeasured(self):
        r = self.score("")
        self.assertEqual(r.coverage, 0)

    def test_math_without_markers_low_coverage(self):
        r = self.score("this is not an equation")
        self.assertLess(r.coverage, 0.2)

if __name__ == '__main__': unittest.main()
