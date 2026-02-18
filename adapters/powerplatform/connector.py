"""Dataverse Web API connector for DeepSigma canonical record ingestion.

Implements the field mapping from ``llm_data_model/04_mappings/power_platform_mapping.md``.

Usage::

    connector = DataverseConnector()
    records = connector.list_records("accounts")
    result  = connector.query("incidents", "$filter=statecode eq 0")
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional

from adapters._azure_auth import AzureADAuth
from adapters._connector_helpers import to_iso

logger = logging.getLogger(__name__)

# Dataverse table → canonical record_type
_TABLE_TYPE_MAP: Dict[str, str] = {
    "accounts": "Entity",
    "contacts": "Entity",
    "incidents": "Event",
    "cases": "Event",
    "annotations": "Document",
    "notes": "Document",
    "tasks": "Event",
    "emails": "Event",
}

# Confidence by table category
_TABLE_CONFIDENCE: Dict[str, float] = {
    "accounts": 0.95,
    "contacts": 0.95,
    "incidents": 0.75,
    "cases": 0.75,
    "annotations": 0.75,
    "notes": 0.75,
}

# TTL defaults (ms) per table
_TABLE_TTL: Dict[str, int] = {
    "accounts": 86400000,       # 24h
    "contacts": 86400000,
    "incidents": 3600000,       # 1h (active)
    "cases": 3600000,
    "annotations": 0,           # perpetual
    "notes": 0,
}


class DataverseConnector:
    """Microsoft Dataverse Web API connector.

    Configuration is read from environment variables:

    - ``DV_ENVIRONMENT_URL`` — e.g. ``https://org.crm.dynamics.com``
    - ``DV_CLIENT_ID``
    - ``DV_CLIENT_SECRET``
    - ``DV_TENANT_ID``

    Implements ConnectorV1 contract (v0.6.0+).
    """

    source_name = "dataverse"

    def __init__(
        self,
        environment_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        self._env_url = (environment_url or os.environ.get("DV_ENVIRONMENT_URL", "")).rstrip("/")
        self._client_id = client_id or os.environ.get("DV_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("DV_CLIENT_SECRET", "")
        self._tenant_id = tenant_id or os.environ.get("DV_TENANT_ID", "")

        scope = f"{self._env_url}/.default" if self._env_url else ""
        self._auth = AzureADAuth(
            tenant_id=self._tenant_id,
            client_id=self._client_id,
            client_secret=self._client_secret,
            scope=scope,
        )

    # ── Public API ───────────────────────────────────────────────

    def list_records(self, table_name: str) -> List[Dict[str, Any]]:
        """Fetch all records from a Dataverse table."""
        url = f"{self._env_url}/api/data/v9.2/{table_name}"
        data = self._dv_get(url)
        rows = data.get("value", [])
        return [self._to_canonical(row, table_name) for row in rows]

    def get_record(self, table_name: str, record_id: str) -> Dict[str, Any]:
        """Fetch a single record by Dataverse GUID."""
        url = f"{self._env_url}/api/data/v9.2/{table_name}({record_id})"
        row = self._dv_get(url)
        return self._to_canonical(row, table_name)

    def query(self, table_name: str, filter_expr: str) -> List[Dict[str, Any]]:
        """Query with OData $filter expression."""
        url = f"{self._env_url}/api/data/v9.2/{table_name}?{filter_expr}"
        data = self._dv_get(url)
        rows = data.get("value", [])
        return [self._to_canonical(row, table_name) for row in rows]

    # ── Envelope contract ──────────────────────────────────────────

    def to_envelopes(self, records: List[Dict[str, Any]]) -> list:
        """Wrap canonical records in RecordEnvelope instances (ConnectorV1)."""
        from connectors.contract import canonical_to_envelope
        env_name = self._env_url.split("//")[-1].split(".")[0] if self._env_url else "unknown"
        return [canonical_to_envelope(r, source_instance=env_name) for r in records]

    # ── Field mapping ────────────────────────────────────────────

    def _to_canonical(self, row: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Transform a Dataverse row to a canonical record envelope."""
        # Find the primary key (table-specific <entity>id or fallback)
        pk = self._extract_pk(row, table_name)
        record_id = f"rec_{pk}" if pk else ""

        record_type = _TABLE_TYPE_MAP.get(table_name, "Claim")
        confidence = _TABLE_CONFIDENCE.get(table_name, 0.70)
        ttl = _TABLE_TTL.get(table_name, 604800000)

        # Resolve TTL for resolved/inactive cases
        statecode = row.get("statecode")
        if statecode is not None and int(statecode) != 0:
            ttl = 0  # resolved/inactive → perpetual
            confidence = max(confidence, 0.80)

        # Owner type mapping
        owner_type = row.get("_ownerid_type", "")
        actor_type = "human" if owner_type == "systemuser" else "system"

        # Tags from state/status
        tags: List[str] = []
        if statecode is not None:
            state_map = {0: "Active", 1: "Inactive", 2: "Resolved"}
            tags.append(f"state:{state_map.get(int(statecode), str(statecode))}")
        statuscode = row.get("statuscode")
        if statuscode is not None:
            tags.append(f"status:{statuscode}")

        # Build content from remaining fields (excluding metadata)
        content = {
            k: v for k, v in row.items()
            if not k.startswith("@") and not k.startswith("_") and k not in (
                "createdon", "modifiedon", "statecode", "statuscode",
            )
        }

        env_name = self._env_url.split("//")[-1].split(".")[0] if self._env_url else "unknown"

        return {
            "record_id": record_id,
            "record_type": record_type,
            "created_at": to_iso(row.get("createdon", "")),
            "observed_at": to_iso(row.get("modifiedon", "")),
            "source": {
                "system": "dataverse",
                "actor": {
                    "id": row.get("_ownerid_value", ""),
                    "type": actor_type,
                },
            },
            "provenance": [
                {
                    "type": "source",
                    "ref": f"dataverse://{env_name}/{table_name}/{pk}",
                }
            ],
            "confidence": {"score": confidence},
            "ttl": ttl,
            "content": content,
            "labels": {"tags": tags},
        }

    @staticmethod
    def _extract_pk(row: Dict[str, Any], table_name: str) -> str:
        """Extract primary key from a Dataverse row."""
        # Common pattern: singular form + "id" (e.g., accountid, contactid)
        singular = table_name.rstrip("s")
        pk_field = f"{singular}id"
        if pk_field in row:
            return str(row[pk_field])
        # Fallback: activityid (for activities)
        if "activityid" in row:
            return str(row["activityid"])
        # Last resort: scan for any field ending in "id" that's a GUID
        for k, v in row.items():
            if k.endswith("id") and isinstance(v, str) and len(v) == 36:
                return v
        return ""

    # ── HTTP helpers ─────────────────────────────────────────────

    def _dv_get(self, url: str) -> Dict[str, Any]:
        token = self._auth.get_token()
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
