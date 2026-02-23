#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
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

PROOF_SCRIPTS = [
    "scripts/pre_exec_gate.py",
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

SCHEMA_REQUIRED_KEYS = {
    "intent_statement",
    "scope",
    "success_criteria",
    "ttl_expires_at",
    "author",
    "authority",
}

INVARIANT_SNIPPETS = [
    "Claim",
    "Evidence",
    "Authority",
    "seal",
    "version",
    "patch",
]

PLACEHOLDER_PATTERNS = [
    "TODO:",
    "stub",
    "implement me",
    "placeholder",
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def pass_msg(msg: str) -> None:
    print(f"PASS: {msg}")


def check_placeholder_free(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()
    hits = [p for p in PLACEHOLDER_PATTERNS if p.lower() in text]
    if hits:
        raise ValueError(f"{path} contains placeholder tokens: {', '.join(hits)}")


def check_intent_schema(path: Path) -> None:
    schema = json.loads(path.read_text(encoding="utf-8"))
    if schema.get("type") != "object":
        raise ValueError("intent schema must define type=object")
    required = set(schema.get("required", []))
    missing = sorted(SCHEMA_REQUIRED_KEYS - required)
    if missing:
        raise ValueError(f"intent schema missing required keys: {', '.join(missing)}")
    props = schema.get("properties", {})
    if not isinstance(props, dict) or not props:
        raise ValueError("intent schema properties must be a non-empty object")


def check_invariants_doc(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for token in INVARIANT_SNIPPETS:
        if token.lower() not in text.lower():
            raise ValueError(f"decision invariants missing semantic token '{token}'")


def run_script_self_check(script_rel: str) -> None:
    cmd = [sys.executable, str(ROOT / script_rel), "--self-check"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    output = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode != 0:
        raise ValueError(f"self-check failed for {script_rel}:\n{output}")
    if "PASS:" not in output:
        raise ValueError(f"self-check for {script_rel} did not emit PASS: convention")


def verify_pass_fail_convention(script_rel: str) -> None:
    text = (ROOT / script_rel).read_text(encoding="utf-8")
    if "PASS:" not in text or "FAIL:" not in text:
        raise ValueError(f"{script_rel} must contain PASS:/FAIL: output conventions")


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
        fail("Missing v2.1.0 proof-point files:\n- " + "\n- ".join(missing_proofs))

    check_intent_schema(ROOT / "schemas/intent_packet.schema.json")
    pass_msg("intent schema semantic checks passed")

    check_invariants_doc(ROOT / "governance/decision_invariants.md")
    pass_msg("decision invariants semantic checks passed")

    for script in PROOF_SCRIPTS:
        check_placeholder_free(ROOT / script)
        verify_pass_fail_convention(script)
        run_script_self_check(script)
        pass_msg(f"validated {script}")

    pass_msg("v2.1.0 milestone gate satisfied (no-theater semantics enforced)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
