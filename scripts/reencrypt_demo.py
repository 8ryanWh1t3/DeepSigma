#!/usr/bin/env python3
"""Run a deterministic DISR rotation + reencrypt dry-run demo."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepsigma.security.reencrypt import reencrypt_summary_to_dict, run_reencrypt_job  # noqa: E402
from deepsigma.security.rotate_keys import rotate_keys, rotation_result_to_dict  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="DISR 10-minute demo: rotate + reencrypt dry-run")
    parser.add_argument("--tenant", default="tenant-alpha", help="Tenant ID")
    parser.add_argument("--key-id", default="credibility", help="Logical key id")
    parser.add_argument("--ttl-days", type=int, default=14, help="Rotation TTL in days")
    parser.add_argument(
        "--out-dir",
        default="artifacts/disr_demo",
        help="Output directory for demo fixtures and reports",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    data_dir = out_dir / "cred"
    data_dir.mkdir(parents=True, exist_ok=True)
    claims_path = data_dir / "claims.jsonl"
    claims_path.write_text(
        (
            '{"tenant_id":"tenant-alpha","nonce":"AAAAAAAAAAAAAAAA","encrypted_payload":"BBBB",'
            '"key_id":"credibility","key_version":1,"alg":"AES-256-GCM","aad":"tenant-alpha"}\n'
        ),
        encoding="utf-8",
    )

    signing_key = os.getenv("DEEPSIGMA_AUTHORITY_SIGNING_KEY", "demo-signing-key")
    rotation = rotate_keys(
        tenant_id=args.tenant,
        key_id=args.key_id,
        ttl_days=args.ttl_days,
        actor_user="demo-operator",
        actor_role="coherence_steward",
        authority_dri="demo.dri",
        authority_role="dri_approver",
        authority_reason="DISR 10-minute demo approval",
        authority_signing_key=signing_key,
        keyring_path=out_dir / "keyring.json",
        event_log_path=out_dir / "key_rotation_events.jsonl",
        authority_ledger_path=out_dir / "authority_ledger.json",
    )
    reencrypt = run_reencrypt_job(
        tenant_id=args.tenant,
        dry_run=True,
        resume=False,
        data_dir=data_dir,
        checkpoint_path=out_dir / "reencrypt_checkpoint.json",
        actor_user="demo-operator",
        actor_role="coherence_steward",
    )

    summary = {
        "rotation": rotation_result_to_dict(rotation),
        "reencrypt": reencrypt_summary_to_dict(reencrypt),
        "outputs": {
            "keyring": str(out_dir / "keyring.json"),
            "events": str(out_dir / "key_rotation_events.jsonl"),
            "authority_ledger": str(out_dir / "authority_ledger.json"),
            "checkpoint": str(out_dir / "reencrypt_checkpoint.json"),
        },
    }
    report_path = out_dir / "disr_demo_summary.json"
    report_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
