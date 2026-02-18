"""Snowflake authentication helper.

Supports three auth methods:
1. JWT (keypair) — requires ``cryptography`` optional dep
2. OAuth — pre-generated OAuth token
3. Programmatic Access Token (PAT) — pre-generated token

Usage::

    auth = SnowflakeAuth()
    headers = auth.get_headers()
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SnowflakeAuth:
    """Snowflake authentication with JWT, OAuth, or PAT support.

    Configuration via environment variables:

    - ``SNOWFLAKE_ACCOUNT``
    - ``SNOWFLAKE_USER``
    - ``SNOWFLAKE_PRIVATE_KEY_PATH`` — RSA private key for JWT auth
    - ``SNOWFLAKE_TOKEN`` — pre-generated OAuth or PAT token
    """

    def __init__(
        self,
        account: Optional[str] = None,
        user: Optional[str] = None,
        private_key_path: Optional[str] = None,
        token: Optional[str] = None,
    ) -> None:
        self._account = account or os.environ.get("SNOWFLAKE_ACCOUNT", "")
        self._user = user or os.environ.get("SNOWFLAKE_USER", "")
        self._private_key_path = private_key_path or os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH", "")
        self._token = token or os.environ.get("SNOWFLAKE_TOKEN", "")

        self._jwt_token: Optional[str] = None
        self._jwt_expiry: float = 0.0

    @property
    def account(self) -> str:
        return self._account

    @property
    def base_url(self) -> str:
        return f"https://{self._account}.snowflakecomputing.com"

    def get_headers(self) -> Dict[str, str]:
        """Return Authorization headers for Snowflake REST API."""
        if self._private_key_path:
            token = self._get_jwt_token()
            return {
                "Authorization": f"Bearer {token}",
                "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
            }
        elif self._token:
            # Detect token type
            token_type = "OAUTH"
            if self._token.startswith("ver:"):
                token_type = "PROGRAMMATIC_ACCESS_TOKEN"
            return {
                "Authorization": f"Bearer {self._token}",
                "X-Snowflake-Authorization-Token-Type": token_type,
            }
        else:
            raise RuntimeError(
                "No Snowflake auth configured. Set SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_TOKEN."
            )

    def _get_jwt_token(self) -> str:
        """Generate JWT from RSA private key (requires cryptography)."""
        if self._jwt_token and time.time() < self._jwt_expiry:
            return self._jwt_token

        try:
            from cryptography.hazmat.primitives import serialization
            import hashlib
            import base64
        except ImportError:
            raise RuntimeError(
                "cryptography package required for JWT auth. "
                "Install with: pip install 'deepsigma[snowflake]'"
            )

        from pathlib import Path
        key_data = Path(self._private_key_path).read_bytes()
        private_key = serialization.load_pem_private_key(key_data, password=None)

        # Build JWT manually to avoid PyJWT dependency
        public_key = private_key.public_key()
        public_key_der = public_key.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        fingerprint = hashlib.sha256(public_key_der).digest()
        fp_b64 = base64.b64encode(fingerprint).decode()

        account_upper = self._account.upper().split(".")[0]
        user_upper = self._user.upper()
        qualified_user = f"{account_upper}.{user_upper}"

        now = int(time.time())
        exp = now + 3600  # 1 hour

        # Build JWT (header.payload.signature)
        header = base64.urlsafe_b64encode(json.dumps({
            "alg": "RS256",
            "typ": "JWT",
        }).encode()).rstrip(b"=").decode()

        payload = base64.urlsafe_b64encode(json.dumps({
            "iss": f"{qualified_user}.SHA256:{fp_b64}",
            "sub": qualified_user,
            "iat": now,
            "exp": exp,
        }).encode()).rstrip(b"=").decode()

        signing_input = f"{header}.{payload}".encode()

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        signature = private_key.sign(
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

        self._jwt_token = f"{header}.{payload}.{sig_b64}"
        self._jwt_expiry = exp - 60  # refresh 60s before expiry
        return self._jwt_token
