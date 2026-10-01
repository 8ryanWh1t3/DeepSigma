import unittest
from vinculum import VinculumEngine, ObjectType, ingest_ttl

TTL = '''
@prefix ex: <https://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:a a ex:Thing ; ex:value "42"^^xsd:integer ; ex:rel ex:b .
'''

class TTLTests(unittest.TestCase):
    def setUp(self): self.e = VinculumEngine()

    def test_parse_and_decompose(self):
        obj = ingest_ttl(TTL, object_id="g")
        self.assertTrue(obj.metadata["parsed"])
        self.assertEqual(obj.object_type, ObjectType.TTL_GRAPH)
        self.assertGreaterEqual(len(obj.children), 3)

    def test_ttl_d_dominant(self):
        r = self.e.score(ingest_ttl(TTL, object_id="g"))
        self.assertGreater(r.deterministic_strength, r.probabilistic_pressure)

    def test_triples_have_scores(self):
        r = self.e.score(ingest_ttl(TTL, object_id="g"))
        self.assertTrue(all(c.object_type is ObjectType.RDF_TRIPLE for c in r.children))

    def test_typed_literal_driver(self):
        r = self.e.score(ingest_ttl(TTL, object_id="g"))
        ids = {s.id for c in r.children for s in c.drivers_d}
        self.assertIn("D_TYPED_LITERAL", ids)

    def test_blank_node_raises_p(self):
        ttl = '@prefix ex: <https://example.org/> . [] ex:p ex:o .'
        r = self.e.score(ingest_ttl(ttl, object_id="b"))
        self.assertTrue(any(s.id.startswith("P_BNODE") for c in r.children for s in c.drivers_p) or any(s.id == "P_BNODES" for s in r.drivers_p))

    def test_malformed_ttl_partial_visibility(self):
        obj = ingest_ttl('@prefix ex: <https://example.org/> . ex:a ex:p "unterminated .', object_id="bad")
        self.assertFalse(obj.metadata["parsed"])
        r = self.e.score(obj)
        self.assertLess(r.coverage, 0.8)
        self.assertGreater(r.probabilistic_pressure, r.deterministic_strength)

if __name__ == '__main__': unittest.main()
