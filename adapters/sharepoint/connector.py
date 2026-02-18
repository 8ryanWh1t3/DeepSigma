"""SharePoint Graph API connector for DeepSigma canonical record ingestion.

Implements the field mapping from ``llm_data_model/04_mappings/sharepoint_mapping.md``.

Usage::

    connector = SharePointConnector()
    records = connector.list_items("my-list-id")
    result  = connector.delta_sync("my-list-id")
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional

from adapters._azure_auth import AzureADAuth
from adapters._connector_helpers import strip_html, to_iso, uuid_from_hash

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

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
        self._tenant_id = tenant_id or os.environ.get("SP_TENANT_ID", "")
        self._client_id = client_id or os.environ.get("SP_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("SP_CLIENT_SECRET", "")
        self._site_id = site_id or os.environ.get("SP_SITE_ID", "")

        self._auth = AzureADAuth(
            tenant_id=self._tenant_id,
            client_id=self._client_id,
            client_secret=self._client_secret,
            scope="https://graph.microsoft.com/.default",
        )

        # Delta tokens per list for incremental sync
        self._delta_tokens: Dict[str, str] = {}

    # ── Public API ───────────────────────────────────────────────

    def list_items(self, list_id: str) -> List[Dict[str, Any]]:
        """Fetch all items from a SharePoint list and return canonical records."""
        url = f"{GRAPH_BASE}/sites/{self._site_id}/lists/{list_id}/items?expand=fields"
        data = self._graph_get(url)
        items = data.get("value", [])
        return [self._to_canonical(item, list_id) for item in items]

    def get_item(self, list_id: str, item_id: str) -> Dict[str, Any]:
        """Fetch a single list item and return a canonical record."""
        url = f"{GRAPH_BASE}/sites/{self._site_id}/lists/{list_id}/items/{item_id}?expand=fields"
        item = self._graph_get(url)
        return self._to_canonical(item, list_id)

    def delta_sync(self, list_id: str) -> Dict[str, Any]:
        """Incremental sync using Graph delta queries.

        Returns ``{synced: str, created: int, updated: int, records: list}``.
        """
        delta_token = self._delta_tokens.get(list_id)
        if delta_token:
            url = delta_token
        else:
            url = f"{GRAPH_BASE}/sites/{self._site_id}/lists/{list_id}/items/delta?expand=fields"

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

    def subscribe(self, list_id: str, webhook_url: str, expiry_hours: int = 48) -> Dict[str, Any]:
        """Create a Graph API webhook subscription for a list."""
        from datetime import datetime, timedelta, timezone

        expiry = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
        body = {
            "changeType": "created,updated,deleted",
            "notificationUrl": webhook_url,
            "resource": f"sites/{self._site_id}/lists/{list_id}/items",
            "expirationDateTime": expiry,
        }
        return self._graph_post(f"{GRAPH_BASE}/subscriptions", body)

    # ── Envelope contract ──────────────────────────────────────────

    def to_envelopes(self, records: List[Dict[str, Any]]) -> list:
        """Wrap canonical records in RecordEnvelope instances (ConnectorV1)."""
        from connectors.contract import canonical_to_envelope
        instance = f"{self._site_id}" if self._site_id else "unknown"
        return [canonical_to_envelope(r, source_instance=instance) for r in records]

    # ── Field mapping ────────────────────────────────────────────

    def _to_canonical(self, item: Dict[str, Any], list_id: str) -> Dict[str, Any]:
        """Transform a Graph API list item to a canonical record envelope."""
        fields = item.get("fields", {})
        item_id = str(item.get("id", fields.get("id", "")))
        content_type = fields.get("ContentType", {})
        ct_name = content_type.get("Name", "") if isinstance(content_type, dict) else str(content_type)

        record_type = _CONTENT_TYPE_MAP.get(ct_name, "Entity")

        # Confidence: 0.8 for authored, 0.5 for auto-generated
        author = fields.get("Author", item.get("createdBy", {}).get("user", {}).get("email", ""))
        confidence = 0.5 if not author or author == "System Account" else 0.8

        # TTL: 0 for policy/permanent, 604800000 (7d) for working docs
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
            "provenance": [
                {
                    "type": "source",
                    "ref": f"sharepoint://{self._site_id}/{list_id}/{item_id}",
                }
            ],
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

    # ── HTTP helpers ─────────────────────────────────────────────

    def _graph_get(self, url: str) -> Dict[str, Any]:
        token = self._auth.get_token()
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def _graph_post(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        token = self._auth.get_token()
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
