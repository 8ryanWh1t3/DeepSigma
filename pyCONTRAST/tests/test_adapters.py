import unittest

from deepsigma_contrast import Assumption, ContrastEngine, Episode, Outcome, InMemoryEpisodeStore
from deepsigma_contrast.adapters import PathfinderAdapter, ResonatorAdapter


class AdapterTests(unittest.TestCase):
    def test_pathfinder_returns_comparable(self):
        store = InMemoryEpisodeStore()
        store.add(Episode(id="p1", title="Prior", claim="sensor coverage", tags={"cuas"}))
        current = Episode(id="c1", title="Current", claim="sensor coverage degraded", tags={"cuas"})
        results = PathfinderAdapter(store).comparable_episodes(current)
        self.assertEqual(results[0][0].id, "p1")

    def test_resonator_projects_findings(self):
        prior = Episode(
            id="p", title="P", claim="x",
            assumptions=[Assumption("A", "x", 0.9)],
            outcome=Outcome("SUCCESS")
        )
        current = Episode(
            id="c", title="C", claim="x",
            assumptions=[Assumption("A", "x", 0.1)],
            outcome=Outcome("FAILURE")
        )
        result = ContrastEngine().compare(current_episode=current, prior_episode=prior)
        findings = ResonatorAdapter().analyze(result)
        self.assertTrue(any(f.kind == "ASSUMPTION_DELTA" for f in findings))
        self.assertTrue(any(f.kind == "OUTCOME_DELTA" for f in findings))


if __name__ == "__main__":
    unittest.main()
