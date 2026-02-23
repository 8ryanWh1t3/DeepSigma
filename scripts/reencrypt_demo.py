#!/usr/bin/env python3
"""Run a deterministic DISR rotation + reencrypt dry-run demo."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

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
    records_targeted = sum(1 for line in claims_path.read_text(encoding="utf-8").splitlines() if line.strip())
    bytes_targeted = claims_path.stat().st_size

    signing_key = os.getenv("DEEPSIGMA_AUTHORITY_SIGNING_KEY", "demo-signing-key")
    signing_key_source = "env" if os.getenv("DEEPSIGMA_AUTHORITY_SIGNING_KEY") else "placeholder_default"
    compromise_started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    t0 = time.perf_counter()
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
        security_events_path=out_dir / "security_events.jsonl",
    )
    rotation_completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    reencrypt = run_reencrypt_job(
        tenant_id=args.tenant,
        dry_run=True,
        resume=False,
        data_dir=data_dir,
        checkpoint_path=out_dir / "reencrypt_checkpoint.json",
        actor_user="demo-operator",
        actor_role="coherence_steward",
        authority_dri="demo.dri",
        authority_reason="DISR 10-minute demo approval",
        authority_signing_key=signing_key,
        authority_ledger_path=out_dir / "authority_ledger.json",
        security_events_path=out_dir / "security_events.jsonl",
    )
    recovery_completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    elapsed_seconds = max(time.perf_counter() - t0, 0.001)
    records_per_second = records_targeted / elapsed_seconds
    mb_per_minute = (bytes_targeted / (1024 * 1024)) / (elapsed_seconds / 60.0)

    metrics = {
        "schema_version": "1.0",
        "metric_family": "disr_security",
        "execution_mode": "dry_run",
        "evidence_level": "simulated",
        "kpi_eligible": False,
        "tenant_id": args.tenant,
        "compromise_started_at": compromise_started_at,
        "rotation_completed_at": rotation_completed_at,
        "recovery_completed_at": recovery_completed_at,
        "mttr_seconds": round(elapsed_seconds, 3),
        "records_targeted": records_targeted,
        "bytes_targeted": bytes_targeted,
        "reencrypt_records_per_second": round(records_per_second, 3),
        "reencrypt_mb_per_minute": round(mb_per_minute, 6),
        "signing_mode": "hmac",
        "signing_key_source": signing_key_source,
        "signing_notice": "Pilot signing key may be placeholder unless DEEPSIGMA_AUTHORITY_SIGNING_KEY is set.",
    }
    kpi_metrics_path = ROOT / "release_kpis" / "security_metrics.json"
    kpi_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    kpi_metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    summary = {
        "rotation": rotation_result_to_dict(rotation),
        "reencrypt": reencrypt_summary_to_dict(reencrypt),
        "metrics": metrics,
        "outputs": {
            "keyring": str(out_dir / "keyring.json"),
            "events": str(out_dir / "key_rotation_events.jsonl"),
            "authority_ledger": str(out_dir / "authority_ledger.json"),
            "security_events": str(out_dir / "security_events.jsonl"),
            "checkpoint": str(out_dir / "reencrypt_checkpoint.json"),
            "security_metrics": str(kpi_metrics_path),
        },
    }
    report_path = out_dir / "disr_demo_summary.json"
    report_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
