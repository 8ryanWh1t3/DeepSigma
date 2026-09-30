import unittest

from vinculum import (
    AuthorityGrant,
    AuthorityStatus,
    BoundedState,
    Constraint,
    EvidenceRecord,
    EvidenceStatus,
    GovernanceContext,
    GovernancePolicy,
    GovernanceStatus,
    Hypothesis,
    ProvenanceRecord,
    ProvenanceStatus,
    VinculumEngine,
)
from vinculum.exceptions import EvidenceIntegrityError
from vinculum.receipts import sha256_receipt


class GovernanceTests(unittest.TestCase):
    def governed_fixture(self):
        evidence = EvidenceRecord.from_payload(
            id="E-H1",
            kind="OBSERVATION",
            source="sensor-A",
            payload={"distance_ft": 90, "quality": "verified"},
        )
        source_prov = ProvenanceRecord.from_payload(
            id="PROV-SOURCE",
            kind="SOURCE",
            source="sensor-A",
            payload={"sensor": "A", "calibration": "2026-Q3"},
            version="1",
        )
        hypothesis_prov = ProvenanceRecord.from_payload(
            id="PROV-H1",
            kind="MODEL_RUN",
            source="fusion-runtime",
            payload={"run": "R-17", "model": "M-2"},
            version="17",
            parent_ids=("PROV-SOURCE",),
        )
        policy_prov = ProvenanceRecord.from_payload(
            id="PROV-POLICY",
            kind="POLICY",
            source="policy-repository",
            payload={"clause": "minimum distance >= 82ft"},
            version="4",
        )
        authority_prov = ProvenanceRecord.from_payload(
            id="PROV-AUTH",
            kind="SOURCE",
            source="authority-ledger",
            payload={"principal": "P-1", "role": "PolicyOwner"},
            version="12",
        )
        authority = AuthorityGrant(
            id="AUTH-1",
            principal_id="P-1",
            role="PolicyOwner",
            actions=("DEFINE_CONSTRAINT",),
            scopes=("policy:cuas:*",),
            provenance_ref="PROV-AUTH",
        )
        context = GovernanceContext(
            context_id="CTX-1",
            evidence=(evidence,),
            provenance=(source_prov, hypothesis_prov, policy_prov, authority_prov),
            authorities=(authority,),
        )
        h = Hypothesis(
            id="H1",
            statement="Object meets the standoff requirement.",
            probability=0.83,
            payload={"distance": {"value": 90, "unit": "ft"}},
            evidence_refs=("E-H1",),
            provenance_ref="PROV-H1",
        )
        d = Constraint(
            id="D1",
            field="distance",
            op="gte",
            expected={"value": 82, "unit": "ft"},
            hard=True,
            provenance_ref="PROV-POLICY",
            authority_ref="AUTH-1",
            authority_scope="policy:cuas:standoff",
        )
        return h, d, context

    def test_strict_valid_context_accepts(self):
        h, d, context = self.governed_fixture()
        report = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        )
        result = report.results[0]
        self.assertEqual(result.state, BoundedState.ACCEPTED)
        self.assertEqual(result.governance_status, GovernanceStatus.PASS)
        self.assertEqual(result.governance_coverage, 1.0)
        self.assertIsNotNone(report.governance_context_sha256)

    def test_strict_missing_hypothesis_evidence_is_unresolved(self):
        h, d, context = self.governed_fixture()
        h = Hypothesis(
            id=h.id,
            statement=h.statement,
            probability=h.probability,
            payload=h.payload,
            provenance_ref=h.provenance_ref,
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.UNRESOLVED)
        self.assertEqual(result.governance_status, GovernanceStatus.UNKNOWN)

    def test_strict_missing_hypothesis_provenance_is_unresolved(self):
        h, d, context = self.governed_fixture()
        h = Hypothesis(
            id=h.id,
            statement=h.statement,
            probability=h.probability,
            payload=h.payload,
            evidence_refs=h.evidence_refs,
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.UNRESOLVED)

    def test_strict_missing_constraint_authority_is_unresolved(self):
        h, d, context = self.governed_fixture()
        d = Constraint(
            id=d.id, field=d.field, op=d.op, expected=d.expected,
            provenance_ref=d.provenance_ref,
            authority_scope=d.authority_scope,
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.UNRESOLVED)

    def test_revoked_authority_rejects(self):
        h, d, context = self.governed_fixture()
        revoked = AuthorityGrant(
            id="AUTH-1",
            principal_id="P-1",
            role="PolicyOwner",
            actions=("DEFINE_CONSTRAINT",),
            scopes=("policy:cuas:*",),
            status=AuthorityStatus.REVOKED,
            provenance_ref="PROV-AUTH",
        )
        context = GovernanceContext(
            evidence=context.evidence,
            provenance=context.provenance,
            authorities=(revoked,),
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.REJECTED)
        self.assertEqual(result.governance_status, GovernanceStatus.FAIL)

    def test_authority_scope_mismatch_rejects(self):
        h, d, context = self.governed_fixture()
        d = Constraint(
            id=d.id, field=d.field, op=d.op, expected=d.expected,
            provenance_ref=d.provenance_ref,
            authority_ref=d.authority_ref,
            authority_scope="policy:aviation:standoff",
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.REJECTED)

    def test_authority_action_mismatch_rejects(self):
        h, d, context = self.governed_fixture()
        d = Constraint(
            id=d.id, field=d.field, op=d.op, expected=d.expected,
            provenance_ref=d.provenance_ref,
            authority_ref=d.authority_ref,
            authority_scope=d.authority_scope,
            authority_action="APPROVE_OPERATION",
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.REJECTED)

    def test_missing_provenance_parent_rejects(self):
        h, d, context = self.governed_fixture()
        broken = ProvenanceRecord.from_payload(
            id="PROV-H1",
            kind="MODEL_RUN",
            source="fusion-runtime",
            payload={"run": "R-17"},
            parent_ids=("MISSING-PARENT",),
        )
        provenance = tuple(p for p in context.provenance if p.id != "PROV-H1") + (broken,)
        context = GovernanceContext(
            evidence=context.evidence,
            provenance=provenance,
            authorities=context.authorities,
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.REJECTED)
        self.assertEqual(result.governance_status, GovernanceStatus.FAIL)

    def test_superseded_provenance_rejects(self):
        h, d, context = self.governed_fixture()
        old = ProvenanceRecord.from_payload(
            id="PROV-POLICY",
            kind="POLICY",
            source="policy-repository",
            payload={"clause": "old"},
            status=ProvenanceStatus.SUPERSEDED,
        )
        provenance = tuple(p for p in context.provenance if p.id != "PROV-POLICY") + (old,)
        context = GovernanceContext(
            evidence=context.evidence,
            provenance=provenance,
            authorities=context.authorities,
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.REJECTED)

    def test_withdrawn_evidence_rejects(self):
        h, d, context = self.governed_fixture()
        ev = EvidenceRecord(
            id="E-H1",
            kind="OBSERVATION",
            source="sensor-A",
            sha256=sha256_receipt({"distance_ft": 90}),
            status=EvidenceStatus.WITHDRAWN,
        )
        context = GovernanceContext(
            evidence=(ev,),
            provenance=context.provenance,
            authorities=context.authorities,
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.REJECTED)

    def test_missing_evidence_record_is_unresolved(self):
        h, d, context = self.governed_fixture()
        context = GovernanceContext(
            evidence=(),
            provenance=context.provenance,
            authorities=context.authorities,
        )
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=context
        ).results[0]
        self.assertEqual(result.state, BoundedState.UNRESOLVED)

    def test_require_materialized_evidence_is_unresolved_for_digest_only(self):
        h, d, context = self.governed_fixture()
        ev0 = context.evidence[0]
        digest_only = EvidenceRecord(
            id=ev0.id,
            kind=ev0.kind,
            source=ev0.source,
            sha256=ev0.sha256,
        )
        context = GovernanceContext(
            evidence=(digest_only,),
            provenance=context.provenance,
            authorities=context.authorities,
        )
        policy = GovernancePolicy(
            **{**GovernancePolicy.strict().to_dict(), "require_materialized_evidence": True}
        )
        result = VinculumEngine(governance_policy=policy).bind([h], [d], context=context).results[0]
        self.assertEqual(result.state, BoundedState.UNRESOLVED)


    def test_materialized_evidence_mutation_is_rejected(self):
        payload = {"distance_ft": 90}
        ev = EvidenceRecord.from_payload(
            id="E-MUT", kind="OBSERVATION", source="sensor", payload=payload
        )
        payload["distance_ft"] = 10
        prov_h = ProvenanceRecord.from_payload(
            id="PH", kind="MODEL_RUN", source="runtime", payload={"run": 1}
        )
        prov_p = ProvenanceRecord.from_payload(
            id="PP", kind="POLICY", source="repo", payload={"rule": "x>=5"}
        )
        prov_a = ProvenanceRecord.from_payload(
            id="PA", kind="SOURCE", source="auth", payload={"grant": 1}
        )
        auth = AuthorityGrant(
            id="A", principal_id="P", role="Owner",
            actions=("DEFINE_CONSTRAINT",), scopes=("*",), provenance_ref="PA"
        )
        ctx = GovernanceContext(
            evidence=(ev,), provenance=(prov_h, prov_p, prov_a), authorities=(auth,)
        )
        h = Hypothesis(
            "H", "claim", 0.8, {"x": 10}, evidence_refs=("E-MUT",), provenance_ref="PH"
        )
        d = Constraint(
            "D", "x", "gte", 5, provenance_ref="PP", authority_ref="A"
        )
        r = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
            [h], [d], context=ctx
        ).results[0]
        self.assertEqual(r.state, BoundedState.REJECTED)

    def test_evidence_digest_mismatch_raises(self):
        with self.assertRaises(EvidenceIntegrityError):
            EvidenceRecord(
                id="E",
                kind="DOCUMENT",
                source="repo",
                payload={"a": 1},
                sha256="0" * 64,
            )

    def test_context_receipt_is_deterministic(self):
        _, _, context = self.governed_fixture()
        a = context.sha256()
        b = GovernanceContext(
            context_id=context.context_id,
            evidence=reversed(context.evidence),
            provenance=reversed(context.provenance),
            authorities=reversed(context.authorities),
        ).sha256()
        self.assertEqual(a, b)

    def test_context_change_changes_report_receipt(self):
        h, d, context = self.governed_fixture()
        engine = VinculumEngine(governance_policy=GovernancePolicy.strict())
        a = engine.bind([h], [d], context=context).sha256()
        evidence2 = EvidenceRecord.from_payload(
            id="E-H1",
            kind="OBSERVATION",
            source="sensor-A",
            payload={"distance_ft": 91, "quality": "verified"},
        )
        context2 = GovernanceContext(
            context_id=context.context_id,
            evidence=(evidence2,),
            provenance=context.provenance,
            authorities=context.authorities,
        )
        b = engine.bind([h], [d], context=context2).sha256()
        self.assertNotEqual(a, b)

    def test_compatibility_mode_preserves_v01_behavior(self):
        h = Hypothesis("H", "legacy", 0.7, {"x": 10})
        d = Constraint("D", "x", "gte", 5)
        result = VinculumEngine().bind([h], [d]).results[0]
        self.assertEqual(result.state, BoundedState.ACCEPTED)
        self.assertEqual(result.governance_status, GovernanceStatus.PASS)

    def test_strict_without_context_is_unresolved(self):
        h = Hypothesis("H", "strict", 0.7, {"x": 10})
        d = Constraint("D", "x", "gte", 5)
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind([h], [d]).results[0]
        self.assertEqual(result.state, BoundedState.UNRESOLVED)

    def test_hard_fail_still_rejects_when_governance_unknown(self):
        h = Hypothesis("H", "bad", 0.99, {"x": 1})
        d = Constraint("D", "x", "gte", 5)
        result = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind([h], [d]).results[0]
        self.assertEqual(result.state, BoundedState.REJECTED)


if __name__ == "__main__":
    unittest.main()
