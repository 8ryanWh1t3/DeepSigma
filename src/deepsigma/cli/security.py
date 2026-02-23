"""deepsigma security — DISR security operations."""

from __future__ import annotations

import argparse
import json
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
    reenc.add_argument("--json", action="store_true", help="Output JSON")
    reenc.set_defaults(func=run_reencrypt)


def run_rotate(args: argparse.Namespace) -> int:
    result = rotate_keys(
        tenant_id=args.tenant,
        key_id=args.key_id,
        ttl_days=args.ttl_days,
        actor_user=args.actor_user,
        actor_role=args.actor_role,
        keyring_path=Path(args.keyring_path),
        event_log_path=Path(args.event_log_path),
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
    summary = run_reencrypt_job(
        tenant_id=args.tenant,
        dry_run=bool(args.dry_run),
        resume=bool(args.resume),
        data_dir=Path(args.data_dir) if args.data_dir else None,
        checkpoint_path=Path(args.checkpoint),
        previous_master_key_env=args.previous_master_key_env,
        actor_user=args.actor_user,
        actor_role=args.actor_role,
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
