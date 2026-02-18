"""Azure AD OAuth 2.0 client-credentials helper.

Shared by SharePoint (E17) and Power Platform (E18) connectors.
Uses ``msal`` when available, falls back to raw ``urllib`` token request.

Usage::

    auth = AzureADAuth(
        tenant_id=os.environ["SP_TENANT_ID"],
        client_id=os.environ["SP_CLIENT_ID"],
        client_secret=os.environ["SP_CLIENT_SECRET"],
        scope="https://graph.microsoft.com/.default",
    )
    token = auth.get_token()
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

# Token refresh buffer — refresh if less than 60s remaining
_REFRESH_BUFFER_S = 60


class AzureADAuth:
    """Azure AD client-credentials OAuth 2.0 with token caching.

    Parameters
    ----------
    tenant_id : str
        Azure AD tenant (directory) ID.
    client_id : str
        Application (client) ID.
    client_secret : str
        Client secret value.
    scope : str
        OAuth scope, e.g. ``https://graph.microsoft.com/.default``.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scope: str,
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope

        self._cached_token: Optional[str] = None
        self._token_expiry: float = 0.0

        # Try to use msal for robust token management
        self._msal_app = None
        try:
            import msal  # type: ignore[import-untyped]
            self._msal_app = msal.ConfidentialClientApplication(
                client_id,
                authority=f"https://login.microsoftonline.com/{tenant_id}",
                client_credential=client_secret,
            )
            logger.debug("Using msal for Azure AD auth")
        except ImportError:
            logger.debug("msal not installed, using urllib fallback")

    def get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if self._cached_token and time.time() < self._token_expiry - _REFRESH_BUFFER_S:
            return self._cached_token

        if self._msal_app is not None:
            return self._acquire_msal()

        return self._acquire_urllib()

    # ── msal path ────────────────────────────────────────────────

    def _acquire_msal(self) -> str:
        result = self._msal_app.acquire_token_for_client(scopes=[self._scope])
        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "unknown"))
            raise RuntimeError(f"Azure AD token acquisition failed: {error}")
        self._cached_token = result["access_token"]
        self._token_expiry = time.time() + result.get("expires_in", 3600)
        return self._cached_token

    # ── urllib fallback ──────────────────────────────────────────

    def _acquire_urllib(self) -> str:
        url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        body = (
            f"grant_type=client_credentials"
            f"&client_id={self._client_id}"
            f"&client_secret={self._client_secret}"
            f"&scope={self._scope}"
        ).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if "access_token" not in data:
            raise RuntimeError(f"Azure AD token error: {data.get('error_description', 'unknown')}")
        self._cached_token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600)
        return self._cached_token
