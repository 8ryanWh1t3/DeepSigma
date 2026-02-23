"""Mesh Transport — pluggable transport layer for inter-node communication.

Provides a Transport protocol with two implementations:
- LocalTransport: filesystem-based push/pull (in-process, testing)
- HTTPTransport: real HTTP calls via httpx (distributed deployment)

Also includes the FastAPI mesh router for server-side endpoints.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from mesh.logstore import append_jsonl, load_json, load_since, write_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------

_BASE_DATA_DIR = Path(__file__).parent.parent / "data" / "mesh"
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def _safe_slug(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _node_dir(tenant_id: str, node_id: str) -> Path:
    if os.path.basename(tenant_id) != tenant_id:
        raise ValueError("Invalid tenant_id")
    if os.path.basename(node_id) != node_id:
        raise ValueError("Invalid node_id")
    if not _SAFE_ID_RE.fullmatch(tenant_id):
        raise ValueError("Invalid tenant_id")
    if not _SAFE_ID_RE.fullmatch(node_id):
        raise ValueError("Invalid node_id")
    base = _BASE_DATA_DIR.resolve()
    d = (base / _safe_slug(tenant_id) / _safe_slug(node_id)).resolve()
    if os.path.commonpath([str(base), str(d)]) != str(base):
        raise ValueError("Invalid mesh path")
    return d


def _tenant_dir(tenant_id: str) -> Path:
    if os.path.basename(tenant_id) != tenant_id:
        raise ValueError("Invalid tenant_id")
    if not _SAFE_ID_RE.fullmatch(tenant_id):
        raise ValueError("Invalid tenant_id")
    base = _BASE_DATA_DIR.resolve()
    d = (base / _safe_slug(tenant_id)).resolve()
    if os.path.commonpath([str(base), str(d)]) != str(base):
        raise ValueError("Invalid tenant path")
    return d


def _log_path(tenant_id: str, node_id: str, log_name: str) -> Path:
    if log_name not in LOG_FILES and log_name != NODE_STATUS_FILE:
        raise ValueError(f"Unsupported log file: {log_name}")
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
# Transport Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class Transport(Protocol):
    """Abstract transport interface for inter-node communication.

    Implementations:
    - LocalTransport: filesystem-based (in-process, testing)
    - HTTPTransport: real HTTP calls (distributed deployment)
    """

    def push(
        self,
        tenant_id: str,
        target_node_id: str,
        log_name: str,
        records: list[dict],
    ) -> int:
        """Push records to a target node's log."""
        ...

    def pull(
        self,
        tenant_id: str,
        source_node_id: str,
        log_name: str,
        since: str = "",
    ) -> list[dict]:
        """Pull records from a source node's log."""
        ...

    def get_status(self, tenant_id: str, node_id: str) -> dict | None:
        """Read node status."""
        ...

    def set_status(self, tenant_id: str, node_id: str, status: dict) -> None:
        """Write node status."""
        ...

    def health(self) -> dict[str, Any]:
        """Return transport health info."""
        ...


# ---------------------------------------------------------------------------
# LocalTransport — filesystem-based (backward compatible)
# ---------------------------------------------------------------------------

class LocalTransport:
    """In-process transport using local filesystem JSONL files.

    Wraps the existing push_records/pull_records module functions.
    This is the default transport for single-process and testing scenarios.
    """

    def push(
        self,
        tenant_id: str,
        target_node_id: str,
        log_name: str,
        records: list[dict],
    ) -> int:
        return push_records(tenant_id, target_node_id, log_name, records)

    def pull(
        self,
        tenant_id: str,
        source_node_id: str,
        log_name: str,
        since: str = "",
    ) -> list[dict]:
        return pull_records(tenant_id, source_node_id, log_name, since)

    def get_status(self, tenant_id: str, node_id: str) -> dict | None:
        return get_node_status(tenant_id, node_id)

    def set_status(self, tenant_id: str, node_id: str, status: dict) -> None:
        set_node_status(tenant_id, node_id, status)

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "transport": "local"}


# ---------------------------------------------------------------------------
# HTTPTransport — real HTTP calls for distributed deployment
# ---------------------------------------------------------------------------

# Optional msgpack support
_HAS_MSGPACK = False
try:
    import msgpack
    _HAS_MSGPACK = True
except ImportError:
    pass


def _encode_payload(data: Any, use_msgpack: bool = False) -> tuple[bytes, str]:
    """Encode payload as JSON or MessagePack. Returns (bytes, content_type)."""
    if use_msgpack and _HAS_MSGPACK:
        return msgpack.packb(data, use_bin_type=True), "application/msgpack"
    return json.dumps(data, default=str).encode("utf-8"), "application/json"


def _decode_payload(raw: bytes, content_type: str) -> Any:
    """Decode payload based on content type."""
    if "msgpack" in content_type and _HAS_MSGPACK:
        return msgpack.unpackb(raw, raw=False)
    return json.loads(raw)


_TRANSIENT_CODES = {502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 0.5

PEER_ONLINE = "ONLINE"
PEER_SUSPECT = "SUSPECT"
PEER_OFFLINE = "OFFLINE"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class HTTPTransport:
    """HTTP-based transport for distributed mesh nodes.

    Sends push/pull requests to remote node servers via httpx.
    Supports JSON (default) and MessagePack (when available) serialization.

    Parameters
    ----------
    peer_registry : dict[str, str]
        Maps node_id → base_url (e.g. {"edge-A": "http://host1:8100"}).
    timeout : float
        HTTP request timeout in seconds.
    verify_tls : bool
        Whether to verify TLS certificates.
    use_msgpack : bool
        Prefer MessagePack when available.
    """

    def __init__(
        self,
        peer_registry: dict[str, str],
        timeout: float = 5.0,
        verify_tls: bool = True,
        use_msgpack: bool = False,
        max_retries: int = _MAX_RETRIES,
        backoff_base: float = _BACKOFF_BASE,
        suspect_after_failures: int = 1,
        offline_after_failures: int = 2,
        recovery_successes: int = 1,
    ) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        if suspect_after_failures < 1:
            raise ValueError("suspect_after_failures must be >= 1")
        if offline_after_failures < suspect_after_failures:
            raise ValueError("offline_after_failures must be >= suspect_after_failures")
        if recovery_successes < 1:
            raise ValueError("recovery_successes must be >= 1")

        self._peers = dict(peer_registry)
        self._timeout = timeout
        self._verify_tls = verify_tls
        self._use_msgpack = use_msgpack and _HAS_MSGPACK
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._suspect_after_failures = suspect_after_failures
        self._offline_after_failures = offline_after_failures
        self._recovery_successes = recovery_successes
        self._peer_states: dict[str, dict[str, Any]] = {
            node_id: {
                "state": PEER_ONLINE,
                "consecutive_failures": 0,
                "consecutive_successes": 0,
                "last_change": _now_iso(),
            }
            for node_id in self._peers
        }
        self._partition_events: list[dict[str, str]] = []

        try:
            import httpx
            self._client = httpx.Client(
                timeout=timeout,
                verify=verify_tls,
            )
        except ImportError:
            raise ImportError(
                "httpx is required for HTTPTransport. "
                "Install with: pip install httpx"
            )

    def _base_url(self, node_id: str) -> str:
        url = self._peers.get(node_id)
        if url is None:
            raise ValueError(f"Unknown peer node: {node_id}")
        return url.rstrip("/")

    def _ensure_runtime_state(self) -> None:
        """Backfill runtime fields for test-constructed instances."""
        if not hasattr(self, "_max_retries"):
            self._max_retries = _MAX_RETRIES
        if not hasattr(self, "_backoff_base"):
            self._backoff_base = _BACKOFF_BASE
        if not hasattr(self, "_suspect_after_failures"):
            self._suspect_after_failures = 1
        if not hasattr(self, "_offline_after_failures"):
            self._offline_after_failures = 2
        if not hasattr(self, "_recovery_successes"):
            self._recovery_successes = 1
        if not hasattr(self, "_peer_states"):
            self._peer_states = {
                node_id: {
                    "state": PEER_ONLINE,
                    "consecutive_failures": 0,
                    "consecutive_successes": 0,
                    "last_change": _now_iso(),
                }
                for node_id in getattr(self, "_peers", {})
            }
        if not hasattr(self, "_partition_events"):
            self._partition_events = []

    def _record_partition_event(
        self,
        peer_id: str,
        event_type: str,
        from_state: str,
        to_state: str,
        reason: str,
    ) -> None:
        event = {
            "timestamp": _now_iso(),
            "peer_id": peer_id,
            "event_type": event_type,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
        }
        self._partition_events.append(event)
        if len(self._partition_events) > 200:
            self._partition_events = self._partition_events[-200:]

    def _set_peer_state(self, peer_id: str, new_state: str, reason: str) -> None:
        state = self._peer_states.setdefault(
            peer_id,
            {
                "state": PEER_ONLINE,
                "consecutive_failures": 0,
                "consecutive_successes": 0,
                "last_change": _now_iso(),
            },
        )
        prev = state["state"]
        if prev == new_state:
            return
        state["state"] = new_state
        state["last_change"] = _now_iso()
        if new_state == PEER_ONLINE:
            self._record_partition_event(peer_id, "recovery", prev, new_state, reason)
        else:
            self._record_partition_event(peer_id, "partition", prev, new_state, reason)

    def _mark_peer_success(self, peer_id: str) -> None:
        state = self._peer_states.setdefault(
            peer_id,
            {
                "state": PEER_ONLINE,
                "consecutive_failures": 0,
                "consecutive_successes": 0,
                "last_change": _now_iso(),
            },
        )
        state["consecutive_failures"] = 0
        state["consecutive_successes"] = int(state.get("consecutive_successes", 0)) + 1
        if (
            state["state"] != PEER_ONLINE
            and state["consecutive_successes"] >= self._recovery_successes
        ):
            self._set_peer_state(peer_id, PEER_ONLINE, "request_succeeded")

    def _mark_peer_failure(self, peer_id: str, reason: str) -> None:
        state = self._peer_states.setdefault(
            peer_id,
            {
                "state": PEER_ONLINE,
                "consecutive_failures": 0,
                "consecutive_successes": 0,
                "last_change": _now_iso(),
            },
        )
        state["consecutive_successes"] = 0
        state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1
        failures = state["consecutive_failures"]
        if failures >= self._offline_after_failures:
            self._set_peer_state(peer_id, PEER_OFFLINE, reason)
        elif failures >= self._suspect_after_failures:
            self._set_peer_state(peer_id, PEER_SUSPECT, reason)

    def _request_with_retry(
        self,
        method: str,
        url: str,
        peer_id: str = "",
        **kwargs: Any,
    ) -> Any:
        """Make HTTP request with retry on transient failures."""
        import httpx

        self._ensure_runtime_state()
        last_exc = None
        for attempt in range(self._max_retries):
            try:
                resp = self._client.request(method, url, **kwargs)
                if resp.status_code in _TRANSIENT_CODES:
                    logger.warning(
                        "Transient %d from %s (attempt %d/%d)",
                        resp.status_code, url, attempt + 1, self._max_retries,
                    )
                    if attempt < self._max_retries - 1:
                        time.sleep(self._backoff_base * (2 ** attempt))
                    continue
                resp.raise_for_status()
                ct = resp.headers.get("content-type", "application/json")
                payload = _decode_payload(resp.content, ct)
                if peer_id:
                    self._mark_peer_success(peer_id)
                return payload
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.warning(
                    "Connection error to %s (attempt %d/%d): %s",
                    url, attempt + 1, self._max_retries, exc,
                )
                if attempt < self._max_retries - 1:
                    time.sleep(self._backoff_base * (2 ** attempt))
            except httpx.HTTPError as exc:
                last_exc = exc
                break

        if peer_id:
            reason = last_exc.__class__.__name__ if last_exc else "request_failed"
            self._mark_peer_failure(peer_id, reason)
        raise ConnectionError(
            f"Failed after {self._max_retries} retries: {url}"
        ) from last_exc

    def push(
        self,
        tenant_id: str,
        target_node_id: str,
        log_name: str,
        records: list[dict],
    ) -> int:
        base = self._base_url(target_node_id)
        url = f"{base}/mesh/{tenant_id}/{target_node_id}/push"
        key = log_name.replace(".jsonl", "")
        payload = {key: records}
        body, content_type = _encode_payload(payload, self._use_msgpack)
        result = self._request_with_retry(
            "POST", url,
            peer_id=target_node_id,
            content=body,
            headers={"Content-Type": content_type},
        )
        return result.get("received", {}).get(key, 0)

    def pull(
        self,
        tenant_id: str,
        source_node_id: str,
        log_name: str,
        since: str = "",
    ) -> list[dict]:
        base = self._base_url(source_node_id)
        url = f"{base}/mesh/{tenant_id}/{source_node_id}/pull"
        params = {}
        if since:
            params["since"] = since
        result = self._request_with_retry("GET", url, params=params, peer_id=source_node_id)
        key = log_name.replace(".jsonl", "")
        return result.get("records", {}).get(key, [])

    def get_status(self, tenant_id: str, node_id: str) -> dict | None:
        try:
            base = self._base_url(node_id)
        except ValueError:
            return None
        url = f"{base}/mesh/{tenant_id}/{node_id}/status"
        try:
            return self._request_with_retry("GET", url, peer_id=node_id)
        except (ConnectionError, Exception):
            return None

    def set_status(self, tenant_id: str, node_id: str, status: dict) -> None:
        # Status is node-local — always write to filesystem
        set_node_status(tenant_id, node_id, status)

    def health(self) -> dict[str, Any]:
        """Ping all peers and return aggregate health."""
        import httpx

        self._ensure_runtime_state()
        peer_health: dict[str, str] = {}
        for node_id, base_url in self._peers.items():
            try:
                resp = self._client.get(
                    f"{base_url.rstrip('/')}/health",
                    timeout=2.0,
                )
                if resp.status_code == 200:
                    peer_health[node_id] = "ok"
                    self._mark_peer_success(node_id)
                else:
                    peer_health[node_id] = f"error:{resp.status_code}"
                    self._mark_peer_failure(node_id, f"http_{resp.status_code}")
            except (httpx.ConnectError, httpx.TimeoutException):
                peer_health[node_id] = "unreachable"
                self._mark_peer_failure(node_id, "health_unreachable")

        reachable = sum(1 for v in peer_health.values() if v == "ok")
        state_map = {
            node_id: self._peer_states.get(node_id, {}).get("state", PEER_ONLINE)
            for node_id in self._peers
        }
        partition_events = sum(
            1 for e in self._partition_events if e.get("event_type") == "partition"
        )
        recovery_events = sum(
            1 for e in self._partition_events if e.get("event_type") == "recovery"
        )
        return {
            "status": "ok" if reachable == len(self._peers) else "degraded",
            "transport": "http",
            "peers_total": len(self._peers),
            "peers_reachable": reachable,
            "peer_health": peer_health,
            "peer_states": state_map,
            "partition_metrics": {
                "partition_events": partition_events,
                "recovery_events": recovery_events,
                "suspect_peers": sum(1 for s in state_map.values() if s == PEER_SUSPECT),
                "offline_peers": sum(1 for s in state_map.values() if s == PEER_OFFLINE),
            },
            "msgpack_enabled": self._use_msgpack,
        }

    def peer_states(self) -> dict[str, str]:
        """Return current peer state map (ONLINE/SUSPECT/OFFLINE)."""
        return {
            node_id: self._peer_states.get(node_id, {}).get("state", PEER_ONLINE)
            for node_id in self._peers
        }

    def partition_events(self) -> list[dict[str, str]]:
        """Return recent partition/recovery events."""
        return list(self._partition_events)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()


# ---------------------------------------------------------------------------
# FastAPI Router (for API server integration)
# ---------------------------------------------------------------------------

def create_mesh_router():
    """Create FastAPI router for mesh endpoints.

    Returns an APIRouter with push/pull/status endpoints.
    """
    from fastapi import APIRouter, Body

    router = APIRouter(tags=["mesh"])

    @router.post("/mesh/{tenant_id}/{node_id}/push")
    def mesh_push(
        tenant_id: str,
        node_id: str,
        body: dict = Body(),
    ) -> dict[str, Any]:
        """Receive pushed records from a peer node."""
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
        try:
            tenant_dir = _tenant_dir(tenant_id)
        except ValueError:
            return {
                "tenant_id": tenant_id,
                "status": "invalid_tenant_id",
                "nodes": [],
            }
        if not tenant_dir.exists():  # lgtm [py/path-injection]
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
