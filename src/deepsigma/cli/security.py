"""deepsigma security — DISR security operations."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from deepsigma.security.reencrypt import reencrypt_summary_to_dict, run_reencrypt_job
from deepsigma.security.rotate_keys import rotate_keys, rotation_result_to_dict


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("security", help="DISR security commands")
    sp = p.add_subparsers(dest="security_command", required=True)

    rotate = sp.add_parser("rotate-keys", help="Rotate key version and emit KEY_ROTATED event")
    rotate.add_argument("--tenant", required=True, help="Tenant ID")
    rotate.add_argument("--key-id", required=True, help="Logical key identifier")
    rotate.add_argument("--ttl-days", type=int, default=14, help="Days before key expiry")
    rotate.add_argument("--actor-user", default="system", help="Actor user for audit event")
    rotate.add_argument("--actor-role", default="coherence_steward", help="Actor role for audit event")
    rotate.add_argument("--authority-dri", required=True, help="Approving DRI identity")
    rotate.add_argument("--authority-role", default="dri_approver", help="Approving authority role")
    rotate.add_argument("--authority-reason", required=True, help="Approval rationale")
    rotate.add_argument(
        "--authority-signing-key-env",
        default="DEEPSIGMA_AUTHORITY_SIGNING_KEY",
        help="Env var name containing HMAC key for signed authority events",
    )
    rotate.add_argument(
        "--action-contract-path",
        default=None,
        help="Optional JSON file with signed authority action contract",
    )
    rotate.add_argument(
        "--authority-ledger-path",
        default="data/security/authority_ledger.json",
        help="Path to append authority ledger entries",
    )
    rotate.add_argument("--keyring-path", default="data/security/keyring.json", help="Path to keyring JSON")
    rotate.add_argument(
        "--event-log-path",
        default="data/security/key_rotation_events.jsonl",
        help="Path to append key rotation events",
    )
    rotate.add_argument("--json", action="store_true", help="Output JSON")
    rotate.set_defaults(func=run_rotate)

    reenc = sp.add_parser("reencrypt", help="Re-encrypt tenant evidence using current key")
    reenc.add_argument("--tenant", required=True, help="Tenant ID")
    reenc.add_argument("--data-dir", default=None, help="Optional explicit credibility data directory")
    reenc.add_argument(
        "--checkpoint",
        default="artifacts/checkpoints/reencrypt_checkpoint.json",
        help="Checkpoint path",
    )
    reenc.add_argument("--resume", action="store_true", help="Resume from existing checkpoint")
    reenc.add_argument("--dry-run", action="store_true", help="Plan run without rewriting records")
    reenc.add_argument(
        "--previous-master-key-env",
        default="DEEPSIGMA_PREVIOUS_MASTER_KEY",
        help="Env var containing previous master key",
    )
    reenc.add_argument("--actor-user", default="system", help="Actor user for audit event")
    reenc.add_argument("--actor-role", default="coherence_steward", help="Actor role for audit event")
    reenc.add_argument("--authority-dri", required=True, help="Approving DRI identity")
    reenc.add_argument("--authority-role", default="dri_approver", help="Approving authority role")
    reenc.add_argument("--authority-reason", required=True, help="Approval rationale")
    reenc.add_argument(
        "--authority-signing-key-env",
        default="DEEPSIGMA_AUTHORITY_SIGNING_KEY",
        help="Env var name containing HMAC key for signed authority events",
    )
    reenc.add_argument(
        "--authority-ledger-path",
        default="data/security/authority_ledger.json",
        help="Path to append authority ledger entries",
    )
    reenc.add_argument(
        "--action-contract-path",
        default=None,
        help="Optional JSON file with signed authority action contract",
    )
    reenc.add_argument("--json", action="store_true", help="Output JSON")
    reenc.set_defaults(func=run_reencrypt)


def _load_action_contract(path: str | None) -> dict | None:
    if not path:
        return None
    raw = Path(path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("action contract file must contain a JSON object")
    return payload


def run_rotate(args: argparse.Namespace) -> int:
    signing_key = os.getenv(args.authority_signing_key_env)
    action_contract = _load_action_contract(args.action_contract_path)
    result = rotate_keys(
        tenant_id=args.tenant,
        key_id=args.key_id,
        ttl_days=args.ttl_days,
        actor_user=args.actor_user,
        actor_role=args.actor_role,
        authority_dri=args.authority_dri,
        authority_role=args.authority_role,
        authority_reason=args.authority_reason,
        authority_signing_key=signing_key,
        action_contract=action_contract,
        keyring_path=Path(args.keyring_path),
        event_log_path=Path(args.event_log_path),
        authority_ledger_path=Path(args.authority_ledger_path),
    )
    payload = rotation_result_to_dict(result)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"Key rotated tenant={payload['tenant_id']} key={payload['key_id']} "
            f"version={payload['key_version']} expires_at={payload['expires_at']}"
        )
    return 0


def run_reencrypt(args: argparse.Namespace) -> int:
    signing_key = os.getenv(args.authority_signing_key_env)
    action_contract = _load_action_contract(args.action_contract_path)
    summary = run_reencrypt_job(
        tenant_id=args.tenant,
        dry_run=bool(args.dry_run),
        resume=bool(args.resume),
        data_dir=Path(args.data_dir) if args.data_dir else None,
        checkpoint_path=Path(args.checkpoint),
        previous_master_key_env=args.previous_master_key_env,
        actor_user=args.actor_user,
        actor_role=args.actor_role,
        authority_dri=args.authority_dri,
        authority_role=args.authority_role,
        authority_reason=args.authority_reason,
        authority_signing_key=signing_key,
        action_contract=action_contract,
        authority_ledger_path=Path(args.authority_ledger_path),
    )
    payload = reencrypt_summary_to_dict(summary)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"Reencrypt status={payload['status']} tenant={payload['tenant_id']} "
            f"targeted={payload['records_targeted']} rewritten={payload['records_reencrypted']}"
        )
    return 0
