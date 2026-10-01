import io, json, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from vinculum import VinculumEngine, ObjectType, ScoreMode, ingest_text, ingest_file
from vinculum.cli import main

class ModesCliTests(unittest.TestCase):
    def test_auto_language(self):
        r = VinculumEngine().score(ingest_text("This may be correct.", decompose=False))
        self.assertEqual(r.mode, ScoreMode.LANGUAGE)

    def test_auto_math(self):
        r = VinculumEngine().score(ingest_text("x + 2 = 4 and y > 1", object_type=ObjectType.MATH, decompose=False))
        self.assertEqual(r.mode, ScoreMode.MATH)

    def test_file_ttl_detection(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"x.ttl"
            p.write_text('@prefix ex: <https://e/> . ex:a ex:p ex:b .', encoding='utf-8')
            obj = ingest_file(p)
            self.assertEqual(obj.object_type, ObjectType.TTL_GRAPH)

    def test_cli_literal(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["score", "This may be true", "--summary"])
        self.assertEqual(rc, 0)
        d = json.loads(buf.getvalue())
        self.assertIn("Sigma_V", d)

    def test_cli_file(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"doc.txt"; p.write_text("Maybe A.\n\nB is defined as exactly 2 m.", encoding='utf-8')
            buf=io.StringIO()
            with redirect_stdout(buf): rc=main(["score", str(p), "--pretty"])
            self.assertEqual(rc,0)
            d=json.loads(buf.getvalue())
            self.assertEqual(d["object_type"], "document")

if __name__ == '__main__': unittest.main()
