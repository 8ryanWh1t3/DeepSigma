#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "specs/decision_infrastructure_model.md",
    "release_kpis/layer_kpi_mapping.json",
]

REQUIRED_PROOFS = [
    "schemas/intent_packet.schema.json",
    "scripts/pre_exec_gate.py",
    "governance/decision_invariants.md",
    "scripts/validate_claim_evidence_authority.py",
    "scripts/verify_authority_signature.py",
    "scripts/idempotency_guard.py",
    "scripts/capture_run_snapshot.py",
    "scripts/replay_run.py",
    "scripts/export_audit_neutral_pack.py",
]

REQUIRED_LAYERS = [
    "Layer_0_Intent",
    "Layer_1_AuditLogic",
    "Layer_2_PreExecution",
    "Layer_3_RuntimeSafety",
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> int:
    missing_baseline = [p for p in REQUIRED_FILES if not (ROOT / p).exists()]
    if missing_baseline:
        fail("Missing required baseline files:\n- " + "\n- ".join(missing_baseline))

    mapping_path = ROOT / "release_kpis/layer_kpi_mapping.json"
    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"layer_kpi_mapping.json is not valid JSON: {exc}")

    for layer in REQUIRED_LAYERS:
        if layer not in mapping:
            fail(f"layer_kpi_mapping.json missing layer: {layer}")
        if not isinstance(mapping[layer], list) or not mapping[layer]:
            fail(f"layer_kpi_mapping.json layer has empty KPI list: {layer}")

    missing_proofs = [p for p in REQUIRED_PROOFS if not (ROOT / p).exists()]
    if missing_proofs:
        fail("Missing v2.1.0 proof-point files (create stubs if needed):\n- " + "\n- ".join(missing_proofs))

    print("PASS: v2.1.0 milestone gate satisfied (baseline proof points present).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
