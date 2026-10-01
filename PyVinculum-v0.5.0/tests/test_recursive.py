import unittest
from vinculum import VinculumEngine, ObjectType, ingest_mapping, ingest_text

class RecursiveTests(unittest.TestCase):
    def setUp(self): self.e = VinculumEngine()

    def test_document_decomposes(self):
        obj = ingest_text("Likely A.\n\nB is defined as exactly 4 m.", object_type=ObjectType.DOCUMENT)
        self.assertEqual(len(obj.children), 2)
        r = self.e.score(obj)
        self.assertEqual(len(r.children), 2)

    def test_weighted_document_rollup(self):
        obj = ingest_text("Maybe.\n\nThis value is defined as exactly 4 m and shall not exceed 4 m.", object_type=ObjectType.DOCUMENT)
        r = self.e.score(obj)
        self.assertTrue(0 <= r.probabilistic_pressure <= 1)
        self.assertTrue(0 <= r.deterministic_strength <= 1)

    def test_episode_children(self):
        ep = {"claims":["likely target", "ID TRK-1 shall mean track one"], "events":[{"speed":41.2}], "decisions":["review"]}
        obj = ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="EP-1")
        self.assertEqual(len(obj.children), 4)
        r = self.e.score(obj)
        self.assertEqual(len(r.children), 4)

    def test_dataset_children(self):
        obj = ingest_mapping([{"x":1},{"x":2},{"x":None}], object_type=ObjectType.DATASET, object_id="DS")
        r = self.e.score(obj)
        self.assertEqual(len(r.children), 3)
        self.assertLess(r.coverage, 1.0)

    def test_child_weights_affect_rollup(self):
        a = ingest_text("maybe likely uncertain", object_id="a", decompose=False)
        b = ingest_text("defined as exactly 4 m", object_id="b", decompose=False)
        from vinculum import VinculumObject
        parent = VinculumObject("p", ObjectType.DOCUMENT, "", children=(type(a)(a.object_id,a.object_type,a.content,a.mode,10.0,a.metadata,a.children), b))
        r = self.e.score(parent)
        self.assertGreater(r.probabilistic_pressure, r.deterministic_strength)

if __name__ == '__main__': unittest.main()
