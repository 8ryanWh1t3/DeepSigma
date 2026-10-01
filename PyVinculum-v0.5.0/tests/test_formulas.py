import unittest
from vinculum import derive_vector

class FormulaTests(unittest.TestCase):
    def test_equal_pd_is_boundary(self):
        v = derive_vector(0.5, 0.5, 1.0)
        self.assertAlmostEqual(v.vinculum_signed, 0.0)
        self.assertAlmostEqual(v.vinculum_score, 50.0)
        self.assertAlmostEqual(v.tension_balance, 1.0)

    def test_p_dominant(self):
        v = derive_vector(0.8, 0.2, 1.0)
        self.assertLess(v.vinculum_signed, 0)
        self.assertLess(v.vinculum_score, 50)

    def test_d_dominant(self):
        v = derive_vector(0.2, 0.8, 1.0)
        self.assertGreater(v.vinculum_signed, 0)
        self.assertGreater(v.vinculum_score, 50)

    def test_zero_total_neutral(self):
        v = derive_vector(0, 0, 0)
        self.assertEqual(v.vinculum_score, 50)
        self.assertEqual(v.usable_value, 50)

    def test_coverage_damps_usable_value(self):
        full = derive_vector(0.8, 0.2, 1)
        half = derive_vector(0.8, 0.2, 0.5)
        self.assertLess(abs(half.usable_value - 50), abs(full.usable_value - 50))

    def test_effective_tension_uses_intensity(self):
        low = derive_vector(0.1, 0.1, 1)
        high = derive_vector(0.8, 0.8, 1)
        self.assertGreater(high.effective_tension, low.effective_tension)

    def test_ranges(self):
        for P in [0, .1, .5, 1]:
            for D in [0, .1, .5, 1]:
                v = derive_vector(P, D, .7)
                self.assertTrue(-1 <= v.vinculum_signed <= 1)
                self.assertTrue(0 <= v.vinculum_score <= 100)
                self.assertTrue(0 <= v.effective_tension <= 1)
                self.assertTrue(0 <= v.usable_value <= 100)

if __name__ == '__main__': unittest.main()
