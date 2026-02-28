"""deepsigma compliance export — SOC 2 evidence package generator."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from credibility_engine.store import CredibilityStore
from governance import audit as audit_mod
from tenancy import policies as policy_mod

REPO_ROOT = Path(__file__).resolve().parents[3]
TENANT_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "tenants.json"
VALID_ROLES = ("truth_owner", "coherence_steward", "dri", "exec")
REDACTED = "[REDACTED]"
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

PII_KEYS = {
    "actor_user",
    "user",
    "updated_by",
    "author",
    "email",
    "assignee",
    "owner",
}


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "compliance",
        help="Compliance report and evidence export operations",
    )
    sub = p.add_subparsers(dest="compliance_command", required=True)

    export = sub.add_parser(
        "export",
        help="Export SOC 2 evidence package for a tenant and date window",
    )
    export.add_argument("--tenant", required=True, help="Tenant ID")
    export.add_argument("--from", dest="from_date", required=True, help="Start date YYYY-MM-DD")
    export.add_argument("--to", dest="to_date", required=True, help="End date YYYY-MM-DD")
    export.add_argument("--out", required=True, help="Output directory")
    export.add_argument(
        "--redact",
        action="store_true",
        help="Strip user identifiers from export artifacts",
    )
    export.add_argument("--json", action="store_true", help="Print run summary as JSON")
    export.add_argument(
        "--encrypt",
        action="store_true",
        help="Encrypt output artifacts at rest (requires DEEPSIGMA_ENCRYPTION_KEY)",
    )
    export.add_argument(
        "--schedule",
        metavar="DAYS",
        type=int,
        help="Auto-export mode: export the last N days of evidence (cron-friendly)",
    )
    export.set_defaults(func=run_export)


def run_export(args: argparse.Namespace) -> int:
    # --schedule N: auto-compute date window as last N days
    if getattr(args, "schedule", None):
        today = date.today()
        from_dt = today - __import__("datetime").timedelta(days=args.schedule)
        to_dt = today
        if not args.from_date:
            args.from_date = from_dt.isoformat()
        if not args.to_date:
            args.to_date = to_dt.isoformat()
    from_dt = _parse_date(args.from_date, flag="--from")
    to_dt = _parse_date(args.to_date, flag="--to")
    if from_dt > to_dt:
        raise ValueError("--from must be <= --to")

    tenant_id = args.tenant
    tenant = _load_tenant_or_raise(tenant_id)

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    audit_events = _load_audit_events(tenant_id, from_dt, to_dt)
    seal_chain, packet_latest = _load_seal_chain(tenant_id, from_dt, to_dt)
    policy_snapshots = _load_policy_snapshots(tenant_id, from_dt, to_dt)
    scorecards = _load_trust_scorecards(from_dt, to_dt)
    tenant_config = _build_tenant_config(tenant_id, tenant)

    if args.redact:
        audit_events = _redact_obj(audit_events)
        seal_chain = _redact_obj(seal_chain)
        packet_latest = _redact_obj(packet_latest)
        policy_snapshots = _redact_obj(policy_snapshots)
        scorecards = _redact_obj(scorecards)
        tenant_config = _redact_obj(tenant_config)

    _write_json(out_dir / "audit_log.json", audit_events)
    _write_audit_csv(out_dir / "audit_log.csv", audit_events)
    _write_json(
        out_dir / "sealed_packet_chain.json",
        {"entries": seal_chain, "latest_packet": packet_latest},
    )
    _write_json(out_dir / "policy_snapshots.json", policy_snapshots)
    _write_json(out_dir / "trust_scorecard_history.json", scorecards)
    _write_json(out_dir / "tenant_configuration.json", tenant_config)

    connectors = _discover_connectors()
    diagram = _build_data_flow_diagram(connectors)
    (out_dir / "data_flow_diagram.mmd").write_text(diagram, encoding="utf-8")
    _write_summary(
        out_dir=out_dir,
        tenant_id=tenant_id,
        from_dt=from_dt,
        to_dt=to_dt,
        redact=args.redact,
        counts={
            "audit_events": len(audit_events),
            "seal_entries": len(seal_chain),
            "policy_snapshots": len(policy_snapshots),
            "scorecards": len(scorecards),
            "connectors": len(connectors),
        },
    )

    # --encrypt: encrypt all output artifacts at rest
    encrypted_files: list[str] = []
    if getattr(args, "encrypt", False):
        from governance.encryption import FileEncryptor

        enc = FileEncryptor()
        if enc.enabled:
            for child in out_dir.iterdir():
                if child.is_file() and not child.name.endswith(".enc"):
                    enc.encrypt_file(child)
                    encrypted_files.append(child.name + ".enc")

    result = {
        "tenant_id": tenant_id,
        "window": {"from": from_dt.date().isoformat(), "to": to_dt.date().isoformat()},
        "output_dir": str(out_dir),
        "redacted": bool(args.redact),
        "encrypted": bool(encrypted_files),
        "files": [
            "audit_log.json",
            "audit_log.csv",
            "sealed_packet_chain.json",
            "policy_snapshots.json",
            "trust_scorecard_history.json",
            "tenant_configuration.json",
            "data_flow_diagram.mmd",
            "compliance_summary.md",
        ] + encrypted_files,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Compliance export complete for tenant={tenant_id}")
        print(f"Window: {result['window']['from']} -> {result['window']['to']}")
        print(f"Output: {out_dir}")
        for file_name in result["files"]:
            print(f"  - {file_name}")
    return 0


def _parse_date(raw: str, flag: str) -> datetime:
    try:
        d = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {flag} date: {raw}. Expected YYYY-MM-DD") from exc
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _in_window(ts: datetime | None, from_dt: datetime, to_dt: datetime) -> bool:
    if ts is None:
        return False
    end = to_dt.replace(hour=23, minute=59, second=59)
    return from_dt <= ts <= end


def _load_audit_events(tenant_id: str, from_dt: datetime, to_dt: datetime) -> list[dict[str, Any]]:
    path = audit_mod._audit_path(tenant_id)
    if not path.exists():
        return []

    selected: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if _in_window(_parse_ts(event.get("timestamp")), from_dt, to_dt):
            selected.append(event)
    return selected


def _load_seal_chain(
    tenant_id: str,
    from_dt: datetime,
    to_dt: datetime,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    store = CredibilityStore(tenant_id=tenant_id)
    chain = []
    for rec in store.load_all("seal_chain.jsonl"):
        if _in_window(_parse_ts(rec.get("sealed_at")), from_dt, to_dt):
            chain.append(rec)
    return chain, store.latest_packet()


def _load_policy_snapshots(
    tenant_id: str,
    from_dt: datetime,
    to_dt: datetime,
) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    policy = policy_mod.load_policy(tenant_id)
    updated_at = _parse_ts(policy.get("updated_at"))
    if _in_window(updated_at, from_dt, to_dt):
        snapshots.append(
            {
                "source": str(policy_mod._policy_path(tenant_id)),
                "updated_at": policy.get("updated_at"),
                "updated_by": policy.get("updated_by", "unknown"),
                "policy_hash": policy_mod.get_policy_hash(policy),
                "policy": policy,
            }
        )

    for event in _load_audit_events(tenant_id, from_dt, to_dt):
        if event.get("action") != "POLICY_UPDATE":
            continue
        snapshots.append(
            {
                "source": "audit_event",
                "timestamp": event.get("timestamp"),
                "actor_user": event.get("actor_user"),
                "metadata": event.get("metadata", {}),
            }
        )
    return snapshots


def _load_trust_scorecards(from_dt: datetime, to_dt: datetime) -> list[dict[str, Any]]:
    candidates: list[Path] = []
    for p in REPO_ROOT.rglob("trust_scorecard*.json"):
        if ".git" in p.parts or "node_modules" in p.parts:
            continue
        candidates.append(p)

    rows: list[dict[str, Any]] = []
    for path in sorted(set(candidates)):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ts = _parse_ts(obj.get("timestamp"))
        if ts is None:
            try:
                ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                ts = None
        if _in_window(ts, from_dt, to_dt):
            rows.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "timestamp": ts.isoformat().replace("+00:00", "Z") if ts else None,
                    "scorecard": obj,
                }
            )
    return rows


def _build_tenant_config(tenant_id: str, tenant: dict[str, Any]) -> dict[str, Any]:
    cred_store = CredibilityStore(tenant_id=tenant_id)
    policy = policy_mod.load_policy(tenant_id)
    return {
        "tenant": tenant,
        "rbac": {
            "valid_roles": sorted(VALID_ROLES),
            "model": "header-based (X-Role, X-User)",
        },
        "data_paths": {
            "credibility_dir": str(cred_store.data_dir),
            "audit_log": str(audit_mod._audit_path(tenant_id)),
            "policy_file": str(policy_mod._policy_path(tenant_id)),
        },
        "retention": policy.get("retention_policy", {}),
    }


def _load_tenant_or_raise(tenant_id: str) -> dict[str, Any]:
    tenants = _load_tenant_registry()
    for tenant in tenants:
        if tenant.get("tenant_id") == tenant_id:
            return tenant
    raise ValueError(f"Tenant not found: {tenant_id}")


def _load_tenant_registry() -> list[dict[str, Any]]:
    if not TENANT_REGISTRY_PATH.exists():
        return []
    try:
        data = json.loads(TENANT_REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _discover_connectors() -> list[str]:
    adapters = REPO_ROOT / "src" / "adapters"
    if not adapters.exists():
        return []
    names: list[str] = []
    for child in sorted(adapters.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_") or child.name in {"__pycache__", "testing"}:
            continue
        if any((child / fname).exists() for fname in ("connector.py", "README.md", "__init__.py")):
            names.append(child.name)
    return names


def _build_data_flow_diagram(connectors: list[str]) -> str:
    lines = [
        "flowchart LR",
        '  A["Connectors"] --> B["Normalize + Extract"]',
        '  B --> C["Seal Packet Chain"]',
        '  C --> D["Drift + Patch Governance"]',
        '  D --> E["Trust Scorecard"]',
    ]
    for i, connector in enumerate(connectors, start=1):
        safe = re.sub(r"[^A-Za-z0-9_]", "_", connector)
        lines.append(f'  C{i}["{connector}"] --> A')
        lines.append(f"  C{i}:::connector")
        lines.append(f"  class C{i} connector")
        lines.append(f"  %% connector_id: {safe}")
    lines.append("  classDef connector fill:#e3f2fd,stroke:#1565c0,stroke-width:1px")
    return "\n".join(lines) + "\n"


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def _write_audit_csv(path: Path, events: list[dict[str, Any]]) -> None:
    fields = [
        "timestamp",
        "audit_id",
        "tenant_id",
        "actor_user",
        "actor_role",
        "action",
        "target_type",
        "target_id",
        "outcome",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for event in events:
            writer.writerow({k: event.get(k, "") for k in fields})


def _write_summary(
    out_dir: Path,
    tenant_id: str,
    from_dt: datetime,
    to_dt: datetime,
    redact: bool,
    counts: dict[str, int],
) -> None:
    mapping = [
        ("CC6.1 Logical Access Controls", "RBAC model + audit trail in tenant_configuration + audit_log"),
        ("CC7.2 Change Management", "Policy update and packet seal events in audit_log + sealed_packet_chain"),
        ("CC7.3 Monitoring", "Trust scorecard history + drift/patch governance artifacts"),
        ("CC8.1 Data Protection", "Retention policy + optional redaction mode in export flow"),
    ]
    gaps = [
        "External attestation evidence (vendor SOC reports, pen tests) is out-of-repo.",
        "Historical policy versions depend on retained snapshots/audit logs in tenant data.",
        "Infrastructure-level controls (SSO, IdP MFA, ticketing approvals) require external system evidence.",
    ]

    lines = [
        "# Compliance Summary (SOC 2 Evidence Export)",
        "",
        f"- Tenant: `{tenant_id}`",
        f"- Window: `{from_dt.date().isoformat()}` to `{to_dt.date().isoformat()}`",
        f"- Redaction: `{str(redact).lower()}`",
        "- Export mode: read-only extracts (no source mutation).",
        "",
        "## Export Inventory",
        f"- Audit events: **{counts['audit_events']}** (`audit_log.json`, `audit_log.csv`)",
        f"- Sealed chain entries: **{counts['seal_entries']}** (`sealed_packet_chain.json`)",
        f"- Policy snapshots/events: **{counts['policy_snapshots']}** (`policy_snapshots.json`)",
        f"- Trust scorecards: **{counts['scorecards']}** (`trust_scorecard_history.json`)",
        f"- Active connectors discovered: **{counts['connectors']}** (`data_flow_diagram.mmd`)",
        "",
        "## Control Mapping",
    ]
    for control, evidence in mapping:
        lines.append(f"- **{control}**: {evidence}")

    lines.extend(["", "## Gap Analysis"])
    for gap in gaps:
        lines.append(f"- {gap}")

    lines.extend(
        [
            "",
            "## Data Flow Diagram",
            "- See `data_flow_diagram.mmd` for auto-generated connector flow.",
            "",
        ]
    )
    (out_dir / "compliance_summary.md").write_text("\n".join(lines), encoding="utf-8")


def _redact_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        redacted: dict[str, Any] = {}
        for key, value in obj.items():
            lowered = str(key).lower()
            if lowered in PII_KEYS or lowered.endswith("_user") or lowered.endswith("_email"):
                redacted[key] = REDACTED
            else:
                redacted[key] = _redact_obj(value)
        return redacted
    if isinstance(obj, list):
        return [_redact_obj(item) for item in obj]
    if isinstance(obj, str):
        if EMAIL_RE.search(obj):
            return EMAIL_RE.sub(REDACTED, obj)
        if _looks_like_user_id(obj):
            return REDACTED
    return obj


def _looks_like_user_id(value: str) -> bool:
    if value in {"anonymous", "system"}:
        return False
    if value.lower().startswith(("user-", "usr-", "svc-")):
        return True
    if len(value) > 8 and re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return digest.startswith(("0", "1")) and "_" in value
    return False
