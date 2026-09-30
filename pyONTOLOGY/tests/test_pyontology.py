import json
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph

from pyontology import Fabric, OntologyModule, SemanticCollisionError, diff_modules
from pyontology.model import BridgeSuggestion


TTL_A = '''
@prefix a: <https://a.example/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<https://a.example/ontology> a owl:Ontology ; owl:versionInfo "1.0" .
a:Installation a owl:Class ; rdfs:label "Installation" ; rdfs:comment "A managed physical site." .
a:Policy a owl:Class ; rdfs:label "Policy" .
'''

TTL_B = '''
@prefix b: <https://b.example/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<https://b.example/ontology> a owl:Ontology ; owl:versionInfo "1.1" .
b:Installation a owl:Class ; rdfs:label "Installation" ; rdfs:comment "A military or enterprise site." .
b:Facility a owl:Class ; rdfs:label "Facility" .
'''


class PyOntologyTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "a.ttl").write_text(TTL_A)
        (self.root / "b.ttl").write_text(TTL_B)
        self.a = OntologyModule.load(self.root / "a.ttl", module_id="a")
        self.b = OntologyModule.load(self.root / "b.ttl", module_id="b")

    def tearDown(self):
        self.td.cleanup()

    def test_load_and_stats(self):
        self.assertGreaterEqual(self.a.stats()["Class"], 2)
        self.assertEqual(self.a.manifest.version, "1.0")

    def test_collision_detection(self):
        f = Fabric()
        f.register(self.a)
        f.register(self.b)
        collisions = f.detect_collisions()
        self.assertTrue(any(c.normalized_label == "installation" for c in collisions))

    def test_bridge_discovery(self):
        f = Fabric()
        f.register(self.a)
        f.register(self.b)
        bridges = f.discover_bridges(threshold=0.70)
        self.assertTrue(any("Installation" in x.source_uri and "Installation" in x.target_uri for x in bridges))

    def test_creation_gate_blocks_duplicate(self):
        f = Fabric()
        f.register(self.a)
        f.register(self.b)
        proposal = f.propose_concept("b", "Installation")
        self.assertEqual(proposal.recommended_action, "REUSE")
        with self.assertRaises(SemanticCollisionError):
            f.add_concept("b", "https://b.example/NewInstallation", "Installation")

    def test_create_unique(self):
        f = Fabric()
        f.register(self.a)
        proposal = f.add_concept("a", "https://a.example/DecisionPacket", "Decision Packet")
        self.assertEqual(proposal.recommended_action, "CREATE")
        self.assertTrue(any(t.uri.endswith("DecisionPacket") for t in self.a.terms()))

    def test_registry_persistence(self):
        db = self.root / "registry.sqlite"
        f = Fabric(registry_path=db)
        f.register(self.a)
        self.assertTrue(db.exists())
        self.assertEqual(len(f.registry.exact_label("Installation")), 1)

    def test_diff(self):
        (self.root / "a2.ttl").write_text(TTL_A.replace('rdfs:label "Policy"', 'rdfs:label "Enterprise Policy"'))
        a2 = OntologyModule.load(self.root / "a2.ttl", module_id="a2")
        d = diff_modules(self.a, a2)
        self.assertGreater(d.added_triples, 0)
        self.assertGreater(d.removed_triples, 0)
        self.assertTrue(any(uri.endswith("Policy") for uri in d.changed_terms))

    def test_graph_fingerprint_stable_with_blank_nodes(self):
        ttl = """
@prefix ex: <https://x.example/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
ex:A a owl:Class ; owl:equivalentClass [ a owl:Class ; owl:unionOf (ex:B ex:C) ] .
ex:B a owl:Class . ex:C a owl:Class .
"""
        (self.root / "blank.ttl").write_text(ttl)
        x1 = OntologyModule.load(self.root / "blank.ttl", module_id="x1")
        x2 = OntologyModule.load(self.root / "blank.ttl", module_id="x2")
        self.assertEqual(x1.fingerprint, x2.fingerprint)

    def test_accepted_bridge_resolves_collision(self):
        f = Fabric()
        f.register(self.a)
        f.register(self.b)
        self.assertTrue(any(c.normalized_label == "installation" for c in f.detect_collisions()))
        bridge = BridgeSuggestion(
            source_uri="https://a.example/Installation", target_uri="https://b.example/Installation",
            source_module="a", target_module="b", relation="skos:exactMatch", score=1.0, rationale="approved test"
        )
        f.accept_bridge(bridge)
        self.assertFalse(any(c.normalized_label == "installation" for c in f.detect_collisions()))


if __name__ == "__main__":
    unittest.main()
