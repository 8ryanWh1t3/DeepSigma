"""Tests: validate RDF Claim Primitive instance against SHACL shapes.

Requires: pip install pyshacl rdflib
"""

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
      """Read a file relative to repo root."""
      return (ROOT / rel_path).read_text(encoding="utf-8")


class TestSHACLClaimPrimitive:
      """Validate claim_primitive_instance.ttl against claim_primitive.shacl.ttl."""

    @pytest.fixture(autouse=True)
    def _load(self):
              self.rdflib = pytest.importorskip("rdflib")
              self.pyshacl = pytest.importorskip("pyshacl")

        # Load ontology + instance
              self.data_graph = self.rdflib.Graph()
              self.data_graph.parse(
                  data=_read("rdf/ontology/claim_primitive.ttl"), format="turtle"
              )
              self.data_graph.parse(
                  data=_read("rdf/examples/claim_primitive_instance.ttl"), format="turtle"
              )

        # Load shapes
              self.shapes_graph = self.rdflib.Graph()
              self.shapes_graph.parse(
                  data=_read("rdf/shapes/claim_primitive.shacl.ttl"), format="turtle"
              )

    def test_instance_conforms_to_shapes(self):
              """The sample instance must pass all SHACL shape constraints."""
              conforms, results_graph, results_text = self.pyshacl.validate(
                  data_graph=self.data_graph,
                  shacl_graph=self.shapes_graph,
                  inference="rdfs",
                  abort_on_first=False,
              )
              assert conforms, f"SHACL validation failed:\n{results_text}"

    def test_data_graph_has_claim(self):
              """Data graph must contain at least one AtomicClaim instance."""
              query = """
              PREFIX ds: <https://deepsigma.ai/ns/coherence#>
              SELECT (COUNT(?c) AS ?count)
              WHERE { ?c a ds:AtomicClaim }
              """
              results = list(self.data_graph.query(query))
              count = int(results[0][0])
              assert count >= 1, "Expected at least 1 AtomicClaim in the data graph"

    def test_claim_has_required_properties(self):
              """CLAIM-2026-0001 must have claimId, statement, owner."""
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
              assert len(results) == 1, "Expected exactly 1 result for CLAIM-2026-0001"
              claim_id, statement, owner = results[0]
              assert str(claim_id) == "CLAIM-2026-0001"
              assert len(str(statement)) >= 10
              assert len(str(owner)) >= 1

    def test_claim_has_sources(self):
              """CLAIM-2026-0001 must have at least 1 ClaimSource."""
              query = """
              PREFIX ds: <https://deepsigma.ai/ns/coherence#>
              PREFIX ex: <https://deepsigma.ai/ns/examples/>
              SELECT (COUNT(?src) AS ?count)
              WHERE { ex:CLAIM-2026-0001 ds:hasClaimSource ?src }
              """
              results = list(self.data_graph.query(query))
              count = int(results[0][0])
              assert count >= 1, f"Expected >= 1 sources, got {count}"

    def test_claim_has_seal(self):
              """CLAIM-2026-0001 must have exactly 1 ClaimSeal."""
              query = """
              PREFIX ds: <https://deepsigma.ai/ns/coherence#>
              PREFIX ex: <https://deepsigma.ai/ns/examples/>
              SELECT (COUNT(?seal) AS ?count)
              WHERE { ex:CLAIM-2026-0001 ds:hasSeal ?seal }
              """
              results = list(self.data_graph.query(query))
              count = int(results[0][0])
              assert count == 1, f"Expected exactly 1 seal, got {count}"

    def test_ontology_files_parse(self):
              """Both ontology and shapes files must parse without error."""
              g = self.rdflib.Graph()
              g.parse(
                  data=_read("rdf/ontology/coherence_ops_core.ttl"), format="turtle"
              )
              assert len(g) > 0, "Core ontology should have triples"
