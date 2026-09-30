from vinculum import (
    AuthorityGrant,
    Constraint,
    EvidenceRecord,
    GovernanceContext,
    GovernancePolicy,
    Hypothesis,
    ProvenanceRecord,
    VinculumEngine,
)

# P-side evidence and lineage.
evidence = EvidenceRecord.from_payload(
    id="E-OBS-001",
    kind="OBSERVATION",
    source="sensor-A",
    payload={"distance_ft": 90, "quality": "verified"},
)

source_prov = ProvenanceRecord.from_payload(
    id="PROV-SENSOR-A",
    kind="SOURCE",
    source="sensor-registry",
    payload={"sensor": "A", "calibration": "2026-Q3"},
    version="1",
)

hypothesis_prov = ProvenanceRecord.from_payload(
    id="PROV-RUN-017",
    kind="MODEL_RUN",
    source="fusion-runtime",
    payload={"run": "R-17", "model": "M-2"},
    version="17",
    parent_ids=("PROV-SENSOR-A",),
)

# D-side rule lineage and authority.
policy_prov = ProvenanceRecord.from_payload(
    id="PROV-POLICY-004",
    kind="POLICY",
    source="composer://policy/installation-cuas",
    payload={"clause": "minimum standoff distance >= 82ft"},
    version="4",
)

authority_prov = ProvenanceRecord.from_payload(
    id="PROV-AUTH-012",
    kind="SOURCE",
    source="authority-ledger",
    payload={"principal": "P-1", "role": "PolicyOwner"},
    version="12",
)

authority = AuthorityGrant(
    id="AUTH-POLICY-OWNER",
    principal_id="P-1",
    role="PolicyOwner",
    actions=("DEFINE_CONSTRAINT",),
    scopes=("policy:cuas:*",),
    provenance_ref="PROV-AUTH-012",
)

context = GovernanceContext(
    context_id="DEMO-CTX-001",
    evidence=(evidence,),
    provenance=(source_prov, hypothesis_prov, policy_prov, authority_prov),
    authorities=(authority,),
)

hypothesis = Hypothesis(
    id="H1",
    statement="The object meets the governed standoff requirement.",
    probability=0.83,
    payload={"distance": {"value": 90, "unit": "ft"}},
    evidence_refs=("E-OBS-001",),
    provenance_ref="PROV-RUN-017",
)

constraint = Constraint(
    id="D-STANDOFF",
    field="distance",
    op="gte",
    expected={"value": 82, "unit": "ft"},
    hard=True,
    provenance_ref="PROV-POLICY-004",
    authority_ref="AUTH-POLICY-OWNER",
    authority_scope="policy:cuas:standoff",
)

report = VinculumEngine(governance_policy=GovernancePolicy.strict()).bind(
    [hypothesis], [constraint], context=context
)

result = report.results[0]
print(result.state.value)
print(result.governance_status.value)
print(report.governance_context_sha256)
print(report.sha256())
