"""llama.cpp / OpenAI-compatible local inference connector.

Targets any server exposing ``/v1/chat/completions``, ``/v1/completions``,
and ``/v1/models`` — llama.cpp, Ollama, vLLM, LocalAI, text-gen-webui, etc.

Usage::

    connector = LlamaCppConnector()
    result = connector.chat([{"role": "user", "content": "Hello"}])
    print(result["text"])

Configure via environment variables::

    DEEPSIGMA_LOCAL_BASE_URL  (default: http://localhost:8080)
    DEEPSIGMA_LOCAL_API_KEY   (optional bearer token)
    DEEPSIGMA_LOCAL_MODEL     (empty = server default)
    DEEPSIGMA_LOCAL_TIMEOUT   (default: 120 seconds)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8080"
_DEFAULT_TIMEOUT = 120


class LlamaCppConnector:
    """OpenAI-compatible local inference connector.

    Works with any server that implements the ``/v1/chat/completions``
    and ``/v1/models`` endpoints (llama.cpp, Ollama, vLLM, LocalAI, etc.).
    """

    source_name = "local_llm"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("DEEPSIGMA_LOCAL_BASE_URL", _DEFAULT_BASE_URL)
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("DEEPSIGMA_LOCAL_API_KEY", "")
        self.model = model or os.environ.get("DEEPSIGMA_LOCAL_MODEL", "")
        self.timeout = timeout or int(
            os.environ.get("DEEPSIGMA_LOCAL_TIMEOUT", str(_DEFAULT_TIMEOUT))
        )

    # ── Public API ────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request.

        Returns::

            {
                "text": str,
                "model": str,
                "backend": "llama.cpp",
                "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
                "timing": {"latency_ms": int},
            }
        """
        payload: Dict[str, Any] = {"messages": messages}
        if self.model:
            payload["model"] = self.model
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        start = time.monotonic()
        data = self._post("/v1/chat/completions", payload)
        latency_ms = int((time.monotonic() - start) * 1000)

        text = ""
        choices = data.get("choices", [])
        if choices:
            text = choices[0].get("message", {}).get("content", "")

        return {
            "text": text,
            "model": data.get("model", self.model),
            "backend": "llama.cpp",
            "usage": data.get("usage", {}),
            "timing": {"latency_ms": latency_ms},
        }

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Send a text completion request (``/v1/completions``).

        Returns the same shape as :meth:`chat`.
        """
        payload: Dict[str, Any] = {"prompt": prompt}
        if self.model:
            payload["model"] = self.model
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        start = time.monotonic()
        data = self._post("/v1/completions", payload)
        latency_ms = int((time.monotonic() - start) * 1000)

        text = ""
        choices = data.get("choices", [])
        if choices:
            text = choices[0].get("text", "")

        return {
            "text": text,
            "model": data.get("model", self.model),
            "backend": "llama.cpp",
            "usage": data.get("usage", {}),
            "timing": {"latency_ms": latency_ms},
        }

    def health(self) -> Dict[str, Any]:
        """Check server health via ``GET /v1/models``.

        Returns::

            {"ok": True, "models": [...], "base_url": str}
        """
        try:
            data = self._get("/v1/models")
            models = [m.get("id", "") for m in data.get("data", [])]
            return {"ok": True, "models": models, "base_url": self.base_url}
        except Exception as exc:
            logger.warning("Local LLM health check failed: %s", exc)
            return {"ok": False, "models": [], "base_url": self.base_url, "error": str(exc)}

    def model_info(self) -> Dict[str, Any]:
        """Return the first model entry from ``GET /v1/models``, or ``{}``."""
        try:
            data = self._get("/v1/models")
            entries = data.get("data", [])
            return entries[0] if entries else {}
        except Exception:
            return {}

    # ── Internal HTTP helpers ─────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "httpx required for local inference: pip install -e '.[local]'"
            ) from exc

        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def _get(self, path: str) -> Dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "httpx required for local inference: pip install -e '.[local]'"
            ) from exc

        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()
