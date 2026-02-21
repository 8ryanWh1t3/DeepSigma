#!/usr/bin/env python3
"""Replay Sealed Run — adversarial reconstruction without live access.

Validates a sealed run JSON against the sealed_run_v1 schema (structurally)
and prints a deterministic reconstruction report.

Usage:
    python src/tools/reconstruct/replay_sealed_run.py --sealed artifacts/sealed_runs/RUN-001_20260221T120000Z.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


REQUIRED_TOP_KEYS = [
    "schema_version",
    "authority_envelope",
    "decision_state",
    "inputs_snapshot",
    "outputs",
    "artifacts_emitted",
    "replay_instructions",
    "hash",
]

REQUIRED_ENVELOPE_KEYS = [
    "envelope_version",
    "actor",
    "authority",
    "scope_bound",
    "policy_snapshot",
    "refusal",
    "enforcement",
    "provenance",
]

REQUIRED_ACTOR_KEYS = ["id", "role"]
REQUIRED_AUTHORITY_KEYS = ["type", "source", "effective_at", "expires_at"]
REQUIRED_SCOPE_KEYS = ["decisions", "claims", "patches", "prompts", "datasets"]
REQUIRED_POLICY_KEYS = ["policy_version", "policy_hash", "prompt_hashes", "schema_version"]
REQUIRED_REFUSAL_KEYS = [
    "refusal_available", "refusal_triggered", "refusal_reason_code", "checks_performed",
]
REQUIRED_ENFORCEMENT_KEYS = ["gates_checked", "gate_outcomes", "enforcement_emitted"]
REQUIRED_PROVENANCE_KEYS = ["created_at", "run_id", "deterministic_inputs_hash"]
REQUIRED_DECISION_KEYS = ["decision_id", "title", "status", "confidence_pct", "priority_score"]
REQUIRED_REPLAY_KEYS = ["method", "command", "required_files"]


class ReplayResult:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append((name, passed, detail))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    @property
    def failed_count(self) -> int:
        return sum(1 for _, ok, _ in self.checks if not ok)


def verify_keys(obj: dict, required: list[str], prefix: str, result: ReplayResult) -> bool:
    """Check that all required keys are present."""
    missing = [k for k in required if k not in obj]
    if missing:
        result.check(f"{prefix}.keys", False, f"Missing: {missing}")
        return False
    result.check(f"{prefix}.keys", True, f"All {len(required)} keys present")
    return True


def verify_hash(sealed: dict, result: ReplayResult) -> None:
    """Verify the content hash."""
    recorded = sealed.get("hash", "")
    if not recorded:
        result.check("hash.present", False, "No hash field")
        return

    copy = dict(sealed)
    copy["hash"] = ""
    canonical = json.dumps(copy, sort_keys=True)
    computed = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    if computed == recorded:
        result.check("hash.integrity", True, f"Hash verified: {recorded[:30]}...")
    else:
        result.check("hash.integrity", False, f"Expected {computed[:30]}... got {recorded[:30]}...")


def replay(sealed_path: Path) -> ReplayResult:
    """Run the full replay validation."""
    result = ReplayResult()

    # Load
    if not sealed_path.exists():
        result.check("file.exists", False, f"Not found: {sealed_path}")
        return result
    result.check("file.exists", True, str(sealed_path))

    try:
        sealed = json.loads(sealed_path.read_text())
    except json.JSONDecodeError as e:
        result.check("file.json", False, str(e))
        return result
    result.check("file.json", True, "Valid JSON")

    # Top-level structure
    if not verify_keys(sealed, REQUIRED_TOP_KEYS, "sealed_run", result):
        return result

    # Schema version
    sv = sealed.get("schema_version")
    result.check("schema_version", sv == "1.0", f"version={sv}")

    # Authority envelope
    envelope = sealed.get("authority_envelope", {})
    if not verify_keys(envelope, REQUIRED_ENVELOPE_KEYS, "envelope", result):
        return result

    result.check(
        "envelope.version",
        envelope.get("envelope_version") == "1.0",
        f"version={envelope.get('envelope_version')}",
    )

    # Actor
    actor = envelope.get("actor", {})
    verify_keys(actor, REQUIRED_ACTOR_KEYS, "actor", result)
    result.check("actor.id", bool(actor.get("id")), f"id={actor.get('id')}")
    result.check("actor.role", bool(actor.get("role")), f"role={actor.get('role')}")

    # Authority
    authority = envelope.get("authority", {})
    verify_keys(authority, REQUIRED_AUTHORITY_KEYS, "authority", result)
    result.check(
        "authority.type",
        authority.get("type") in ("delegated", "direct", "system", "inherited"),
        f"type={authority.get('type')}",
    )

    # Scope
    scope = envelope.get("scope_bound", {})
    verify_keys(scope, REQUIRED_SCOPE_KEYS, "scope", result)
    result.check(
        "scope.decisions",
        len(scope.get("decisions", [])) > 0,
        f"{len(scope.get('decisions', []))} decisions bound",
    )

    # Policy snapshot
    policy = envelope.get("policy_snapshot", {})
    verify_keys(policy, REQUIRED_POLICY_KEYS, "policy", result)
    result.check(
        "policy.version",
        bool(policy.get("policy_version")),
        f"version={policy.get('policy_version')}",
    )
    result.check(
        "policy.hash",
        bool(policy.get("policy_hash")),
        f"hash={str(policy.get('policy_hash', ''))[:30]}...",
    )

    # Refusal
    refusal = envelope.get("refusal", {})
    verify_keys(refusal, REQUIRED_REFUSAL_KEYS, "refusal", result)
    result.check(
        "refusal.available",
        refusal.get("refusal_available") is True,
        f"available={refusal.get('refusal_available')}",
    )
    checks_count = len(refusal.get("checks_performed", []))
    result.check(
        "refusal.checks_recorded",
        checks_count > 0,
        f"{checks_count} checks recorded",
    )

    # Enforcement
    enforcement = envelope.get("enforcement", {})
    verify_keys(enforcement, REQUIRED_ENFORCEMENT_KEYS, "enforcement", result)
    result.check(
        "enforcement.emitted",
        enforcement.get("enforcement_emitted") is True,
        f"emitted={enforcement.get('enforcement_emitted')}",
    )
    gates = enforcement.get("gate_outcomes", [])
    failed_gates = [g for g in gates if g.get("result") == "fail"]
    result.check(
        "enforcement.gates",
        len(failed_gates) == 0,
        f"{len(gates)} gates checked, {len(failed_gates)} failed",
    )

    # Provenance
    provenance = envelope.get("provenance", {})
    verify_keys(provenance, REQUIRED_PROVENANCE_KEYS, "provenance", result)
    result.check(
        "provenance.run_id",
        bool(provenance.get("run_id")),
        f"run_id={provenance.get('run_id')}",
    )
    result.check(
        "provenance.inputs_hash",
        bool(provenance.get("deterministic_inputs_hash")),
        "deterministic inputs hash present",
    )

    # Decision state
    decision = sealed.get("decision_state", {})
    verify_keys(decision, REQUIRED_DECISION_KEYS, "decision", result)

    # Inputs snapshot
    inputs = sealed.get("inputs_snapshot", {})
    files = inputs.get("files", [])
    result.check("inputs.files", len(files) > 0, f"{len(files)} input files referenced")
    for fi in files:
        has_hash = bool(fi.get("sha256"))
        result.check(
            f"inputs.hash[{fi.get('path', '?')}]",
            has_hash,
            "hash present" if has_hash else "MISSING hash",
        )

    # Replay instructions
    replay_inst = sealed.get("replay_instructions", {})
    verify_keys(replay_inst, REQUIRED_REPLAY_KEYS, "replay", result)

    # Hash integrity (last check)
    verify_hash(sealed, result)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay Sealed Run — adversarial reconstruction validator"
    )
    parser.add_argument(
        "--sealed", type=Path, required=True,
        help="Path to sealed run JSON",
    )
    args = parser.parse_args()

    result = replay(args.sealed)

    # Print report
    print("=" * 60)
    print("  Adversarial Reconstruction Report")
    print("=" * 60)

    for name, passed, detail in result.checks:
        icon = "PASS" if passed else "FAIL"
        detail_str = f"  ({detail})" if detail else ""
        print(f"  [{icon}] {name}{detail_str}")

    print("-" * 60)
    total = len(result.checks)
    passed = sum(1 for _, ok, _ in result.checks if ok)
    failed = result.failed_count

    if result.passed:
        print(f"  RESULT: ADMISSIBLE  ({passed}/{total} checks passed)")
    else:
        print(f"  RESULT: INADMISSIBLE  ({failed}/{total} checks failed)")
    print("=" * 60)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
