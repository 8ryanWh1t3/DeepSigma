"""Re-encryption job primitive with checkpoint and resume semantics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from credibility_engine.store import CredibilityStore
from governance.audit import audit_action


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ReencryptSummary:
    tenant_id: str
    dry_run: bool
    resumed: bool
    checkpoint_path: str
    files_targeted: int
    records_targeted: int
    files_rewritten: int
    records_reencrypted: int
    status: str



def _count_records(path: Path) -> int:
    if path.suffix == ".jsonl":
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    if path.suffix == ".json":
        return 1
    return 0


def _target_files(store: CredibilityStore) -> list[Path]:
    files = []
    for path in sorted(store.data_dir.glob("*")):
        if path.is_dir():
            continue
        if path.name == store.PACKET_FILE:
            continue
        if path.suffix in {".json", ".jsonl"}:
            files.append(path)
    return files


def _write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_reencrypt_job(
    *,
    tenant_id: str,
    dry_run: bool,
    resume: bool,
    data_dir: str | Path | None = None,
    checkpoint_path: str | Path = "artifacts/checkpoints/reencrypt_checkpoint.json",
    previous_master_key_env: str = "DEEPSIGMA_PREVIOUS_MASTER_KEY",
    actor_user: str = "system",
    actor_role: str = "coherence_steward",
) -> ReencryptSummary:
    checkpoint = Path(checkpoint_path)

    if resume and checkpoint.exists():
        prior = json.loads(checkpoint.read_text(encoding="utf-8"))
        if prior.get("status") == "completed":
            return ReencryptSummary(
                tenant_id=tenant_id,
                dry_run=dry_run,
                resumed=True,
                checkpoint_path=str(checkpoint),
                files_targeted=int(prior.get("files_targeted", 0)),
                records_targeted=int(prior.get("records_targeted", 0)),
                files_rewritten=int(prior.get("files_rewritten", 0)),
                records_reencrypted=int(prior.get("records_reencrypted", 0)),
                status="completed",
            )

    store = CredibilityStore(data_dir=data_dir, tenant_id=tenant_id, encrypt_at_rest=True)
    targets = _target_files(store)
    files_targeted = len(targets)
    records_targeted = sum(_count_records(path) for path in targets)

    if dry_run:
        payload = {
            "tenant_id": tenant_id,
            "status": "dry_run",
            "updated_at": _utc_now_iso(),
            "files_targeted": files_targeted,
            "records_targeted": records_targeted,
            "files_rewritten": 0,
            "records_reencrypted": 0,
        }
        _write_checkpoint(checkpoint, payload)
        return ReencryptSummary(
            tenant_id=tenant_id,
            dry_run=True,
            resumed=False,
            checkpoint_path=str(checkpoint),
            files_targeted=files_targeted,
            records_targeted=records_targeted,
            files_rewritten=0,
            records_reencrypted=0,
            status="dry_run",
        )

    previous_master_key = os.environ.get(previous_master_key_env, "")
    if not previous_master_key:
        raise RuntimeError(f"Missing previous key: set ${previous_master_key_env}")
    if not os.environ.get("DEEPSIGMA_MASTER_KEY", ""):
        raise RuntimeError("Missing current key: set $DEEPSIGMA_MASTER_KEY")

    stats = store.rekey(previous_master_key=previous_master_key)

    payload = {
        "tenant_id": tenant_id,
        "status": "completed",
        "updated_at": _utc_now_iso(),
        "files_targeted": files_targeted,
        "records_targeted": records_targeted,
        "files_rewritten": int(stats.get("files", 0)),
        "records_reencrypted": int(stats.get("records", 0)),
    }
    _write_checkpoint(checkpoint, payload)

    audit_action(
        tenant_id=tenant_id,
        actor_user=actor_user,
        actor_role=actor_role,
        action="REENCRYPT_COMPLETED",
        target_type="EVIDENCE",
        target_id=tenant_id,
        outcome="SUCCESS",
        metadata={
            "files_rewritten": payload["files_rewritten"],
            "records_reencrypted": payload["records_reencrypted"],
            "checkpoint_path": str(checkpoint),
        },
    )

    return ReencryptSummary(
        tenant_id=tenant_id,
        dry_run=False,
        resumed=False,
        checkpoint_path=str(checkpoint),
        files_targeted=files_targeted,
        records_targeted=records_targeted,
        files_rewritten=payload["files_rewritten"],
        records_reencrypted=payload["records_reencrypted"],
        status="completed",
    )


def reencrypt_summary_to_dict(summary: ReencryptSummary) -> dict[str, Any]:
    return asdict(summary)
