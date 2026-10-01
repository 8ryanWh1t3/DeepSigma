import unittest
from vinculum import VinculumEngine, DominantState, ObjectType, ScoreMode, ingest_text

class LanguageTests(unittest.TestCase):
    def setUp(self): self.e = VinculumEngine()

    def score(self, text):
        return self.e.score(ingest_text(text, object_type=ObjectType.CLAIM, mode=ScoreMode.LANGUAGE, decompose=False))

    def test_plain_language_leans_p(self):
        r = self.score("The vehicle is near the gate.")
        self.assertGreater(r.probabilistic_pressure, r.deterministic_strength)

    def test_hedges_raise_p(self):
        a = self.score("The vehicle is near the gate.")
        b = self.score("The vehicle may possibly be near the gate and is likely moving.")
        self.assertGreater(b.probabilistic_pressure, a.probabilistic_pressure)

    def test_definition_raises_d(self):
        a = self.score("A track is important.")
        b = self.score('"confirmed track" is defined as a track persisting for at least 5 seconds.')
        self.assertGreater(b.deterministic_strength, a.deterministic_strength)

    def test_quantified_constraint_raises_d(self):
        r = self.score("Track TRK-204 shall be classified as UAS when speed is at most 45 m/s.")
        self.assertGreater(r.deterministic_strength, 0.45)

    def test_rdf_tokens_raise_d(self):
        r = self.score("ex:Track204 rdf:type ex:Track and skos:prefLabel means its preferred label.")
        self.assertGreater(r.deterministic_strength, 0.45)

    def test_uncertainty_driver_exposed(self):
        r = self.score("The source is uncertain and the value is approximately 10.")
        ids = {s.id for s in r.drivers_p}
        self.assertIn("P_UNCERTAIN", ids)
        self.assertIn("P_APPROX", ids)

    def test_sigma_vector_present(self):
        d = self.score("The vehicle may be present.").to_dict(include_children=False)
        self.assertEqual(set(d["Sigma_V"].keys()), {"P","D","V","tau","Coverage"})

    def test_not_truth_score(self):
        wrong_but_exact = self.score("The Moon is defined as exactly 3 meters wide.")
        self.assertGreater(wrong_but_exact.deterministic_strength, 0.3)

if __name__ == '__main__': unittest.main()
