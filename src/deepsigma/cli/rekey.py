"""deepsigma rekey — rotate encrypted credibility evidence keys."""
from __future__ import annotations

import argparse
import json
import os

from credibility_engine.store import CredibilityStore


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "rekey",
        help="Re-encrypt tenant credibility evidence with current master key",
    )
    p.add_argument("--tenant", required=True, help="Tenant ID to rekey")
    p.add_argument(
        "--data-dir",
        default=None,
        help="Optional explicit credibility data directory",
    )
    p.add_argument(
        "--previous-master-key-env",
        default="DEEPSIGMA_PREVIOUS_MASTER_KEY",
        help="Env var name containing previous master key",
    )
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    previous_key = os.environ.get(args.previous_master_key_env, "")
    if not previous_key:
        print(
            f"Missing previous key: set ${args.previous_master_key_env}",
        )
        return 2

    if not os.environ.get("DEEPSIGMA_MASTER_KEY", ""):
        print("Missing current key: set $DEEPSIGMA_MASTER_KEY")
        return 2

    store = CredibilityStore(
        data_dir=args.data_dir,
        tenant_id=args.tenant,
        encrypt_at_rest=True,
    )
    stats = store.rekey(previous_master_key=previous_key)
    out = {
        "tenant_id": args.tenant,
        "files_rewritten": stats["files"],
        "records_reencrypted": stats["records"],
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(
            f"Rekey complete for tenant={args.tenant}: "
            f"files={stats['files']} records={stats['records']}"
        )
    return 0
