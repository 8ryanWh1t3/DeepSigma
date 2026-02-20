"""Webhook notification system for DeepSigma governance events.

Pushes drift events, quorum breaks, credibility threshold crossings,
patch applications, and seal creations to external endpoints.

Stdlib only (urllib.request) — no requests/httpx dependency.
Works standalone for CLI and MCP use; optional FastAPI routes when dashboard runs.
"""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import logging
import os
import random
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("pydantic is required: pip install pydantic>=2.0")

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────

class WebhookEventType(str, Enum):
    drift_detected = "drift_detected"
    quorum_break = "quorum_break"
    credibility_threshold = "credibility_threshold"
    patch_applied = "patch_applied"
    seal_created = "seal_created"


class DeliveryStatus(str, Enum):
    success = "success"
    failed = "failed"
    pending = "pending"


class PayloadFormat(str, Enum):
    standard = "standard"
    slack = "slack"


# ── Helpers ──────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ── Models ───────────────────────────────────────────────────────

class WebhookConfig(BaseModel):
    """Registration for an external webhook endpoint."""
    webhook_id: str = Field(default="", description="Auto-generated if blank")
    name: str = Field(..., description="Human-readable label")
    url: str = Field(..., description="Target URL for POST delivery")
    secret: str = Field(..., description="HMAC-SHA256 shared secret")
    event_types: List[WebhookEventType] = Field(
        ..., description="Events that trigger this webhook"
    )
    payload_format: PayloadFormat = PayloadFormat.standard
    enabled: bool = True
    tenant_id: str = Field(default="default")
    created_at: str = Field(default="")
    updated_at: str = Field(default="")

    def model_post_init(self, __context: Any) -> None:
        if not self.webhook_id:
            self.webhook_id = f"WH-{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.updated_at:
            self.updated_at = _now_iso()


class WebhookEvent(BaseModel):
    """A single event payload to be delivered."""
    event_id: str = Field(default="")
    event_type: WebhookEventType
    timestamp: str = Field(default="")
    tenant_id: str = Field(default="default")
    payload: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.event_id:
            self.event_id = f"EVT-{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = _now_iso()


class DeliveryRecord(BaseModel):
    """Log of a single webhook delivery attempt."""
    delivery_id: str = Field(default="")
    webhook_id: str
    event_id: str
    event_type: WebhookEventType
    url: str
    status: DeliveryStatus = DeliveryStatus.pending
    status_code: Optional[int] = None
    attempt: int = 1
    max_attempts: int = 3
    error_message: str = ""
    delivered_at: str = Field(default="")
    duration_ms: Optional[float] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.delivery_id:
            self.delivery_id = f"DLV-{uuid.uuid4().hex[:12]}"
        if not self.delivered_at:
            self.delivered_at = _now_iso()


# ── HMAC Signing ─────────────────────────────────────────────────

def compute_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 hex digest for a webhook payload."""
    return hmac_mod.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def verify_hmac_signature(payload_bytes: bytes, secret: str, signature: str) -> bool:
    """Verify an HMAC-SHA256 signature."""
    if not secret or not signature:
        return False
    expected = hmac_mod.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac_mod.compare_digest(expected, signature)


# ── Transient detection + backoff ────────────────────────────────

def _is_transient_http(status_code: int) -> bool:
    """Return True if the HTTP status code is retriable."""
    return status_code in (408, 429, 500, 502, 503, 504)


def _is_transient_error(exc: Exception) -> bool:
    """Return True if the exception looks like a transient failure."""
    msg = str(exc).lower()
    for signal in ("429", "502", "503", "504", "timeout",
                   "connection reset", "temporary failure",
                   "service unavailable", "rate limit"):
        if signal in msg:
            return True
    return False


def _backoff_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """Exponential backoff with jitter."""
    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    jitter = random.uniform(0, delay * 0.5)  # noqa: S311
    return delay + jitter


# ── Slack Block Kit formatter ────────────────────────────────────

SEVERITY_EMOJI = {
    "drift_detected": ":warning:",
    "quorum_break": ":rotating_light:",
    "credibility_threshold": ":chart_with_downwards_trend:",
    "patch_applied": ":wrench:",
    "seal_created": ":lock:",
}


def format_slack_payload(event: WebhookEvent) -> Dict[str, Any]:
    """Convert a WebhookEvent to Slack Block Kit format."""
    emoji = SEVERITY_EMOJI.get(event.event_type.value, ":bell:")
    header_text = f"{emoji} DeepSigma: {event.event_type.value.replace('_', ' ').title()}"

    fields = []
    for key, value in event.payload.items():
        fields.append({"type": "mrkdwn", "text": f"*{key}:*\n{value}"})

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": True},
        },
        {
            "type": "section",
            "fields": fields[:10],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"Event ID: `{event.event_id}` | "
                        f"Tenant: `{event.tenant_id}` | "
                        f"Time: {event.timestamp}"
                    ),
                },
            ],
        },
    ]

    return {"blocks": blocks}


# ── JSONL Storage ────────────────────────────────────────────────

_WEBHOOK_DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data")) / "webhooks"
_WEBHOOKS_FILE = _WEBHOOK_DATA_DIR / "webhooks.jsonl"
_DELIVERY_LOG_FILE = _WEBHOOK_DATA_DIR / "delivery_log.jsonl"

_write_lock = threading.Lock()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _append_webhook_jsonl(path: Path, data: Dict[str, Any]) -> None:
    with _write_lock:
        _ensure_parent(path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")


def _read_webhook_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return results


def _rewrite_webhook_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    """Rewrite an entire JSONL file (for updates/deletes)."""
    with _write_lock:
        _ensure_parent(path)
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, default=str) + "\n")


# ── Environment config ───────────────────────────────────────────

WEBHOOK_MAX_RETRIES = int(os.environ.get("WEBHOOK_MAX_RETRIES", "3"))
WEBHOOK_BASE_DELAY = float(os.environ.get("WEBHOOK_BASE_DELAY", "1.0"))
WEBHOOK_MAX_DELAY = float(os.environ.get("WEBHOOK_MAX_DELAY", "60.0"))
WEBHOOK_TIMEOUT = int(os.environ.get("WEBHOOK_TIMEOUT", "10"))


# ── WebhookManager ──────────────────────────────────────────────

class WebhookManager:
    """Thread-safe webhook manager for DeepSigma governance events.

    Handles registration, dispatch, retry with exponential backoff,
    delivery logging, and audit integration.
    """

    def __init__(
        self,
        webhooks_file: Optional[Path] = None,
        delivery_log_file: Optional[Path] = None,
        max_retries: int = WEBHOOK_MAX_RETRIES,
        base_delay: float = WEBHOOK_BASE_DELAY,
        max_delay: float = WEBHOOK_MAX_DELAY,
        timeout: int = WEBHOOK_TIMEOUT,
    ) -> None:
        self._webhooks_file = webhooks_file or _WEBHOOKS_FILE
        self._delivery_log_file = delivery_log_file or _DELIVERY_LOG_FILE
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._timeout = timeout

    # ── Registration ─────────────────────────────────────────

    def register(self, config: WebhookConfig) -> WebhookConfig:
        """Register a new webhook. Returns the config with generated ID."""
        _append_webhook_jsonl(self._webhooks_file, config.model_dump())
        self._audit(
            "WEBHOOK_REGISTER", config.webhook_id, config.tenant_id,
            metadata={"url": config.url, "event_types": [e.value for e in config.event_types]},
        )
        return config

    def list_webhooks(self, tenant_id: str = "default") -> List[WebhookConfig]:
        """List all registered webhooks for a tenant."""
        records = _read_webhook_jsonl(self._webhooks_file)
        return [WebhookConfig(**r) for r in records if r.get("tenant_id", "default") == tenant_id]

    def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Get a webhook config by ID."""
        for r in _read_webhook_jsonl(self._webhooks_file):
            if r.get("webhook_id") == webhook_id:
                return WebhookConfig(**r)
        return None

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook registration. Returns True if found and deleted."""
        records = _read_webhook_jsonl(self._webhooks_file)
        filtered = [r for r in records if r.get("webhook_id") != webhook_id]
        if len(filtered) == len(records):
            return False
        removed = [r for r in records if r.get("webhook_id") == webhook_id]
        _rewrite_webhook_jsonl(self._webhooks_file, filtered)
        tenant_id = removed[0].get("tenant_id", "default") if removed else "default"
        self._audit("WEBHOOK_DELETE", webhook_id, tenant_id)
        return True

    def update_webhook(self, webhook_id: str, **updates: Any) -> Optional[WebhookConfig]:
        """Update fields on an existing webhook config."""
        records = _read_webhook_jsonl(self._webhooks_file)
        found_idx = None
        for i, r in enumerate(records):
            if r.get("webhook_id") == webhook_id:
                found_idx = i
                break
        if found_idx is None:
            return None
        records[found_idx].update(updates)
        records[found_idx]["updated_at"] = _now_iso()
        _rewrite_webhook_jsonl(self._webhooks_file, records)
        return WebhookConfig(**records[found_idx])

    # ── Dispatch ─────────────────────────────────────────────

    def dispatch(self, event: WebhookEvent) -> List[DeliveryRecord]:
        """Dispatch an event to all matching webhooks."""
        webhooks = self.list_webhooks(tenant_id=event.tenant_id)
        matching = [w for w in webhooks if w.enabled and event.event_type in w.event_types]
        return [self._deliver_with_retry(w, event) for w in matching]

    def dispatch_async(self, event: WebhookEvent) -> None:
        """Fire-and-forget dispatch in a background thread."""
        t = threading.Thread(target=self.dispatch, args=(event,), daemon=True)
        t.start()

    # ── Delivery Log ─────────────────────────────────────────

    def get_delivery_log(
        self,
        webhook_id: Optional[str] = None,
        event_type: Optional[WebhookEventType] = None,
        status: Optional[DeliveryStatus] = None,
        limit: int = 100,
    ) -> List[DeliveryRecord]:
        """Query delivery log with optional filters."""
        records = _read_webhook_jsonl(self._delivery_log_file)
        result = []
        for r in records:
            if webhook_id and r.get("webhook_id") != webhook_id:
                continue
            if event_type and r.get("event_type") != event_type.value:
                continue
            if status and r.get("status") != status.value:
                continue
            result.append(DeliveryRecord(**r))
            if len(result) >= limit:
                break
        return result

    # ── Internal delivery ────────────────────────────────────

    def _deliver_with_retry(self, webhook: WebhookConfig, event: WebhookEvent) -> DeliveryRecord:
        """Attempt delivery with exponential backoff retry."""
        if webhook.payload_format == PayloadFormat.slack:
            body_dict = format_slack_payload(event)
        else:
            body_dict = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp,
                "tenant_id": event.tenant_id,
                "payload": event.payload,
            }

        payload_bytes = json.dumps(body_dict, default=str).encode("utf-8")
        signature = compute_hmac_signature(payload_bytes, webhook.secret)

        last_record: Optional[DeliveryRecord] = None

        for attempt in range(1, self._max_retries + 1):
            start_time = time.monotonic()
            record = DeliveryRecord(
                webhook_id=webhook.webhook_id,
                event_id=event.event_id,
                event_type=event.event_type,
                url=webhook.url,
                attempt=attempt,
                max_attempts=self._max_retries,
            )

            try:
                req = urllib.request.Request(
                    webhook.url,
                    data=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-DeepSigma-Signature": signature,
                        "X-DeepSigma-Event": event.event_type.value,
                        "X-DeepSigma-Delivery": record.delivery_id,
                        "User-Agent": "DeepSigma-Webhook/1.0",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    record.status_code = resp.status
                    record.status = DeliveryStatus.success
                    record.duration_ms = round((time.monotonic() - start_time) * 1000, 2)

                self._log_delivery(record)
                self._audit_delivery(record, webhook.tenant_id, "SUCCESS")
                return record

            except urllib.error.HTTPError as exc:
                record.status_code = exc.code
                record.duration_ms = round((time.monotonic() - start_time) * 1000, 2)
                record.error_message = f"HTTP {exc.code}: {exc.reason}"

                if not _is_transient_http(exc.code) or attempt == self._max_retries:
                    record.status = DeliveryStatus.failed
                    self._log_delivery(record)
                    self._audit_delivery(record, webhook.tenant_id, "FAILED")
                    return record

                self._log_delivery(record)
                time.sleep(_backoff_delay(attempt, self._base_delay, self._max_delay))
                last_record = record

            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                record.duration_ms = round((time.monotonic() - start_time) * 1000, 2)
                record.error_message = str(exc)

                if not _is_transient_error(exc) or attempt == self._max_retries:
                    record.status = DeliveryStatus.failed
                    self._log_delivery(record)
                    self._audit_delivery(record, webhook.tenant_id, "FAILED")
                    return record

                self._log_delivery(record)
                time.sleep(_backoff_delay(attempt, self._base_delay, self._max_delay))
                last_record = record

        # Should not reach here
        if last_record:
            last_record.status = DeliveryStatus.failed
            return last_record
        raise RuntimeError("Delivery loop exited without result")  # pragma: no cover

    def _log_delivery(self, record: DeliveryRecord) -> None:
        """Append delivery record to the JSONL log."""
        _append_webhook_jsonl(self._delivery_log_file, record.model_dump())

    def _audit(self, action: str, target_id: str, tenant_id: str,
               metadata: Optional[Dict[str, Any]] = None) -> None:
        """Write an audit trail entry."""
        try:
            from governance.audit import audit_action
            audit_action(
                tenant_id=tenant_id,
                actor_user="webhook-manager",
                actor_role="system",
                action=action,
                target_type="WEBHOOK",
                target_id=target_id,
                outcome="SUCCESS",
                metadata=metadata or {},
            )
        except Exception:
            logger.warning("Failed to write audit entry for %s", action, exc_info=True)

    def _audit_delivery(self, record: DeliveryRecord, tenant_id: str, outcome: str) -> None:
        """Audit a delivery attempt."""
        try:
            from governance.audit import audit_action
            audit_action(
                tenant_id=tenant_id,
                actor_user="webhook-manager",
                actor_role="system",
                action="WEBHOOK_DELIVER",
                target_type="WEBHOOK_DELIVERY",
                target_id=record.delivery_id,
                outcome=outcome,
                metadata={
                    "webhook_id": record.webhook_id,
                    "event_id": record.event_id,
                    "event_type": record.event_type.value,
                    "status_code": record.status_code,
                    "attempt": record.attempt,
                    "duration_ms": record.duration_ms,
                    "error": record.error_message,
                },
            )
        except Exception:
            logger.warning("Failed to write delivery audit", exc_info=True)


# ── Module-level convenience ─────────────────────────────────────

_default_manager: Optional[WebhookManager] = None
_manager_lock = threading.Lock()


def get_webhook_manager() -> WebhookManager:
    """Get or create the default singleton WebhookManager."""
    global _default_manager
    if _default_manager is None:
        with _manager_lock:
            if _default_manager is None:
                _default_manager = WebhookManager()
    return _default_manager


def notify_drift_detected(
    drift_id: str,
    drift_type: str,
    severity: str,
    entity: str = "",
    description: str = "",
    tenant_id: str = "default",
    **extra: Any,
) -> None:
    """Fire-and-forget notification for a detected drift signal."""
    event = WebhookEvent(
        event_type=WebhookEventType.drift_detected,
        tenant_id=tenant_id,
        payload={"drift_id": drift_id, "drift_type": drift_type,
                 "severity": severity, "entity": entity,
                 "description": description, **extra},
    )
    get_webhook_manager().dispatch_async(event)


def notify_quorum_break(
    claim_id: str,
    claim_title: str,
    previous_state: str,
    new_state: str,
    tenant_id: str = "default",
    **extra: Any,
) -> None:
    """Fire-and-forget notification for a quorum break."""
    event = WebhookEvent(
        event_type=WebhookEventType.quorum_break,
        tenant_id=tenant_id,
        payload={"claim_id": claim_id, "claim_title": claim_title,
                 "previous_state": previous_state, "new_state": new_state, **extra},
    )
    get_webhook_manager().dispatch_async(event)


def notify_credibility_threshold(
    score: float,
    band: str,
    previous_band: str,
    direction: str,
    tenant_id: str = "default",
    **extra: Any,
) -> None:
    """Fire-and-forget notification for a credibility threshold crossing."""
    event = WebhookEvent(
        event_type=WebhookEventType.credibility_threshold,
        tenant_id=tenant_id,
        payload={"credibility_index": score, "band": band,
                 "previous_band": previous_band, "direction": direction, **extra},
    )
    get_webhook_manager().dispatch_async(event)


def notify_patch_applied(
    patch_id: str,
    patch_type: str,
    target: str,
    tenant_id: str = "default",
    **extra: Any,
) -> None:
    """Fire-and-forget notification for an applied patch."""
    event = WebhookEvent(
        event_type=WebhookEventType.patch_applied,
        tenant_id=tenant_id,
        payload={"patch_id": patch_id, "patch_type": patch_type, "target": target, **extra},
    )
    get_webhook_manager().dispatch_async(event)


def notify_seal_created(
    packet_id: str,
    seal_hash: str,
    chain_length: int,
    tenant_id: str = "default",
    **extra: Any,
) -> None:
    """Fire-and-forget notification for a created seal."""
    event = WebhookEvent(
        event_type=WebhookEventType.seal_created,
        tenant_id=tenant_id,
        payload={"packet_id": packet_id, "seal_hash": seal_hash,
                 "chain_length": chain_length, **extra},
    )
    get_webhook_manager().dispatch_async(event)
