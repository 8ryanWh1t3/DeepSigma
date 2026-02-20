"""AskSage API connector for DeepSigma.

Provides query, model listing, dataset management, and training capabilities
via the AskSage REST API.

Usage::

    connector = AskSageConnector()
    result = connector.query("What is the NIST CSF?")
    models = connector.get_models()
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AskSageConnector:
    """AskSage API connector.

    Configuration via environment variables:

    - ``ASKSAGE_EMAIL``
    - ``ASKSAGE_API_KEY``
    - ``ASKSAGE_BASE_URL`` (default: ``https://api.asksage.ai``)

    Implements ConnectorV1 contract (v0.6.0+).
    """

    source_name = "asksage"

    def __init__(
        self,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._email = email or os.environ.get("ASKSAGE_EMAIL", "")
        self._api_key = api_key or os.environ.get("ASKSAGE_API_KEY", "")
        self._base_url = (base_url or os.environ.get("ASKSAGE_BASE_URL", "https://api.asksage.ai")).rstrip("/")

        self._cached_token: Optional[str] = None
        self._token_expiry: float = 0.0

    # ── Auth ─────────────────────────────────────────────────────

    def get_token(self) -> str:
        """Acquire or return cached 24h access token."""
        if self._cached_token and time.time() < self._token_expiry:
            return self._cached_token

        body = json.dumps({
            "email": self._email,
            "api_key": self._api_key,
        }).encode()
        resp = self._post("/user/get-token-with-api-key", body, use_token=False)
        token = resp.get("token") or resp.get("access_token", "")
        if not token:
            raise RuntimeError(f"AskSage token acquisition failed: {resp}")

        self._cached_token = token
        self._token_expiry = time.time() + 23 * 3600  # 23h to be safe
        return self._cached_token

    # ── Public API ───────────────────────────────────────────────

    def query(
        self,
        prompt: str,
        model: Optional[str] = None,
        dataset: Optional[str] = None,
        persona: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a query to AskSage and return the response."""
        payload: Dict[str, Any] = {"message": prompt}
        if model:
            payload["model"] = model
        if dataset:
            payload["dataset"] = dataset
        if persona:
            payload["persona"] = persona

        body = json.dumps(payload).encode()
        return self._post("/server/query", body)

    def query_with_file(
        self,
        prompt: str,
        file_path: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query with a file attachment."""
        payload: Dict[str, Any] = {"message": prompt, "file": file_path}
        if model:
            payload["model"] = model
        body = json.dumps(payload).encode()
        return self._post("/server/query_with_file", body)

    def get_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        resp = self._get("/server/get-models")
        return resp.get("models", resp.get("data", []))

    def get_datasets(self) -> List[Dict[str, Any]]:
        """List user datasets."""
        resp = self._get("/server/get-datasets")
        return resp.get("datasets", resp.get("data", []))

    def get_personas(self) -> List[Dict[str, Any]]:
        """List available personas."""
        resp = self._get("/server/get-personas")
        return resp.get("personas", resp.get("data", []))

    def get_user_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get prompt history."""
        resp = self._get(f"/user/get-user-logs?limit={limit}")
        return resp.get("logs", resp.get("data", []))

    def train(self, content: str, dataset: str) -> Dict[str, Any]:
        """Train on content into a dataset."""
        payload = {"content": content, "dataset": dataset}
        body = json.dumps(payload).encode()
        return self._post("/server/train", body)

    # ── ConnectorV1 contract ─────────────────────────────────────

    def list_records(
        self, **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Not supported — AskSage is query-based.

        Use ``query()`` or ``get_user_logs()`` instead.
        """
        raise NotImplementedError(
            "AskSage is query-based; "
            "use query() or get_user_logs()"
        )

    def get_record(
        self,
        record_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Not supported — AskSage is query-based.

        Use ``query()`` instead.
        """
        raise NotImplementedError(
            "AskSage is query-based; use query()"
        )

    def to_envelopes(
        self, records: List[Dict[str, Any]],
    ) -> list:
        """Wrap records in RecordEnvelope (ConnectorV1)."""
        from adapters.contract import (
            canonical_to_envelope,
        )
        return [
            canonical_to_envelope(
                r, source_instance=self._base_url,
            )
            for r in records
        ]

    # ── HTTP helpers ─────────────────────────────────────────────

    def _post(self, path: str, body: bytes, use_token: bool = True) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if use_token:
            headers["x-access-tokens"] = self.get_token()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = {"x-access-tokens": self.get_token()}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
