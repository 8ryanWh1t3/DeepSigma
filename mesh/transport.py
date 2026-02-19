"""Mesh Transport — HTTP push/pull replication and FastAPI router.

Minimal FastAPI router under /mesh/* prefix for inter-node communication.
Push/pull helpers for append-only log replication.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mesh.logstore import append_jsonl, load_json, load_since, write_json

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------

_BASE_DATA_DIR = Path(__file__).parent.parent / "data" / "mesh"


def _node_dir(tenant_id: str, node_id: str) -> Path:
    return _BASE_DATA_DIR / tenant_id / node_id


def _log_path(tenant_id: str, node_id: str, log_name: str) -> Path:
    return _node_dir(tenant_id, node_id) / log_name


# Log file names
ENVELOPES_LOG = "envelopes.jsonl"
VALIDATIONS_LOG = "validations.jsonl"
AGGREGATES_LOG = "aggregates.jsonl"
SEAL_CHAIN_MIRROR_LOG = "seal_chain_mirror.jsonl"
REPLICATION_LOG = "replication.jsonl"
NODE_STATUS_FILE = "node_status.json"

LOG_FILES = [
    ENVELOPES_LOG,
    VALIDATIONS_LOG,
    AGGREGATES_LOG,
    SEAL_CHAIN_MIRROR_LOG,
    REPLICATION_LOG,
]


# ---------------------------------------------------------------------------
# Push/pull helpers (used by node runtime)
# ---------------------------------------------------------------------------

def push_records(
    tenant_id: str,
    target_node_id: str,
    log_name: str,
    records: list[dict],
) -> int:
    """Push records to a target node's log (local write for MVP)."""
    path = _log_path(tenant_id, target_node_id, log_name)
    written = 0
    for rec in records:
        append_jsonl(path, rec)
        written += 1
    return written


def pull_records(
    tenant_id: str,
    source_node_id: str,
    log_name: str,
    since: str = "",
) -> list[dict]:
    """Pull records from a source node's log since a given time."""
    path = _log_path(tenant_id, source_node_id, log_name)
    if since:
        return load_since(path, since)
    from mesh.logstore import load_all
    return load_all(path)


def get_node_status(tenant_id: str, node_id: str) -> dict | None:
    """Read node status."""
    path = _node_dir(tenant_id, node_id) / NODE_STATUS_FILE
    return load_json(path)


def set_node_status(tenant_id: str, node_id: str, status: dict) -> None:
    """Write node status."""
    path = _node_dir(tenant_id, node_id) / NODE_STATUS_FILE
    write_json(path, status)


def ensure_node_dirs(tenant_id: str, node_id: str) -> Path:
    """Create node data directory."""
    d = _node_dir(tenant_id, node_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Replication event logging
# ---------------------------------------------------------------------------

def log_replication(
    tenant_id: str,
    node_id: str,
    direction: str,
    peer_id: str,
    log_name: str,
    count: int,
) -> None:
    """Log a replication event."""
    path = _log_path(tenant_id, node_id, REPLICATION_LOG)
    append_jsonl(path, {
        "node_id": node_id,
        "direction": direction,
        "peer_id": peer_id,
        "log_name": log_name,
        "record_count": count,
    })


# ---------------------------------------------------------------------------
# FastAPI Router (for API server integration)
# ---------------------------------------------------------------------------

def create_mesh_router():
    """Create FastAPI router for mesh endpoints.

    Returns an APIRouter with push/pull/status endpoints.
    """
    from fastapi import APIRouter, Request

    router = APIRouter(tags=["mesh"])

    @router.post("/mesh/{tenant_id}/{node_id}/push")
    async def mesh_push(
        tenant_id: str,
        node_id: str,
        request: Request,
    ) -> dict[str, Any]:
        """Receive pushed records from a peer node."""
        body = await request.json()
        counts = {}
        for log_name in LOG_FILES:
            key = log_name.replace(".jsonl", "")
            records = body.get(key, [])
            if records:
                written = push_records(tenant_id, node_id, log_name, records)
                counts[key] = written
        return {"status": "ok", "received": counts}

    @router.get("/mesh/{tenant_id}/{node_id}/pull")
    def mesh_pull(
        tenant_id: str,
        node_id: str,
        since: str = "",
    ) -> dict[str, Any]:
        """Pull records from this node's logs since a given time."""
        result = {}
        for log_name in LOG_FILES:
            key = log_name.replace(".jsonl", "")
            result[key] = pull_records(tenant_id, node_id, log_name, since)
        return {"status": "ok", "records": result}

    @router.get("/mesh/{tenant_id}/{node_id}/status")
    def mesh_node_status(
        tenant_id: str,
        node_id: str,
    ) -> dict[str, Any]:
        """Return node status."""
        status = get_node_status(tenant_id, node_id)
        if status is None:
            return {"status": "unknown", "node_id": node_id}
        return status

    @router.get("/mesh/{tenant_id}/summary")
    def mesh_summary(tenant_id: str) -> dict[str, Any]:
        """Return mesh summary for a tenant.

        Aggregates node statuses, last aggregate, last seal,
        and basic verification health.
        """
        tenant_dir = _BASE_DATA_DIR / tenant_id
        if not tenant_dir.exists():
            return {
                "tenant_id": tenant_id,
                "status": "not_initialized",
                "nodes": [],
            }

        nodes = []
        last_aggregate = None
        last_seal = None
        total_envelopes = 0
        total_validations = 0

        for node_dir in sorted(tenant_dir.iterdir()):
            if not node_dir.is_dir():
                continue
            nid = node_dir.name
            status = get_node_status(tenant_id, nid)
            if status:
                nodes.append(status)

            # Check aggregates
            from mesh.logstore import load_last_n as _load_n
            aggs = _load_n(
                _log_path(tenant_id, nid, AGGREGATES_LOG), 1,
            )
            if aggs:
                if last_aggregate is None or \
                   aggs[-1].get("timestamp", "") > last_aggregate.get("timestamp", ""):
                    last_aggregate = aggs[-1]

            # Check seal chain mirror
            seals = _load_n(
                _log_path(tenant_id, nid, SEAL_CHAIN_MIRROR_LOG), 1,
            )
            if seals:
                if last_seal is None or \
                   seals[-1].get("timestamp", "") > last_seal.get("timestamp", ""):
                    last_seal = seals[-1]

            # Count envelopes/validations
            from mesh.logstore import load_all as _load_all
            total_envelopes += len(
                _load_all(_log_path(tenant_id, nid, ENVELOPES_LOG))
            )
            total_validations += len(
                _load_all(_log_path(tenant_id, nid, VALIDATIONS_LOG))
            )

        return {
            "tenant_id": tenant_id,
            "status": "active" if nodes else "empty",
            "node_count": len(nodes),
            "nodes": nodes,
            "last_aggregate_timestamp": (
                last_aggregate.get("timestamp") if last_aggregate else None
            ),
            "last_seal_hash": (
                last_seal.get("seal_hash") if last_seal else None
            ),
            "total_envelopes": total_envelopes,
            "total_validations": total_validations,
        }

    return router
