import unittest
from pathlib import Path

from pyontology import Fabric, OntologyModule

ROOT = Path(__file__).resolve().parents[1]


class CoherenceExampleTests(unittest.TestCase):
    def test_coherence_federation(self):
        fabric = Fabric()
        core = OntologyModule.load(
            ROOT / "examples/ontologies/coherence_ops_v2.ttl",
            ROOT / "examples/manifests/coherence_ops_v2.module.json",
        )
        lenses = OntologyModule.load(
            ROOT / "examples/ontologies/coherence_ops_lenses_v2.1.ttl",
            ROOT / "examples/manifests/coherence_ops_lenses_v2.1.module.json",
        )
        fabric.register(core)
        fabric.register(lenses)
        report = fabric.validate()
        self.assertTrue(report.ok, [f.message for f in report.errors])
        self.assertGreater(len(core.graph), 800)
        self.assertGreater(len(lenses.graph), 200)
        self.assertTrue(fabric.search("Decision"))


if __name__ == "__main__":
    unittest.main()
