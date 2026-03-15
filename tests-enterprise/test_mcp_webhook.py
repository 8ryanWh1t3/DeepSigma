"""Tests for MCP Webhook Bridge — registration, notification, SSE streaming."""

from __future__ import annotations

import json
import queue
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

import sys
from pathlib import Path

_ENTERPRISE_ROOT = Path(__file__).resolve().parents[1] / "enterprise"
if str(_ENTERPRISE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENTERPRISE_ROOT))


# ── Registry tests ───────────────────────────────────────────────


class TestWebhookRegistry:
    """Test webhook URL registration and unregistration."""

    def test_register_and_list(self):
        from src.adapters.mcp.webhook_bridge import WebhookRegistry

        reg = WebhookRegistry()
        reg.register("http://localhost:9000/hook")
        assert "http://localhost:9000/hook" in reg.get_urls()

    def test_unregister(self):
        from src.adapters.mcp.webhook_bridge import WebhookRegistry

        reg = WebhookRegistry()
        reg.register("http://localhost:9000/hook")
        reg.unregister("http://localhost:9000/hook")
        assert reg.get_urls() == []

    def test_register_multiple_event_types(self):
        from src.adapters.mcp.webhook_bridge import WebhookRegistry

        reg = WebhookRegistry()
        reg.register("http://a.com", "bundleUpdated")
        reg.register("http://b.com", "bundleCreated")
        assert len(reg.get_urls("bundleUpdated")) == 1
        assert len(reg.get_urls("bundleCreated")) == 1


# ── SSE bus tests ────────────────────────────────────────────────


class TestSSEBus:
    """Test fan-out event bus for SSE clients."""

    def test_publish_to_subscriber(self):
        from src.adapters.mcp.webhook_bridge import SSEBus

        bus = SSEBus()
        q = bus.subscribe()
        bus.publish("bundleUpdated", {"bundleId": "test-001"})
        msg = q.get(timeout=1)
        data = json.loads(msg)
        assert data["type"] == "bundleUpdated"
        assert data["data"]["bundleId"] == "test-001"

    def test_unsubscribe_stops_delivery(self):
        from src.adapters.mcp.webhook_bridge import SSEBus

        bus = SSEBus()
        q = bus.subscribe()
        bus.unsubscribe(q)
        bus.publish("bundleUpdated", {"bundleId": "test-001"})
        assert q.empty()


# ── Bridge integration tests ────────────────────────────────────


class TestWebhookBridge:
    """Test the full HTTP bridge server."""

    def test_bridge_health(self):
        from src.adapters.mcp.webhook_bridge import WebhookBridge
        import urllib.request

        bridge = WebhookBridge(port=0)  # port=0 picks a free port
        bridge.start()
        try:
            port = bridge._server.server_address[1]
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5)
            data = json.loads(resp.read())
            assert data["status"] == "ok"
        finally:
            bridge.stop()

    def test_bridge_register_webhook(self):
        from src.adapters.mcp.webhook_bridge import WebhookBridge
        import urllib.request

        bridge = WebhookBridge(port=0)
        bridge.start()
        try:
            port = bridge._server.server_address[1]
            body = json.dumps({"url": "http://example.com/hook"}).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/webhooks/register",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            assert data["registered"] == "http://example.com/hook"
        finally:
            bridge.stop()

    def test_bridge_notify_counts(self):
        from src.adapters.mcp.webhook_bridge import WebhookBridge

        bridge = WebhookBridge(port=0)
        bridge.start()
        try:
            # No webhooks registered, so 0 deliveries
            count = bridge.notify("bundle-001", {"action": "verified"})
            assert count == 0
        finally:
            bridge.stop()
