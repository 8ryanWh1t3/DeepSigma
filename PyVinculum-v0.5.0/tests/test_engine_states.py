import unittest
from vinculum import VinculumEngine, DominantState, ObjectType, ScoreMode, ScoringConfig, VinculumObject, ingest_mapping, ingest_text

class EngineStateTests(unittest.TestCase):
    def test_probabilistic_dominant_label(self):
        r = VinculumEngine().score(ingest_text("This may possibly be true and is probably uncertain.", decompose=False))
        self.assertEqual(r.dominant_state, DominantState.PROBABILISTIC_DOMINANT)

    def test_deterministic_dominant_label(self):
        r = VinculumEngine().score(ingest_text("x + 2 = 4 and x = 2", object_type=ObjectType.MATH, mode=ScoreMode.MATH, decompose=False))
        self.assertEqual(r.dominant_state, DominantState.DETERMINISTIC_DOMINANT)

    def test_boundary_label(self):
        r = VinculumEngine().score(ingest_text("x ≈ 4 ± 0.5 with 80% confidence", object_type=ObjectType.MATH, mode=ScoreMode.MATH, decompose=False))
        self.assertEqual(r.dominant_state, DominantState.BOUNDARY_TENSION)

    def test_custom_thresholds(self):
        e = VinculumEngine(ScoringConfig(boundary_low=20, boundary_high=80))
        r = e.score(ingest_text("The object may be present.", decompose=False))
        self.assertEqual(r.dominant_state, DominantState.BOUNDARY_TENSION)

    def test_policy_decomposes_like_document(self):
        obj = ingest_text("Rule A may apply.\n\nRule B shall mean exactly 5 m.", object_type=ObjectType.POLICY)
        self.assertEqual(len(obj.children), 2)

    def test_corpus_from_mapping(self):
        obj = ingest_mapping(["Maybe A", "B is defined as exactly 2 m"], object_type=ObjectType.CORPUS, object_id="C")
        r = VinculumEngine().score(obj)
        self.assertEqual(len(r.children), 2)

    def test_sensor_observation_language(self):
        obj = VinculumObject("S", ObjectType.SENSOR_OBSERVATION, "Range approximately 80 meters", ScoreMode.LANGUAGE)
        r = VinculumEngine().score(obj)
        self.assertGreater(r.probabilistic_pressure, 0.45)
        self.assertGreater(r.deterministic_strength, 0.25)

    def test_model_output_structured(self):
        obj = VinculumObject("M", ObjectType.MODEL_OUTPUT, {"label":"uas", "score":0.72}, ScoreMode.STRUCTURED)
        r = VinculumEngine().score(obj)
        self.assertGreater(r.coverage, 0.9)

    def test_long_literal_cli_path_safety(self):
        from vinculum.cli import main
        import io, json
        from contextlib import redirect_stdout
        text = "may " * 2000
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["score", text, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("Sigma_V", json.loads(buf.getvalue()))

if __name__ == '__main__': unittest.main()
