import base64
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from vinculum import (
    AuthorityGrant,
    AuthoritativeBootstrapService,
    AuthoritativeCommitService,
    AuthoritativeGovernanceRuntime,
    AuthoritativeState,
    BoundedState,
    CerpaBridge,
    ComposerChange,
    Constraint,
    EvidenceRecord,
    FileAuthoritativeStateStore,
    GovernanceContext,
    GovernancePolicy,
    Hypothesis,
    ProvenanceRecord,
    RootTrustAnchor,
    TrustError,
    VinculumEngine,
    generate_root_keypair,
)


class AuthoritativeChokePointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.private, public = generate_root_keypair()
        self.root = RootTrustAnchor.from_public_key(
            deployment_id="DEPLOY-VINCULUM-04",
            key_id="ROOT-COMPOSER-01",
            public_key=public,
        )
        self.store = FileAuthoritativeStateStore(
            self.tmp.name,
            integrity_key=b"authoritative-integrity-key-0001"[:32],
        )

    def tearDown(self):
        self.tmp.cleanup()

    def context(self, suffix="1", min_ft=82):
        evidence = EvidenceRecord.from_payload(
            id=f"E-{suffix}", kind="OBSERVATION", source="sensor-A",
            payload={"distance_ft": 90},
        )
        hp = ProvenanceRecord.from_payload(
            id=f"PROV-H-{suffix}", kind="MODEL_RUN", source="fusion-runtime",
            payload={"run": f"R-{suffix}"},
        )
        pp = ProvenanceRecord.from_payload(
            id=f"PROV-POL-{suffix}", kind="POLICY", source="composer://policy/cu",
            payload={"clause": f"distance >= {min_ft}ft"},
        )
        ap = ProvenanceRecord.from_payload(
            id=f"PROV-AUTH-{suffix}", kind="SOURCE", source="composer://authority-ledger",
            payload={"principal": "P-1", "role": "PolicyOwner"},
        )
        authority = AuthorityGrant(
            id=f"AUTH-{suffix}", principal_id="P-1", role="PolicyOwner",
            actions=("DEFINE_CONSTRAINT",), scopes=("policy:cuas:*",),
            provenance_ref=f"PROV-AUTH-{suffix}",
        )
        return GovernanceContext(
            context_id=f"CTX-{suffix}",
            evidence=(evidence,), provenance=(hp, pp, ap), authorities=(authority,),
            metadata={"origin": "COMPOSER"},
        )

    def hypothesis_constraint(self, suffix="1", min_ft=82):
        h = Hypothesis(
            id=f"H-{suffix}", statement="meets standoff", probability=0.83,
            payload={"distance": {"value": 90, "unit": "ft"}},
            evidence_refs=(f"E-{suffix}",), provenance_ref=f"PROV-H-{suffix}",
        )
        d = Constraint(
            id=f"D-{suffix}", field="distance", op="gte",
            expected={"value": min_ft, "unit": "ft"}, hard=True,
            provenance_ref=f"PROV-POL-{suffix}", authority_ref=f"AUTH-{suffix}",
            authority_scope="policy:cuas:standoff",
        )
        return h, d

    def sign(self, intent):
        return base64.b64encode(self.private.sign(intent.signing_bytes())).decode("ascii")

    def bootstrap(self):
        ctx = self.context("1")
        change = ComposerChange(
            change_id="CHG-1", artifact_id="POLICY-CUAS", revision="1",
            actor_id="P-1", reason="initial authoritative corpus",
        )
        svc = AuthoritativeBootstrapService(root=self.root, store=self.store)
        intent = svc.prepare_genesis(change=change, context=ctx, issued_at="2026-09-30T18:00:00-04:00")
        receipt = svc.commit_genesis(
            intent=intent,
            signature_b64=self.sign(intent),
            committed_at="2026-09-30T18:00:01-04:00",
        )
        return ctx, intent, receipt

    def advance(self, suffix="2", min_ft=82):
        svc = AuthoritativeCommitService(root=self.root, store=self.store)
        ctx = self.context(suffix, min_ft=min_ft)
        intent = svc.prepare(
            change=ComposerChange(
                change_id=f"CHG-{suffix}", artifact_id="POLICY-CUAS", revision=suffix,
                actor_id="P-1", reason="governed revision",
            ),
            context=ctx,
            issued_at=f"2026-09-30T18:{suffix.zfill(2)}:00-04:00",
        )
        receipt = svc.commit(
            intent=intent,
            signature_b64=self.sign(intent),
            committed_at=f"2026-09-30T18:{suffix.zfill(2)}:01-04:00",
        )
        return ctx, intent, receipt

    def test_genesis_commit_creates_authoritative_head(self):
        ctx, _, receipt = self.bootstrap()
        self.assertEqual(receipt.epoch, 1)
        self.assertEqual(receipt.producer, "COMPOSER")
        loaded = self.store.inspect(root=self.root)
        self.assertEqual(loaded.state, AuthoritativeState.READY)
        self.assertEqual(loaded.snapshot.context.sha256(), ctx.sha256())
        self.assertEqual(loaded.snapshot.commit_receipt, receipt)

    def test_runtime_is_read_only(self):
        self.bootstrap()
        runtime = AuthoritativeGovernanceRuntime(root=self.root, store=self.store)
        for forbidden in ("commit", "advance", "bootstrap", "set_root"):
            self.assertFalse(hasattr(runtime, forbidden), forbidden)
        self.assertEqual(runtime.snapshot().commit_receipt.epoch, 1)

    def test_prepare_sign_commit_advances_exact_head(self):
        self.bootstrap()
        _, intent, receipt = self.advance("2")
        self.assertEqual(receipt.epoch, 2)
        self.assertEqual(receipt.previous_commit_sha256, intent.previous_commit_sha256)
        self.assertEqual(self.store.inspect(root=self.root).snapshot.commit_receipt, receipt)

    def test_concurrent_stale_intent_rejected(self):
        self.bootstrap()
        svc = AuthoritativeCommitService(root=self.root, store=self.store)
        intent_a = svc.prepare(
            change=ComposerChange("CHG-2A", "POLICY-CUAS", "2A"),
            context=self.context("2A"),
        )
        intent_b = svc.prepare(
            change=ComposerChange("CHG-2B", "POLICY-CUAS", "2B"),
            context=self.context("2B"),
        )
        svc.commit(intent=intent_a, signature_b64=self.sign(intent_a))
        with self.assertRaisesRegex(TrustError, "STALE_COMMIT_INTENT"):
            svc.commit(intent=intent_b, signature_b64=self.sign(intent_b))

    def test_signature_must_cover_exact_prepared_intent(self):
        self.bootstrap()
        svc = AuthoritativeCommitService(root=self.root, store=self.store)
        intent = svc.prepare(
            change=ComposerChange("CHG-2", "POLICY-CUAS", "2"),
            context=self.context("2"),
        )
        other = svc.prepare(
            change=ComposerChange("CHG-2X", "POLICY-CUAS", "2X"),
            context=self.context("2X"),
        )
        with self.assertRaisesRegex(TrustError, "pinned-root verification"):
            svc.commit(intent=intent, signature_b64=self.sign(other))

    def test_deleted_head_fails_closed(self):
        self.bootstrap()
        self.store.head_path.unlink()
        loaded = self.store.inspect(root=self.root)
        self.assertEqual(loaded.state, AuthoritativeState.LOST)
        runtime = AuthoritativeGovernanceRuntime(root=self.root, store=self.store)
        with self.assertRaisesRegex(TrustError, "AUTHORITATIVE_STATE_LOST"):
            runtime.snapshot()

    def test_head_tamper_fails_closed(self):
        self.bootstrap()
        obj = json.loads(self.store.head_path.read_text())
        obj["payload"]["epoch"] = 999
        self.store.head_path.write_text(json.dumps(obj))
        loaded = self.store.inspect(root=self.root)
        self.assertEqual(loaded.state, AuthoritativeState.CORRUPT)

    def test_commit_record_tamper_fails_closed(self):
        self.bootstrap()
        head = self.store._decode(self.store.head_path.read_bytes())
        record = self.store._record_path(head["epoch"], head["commit_record_sha256"])
        obj = json.loads(record.read_text())
        obj["payload"]["change"]["revision"] = "forged"
        record.write_text(json.dumps(obj))
        loaded = self.store.inspect(root=self.root)
        self.assertEqual(loaded.state, AuthoritativeState.CORRUPT)

    def test_full_chain_verifies(self):
        self.bootstrap()
        self.advance("2")
        self.advance("3")
        chain = self.store.verify_chain(root=self.root)
        self.assertEqual([r.epoch for r in chain], [1, 2, 3])
        self.assertEqual([r.change_id for r in chain], ["CHG-1", "CHG-2", "CHG-3"])

    def test_authoritative_binding_uses_repository_context(self):
        self.bootstrap()
        runtime = AuthoritativeGovernanceRuntime(root=self.root, store=self.store)
        h, d = self.hypothesis_constraint("1")
        binding = VinculumEngine(governance_policy=GovernancePolicy.trusted()).bind_authoritative(
            [h], [d], runtime=runtime
        )
        self.assertEqual(binding.report.results[0].state, BoundedState.ACCEPTED)
        self.assertEqual(binding.commit.epoch, 1)
        self.assertEqual(binding.report.governance_context_sha256, binding.commit.context_sha256)

    def test_signed_but_uncommitted_state_cannot_drive_authoritative_binding(self):
        self.bootstrap()
        svc = AuthoritativeCommitService(root=self.root, store=self.store)
        intent = svc.prepare(
            change=ComposerChange("CHG-2", "POLICY-CUAS", "2"),
            context=self.context("2"),
        )
        # We can produce a valid root signature, but until commit() advances the store,
        # the authoritative runtime must still expose epoch 1.
        _valid_uncommitted_signature = self.sign(intent)
        runtime = AuthoritativeGovernanceRuntime(root=self.root, store=self.store)
        self.assertEqual(runtime.snapshot().commit_receipt.epoch, 1)

    def test_binding_requires_authoritative_runtime_type(self):
        h, d = self.hypothesis_constraint("1")
        with self.assertRaises(TypeError):
            VinculumEngine().bind_authoritative([h], [d], runtime=object())

    def test_cerpa_review_handoff_is_bound_to_current_state(self):
        self.bootstrap()
        runtime = AuthoritativeGovernanceRuntime(root=self.root, store=self.store)
        h, d = self.hypothesis_constraint("1")
        binding = VinculumEngine(governance_policy=GovernancePolicy.trusted()).bind_authoritative(
            [h], [d], runtime=runtime
        )
        bridge = CerpaBridge()
        handoff = bridge.prepare_review(
            binding=binding,
            runtime=runtime,
            episode_id="CERPA-EP-1",
            claim_id="CLAIM-1",
            created_at="2026-09-30T18:15:00-04:00",
        )
        self.assertEqual(handoff.phase.value, "REVIEW")
        guarded = bridge.validate_apply_guard(handoff=handoff, binding=binding, runtime=runtime)
        self.assertEqual(guarded.phase.value, "APPLY_GUARD")
        self.assertEqual(guarded.metadata["apply_guard"], "CURRENT")

    def test_cerpa_guard_rejects_state_changed_after_binding(self):
        self.bootstrap()
        runtime = AuthoritativeGovernanceRuntime(root=self.root, store=self.store)
        h, d = self.hypothesis_constraint("1")
        binding = VinculumEngine(governance_policy=GovernancePolicy.trusted()).bind_authoritative(
            [h], [d], runtime=runtime
        )
        bridge = CerpaBridge()
        handoff = bridge.prepare_review(
            binding=binding, runtime=runtime, episode_id="EP", claim_id="CLAIM"
        )
        self.advance("2")
        with self.assertRaisesRegex(TrustError, "STALE_AUTHORITATIVE_STATE"):
            bridge.validate_apply_guard(handoff=handoff, binding=binding, runtime=runtime)


    def test_runtime_requires_complete_authoritative_history(self):
        self.bootstrap()
        self.advance("2")
        head = self.store._decode(self.store.head_path.read_bytes())
        current_record = self.store._record_path(head["epoch"], head["commit_record_sha256"])
        current_payload = self.store._decode(current_record.read_bytes())
        previous_sha = current_payload["previous_commit_sha256"]
        previous_record = self.store._record_path(1, previous_sha)
        previous_record.unlink()
        runtime = AuthoritativeGovernanceRuntime(root=self.root, store=self.store)
        with self.assertRaisesRegex(TrustError, "authoritative chain record missing"):
            runtime.snapshot()


    def test_cerpa_tampered_handoff_is_rejected(self):
        self.bootstrap()
        runtime = AuthoritativeGovernanceRuntime(root=self.root, store=self.store)
        h, d = self.hypothesis_constraint("1")
        binding = VinculumEngine(governance_policy=GovernancePolicy.authoritative()).bind_authoritative(
            [h], [d], runtime=runtime
        )
        bridge = CerpaBridge()
        handoff = bridge.prepare_review(
            binding=binding, runtime=runtime, episode_id="EP", claim_id="CLAIM"
        )
        tampered = replace(handoff, result_states={"H-1": "BOUNDED_REJECTED"})
        with self.assertRaisesRegex(TrustError, "CERPA_HANDOFF_RESULT_STATES_MISMATCH"):
            bridge.validate_apply_guard(handoff=tampered, binding=binding, runtime=runtime)

    def test_crash_after_record_before_head_does_not_advance_authority(self):
        self.bootstrap()
        svc = AuthoritativeCommitService(root=self.root, store=self.store)
        intent = svc.prepare(
            change=ComposerChange("CHG-2", "POLICY-CUAS", "2"),
            context=self.context("2"),
        )
        signature = self.sign(intent)
        original_atomic = self.store._atomic_write

        def fail_head(path, data, **kwargs):
            if path == self.store.head_path:
                raise OSError("simulated HEAD write failure")
            return original_atomic(path, data, **kwargs)

        with patch.object(self.store, "_atomic_write", side_effect=fail_head):
            with self.assertRaises(OSError):
                svc.commit(intent=intent, signature_b64=signature)

        loaded = self.store.inspect(root=self.root)
        self.assertEqual(loaded.state, AuthoritativeState.READY)
        self.assertEqual(loaded.snapshot.commit_receipt.epoch, 1)
        # The epoch-2 record may exist as an orphan, but it is not authoritative because HEAD did not move.
        self.assertTrue(any(self.store.commits_dir.glob("00000000000000000002-*.json")))

    def test_bad_signature_cannot_commit_genesis(self):
        ctx = self.context("1")
        svc = AuthoritativeBootstrapService(root=self.root, store=self.store)
        intent = svc.prepare_genesis(
            change=ComposerChange("CHG-1", "POLICY-CUAS", "1"),
            context=ctx,
        )
        attacker_private, _ = generate_root_keypair()
        bad_sig = base64.b64encode(attacker_private.sign(intent.signing_bytes())).decode("ascii")
        with self.assertRaisesRegex(TrustError, "pinned-root verification"):
            svc.commit_genesis(intent=intent, signature_b64=bad_sig)
        self.assertEqual(self.store.inspect(root=self.root).state, AuthoritativeState.LOST)

    def test_normal_commit_service_cannot_create_genesis(self):
        svc = AuthoritativeCommitService(root=self.root, store=self.store)
        with self.assertRaisesRegex(TrustError, "prepare refused"):
            svc.prepare(
                change=ComposerChange("CHG-1", "POLICY-CUAS", "1"),
                context=self.context("1"),
            )


if __name__ == "__main__":
    unittest.main()
