"""deepsigma retention — evidence lifecycle management."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from credibility_engine.store import CredibilityStore
from credibility_engine.tiering import EvidenceTierManager, TieringPolicy
from deepsigma.cli.compact import compact_directory
from governance.audit import _audit_path, audit_action
from tenancy.policies import load_policy, save_policy

_RETENTION_DEFAULTS = {
    "hot_retention_hours": 24,
    "warm_retention_days": 30,
    "cold_retention_days": 365,
    "audit_retention_days": 2555,
}

_TIERABLE_FILES = [
    CredibilityStore.CLAIMS_FILE,
    CredibilityStore.DRIFT_FILE,
    CredibilityStore.SNAPSHOTS_FILE,
    CredibilityStore.CORRELATION_FILE,
    CredibilityStore.SYNC_FILE,
]


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "retention",
        help="Evidence retention and purge operations",
    )
    retention_sub = p.add_subparsers(dest="retention_command", required=True)

    sweep = retention_sub.add_parser(
        "sweep",
        help="Run tier sweep, cold purge, audit purge, and compaction",
    )
    sweep.add_argument("--tenant", required=True, help="Tenant ID")
    sweep.add_argument(
        "--data-dir",
        default=None,
        help="Optional explicit tenant credibility data dir",
    )
    sweep.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without deleting or rewriting",
    )
    sweep.add_argument("--json", action="store_true", dest="json_output", help="Output JSON")
    sweep.set_defaults(func=run_sweep)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _retention_policy(tenant_id: str) -> dict[str, int]:
    policy = load_policy(tenant_id)
    retention = dict(policy.get("retention_policy", {}))
    changed = False
    for k, v in _RETENTION_DEFAULTS.items():
        if k not in retention:
            retention[k] = v
            changed = True
    if changed:
        policy["retention_policy"] = retention
        save_policy(tenant_id, policy)
    return {k: int(retention[k]) for k in _RETENTION_DEFAULTS}


def _simulate_tier_sweep(
    store: CredibilityStore,
    tier_policy: TieringPolicy,
    now: datetime,
) -> dict[str, Any]:
    mgr = EvidenceTierManager(store, tier_policy)
    promoted = 0
    demoted = 0
    unchanged = 0
    by_tier = {"hot": 0, "warm": 0, "cold": 0}
    files_processed = 0

    for filename in _TIERABLE_FILES:
        hot = store.load_all(filename)
        warm = store.load_warm(filename)
        cold = store.load_cold(filename)
        if not (hot or warm or cold):
            continue
        files_processed += 1

        for prev_tier, bucket in (("hot", hot), ("warm", warm), ("cold", cold)):
            for record in bucket:
                target = mgr.classify(record, now).value
                by_tier[target] += 1
                if target == prev_tier:
                    unchanged += 1
                elif (prev_tier == "hot" and target in {"warm", "cold"}) or (
                    prev_tier == "warm" and target == "cold"
                ):
                    demoted += 1
                else:
                    promoted += 1

    return {
        "promoted": promoted,
        "demoted": demoted,
        "unchanged": unchanged,
        "by_tier": by_tier,
        "files_processed": files_processed,
    }


def _purge_expired_cold(
    store: CredibilityStore,
    tenant_id: str,
    cutoff: datetime,
    dry_run: bool,
) -> dict[str, int]:
    summary: dict[str, int] = {}
    for filename in _TIERABLE_FILES:
        cold_records = store.load_cold(filename)
        if not cold_records:
            continue
        kept: list[dict[str, Any]] = []
        deleted = 0
        for r in cold_records:
            ts = _parse_iso(str(r.get("timestamp", "")))
            if ts is not None and ts < cutoff:
                deleted += 1
            else:
                kept.append(r)
        if deleted:
            summary[filename] = deleted
            if not dry_run:
                store.write_cold(filename, kept)
                audit_action(
                    tenant_id=tenant_id,
                    actor_user="system",
                    actor_role="coherence_steward",
                    action="RETENTION_PURGE",
                    target_type="EVIDENCE",
                    target_id=filename,
                    outcome="SUCCESS",
                    metadata={
                        "tier": "cold",
                        "deleted_count": deleted,
                        "cutoff": cutoff.isoformat(),
                    },
                )
    return summary


def _purge_expired_audit(
    tenant_id: str,
    cutoff: datetime,
    dry_run: bool,
) -> int:
    path = _audit_path(tenant_id)
    if not path.exists():
        return 0

    lines = path.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    deleted = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        ts = _parse_iso(str(obj.get("timestamp", "")))
        if ts is not None and ts < cutoff:
            deleted += 1
        else:
            kept.append(line)

    if deleted and not dry_run:
        path.write_text(("\n".join(kept) + "\n") if kept else "", encoding="utf-8")
        audit_action(
            tenant_id=tenant_id,
            actor_user="system",
            actor_role="coherence_steward",
            action="RETENTION_PURGE",
            target_type="AUDIT",
            target_id="audit.jsonl",
            outcome="SUCCESS",
            metadata={
                "deleted_count": deleted,
                "cutoff": cutoff.isoformat(),
            },
        )
    return deleted


def run_sweep(args: argparse.Namespace) -> int:
    now = _now()
    tenant_id = args.tenant
    retention = _retention_policy(tenant_id)

    hot_hours = retention["hot_retention_hours"]
    warm_days = retention["warm_retention_days"]
    cold_days = retention["cold_retention_days"]
    audit_days = retention["audit_retention_days"]

    data_dir = Path(args.data_dir) if args.data_dir else None
    store = CredibilityStore(data_dir=data_dir, tenant_id=tenant_id)
    tier_policy = TieringPolicy(
        hot_max_age_minutes=hot_hours * 60,
        warm_max_age_minutes=(hot_hours * 60) + (warm_days * 1440),
        ttl_expiry_demotes=True,
        cold_excludes_scoring=True,
    )

    if args.dry_run:
        sweep_summary = _simulate_tier_sweep(store, tier_policy, now)
    else:
        sweep_summary = EvidenceTierManager(store, tier_policy).sweep(now).to_dict()

    cold_cutoff = now - timedelta(days=cold_days)
    cold_purge = _purge_expired_cold(
        store=store,
        tenant_id=tenant_id,
        cutoff=cold_cutoff,
        dry_run=args.dry_run,
    )

    audit_cutoff = now - timedelta(days=audit_days)
    audit_purged = _purge_expired_audit(
        tenant_id=tenant_id,
        cutoff=audit_cutoff,
        dry_run=args.dry_run,
    )

    compaction = compact_directory(
        store.data_dir,
        retention_days=max(1, hot_hours // 24),
        warm_days=warm_days,
        dry_run=args.dry_run,
    )

    output = {
        "tenant_id": tenant_id,
        "dry_run": bool(args.dry_run),
        "retention_policy": retention,
        "tier_sweep": sweep_summary,
        "cold_purge": {
            "cutoff": cold_cutoff.isoformat(),
            "by_file": cold_purge,
            "deleted_total": sum(cold_purge.values()),
        },
        "audit_purge": {
            "cutoff": audit_cutoff.isoformat(),
            "deleted": audit_purged,
        },
        "compaction": compaction,
    }

    if args.json_output:
        print(json.dumps(output, indent=2))
    else:
        mode = "DRY RUN" if args.dry_run else "APPLIED"
        print(f"Retention sweep ({mode}) for tenant={tenant_id}")
        print(
            "Policy:"
            f" hot={hot_hours}h warm={warm_days}d cold={cold_days}d audit={audit_days}d"
        )
        print(
            "Tier sweep:"
            f" demoted={sweep_summary['demoted']} promoted={sweep_summary['promoted']}"
            f" unchanged={sweep_summary['unchanged']}"
        )
        print(f"Cold purge deleted: {sum(cold_purge.values())}")
        print(f"Audit purge deleted: {audit_purged}")
        print(f"Compaction files processed: {len(compaction)}")
    return 0
