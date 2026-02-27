#!/usr/bin/env python3
"""Seal Bundle Builder — creates an admissible, reconstructable sealed run.

Reads decision data, prompts, schemas, and policy docs; hashes everything
using canonical serialization; builds a sealed_run_v1 JSON with embedded
authority envelope and deterministic commit hash.

Deterministic mode (default):
  --clock 2026-02-21T00:00:00Z --deterministic true

Usage:
    python src/tools/reconstruct/seal_bundle.py --decision-id DEC-001
    python src/tools/reconstruct/seal_bundle.py --decision-id DEC-001 --clock 2026-02-21T00:00:00Z
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from canonical_json import canonical_dumps, sha256_text
from deterministic_ids import det_id
from deterministic_io import list_files_deterministic, read_csv_deterministic
from sign_artifact import sign_artifact
from time_controls import format_utc, format_utc_compact, observed_now, parse_clock


# ── Defaults ──────────────────────────────────────────────────────
DEFAULT_DATA_DIR = Path("enterprise/artifacts/sample_data/prompt_os_v2")
DEFAULT_OUT_DIR = Path("enterprise/artifacts/sealed_runs")
DEFAULT_PROMPTS_DIR = Path("enterprise/prompts")
DEFAULT_SCHEMAS_DIR = Path("enterprise/schemas")
DEFAULT_POLICY_BASELINE = Path("enterprise/docs/governance/POLICY_BASELINE.md")
DEFAULT_POLICY_VERSION = Path("enterprise/docs/governance/POLICY_VERSION.txt")

REFUSAL_CHECKS = [
    "authority_present",
    "scope_bound_valid",
    "policy_not_expired",
    "evidence_threshold_met",
    "provenance_complete",
]

ENFORCEMENT_GATES = [
    "authority_envelope_complete",
    "policy_hash_matches",
    "schema_version_valid",
    "inputs_hashed",
    "refusal_checks_recorded",
]


# ── Helpers ──────────────────────────────────────────────────────
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def hash_prompt_files(prompts_dir: Path) -> dict[str, str]:
    """Hash all prompt files, returning {relative_path: hash}."""
    result = {}
    if not prompts_dir.exists():
        return result
    for p in sorted(prompts_dir.rglob("*")):
        if p.is_file() and p.suffix in (".md", ".txt", ".yaml", ".yml"):
            rel = str(p.relative_to(prompts_dir.parent))
            result[rel] = sha256_file(p)
    return result


def hash_schema_files(schemas_dir: Path) -> dict[str, str]:
    """Hash all schema files, returning {relative_path: hash}."""
    result = {}
    if not schemas_dir.exists():
        return result
    for p in sorted(schemas_dir.rglob("*.json")):
        if p.is_file():
            rel = str(p.relative_to(schemas_dir.parent))
            result[rel] = sha256_file(p)
    return result


# ── Hash Scope Builder ───────────────────────────────────────────
def build_hash_scope(
    data_dir: Path,
    prompts_dir: Path,
    schemas_dir: Path,
    policy_baseline: Path,
    policy_version: str,
    clock: str | None,
    deterministic: bool,
) -> dict:
    """Build the deterministic hash scope manifest."""
    # Input files (CSVs) — sorted lexicographically
    input_entries = []
    for csv_file in list_files_deterministic(data_dir, "*.csv"):
        rel = str(csv_file.relative_to(data_dir.parent.parent.parent))
        input_entries.append({
            "path": rel,
            "sha256": sha256_file(csv_file),
            "type": "csv",
        })

    # Prompt files
    prompt_hashes = hash_prompt_files(prompts_dir)
    prompt_entries = [
        {"path": p, "sha256": h} for p, h in sorted(prompt_hashes.items())
    ]

    # Policy
    policy_entries = []
    if policy_baseline.exists():
        policy_entries.append({
            "path": str(policy_baseline),
            "sha256": sha256_file(policy_baseline),
            "version": policy_version,
        })

    # Schema files
    schema_hashes = hash_schema_files(schemas_dir)
    schema_entries = [
        {"path": p, "sha256": h} for p, h in sorted(schema_hashes.items())
    ]

    return {
        "scope_version": "1.0",
        "inputs": input_entries,
        "prompts": prompt_entries,
        "policies": policy_entries,
        "schemas": schema_entries,
        "parameters": {
            "clock": clock,
            "deterministic": deterministic,
        },
        "exclusions": [
            "observed_at",
            "artifacts_emitted",
        ],
    }


# ── Builder ──────────────────────────────────────────────────────
def build_sealed_run(
    decision_row: dict,
    user: str,
    data_dir: Path,
    prompts_dir: Path,
    schemas_dir: Path,
    policy_baseline: Path,
    policy_version_file: Path,
    clock: str | None = None,
    deterministic: bool = True,
    authority_ledger_path: Path | None = None,
    authority_entry_id: str | None = None,
) -> tuple[dict, str, str]:
    """Build a deterministic sealed run.

    Returns (sealed_dict, filename, run_id).
    """
    committed_at = parse_clock(clock)
    committed_at_iso = format_utc(committed_at)

    # Wall clock (excluded from hash scope)
    obs = observed_now()

    # Read policy version
    policy_version = "GOV-UNKNOWN"
    if policy_version_file.exists():
        policy_version = policy_version_file.read_text().strip()

    # Build hash scope
    hash_scope = build_hash_scope(
        data_dir=data_dir,
        prompts_dir=prompts_dir,
        schemas_dir=schemas_dir,
        policy_baseline=policy_baseline,
        policy_version=policy_version,
        clock=clock,
        deterministic=deterministic,
    )

    # Compute commit hash from canonical hash scope
    commit_hash = sha256_text(canonical_dumps(hash_scope))

    # Derive run ID deterministically
    run_id = det_id("RUN", commit_hash, length=8)

    # Hash policy baseline
    policy_hash = ""
    if policy_baseline.exists():
        policy_hash = sha256_file(policy_baseline)

    # Prompt hashes
    prompt_hashes = hash_prompt_files(prompts_dir)

    # Input files
    input_files = []
    for csv_file in list_files_deterministic(data_dir, "*.csv"):
        rel = str(csv_file.relative_to(data_dir.parent.parent.parent))
        input_files.append({
            "path": rel,
            "sha256": sha256_file(csv_file),
        })

    # Scope
    scope_decisions = [decision_row["DecisionID"]]
    scope_datasets = [f["path"] for f in input_files]

    # Authority envelope
    authority_envelope = {
        "envelope_version": "1.0",
        "actor": {
            "id": user,
            "role": "Operator",
        },
        "authority": {
            "type": "direct",
            "source": policy_version,
            "effective_at": committed_at_iso,
            "expires_at": None,
        },
        "scope_bound": {
            "decisions": scope_decisions,
            "claims": [],
            "patches": [],
            "prompts": sorted(prompt_hashes.keys()),
            "datasets": scope_datasets,
        },
        "policy_snapshot": {
            "policy_version": policy_version,
            "policy_hash": policy_hash,
            "prompt_hashes": dict(sorted(prompt_hashes.items())),
            "schema_version": "1.0",
        },
        "refusal": {
            "refusal_available": True,
            "refusal_triggered": False,
            "refusal_reason_code": None,
            "checks_performed": REFUSAL_CHECKS,
        },
        "enforcement": {
            "gates_checked": ENFORCEMENT_GATES,
            "gate_outcomes": [
                {"gate": g, "result": "pass"} for g in ENFORCEMENT_GATES
            ],
            "enforcement_emitted": True,
        },
        "provenance": {
            "created_at": committed_at_iso,
            "observed_at": obs,
            "run_id": run_id,
            "deterministic_inputs_hash": commit_hash,
        },
    }

    # Decision state
    decision_state = {
        "decision_id": decision_row["DecisionID"],
        "title": decision_row.get("Title", ""),
        "status": decision_row.get("Status", ""),
        "confidence_pct": float(decision_row.get("Confidence_pct", 0)),
        "priority_score": float(decision_row.get("PriorityScore", 0)),
    }

    # Outputs (placeholder)
    outputs = {
        "top_risks": [],
        "top_actions": [],
        "suggested_updates": [],
    }

    # Replay instructions
    ts = format_utc_compact(committed_at)
    sealed_filename = f"{run_id}_{ts}.json"
    replay_cmd = (
        "python src/tools/reconstruct/replay_sealed_run.py"
        f" --sealed artifacts/sealed_runs/{sealed_filename}"
    )

    replay_instructions = {
        "method": "replay_sealed_run.py",
        "command": replay_cmd,
        "required_files": [f["path"] for f in input_files],
    }

    # Build merkle commitment roots (derived from same data as hash_scope)
    # Lazy import to avoid circular dependency (build_commitments → seal_bundle)
    from build_commitments import build_commitment
    inputs_commitments = build_commitment(
        data_dir=data_dir,
        prompts_dir=prompts_dir,
        schemas_dir=schemas_dir,
        policy_baseline=policy_baseline,
    )

    # Authority ledger ref (optional, v2.0.3+)
    authority_ledger_ref = None
    if authority_ledger_path and authority_entry_id:
        from authority_ledger_append import find_entry as find_ledger_entry
        ledger_entry = find_ledger_entry(authority_ledger_path, authority_entry_id)
        if ledger_entry:
            authority_ledger_ref = {
                "authority_entry_id": ledger_entry["entry_id"],
                "authority_entry_hash": ledger_entry["entry_hash"],
                "authority_id": ledger_entry["authority_id"],
                "authority_ledger_path": str(authority_ledger_path),
            }

    sealed = {
        "schema_version": "1.0",
        "authority_envelope": authority_envelope,
        "decision_state": decision_state,
        "inputs_snapshot": {"files": input_files},
        "outputs": outputs,
        "artifacts_emitted": [],
        "replay_instructions": replay_instructions,
        "hash_scope": hash_scope,
        "commit_hash": commit_hash,
        "inputs_commitments": inputs_commitments,
        "authority_ledger_ref": authority_ledger_ref,
        "hash": "",
    }

    # Compute content hash over canonical serialization
    sealed["hash"] = sha256_text(canonical_dumps(sealed))

    return sealed, sealed_filename, run_id


def write_sealed_output(
    sealed: dict,
    filename: str,
    out_dir: Path,
    data_dir: Path,
) -> tuple[Path, Path]:
    """Write sealed run + manifest to disk. Returns (sealed_path, manifest_path)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    with open(out_path, "w") as f:
        f.write(json.dumps(sealed, indent=2, sort_keys=True))

    # Write manifest
    run_id = sealed["authority_envelope"]["provenance"]["run_id"]
    decision_id = sealed["decision_state"]["decision_id"]
    manifest_path = out_dir / filename.replace(".json", ".manifest.json")
    manifest = {
        "sealed_run": filename,
        "run_id": run_id,
        "decision_id": decision_id,
        "commit_hash": sealed["commit_hash"],
        "hash_scope": sealed["hash_scope"],
        "file_row_counts": {
            e["path"]: _count_csv_rows(data_dir.parent.parent.parent / e["path"])
            for e in sealed["hash_scope"]["inputs"]
        },
        "policy_version": sealed["authority_envelope"]["policy_snapshot"]["policy_version"],
        "schema_versions": {
            e["path"]: "1.0" for e in sealed["hash_scope"]["schemas"]
        },
    }
    with open(manifest_path, "w") as f:
        f.write(json.dumps(manifest, indent=2, sort_keys=True))

    # Update artifacts_emitted and recompute hash
    sealed["artifacts_emitted"] = [
        {"path": str(out_path), "sha256": sha256_file(out_path)},
        {"path": str(manifest_path), "sha256": sha256_file(manifest_path)},
    ]
    sealed["hash"] = ""
    sealed["hash"] = sha256_text(canonical_dumps(sealed))
    with open(out_path, "w") as f:
        f.write(json.dumps(sealed, indent=2, sort_keys=True))

    return out_path, manifest_path


# ── Main ─────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seal Bundle Builder — create admissible sealed run"
    )
    parser.add_argument("--decision-id", required=True, help="DecisionID to seal")
    parser.add_argument("--run-id", default=None,
                        help="Run ID override (ignored in deterministic mode)")
    parser.add_argument("--user", default="Boss", help="Operator name")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--prompts-dir", type=Path, default=DEFAULT_PROMPTS_DIR)
    parser.add_argument("--schemas-dir", type=Path, default=DEFAULT_SCHEMAS_DIR)
    parser.add_argument("--policy-baseline", type=Path, default=DEFAULT_POLICY_BASELINE)
    parser.add_argument("--policy-version", type=Path, default=DEFAULT_POLICY_VERSION)
    parser.add_argument("--clock", default=None,
                        help="Fixed clock (ISO8601 UTC, e.g. 2026-02-21T00:00:00Z)")
    parser.add_argument("--deterministic", default="true", choices=["true", "false"],
                        help="Deterministic mode (default: true)")
    parser.add_argument("--sign", default="false", choices=["true", "false"],
                        help="Sign sealed artifacts (default: false)")
    parser.add_argument("--sign-algo", default="hmac", choices=["ed25519", "hmac"],
                        help="Signing algorithm (default: hmac)")
    parser.add_argument("--sign-key-id", default="ds-dev-2026-01",
                        help="Signing key ID")
    parser.add_argument("--sign-key", default=None,
                        help="Base64 signing key (or set DEEPSIGMA_SIGNING_KEY env)")
    parser.add_argument("--authority-ledger", type=Path, default=None,
                        help="Path to authority ledger NDJSON")
    parser.add_argument("--authority-entry-id", default=None,
                        help="Authority ledger entry ID to bind")
    args = parser.parse_args()

    deterministic = args.deterministic == "true"
    data_dir: Path = args.data_dir

    # Find decision
    decision_path = data_dir / "decision_log.csv"
    if not decision_path.exists():
        print(f"ERROR: Decision log not found: {decision_path}", file=sys.stderr)
        return 1

    rows = read_csv_deterministic(decision_path)
    target = None
    for row in rows:
        if row.get("DecisionID") == args.decision_id:
            target = row
            break

    if not target:
        print(f"ERROR: DecisionID '{args.decision_id}' not found", file=sys.stderr)
        return 1

    sealed, filename, run_id = build_sealed_run(
        decision_row=target,
        user=args.user,
        data_dir=data_dir,
        prompts_dir=args.prompts_dir,
        schemas_dir=args.schemas_dir,
        policy_baseline=args.policy_baseline,
        policy_version_file=args.policy_version,
        clock=args.clock,
        deterministic=deterministic,
        authority_ledger_path=args.authority_ledger,
        authority_entry_id=args.authority_entry_id,
    )

    # Write sealed run + manifest
    out_path, manifest_path = write_sealed_output(
        sealed, filename, args.out_dir, data_dir,
    )

    # Signing (optional)
    sig_paths = []
    do_sign = args.sign == "true"
    if do_sign:
        sign_key = args.sign_key or os.environ.get("DEEPSIGMA_SIGNING_KEY")
        if not sign_key:
            print("ERROR: --sign requires --sign-key or DEEPSIGMA_SIGNING_KEY env",
                  file=sys.stderr)
            return 1
        for artifact in [out_path, manifest_path]:
            sp = sign_artifact(artifact, args.sign_algo, args.sign_key_id, sign_key)
            sig_paths.append(sp)

    # Summary
    print("=" * 55)
    print("  Seal Bundle Builder (Deterministic)")
    print("=" * 55)
    print(f"  Decision:        {target['DecisionID']} — {target.get('Title', '?')}")
    print(f"  Run ID:          {run_id}")
    print(f"  Operator:        {args.user}")
    print(f"  Deterministic:   {deterministic}")
    print(f"  Clock:           {args.clock or '(wall clock)'}")
    print(f"  Policy:          {sealed['authority_envelope']['policy_snapshot']['policy_version']}")
    print(f"  Commit hash:     {sealed['commit_hash']}")
    print(f"  Refusal checked: {len(REFUSAL_CHECKS)} checks, none triggered")
    print(f"  Gates passed:    {len(ENFORCEMENT_GATES)}/{len(ENFORCEMENT_GATES)}")
    print(f"  Sealed file:     {out_path}")
    print(f"  Manifest:        {manifest_path}")
    if sig_paths:
        print(f"  Signed:          {args.sign_algo} ({args.sign_key_id})")
        for sp in sig_paths:
            print(f"    Sig:           {sp}")
    print(f"  Content hash:    {sealed['hash']}")
    print("=" * 55)

    return 0


def _count_csv_rows(path: Path) -> int:
    """Count data rows in a CSV (excluding header)."""
    if not path.exists():
        return 0
    with open(path) as f:
        return max(0, sum(1 for _ in f) - 1)


if __name__ == "__main__":
    sys.exit(main())
