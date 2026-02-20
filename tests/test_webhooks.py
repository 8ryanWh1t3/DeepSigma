"""Tests for engine/webhooks.py — Webhook notification system.

Run:  pytest tests/test_webhooks.py -v
"""
from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.webhooks import (
    DeliveryRecord,
    DeliveryStatus,
    PayloadFormat,
    WebhookConfig,
    WebhookEvent,
    WebhookEventType,
    WebhookManager,
    _backoff_delay,
    _is_transient_error,
    _is_transient_http,
    compute_hmac_signature,
    format_slack_payload,
    verify_hmac_signature,
)


# ── Helpers ──────────────────────────────────────────────────────

def _mock_urlopen_success():
    """Return a mock urllib response for a successful delivery."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"ok": true}'
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_config(**overrides) -> WebhookConfig:
    defaults = {
        "name": "Test Webhook",
        "url": "https://example.com/hook",
        "secret": "test-secret-123",
        "event_types": [WebhookEventType.drift_detected],
    }
    defaults.update(overrides)
    return WebhookConfig(**defaults)


def _make_event(**overrides) -> WebhookEvent:
    defaults = {
        "event_type": WebhookEventType.drift_detected,
        "payload": {"drift_id": "D-001", "severity": "red"},
    }
    defaults.update(overrides)
    return WebhookEvent(**defaults)


@pytest.fixture
def manager(tmp_path):
    return WebhookManager(
        webhooks_file=tmp_path / "webhooks.jsonl",
        delivery_log_file=tmp_path / "delivery_log.jsonl",
        max_retries=3,
        base_delay=0.01,
        max_delay=0.05,
        timeout=5,
    )


# ── HMAC Signing ─────────────────────────────────────────────────

class TestHMACSigning:
    def test_compute_hmac_produces_hex_digest(self):
        sig = compute_hmac_signature(b'{"test": true}', "secret")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex digest

    def test_verify_hmac_round_trip(self):
        payload = b'{"event": "drift_detected"}'
        secret = "my-secret"
        sig = compute_hmac_signature(payload, secret)
        assert verify_hmac_signature(payload, secret, sig)

    def test_verify_hmac_rejects_wrong_signature(self):
        payload = b'{"event": "drift_detected"}'
        sig = compute_hmac_signature(payload, "correct-secret")
        assert not verify_hmac_signature(payload, "wrong-secret", sig)


# ── Transient Detection ──────────────────────────────────────────

class TestTransientDetection:
    def test_transient_http_codes(self):
        for code in (408, 429, 500, 502, 503, 504):
            assert _is_transient_http(code), f"{code} should be transient"

    def test_non_transient_http_codes(self):
        for code in (400, 401, 403, 404, 422):
            assert not _is_transient_http(code), f"{code} should NOT be transient"

    def test_transient_error_by_message(self):
        assert _is_transient_error(RuntimeError("Connection timeout after 30s"))
        assert _is_transient_error(RuntimeError("503 Service Unavailable"))

    def test_non_transient_error(self):
        assert not _is_transient_error(ValueError("bad input"))


# ── Backoff ──────────────────────────────────────────────────────

class TestBackoff:
    def test_backoff_increases_with_attempts(self):
        # Average over many samples to account for jitter
        samples_1 = [_backoff_delay(1, base_delay=1.0, max_delay=60.0) for _ in range(100)]
        samples_3 = [_backoff_delay(3, base_delay=1.0, max_delay=60.0) for _ in range(100)]
        assert sum(samples_3) / len(samples_3) > sum(samples_1) / len(samples_1)

    def test_backoff_respects_max_delay(self):
        for _ in range(50):
            delay = _backoff_delay(10, base_delay=1.0, max_delay=5.0)
            # max_delay + max jitter (50% of max_delay)
            assert delay <= 5.0 + 2.5 + 0.01


# ── Slack Formatter ──────────────────────────────────────────────

class TestSlackFormatter:
    def test_produces_blocks(self):
        event = _make_event()
        result = format_slack_payload(event)
        assert "blocks" in result
        blocks = result["blocks"]
        assert len(blocks) == 3
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "section"
        assert blocks[2]["type"] == "context"

    def test_emoji_mapping(self):
        for event_type in WebhookEventType:
            event = _make_event(event_type=event_type)
            result = format_slack_payload(event)
            header_text = result["blocks"][0]["text"]["text"]
            assert "DeepSigma:" in header_text


# ── WebhookManager ───────────────────────────────────────────────

class TestWebhookManager:
    def test_register_and_list(self, manager):
        config = _make_config()
        result = manager.register(config)
        assert result.webhook_id.startswith("WH-")

        webhooks = manager.list_webhooks()
        assert len(webhooks) == 1
        assert webhooks[0].webhook_id == result.webhook_id
        assert webhooks[0].name == "Test Webhook"

    def test_delete_webhook(self, manager):
        config = _make_config()
        manager.register(config)
        assert manager.delete_webhook(config.webhook_id)
        assert len(manager.list_webhooks()) == 0

    def test_delete_nonexistent_returns_false(self, manager):
        assert not manager.delete_webhook("WH-nonexistent")

    def test_update_webhook(self, manager):
        config = _make_config()
        manager.register(config)
        updated = manager.update_webhook(config.webhook_id, name="Updated Name")
        assert updated is not None
        assert updated.name == "Updated Name"

    @patch("urllib.request.urlopen")
    def test_dispatch_to_matching_webhook(self, mock_urlopen, manager):
        mock_urlopen.return_value = _mock_urlopen_success()
        config = _make_config()
        manager.register(config)
        event = _make_event()
        records = manager.dispatch(event)
        assert len(records) == 1
        assert records[0].status == DeliveryStatus.success
        assert records[0].status_code == 200

        # Verify HMAC header was sent
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.get_header("X-deepsigma-signature")
        assert req.get_header("X-deepsigma-event") == "drift_detected"

    @patch("urllib.request.urlopen")
    def test_dispatch_skips_disabled_webhook(self, mock_urlopen, manager):
        config = _make_config(enabled=False)
        manager.register(config)
        records = manager.dispatch(_make_event())
        assert len(records) == 0
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_dispatch_skips_unmatched_event_types(self, mock_urlopen, manager):
        config = _make_config(event_types=[WebhookEventType.seal_created])
        manager.register(config)
        records = manager.dispatch(_make_event(event_type=WebhookEventType.drift_detected))
        assert len(records) == 0
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_dispatch_retry_on_transient_error(self, mock_urlopen, manager):
        http_error = urllib.error.HTTPError(
            "https://example.com/hook", 503, "Service Unavailable", {}, None
        )
        mock_urlopen.side_effect = [http_error, http_error, _mock_urlopen_success()]
        config = _make_config()
        manager.register(config)
        records = manager.dispatch(_make_event())
        assert len(records) == 1
        assert records[0].status == DeliveryStatus.success
        assert mock_urlopen.call_count == 3

    @patch("urllib.request.urlopen")
    def test_dispatch_fails_after_max_retries(self, mock_urlopen, manager):
        http_error = urllib.error.HTTPError(
            "https://example.com/hook", 503, "Service Unavailable", {}, None
        )
        mock_urlopen.side_effect = http_error
        config = _make_config()
        manager.register(config)
        records = manager.dispatch(_make_event())
        assert len(records) == 1
        assert records[0].status == DeliveryStatus.failed
        assert records[0].status_code == 503
        assert mock_urlopen.call_count == 3


# ── Delivery Log ─────────────────────────────────────────────────

class TestDeliveryLog:
    @patch("urllib.request.urlopen")
    def test_delivery_log_persisted(self, mock_urlopen, manager):
        mock_urlopen.return_value = _mock_urlopen_success()
        config = _make_config()
        manager.register(config)
        manager.dispatch(_make_event())

        log = manager.get_delivery_log()
        assert len(log) >= 1
        assert log[0].status == DeliveryStatus.success

    @patch("urllib.request.urlopen")
    def test_delivery_log_filtering(self, mock_urlopen, manager):
        mock_urlopen.return_value = _mock_urlopen_success()

        # Register two webhooks
        config_a = _make_config(name="Hook A")
        config_b = _make_config(name="Hook B", event_types=[WebhookEventType.seal_created])
        manager.register(config_a)
        manager.register(config_b)

        # Dispatch drift event (only matches config_a)
        manager.dispatch(_make_event())

        # Dispatch seal event (only matches config_b)
        manager.dispatch(_make_event(event_type=WebhookEventType.seal_created))

        # Filter by webhook_id
        log_a = manager.get_delivery_log(webhook_id=config_a.webhook_id)
        assert all(r.webhook_id == config_a.webhook_id for r in log_a)

        log_b = manager.get_delivery_log(webhook_id=config_b.webhook_id)
        assert all(r.webhook_id == config_b.webhook_id for r in log_b)

        # Filter by status
        log_success = manager.get_delivery_log(status=DeliveryStatus.success)
        assert all(r.status == DeliveryStatus.success for r in log_success)
