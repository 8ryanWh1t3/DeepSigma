"""Tests for adapters._azure_auth — Azure AD OAuth 2.0 helper."""
from __future__ import annotations

import json
import time
from urllib.parse import urlparse
from unittest.mock import MagicMock, patch

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_auth(**overrides):
    from adapters._azure_auth import AzureADAuth
    defaults = dict(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
        scope="https://graph.microsoft.com/.default",
    )
    defaults.update(overrides)
    # Patch out msal import to test urllib path
    with patch.dict("sys.modules", {"msal": None}):
        auth = AzureADAuth(**defaults)
    return auth


class TestAzureADAuth:
    def test_constructor_stores_config(self):
        auth = _make_auth()
        assert auth._tenant_id == "test-tenant"
        assert auth._client_id == "test-client"
        assert auth._scope == "https://graph.microsoft.com/.default"

    def test_msal_not_available(self):
        auth = _make_auth()
        assert auth._msal_app is None

    @patch("urllib.request.urlopen")
    def test_get_token_urllib(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "access_token": "tok-abc-123",
            "expires_in": 3600,
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        auth = _make_auth()
        token = auth.get_token()
        assert token == "tok-abc-123"
        req = mock_urlopen.call_args[0][0]
        parsed = urlparse(req.full_url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "login.microsoftonline.com"
        assert "/test-tenant/" in parsed.path
        assert req.data is not None

    @patch("urllib.request.urlopen")
    def test_token_caching(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "access_token": "cached-tok",
            "expires_in": 3600,
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        auth = _make_auth()
        tok1 = auth.get_token()
        tok2 = auth.get_token()
        assert tok1 == tok2 == "cached-tok"
        assert mock_urlopen.call_count == 1  # only one HTTP call

    @patch("urllib.request.urlopen")
    def test_token_refresh_on_expiry(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "access_token": "fresh-tok",
            "expires_in": 3600,
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        auth = _make_auth()
        auth.get_token()
        # Simulate expired token
        auth._token_expiry = time.time() - 1
        auth.get_token()
        assert mock_urlopen.call_count == 2  # refreshed

    @patch("urllib.request.urlopen")
    def test_error_on_missing_access_token(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "error": "invalid_client",
            "error_description": "Bad credentials",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        auth = _make_auth()
        with pytest.raises(RuntimeError, match="Bad credentials"):
            auth.get_token()

    def test_msal_path_when_available(self):
        mock_msal = MagicMock()
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "msal-tok",
            "expires_in": 3600,
        }
        mock_msal.ConfidentialClientApplication.return_value = mock_app

        with patch.dict("sys.modules", {"msal": mock_msal}):
            from adapters._azure_auth import AzureADAuth
            auth = AzureADAuth(
                tenant_id="t", client_id="c",
                client_secret="s", scope="scope",
            )
            token = auth.get_token()
            assert token == "msal-tok"
            mock_app.acquire_token_for_client.assert_called_once()

    def test_msal_error(self):
        mock_msal = MagicMock()
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_grant",
            "error_description": "Token expired",
        }
        mock_msal.ConfidentialClientApplication.return_value = mock_app

        with patch.dict("sys.modules", {"msal": mock_msal}):
            from adapters._azure_auth import AzureADAuth
            auth = AzureADAuth(
                tenant_id="t", client_id="c",
                client_secret="s", scope="scope",
            )
            with pytest.raises(RuntimeError, match="Token expired"):
                auth.get_token()

    @patch("urllib.request.urlopen")
    def test_request_body_format(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "access_token": "tok",
            "expires_in": 3600,
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        auth = _make_auth()
        auth.get_token()
        req = mock_urlopen.call_args[0][0]
        body = req.data.decode()
        assert "grant_type=client_credentials" in body
        assert "client_id=test-client" in body
        assert "client_secret=test-secret" in body
        assert "scope=https" in body
