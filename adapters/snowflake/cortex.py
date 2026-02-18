"""Snowflake Cortex AI connector.

Provides LLM completion and embedding via the Cortex REST API.

Usage::

    connector = CortexConnector()
    result = connector.complete_sync("mistral-large", [{"role": "user", "content": "Hello"}])
    embeddings = connector.embed("e5-base-v2", ["text1", "text2"])
"""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Dict, List, Optional

from adapters.snowflake._auth import SnowflakeAuth

logger = logging.getLogger(__name__)


class CortexConnector:
    """Snowflake Cortex AI REST API connector.

    Uses ``/api/v2/cortex/inference:complete`` (SSE) and ``/api/v2/cortex/inference:embed``.
    """

    def __init__(self, auth: Optional[SnowflakeAuth] = None) -> None:
        self._auth = auth or SnowflakeAuth()

    def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """Send a completion request, returning SSE chunks as a list of strings."""
        url = f"{self._auth.base_url}/api/v2/cortex/inference:complete"
        payload: Dict[str, Any] = {"model": model, "messages": messages}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = tools

        headers = self._auth.get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "text/event-stream"

        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        chunks: List[str] = []
        with urllib.request.urlopen(req, timeout=60) as resp:
            for line in resp:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data:"):
                    chunk_data = line_str[5:].strip()
                    if chunk_data == "[DONE]":
                        break
                    try:
                        parsed = json.loads(chunk_data)
                        delta = parsed.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            chunks.append(content)
                    except (json.JSONDecodeError, IndexError):
                        pass

        return chunks

    def complete_sync(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Convenience: collect SSE stream into a single response dict."""
        chunks = self.complete(model, messages, max_tokens=max_tokens, temperature=temperature)
        full_text = "".join(chunks)
        return {
            "response": full_text,
            "model": model,
            "usage": {
                "chunks": len(chunks),
            },
        }

    def embed(self, model: str, texts: List[str]) -> Dict[str, Any]:
        """Generate embeddings for a list of texts."""
        url = f"{self._auth.base_url}/api/v2/cortex/inference:embed"
        payload = {"model": model, "input": texts}

        headers = self._auth.get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())

        return {
            "embeddings": [item.get("embedding", []) for item in result.get("data", [])],
            "model": model,
        }
