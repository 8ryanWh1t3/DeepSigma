import tempfile
import unittest
from pathlib import Path

from deepsigma_contrast import Episode, InMemoryEpisodeStore, JsonlEpisodeStore, find_comparable


class MemoryTests(unittest.TestCase):
    def test_in_memory_store(self):
        store = InMemoryEpisodeStore()
        ep = Episode(id="1", title="A", claim="alpha beta", tags={"x"})
        store.add(ep)
        self.assertEqual(store.get("1").id, "1")

    def test_find_comparable(self):
        current = Episode(id="c", title="Current", claim="alpha beta gamma", tags={"x"})
        close = Episode(id="a", title="Close", claim="alpha beta", tags={"x"})
        far = Episode(id="b", title="Far", claim="delta epsilon", tags={"z"})
        result = find_comparable(current, [far, close], top_k=1)
        self.assertEqual(result[0][0].id, "a")

    def test_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "episodes.jsonl"
            store = JsonlEpisodeStore(p)
            ep = Episode(id="1", title="A", claim="alpha", tags={"x"})
            store.add(ep)
            reload_store = JsonlEpisodeStore(p)
            self.assertEqual(reload_store.get("1").claim, "alpha")


if __name__ == "__main__":
    unittest.main()
