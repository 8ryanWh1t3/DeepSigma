# DeepSigma Feature Catalog

Machine source of truth: `release_kpis/feature_catalog.json`

## Categories

### Deterministic Governance Boundary
Governance enforced before execution: default deny, halt on ambiguity, proof-first artifacts.

- **Pre-Execution Gate** (`PRE_EXEC_GATE`)
  - Blocks execution unless intent+authority+policy requirements are satisfied.
  - Artifacts: runs/intent_packet.json, runs/authority_contract.json, runs/input_snapshot.json
  - Enforcement: make milestone-gate, CI: ci.yml, CI: kpi_gate.yml
  - KPI axes: Automation_Depth, Authority_Modeling, Operational_Maturity
- **Default Deny** (`DEFAULT_DENY`)
  - If required conditions cannot be evaluated or are missing, execution is denied.
  - Artifacts: governance/ambiguity_policy.md
  - Enforcement: scripts/pre_exec_gate.py
  - KPI axes: Authority_Modeling, Operational_Maturity
- **Halt on Ambiguity** (`HALT_ON_AMBIGUITY`)
  - Conflicts/unknowns/insufficient provenance trigger a hard fail before routing.
  - Artifacts: governance/ambiguity_policy.md
  - Enforcement: scripts/pre_exec_gate.py, scripts/validate_v2_1_0_milestone.py
  - KPI axes: Authority_Modeling, Operational_Maturity

### Intent Capture & Governance
Intent declared pre-action and bound to execution.

- **Intent Packet Schema** (`INTENT_PACKET_SCHEMA`)
  - Formal structure for intent, scope, success criteria, TTL, author, authority.
  - Artifacts: schemas/intent_packet.schema.json, runs/intent_packet.json
  - Enforcement: scripts/validate_intent_packet.py, scripts/validate_v2_1_0_milestone.py
  - KPI axes: Authority_Modeling, Technical_Completeness
- **Intent TTL Enforcement** (`INTENT_TTL`)
  - Intent expires; expired intent blocks execution.
  - Artifacts: runs/intent_packet.json
  - Enforcement: scripts/validate_intent_packet.py
  - KPI axes: Operational_Maturity, Authority_Modeling
- **Intent Hash Binding** (`INTENT_HASH_BINDING`)
  - Intent hash is bound into proof chain and audit pack.
  - Artifacts: runs/proof_bundle.json
  - Enforcement: scripts/crypto_proof.py
  - KPI axes: Technical_Completeness, Authority_Modeling

### Audit-Neutral Decision Logic
Claim→Evidence→Authority and context-free audit export.

- **Decision Invariants Ledger** (`DECISION_INVARIANTS`)
  - Rules like claim→evidence required, no overwrite, authority precedence, TTL/half-life.
  - Artifacts: governance/decision_invariants.md
  - Enforcement: scripts/validate_v2_1_0_milestone.py
  - KPI axes: Operational_Maturity, Enterprise_Readiness
- **Claim→Evidence→Authority Validator** (`CEA_VALIDATOR`)
  - Machine-checkable binding of claims, evidence, and authority references.
  - Artifacts: runs/decision_record.json
  - Enforcement: scripts/validate_claim_evidence_authority.py
  - KPI axes: Technical_Completeness, Enterprise_Readiness
- **Audit-Neutral Export Pack** (`AUDIT_NEUTRAL_PACK`)
  - Exports sealed facts + hashes + authority + proof bundle without political narrative.
  - Artifacts: packs/audit_neutral/*
  - Enforcement: scripts/export_audit_neutral_pack.py
  - KPI axes: Enterprise_Readiness, Operational_Maturity

### Deterministic Replay & Proof Chain
Hash chain + optional signature verification + replay checks.

- **Sealed Input Snapshot** (`INPUT_SNAPSHOT`)
  - Inputs captured and hashed for deterministic evidence.
  - Artifacts: runs/input_snapshot.json
  - Enforcement: scripts/capture_run_snapshot.py
  - KPI axes: Technical_Completeness, Operational_Maturity
- **Proof Bundle** (`PROOF_BUNDLE`)
  - Hash chain across intent, snapshot, authority contract, outputs; optional signature verify.
  - Artifacts: runs/proof_bundle.json
  - Enforcement: scripts/crypto_proof.py
  - KPI axes: Technical_Completeness, Authority_Modeling
- **Replay Validation** (`REPLAY_VALIDATION`)
  - Validates proof chain presence and readiness for deterministic replay.
  - Artifacts: runs/proof_bundle.json
  - Enforcement: scripts/replay_run.py
  - KPI axes: Operational_Maturity, Enterprise_Readiness

### Repo Radar KPI System
8 KPI axes, radar render, badge_latest, PR comment, composite history.

- **KPI Run Pipeline** (`KPI_RUN`)
  - Computes KPI scores and emits render + PR artifacts.
  - Artifacts: release_kpis/radar_*.png, release_kpis/badge_latest*.svg, release_kpis/PR_COMMENT*.md
  - Enforcement: CI: kpi.yml, CI: kpi_gate.yml
  - KPI axes: All
- **Layer Coverage Injection** (`LAYER_COVERAGE`)
  - Appends Decision Infrastructure layer→KPI mapping into PR comment.
  - Artifacts: release_kpis/PR_COMMENT*.md
  - Enforcement: scripts/kpi_run.py
  - KPI axes: Operational_Maturity, Enterprise_Readiness

### Economic Measurability (TEC / C-TEC)
Effort/cost modeling, sensitivity bands, complexity scaling.

- **TEC Baseline** (`TEC_MODEL`)
  - Time/Effort/Cost estimation outputs.
  - Artifacts: release_kpis/TEC*.json, release_kpis/TEC*.md
  - Enforcement: scripts/tec_run.py (if present)
  - KPI axes: Economic_Measurability
- **TEC Sensitivity Bands** (`TEC_SENSITIVITY`)
  - Best/expected/worst bounds + volatility metrics.
  - Artifacts: release_kpis/TEC_SENSITIVITY*.json
  - Enforcement: scripts/tec_run.py (if present)
  - KPI axes: Economic_Measurability, Operational_Maturity

## Outer-Edge Boundaries

- Not claiming full jurisdictional policy packs (EU AI Act article-by-article enforcement) yet
- Not claiming full cryptographic attestation across all pipelines and connectors yet
- Not claiming enterprise connectors (Jira/ServiceNow/SharePoint adapters) as complete (target v2.1.1)
- Not claiming a full runtime control plane is governance (runtime is subordinate)
