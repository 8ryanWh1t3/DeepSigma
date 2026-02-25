#!/usr/bin/env python3
"""Seal-and-Prove — single-command court-grade admissibility pipeline.

Orchestrates:
  1. Seal bundle (build_sealed_run)
  2. Merkle commitments (already embedded by seal_bundle)
  3. Write sealed + manifest (write_sealed_output)
  4. Sign primary signature
  5. Append witness signatures (optional)
  6. Append to transparency log
  7. Determinism audit self-check
  8. Replay self-check with all flags
  9. Assemble admissibility pack (optional)

Usage:
    python src/tools/reconstruct/seal_and_prove.py \\
        --decision-id DEC-001 \\
        --clock 2026-02-21T00:00:00Z \\
        --sign-algo hmac \\
        --sign-key-id ds-dev-2026-02 \\
        --sign-key "$DEEPSIGMA_SIGNING_KEY"

    # With witness + transparency log + pack:
    python src/tools/reconstruct/seal_and_prove.py \\
        --decision-id DEC-001 \\
        --clock 2026-02-21T00:00:00Z \\
        --sign-algo hmac \\
        --sign-key-id ds-dev-2026-02 \\
        --sign-key "$DEEPSIGMA_SIGNING_KEY" \\
        --witness-keys '[{"key_b64":"...","key_id":"ds-witness-01","signer_id":"reviewer-1","role":"reviewer"}]' \\
        --transparency-log artifacts/transparency_log/log.ndjson \\
        --pack-dir /tmp/admissibility-pack
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# Ensure reconstruct modules are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from authority_ledger_append import append_entry as append_authority_entry  # noqa: E402
from build_abp import build_abp, write_abp, _resolve_authority_ref  # noqa: E402
from determinism_audit import audit_sealed_run  # noqa: E402
from deterministic_io import read_csv_deterministic  # noqa: E402
from replay_sealed_run import replay  # noqa: E402
from seal_bundle import build_sealed_run, write_sealed_output  # noqa: E402
from sign_artifact import append_signature, sign_artifact  # noqa: E402
from transparency_log_append import append_entry  # noqa: E402


DEFAULT_DATA_DIR = Path("artifacts/sample_data/prompt_os_v2")
DEFAULT_OUT_DIR = Path("artifacts/sealed_runs")
DEFAULT_PROMPTS_DIR = Path("prompts")
DEFAULT_SCHEMAS_DIR = Path("schemas")
DEFAULT_POLICY_BASELINE = Path("docs/governance/POLICY_BASELINE.md")
DEFAULT_POLICY_VERSION = Path("docs/governance/POLICY_VERSION.txt")
DEFAULT_LOG_PATH = Path("artifacts/transparency_log/log.ndjson")
DEFAULT_AUTHORITY_LEDGER = Path("artifacts/authority_ledger/ledger.ndjson")


def seal_and_prove(
    decision_id: str,
    clock: str,
    sign_algo: str,
    sign_key_id: str,
    sign_key: str | None = None,
    user: str = "Boss",
    data_dir: Path = DEFAULT_DATA_DIR,
    out_dir: Path = DEFAULT_OUT_DIR,
    prompts_dir: Path = DEFAULT_PROMPTS_DIR,
    schemas_dir: Path = DEFAULT_SCHEMAS_DIR,
    policy_baseline: Path = DEFAULT_POLICY_BASELINE,
    policy_version_file: Path = DEFAULT_POLICY_VERSION,
    witness_keys: list[dict] | None = None,
    transparency_log: Path | None = None,
    pack_dir: Path | None = None,
    no_audit: bool = False,
    no_replay_check: bool = False,
    external_signer_cmd: str | None = None,
    authority_ledger: Path | None = None,
    authority_entry_id: str | None = None,
    auto_authority: bool = False,
    abp_path: Path | None = None,
    abp_config: Path | None = None,
    auto_abp: bool = False,
) -> dict:
    """Run the full seal-and-prove pipeline. Returns summary dict."""
    errors: list[str] = []
    authority_ledger_path = authority_ledger or DEFAULT_AUTHORITY_LEDGER

    # ── Step 1: Find decision ────────────────────────────────────
    decision_path = data_dir / "decision_log.csv"
    if not decision_path.exists():
        raise FileNotFoundError(f"Decision log not found: {decision_path}")

    rows = read_csv_deterministic(decision_path)
    target = None
    for row in rows:
        if row.get("DecisionID") == decision_id:
            target = row
            break
    if not target:
        raise ValueError(f"DecisionID '{decision_id}' not found in {decision_path}")

    # ── Step 1b: Auto-authority (optional) ─────────────────────────
    if auto_authority and not authority_entry_id:
        policy_version = "GOV-UNKNOWN"
        if policy_version_file.exists():
            policy_version = policy_version_file.read_text().strip()
        policy_hash = ""
        if policy_baseline.exists():
            import hashlib as _hl
            _h = _hl.sha256()
            with open(policy_baseline, "rb") as _f:
                for _chunk in iter(lambda: _f.read(8192), b""):
                    _h.update(_chunk)
            policy_hash = "sha256:" + _h.hexdigest()
        auth_entry = append_authority_entry(
            ledger_path=authority_ledger_path,
            authority_id=f"AUTO-{decision_id}",
            actor_id=user,
            actor_role="Operator",
            grant_type="direct",
            scope_bound={"decisions": [decision_id], "claims": [], "patches": [], "prompts": [], "datasets": []},
            policy_version=policy_version,
            policy_hash=policy_hash,
            effective_at=clock,
        )
        authority_entry_id = auth_entry["entry_id"]

    # ── Step 1c: Build or load ABP (optional) ───────────────────
    abp_artifact_path: Path | None = None
    if abp_path and abp_path.exists():
        abp_artifact_path = abp_path
    elif (auto_abp or abp_config) and authority_entry_id:
        abp_cfg = {}
        if abp_config and abp_config.exists():
            abp_cfg = json.loads(abp_config.read_text())
        try:
            auth_ref = _resolve_authority_ref(authority_entry_id, authority_ledger_path)
            abp_scope = abp_cfg.pop("scope", {
                "contract_id": decision_id,
                "program": None,
                "modules": [],
            })
            abp_obj = build_abp(
                scope=abp_scope,
                authority_ref=auth_ref,
                clock=clock,
                **{k: v for k, v in abp_cfg.items()
                   if k in ("objectives", "tools", "data", "approvals",
                            "escalation", "runtime", "proof")},
            )
            abp_artifact_path = write_abp(abp_obj, out_dir)
        except (ValueError, KeyError) as e:
            errors.append(f"ABP build: {e}")

    # ── Step 2: Build sealed run (includes merkle commitments) ───
    sealed, filename, run_id = build_sealed_run(
        decision_row=target,
        user=user,
        data_dir=data_dir,
        prompts_dir=prompts_dir,
        schemas_dir=schemas_dir,
        policy_baseline=policy_baseline,
        policy_version_file=policy_version_file,
        clock=clock,
        deterministic=True,
        authority_ledger_path=authority_ledger_path if authority_entry_id else None,
        authority_entry_id=authority_entry_id,
    )

    # ── Step 3: Write sealed + manifest ──────────────────────────
    sealed_path, manifest_path = write_sealed_output(
        sealed, filename, out_dir, data_dir,
    )

    # ── Step 4: Primary signature ────────────────────────────────
    sig_path = sign_artifact(
        sealed_path, sign_algo, sign_key_id, sign_key,
        signer_id=user, role="operator",
        signer_type="software" if not external_signer_cmd else "external",
        external_signer_cmd=external_signer_cmd,
    )

    # Sign manifest too
    manifest_sig_path = sign_artifact(
        manifest_path, sign_algo, sign_key_id, sign_key,
        signer_id=user, role="operator",
        signer_type="software" if not external_signer_cmd else "external",
        external_signer_cmd=external_signer_cmd,
    )

    sig_paths = [sig_path, manifest_sig_path]

    # ── Step 5: Witness signatures (optional) ────────────────────
    if witness_keys:
        for wk in witness_keys:
            wp = append_signature(
                sealed_path,
                wk.get("algo", sign_algo),
                wk["key_id"],
                wk["key_b64"],
                signer_id=wk.get("signer_id"),
                role=wk.get("role", "witness"),
            )
            sig_paths.append(wp)

    # ── Step 6: Transparency log ─────────────────────────────────
    log_path = transparency_log or DEFAULT_LOG_PATH
    log_entry = None
    if log_path:
        log_entry = append_entry(
            log_path=log_path,
            run_id=run_id,
            commit_hash=sealed["commit_hash"],
            sealed_hash=sealed["hash"],
            signing_key_id=sign_key_id,
            artifact_path=str(sealed_path),
        )

    # ── Step 7: Determinism audit self-check ─────────────────────
    audit_result = None
    if not no_audit:
        audit_result = audit_sealed_run(sealed_path, strict=True)
        if audit_result.violations > 0:
            errors.append(f"Determinism audit: {audit_result.violations} violations")

    # ── Step 8: Replay self-check ────────────────────────────────
    replay_result = None
    if not no_replay_check:
        replay_result = replay(
            sealed_path,
            verify_hash=True,
            verify_sig=True,
            key_b64=sign_key,
            verify_transparency=log_path is not None,
            transparency_log=log_path,
            require_multisig=len(witness_keys) + 1 if witness_keys else None,
            verify_authority=authority_entry_id is not None,
            authority_ledger=authority_ledger_path if authority_entry_id else None,
        )
        if not replay_result.passed:
            errors.append(f"Replay check: {replay_result.failed_count} failures")

    # ── Step 9: Admissibility pack (optional) ────────────────────
    if pack_dir:
        pack_dir.mkdir(parents=True, exist_ok=True)
        # Copy all artifacts into the pack
        shutil.copy2(sealed_path, pack_dir)
        shutil.copy2(manifest_path, pack_dir)
        for sp in sig_paths:
            if sp.exists():
                shutil.copy2(sp, pack_dir)
        # Copy transparency log if it exists
        if log_path and log_path.exists():
            shutil.copy2(log_path, pack_dir / "transparency_log.ndjson")
        # Copy authority ledger if it exists
        if authority_entry_id and authority_ledger_path.exists():
            shutil.copy2(authority_ledger_path, pack_dir / "authority_ledger.ndjson")
        # Copy ABP if it exists
        if abp_artifact_path and abp_artifact_path.exists():
            shutil.copy2(abp_artifact_path, pack_dir / "abp_v1.json")
        # Write verify instructions
        verify_instructions = (
            "# Verify This Pack\n\n"
            "```bash\n"
            f"python src/tools/reconstruct/verify_pack.py --pack {pack_dir}"
        )
        if sign_algo == "hmac":
            verify_instructions += ' --key "$KEY"'
        verify_instructions += "\n```\n"
        (pack_dir / "VERIFY_INSTRUCTIONS.md").write_text(verify_instructions)

    summary = {
        "decision_id": decision_id,
        "run_id": run_id,
        "commit_hash": sealed["commit_hash"],
        "content_hash": sealed["hash"],
        "sealed_path": str(sealed_path),
        "manifest_path": str(manifest_path),
        "sig_paths": [str(p) for p in sig_paths],
        "transparency_entry": log_entry.get("entry_id") if log_entry else None,
        "authority_entry_id": authority_entry_id,
        "abp_path": str(abp_artifact_path) if abp_artifact_path else None,
        "audit_clean": audit_result.violations == 0 if audit_result else None,
        "replay_passed": replay_result.passed if replay_result else None,
        "pack_dir": str(pack_dir) if pack_dir else None,
        "errors": errors,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seal-and-Prove — court-grade admissibility pipeline"
    )
    parser.add_argument("--decision-id", required=True, help="DecisionID to seal")
    parser.add_argument("--user", default="Boss", help="Operator name")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--prompts-dir", type=Path, default=DEFAULT_PROMPTS_DIR)
    parser.add_argument("--schemas-dir", type=Path, default=DEFAULT_SCHEMAS_DIR)
    parser.add_argument("--policy-baseline", type=Path, default=DEFAULT_POLICY_BASELINE)
    parser.add_argument("--policy-version", type=Path, default=DEFAULT_POLICY_VERSION)
    parser.add_argument("--clock", required=True,
                        help="Fixed clock (ISO8601 UTC, e.g. 2026-02-21T00:00:00Z)")
    parser.add_argument("--sign-algo", default="hmac", choices=["ed25519", "hmac"],
                        help="Signing algorithm (default: hmac)")
    parser.add_argument("--sign-key-id", required=True, help="Signing key ID")
    parser.add_argument("--sign-key", default=None,
                        help="Base64 signing key (or set DEEPSIGMA_SIGNING_KEY env)")
    parser.add_argument("--witness-keys", default=None,
                        help="JSON array of witness key objects")
    parser.add_argument("--transparency-log", type=Path, default=None,
                        help="Transparency log path (default: artifacts/transparency_log/log.ndjson)")
    parser.add_argument("--pack-dir", type=Path, default=None,
                        help="Assemble admissibility pack in this directory")
    parser.add_argument("--no-audit", action="store_true",
                        help="Skip determinism audit self-check")
    parser.add_argument("--no-replay-check", action="store_true",
                        help="Skip replay self-check")
    parser.add_argument("--external-signer-cmd", default=None,
                        help="External signing command")
    parser.add_argument("--authority-ledger", type=Path, default=None,
                        help="Authority ledger path (default: artifacts/authority_ledger/ledger.ndjson)")
    parser.add_argument("--authority-entry-id", default=None,
                        help="Authority entry ID to bind to sealed run")
    parser.add_argument("--auto-authority", action="store_true",
                        help="Auto-append an authority entry before sealing")
    parser.add_argument("--abp-path", type=Path, default=None,
                        help="Path to pre-built ABP v1 JSON")
    parser.add_argument("--abp-config", type=Path, default=None,
                        help="Path to ABP config JSON for auto-build")
    parser.add_argument("--auto-abp", action="store_true",
                        help="Auto-build ABP from authority + defaults")
    args = parser.parse_args()

    # Resolve signing key
    sign_key = args.sign_key or os.environ.get("DEEPSIGMA_SIGNING_KEY")
    if not sign_key and not args.external_signer_cmd:
        print("ERROR: Provide --sign-key, set DEEPSIGMA_SIGNING_KEY, or use --external-signer-cmd",
              file=sys.stderr)
        return 1

    # Parse witness keys
    witness_keys = None
    if args.witness_keys:
        witness_keys = json.loads(args.witness_keys)

    try:
        summary = seal_and_prove(
            decision_id=args.decision_id,
            clock=args.clock,
            sign_algo=args.sign_algo,
            sign_key_id=args.sign_key_id,
            sign_key=sign_key,
            user=args.user,
            data_dir=args.data_dir,
            out_dir=args.out_dir,
            prompts_dir=args.prompts_dir,
            schemas_dir=args.schemas_dir,
            policy_baseline=args.policy_baseline,
            policy_version_file=args.policy_version,
            witness_keys=witness_keys,
            transparency_log=args.transparency_log,
            pack_dir=args.pack_dir,
            no_audit=args.no_audit,
            no_replay_check=args.no_replay_check,
            external_signer_cmd=args.external_signer_cmd,
            authority_ledger=args.authority_ledger,
            authority_entry_id=args.authority_entry_id,
            auto_authority=args.auto_authority,
            abp_path=args.abp_path,
            abp_config=args.abp_config,
            auto_abp=args.auto_abp,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Print summary
    print("=" * 60)
    print("  Seal-and-Prove Pipeline Complete")
    print("=" * 60)
    print(f"  Decision:          {summary['decision_id']}")
    print(f"  Run ID:            {summary['run_id']}")
    print(f"  Commit hash:       {summary['commit_hash']}")
    print(f"  Content hash:      {summary['content_hash']}")
    print(f"  Sealed file:       {summary['sealed_path']}")
    print(f"  Manifest:          {summary['manifest_path']}")
    print(f"  Signatures:        {len(summary['sig_paths'])} files")
    if summary["transparency_entry"]:
        print(f"  Log entry:         {summary['transparency_entry']}")
    if summary.get("authority_entry_id"):
        print(f"  Authority entry:   {summary['authority_entry_id']}")
    if summary.get("abp_path"):
        print(f"  ABP:               {summary['abp_path']}")
    if summary["audit_clean"] is not None:
        icon = "PASS" if summary["audit_clean"] else "FAIL"
        print(f"  Determinism audit: [{icon}]")
    if summary["replay_passed"] is not None:
        icon = "PASS" if summary["replay_passed"] else "FAIL"
        print(f"  Replay check:      [{icon}]")
    if summary["pack_dir"]:
        print(f"  Pack directory:    {summary['pack_dir']}")
    if summary["errors"]:
        print(f"  ERRORS:            {len(summary['errors'])}")
        for err in summary["errors"]:
            print(f"    - {err}")
    print("=" * 60)

    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
