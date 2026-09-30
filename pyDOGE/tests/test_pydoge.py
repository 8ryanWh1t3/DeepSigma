import json
import unittest
from pathlib import Path

from pydoge import WorkSystem
from pydoge.cerpa import CERPALedger


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples" / "agency.json"


class PyDOGETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = WorkSystem.load(DATA)

    def test_explain_traces_mission_and_authority(self):
        x = self.ws.explain("W3")
        self.assertEqual(x["why_it_exists"]["mission"], "Mission Readiness Reporting")
        self.assertEqual(x["why_it_exists"]["policy_authority_chain"][0]["status"], "BOUND")

    def test_orphan_work(self):
        ids = {x["work_id"] for x in self.ws.find_orphan_tasks()}
        self.assertIn("W6", ids)

    def test_duplicate_candidate(self):
        pairs = {(x["work_a"], x["work_b"]) for x in self.ws.find_duplicate_work(threshold=0.55)}
        self.assertTrue(("W3", "W4") in pairs or ("W4", "W3") in pairs)

    def test_blast_radius(self):
        x = self.ws.calculate_blast_radius("W1")
        self.assertIn("W5", x["downstream_work"])

    def test_automation_scores_work_not_people(self):
        rows = self.ws.find_automation_candidates()
        self.assertTrue(any(x["work_id"] == "W2" for x in rows))
        self.assertFalse(any(x["work_id"] == "W6" for x in rows), "orphan work must be validated before automation")
        blob = json.dumps(self.ws.optimize()).lower()
        self.assertNotIn("employee score", blob)
        self.assertIn("does not rank or score individual employees", blob)

    def test_cerpa_order_objects(self):
        ledger = CERPALedger()
        ledger.append("claim", "C1", "W2", "Duplicate entry creates avoidable work")
        ledger.append("event", "E1", "W2", "Integration test completed")
        ledger.append("review", "R1", "W2", "Validated automation boundary")
        ledger.append("patch", "P1", "W2", "Replace manual re-entry with API transfer")
        ledger.append("apply", "A1", "W2", "Patch approved and applied")
        self.assertEqual([x["kind"] for x in ledger.records()], ["CLAIM", "EVENT", "REVIEW", "PATCH", "APPLY"])


if __name__ == "__main__":
    unittest.main()
