import json
import os
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from vinculum import (
    AuthorityGrant,
    BoundedState,
    CheckpointState,
    Constraint,
    EvidenceRecord,
    FileCheckpointStore,
    GovernanceContext,
    GovernancePolicy,
    Hypothesis,
    ProvenanceRecord,
    RootTrustAnchor,
    SignedGovernanceBundle,
    TrustStatus,
    TrustedGovernanceBootstrapper,
    TrustedGovernanceRuntime,
    VinculumEngine,
    generate_root_keypair,
)
from vinculum.exceptions import TrustError


class TrustTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root_private, root_public = generate_root_keypair()
        self.root = RootTrustAnchor.from_public_key(
            deployment_id="DEPLOY-ALPHA",
            key_id="ROOT-2026-A",
            public_key=root_public,
        )
        self.integrity_key = b"checkpoint-integrity-key-32bytes!!"[:32]
        self.store = FileCheckpointStore(self.tmp.name, integrity_key=self.integrity_key)

    def tearDown(self):
        self.tmp.cleanup()

    def governed_fixture(self, *, context_id="CTX-1"):
        evidence = EvidenceRecord.from_payload(
            id="E-1", kind="OBSERVATION", source="sensor-A",
            payload={"distance_ft": 90},
        )
        hp = ProvenanceRecord.from_payload(
            id="PROV-H", kind="MODEL_RUN", source="fusion-runtime",
            payload={"run": "R-17"},
        )
        pp = ProvenanceRecord.from_payload(
            id="PROV-POLICY", kind="POLICY", source="composer://policy/cu",
            payload={"clause": "distance >= 82ft"},
        )
        ap = ProvenanceRecord.from_payload(
            id="PROV-AUTH", kind="SOURCE", source="authority-ledger",
            payload={"principal": "P-1", "role": "PolicyOwner"},
        )
        authority = AuthorityGrant(
            id="AUTH-1", principal_id="P-1", role="PolicyOwner",
            actions=("DEFINE_CONSTRAINT",), scopes=("policy:cuas:*",),
            provenance_ref="PROV-AUTH",
        )
        context = GovernanceContext(
            context_id=context_id,
            evidence=(evidence,), provenance=(hp, pp, ap), authorities=(authority,),
            metadata={"source": "composer"},
        )
        h = Hypothesis(
            id="H1", statement="meets standoff", probability=0.83,
            payload={"distance": {"value": 90, "unit": "ft"}},
            evidence_refs=("E-1",), provenance_ref="PROV-H",
        )
        d = Constraint(
            id="D1", field="distance", op="gte",
            expected={"value": 82, "unit": "ft"}, hard=True,
            provenance_ref="PROV-POLICY", authority_ref="AUTH-1",
            authority_scope="policy:cuas:standoff",
        )
        return context, h, d

    def bundle(self, context, *, epoch=1, supersedes=None, private=None, deployment=None, key_id=None):
        return SignedGovernanceBundle.sign(
            root_private_key=private or self.root_private,
            root_key_id=key_id or self.root.key_id,
            deployment_id=deployment or self.root.deployment_id,
            epoch=epoch,
            context=context,
            supersedes_hash=supersedes,
            issued_at=f"2026-09-30T17:{epoch:02d}:00-04:00",
        )

    def bootstrap(self):
        context, h, d = self.governed_fixture()
        b1 = self.bundle(context)
        receipt = TrustedGovernanceBootstrapper(root=self.root, checkpoint_store=self.store).bootstrap(b1)
        runtime = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        runtime.load_or_advance(b1)
        return context, h, d, b1, receipt, runtime

    def test_root_has_no_runtime_setter(self):
        runtime = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        self.assertFalse(hasattr(runtime, "set_root"))
        self.assertEqual(runtime.root, self.root)

    def test_normal_runtime_cannot_bootstrap_uninitialized_store(self):
        context, *_ = self.governed_fixture()
        b1 = self.bundle(context)
        runtime = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        with self.assertRaisesRegex(TrustError, "UNINITIALIZED"):
            runtime.load_or_advance(b1)

    def test_explicit_bootstrap_creates_trusted_epoch_one(self):
        context, *_ = self.governed_fixture()
        b1 = self.bundle(context)
        receipt = TrustedGovernanceBootstrapper(root=self.root, checkpoint_store=self.store).bootstrap(b1)
        self.assertEqual(receipt.status, TrustStatus.TRUSTED)
        self.assertEqual(receipt.epoch, 1)
        state = self.store.load(root=self.root)
        self.assertEqual(state.state, CheckpointState.READY)
        self.assertEqual(state.checkpoint.highest_epoch, 1)

    def test_bootstrap_refuses_non_genesis_bundle(self):
        context, *_ = self.governed_fixture()
        b2 = self.bundle(context, epoch=2, supersedes="0" * 64)
        with self.assertRaisesRegex(TrustError, "genesis"):
            TrustedGovernanceBootstrapper(root=self.root, checkpoint_store=self.store).bootstrap(b2)

    def test_valid_advance_requires_exact_epoch_and_hash_chain(self):
        context, *_ , b1, _, runtime = self.bootstrap()
        context2, *_ = self.governed_fixture(context_id="CTX-2")
        b2 = self.bundle(context2, epoch=2, supersedes=b1.sha256())
        r2 = runtime.load_or_advance(b2)
        self.assertEqual(r2.epoch, 2)
        self.assertEqual(self.store.load(root=self.root).checkpoint.current_bundle_sha256, b2.sha256())

    def test_rollback_rejected_after_restart(self):
        context, *_ , b1, _, runtime = self.bootstrap()
        context2, *_ = self.governed_fixture(context_id="CTX-2")
        b2 = self.bundle(context2, epoch=2, supersedes=b1.sha256())
        runtime.load_or_advance(b2)
        runtime2 = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        with self.assertRaisesRegex(TrustError, "ROLLBACK_REJECTED"):
            runtime2.load_or_advance(b1)

    def test_epoch_gap_rejected(self):
        context, *_ , b1, _, runtime = self.bootstrap()
        context3, *_ = self.governed_fixture(context_id="CTX-3")
        b3 = self.bundle(context3, epoch=3, supersedes=b1.sha256())
        with self.assertRaisesRegex(TrustError, "EPOCH_GAP"):
            runtime.load_or_advance(b3)

    def test_wrong_supersedes_hash_rejected(self):
        context, *_ , b1, _, runtime = self.bootstrap()
        context2, *_ = self.governed_fixture(context_id="CTX-2")
        b2 = self.bundle(context2, epoch=2, supersedes="f" * 64)
        with self.assertRaisesRegex(TrustError, "CHAIN_MISMATCH"):
            runtime.load_or_advance(b2)

    def test_current_epoch_different_bundle_rejected(self):
        context, *_ , b1, _, _ = self.bootstrap()
        other_context, *_ = self.governed_fixture(context_id="OTHER")
        alternate_b1 = self.bundle(other_context, epoch=1)
        runtime = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        with self.assertRaisesRegex(TrustError, "CURRENT_BUNDLE_MISMATCH"):
            runtime.load_or_advance(alternate_b1)

    def test_bad_root_signature_rejected(self):
        context, *_ = self.governed_fixture()
        attacker = Ed25519PrivateKey.generate()
        b1 = self.bundle(context, private=attacker)
        runtime = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        # uninitialized would otherwise fail first; signature must fail first.
        with self.assertRaisesRegex(TrustError, "SIGNATURE_INVALID"):
            runtime.load_or_advance(b1)

    def test_deployment_mismatch_rejected(self):
        context, *_ = self.governed_fixture()
        b1 = self.bundle(context, deployment="DEPLOY-BETA")
        runtime = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        with self.assertRaisesRegex(TrustError, "DEPLOYMENT_MISMATCH"):
            runtime.load_or_advance(b1)

    def test_context_tamper_rejected(self):
        context, *_ = self.governed_fixture()
        b1 = self.bundle(context)
        tampered_context = dict(b1.context)
        tampered_context["context_id"] = "TAMPERED"
        tampered = replace(b1, context=tampered_context)
        self.assertIn(tampered.verify(self.root), {TrustStatus.SIGNATURE_INVALID, TrustStatus.CONTEXT_HASH_MISMATCH})

    def test_checkpoint_hmac_tamper_fails_closed(self):
        _, *_rest = self.bootstrap()
        p = Path(self.tmp.name) / "checkpoint.vinculum.json"
        obj = json.loads(p.read_text())
        obj["payload"]["highest_epoch"] = 0
        p.write_text(json.dumps(obj))
        state = self.store.load(root=self.root)
        self.assertEqual(state.state, CheckpointState.CORRUPT)
        runtime = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        context, *_ = self.governed_fixture()
        b1 = self.bundle(context)
        with self.assertRaisesRegex(TrustError, "CHECKPOINT_CORRUPT"):
            runtime.load_or_advance(b1)

    def test_checkpoint_loss_after_initialization_fails_closed(self):
        _, *_rest = self.bootstrap()
        os.unlink(Path(self.tmp.name) / "checkpoint.vinculum.json")
        state = self.store.load(root=self.root)
        self.assertEqual(state.state, CheckpointState.LOST)
        context, *_ = self.governed_fixture()
        b1 = self.bundle(context)
        runtime = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        with self.assertRaisesRegex(TrustError, "CHECKPOINT_LOST"):
            runtime.load_or_advance(b1)

    def test_marker_loss_is_corrupt_not_fresh_genesis(self):
        _, *_rest = self.bootstrap()
        os.unlink(Path(self.tmp.name) / "deployment.vinculum.json")
        state = self.store.load(root=self.root)
        self.assertEqual(state.state, CheckpointState.CORRUPT)

    def test_wrong_integrity_key_detects_corruption(self):
        self.bootstrap()
        other = FileCheckpointStore(self.tmp.name, integrity_key=b"x" * 32)
        state = other.load(root=self.root)
        self.assertEqual(state.state, CheckpointState.CORRUPT)

    def test_trusted_engine_binds_and_embeds_trust_receipt(self):
        _, h, d, _, _, runtime = self.bootstrap()
        report = VinculumEngine(governance_policy=GovernancePolicy.trusted()).bind_trusted(
            [h], [d], runtime=runtime
        )
        self.assertEqual(report.results[0].state, BoundedState.ACCEPTED)
        self.assertEqual(report.trust["status"], "TRUSTED")
        self.assertEqual(report.trust["epoch"], 1)
        self.assertEqual(report.governance_context_sha256, report.trust["context_sha256"])


    def test_checkpoint_write_failure_does_not_advance_memory_or_disk(self):
        context, *_ , b1, _, runtime = self.bootstrap()
        context2, *_ = self.governed_fixture(context_id="CTX-2")
        b2 = self.bundle(context2, epoch=2, supersedes=b1.sha256())
        with patch.object(self.store, "_atomic_write", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(TrustError, "CHECKPOINT_WRITE_FAILED"):
                runtime.load_or_advance(b2)
        state = self.store.load(root=self.root)
        self.assertEqual(state.checkpoint.highest_epoch, 1)
        self.assertEqual(runtime.require_receipt().epoch, 1)

    def test_malformed_checkpoint_fails_closed(self):
        self.bootstrap()
        p = Path(self.tmp.name) / "checkpoint.vinculum.json"
        p.write_text("{not-json")
        state = self.store.load(root=self.root)
        self.assertEqual(state.state, CheckpointState.CORRUPT)
        runtime = TrustedGovernanceRuntime(root=self.root, checkpoint_store=self.store)
        context, *_ = self.governed_fixture()
        with self.assertRaisesRegex(TrustError, "CHECKPOINT_CORRUPT"):
            runtime.load_or_advance(self.bundle(context))

    def test_context_round_trip_preserves_governance_hash(self):
        context, *_ = self.governed_fixture()
        rebuilt = GovernanceContext.from_dict(context.to_dict(include_payload=True))
        self.assertEqual(context.sha256(), rebuilt.sha256())
        self.assertEqual(rebuilt.evidence[0].payload, {"distance_ft": 90})


if __name__ == "__main__":
    unittest.main()
