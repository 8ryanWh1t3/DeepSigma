"""SharePoint Graph API connector for DeepSigma canonical record ingestion.

Implements the field mapping from
``llm_data_model/04_mappings/sharepoint_mapping.md``.

Production features:
- Azure AD client-credentials OAuth 2.0 (via AzureADAuth)
- Automatic token caching and refresh
- Rate-limit handling with exponential backoff (HTTP 429 / 503)
- ConnectorV1 contract compliance (list_records, get_record, to_envelopes)
- Configuration via environment variables (no secrets in code)

Usage::

    connector = SharePointConnector()
    records = connector.list_records(list_id="my-list-id")
    result  = connector.delta_sync("my-list-id")
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from adapters._azure_auth import AzureADAuth
from adapters._connector_helpers import (
    strip_html,
    to_iso,
    uuid_from_hash,
)

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Retry configuration for 429 / 503 throttling
_MAX_RETRIES = 4
_INITIAL_BACKOFF_S = 1.0
_BACKOFF_MULTIPLIER = 2.0

# Content type → canonical record_type mapping
_CONTENT_TYPE_MAP: Dict[str, str] = {
    "Document": "Document",
    "Document Set": "Document",
    "Wiki Page": "Document",
    "Page": "Document",
    "Item": "Entity",
    "Event": "Event",
    "Task": "Event",
}


class SharePointConnector:
    """Microsoft Graph API connector for SharePoint lists and libraries.

    Configuration is read from environment variables:

    - ``SP_TENANT_ID``
    - ``SP_CLIENT_ID``
    - ``SP_CLIENT_SECRET``
    - ``SP_SITE_ID``

    Implements ConnectorV1 contract (v0.6.0+).
    """

    source_name = "sharepoint"

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        site_id: Optional[str] = None,
    ) -> None:
        self._tenant_id = (
            tenant_id or os.environ.get("SP_TENANT_ID", "")
        )
        self._client_id = (
            client_id or os.environ.get("SP_CLIENT_ID", "")
        )
        self._client_secret = (
            client_secret
            or os.environ.get("SP_CLIENT_SECRET", "")
        )
        self._site_id = (
            site_id or os.environ.get("SP_SITE_ID", "")
        )

        self._auth = AzureADAuth(
            tenant_id=self._tenant_id,
            client_id=self._client_id,
            client_secret=self._client_secret,
            scope="https://graph.microsoft.com/.default",
        )

        # Delta tokens per list for incremental sync
        self._delta_tokens: Dict[str, str] = {}

    # ── ConnectorV1 contract ─────────────────────────────────────

    def list_records(
        self, **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """List canonical records from a SharePoint list.

        Parameters
        ----------
        list_id : str
            SharePoint list ID (required keyword argument).
        """
        list_id: str = kwargs.get("list_id", "")
        if not list_id:
            raise ValueError(
                "list_id is required for list_records()"
            )
        return self.list_items(list_id)

    def get_record(
        self, record_id: str, **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get a single canonical record by item ID.

        Parameters
        ----------
        record_id : str
            SharePoint item ID (raw Graph API id).
        list_id : str
            SharePoint list ID (required keyword argument).
        """
        list_id: str = kwargs.get("list_id", "")
        if not list_id:
            raise ValueError(
                "list_id is required for get_record()"
            )
        return self.get_item(list_id, record_id)

    # ── Public API ───────────────────────────────────────────────

    def list_items(self, list_id: str) -> List[Dict[str, Any]]:
        """Fetch all items from a SharePoint list."""
        url = (
            f"{GRAPH_BASE}/sites/{self._site_id}"
            f"/lists/{list_id}/items?expand=fields"
        )
        data = self._graph_get(url)
        items = data.get("value", [])
        return [self._to_canonical(item, list_id) for item in items]

    def get_item(
        self, list_id: str, item_id: str,
    ) -> Dict[str, Any]:
        """Fetch a single list item as a canonical record."""
        url = (
            f"{GRAPH_BASE}/sites/{self._site_id}"
            f"/lists/{list_id}/items/{item_id}"
            f"?expand=fields"
        )
        item = self._graph_get(url)
        return self._to_canonical(item, list_id)

    def delta_sync(self, list_id: str) -> Dict[str, Any]:
        """Incremental sync using Graph delta queries.

        Returns ``{synced, created, updated, records}``.
        """
        delta_token = self._delta_tokens.get(list_id)
        if delta_token:
            url = delta_token
        else:
            url = (
                f"{GRAPH_BASE}/sites/{self._site_id}"
                f"/lists/{list_id}/items/delta"
                f"?expand=fields"
            )

        is_initial = not self._delta_tokens.get(list_id)

        data = self._graph_get(url)
        items = data.get("value", [])

        # Store next delta link
        next_delta = data.get("@odata.deltaLink")
        if next_delta:
            self._delta_tokens[list_id] = next_delta

        records = [self._to_canonical(item, list_id) for item in items]
        created = len(records) if is_initial else 0
        updated = len(records) - created

        return {
            "synced": to_iso(None) or "",
            "created": created,
            "updated": updated,
            "records": records,
        }

    def subscribe(
        self,
        list_id: str,
        webhook_url: str,
        expiry_hours: int = 48,
    ) -> Dict[str, Any]:
        """Create a Graph API webhook subscription."""
        from datetime import datetime, timedelta, timezone

        expiry = (
            datetime.now(timezone.utc)
            + timedelta(hours=expiry_hours)
        ).isoformat()
        resource = (
            f"sites/{self._site_id}"
            f"/lists/{list_id}/items"
        )
        body = {
            "changeType": "created,updated,deleted",
            "notificationUrl": webhook_url,
            "resource": resource,
            "expirationDateTime": expiry,
        }
        url = f"{GRAPH_BASE}/subscriptions"
        return self._graph_post(url, body)

    # ── Envelope contract ──────────────────────────────────────────

    def to_envelopes(
        self, records: List[Dict[str, Any]],
    ) -> list:
        """Wrap canonical records in RecordEnvelopes."""
        from adapters.contract import canonical_to_envelope
        inst = self._site_id or "unknown"
        return [
            canonical_to_envelope(r, source_instance=inst)
            for r in records
        ]

    # ── Field mapping ────────────────────────────────────────────

    def _to_canonical(
        self, item: Dict[str, Any], list_id: str,
    ) -> Dict[str, Any]:
        """Transform a Graph API list item to a canonical record."""
        fields = item.get("fields", {})
        item_id = str(
            item.get("id", fields.get("id", ""))
        )
        content_type = fields.get("ContentType", {})
        if isinstance(content_type, dict):
            ct_name = content_type.get("Name", "")
        else:
            ct_name = str(content_type)

        record_type = _CONTENT_TYPE_MAP.get(
            ct_name, "Entity",
        )

        # Confidence: authored=0.8, auto-generated=0.5
        created_by = item.get("createdBy", {})
        user_email = (
            created_by.get("user", {}).get("email", "")
        )
        author = fields.get("Author", user_email)
        is_auto = not author or author == "System Account"
        confidence = 0.5 if is_auto else 0.8

        # TTL: 0 for permanent docs, 7d for working items
        ttl = 0 if record_type == "Document" else 604800000

        body = fields.get("Body", "")
        body_text = strip_html(body) if body else ""

        created = (
            fields.get("Created")
            or item.get("createdDateTime", "")
        )
        modified = (
            fields.get("Modified")
            or item.get("lastModifiedDateTime", "")
        )

        record = {
            "record_id": uuid_from_hash("sp", item_id),
            "record_type": record_type,
            "created_at": to_iso(created),
            "observed_at": to_iso(modified),
            "source": {
                "system": "sharepoint",
                "actor": {
                    "id": str(author) if author else "",
                    "type": "human",
                },
            },
            "provenance": [{
                "type": "source",
                "ref": (
                    f"sharepoint://{self._site_id}"
                    f"/{list_id}/{item_id}"
                ),
            }],
            "confidence": {"score": confidence},
            "ttl": ttl,
            "content": {
                "title": fields.get("Title", ""),
                "body": body_text,
                "filename": fields.get("FileLeafRef", ""),
            },
            "labels": {
                "tags": self._extract_tags(fields),
            },
        }

        return record

    @staticmethod
    def _extract_tags(fields: Dict[str, Any]) -> List[str]:
        tags: List[str] = []
        moderation = fields.get("_ModerationStatus")
        if moderation:
            tags.append(f"approval:{moderation}")
        return tags

    # ── HTTP helpers (with retry for 429 / 503) ────────────────

    def _graph_request(
        self,
        url: str,
        *,
        method: str = "GET",
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a Graph API request with retry on throttle.

        Retries up to ``_MAX_RETRIES`` times on HTTP 429 or 503,
        using exponential backoff and honouring the ``Retry-After``
        header when present.
        """
        backoff = _INITIAL_BACKOFF_S
        last_exc: Optional[Exception] = None

        for attempt in range(_MAX_RETRIES + 1):
            token = self._auth.get_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
            data = None
            if body is not None:
                data = json.dumps(body).encode()
                headers["Content-Type"] = "application/json"

            req = urllib.request.Request(
                url,
                data=data,
                headers=headers,
                method=method,
            )
            try:
                with urllib.request.urlopen(
                    req, timeout=30,
                ) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                if exc.code not in (429, 503):
                    raise
                last_exc = exc
                retry_after = exc.headers.get(
                    "Retry-After",
                )
                if retry_after and retry_after.isdigit():
                    wait = int(retry_after)
                else:
                    wait = backoff
                logger.warning(
                    "Graph API %s (attempt %d/%d), "
                    "retrying in %ss: %s",
                    exc.code,
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    wait,
                    url[:120],
                )
                time.sleep(wait)
                backoff *= _BACKOFF_MULTIPLIER

        raise last_exc  # type: ignore[misc]

    def _graph_get(self, url: str) -> Dict[str, Any]:
        return self._graph_request(url)

    def _graph_post(
        self, url: str, body: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._graph_request(
            url, method="POST", body=body,
        )
