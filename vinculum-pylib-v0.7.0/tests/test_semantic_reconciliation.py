import unittest

from vinculum import (
    MeaningRegistry,
    MeaningRule,
    ObjectType,
    ReconciliationStatus,
    VinculumEngine,
    ingest_mapping,
    ingest_text,
    ingest_ttl,
)


class SemanticReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.e = VinculumEngine()

    def test_bakers_dozen_resolves_once_to_13(self):
        obj = ingest_text("The order is a baker's dozen.", object_id="claim", decompose=False)
        r = self.e.score(obj)
        facts = r.reconciliation["semantic_facts"]
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["value"], 13.0)
        self.assertEqual(facts[0]["concept_key"], "SEM_BAKERS_DOZEN")

    def test_bakers_dozen_receipt_12_is_conflict(self):
        ep = {
            "claims": ["The order is a baker's dozen."],
            "receipt": {"item": "Baker's Dozen Cookies", "quantity": 12},
        }
        r = self.e.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="EP-BD12"))
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.CONFLICT.value)
        self.assertEqual(r.semantic_record_tension, 1.0)
        self.assertEqual(len(r.reconciliation["comparisons"]), 1)
        c = r.reconciliation["comparisons"][0]
        self.assertEqual(c["semantic_value"], 13.0)
        self.assertEqual(c["record_value"], 12.0)
        self.assertEqual(c["delta"], -1.0)
        self.assertEqual(c["status"], "CONFLICT")

    def test_bakers_dozen_receipt_13_is_aligned(self):
        ep = {
            "claims": ["The order is a baker's dozen."],
            "receipt": {"item": "Baker's Dozen Cookies", "quantity": 13},
        }
        r = self.e.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="EP-BD13"))
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.ALIGNED.value)
        self.assertEqual(r.semantic_record_tension, 0.0)
        self.assertEqual(r.reconciliation["comparisons"][0]["status"], "MATCH")

    def test_plain_dozen_resolves_to_12(self):
        ep = {"claims": ["Ship a dozen."], "receipt": {"quantity": 12}}
        r = self.e.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="EP-D12"))
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.ALIGNED.value)
        self.assertEqual(r.reconciliation["comparisons"][0]["semantic_value"], 12.0)

    def test_half_dozen_resolves_to_6(self):
        ep = {"claims": ["Ship a half-dozen."], "receipt": {"quantity": 6}}
        r = self.e.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="EP-HD6"))
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.ALIGNED.value)
        self.assertEqual(r.reconciliation["comparisons"][0]["semantic_value"], 6.0)

    def test_receipt_text_is_compared(self):
        text = "Baker's Dozen Cookies    Qty 12\nSubtotal 12.00"
        r = self.e.score(ingest_text(text, object_type=ObjectType.DOCUMENT, object_id="receipt", decompose=False))
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.CONFLICT.value)
        self.assertEqual(r.semantic_record_tension, 1.0)

    def test_ttl_semantic_literal_vs_numeric_quantity(self):
        ttl = '''
        @prefix ex: <https://example.org/> .
        ex:order ex:label "baker's dozen" ; ex:quantity 12 .
        '''
        r = self.e.score(ingest_ttl(ttl, object_id="g"))
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.CONFLICT.value)
        self.assertEqual(r.semantic_record_tension, 0.70)  # conservative singleton cross-node alignment
        self.assertEqual(r.reconciliation["comparisons"][0]["record_value"], 12.0)

    def test_no_record_is_unresolved_not_conflict(self):
        r = self.e.score(ingest_text("The order is a baker's dozen.", object_id="claim", decompose=False))
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.UNRESOLVED.value)
        self.assertEqual(r.semantic_record_tension, 0.0)

    def test_no_semantic_fact_is_unresolved_when_record_present(self):
        obj = ingest_mapping({"receipt": {"item": "Cookies", "quantity": 12}}, object_type=ObjectType.EPISODE, object_id="R")
        r = self.e.score(obj)
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.UNRESOLVED.value)
        self.assertEqual(r.semantic_record_tension, 0.0)

    def test_ambiguous_multiple_records_do_not_blind_pair(self):
        ep = {
            "claims": ["The order is a baker's dozen."],
            "records": [
                {"item": "Cookies", "quantity": 12},
                {"item": "Bagels", "quantity": 13},
            ],
        }
        r = self.e.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="AMB"))
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.UNRESOLVED.value)
        self.assertEqual(len(r.reconciliation["comparisons"]), 0)

    def test_custom_registry_rule(self):
        trio = MeaningRule.compile(
            id="SEM_TRIO",
            label="trio",
            pattern=r"\ba\s+trio\b",
            dimension="count",
            operator="eq",
            value=3,
            unit="count",
            confidence=1.0,
            priority=5,
        )
        registry = MeaningRegistry.default().with_rule(trio)
        engine = VinculumEngine(meaning_registry=registry)
        ep = {"claims": ["The kit contains a trio."], "receipt": {"quantity": 4}}
        r = engine.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="TRIO"))
        self.assertEqual(r.reconciliation_status, ReconciliationStatus.CONFLICT.value)
        self.assertEqual(r.reconciliation["comparisons"][0]["semantic_value"], 3.0)
        self.assertEqual(r.reconciliation["comparisons"][0]["record_value"], 4.0)

    def test_semantic_resolution_adds_d_driver(self):
        r = self.e.score(ingest_text("A baker's dozen.", object_id="x", decompose=False))
        ids = {s.id for s in r.drivers_d}
        self.assertIn("D_SEMANTIC_RESOLUTION", ids)
        self.assertGreaterEqual(r.deterministic_strength, 0.8)

    def test_record_defense_adds_d_driver(self):
        r = self.e.score(ingest_mapping({"receipt": {"quantity": 12}}, object_type=ObjectType.EPISODE, object_id="x"))
        ids = {s.id for s in r.drivers_d}
        self.assertIn("D_RECORD_CONSTRAINT", ids)
        self.assertGreaterEqual(r.deterministic_strength, 0.95)

    def test_conflict_adjusted_usable_value_collapses_on_exact_full_conflict(self):
        ep = {"claims": ["The order is a baker's dozen."], "receipt": {"item": "Baker's Dozen Cookies", "quantity": 12}}
        r = self.e.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="U-CONFLICT"))
        self.assertEqual(r.semantic_record_tension, 1.0)
        self.assertEqual(r.comparison_coverage, 1.0)
        self.assertAlmostEqual(r.reconciled_usable_value, 0.0)

    def test_aligned_record_preserves_usable_value(self):
        ep = {"claims": ["The order is a baker's dozen."], "receipt": {"item": "Baker's Dozen Cookies", "quantity": 13}}
        r = self.e.score(ingest_mapping(ep, object_type=ObjectType.EPISODE, object_id="U-ALIGN"))
        self.assertEqual(r.semantic_record_tension, 0.0)
        self.assertAlmostEqual(r.reconciled_usable_value, r.usable_value)


if __name__ == "__main__":
    unittest.main()
