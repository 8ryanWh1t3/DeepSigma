"""SHACL validation tests for Claim Primitive.

Validate claim_primitive_instance.ttl against claim_primitive.shacl.ttl."""
import os
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestClaimSHACL(unittest.TestCase):
    """Validate Claim Primitive instance against SHACL shapes."""

    @classmethod
    def setUpClass(cls):
        rdflib = __import__("rdflib")
        pyshacl = __import__("pyshacl")
        cls.rdflib = rdflib
        cls.pyshacl = pyshacl

        cls.data_graph = rdflib.Graph()
        cls.data_graph.parse(
            os.path.join(_REPO_ROOT, "rdf/examples/claim_primitive_instance.ttl"),
            format="turtle",
        )

        cls.shapes_graph = rdflib.Graph()
        cls.shapes_graph.parse(
            os.path.join(_REPO_ROOT, "rdf/shapes/claim_primitive.shacl.ttl"),
            format="turtle",
        )

        cls.conforms, cls.results_graph, cls.results_text = pyshacl.validate(
            cls.data_graph,
            shacl_graph=cls.shapes_graph,
            inference="none",
        )

    def test_conforms(self):
        """Instance data must conform to SHACL shapes."""
        self.assertTrue(self.conforms, f"SHACL violations:\n{self.results_text}")

    def test_claim_has_statement(self):
        """CLAIM-2026-0001 must have a ds:statement property."""
        query = """
        PREFIX ds: <https://deepsigma.ai/ns/coherence#>
        PREFIX ex: <https://deepsigma.ai/ns/examples/>
        SELECT ?stmt
        WHERE { ex:CLAIM-2026-0001 ds:statement ?stmt }
        """
        results = list(self.data_graph.query(query))
        self.assertEqual(len(results), 1, "Expected exactly 1 statement")

    def test_claim_has_confidence(self):
        """CLAIM-2026-0001 must have a ds:confidence property."""
        query = """
        PREFIX ds: <https://deepsigma.ai/ns/coherence#>
        PREFIX ex: <https://deepsigma.ai/ns/examples/>
        SELECT ?conf
        WHERE { ex:CLAIM-2026-0001 ds:confidence ?conf }
        """
        results = list(self.data_graph.query(query))
        self.assertTrue(len(results) >= 1, "Expected at least 1 confidence value")

    def test_claim_query_all(self):
        """Query should return claimId, statement, owner for all claims."""
        query = """
        PREFIX ds: <https://deepsigma.ai/ns/coherence#>
        PREFIX ex: <https://deepsigma.ai/ns/examples/>
        SELECT ?claimId ?statement ?owner
        WHERE {
            ex:CLAIM-2026-0001 ds:claimId ?claimId ;
                               ds:statement ?statement ;
                               ds:owner ?owner .
        }
        """
        results = list(self.data_graph.query(query))
        self.assertEqual(len(results), 1, "Expected 1 result row")
        claim_id, statement, owner = results[0]
        self.assertTrue(str(claim_id).startswith("CLAIM-202"))
        self.assertTrue(len(str(statement)) >= 10)
        self.assertTrue(len(str(owner)) >= 1)

    def test_claim_has_sources(self):
        """CLAIM-2026-0001 must have at least one source."""
        query = """
        PREFIX ds: <https://deepsigma.ai/ns/coherence#>
        PREFIX ex: <https://deepsigma.ai/ns/examples/>
        SELECT (COUNT(?src) AS ?count)
        WHERE { ex:CLAIM-2026-0001 ds:hasSource ?src }
        """
        results = list(self.data_graph.query(query))
        count = int(results[0][0])
        self.assertTrue(count >= 1, f"Expected >= 1 source, got {count}")

    def test_claim_has_seal(self):
        """CLAIM-2026-0001 must have exactly 1 seal."""
        query = """
        PREFIX ds: <https://deepsigma.ai/ns/coherence#>
        PREFIX ex: <https://deepsigma.ai/ns/examples/>
        SELECT (COUNT(?seal) AS ?count)
        WHERE { ex:CLAIM-2026-0001 ds:hasSeal ?seal }
        """
        results = list(self.data_graph.query(query))
        count = int(results[0][0])
        self.assertEqual(count, 1, f"Expected exactly 1 seal, got {count}")

    def test_ontology_files_parse(self):
        """Both ontology and shapes files must parse without error."""
        g = self.rdflib.Graph()
        g.parse(
            os.path.join(_REPO_ROOT, "rdf/ontology/coherence_ops_core.ttl"),
            format="turtle",
        )
        g.parse(
            os.path.join(_REPO_ROOT, "rdf/ontology/claim_primitive.ttl"),
            format="turtle",
        )
        self.assertTrue(len(g) > 0)


if __name__ == "__main__":
    unittest.main()
