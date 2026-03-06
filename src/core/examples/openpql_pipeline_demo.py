"""OpenPQL Pipeline Demo — End-to-end 7-primitive walkthrough.

Run: python -m core.examples.openpql_pipeline_demo

Demonstrates the full OpenPQL pipeline:
  1. Build PolicySource from a ReOps decision packet
  2. Compile to CompiledPolicy (deterministic)
  3. Write artifact to disk + verify seal
  4. Evaluate through RuntimeGate
  5. Append to EvidenceChain
  6. Query with AuditRetrieval
  7. Verify chain integrity
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from core.authority.artifact_builder import (
    build_artifact,
    load_artifact,
    verify_artifact,
    write_artifact,
)
from core.authority.audit_retrieval import AuditRetrieval
from core.authority.evidence_chain import EvidenceChain, EvidenceEntry
from core.authority.policy_compiler import compile_from_source
from core.authority.policy_source import build_policy_source, validate_policy_source
from core.authority.runtime_gate import RuntimeGate


def main() -> None:
    print("=" * 60)
    print("OpenPQL 7-Primitive Pipeline Demo")
    print("=" * 60)

    # ── 1. Policy Source ──────────────────────────────────────
    print("\n[1/7] Building PolicySource from ReOps decision packet...")
    dlr = {
        "dlrId": "DLR-DEMO-001",
        "episodeId": "EP-DEMO-001",
        "actionType": "quarantine",
        "claims": {
            "quarantine": [
                {"claimId": "CLAIM-D001", "statement": "Churn model accuracy 92%", "confidence": {"score": 0.92}},
                {"claimId": "CLAIM-D002", "statement": "Pipeline freshness OK", "confidence": {"score": 0.88}},
            ],
        },
    }
    policy_pack = {
        "policyPackId": "PP-DEMO-001",
        "version": "1.0.0",
        "constraints": [],
        "requiresDlr": True,
        "maxBlastRadius": "medium",
        "minimumConfidence": 0.7,
    }
    source = build_policy_source(dlr, policy_pack)
    valid, errors = validate_policy_source(source)
    print(f"  Source ID:   {source.source_id}")
    print(f"  Source Hash: {source.source_hash}")
    print(f"  Valid:       {valid}")

    # ── 2. Compile ────────────────────────────────────────────
    print("\n[2/7] Compiling to CompiledPolicy...")
    compiled = compile_from_source(source)
    print(f"  Artifact ID:  {compiled.artifact_id}")
    print(f"  Policy Hash:  {compiled.policy_hash}")
    print(f"  Rules:        {len(compiled.rules)} constraints")
    print(f"  Seal Hash:    {compiled.seal_hash}")

    # ── 3. Artifact Builder ───────────────────────────────────
    print("\n[3/7] Writing artifact to disk + verifying seal...")
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        path = write_artifact(compiled, out_dir)
        loaded = load_artifact(path)
        print(f"  Written to:   {path.name}")
        print(f"  Seal valid:   {verify_artifact(loaded)}")

    # ── 4. Runtime Gate ───────────────────────────────────────
    print("\n[4/7] Evaluating through RuntimeGate...")
    gate = RuntimeGate()
    request = {
        "actionId": "ACT-DEMO-001",
        "actionType": "quarantine",
        "actorId": "agent-demo",
        "resourceRef": "resource-demo",
        "episodeId": "EP-DEMO-001",
        "blastRadiusTier": "small",
        "dlrRef": "DLR-DEMO-001",
    }
    context = {
        "actor_registry": {
            "agent-demo": {
                "actorType": "agent",
                "roles": [{"roleId": "R-001", "roleName": "operator", "scope": "security-ops"}],
            },
        },
        "resource_registry": {
            "resource-demo": {"resourceType": "account", "classification": "internal"},
        },
        "policy_packs": {"quarantine": policy_pack, "default": policy_pack},
        "dlr_store": {"DLR-DEMO-001": dlr},
        "claims": dlr["claims"]["quarantine"],
        "kill_switch_active": False,
    }
    decision = gate.evaluate(compiled, request, context)
    print(f"  Gate ID:      {decision.gate_id}")
    print(f"  Verdict:      {decision.verdict}")
    print(f"  Artifact ID:  {decision.artifact_id}")
    print(f"  Passed:       {decision.passed_checks}")

    # ── 5. Evidence Chain ─────────────────────────────────────
    print("\n[5/7] Appending to EvidenceChain...")
    chain = EvidenceChain()
    entry = EvidenceEntry(
        evidence_id="",
        gate_id=decision.gate_id,
        action_id=request["actionId"],
        actor_id=request["actorId"],
        resource_id=request["resourceRef"],
        verdict=decision.verdict,
        evaluated_at=decision.evaluated_at,
        artifact_id=decision.artifact_id,
        policy_hash=decision.policy_hash,
        passed_checks=decision.passed_checks,
        failed_checks=decision.failed_checks,
    )
    chain_hash = chain.append(entry)
    print(f"  Evidence ID:  {entry.evidence_id}")
    print(f"  Chain Hash:   {chain_hash}")

    # ── 6. Audit Retrieval ────────────────────────────────────
    print("\n[6/7] Querying with AuditRetrieval...")
    retrieval = AuditRetrieval(evidence_chain=chain)
    answer = retrieval.why_allowed("ACT-DEMO-001")
    print(f"  Query:        why_allowed('ACT-DEMO-001')")
    print(f"  Found:        {answer.found}")
    print(f"  Verdict:      {answer.verdict}")
    print(f"  Detail:       {answer.detail}")

    hash_answer = retrieval.which_policy_hash("ACT-DEMO-001")
    print(f"  Policy Hash:  {hash_answer.detail}")

    # ── 7. Chain Integrity ────────────────────────────────────
    print("\n[7/7] Verifying chain integrity...")
    print(f"  Chain length: {chain.entry_count}")
    print(f"  Chain valid:  {chain.verify()}")

    print("\n" + "=" * 60)
    print("Pipeline complete. All 7 OpenPQL primitives exercised.")
    print("=" * 60)


if __name__ == "__main__":
    main()
