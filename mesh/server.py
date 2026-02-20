"""Mesh Server — Standalone HTTP server for a mesh node.

Runs a FastAPI application that accepts push/pull/status requests
from peer nodes. Each server instance represents one mesh node.

Usage:
    python -m mesh.server --tenant tenant-alpha --node-id edge-A --port 8100

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Track server start time for uptime reporting
_start_time: float = 0.0
_draining: bool = False


def create_node_server(
    tenant_id: str,
    node_id: str,
) -> Any:
    """Create a FastAPI application for a single mesh node.

    Mounts the standard mesh router and adds a health check endpoint.
    """
    from fastapi import FastAPI

    from mesh.transport import create_mesh_router, ensure_node_dirs

    global _start_time
    _start_time = time.monotonic()

    # Ensure the node's data directory exists
    ensure_node_dirs(tenant_id, node_id)

    app = FastAPI(
        title=f"Mesh Node — {node_id}",
        description=f"Mesh transport server for node {node_id} (tenant {tenant_id})",
    )

    # Mount the standard mesh router
    app.include_router(create_mesh_router())

    @app.get("/health")
    def health_check() -> dict[str, Any]:
        """Health check endpoint for peer discovery and load balancing."""
        return {
            "status": "draining" if _draining else "ok",
            "node_id": node_id,
            "tenant_id": tenant_id,
            "uptime_s": round(time.monotonic() - _start_time, 1),
        }

    @app.on_event("shutdown")
    async def shutdown_drain() -> None:
        """Graceful shutdown: mark as draining, wait for in-flight requests."""
        global _draining
        _draining = True
        logger.info("Node %s entering drain period (2s)...", node_id)
        await asyncio.sleep(2)
        logger.info("Node %s shutdown complete.", node_id)

    return app


def main() -> None:
    """CLI entry point for running a mesh node server."""
    parser = argparse.ArgumentParser(
        description="Run a mesh node HTTP server",
    )
    parser.add_argument("--tenant", required=True, help="Tenant ID")
    parser.add_argument("--node-id", required=True, help="Node ID")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8100, help="Bind port")
    parser.add_argument("--log-level", default="info", help="Log level")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    app = create_node_server(args.tenant, args.node_id)

    try:
        import uvicorn
    except ImportError:
        logger.error("uvicorn is required to run the mesh server. pip install uvicorn")
        raise SystemExit(1)

    logger.info(
        "Starting mesh node %s on %s:%d (tenant=%s)",
        args.node_id, args.host, args.port, args.tenant,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
