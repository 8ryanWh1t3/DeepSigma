"""VINCULUM v0.4 authoritative COMPOSER -> VINCULUM -> CERPA reference flow.

The private key below exists only to make the example runnable. Production should sign
CommitIntent.signing_bytes() through an HSM/KMS/offline root service and return only the
base64 signature to the commit service.
"""

from __future__ import annotations

import base64
import tempfile

from vinculum import (
    AuthorityGrant,
    AuthoritativeBootstrapService,
    AuthoritativeGovernanceRuntime,
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
    VinculumEngine,
    generate_root_keypair,
)


root_private, root_public = generate_root_keypair()
root = RootTrustAnchor.from_public_key(
    deployment_id="DEEP-SIGMA-DEMO",
    key_id="ROOT-2026-A",
    public_key=root_public,
)

# COMPOSER-authoritative governance objects.
evidence = EvidenceRecord.from_payload(
    id="E-OBS-1",
    kind="OBSERVATION",
    source="sensor-A",
    payload={"distance_ft": 90},
)
hypothesis_provenance = ProvenanceRecord.from_payload(
    id="PROV-H-1",
    kind="MODEL_RUN",
    source="resonator://run/17",
    payload={"run": 17},
)
policy_provenance = ProvenanceRecord.from_payload(
    id="PROV-POLICY-1",
    kind="POLICY",
    source="composer://clause/CUAS-STANDOFF",
    payload={"constraint": "distance >= 82ft"},
)
authority_provenance = ProvenanceRecord.from_payload(
    id="PROV-AUTH-1",
    kind="SOURCE",
    source="composer://authority/AUTH-1",
    payload={"principal": "P-1", "role": "PolicyOwner"},
)
authority = AuthorityGrant(
    id="AUTH-1",
    principal_id="P-1",
    role="PolicyOwner",
    actions=("DEFINE_CONSTRAINT",),
    scopes=("policy:cuas:*",),
    provenance_ref="PROV-AUTH-1",
)
context = GovernanceContext(
    context_id="CTX-CUAS-1",
    evidence=(evidence,),
    provenance=(hypothesis_provenance, policy_provenance, authority_provenance),
    authorities=(authority,),
    metadata={"origin": "COMPOSER"},
)

hypothesis = Hypothesis(
    id="H-1",
    statement="Observed system satisfies standoff constraint",
    probability=0.83,
    payload={"distance": {"value": 90, "unit": "ft"}},
    evidence_refs=("E-OBS-1",),
    provenance_ref="PROV-H-1",
)
constraint = Constraint(
    id="D-1",
    field="distance",
    op="gte",
    expected={"value": 82, "unit": "ft"},
    hard=True,
    provenance_ref="PROV-POLICY-1",
    authority_ref="AUTH-1",
    authority_scope="policy:cuas:standoff",
)

with tempfile.TemporaryDirectory() as state_dir:
    store = FileAuthoritativeStateStore(
        state_dir,
        integrity_key=b"demo-integrity-key-not-for-prod!!"[:32],
    )

    # One-time deployment bootstrap.
    bootstrap = AuthoritativeBootstrapService(root=root, store=store)
    intent = bootstrap.prepare_genesis(
        change=ComposerChange(
            change_id="CHG-1",
            artifact_id="POLICY-CUAS",
            revision="1",
            actor_id="P-1",
            reason="initial governed publication",
        ),
        context=context,
        issued_at="2026-09-30T18:00:00-04:00",
    )

    # DEMO signer only. Production signs intent.signing_bytes() outside the app.
    signature = base64.b64encode(root_private.sign(intent.signing_bytes())).decode("ascii")
    bootstrap.commit_genesis(
        intent=intent,
        signature_b64=signature,
        committed_at="2026-09-30T18:00:01-04:00",
    )

    # Normal runtime is read-only over the authoritative repository.
    runtime = AuthoritativeGovernanceRuntime(root=root, store=store)
    binding = VinculumEngine(
        governance_policy=GovernancePolicy.authoritative()
    ).bind_authoritative([hypothesis], [constraint], runtime=runtime)

    # VINCULUM does not APPLY. It emits a freshness-bound CERPA review envelope.
    bridge = CerpaBridge()
    handoff = bridge.prepare_review(
        binding=binding,
        runtime=runtime,
        episode_id="CERPA-EP-1",
        claim_id="CLAIM-CUAS-1",
        created_at="2026-09-30T18:00:02-04:00",
    )

    # CERPA should call this immediately before its own APPLY operation.
    guarded = bridge.validate_apply_guard(
        handoff=handoff,
        binding=binding,
        runtime=runtime,
    )

    print(binding.to_dict())
    print(guarded.to_dict())
