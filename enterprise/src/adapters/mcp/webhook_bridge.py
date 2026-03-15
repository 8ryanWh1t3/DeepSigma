"""MCP Webhook / SSE Bridge — HTTP wrapper for bundle update notifications.

Provides a lightweight HTTP server that:
- Accepts webhook registrations (POST /webhooks/register)
- Removes webhook registrations (POST /webhooks/unregister)
- Emits bundle-update notifications to registered callbacks
- Streams events via SSE (GET /events)

Stdlib only — no external dependencies.  Uses the same CircuitBreaker
and retry primitives from resilience.py for outbound webhook delivery.

Usage::

    bridge = WebhookBridge(host="127.0.0.1", port=8790)
    bridge.start()          # non-blocking, spawns daemon thread
    bridge.notify("cog-bundle-demo-001", {"action": "verified"})
    bridge.stop()
"""

from __future__ import annotations

import json
import queue
import threading
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional, Set

from .resilience import CircuitBreaker, CircuitOpen, is_transient


# ── Webhook registry ─────────────────────────────────────────────


class WebhookRegistry:
    """Thread-safe registry of callback URLs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hooks: Dict[str, Set[str]] = {}  # event_type -> {url, ...}

    def register(self, url: str, event_type: str = "bundleUpdated") -> None:
        with self._lock:
            self._hooks.setdefault(event_type, set()).add(url)

    def unregister(self, url: str, event_type: str = "bundleUpdated") -> None:
        with self._lock:
            if event_type in self._hooks:
                self._hooks[event_type].discard(url)

    def get_urls(self, event_type: str = "bundleUpdated") -> List[str]:
        with self._lock:
            return list(self._hooks.get(event_type, []))

    def clear(self) -> None:
        with self._lock:
            self._hooks.clear()


# ── SSE event bus ─────────────────────────────────────────────────


class SSEBus:
    """Fan-out event bus for SSE clients."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: List[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=256)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s is not q]

    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        payload = json.dumps({"type": event_type, "data": data})
        with self._lock:
            for q in self._subscribers:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    pass  # drop if subscriber is slow


# ── Outbound webhook delivery ────────────────────────────────────


_webhook_breaker = CircuitBreaker(name="webhook_delivery", threshold=5, cooldown=60.0)


def _deliver_webhook(url: str, payload: Dict[str, Any]) -> bool:
    """POST JSON payload to *url*.  Returns True on success."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with _webhook_breaker:
            resp = urllib.request.urlopen(req, timeout=10)
            return 200 <= resp.status < 300
    except (CircuitOpen, urllib.error.URLError, OSError):
        return False


# ── HTTP request handler ─────────────────────────────────────────


def _make_handler(
    registry: WebhookRegistry,
    sse_bus: SSEBus,
) -> type:
    """Factory for the HTTP request handler with closure over shared state."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            pass  # suppress default stderr logging

        def _json_response(self, status: int, body: Dict[str, Any]) -> None:
            out = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def _read_json(self) -> Optional[Dict[str, Any]]:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return None
            try:
                return json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, ValueError):
                return None

        # ── POST routes ──────────────────────────────────────────

        def do_POST(self) -> None:
            if self.path == "/webhooks/register":
                data = self._read_json()
                if not data or "url" not in data:
                    self._json_response(400, {"error": "url required"})
                    return
                event_type = data.get("event_type", "bundleUpdated")
                registry.register(data["url"], event_type)
                self._json_response(200, {"registered": data["url"], "event_type": event_type})

            elif self.path == "/webhooks/unregister":
                data = self._read_json()
                if not data or "url" not in data:
                    self._json_response(400, {"error": "url required"})
                    return
                event_type = data.get("event_type", "bundleUpdated")
                registry.unregister(data["url"], event_type)
                self._json_response(200, {"unregistered": data["url"]})

            else:
                self._json_response(404, {"error": "not found"})

        # ── GET routes ───────────────────────────────────────────

        def do_GET(self) -> None:
            if self.path == "/events":
                self._handle_sse()
            elif self.path == "/webhooks":
                urls = registry.get_urls()
                self._json_response(200, {"webhooks": urls})
            elif self.path == "/health":
                self._json_response(200, {"status": "ok"})
            else:
                self._json_response(404, {"error": "not found"})

        def _handle_sse(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            sub = sse_bus.subscribe()
            try:
                while True:
                    try:
                        event = sub.get(timeout=30)
                        self.wfile.write(f"data: {event}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        # Send keepalive comment
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                sse_bus.unsubscribe(sub)

    return Handler


# ── Bridge server ────────────────────────────────────────────────


class WebhookBridge:
    """HTTP bridge for MCP webhook notifications and SSE streaming."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8790) -> None:
        self.host = host
        self.port = port
        self.registry = WebhookRegistry()
        self.sse_bus = SSEBus()
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the HTTP server on a daemon thread."""
        handler_cls = _make_handler(self.registry, self.sse_bus)
        self._server = HTTPServer((self.host, self.port), handler_cls)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="webhook-bridge",
        )
        self._thread.start()

    def stop(self) -> None:
        """Shut down the HTTP server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def notify(
        self,
        bundle_id: str,
        detail: Optional[Dict[str, Any]] = None,
        event_type: str = "bundleUpdated",
    ) -> int:
        """Emit a notification to all registered webhooks and SSE clients.

        Returns the number of successful webhook deliveries.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": f"notifications/{event_type}",
            "params": {
                "bundleId": bundle_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "detail": detail or {},
            },
        }

        # Publish to SSE subscribers
        self.sse_bus.publish(event_type, payload["params"])

        # Deliver to registered webhook URLs
        urls = self.registry.get_urls(event_type)
        successes = 0
        for url in urls:
            if _deliver_webhook(url, payload):
                successes += 1

        return successes
