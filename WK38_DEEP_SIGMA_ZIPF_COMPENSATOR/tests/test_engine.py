"""Behavioral regression checks for attention, provenance, and simulated gates."""
from copy import deepcopy
import math
import unittest

from deep_sigma_zipf.engine import ValidationError, evaluate
from tests.fixtures import AS_OF, claim, evidence, invalid_scenarios, payload, valid_scenarios


def item(output, claim_id="A"):
    return next(value for value in output["items"] if value["id"] == claim_id)


class EngineBehaviorTests(unittest.TestCase):
    def test_manual_six_event_scores_and_selection(self):
        result = evaluate(payload())
        self.assertEqual(item(result)["base_score"], 80)
        self.assertEqual(item(result)["baseline_score"], 88)
        self.assertEqual(item(result)["rarity_bonus"], 4)
        self.assertEqual(item(result, "B")["baseline_score"], 84)
        self.assertEqual(item(result, "B")["rarity_bonus"], 12)
        self.assertEqual(result["modes"]["baseline"]["selected_ids"], ["C", "A"])
        self.assertEqual(result["modes"]["compensated"]["selected_ids"], ["C", "B"])
        self.assertEqual(result["diagnostics"]["unique_events"], 6)
        self.assertEqual(result["diagnostics"]["duplicate_reports"], 0)

    def test_flooring_is_explicit(self):
        p = payload()
        p["claims"][0].update(relevance=83, consequence=73, quality=61)
        actual = item(evaluate(p))
        self.assertEqual(actual["base_score"], 75)
        self.assertEqual(actual["baseline_score"], 83)
        self.assertEqual(actual["compensated_score"], 79)

    def test_one_hundred_copies_do_not_change_scores_or_gate(self):
        p = payload()
        before = evaluate(p)
        for n in range(100):
            p["reports"].append(dict(p["reports"][0], id=f"COPY_{n}"))
        after = evaluate(p)
        for original, copied in zip(before["items"], after["items"]):
            for field in ["base_score", "baseline_score", "rarity_bonus", "compensated_score",
                          "independent_events", "concept_events", "gate"]:
                self.assertEqual(original[field], copied[field], field)
        self.assertEqual(before["modes"], after["modes"])
        self.assertEqual(after["diagnostics"]["report_count"], 106)
        self.assertEqual(after["diagnostics"]["unique_events"], 6)
        self.assertEqual(after["diagnostics"]["duplicate_reports"], 100)
        self.assertEqual(item(after)["report_count"], 104)

    def test_genuine_recurrence_from_same_origin_counts(self):
        p = payload()
        p["reports"].append(dict(p["reports"][0], id="NEW_REPORT", event_id="NEW_EVENT"))
        result = evaluate(p)
        self.assertEqual(result["diagnostics"]["unique_events"], 7)
        self.assertEqual(item(result)["independent_events"], 5)
        self.assertEqual(item(result)["concept_events"], 5)

    def test_zero_one_reports_have_no_rarity_bonus(self):
        for n in [0, 1]:
            with self.subTest(reports=n):
                p = payload()
                p["reports"] = p["reports"][:n]
                result = evaluate(p)
                self.assertTrue(all(i["rarity_bonus"] == 0 for i in result["items"]))
                self.assertEqual(result["diagnostics"]["unique_events"], n)
                self.assertEqual(len(result["items"]), 3)
                self.assertIn("C", result["modes"]["full_control"]["selected_ids"])

    def test_mandatory_lane_is_outside_budget(self):
        p = payload()
        p["claims"].append(claim("D", "mandatory missing observation", mandatory=True))
        result = evaluate(p)
        for mode in result["modes"].values():
            self.assertEqual(mode["mandatory_ids"], ["C", "D"])
            self.assertEqual(len(mode["review_ids"]), 1)
            self.assertEqual(len(mode["selected_ids"]), 3)
        for c in p["claims"]:
            c["mandatory"] = True
        for mode in evaluate(p)["modes"].values():
            self.assertEqual(mode["selected_ids"], ["A", "B", "C", "D"])
            self.assertEqual(mode["review_ids"], [])

    def test_shared_concept_without_own_observations_has_base_only(self):
        p = payload()
        p["claims"][1]["concept"] = "routine"
        p["reports"] = [r for r in p["reports"] if r["claim_id"] != "B"]
        result = item(evaluate(p), "B")
        self.assertEqual(result["concept_events"], 4)
        self.assertEqual(result["independent_events"], 0)
        self.assertEqual(result["base_score"], 80)
        self.assertEqual(result["baseline_score"], 80)
        self.assertEqual(result["compensated_score"], 80)
        self.assertEqual(result["rarity_bonus"], 0)
        self.assertIn("NO_REPORT_OBSERVATIONS", result["reasons"])

    def test_rarity_thresholds_and_cap(self):
        for field in ["quality", "relevance"]:
            for value, expected in [(49, 0), (50, 12)]:
                with self.subTest(field=field, value=value):
                    p = payload()
                    p["claims"][1][field] = value
                    self.assertEqual(item(evaluate(p), "B")["rarity_bonus"], expected)
        for cap in [0, 30]:
            p = payload()
            p["policy"]["rarity_cap"] = cap
            result = evaluate(p)
            self.assertEqual(item(result, "B")["rarity_bonus"], cap)
            self.assertTrue(all(0 <= i["rarity_bonus"] <= cap for i in result["items"]))

    def test_aliases_group_canonical_events(self):
        p = payload()
        p["aliases"] = {"  Routine Exception  ": "routine"}
        p["claims"][1]["concept"] = "ROUTINE   EXCEPTION"
        result = evaluate(p)
        self.assertEqual(item(result, "B")["canonical_concept"], "routine")
        self.assertEqual(item(result, "B")["concept_events"], 5)
        self.assertEqual(item(result)["concept_events"], 5)
        self.assertEqual(item(result, "B")["rarity_bonus"], 2)

    def test_tie_order_and_input_permutation(self):
        p = payload()
        p["review_budget"] = 5
        p["reports"] = []
        p["claims"] = [claim("z", "z"), claim("a", "a"), claim("Z", "Z")]
        first = evaluate(p)
        self.assertEqual(first["modes"]["compensated"]["review_ids"], ["Z", "a", "z"])
        p["claims"].reverse()
        self.assertEqual(first, evaluate(p))
        # Keep base score tied at 80 while increasing consequence from 80 to 100.
        p["claims"][2].update(relevance=60, consequence=100, quality=90)
        self.assertEqual(item(evaluate(p), "z")["base_score"], 80)
        self.assertEqual(evaluate(p)["modes"]["compensated"]["review_ids"][0], "z")

    def test_evidence_origins_not_rows_define_independence(self):
        p = payload()
        p["claims"][0]["evidence"][1]["origin_id"] = "S_A_1"
        result = item(evaluate(p))["gate"]
        self.assertEqual(result["independent_support_origins"], ["S_A_1"])
        self.assertIn("INSUFFICIENT_INDEPENDENT_SUPPORT", result["reasons"])
        p["claims"][0]["evidence"].append(dict(p["claims"][0]["evidence"][0], id="COPY_E"))
        self.assertEqual(result, item(evaluate(p))["gate"])

    def test_support_exclusion_and_reason_precedence(self):
        scenarios = [
            ({"claim_version": 2, "observed_at": "2026-09-21T12:00:00Z", "support_assessed": False}, "VERSION_MISMATCH"),
            ({"observed_at": "2026-09-21T12:00:00Z", "support_assessed": False}, "FUTURE_EVIDENCE"),
            ({"observed_at": "2026-08-01T12:00:00Z", "support_assessed": False}, "STALE_EVIDENCE"),
            ({"support_assessed": False}, "UNASSESSED_SUPPORT"),
        ]
        for changes, reason in scenarios:
            with self.subTest(reason=reason):
                p = payload()
                for e in p["claims"][0]["evidence"]:
                    e.update(changes)
                gate = item(evaluate(p))["gate"]
                self.assertEqual(gate["status"], "HOLD")
                self.assertEqual(gate["independent_support_origins"], [])
                self.assertEqual(gate["excluded_evidence"], [
                    {"id": "E_A_1", "reason": reason}, {"id": "E_A_2", "reason": reason}])

    def test_evidence_age_boundary_is_inclusive(self):
        p = payload()
        for e in p["claims"][0]["evidence"]:
            e["observed_at"] = "2026-08-21T12:00:00Z"
        self.assertEqual(item(evaluate(p))["gate"]["status"], "ELIGIBLE")
        p["claims"][0]["evidence"][0]["observed_at"] = "2026-08-21T11:59:59Z"
        gate = item(evaluate(p))["gate"]
        self.assertEqual(gate["status"], "HOLD")
        self.assertEqual(gate["excluded_evidence"], [{"id": "E_A_1", "reason": "STALE_EVIDENCE"}])

    def test_contradictions_block_even_if_unassessed(self):
        for assessed in [False, True]:
            p = payload()
            p["claims"][0]["evidence"].append(evidence("A", 3, stance="contradicts", support_assessed=assessed))
            result = item(evaluate(p))
            self.assertEqual(result["gate"]["status"], "HOLD")
            self.assertIn("CONTRADICTION", result["gate"]["reasons"])
            self.assertEqual(result["gate"]["excluded_evidence"], [])
            if not assessed:
                self.assertIn("UNASSESSED_CONTRADICTION", result["reasons"])
        p = payload()
        p["claims"][0]["contradiction"] = True
        self.assertIn("CONTRADICTION", item(evaluate(p))["gate"]["reasons"])
        p = payload()
        p["claims"][0]["evidence"].append(evidence("A", 3, stance="contradicts", observed_at="2026-08-01T00:00:00Z"))
        self.assertEqual(item(evaluate(p))["gate"]["status"], "ELIGIBLE")

    def test_review_and_authority_bind_versions_roles_use_and_expiry(self):
        cases = [
            ("review", "role", "other", "REVIEW_ROLE"),
            ("review", "decision", "rejected", "REVIEW_REJECTED"),
            ("review", "expires_at", AS_OF, "REVIEW_EXPIRED"),
            ("review", "claim_version", 2, "REVIEW_VERSION"),
            ("review", "policy_version", 2, "REVIEW_VERSION"),
            ("authority", "role", "other", "AUTHORITY_ROLE"),
            ("authority", "intended_use", "other", "AUTHORITY_USE"),
            ("authority", "revoked", True, "AUTHORITY_REVOKED"),
            ("authority", "expires_at", AS_OF, "AUTHORITY_EXPIRED"),
            ("authority", "claim_version", 2, "AUTHORITY_VERSION"),
            ("authority", "policy_version", 2, "AUTHORITY_VERSION"),
        ]
        for component, field, value, expected in cases:
            with self.subTest(component=component, field=field):
                p = payload()
                p["claims"][0][component][field] = value
                gate = item(evaluate(p))["gate"]
                self.assertEqual(gate["status"], "HOLD")
                self.assertEqual(gate["reasons"], [expected])
        for component, expected in [("review", "MISSING_REVIEW"), ("authority", "MISSING_AUTHORITY")]:
            p = payload()
            p["claims"][0][component] = None
            self.assertEqual(item(evaluate(p))["gate"]["reasons"], [expected])

    def test_policy_floor_cannot_be_removed_by_claim(self):
        p = payload()
        p["policy"]["required_evidence_types"].append("record")
        gate = item(evaluate(p))["gate"]
        self.assertEqual(gate["missing_evidence_types"], ["record"])
        self.assertIn("MISSING_EVIDENCE_TYPES", gate["reasons"])
        p["claims"][0]["evidence"].append(evidence("A", 3, kind="record", stance="neutral"))
        self.assertEqual(item(evaluate(p))["gate"]["missing_evidence_types"], ["record"])
        p["claims"][0]["evidence"][-1]["stance"] = "supports"
        self.assertEqual(item(evaluate(p))["gate"]["status"], "ELIGIBLE")
        p["claims"][0]["required_evidence_types"] = ["inspection"]
        self.assertEqual(item(evaluate(p))["gate"]["missing_evidence_types"], ["inspection"])

    def test_simulation_is_separate_from_attention_and_labels(self):
        p = payload()
        p["claims"][1]["evidence"] = []
        before = evaluate(p)
        self.assertEqual(item(before, "B")["gate"]["status"], "HOLD")
        self.assertIn("B", before["modes"]["full_control"]["selected_ids"])
        self.assertEqual(before["modes"]["compensated"]["selected_ids"], before["modes"]["full_control"]["selected_ids"])
        self.assertFalse(before["modes"]["baseline"]["gate_applied"])
        self.assertFalse(before["modes"]["compensated"]["gate_applied"])
        self.assertTrue(before["modes"]["full_control"]["gate_applied"])
        self.assertTrue(all(i["gate"]["simulated"] is True for i in before["items"]))
        p["labels"] = {"B": {"truth": True, "priority": 1000000000}, "A": False}
        self.assertEqual(before, evaluate(p))

    def test_evaluation_does_not_mutate_input(self):
        p = payload()
        snapshot = deepcopy(p)
        evaluate(p)
        self.assertEqual(snapshot, p)

    def test_shared_valid_scenarios(self):
        for name, p in valid_scenarios():
            with self.subTest(name=name):
                self.assertIsInstance(evaluate(p), dict)

    def test_shared_invalid_scenarios(self):
        for name, p in invalid_scenarios():
            with self.subTest(name=name):
                with self.assertRaises(ValidationError):
                    evaluate(p)

    def test_nonfinite_numbers_and_wrong_top_level_rejected(self):
        for value in [math.nan, math.inf, -math.inf]:
            p = payload()
            p["claims"][0]["quality"] = value
            with self.assertRaises(ValidationError):
                evaluate(p)
        for value in [None, True, [], "payload", 1]:
            with self.assertRaises(ValidationError):
                evaluate(value)


if __name__ == "__main__":
    unittest.main()
