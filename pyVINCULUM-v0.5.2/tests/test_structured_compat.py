import unittest
from vinculum import VinculumEngine, ObjectType, ScoreMode, VinculumObject
from vinculum.compat_v04 import Hypothesis, Constraint, LegacyV04Adapter

class StructuredCompatTests(unittest.TestCase):
    def test_structured_numeric_d(self):
        obj = VinculumObject("row", ObjectType.DATA_ROW, {"x":1,"y":2}, ScoreMode.STRUCTURED)
        r = VinculumEngine().score(obj)
        self.assertGreater(r.deterministic_strength, r.probabilistic_pressure)

    def test_structured_nulls_reduce_coverage(self):
        obj = VinculumObject("row", ObjectType.DATA_ROW, {"x":1,"y":None}, ScoreMode.STRUCTURED)
        r = VinculumEngine().score(obj)
        self.assertLess(r.coverage, 1)

    def test_legacy_adapter(self):
        h = Hypothesis("H1", "The range may be about 10 m", 0.7)
        c = (Constraint("C1", "range", "gte", 9),)
        r = LegacyV04Adapter().score_hypothesis(h, c)
        self.assertEqual(r.object_id, "H1")
        self.assertEqual(r.metadata["legacy_constraint_count"], 1)

if __name__ == '__main__': unittest.main()
