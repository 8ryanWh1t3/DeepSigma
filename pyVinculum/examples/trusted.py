"""VINCULUM v0.3 trusted-governance demonstration.

The private root and checkpoint integrity key are generated inline ONLY for a demo.
Production deployments must provision both outside application code.
"""

import tempfile

from vinculum import (
    AuthorityGrant,
    Constraint,
    EvidenceRecord,
    FileCheckpointStore,
    GovernanceContext,
    GovernancePolicy,
    Hypothesis,
    ProvenanceRecord,
    RootTrustAnchor,
    SignedGovernanceBundle,
    TrustedGovernanceBootstrapper,
    TrustedGovernanceRuntime,
    VinculumEngine,
    generate_root_keypair,
)

private_root, public_root = generate_root_keypair()
root = RootTrustAnchor.from_public_key(
    deployment_id="DEMO-DEPLOYMENT",
    key_id="ROOT-DEMO-1",
    public_key=public_root,
)

context = GovernanceContext(
    context_id="CTX-DEMO-1",
    evidence=(
        EvidenceRecord.from_payload(
            id="E-1", kind="OBSERVATION", source="sensor-A",
            payload={"distance_ft": 90},
        ),
    ),
    provenance=(
        ProvenanceRecord.from_payload(
            id="PROV-H", kind="MODEL_RUN", source="fusion-runtime",
            payload={"run": "R-17"},
        ),
        ProvenanceRecord.from_payload(
            id="PROV-POLICY", kind="POLICY", source="composer://policy/cu",
            payload={"clause": "distance >= 82ft"},
        ),
        ProvenanceRecord.from_payload(
            id="PROV-AUTH", kind="SOURCE", source="authority-ledger",
            payload={"principal": "P-1", "role": "PolicyOwner"},
        ),
    ),
    authorities=(
        AuthorityGrant(
            id="AUTH-1", principal_id="P-1", role="PolicyOwner",
            actions=("DEFINE_CONSTRAINT",), scopes=("policy:cuas:*",),
            provenance_ref="PROV-AUTH",
        ),
    ),
)

bundle = SignedGovernanceBundle.sign(
    root_private_key=private_root,
    root_key_id=root.key_id,
    deployment_id=root.deployment_id,
    epoch=1,
    context=context,
    supersedes_hash=None,
)

hypothesis = Hypothesis(
    id="H1", statement="The object meets the governed standoff requirement.",
    probability=0.83,
    payload={"distance": {"value": 90, "unit": "ft"}},
    evidence_refs=("E-1",), provenance_ref="PROV-H",
)
constraint = Constraint(
    id="D1", field="distance", op="gte",
    expected={"value": 82, "unit": "ft"}, hard=True,
    provenance_ref="PROV-POLICY", authority_ref="AUTH-1",
    authority_scope="policy:cuas:standoff",
)

with tempfile.TemporaryDirectory() as checkpoint_dir:
    store = FileCheckpointStore(checkpoint_dir, integrity_key=b"demo-checkpoint-integrity-key-32!!"[:32])
    TrustedGovernanceBootstrapper(root=root, checkpoint_store=store).bootstrap(bundle)

    # Simulate a separate application runtime loading only pinned public trust + durable state.
    runtime = TrustedGovernanceRuntime(root=root, checkpoint_store=store)
    runtime.load_or_advance(bundle)

    report = VinculumEngine(
        governance_policy=GovernancePolicy.trusted()
    ).bind_trusted([hypothesis], [constraint], runtime=runtime)

    print(report.results[0].state.value)
    print(report.trust)
    print(report.sha256())
